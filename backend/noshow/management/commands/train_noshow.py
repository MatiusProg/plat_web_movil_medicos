"""US-35 — Entrena el modelo de inasistencia de una o de todas las organizaciones.

    python manage.py train_noshow --organization sangabriel
    python manage.py train_noshow --all

Sólo entrena a las organizaciones **activas cuyo plan incluye la predicción**
(``noshow_prediction``, Premium): a las demás las saltea y lo dice. Cada una se
entrena con **sus propias fichas**, dentro de su ``tenant_context``.

La primera versión que le gana a la línea base queda vigente. Si ya hay una
vigente, la nueva queda como *candidata*: reemplazarla es de US-38
(``retrain_noshow``).

Después de entrenar, ``score_noshow`` (o su proceso de fondo) puntúa las fichas
futuras. Con datos recién sembrados con ``seed_dataset --history``, el orden es:

    python manage.py train_noshow --organization <slug>
    python manage.py score_noshow
"""

from django.core.management.base import BaseCommand, CommandError

from tenancy.context import platform_admin_context
from tenancy.models import Organization

from ... import scoring, training


class Command(BaseCommand):
    help = "Entrena el modelo de riesgo de inasistencia de cada organización."

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization", action="append", metavar="SLUG",
            help="Entrenar sólo esta organización (repetible).",
        )
        parser.add_argument(
            "--all", action="store_true",
            help="Entrenar a todas las organizaciones activas con el plan que lo incluye.",
        )

    def handle(self, *args, **opciones):
        slugs = opciones["organization"]
        if not slugs and not opciones["all"]:
            raise CommandError("Indicá --organization SLUG o --all.")

        if slugs:
            with platform_admin_context():
                existentes = set(
                    Organization.objects.filter(slug__in=slugs).values_list("slug", flat=True)
                )
            for slug in slugs:
                if slug not in existentes:
                    raise CommandError(f"No existe la organización «{slug}».")

        habilitadas = scoring.eligible_organizations(slugs)
        habilitadas_slugs = {o.slug for o in habilitadas}
        for slug in slugs or []:
            if slug not in habilitadas_slugs:
                self.stdout.write(self.style.WARNING(
                    f"{slug}: su plan no incluye la predicción de inasistencia, se saltea."))

        for organizacion in habilitadas:
            try:
                resultado = training.train_for(organizacion)
            except Exception as error:  # noqa: BLE001 - una organización no frena al resto
                self.stderr.write(self.style.ERROR(f"{organizacion.slug}: falló ({error})."))
                continue
            estilo = self.style.SUCCESS if resultado.version else self.style.WARNING
            self.stdout.write(estilo(f"{organizacion.slug}: {resultado.message}"))
