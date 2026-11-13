"""US-47 — Las reglas del chat, fuera de las vistas.

**Quién entra** (todo lo demás recibe 404, no 403: decir que existe ya es
decir algo de un paciente ajeno):

- el lado del **paciente**: el paciente de la atención o el titular de un
  dependiente (``history_scope`` == ``OWN``), con el mismo criterio que la
  historia clínica;
- el lado del **médico**: el médico de esa atención. Otro médico del centro,
  aunque tenga vínculo con el paciente, no lee ni escribe: la consulta es con
  quien lo atendió.

**Cuándo se escribe:** la atención tiene que estar firmada, la conversación
no puede estar cerrada por el médico y no puede haber vencido la ventana
(``ENCOUNTER_CHAT_DAYS``, 15 días desde la firma por omisión). Después queda
de sólo lectura.

**No es un canal de urgencias.** Cada mensaje del paciente pasa por las reglas
de US-34 (``assistant.triage.check``), que no dependen de ningún proveedor.
Si disparan, el mensaje se guarda igual —el médico tiene que verlo—, pero se
marca y la respuesta lleva la derivación a emergencias, que la pantalla
muestra antes que nada.

**Avisos:** el mensaje del médico le llega al paciente por push (el FCM de
US-28), después del COMMIT y sin propagar errores. El médico trabaja en la web
y ve el contador de sin leer en su bandeja.
"""

from __future__ import annotations

import datetime as dt
import logging

from django.conf import settings
from django.db import transaction
from django.db.models import Count, F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from assistant import triage
from encounters.models import Encounter
from encounters.services import OWN, history_scope, practitioner_of

from .models import EncounterMessage, EncounterThread

logger = logging.getLogger(__name__)

MAX_BODY_CHARS = 2000
PATIENT = EncounterMessage.Side.PATIENT
PRACTITIONER = EncounterMessage.Side.PRACTITIONER


