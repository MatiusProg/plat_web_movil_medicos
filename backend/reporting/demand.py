"""US-37 — Proyección transparente de demanda y ocupación por especialidad.

Proyección: promedio de fichas por semana de las ocho semanas previas,
separado por especialidad/franja. La ocupación estimada se compara con
espacios de agendas vigentes menos bloqueos. Sin datos => no se inventa IA.
"""
from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from zoneinfo import ZoneInfo

from django.utils import timezone

from appointments.models import Appointment
from catalog.models import PractitionerSpecialty, Specialty
from scheduling.availability import generate_slots
from scheduling.models import Schedule, ScheduleBlock

HISTORY_WEEKS = 8
MAX_WEEKS = 8


def band(hour):
    if hour < 12:
        return "manana"
    if hour < 18:
        return "tarde"
    return "noche"


def project(organization, *, weeks=4, branch_id=None, now=None):
    now = now or timezone.now()
    tz = ZoneInfo(organization.timezone or "America/La_Paz")
    today = now.astimezone(tz).date()
    start = today + dt.timedelta(days=(7 - today.weekday()) % 7)
    # Proyección de semanas completas, comenzando por el lunes siguiente.
    if start == today:
        start += dt.timedelta(days=7)
    end = start + dt.timedelta(weeks=weeks)
    # Excluir la semana actual incompleta del histórico y del backtest.
    hist_end = start - dt.timedelta(weeks=1)
    hist_start = hist_end - dt.timedelta(weeks=HISTORY_WEEKS)
    backtest_start = hist_start - dt.timedelta(weeks=HISTORY_WEEKS)
    specs = list(Specialty.objects.filter(organization=organization, is_active=True))
    spec_names = {str(s.id): s.name for s in specs}
    links = PractitionerSpecialty.objects.filter(organization=organization).order_by("id").values_list("practitioner_id", "specialty_id")
    # Un profesional con varias especialidades se asigna a su especialidad
    # principal (primer vínculo), para evitar duplicar fichas o capacidad.
    primary = {}
    for practitioner_id, specialty_id in links:
        primary.setdefault(practitioner_id, str(specialty_id))

    # Una sola consulta para todas las fichas del horizonte histórico y futuro.
    beginning = dt.datetime.combine(backtest_start, dt.time.min, tzinfo=tz)
    ending = dt.datetime.combine(end, dt.time.min, tzinfo=tz)
    qs = Appointment.objects.filter(
        organization=organization, starts_at__gte=beginning,
        starts_at__lt=ending,
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.ATTENDED,
                    Appointment.Status.NO_SHOW],
    )
    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    historical = Counter()
    historical_weeks = Counter()
    reserved = Counter()
    for practitioner_id, starts_at in qs.values_list("practitioner_id", "starts_at"):
        spec = primary.get(practitioner_id)
        if spec is None or spec not in spec_names:
            continue
        local = starts_at.astimezone(tz)
        key = (spec, band(local.hour))
        if backtest_start <= local.date() < hist_end:
            week_key = (local.date() - backtest_start).days // 7
            historical_weeks[(week_key, *key)] += 1
            if hist_start <= local.date():
                historical[key] += 1
        elif start <= local.date() < end:
            week = (local.date() - start).days // 7
            reserved[(week, *key)] += 1

    capacity = Counter()
    schedules = Schedule.objects.filter(
        organization=organization, is_active=True,
        valid_from__lt=end,
    ).select_related("branch")
    if branch_id:
        schedules = schedules.filter(branch_id=branch_id)
    blocks = list(ScheduleBlock.objects.filter(
        organization=organization, is_active=True,
        starts_at__lt=dt.datetime.combine(end, dt.time.min, tzinfo=tz),
        ends_at__gt=dt.datetime.combine(start, dt.time.min, tzinfo=tz),
    ))
    for schedule in schedules:
        spec = primary.get(schedule.practitioner_id)
        if spec is None or spec not in spec_names:
            continue
        branch_tz = ZoneInfo(schedule.branch.timezone or organization.timezone or "America/La_Paz")
        for date, slot_start, slot_end in generate_slots(
            schedule, start, end - dt.timedelta(days=1), tz=branch_tz,
        ):
            if slot_start <= now:
                continue
            if any(b.starts_at < slot_end and b.ends_at > slot_start and
                   (b.practitioner_id is None or b.practitioner_id == schedule.practitioner_id) and
                   (b.branch_id is None or b.branch_id == schedule.branch_id)
                   for b in blocks):
                continue
            week = (date - start).days // 7
            capacity[(week, spec, band(slot_start.astimezone(tz).hour))] += schedule.capacity

    # Backtest walk-forward: para cada semana cerrada usar únicamente las 8
    # anteriores, jamás la semana objetivo. MAE en fichas/semana y WAPE agregado.
    # Las primeras ocho semanas sirven de calentamiento; las últimas ocho se evalúan.
    evaluation = {}
    total_absolute_error = total_actual = comparisons = 0
    for key in historical:
        errors = []
        for evaluation_week in range(HISTORY_WEEKS, HISTORY_WEEKS * 2):
            expected = sum(historical_weeks[(j, *key)] for j in range(
                evaluation_week - HISTORY_WEEKS, evaluation_week)) / HISTORY_WEEKS
            actual = historical_weeks[(evaluation_week, *key)]
            errors.append(abs(actual - expected))
            total_absolute_error += abs(actual - expected)
            total_actual += actual
            comparisons += 1
        evaluation[key] = round(sum(errors) / len(errors), 2)

    rows = []
    for week in range(weeks):
        week_start = start + dt.timedelta(weeks=week)
        for spec_id, name in sorted(spec_names.items(), key=lambda x: x[1]):
            for period in ("manana", "tarde", "noche"):
                key = (spec_id, period)
                slots = capacity[(week, *key)]
                booked = reserved[(week, *key)]
                estimate = round(historical[key] / HISTORY_WEEKS, 1)
                if not (slots or booked or historical[key]):
                    continue
                rows.append({
                    "week_start": week_start.isoformat(),
                    "specialty_id": spec_id, "specialty": name,
                    "period": period, "historical_count": historical[key],
                    "estimated_demand": estimate, "mae_weekly": evaluation.get(key),
                    "already_booked": booked,
                    "capacity": slots,
                    "expected_occupancy": round(min(1, max(booked, estimate) / slots), 4) if slots else None,
                    "over_capacity": slots > 0 and max(booked, estimate) > slots,
                })
    return {
        "method": "historical_weekly_average", "history_weeks": HISTORY_WEEKS,
        "history_from": hist_start.isoformat(), "history_to": hist_end.isoformat(),
        "forecast_from": start.isoformat(), "forecast_to": end.isoformat(),
        "weeks": weeks, "historical_sample": sum(historical.values()),
        "has_historical_data": sum(historical.values()) > 0,
        "validation": {
            "method": "walk_forward", "evaluation_weeks": HISTORY_WEEKS,
            "mae_weekly": round(total_absolute_error / comparisons, 2) if comparisons else None,
            "wape": round(total_absolute_error / total_actual, 4) if total_actual else None,
            "observations": comparisons,
            "note": "Error observado al pronosticar semanas cerradas usando sólo semanas anteriores. "
                    "MAE está en fichas/semana; WAPE no se calcula si no hubo demanda real.",
        },
        "rows": rows,
        "note": ("Estimación basada en promedios de fichas históricas, no un modelo IA. "
                 "La semana actual incompleta se excluye del histórico. La capacidad descuenta bloqueos de agenda. Los médicos con múltiples "
                 "especialidades se asignan a su primera especialidad registrada."),
    }
