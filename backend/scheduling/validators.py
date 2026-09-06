"""Las tres validaciones que definen US-13: solapamiento, horario de la
sucursal y vigencia.

Devuelven `None` si todo está bien y lanzan `ValidationError` con un `code`
propio si no. El serializer las traduce a la respuesta con `code` que esperan
el frontend web y la app móvil.
"""

import datetime as dt

from django.core.exceptions import ValidationError

from catalog.models import BranchHours

from .models import Schedule


def _times_overlap(a_start, a_end, b_start, b_end) -> bool:
    return a_start < b_end and b_start < a_end


def _dates_overlap(a_from, a_until, b_from, b_until) -> bool:
    a_until = a_until or dt.date.max
    b_until = b_until or dt.date.max
    return a_from <= b_until and b_from <= a_until


def validate_no_overlap(
    *,
    organization,
    practitioner_id,
    weekday,
    start_time,
    end_time,
    valid_from,
    valid_until,
    exclude_id=None,
):
    """US-13 c — un profesional no puede tener dos agendas que se pisen el
    mismo día y hora, **ni siquiera en sucursales distintas**: no puede estar
    en dos sedes a la vez."""
    queryset = Schedule.objects.filter(
        organization=organization,
        practitioner_id=practitioner_id,
        weekday=weekday,
        is_active=True,
    )
    if exclude_id:
        queryset = queryset.exclude(pk=exclude_id)

    for other in queryset:
        if _times_overlap(
            start_time, end_time, other.start_time, other.end_time,
        ) and _dates_overlap(
            valid_from, valid_until, other.valid_from, other.valid_until,
        ):
            raise ValidationError(
                "El profesional ya tiene una agenda que se solapa con esta "
                f"({other.start_time:%H:%M}–{other.end_time:%H:%M}).",
                code="agenda_solapada",
            )


def validate_within_branch_hours(
    *, organization, branch_id, weekday, start_time, end_time,
):
    """US-13 d — la agenda no puede extenderse fuera del horario de atención
    de la sucursal ese día. Si la sucursal no tiene horario cargado, no se
    valida: no se asume que esté cerrada."""
    franjas = list(
        BranchHours.objects.filter(
            organization=organization, branch_id=branch_id, weekday=weekday,
        )
    )
    if not franjas:
        return
    for franja in franjas:
        if franja.opens_at <= start_time and end_time <= franja.closes_at:
            return
    raise ValidationError(
        "La agenda queda fuera del horario de atención de la sucursal ese día.",
        code="fuera_de_horario",
    )
