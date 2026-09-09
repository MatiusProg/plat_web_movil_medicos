"""US-11 — Lógica de negocio de sucursales.

Conserva los modelos y endpoints de lectura existentes.
Las operaciones de escritura se ejecutan dentro de una transacción.
"""

from django.db import transaction
from rest_framework.exceptions import ValidationError

from audit.services import record
from scheduling.models import Schedule

from .models import Branch, BranchHours


def _validate_existing_schedules(branch, hours):
    """Impide que un cambio de horario deje agendas activas fuera de la sede."""

    schedules = Schedule.objects.filter(
        organization_id=branch.organization_id,
        branch=branch,
        is_active=True,
    )

    by_weekday = {}
    for hour in hours:
        by_weekday.setdefault(hour["weekday"], []).append(hour)

    for schedule in schedules:
        ranges = by_weekday.get(schedule.weekday, [])

        # Se conserva la convención actual de US-13:
        # si un día no tiene franjas, no se impone restricción horaria.
        if not ranges:
            continue

        fits = any(
            hour["opens_at"] <= schedule.start_time
            and schedule.end_time <= hour["closes_at"]
            for hour in ranges
        )

        if not fits:
            raise ValidationError({
                "hours": (
                    "El nuevo horario dejaría fuera de atención una agenda "
                    f"activa del día {schedule.weekday}. Modifique primero "
                    "la agenda correspondiente."
                )
            })


@transaction.atomic
def create_branch(*, organization, data, request=None):
    """Registra una sucursal y sus franjas de atención."""

    data = dict(data)
    hours = data.pop("hours", [])

    branch = Branch.objects.create(
        organization=organization,
        **data,
    )

    BranchHours.objects.bulk_create([
        BranchHours(
            organization=organization,
            branch=branch,
            **hour,
        )
        for hour in hours
    ])

    record(
        request,
        action="catalog.branch.create",
        entity="branches",
        entity_id=branch.id,
        detail={"name": branch.name},
        organization=organization,
    )

    return branch


@transaction.atomic
def update_branch(*, branch, data, request=None):
    """Edita una sucursal y, si se envían, reemplaza sus horarios."""

    data = dict(data)
    hours = data.pop("hours", None)

    if hours is not None:
        _validate_existing_schedules(branch, hours)

    previous_name = branch.name

    for field, value in data.items():
        setattr(branch, field, value)

    branch.save()

    if hours is not None:
        BranchHours.objects.filter(
            organization_id=branch.organization_id,
            branch=branch,
        ).delete()

        BranchHours.objects.bulk_create([
            BranchHours(
                organization_id=branch.organization_id,
                branch=branch,
                **hour,
            )
            for hour in hours
        ])

    record(
        request,
        action="catalog.branch.update",
        entity="branches",
        entity_id=branch.id,
        detail={
            "previous_name": previous_name,
            "name": branch.name,
            "hours_updated": hours is not None,
        },
        organization=branch.organization,
    )

    return branch


@transaction.atomic
def deactivate_branch(*, branch, request=None):
    """Realiza la baja lógica de una sucursal."""

    if not branch.is_active:
        return branch

    if Schedule.objects.filter(
        organization_id=branch.organization_id,
        branch=branch,
        is_active=True,
    ).exists():
        raise ValidationError({
            "branch": (
                "No se puede desactivar una sucursal con agendas activas. "
                "Desactive o reorganice primero sus agendas."
            )
        })

    branch.is_active = False
    branch.save(update_fields=["is_active", "updated_at"])

    record(
        request,
        action="catalog.branch.deactivate",
        entity="branches",
        entity_id=branch.id,
        detail={"name": branch.name},
        organization=branch.organization,
    )

    return branch