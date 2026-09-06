"""US-15 — Disponibilidad consolidada de un profesional entre sus sucursales.

El espacio libre se calcula restando, a lo que deriva de la agenda (US-13),
los bloqueos (US-14) y las fichas ya reservadas. En el Sprint 1 todavía no hay
tabla de fichas: `_booked_slots` devuelve un conjunto vacío y marca el punto
donde el Sprint 2 lo llena.

RNF-02 (menos de 3 segundos): se resuelve en **una consulta de agendas y una
de bloqueos por rango**, no una por día. El corte de "hora ya pasada" se
calcula en la zona horaria de la sucursal, no en la del servidor.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Practitioner

from .models import Schedule, ScheduleBlock
from .permissions import CanReadSlots


def _daterange(date_from: dt.date, date_to: dt.date):
    day = date_from
    while day <= date_to:
        yield day
        day += dt.timedelta(days=1)


def slot_starts(start: dt.time, end: dt.time, step_minutes: int):
    """Las horas de inicio de cada espacio de `[start, end)`, paso a paso."""
    cursor = dt.datetime.combine(dt.date.min, start)
    limit = dt.datetime.combine(dt.date.min, end)
    step = dt.timedelta(minutes=step_minutes)
    while cursor + step <= limit:
        yield cursor.time()
        cursor += step


def _booked_slots(practitioner_id, date_from, date_to) -> set:
    """Fichas ya reservadas en el rango. El Sprint 2 lo implementa."""
    return set()


def generate_slots(schedule: Schedule, date_from: dt.date, date_to: dt.date, *, tz):
    """Los espacios que deriva una regla de agenda dentro del rango.

    Devuelve tuplas `(fecha, inicio_aware, fin_aware)` sólo para las fechas
    cuyo día de la semana coincide y que caen dentro de la vigencia.

    Nota: `America/La_Paz` no tiene horario de verano, así que combinar fecha y
    hora con la zona de la sucursal es exacto. En una zona con DST habría un
    desfase de una hora en los dos días de transición.
    """
    step = schedule.slot_minutes
    for day in _daterange(date_from, date_to):
        if day.weekday() != schedule.weekday:
            continue
        if day < schedule.valid_from:
            continue
        if schedule.valid_until and day > schedule.valid_until:
            continue
        for start in slot_starts(schedule.start_time, schedule.end_time, step):
            start_aware = dt.datetime.combine(day, start, tzinfo=tz)
            end_aware = start_aware + dt.timedelta(minutes=step)
            yield day, start_aware, end_aware


def _blocked(start_aware, end_aware, blocks) -> bool:
    for block in blocks:
        if start_aware < block.ends_at and end_aware > block.starts_at:
            return True
    return False


def consolidated_availability(
    *,
    practitioner_id,
    date_from: dt.date,
    date_to: dt.date,
    branch_id=None,
    now=None,
) -> dict:
    """La disponibilidad del profesional agrupada por día.

    Lanza `django.core.exceptions.ValidationError` si el rango está invertido,
    supera el horizonte configurable o el profesional no existe.
    """
    if date_to < date_from:
        raise ValidationError("El rango de fechas está invertido.")

    horizon = settings.AVAILABILITY_MAX_HORIZON_DAYS
    if (date_to - date_from).days > horizon:
        raise ValidationError(
            f"No se puede pedir más de {horizon} días de disponibilidad."
        )

    practitioner = Practitioner.objects.filter(pk=practitioner_id).first()
    if practitioner is None:
        raise ValidationError("El profesional no existe.")

    now = now or timezone.now()

    schedule_qs = (
        Schedule.objects.filter(
            practitioner_id=practitioner_id,
            is_active=True,
            valid_from__lte=date_to,
        )
        .filter(Q(valid_until__isnull=True) | Q(valid_until__gte=date_from))
        .select_related("branch")
    )
    if branch_id:
        schedule_qs = schedule_qs.filter(branch_id=branch_id)
    schedules = list(schedule_qs)

    # Ventana en UTC con un día de margen a cada lado, para no perder un
    # bloqueo que en la zona de la sucursal cae dentro del rango pero en UTC
    # queda justo afuera.
    range_start = (
        dt.datetime.combine(date_from, dt.time.min, tzinfo=dt.timezone.utc)
        - dt.timedelta(days=1)
    )
    range_end = (
        dt.datetime.combine(date_to, dt.time.max, tzinfo=dt.timezone.utc)
        + dt.timedelta(days=1)
    )
    blocks = list(
        ScheduleBlock.objects.filter(
            is_active=True,
            starts_at__lt=range_end,
            ends_at__gt=range_start,
        ).filter(
            Q(practitioner_id=practitioner_id) | Q(practitioner__isnull=True)
        )
    )

    booked = _booked_slots(practitioner_id, date_from, date_to)

    by_day: dict[dt.date, list] = defaultdict(list)
    for schedule in schedules:
        branch = schedule.branch
        tz = ZoneInfo(branch.timezone or "America/La_Paz")
        reservable = practitioner.is_active and branch.is_active
        reason = None
        if not practitioner.is_active:
            reason = "profesional_inactivo"
        elif not branch.is_active:
            reason = "sucursal_inactiva"

        for day, start_aware, end_aware in generate_slots(
            schedule, date_from, date_to, tz=tz,
        ):
            if start_aware <= now:  # US-15 e: ya pasó, en la zona de la sede
                continue
            if _blocked(start_aware, end_aware, blocks):
                continue
            if (schedule.id, start_aware) in booked:
                continue
            by_day[day].append({
                "start": start_aware.isoformat(),
                "end": end_aware.isoformat(),
                "branch": {"id": str(branch.id), "name": branch.name},
                "capacity": schedule.capacity,
                "reservable": reservable,
                "reason": reason,
            })

    days = []
    for day in sorted(by_day):
        slots = sorted(by_day[day], key=lambda slot: slot["start"])
        days.append({"date": day.isoformat(), "slots": slots})

    return {
        "practitioner": {
            "id": str(practitioner.id),
            "full_name": practitioner.full_name,
            "is_active": practitioner.is_active,
        },
        "range": {"from": date_from.isoformat(), "to": date_to.isoformat()},
        "days": days,
    }


def next_available_slot(practitioner_id, *, now=None, horizon_days=14):
    """El primer espacio reservable futuro. Lo usa la tarjeta de US-16.

    Devuelve el `start` en ISO 8601, o `None` si no hay nada en el horizonte.
    """
    now = now or timezone.now()
    today = now.astimezone(dt.timezone.utc).date()
    data = consolidated_availability(
        practitioner_id=practitioner_id,
        date_from=today,
        date_to=today + dt.timedelta(days=horizon_days),
        now=now,
    )
    for day in data["days"]:
        for slot in day["slots"]:
            if slot["reservable"]:
                return slot["start"]
    return None


def _parse_date(value):
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


class AvailabilityView(APIView):
    """`GET /api/scheduling/availability/?practitioner=&from=&to=&branch=`

    El contrato que consumen US-16 y la reserva del Sprint 2. Respuesta
    agrupada por día (US-15 f).
    """

    permission_classes = [IsAuthenticated, CanReadSlots]

    def get(self, request):
        practitioner_id = request.query_params.get("practitioner")
        date_from = _parse_date(request.query_params.get("from"))
        date_to = _parse_date(request.query_params.get("to"))
        branch_id = request.query_params.get("branch") or None

        if not practitioner_id or date_from is None or date_to is None:
            return Response(
                {"detail": "Hacen falta practitioner, from y to (fechas ISO)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = consolidated_availability(
                practitioner_id=practitioner_id,
                date_from=date_from,
                date_to=date_to,
                branch_id=branch_id,
            )
        except ValidationError as error:
            return Response(
                {"detail": error.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(data)
