"""US-28 — El recordatorio previo a la ficha.

Un proceso de fondo (`send_appointment_reminders --loop`, lanzado por
`scripts/start.sh` junto a las copias automáticas) da una vuelta cada 15
minutos y avisa —push y correo— de las fichas confirmadas que empiezan dentro
de las próximas `APPOINTMENT_REMINDER_HOURS` horas (24 por omisión).

Cuatro decisiones:

- **Una organización a la vez, cada una en su `tenant_context`.** Fuera de una
  petición no hay contexto, y sin él RLS no devuelve ninguna ficha.
- **Nunca dos veces.** Cada ficha se toma con
  `select_for_update(skip_locked=True)` y se marca `reminder_sent_at` en la
  misma transacción que la avisa: si el proceso se reinicia, o el contenedor
  viejo y el nuevo conviven durante un despliegue, la segunda vuelta ya no la
  encuentra.
- **No se recuerda lo que se acaba de confirmar.** Una ficha reservada cuando
  ya faltaban menos de 24 horas recibió el aviso de confirmación hace un
  momento: recordársela sería repetirlo. Sólo se recuerdan las reservadas
  antes de que empezara la ventana.
- **Se marca aunque el envío falle.** Un correo que rebota o un paciente sin
  teléfono registrado fallarían en cada vuelta, para siempre.
"""

from __future__ import annotations

import datetime as dt
import logging

from django.conf import settings
from django.db.models import F
from django.utils import timezone

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from .models import Appointment

logger = logging.getLogger(__name__)


def due(now=None):
    """Las fichas a las que les toca el recordatorio. Supone el contexto fijado."""
    now = now or timezone.now()
    ventana = dt.timedelta(hours=settings.APPOINTMENT_REMINDER_HOURS)
    return Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        reminder_sent_at__isnull=True,
        starts_at__gt=now,
        starts_at__lte=now + ventana,
        created_at__lte=F("starts_at") - ventana,
    )


def run_for(organization, now=None) -> int:
    """Recuerda las fichas de una organización. Devuelve cuántas avisó."""
    from notifications.services import REMINDER, notify

    with tenant_context(organization.id):
        pendientes = list(due(now).values_list("pk", flat=True))

    avisadas = 0
    for pk in pendientes:
        # Una transacción por ficha: si una falla, las ya avisadas quedan
        # marcadas y no se repiten en la vuelta siguiente.
        with tenant_context(organization.id):
            ficha = (
                due(now).select_for_update(skip_locked=True)
                .filter(pk=pk).first()
            )
            if ficha is None:
                # La tomó otro proceso, o dejó de corresponder (se canceló).
                continue
            notify(REMINDER, ficha.id, organization.id)
            ficha.reminder_sent_at = timezone.now()
            ficha.save(update_fields=["reminder_sent_at", "updated_at"])
            avisadas += 1
    return avisadas


def run_due(now=None) -> int:
    """Recuerda las fichas de todas las organizaciones activas.

    Una que falla no frena a las demás: se anota y se sigue. Sus fichas
    siguen sin marcar, así que la vuelta siguiente las vuelve a intentar.
    """
    with platform_admin_context():
        organizaciones = list(
            Organization.objects.filter(status=Organization.Status.ACTIVE)
        )

    total = 0
    for organization in organizaciones:
        try:
            total += run_for(organization, now)
        except Exception:  # noqa: BLE001 - una organización no frena al resto
            logger.exception("Fallaron los recordatorios de «%s».",
                             organization.slug)
    return total
