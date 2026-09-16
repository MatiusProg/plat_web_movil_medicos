"""US-31 — Indexa el catálogo de una organización para el asistente.

    python manage.py embed_catalog --organization morita2
    python manage.py embed_catalog --all
    python manage.py embed_catalog --organization morita2 --dry-run

Es el paso que convierte el catálogo en algo recuperable: parte las
descripciones en fragmentos, los vectoriza y los guarda. Sin correrlo,
``/api/assistant/suggest/`` contesta correctamente que no sabe nada, porque
efectivamente no hay nada indexado.

**Es idempotente y se puede correr cuantas veces haga falta.** Cada corrida
borra los fragmentos de las especialidades de esa organización y los reescribe
(ver ``indexing.py``), así que reindexar después de editar el catálogo es
volver a correr esto y nada más.

**Hay que reindexar cuando cambia el texto del catálogo, y también cuando
cambia el proveedor de embeddings.** Lo segundo es menos evidente y peor: un
índice con vectores de dos modelos distintos no da error, da distancias que no
significan nada. Por eso el comando avisa si en la tabla ya hay fragmentos
calculados con otro modelo.
"""

from django.core.management.base import BaseCommand, CommandError

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ...embeddings import EmbeddingError, active_model_name
from ...indexing import index_specialties, split_into_fragments
from ...models import CatalogFragment, SourceType


class Command(BaseCommand):
    help = "Vectoriza el catálogo de una organización para el asistente (US-31)."

    def add_arguments(self, parser):
        grupo = parser.add_mutually_exclusive_group(required=True)
        grupo.add_argument(
            "--organization",
            help="Slug de la organización a indexar (por ejemplo: morita2).",
        )
        grupo.add_argument(
            "--all", action="store_true",
            help="Indexa todas las organizaciones, una por una y cada una en "
                 "su propio contexto.",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Muestra los fragmentos que se generarían y no llama al "
                 "proveedor ni escribe nada. Sirve para revisar el corpus.",
        )

    def handle(self, *args, **opciones):
        # `organizations` está bajo RLS: sin contexto de plataforma la
        # búsqueda devuelve cero filas y el comando se queja de que el slug no
        # existe cuando en realidad existe.
        with platform_admin_context():
            if opciones["all"]:
                organizaciones = list(Organization.objects.order_by("slug"))
            else:
                slug = opciones["organization"]
                organizaciones = list(Organization.objects.filter(slug=slug))
                if not organizaciones:
                    disponibles = list(
                        Organization.objects.values_list("slug", flat=True)
                    )
                    raise CommandError(
                        f"No existe una organización con slug «{slug}». "
                        f"Las que hay son: "
                        f"{', '.join(disponibles) or '(ninguna)'}."
                    )

        if not organizaciones:
            raise CommandError("No hay ninguna organización dada de alta.")

        modelo = active_model_name()
        self.stdout.write(f"Proveedor de embeddings: {self.style.MIGRATE_LABEL(modelo)}")

        for organizacion in organizaciones:
            self.stdout.write("")
            self.stdout.write(f"{organizacion.name} ({organizacion.slug})")

            # Regla 4 del reparto: fuera del ciclo HTTP, todo va envuelto.
            with tenant_context(organizacion.id):
                if opciones["dry_run"]:
                    self._dry_run(organizacion)
                else:
                    self._indexar(organizacion, modelo)

    # ----------------------------------------------------------------------

    def _dry_run(self, organizacion):
        from catalog.models import Specialty

        total = 0
        for especialidad in Specialty.objects.filter(
            organization=organizacion, is_active=True,
        ).order_by("name"):
            fragmentos = split_into_fragments(
                especialidad.name, especialidad.description,
            )
            total += len(fragmentos)
            self.stdout.write(f"  {especialidad.name} → {len(fragmentos)} fragmentos")
            for texto in fragmentos:
                self.stdout.write(f"      · {texto}")
        self.stdout.write(f"  (sin escribir) {total} fragmentos en total")

    def _indexar(self, organizacion, modelo):
        self._avisar_si_hay_otro_modelo(organizacion, modelo)

        try:
            resumen = index_specialties(organizacion, stdout=self.stdout)
        except EmbeddingError as error:
            raise CommandError(str(error)) from error

        if resumen["fragments"] == 0:
            self.stdout.write(self.style.WARNING(
                "  No hay especialidades activas: no se indexó nada. "
                "¿Corriste `seed_catalog` en esta organización?"
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"  {resumen['fragments']} fragmentos de "
            f"{resumen['specialties']} especialidades, con {resumen['model']}"
        ))
        if resumen["empty"]:
            self.stdout.write(self.style.WARNING(
                "  Sin descripción, y por lo tanto casi imposibles de "
                "recuperar: " + ", ".join(resumen["empty"])
            ))

    def _avisar_si_hay_otro_modelo(self, organizacion, modelo):
        otros = set(
            CatalogFragment.objects
            .filter(organization=organizacion)
            .exclude(embedding_model=modelo)
            .exclude(source_type=SourceType.SPECIALTY)
            .values_list("embedding_model", flat=True)
        )
        if otros:
            self.stdout.write(self.style.WARNING(
                f"  Ojo: quedan fragmentos de otras fuentes calculados con "
                f"{', '.join(sorted(otros))}. Mezclar modelos en el mismo "
                f"índice da distancias que no significan nada: reindexá todo "
                f"con --all."
            ))
