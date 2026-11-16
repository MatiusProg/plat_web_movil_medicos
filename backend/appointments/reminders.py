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

**US-36 — el recordatorio reforzado.** En la misma vuelta, y con la misma
técnica, las fichas que US-35 calificó con riesgo **alto** reciben un segundo
aviso, más cerca de la hora (`APPOINTMENT_REINFORCED_REMINDER_HOURS`, 3 por
omisión). Tres reglas más:

- **Se lee la predicción, no se calcula.** Sin predicción vigente para la
  ficha —sin modelo, sin plan que lo incluya, ficha sin calificar— no hay
  refuerzo.
- **Marca propia**, `reinforced_reminder_sent_at`, puesta en la misma
  transacción que el envío. Es independiente de `reminder_sent_at`: una ficha
  puede recibir los dos avisos.
- **Tampoco se refuerza lo que se acaba de confirmar**, por la misma razón que
  el primero.
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


def due_reinforced(now=None):
    """Las fichas con riesgo alto a las que les toca el segundo recordatorio.

    Supone el contexto fijado. Lee `NoShowPrediction` (US-35); sólo cuenta la
    de un modelo vigente: sin modelo vigente no hay refuerzo.
    """
    now = now or timezone.now()
    ventana = dt.timedelta(hours=settings.APPOINTMENT_REINFORCED_REMINDER_HOURS)
    return Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        reinforced_reminder_sent_at__isnull=True,
        starts_at__gt=now,
        starts_at__lte=now + ventana,
        created_at__lte=F("starts_at") - ventana,
        noshow_prediction__level="high",
        noshow_prediction__model_version__status="active",
    )


def _enviar(organization, consulta, evento, campo, now=None) -> int:
    """Avisa de [evento] las fichas de [consulta] y marca [campo]. Devuelve cuántas."""
    from notifications.services import notify

    with tenant_context(organization.id):
        pendientes = list(consulta(now).values_list("pk", flat=True))

    avisadas = 0
    for pk in pendientes:
        # Una transacción por ficha: si una falla, las ya avisadas quedan
        # marcadas y no se repiten en la vuelta siguiente.
        with tenant_context(organization.id):
            # `of=("self",)`: sólo se bloquea la ficha, no la fila de la
            # predicción que la consulta del refuerzo une.
            ficha = (
                consulta(now).select_for_update(skip_locked=True, of=("self",))
                .filter(pk=pk).first()
            )
            if ficha is None:
                # La tomó otro proceso, o dejó de corresponder (se canceló).
                continue
            notify(evento, ficha.id, organization.id)
            setattr(ficha, campo, timezone.now())
            ficha.save(update_fields=[campo, "updated_at"])
            avisadas += 1
    return avisadas


def run_for(organization, now=None) -> int:
    """Recuerda las fichas de una organización. Devuelve cuántas avisó."""
    from notifications.services import REMINDER

    return _enviar(organization, due, REMINDER, "reminder_sent_at", now)


def run_reinforced_for(organization, now=None) -> int:
    """Manda el segundo recordatorio a las fichas con riesgo alto. Devuelve cuántas.

    Sólo si el plan de la organización incluye la predicción: la predicción de
    una organización que bajó de plan sigue guardada, pero ya no se usa.
    """
    from noshow.scoring import has_feature
    from notifications.services import REINFORCED_REMINDER

    if not has_feature(organization):
        return 0
    return _enviar(organization, due_reinforced, REINFORCED_REMINDER,
                   "reinforced_reminder_sent_at", now)


def _organizaciones_activas():
    with platform_admin_context():
        return list(
            Organization.objects.filter(status=Organization.Status.ACTIVE)
        )


def _por_organizacion(funcion, mensaje, now=None) -> int:
    """Corre [funcion] en cada organización activa; una que falla no frena al resto."""
    total = 0
    for organization in _organizaciones_activas():
        try:
            total += funcion(organization, now)
        except Exception:  # noqa: BLE001 - una organización no frena al resto
            logger.exception(mensaje, organization.slug)
    return total


def run_cycle(now=None) -> tuple[int, int]:
    """Una vuelta: `(recordatorios, reforzados)` enviados en todas las organizaciones.

    Una organización que falla no frena a las demás: se anota y se sigue. Sus
    fichas siguen sin marcar, así que la vuelta siguiente las vuelve a intentar.
    El refuerzo corre aparte: que falle uno no impide el otro.
    """
    normales = _por_organizacion(
        run_for, "Fallaron los recordatorios de «%s».", now)
    reforzados = _por_organizacion(
        run_reinforced_for, "Fallaron los recordatorios reforzados de «%s».", now)
    return normales, reforzados


def run_due(now=None) -> int:
    """Recuerda las fichas de todas las organizaciones activas. Devuelve el total."""
    return sum(run_cycle(now))