class ChatClosed(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "La conversación ya no admite mensajes."
    default_code = "chat_closed"


def window_days() -> int:
    return int(getattr(settings, "ENCOUNTER_CHAT_DAYS", 15))


# --------------------------------------------------------------------------
#  Quién entra
# --------------------------------------------------------------------------

def side_of(user, encounter) -> str | None:
    """``PATIENT``, ``PRACTITIONER`` o ``None`` si ``user`` no tiene lugar.

    El orden importa, como en ``history_scope``: un médico que además es
    paciente del centro escribe en su propia atención como paciente.
    """
    if encounter is None or encounter.status != Encounter.Status.SIGNED:
        return None
    if encounter.organization_id != user.organization_id:
        return None
    if history_scope(user, encounter.patient) == OWN:
        return PATIENT
    profesional = practitioner_of(user)
    if profesional is not None and encounter.practitioner_id == profesional.id:
        return PRACTITIONER
    return None


def encounter_for(user, encounter_id):
    """La atención y el lado de ``user``, o ``(None, None)``."""
    encounter = (
        Encounter.objects
        .select_related("patient", "patient__guardian", "practitioner",
                        "appointment", "branch")
        .filter(pk=encounter_id, organization=user.organization)
        .first()
    )
    lado = side_of(user, encounter)
    return (encounter, lado) if lado else (None, None)


# --------------------------------------------------------------------------
#  La ventana
# --------------------------------------------------------------------------

def closes_at(encounter) -> dt.datetime:
    return encounter.signed_at + dt.timedelta(days=window_days())


def can_write(encounter, thread=None, now=None) -> bool:
    now = now or timezone.now()
    if thread is not None and thread.closed_at is not None:
        return False
    return now < closes_at(encounter)


def thread_of(encounter):
    return EncounterThread.objects.filter(encounter=encounter).first()


def _thread_for_update(encounter):
    """La conversación de la atención, creada si no existía, y bloqueada."""
    thread, _ = EncounterThread.objects.get_or_create(
        encounter=encounter,
        defaults={
            "organization_id": encounter.organization_id,
            "patient_id": encounter.patient_id,
            "practitioner_id": encounter.practitioner_id,
        },
    )
    return EncounterThread.objects.select_for_update().get(pk=thread.pk)


# --------------------------------------------------------------------------
#  Escribir, leer y cerrar
# --------------------------------------------------------------------------

def _clean(body) -> str:
    body = (body or "").strip()
    if not body:
        raise ValidationError({"body": "El mensaje no puede estar vacío."})
    if len(body) > MAX_BODY_CHARS:
        raise ValidationError(
            {"body": f"El mensaje no puede pasar de {MAX_BODY_CHARS} caracteres."})
    return body


def send(user, encounter, side, body):
    """Guarda el mensaje. Devuelve ``(mensaje, resultado_de_la_barrera)``.

    El resultado de la barrera es ``None`` para el médico.
    """
    body = _clean(body)
    barrera = triage.check(body) if side == PATIENT else None
    with transaction.atomic():
        thread = _thread_for_update(encounter)
        if not can_write(encounter, thread):
            raise ChatClosed()
        mensaje = EncounterMessage.objects.create(
            organization_id=encounter.organization_id,
            thread=thread,
            author=user,
            side=side,
            body=body,
            flagged_emergency=bool(barrera and barrera.is_emergency),
        )
        thread.last_message_at = mensaje.created_at
        # Quien escribe leyó todo lo anterior.
        if side == PATIENT:
            thread.patient_read_at = mensaje.created_at
        else:
            thread.practitioner_read_at = mensaje.created_at
        thread.save(update_fields=["last_message_at", "patient_read_at",
                                   "practitioner_read_at"])
        if side == PRACTITIONER:
            organizacion, encuentro = encounter.organization_id, encounter.id
            transaction.on_commit(lambda: notify_patient(encuentro, organizacion))
    return mensaje, barrera


def mark_read(thread, side):
    if thread is None:
        return
    campo = "patient_read_at" if side == PATIENT else "practitioner_read_at"
    EncounterThread.objects.filter(pk=thread.pk).update(**{campo: timezone.now()})


def close(user, encounter):
    """El médico cierra la conversación antes de que venza la ventana."""
    with transaction.atomic():
        thread = _thread_for_update(encounter)
        if thread.closed_at is not None:
            raise ChatClosed("La conversación ya estaba cerrada.")
        thread.closed_at = timezone.now()
        thread.closed_by = user
        thread.save(update_fields=["closed_at", "closed_by"])
    return thread


# --------------------------------------------------------------------------
#  La bandeja del médico
# --------------------------------------------------------------------------

def inbox_for(user):
    """Las conversaciones con mensajes de las atenciones de ``user``.

    Cada una con ``unread``: los mensajes del paciente posteriores a lo que el
    médico leyó. Las que tienen sin leer van primero.
    """
    profesional = practitioner_of(user)
    if profesional is None:
        return EncounterThread.objects.none()
    sin_leer = Count(
        "messages",
        filter=Q(messages__side=PATIENT)
        & (Q(practitioner_read_at__isnull=True)
           | Q(messages__created_at__gt=F("practitioner_read_at"))),
    )
    urgentes = Count(
        "messages",
        filter=Q(messages__flagged_emergency=True)
        & (Q(practitioner_read_at__isnull=True)
           | Q(messages__created_at__gt=F("practitioner_read_at"))),
    )
    return (
        EncounterThread.objects
        .filter(organization=user.organization, practitioner=profesional,
                last_message_at__isnull=False)
        .select_related("patient", "encounter", "encounter__appointment")
        .annotate(unread=sin_leer, unread_emergency=urgentes)
        .order_by("-unread", "-last_message_at")
    )


# --------------------------------------------------------------------------
#  El aviso al paciente
# --------------------------------------------------------------------------

def notify_patient(encounter_id, organization_id) -> None:
    """Push al paciente (o a su titular) de que el médico le respondió.

    Corre después del COMMIT. **Nunca propaga un error**: un FCM caído no
    deshace un mensaje ya guardado.
    """
    from appointments.attendance import recipient_user
    from notifications import push
    from tenancy.context import tenant_context

    try:
        with tenant_context(organization_id):
            encounter = (Encounter.objects
                         .select_related("appointment__patient__user",
                                         "appointment__patient__guardian__user",
                                         "practitioner")
                         .get(pk=encounter_id))
            user = recipient_user(encounter.appointment)
            if user is None:
                return
            push.send_to_user(user, push.Message(
                "Tu médico te respondió",
                f"{encounter.practitioner.full_name} respondió tu consulta.",
                data={"encounter_id": str(encounter.id), "event": "chat"},
            ))
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo avisar del mensaje de la atención %s", encounter_id)
