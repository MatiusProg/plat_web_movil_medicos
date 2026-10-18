"""US-29 — Indicadores del panel de la organización.

Las definiciones están en `docs/sprints/sprint-3/us-29-indicadores.md`. Los
filtros `debian_atenderse_q` e `inasistencia_q` son la fuente única de esos
números: los conjuntos de datos de US-30 los importan para dar lo mismo que el
panel.

Todo se cuenta en la base (`Count(filter=...)`, `Sum`, `values().annotate()`).
Lo único que se recorre en Python son las agendas (`Schedule`), que son pocas,
para saber cuántos espacios ofrecen en el rango.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Count, Q, Sum
from django.utils import timezone

from catalog.models import PractitionerSpecialty
from payments.models import Payment
from scheduling.availability import generate_slots
from scheduling.models import Schedule, ScheduleBlock

from .models import Appointment

# Estados que ocuparon un espacio de la agenda. Cancelar lo libera, reprogramar
# deja la ficha nueva, y una vencida nunca llegó a ocuparlo.
OCUPAN_ESPACIO = ["pending_payment", "confirmed", "attended", "no_show"]

# Tope del rango, para que contar espacios no se dispare.
MAX_DIAS = 366

SIN_ESPECIALIDAD = "Sin especialidad"


def debian_atenderse_q(ahora) -> Q:
    """Fichas que ya tendrían que haberse atendido: la base de la inasistencia."""
    return (
        Q(status__in=["attended", "no_show"])
        | Q(status="confirmed", ends_at__lt=ahora)
    )


def inasistencia_q(ahora) -> Q:
    """Fichas ausentes: `no_show`, o confirmada vencida que nunca hizo check-in."""
    return (
        Q(status="no_show")
        | Q(status="confirmed", ends_at__lt=ahora, checked_in_at__isnull=True)
    )


def rango_utc(organizacion, desde: dt.date, hasta: dt.date):
    """`[desde 00:00, hasta+1 00:00)` en la zona de la organización."""
    tz = ZoneInfo(organizacion.timezone or "America/La_Paz")
    inicio = dt.datetime.combine(desde, dt.time.min, tzinfo=tz)
    fin = dt.datetime.combine(hasta + dt.timedelta(days=1), dt.time.min, tzinfo=tz)
    return inicio, fin


def _tasa(parte: int, total: int):
    return round(parte / total, 4) if total else None


def _espacios_ofrecidos(organizacion, desde, hasta, branch_id) -> int:
    """Espacios que derivan las agendas activas en el rango, menos bloqueos."""
    agendas = Schedule.objects.filter(
        organization=organizacion, is_active=True,
        valid_from__lte=hasta,
    ).filter(Q(valid_until__isnull=True) | Q(valid_until__gte=desde)).select_related("branch")
    if branch_id:
        agendas = agendas.filter(branch_id=branch_id)
    agendas = list(agendas)
    if not agendas:
        return 0

    # Ventana en UTC con un día de margen a cada lado, como en la disponibilidad.
    ventana_ini = dt.datetime.combine(desde, dt.time.min, tzinfo=dt.timezone.utc) - dt.timedelta(days=1)
    ventana_fin = dt.datetime.combine(hasta, dt.time.max, tzinfo=dt.timezone.utc) + dt.timedelta(days=1)
    por_profesional = defaultdict(list)
    for bloqueo in ScheduleBlock.objects.filter(
        organization=organizacion, is_active=True,
        starts_at__lt=ventana_fin, ends_at__gt=ventana_ini,
    ):
        por_profesional[bloqueo.practitioner_id].append(bloqueo)

    total = 0
    for agenda in agendas:
        tz = ZoneInfo(agenda.branch.timezone or "America/La_Paz")
        bloqueos = [
            b
            for clave in (agenda.practitioner_id, None)
            for b in por_profesional.get(clave, ())
            if b.branch_id in (None, agenda.branch_id)
        ]
        for _dia, inicio, fin in generate_slots(agenda, desde, hasta, tz=tz):
            if any(inicio < b.ends_at and fin > b.starts_at for b in bloqueos):
                continue
            total += 1
    return total


def calcular(organizacion, desde: dt.date, hasta: dt.date, branch_id=None, ahora=None) -> dict:
    """Los indicadores de la organización en `[desde, hasta]`."""
    ahora = ahora or timezone.now()
    inicio, fin = rango_utc(organizacion, desde, hasta)

    fichas = Appointment.objects.filter(
        organization=organizacion, starts_at__gte=inicio, starts_at__lt=fin,
    )
    pagos = Payment.objects.filter(
        organization=organizacion, status=Payment.Status.SUCCEEDED,
        appointment__starts_at__gte=inicio, appointment__starts_at__lt=fin,
    )
    if branch_id:
        fichas = fichas.filter(branch_id=branch_id)
        pagos = pagos.filter(appointment__branch_id=branch_id)

    # ---- Ocupación y demanda: las fichas que ocuparon un espacio ----------
    ocupadas = fichas.filter(status__in=OCUPAN_ESPACIO)
    reservadas = ocupadas.count()
    ofrecidos = _espacios_ofrecidos(organizacion, desde, hasta, branch_id)

    # ---- Inasistencia ------------------------------------------------------
    conteo = fichas.aggregate(
        esperadas=Count("id", filter=debian_atenderse_q(ahora)),
        ausentes=Count("id", filter=inasistencia_q(ahora)),
    )

    # ---- Demanda -----------------------------------------------------------
    por_sucursal = [
        {"id": str(fila["branch_id"]), "name": fila["branch__name"], "total": fila["total"]}
        for fila in ocupadas.values("branch_id", "branch__name")
        .annotate(total=Count("id")).order_by("-total", "branch__name")
    ]
    # Un profesional con varias especialidades cuenta en cada una; el total
    # de arriba (`reservadas`) no duplica.
    nombres = dict(
        PractitionerSpecialty.objects.filter(organization=organizacion)
        .values_list("specialty_id", "specialty__name")
    )
    por_especialidad = []
    for fila in (
        ocupadas.values("practitioner__specialty_links__specialty_id")
        .annotate(total=Count("id")).order_by("-total")
    ):
        especialidad_id = fila["practitioner__specialty_links__specialty_id"]
        por_especialidad.append({
            "id": str(especialidad_id) if especialidad_id else None,
            "name": nombres.get(especialidad_id, SIN_ESPECIALIDAD),
            "total": fila["total"],
        })
    por_especialidad.sort(key=lambda f: (-f["total"], f["name"]))

    # ---- Ingresos ----------------------------------------------------------
    def _plata(valor):
        return str((valor or Decimal("0")).quantize(Decimal("0.01")))

    por_moneda = [
        {"currency": fila["currency"], "total": _plata(fila["total"]), "payments": fila["pagos"]}
        for fila in pagos.values("currency")
        .annotate(total=Sum("amount"), pagos=Count("id")).order_by("currency")
    ]
    ingresos_sucursal = [
        {
            "id": str(fila["appointment__branch_id"]),
            "name": fila["appointment__branch__name"],
            "currency": fila["currency"],
            "total": _plata(fila["total"]),
        }
        for fila in pagos.values("appointment__branch_id", "appointment__branch__name", "currency")
        .annotate(total=Sum("amount")).order_by("appointment__branch__name", "currency")
    ]

    return {
        "range": {
            "from": desde.isoformat(), "to": hasta.isoformat(),
            "timezone": organizacion.timezone or "America/La_Paz",
        },
        "branch": str(branch_id) if branch_id else None,
        "occupancy": {
            "offered": ofrecidos, "booked": reservadas, "rate": _tasa(reservadas, ofrecidos),
        },
        "no_show": {
            "expected": conteo["esperadas"], "missed": conteo["ausentes"],
            "rate": _tasa(conteo["ausentes"], conteo["esperadas"]),
        },
        "demand": {
            "total": reservadas, "by_branch": por_sucursal, "by_specialty": por_especialidad,
        },
        "revenue": {"by_currency": por_moneda, "by_branch": ingresos_sucursal},
    }
