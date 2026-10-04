"""US-24 — Las reglas del encuentro clínico, fuera de las vistas.

Quién puede atender qué:

- **Sólo el profesional de la ficha.** Tener el permiso no alcanza: un
  médico del mismo centro tiene el mismo permiso y no por eso puede escribir
  en la historia de un paciente que no atendió. Se resuelve por el vínculo
  `Practitioner.user`, consultado en cada petición (dar de baja al
  profesional le corta el acceso en ese momento, como en US-08).
- **Sólo una ficha que sigue en pie.** Cancelada, reprogramada, vencida o
  ausente no se atiende. *Pendiente de pago* sí, por ahora: el pago en línea
  (US-18) todavía no confirma fichas, y el paciente puede pagar en el
  mostrador. Cuando US-18 entre, sacar `PENDING_PAYMENT` de
  `ATTENDABLE_STATUSES` es la única línea que cambia.
- **No antes del día del turno.** Una atención registrada para la semana que
  viene es un error de tipeo, no una atención.

Firmar marca la ficha como **atendida**. Es el desenlace que el modelo de
inasistencia del Sprint 4 necesita y que el reparto pide guardar desde el
primer día: una ficha firmada es, sin ambigüedad, una ficha a la que el
paciente vino.
"""

from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from appointments.models import Appointment
from catalog.models import Practitioner

from .models import Encounter, EncounterAmendment

ATTENDABLE_STATUSES = [
    Appointment.Status.PENDING_PAYMENT,
    Appointment.Status.CONFIRMED,
    Appointment.Status.ATTENDED,
]

# Lo mínimo para firmar. Sin motivo ni diagnóstico, lo firmado no dice qué
# pasó en la consulta; el resto puede ir vacío (un control puede no tener
# tratamiento).
REQUIRED_TO_SIGN = ("reason", "diagnosis")


class Conflict(APIException):
    """409: la operación choca con el estado del encuentro, no con los datos."""

    status_code = status.HTTP_409_CONFLICT
    default_detail = "El encuentro no admite esta operación en su estado actual."
    default_code = "conflict"


def practitioner_of(user):
    """La ficha de profesional activa del usuario, o ``None``."""
    if user is None or not user.is_authenticated:
        return None
    return Practitioner.objects.filter(user=user, is_active=True).first()


def is_own(user, encounter) -> bool:
    profesional = practitioner_of(user)
    return profesional is not None and encounter.practitioner_id == profesional.id


def local_today(appointment):
    tz = ZoneInfo(appointment.branch.timezone or "America/La_Paz")
    return timezone.now().astimezone(tz).date()


def appointment_local_date(appointment):
    tz = ZoneInfo(appointment.branch.timezone or "America/La_Paz")
    return appointment.starts_at.astimezone(tz).date()


@transaction.atomic
def open_encounter(user, appointment):
    """Abre (o devuelve) el encuentro de una ficha.

    Devuelve ``(encuentro, creado)``. Es idempotente: abrir dos veces la
    misma ficha devuelve el mismo borrador, no dos.
    """
    profesional = practitioner_of(user)
    if profesional is None or appointment.practitioner_id != profesional.id:
        raise ValidationError({"appointment": [
            "Sólo el profesional de la ficha puede registrar su atención.",
        ]})

    existente = Encounter.objects.filter(appointment=appointment).first()
    if existente is not None:
        return existente, False

    if appointment.status not in ATTENDABLE_STATUSES:
        raise Conflict(
            f"La ficha está {appointment.get_status_display().lower()}: "
            "no se puede registrar su atención."
        )
    if appointment_local_date(appointment) > local_today(appointment):
        raise Conflict("La ficha es de otro día: se atiende el día del turno.")

    encuentro = Encounter.objects.create(
        organization=appointment.organization,
        appointment=appointment,
        # Copiados de la ficha, nunca del cliente.
        patient_id=appointment.patient_id,
        practitioner_id=appointment.practitioner_id,
        branch_id=appointment.branch_id,
    )
    return encuentro, True


def update_draft(encounter, data):
    if encounter.is_signed:
        raise Conflict(
            "El encuentro está firmado y no se edita. Agregá una enmienda.",
        )
    campos = [campo for campo in Encounter.SECTIONS if campo in data]
    for campo in campos:
        setattr(encounter, campo, data[campo])
    encounter.save(update_fields=[*campos, "updated_at"])
    return encounter


@transaction.atomic
def sign(encounter, user):
    if encounter.is_signed:
        raise Conflict("El encuentro ya estaba firmado.")

    faltan = {
        campo: [f"Completá {Encounter.SECTIONS[campo].lower()} antes de firmar."]
        for campo in REQUIRED_TO_SIGN
        if not getattr(encounter, campo).strip()
    }
    if faltan:
        raise ValidationError(faltan)

    encounter.status = Encounter.Status.SIGNED
    encounter.signed_at = timezone.now()
    encounter.signed_by = user
    encounter.save(update_fields=["status", "signed_at", "signed_by", "updated_at"])

    # El desenlace de la ficha. `select_for_update` porque US-20 puede estar
    # cancelando o reprogramando esta misma ficha en este momento.
    ficha = Appointment.objects.select_for_update().get(pk=encounter.appointment_id)
    if ficha.status in (Appointment.Status.PENDING_PAYMENT, Appointment.Status.CONFIRMED):
        ficha.status = Appointment.Status.ATTENDED
        ficha.save(update_fields=["status", "updated_at"])
    return encounter


def amend(encounter, user, section, text):
    if not encounter.is_signed:
        raise Conflict(
            "El encuentro todavía es borrador: corregilo directamente.",
        )
    return EncounterAmendment.objects.create(
        organization=encounter.organization,
        encounter=encounter,
        section=section,
        text=text,
        author=user,
    )


# --------------------------------------------------------------------------
#  US-25 — Quién lee el historial longitudinal de un paciente
# --------------------------------------------------------------------------

# Los dos alcances posibles, con los mismos nombres que US-08.
OWN = "own"
PROFESSIONAL = "professional"


def history_scope(user, patient):
    """Qué alcance tiene ``user`` sobre el historial de ``patient``.

    Devuelve ``OWN``, ``PROFESSIONAL`` o ``None``.

    - **Propio:** el paciente, o el titular sobre un dependiente a su cargo
      (US-07). Mismo criterio que los antecedentes de US-08.
    - **Profesional:** un médico activo que **tiene o tuvo una ficha** con el
      paciente. El permiso solo no alcanza: lo tiene todo médico del centro, y
      con él cualquiera podría leer la historia de cualquier paciente. La
      ficha es el vínculo de atención que lo justifica. Una vez que existe,
      ve **todos** los encuentros firmados, de todos los médicos y todas las
      sucursales: es lo que hace útil al historial.

    El orden importa, como en US-08: un médico que además es paciente del
    centro lee su propia historia como propia.
    """
    if patient is None:
        return None

    from patients.dependents import titular_de

    if patient.user_id == user.id:
        return OWN
    if patient.guardian_id is not None:
        titular = titular_de(user)
        if titular is not None and patient.guardian_id == titular.id:
            return OWN

    profesional = practitioner_of(user)
    if profesional is not None and Appointment.objects.filter(
        organization=patient.organization,
        patient=patient,
        practitioner=profesional,
        status__in=ATTENDABLE_STATUSES,
    ).exists():
        return PROFESSIONAL
    return None
