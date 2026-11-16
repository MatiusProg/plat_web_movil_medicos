"""US-35 — Recalcula el riesgo de inasistencia de las fichas futuras.

    python manage.py score_noshow            una vuelta y termina
    python manage.py score_noshow --loop     una vuelta cada hora, siempre

Puntúa, organización por organización y con su modelo vigente, las fichas que
empiezan dentro de los próximos 60 días (ver ``noshow/scoring.py``). Es
idempotente: correrlo de más sólo actualiza la misma fila de cada ficha.

**En producción corre con ``--loop`` junto a gunicorn**, lanzado por
``scripts/start.sh``, igual que los recordatorios de fichas. Se apaga con
``NOSHOW_SCORING=off``.
"""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from ... import scoring

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Calcula el riesgo de inasistencia de las fichas futuras."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true",
            help="Repetir para siempre, con la pausa de --every.",
        )
        parser.add_argument(
            "--every", type=int, default=60,
            help="Minutos entre vueltas con --loop. Por omisión, 60.",
        )

    def handle(self, *args, **options):
        if str(settings.NOSHOW_SCORING).lower() in ("off", "0", "false"):
            self.stdout.write("Predicción de inasistencia apagada (NOSHOW_SCORING=off).")
            return

        if not options["loop"]:
            self._vuelta()
            return

        pausa = max(options["every"], 1) * 60
        self.stdout.write(
            f"Predicción de inasistencia: una vuelta cada {options['every']} minuto(s).",
        )
        while True:
            try:
                self._vuelta()
            except Exception:  # noqa: BLE001 - el proceso no se puede morir
                # Una vuelta que falla entera —la base caída, por ejemplo— no
                # puede terminar el proceso: nadie lo volvería a levantar hasta
                # el próximo despliegue.
                logger.exception("Falló una vuelta de la predicción de inasistencia.")
            finally:
                # Una conexión que la base cerró durante la pausa haría fallar
                # la vuelta siguiente.
                close_old_connections()
            time.sleep(pausa)

    def _vuelta(self):
        puntuadas = scoring.run_due()
        self.stdout.write(self.style.SUCCESS(
            f"Predicción de inasistencia: {puntuadas} ficha(s) calificada(s).",
        ))
