"""US-31, pieza 1 — Indexa el catálogo de una organización.

    python manage.py embed_catalog --organization demo
    python manage.py embed_catalog --all
    python manage.py embed_catalog --organization demo --only specialty
    python manage.py embed_catalog --all --dry-run     # qué indexaría, sin tocar nada

**Corre dentro de ``tenant_context(org.id)``**, como toda tarea fuera del ciclo
HTTP. Sin contexto, las consultas al catálogo devuelven cero filas y el comando
terminaría con éxito habiendo indexado nada — el modo de fallo más caro que
tiene este proyecto, y el que ya pasó una vez con ``catalog/0004_seed_demo``
(ver ``seed_catalog``).

**Es un comando y no un endpoint** porque recorre el catálogo entero y llama al
proveedor de embeddings. Exponerlo por HTTP es poner un botón que gasta cuota y
tarda minutos.

**Reemplaza, no acumula.** Cada fragmento se identifica por su origen y su
título, así que reindexar actualiza el vector en su lugar. Los fragmentos cuyo
origen ya no existe —una especialidad dada de baja— se borran: dejarlos es que
el asistente siga sugiriendo una especialidad que ya no atiende.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ... import corpus, embeddings
from ...models import KnowledgeChunk

# De a cuántos se vectoriza por llamada al proveedor. Con lotes muy grandes,
# un fallo de red obliga a rehacer todo el lote; con lotes de uno, son cien
# viajes. Sesenta y cuatro es el punto cómodo.
LOTE = 64


class Command(BaseCommand):
    help = "Indexa el catálogo de una organización para el asistente (US-31)."

    def add_arguments(self, parser):
        grupo = parser.add_mutually_exclusive_group(required=True)
        grupo.add_argument("--organization",
                           help="Slug de la organización a indexar.")
        grupo.add_argument("--all", action="store_true",
                           help="Indexar todas las organizaciones.")
        parser.add_argument(
            "--only", action="append", dest="source_types",
            choices=list(KnowledgeChunk.Source.values),
            help="Indexar sólo este tipo de fuente. Se puede repetir.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Mostrar qué se indexaría, sin escribir ni llamar al proveedor.",
        )

    def handle(self, *args, **options):
        proveedor = embeddings.provider_name()

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

        self.stdout.write(f"Proveedor de embeddings: {proveedor}")
        if proveedor == embeddings.LOCAL:
            self.stdout.write(self.style.WARNING(
                "  Sin OPENAI_API_KEY: se usa el proveedor local, que sólo "
                "captura solapamiento de palabras. Sirve para probar el "
                "camino completo; no para producción.",
            ))

        for organization in organizaciones:
            self._indexar(organization, options, proveedor)

    def _indexar(self, organization, options, proveedor):
        self.stdout.write(f"\n{organization.name} ({organization.slug})")

        with tenant_context(organization.id):
            fragmentos = corpus.build(organization, options["source_types"])

            if not fragmentos:
                self.stdout.write(self.style.WARNING(
                    "  El catálogo está vacío: no hay nada que indexar. "
                    "Sembralo con «manage.py seed_catalog» o cargalo por la "
                    "aplicación.",
                ))
                return

            if options["dry_run"]:
                for fragmento in fragmentos:
                    self.stdout.write(
                        f"  [{fragmento['source_type']}] {fragmento['title']}"
                        f"  ({len(fragmento['content'])} caracteres)",
                    )
                self.stdout.write(f"  {len(fragmentos)} fragmento(s). "
                                  "No se escribió nada (--dry-run).")
                return

            try:
                vectores = self._vectorizar(fragmentos)
            except embeddings.EmbeddingError as error:
                raise CommandError(
                    f"El proveedor de embeddings no respondió: {error}. "
                    "No se modificó el índice.",
                ) from error

            creados, actualizados, borrados = self._guardar(
                organization, fragmentos, vectores, proveedor,
                options["source_types"],
            )

        self.stdout.write(self.style.SUCCESS(
            f"  {creados} nuevo(s), {actualizados} actualizado(s), "
            f"{borrados} borrado(s).",
        ))

    def _vectorizar(self, fragmentos):
        vectores = []
        for inicio in range(0, len(fragmentos), LOTE):
            lote = fragmentos[inicio:inicio + LOTE]
            vectores += embeddings.embed_many([f["content"] for f in lote])
        return vectores

    def _guardar(self, organization, fragmentos, vectores, proveedor,
                 source_types):
        """Escribe el índice. Todo dentro de una transacción.

        Si el guardado se interrumpiera a mitad, el asistente quedaría
        respondiendo con medio catálogo indexado y el otro medio no — y
        contestando «no tengo esa información» sobre cosas que sí están, que es
        indistinguible de un problema de calidad del corpus.
        """
        creados = actualizados = 0
        vistos = []

        with transaction.atomic():
            for fragmento, vector in zip(fragmentos, vectores):
                objeto, creado = KnowledgeChunk.objects.update_or_create(
                    organization=organization,
                    source_type=fragmento["source_type"],
                    source_id=fragmento["source_id"],
                    title=fragmento["title"],
                    defaults={
                        "content": fragmento["content"],
                        "embedding": vector,
                        "provider": proveedor,
                    },
                )
                vistos.append(objeto.id)
                creados += int(creado)
                actualizados += int(not creado)

            # Lo que ya no está en el catálogo se va. Se acota a los tipos que
            # esta corrida indexó: con `--only specialty` no se pueden borrar
            # las sucursales, que esta corrida ni miró.
            obsoletos = KnowledgeChunk.objects.filter(
                organization=organization,
            ).exclude(id__in=vistos)
            if source_types:
                obsoletos = obsoletos.filter(source_type__in=source_types)
            borrados, _ = obsoletos.delete()

        return creados, actualizados, borrados
