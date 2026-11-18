"""US-52 — Las reservas pendientes que vencieron dejan libre el turno.

Una ficha nace `pending_payment` con `expires_at` a `APPOINTMENT_HOLD_MINUTES`
minutos (ver `booking.py`). Hasta US-52 nada marcaba como `expired` a la que
nadie pagó, y como `scheduling.availability._booked_slots` y el índice único
`uq_appointment_active_slot` cuentan `pending_payment` sin mirar el
vencimiento, **una reserva abandonada ocupaba el turno para siempre**.

La lista de espera (`waitlist.py`) guarda el turno liberado 15 minutos con
una de estas reservas y, si el paciente no la paga, tiene que pasárselo al
siguiente: sin esto no pasaba nunca.

Se libera en tres lugares, de más a menos urgente:

- `book_appointment`, justo antes de insertar: el turno que se quiere tomar
  deja de estar bloqueado por una reserva muerta.
- `scheduling.availability._booked_slots`: la búsqueda ya no los cuenta.
- `manage.py process_waitlist`: una vuelta por minuto marca el resto, para que
  los listados y la lista de espera vean el estado real.

Un pago que llegue tarde sobre una ficha `expired` se devuelve solo
(`payments.services.confirm_payment`, motivo `ficha_no_disponible`).

**El turno que se le guardó a alguien de la lista de espera tiene un margen.**
Cuando esa reserva vence, el turno le toca al *siguiente de la fila*, y ofrecérselo
es trabajo de `process_waitlist`. Si la búsqueda y `book_appointment` lo
soltaran en el mismo segundo, cualquiera que reservara antes de la próxima
vuelta —hasta un minuto— se lo llevaría saltándose la fila. Por eso esas
reservas, y sólo ellas, siguen bloqueando `GRACE_MINUTES` minutos más allá de
su vencimiento para quien llega por la búsqueda; el proceso las libera sin
margen (`include_offers=True`) y se las ofrece al siguiente en la misma vuelta.
Si el proceso estuviera apagado, el margen termina y el turno se libera igual.
"""

from __future__ import annotations

import datetime as dt

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from .models import Appointment, WaitlistEntry

# Cuánto sigue bloqueando, para la búsqueda y la reserva, una reserva vencida
# que era la oferta de la lista de espera. Pasado esto el turno se libera aunque
# `process_waitlist` no haya corrido.
GRACE_MINUTES = 3


def _es_oferta():
    """Subconsulta: la ficha es el turno que se le guardó a alguien de la lista."""
    return Exists(WaitlistEntry.objects.filter(
        offered_appointment_id=OuterRef("pk"),
        status=WaitlistEntry.Status.OFFERED,
    ))


def blocking_q(now=None) -> Q:
    """Las fichas que ocupan su turno ahora mismo, para la búsqueda: las
    confirmadas, las pendientes vigentes y las ofertas de la lista de espera
    dentro de su margen. Ver el encabezado del módulo."""
    now = now or timezone.now()
    return Q(status=Appointment.Status.CONFIRMED) | (
        Q(status=Appointment.Status.PENDING_PAYMENT)
        & (Q(expires_at__isnull=True) | Q(expires_at__gt=now)
           | (Q(_es_oferta())
              & Q(expires_at__gt=now - dt.timedelta(minutes=GRACE_MINUTES))))
    )


def release_expired_holds(*, now=None, schedule_id=None, starts_at=None,
                          include_offers=False):
    """Marca `expired` las `pending_payment` vencidas y devuelve cuáles eran.

    Corre dentro del contexto de una organización (RLS): sólo ve las suyas.
    Con `schedule_id` y `starts_at` se acota a un turno. Idempotente.

    Las ofertas de la lista de espera conservan su margen (`GRACE_MINUTES`)
    salvo con `include_offers=True`, que es como las libera el proceso de la
    lista, justo antes de ofrecer el turno al siguiente.
    """
    now = now or timezone.now()
    consulta = Appointment.objects.filter(
        status=Appointment.Status.PENDING_PAYMENT, expires_at__lte=now,
    )
    if not include_offers:
        consulta = consulta.exclude(
            _es_oferta(),
            expires_at__gt=now - dt.timedelta(minutes=GRACE_MINUTES),
        )
    if schedule_id is not None:
        consulta = consulta.filter(schedule_id=schedule_id)
    if starts_at is not None:
        consulta = consulta.filter(starts_at=starts_at)

    with transaction.atomic():
        vencidas = list(consulta.select_for_update())
        if vencidas:
            Appointment.objects.filter(
                pk__in=[ficha.pk for ficha in vencidas],
            ).update(status=Appointment.Status.EXPIRED, updated_at=now)
    for ficha in vencidas:
        ficha.status = Appointment.Status.EXPIRED
    return vencidas
