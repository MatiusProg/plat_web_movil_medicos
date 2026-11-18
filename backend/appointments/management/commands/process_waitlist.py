"""US-52 — El proceso de la lista de espera, desde la consola o de fondo.

    python manage.py process_waitlist            una vuelta y termina
    python manage.py process_waitlist --loop     una vuelta por minuto, siempre

Una vuelta, por cada organización cuyo plan incluye la lista de espera:

1. Marca `expired` las reservas pendientes que vencieron y dejan libre su
   turno (`appointments/holds.py`).
2. Le ofrece cada turno que quedó libre al siguiente de la fila
   (`appointments/waitlist.py`) y le avisa.
3. Pone al día las entradas: las que pagaron, las que vencieron.

Sin este proceso, el segundo de la fila sólo avanzaría cuando alguien tocara
el turno. Es idempotente: correrla de más no ofrece nada dos veces.

**En producción corre con ``--loop`` junto a gunicorn**, lanzado por
``scripts/start.sh``. Se apaga con ``WAITLIST_PROCESS=off``.
"""

import logging
import time

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import close_old_connections

from ... import waitlist

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Libera reservas vencidas y ofrece los turnos a la lista de espera."

    def add_arguments(self, parser):
        parser.add_argument(
            "--loop", action="store_true",
            help="Repetir para siempre, con la pausa de --every.",
        )
        parser.add_argument(
            "--every", type=int, default=1,
            help="Minutos entre vueltas con --loop. Por omisión, 1.",
        )

    def handle(self, *args, **options):
        if str(settings.WAITLIST_PROCESS).lower() in ("off", "0", "false"):
            self.stdout.write("Lista de espera apagada (WAITLIST_PROCESS=off).")
            return

        if not options["loop"]:
            self._vuelta()
            return

        pausa = max(options["every"], 1) * 60
        self.stdout.write(
            f"Lista de espera: una vuelta cada {options['every']} minuto(s).",
        )
        while True:
            try:
                self._vuelta()
            except Exception:  # noqa: BLE001 - el proceso no se puede morir
                # Una vuelta que falla entera —la base caída, por ejemplo— no
                # puede terminar el proceso: nadie lo volvería a levantar hasta
                # el próximo despliegue.
                logger.exception("Falló una vuelta de la lista de espera.")
            finally:
                # Una conexión que la base cerró durante la pausa haría fallar
                # la vuelta siguiente.
                close_old_connections()
            time.sleep(pausa)

    def _vuelta(self):
        resultado = waitlist.run_due()
        self.stdout.write(self.style.SUCCESS(
            f"Lista de espera: {resultado['liberadas']} reserva(s) vencida(s) "
            f"liberada(s), {resultado['ofrecidas']} turno(s) ofrecido(s).",
        ))
