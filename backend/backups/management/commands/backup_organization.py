"""Copia de seguridad de **una organización**, desde la consola.

    python manage.py backup_organization --organization kolping3k
    python manage.py backup_organization --organization morita2 --output C:\\respaldos

Es el mismo trabajo que ``POST /api/backups/create/`` y llama al mismo
servicio. Existe aparte por dos casos que la API no cubre:

1. **Respaldar todas las organizaciones de una vez** —``--all``—, que es lo que
   haría una tarea programada nocturna.
2. **Respaldar cuando la aplicación web no está disponible.** El caso de uso de
   un respaldo suele ser precisamente ése.

Lo que la consola **no** hace es dejar el asiento en la bitácora de US-06: no
hay petición HTTP de la que sacar la IP ni usuario que la firme. Queda el
registro en ``backup_records`` con ``performed_by`` en NULL, que se lee como
«lo hizo el sistema». Es una diferencia real y está dicha acá para que nadie
concluya, mirando la bitácora, que ese respaldo no existió.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ... import services
from ...models import BackupRecord


class Command(BaseCommand):
    help = "Genera la copia de seguridad de una organización, en JSON."

    def add_arguments(self, parser):
        grupo = parser.add_mutually_exclusive_group(required=True)
        grupo.add_argument(
            "--organization",
            help="Slug de la organización a respaldar.",
        )
        grupo.add_argument(
            "--all", action="store_true",
            help="Respaldar todas las organizaciones activas.",
        )
        parser.add_argument(
            "--output", default=".",
            help="Carpeta donde dejar los archivos. Por omisión, la actual.",
        )

    def handle(self, *args, **options):
        destino = Path(options["output"]).expanduser().resolve()
        destino.mkdir(parents=True, exist_ok=True)

        # Listar organizaciones exige contexto de plataforma: la tabla
        # `organizations` está protegida por RLS como todo lo demás.
        with platform_admin_context():
            if options["all"]:
                organizaciones = list(Organization.objects.all())
            else:
                slug = options["organization"]
                organizaciones = list(Organization.objects.filter(slug=slug))
                if not organizaciones:
                    disponibles = ", ".join(
                        Organization.objects.values_list("slug", flat=True)
                    ) or "(ninguna)"
                    raise CommandError(
                        f"No existe la organización «{slug}». "
                        f"Las que hay: {disponibles}.",
                    )

        if not organizaciones:
            raise CommandError("No hay ninguna organización que respaldar.")

        for organization in organizaciones:
            self._respaldar(organization, destino)

    def _respaldar(self, organization, destino):
        self.stdout.write(f"Respaldando «{organization.name}» …")

        documento = services.create(organization)
        contenido = services.to_bytes(documento)
        archivo = destino / services.filename(
            organization, documento["generated_at"],
        )
        archivo.write_bytes(contenido)

        # El registro va dentro del contexto del inquilino: `backup_records`
        # tiene RLS y sin contexto el INSERT se rechaza.
        with tenant_context(organization.id):
            BackupRecord.objects.create(
                organization=organization,
                kind=BackupRecord.Kind.BACKUP,
                performed_by=None,
                filename=archivo.name,
                size_bytes=len(contenido),
                row_counts=documento["counts"],
                checksum=documento["checksum"],
            )

        filas = sum(documento["counts"].values())
        self.stdout.write(self.style.SUCCESS(
            f"  {archivo}  ·  {filas} fila(s)  ·  "
            f"{len(contenido) / 1024:.0f} KB",
        ))
