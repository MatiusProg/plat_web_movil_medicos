"""US-49 — Marcar las tomas de la receta y calcular el cumplimiento.

Los avisos los programa el teléfono (`flutter_local_notifications`) con el
horario que da `frequency.interpretar`. Acá llega cada toma que el paciente
marca: «Tomada» desde el aviso o desde *Mis medicamentos*, o «Salteada».

Quién marca: el paciente o el titular de su dependiente, con el mismo
alcance que el historial (`history_scope == OWN`). El médico sólo lee el
cumplimiento.
"""

from __future__ import annotations

from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException

from .frequency import interpretar
from .models import MedicationIntake


class IntakeConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "intake_conflict"

    def __init__(self, code, detail):
        super().__init__(detail={"code": code, "detail": detail})


class IntakeInvalid(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "intake_invalid"

    def __init__(self, code, detail):
        super().__init__(detail={"code": code, "detail": detail})


def cumplimiento(item, horario: dict | None) -> dict:
    """«12 de 15 tomas (80 %)». Usa las tomas prefetcheadas si las hay."""
    tomas = list(item.intakes.all())
    tomadas = sum(1 for t in tomas if t.status == MedicationIntake.Status.TAKEN)
    salteadas = len(tomas) - tomadas
    total = horario["total_doses"] if horario else None
    return {
        "taken": tomadas,
        "skipped": salteadas,
        "total": total,
        "rate": round(tomadas / total, 4) if total else None,
    }


def registrar(user, item, dose_number: int, estado: str, scheduled_at=None):
    """Marca una toma. Dos veces la misma toma es un 409, no una fila más."""
    horario, _motivo = interpretar(item.frequency, item.duration)
    if horario is None:
        raise IntakeInvalid(
            "no_schedule",
            "Este medicamento no tiene horario fijo: no hay tomas que marcar.",
        )
    if not 1 <= dose_number <= horario.total_doses:
        raise IntakeInvalid(
            "invalid_dose",
            f"La toma tiene que estar entre 1 y {horario.total_doses}.",
        )
    try:
        with transaction.atomic():
            return MedicationIntake.objects.create(
                organization_id=item.organization_id,
                prescription_item=item,
                patient_id=item.encounter.patient_id,
                dose_number=dose_number,
                status=estado,
                scheduled_at=scheduled_at,
                recorded_by=user,
            )
    except IntegrityError:
        raise IntakeConflict("already_recorded", "Esa toma ya está marcada.")


def as_dict(toma):
    return {
        "dose_number": toma.dose_number,
        "status": toma.status,
        "scheduled_at": toma.scheduled_at,
        "recorded_at": toma.recorded_at,
    }
