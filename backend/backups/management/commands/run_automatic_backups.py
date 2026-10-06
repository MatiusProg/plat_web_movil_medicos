"""Las copias automáticas, desde la consola o como proceso de fondo.

    python manage.py run_automatic_backups            una vuelta y termina
    python manage.py run_automatic_backups --loop     una vuelta cada hora, siempre

Una vuelta respalda a las organizaciones activas a las que les toca según su
plan (ver ``backups/automatic.py``). Es idempotente: correrla de más no
duplica nada.

**En producción corre con ``--loop`` junto a gunicorn**, lanzado por
``scripts/start.sh``. Se eligió así y no un servicio cron de Railway porque
no exige configurar nada en el panel: el despliegue que sube el código ya deja
las copias andando. Si algún día se pasa a un cron aparte, se pone
``AUTOMATIC_BACKUPS=off`` en el servicio web y el cron corre este comando sin
``--loop``.
"""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from ... import automatic

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Genera las copias automáticas que correspondan según el plan."

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
        if str(settings.AUTOMATIC_BACKUPS).lower() in ("off", "0", "false"):
            self.stdout.write("Copias automáticas apagadas (AUTOMATIC_BACKUPS=off).")
            return

        if not options["loop"]:
            self._vuelta()
            return

        pausa = max(options["every"], 1) * 60
        self.stdout.write(
            f"Copias automáticas: una vuelta cada {options['every']} minuto(s).",
        )
        while True:
            try:
                self._vuelta()
            except Exception:  # noqa: BLE001 - el proceso no se puede morir
                # Una vuelta que falla entera —la base caída, por ejemplo— no
                # puede terminar el proceso: nadie lo volvería a levantar
                # hasta el próximo despliegue.
                logger.exception("Falló una vuelta de copias automáticas.")
            finally:
                # Una conexión que la base cerró durante la pausa haría fallar
                # la vuelta siguiente.
                close_old_connections()
            time.sleep(pausa)

    def _vuelta(self):
        hechas = automatic.run_due()
        for record in hechas:
            self.stdout.write(
                f"  {record.filename}  ·  {record.size_bytes / 1024:.0f} KB",
            )
        self.stdout.write(self.style.SUCCESS(
            f"Copias automáticas: {len(hechas)} generada(s).",
        ))
