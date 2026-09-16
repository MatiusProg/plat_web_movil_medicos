"""Restaura una organización desde su copia de seguridad, desde la consola.

    python manage.py restore_organization --file respaldo-kolping3k-20260915-2240.json
    python manage.py restore_organization --file ... --yes      # sin preguntar

**Esto borra y reescribe todos los datos de la organización.** Por eso el
comando pregunta antes, mostrando de qué organización es el archivo, de cuándo
y cuántas filas trae. ``--yes`` salta la pregunta y existe sólo para una tarea
programada; escribirlo a mano es asumir que ya se leyó el resumen.

La organización de destino **sale del archivo**, no de un parámetro. Es
deliberado: dejar elegir el destino es la forma de volcar el padrón de un
centro médico dentro de otro por un error de tipeo. Si el archivo es de
``kolping3k``, se restaura en ``kolping3k`` o no se restaura.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ... import manifest, services
from ...models import BackupRecord


class Command(BaseCommand):
    help = "Restaura una organización desde un archivo de respaldo JSON."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True,
                            help="Ruta del archivo de respaldo.")
        parser.add_argument("--yes", action="store_true",
                            help="No preguntar antes de reemplazar los datos.")

    def handle(self, *args, **options):
        archivo = Path(options["file"]).expanduser().resolve()
        if not archivo.is_file():
            raise CommandError(f"No existe el archivo {archivo}.")

        try:
            documento = json.loads(archivo.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CommandError(f"El archivo no es un JSON válido: {error}") from error

        try:
            resumen = services.inspect(documento)
        except services.BackupError as error:
            raise CommandError(error.detail) from error

        datos = resumen["organization"] or {}
        with platform_admin_context():
            organization = Organization.objects.filter(id=datos.get("id")).first()

        if organization is None:
            raise CommandError(
                f"El respaldo es de la organización «{datos.get('slug')}» "
                f"({datos.get('id')}), que no existe en esta base. Creala "
                "primero: una restauración vuelca datos dentro de una "
                "organización que ya existe, no la crea.",
            )

        self._mostrar(resumen, organization, archivo)

        if not options["yes"] and not self._confirmar(organization):
            self.stdout.write("Cancelado. No se tocó nada.")
            return

        try:
            resultado = services.restore(documento, organization)
        except services.BackupError as error:
            raise CommandError(error.detail) from error

        with tenant_context(organization.id):
            BackupRecord.objects.create(
                organization=organization,
                kind=BackupRecord.Kind.RESTORE,
                performed_by=None,
                filename=archivo.name,
                row_counts=resultado["written"],
                checksum=documento.get("checksum", ""),
            )

        escritas = sum(resultado["written"].values())
        borradas = sum(resultado["deleted"].values())
        self.stdout.write(self.style.SUCCESS(
            f"Restaurado: {borradas} fila(s) borradas, {escritas} escritas.",
        ))
        if resultado["skipped"]:
            etiquetas = ", ".join(
                manifest.BY_KEY[clave].label for clave in resultado["skipped"]
            )
            self.stdout.write(
                f"No se tocaron (nunca se restauran): {etiquetas}.",
            )

    def _mostrar(self, resumen, organization, archivo):
        self.stdout.write("")
        self.stdout.write(f"  Archivo:       {archivo.name}")
        self.stdout.write(f"  Organización:  {organization.name} "
                          f"({organization.slug})")
        self.stdout.write(f"  Generado:      {resumen['generated_at']}")
        self.stdout.write("  Contenido:")
        for clave, cantidad in (resumen["counts"] or {}).items():
            if not cantidad:
                continue
            tabla = manifest.BY_KEY.get(clave)
            etiqueta = tabla.label if tabla else clave
            nota = "" if (tabla and tabla.restore) else "   (no se restaura)"
            self.stdout.write(f"      {cantidad:>7}  {etiqueta}{nota}")
        self.stdout.write("")

    def _confirmar(self, organization) -> bool:
        """Pide escribir el slug, no un «sí».

        Un «sí» se contesta sin leer; escribir el nombre de la organización
        que está por reemplazarse obliga a mirar cuál es. Es la misma idea que
        usan las herramientas que borran repositorios.
        """
        self.stdout.write(self.style.WARNING(
            "Esto BORRA y reescribe todos los datos de esta organización. "
            "No se puede deshacer.",
        ))
        respuesta = input(
            f"Escribí «{organization.slug}» para continuar: ",
        ).strip()
        return respuesta == organization.slug
