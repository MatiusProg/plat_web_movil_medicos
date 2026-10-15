"""US-28 — Los recordatorios de fichas, desde la consola o como proceso de fondo.

    python manage.py send_appointment_reminders            una vuelta y termina
    python manage.py send_appointment_reminders --loop     una vuelta cada 15 minutos, siempre

Una vuelta avisa —push y correo— de las fichas confirmadas que empiezan dentro
de las próximas `APPOINTMENT_REMINDER_HOURS` horas (ver
``appointments/reminders.py``). Es idempotente: correrla de más no repite
ningún recordatorio.

**En producción corre con ``--loop`` junto a gunicorn**, lanzado por
``scripts/start.sh``, igual que ``run_automatic_backups``. Se apaga con
``APPOINTMENT_REMINDERS=off``.
"""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from ... import reminders

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Manda los recordatorios de las fichas que empiezan pronto."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true",
            help="Repetir para siempre, con la pausa de --every.",
        )
        parser.add_argument(
            "--every", type=int, default=15,
            help="Minutos entre vueltas con --loop. Por omisión, 15.",
        )

    def handle(self, *args, **options):
        if str(settings.APPOINTMENT_REMINDERS).lower() in ("off", "0", "false"):
            self.stdout.write("Recordatorios apagados (APPOINTMENT_REMINDERS=off).")
            return

        if not options["loop"]:
            self._vuelta()
            return

        pausa = max(options["every"], 1) * 60
        self.stdout.write(
            f"Recordatorios de fichas: una vuelta cada {options['every']} minuto(s).",
        )
        while True:
            try:
                self._vuelta()
            except Exception:  # noqa: BLE001 - el proceso no se puede morir
                # Una vuelta que falla entera —la base caída, por ejemplo— no
                # puede terminar el proceso: nadie lo volvería a levantar
                # hasta el próximo despliegue.
                logger.exception("Falló una vuelta de recordatorios.")
            finally:
                # Una conexión que la base cerró durante la pausa haría fallar
                # la vuelta siguiente.
                close_old_connections()
            time.sleep(pausa)

    def _vuelta(self):
        avisadas = reminders.run_due()
        self.stdout.write(self.style.SUCCESS(
            f"Recordatorios de fichas: {avisadas} enviado(s).",
        ))
