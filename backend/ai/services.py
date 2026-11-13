"""US-42 — Las reglas de la validación, fuera de las vistas.

**Para quien genera textos (US-39, US-40):** la única puerta de entrada es
:func:`create_draft`. El texto nace en ``draft`` y desde ahí sólo el médico
de la atención lo aprueba, lo corrige o lo descarta. Ejemplo::

    from ai.services import create_draft
    from ai.models import AiGeneratedText

    create_draft(
        kind=AiGeneratedText.Kind.PREPARATION,
        encounter=orden.encounter,
        medical_order=orden,
        text=texto_del_modelo,
        generated_by="gemini",
    )

**Para quien muestra textos al paciente:** :func:`approved_for` es lo único
que se lee. Un ``draft`` no sale de acá, y la prueba lo intenta (regla 14).
"""

import difflib
import re

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from encounters.services import practitioner_of
from patients.dependents import titular_de
from patients.models import Patient

from .models import AiGeneratedText

MAX_TEXT_CHARS = 4000


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "El texto ya fue validado o descartado."
    default_code = "conflict"


# --------------------------------------------------------------------------
#  Para quien genera: US-39 y US-40
# --------------------------------------------------------------------------

def create_draft(*, kind, text, encounter=None, medical_order=None,
                 patient=None, generated_by=""):
    """Guarda lo que escribió el modelo, como borrador para el médico.

    El paciente, el médico y la organización salen de la atención: quien
    genera no los elige, así un texto no puede quedar a nombre de otro
    paciente ni en la bandeja de otro médico. Corre dentro del
    ``tenant_context`` de la petición o del proceso que genera.
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("No hay texto que guardar.")
    if medical_order is not None:
        if encounter is None:
            encounter = medical_order.encounter
        elif medical_order.encounter_id != encounter.id:
            raise ValueError("La orden no es de esa atención.")
    if encounter is None:
        raise ValueError("Un texto para el paciente sale de una atención.")
    if patient is not None and patient.id != encounter.patient_id:
        raise ValueError("El paciente no es el de la atención.")

    return AiGeneratedText.objects.create(
        organization_id=encounter.organization_id,
        kind=kind,
        patient_id=encounter.patient_id,
        practitioner_id=encounter.practitioner_id,
        encounter=encounter,
        medical_order=medical_order,
        generated_text=text[:MAX_TEXT_CHARS],
        generated_by=generated_by[:60],
    )


# --------------------------------------------------------------------------
#  La bandeja del médico
# --------------------------------------------------------------------------

def inbox_for(user):
    """Los textos que le toca validar a ``user``: los de sus atenciones."""
    profesional = practitioner_of(user)
    if profesional is None:
        return AiGeneratedText.objects.none()
    return (
        AiGeneratedText.objects
        .filter(organization=user.organization, practitioner=profesional)
        .select_related("patient", "encounter__appointment", "medical_order",
                        "reviewed_by")
        # US-39: las advertencias del resumen miran la receta.
        .prefetch_related("encounter__prescription_items")
    )


def _clean(text):
    text = (text or "").strip()
    if not text:
        raise ValidationError({"final_text": "El texto no puede quedar vacío."})
    if len(text) > MAX_TEXT_CHARS:
        raise ValidationError(
            {"final_text": f"El texto no puede pasar de {MAX_TEXT_CHARS} caracteres."})
    return text


def _lock_draft(texto):
    """La fila bloqueada, y sólo si sigue en borrador.

    El bloqueo evita que dos pestañas del mismo médico aprueben y descarten a
    la vez: la segunda espera, ve que ya no es borrador y recibe un 409.
    """
    fila = AiGeneratedText.objects.select_for_update().get(pk=texto.pk)
    if fila.status != AiGeneratedText.Status.DRAFT:
        raise Conflict()
    return fila


def edit(texto, final_text):
    """Guarda la corrección del médico sin aprobarla todavía."""
    with transaction.atomic():
        fila = _lock_draft(texto)
        fila.final_text = _clean(final_text)
        fila.save(update_fields=["final_text", "updated_at"])
    return fila


def approve(texto, user, final_text=None):
    """Aprueba el texto. Desde acá, y sólo desde acá, lo ve el paciente.

    Sin ``final_text`` se aprueba la última corrección guardada o, si no hubo
    ninguna, el texto del modelo tal cual.
    """
    with transaction.atomic():
        fila = _lock_draft(texto)
        if final_text is not None:
            fila.final_text = _clean(final_text)
        elif not fila.final_text:
            fila.final_text = fila.generated_text
        fila.status = AiGeneratedText.Status.APPROVED
        fila.reviewed_by = user
        fila.reviewed_at = timezone.now()
        fila.save()
    return fila


def discard(texto, user):
    with transaction.atomic():
        fila = _lock_draft(texto)
        fila.status = AiGeneratedText.Status.DISCARDED
        fila.reviewed_by = user
        fila.reviewed_at = timezone.now()
        fila.save()
    return fila


# --------------------------------------------------------------------------
#  Lo que corrigió el médico
# --------------------------------------------------------------------------

# Espacios, palabras y cada signo por separado: si el médico cambia «días.»
# por «días, aunque…», lo que cambió es el punto, no la palabra.
_TOKEN = re.compile(r"\s+|\w+|[^\w\s]")


def diff(original, final):
    """La diferencia palabra por palabra entre el texto del modelo y el final.

    Devuelve tramos ``{"op": "equal" | "insert" | "delete", "text": ...}`` que
    se pintan uno detrás del otro. Por palabras y no por letras: «2 veces al
    día» → «3 veces al día» se lee como una palabra cambiada, no como un
    carácter suelto.
    """
    if not final or final == original:
        return [{"op": "equal", "text": original}]
    a, b = _TOKEN.findall(original), _TOKEN.findall(final)
    tramos = []

    def agregar(op, partes):
        texto = "".join(partes)
        if not texto:
            return
        if tramos and tramos[-1]["op"] == op:
            tramos[-1]["text"] += texto
        else:
            tramos.append({"op": op, "text": texto})

    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            agregar("equal", a[i1:i2])
        else:
            agregar("delete", a[i1:i2])
            agregar("insert", b[j1:j2])
    return tramos


# --------------------------------------------------------------------------
#  Lo que lee el paciente
# --------------------------------------------------------------------------

def own_patient_ids(user):
    """El paciente que es ``user`` y sus dependientes. Nadie más."""
    titular = titular_de(user)
    if titular is None:
        return []
    return [titular.id, *Patient.objects.filter(
        organization=user.organization, guardian=titular,
    ).values_list("id", flat=True)]


def approved_for(user):
    """Los textos aprobados del paciente que pide y de sus dependientes.

    **Regla 14 del Sprint 4:** el filtro por ``approved`` va acá, en el único
    lugar por donde el paciente lee, y no en cada vista que lo use.
    """
    return (
        AiGeneratedText.objects
        .filter(organization=user.organization,
                patient_id__in=own_patient_ids(user),
                status=AiGeneratedText.Status.APPROVED)
        .select_related("patient", "practitioner", "encounter__appointment",
                        "medical_order", "reviewed_by")
    )
