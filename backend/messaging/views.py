"""US-47 — Endpoints del chat con el médico tratante.

Todos piden el permiso ``encounters.chat`` (paciente y médico) **y** tener lugar
en esa atención (``services.side_of``). Sin lugar, 404.

- ``GET  /api/messaging/encounters/<id>/chat/``           la conversación, la
  receta y las órdenes de la atención, y si se puede escribir. Marca como
  leído lo del otro lado.
- ``POST /api/messaging/encounters/<id>/chat/messages/``  escribe un mensaje.
- ``POST /api/messaging/encounters/<id>/chat/close/``     el médico la cierra.
- ``GET  /api/messaging/inbox/``                           la bandeja del médico,
  con los sin leer.

**Sin tiempo real:** la pantalla abierta vuelve a pedir la conversación cada
10 segundos. Railway corre un solo proceso y no hay canales; para mensajes
que se contestan en horas, sondear alcanza y no agrega infraestructura.
"""

import uuid

from django.http import Http404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action
from encounters.models import MedicalOrder, PrescriptionItem
from encounters.permissions import RequiresPermission

from . import services
from .models import EncounterMessage

MAX_MESSAGES = 300

# El mismo límite dicho a cada uno: al paciente, que no es para urgencias; al
# médico, que el sistema ya deriva lo que suena a urgencia y se lo marca.
AVISO = {
    services.PATIENT: (
        "Este chat es para consultas sobre tu atención, como la medicación o las "
        "indicaciones. No es para urgencias: ante una urgencia ve al servicio de "
        "emergencias más cercano."
    ),
    services.PRACTITIONER: (
        "Consultas del paciente sobre esta atención, como la medicación o las "
        "indicaciones. No es un canal de urgencias: si un mensaje suena a urgencia, "
        "al paciente se le indica ir a emergencias y acá aparece marcado."
    ),
}


class CanChat(RequiresPermission):
    code = "encounters.chat"


def _uuid(valor):
    try:
        return uuid.UUID(str(valor))
    except ValueError:
        raise Http404


def _atencion(request, encounter_id):
    encounter, lado = services.encounter_for(request.user, _uuid(encounter_id))
    if encounter is None:
        raise Http404
    return encounter, lado


def _mensaje(m, lado_de_quien_lee):
    return {
        "id": str(m.id),
        "side": m.side,
        "author_name": m.author.full_name,
        "body": m.body,
        "created_at": serializers.DateTimeField().to_representation(m.created_at),
        "mine": m.side == lado_de_quien_lee,
        # El médico ve la marca; el paciente ya vio la derivación al escribir.
        "flagged_emergency": m.flagged_emergency if lado_de_quien_lee == services.PRACTITIONER
        else False,
    }


def _fecha(valor):
    return serializers.DateTimeField().to_representation(valor) if valor else None


def _conversacion(encounter, lado, thread):
    mensajes = []
    if thread is not None:
        mensajes = list(
            thread.messages.select_related("author").order_by("-created_at")[:MAX_MESSAGES]
        )[::-1]
    abierta = services.can_write(encounter, thread)
    if thread is not None and thread.closed_at is not None:
        motivo = "closed"
    elif not abierta:
        motivo = "expired"
    else:
        motivo = None
    return {
        "encounter": str(encounter.id),
        "side": lado,
        "patient_name": encounter.patient.full_name,
        "practitioner_name": encounter.practitioner.full_name,
        "encounter_date": _fecha(encounter.appointment.starts_at),
        "signed_at": _fecha(encounter.signed_at),
        "closes_at": _fecha(services.closes_at(encounter)),
        "can_write": abierta,
        "closed_reason": motivo,
        "window_days": services.window_days(),
        "notice": AVISO[lado],
        "prescription": [
            {"medication": p.medication, "dose": p.dose, "frequency": p.frequency,
             "duration": p.duration, "instructions": p.instructions}
            for p in PrescriptionItem.objects.filter(encounter=encounter).order_by("created_at")
        ],
        "orders": [
            {"kind": o.kind, "kind_display": o.get_kind_display(), "description": o.description}
            for o in MedicalOrder.objects.filter(encounter=encounter).order_by("created_at")
        ],
        "messages": [_mensaje(m, lado) for m in mensajes],
    }


class ChatView(APIView):
    permission_classes = [IsAuthenticated, CanChat]

    def get(self, request, encounter_id):
        encounter, lado = _atencion(request, encounter_id)
        thread = services.thread_of(encounter)
        datos = _conversacion(encounter, lado, thread)
        services.mark_read(thread, lado)
        return Response(datos)


class MessageSerializer(serializers.Serializer):
    body = serializers.CharField(allow_blank=True, trim_whitespace=False,
                                 max_length=services.MAX_BODY_CHARS)


class SendMessageView(APIView):
    permission_classes = [IsAuthenticated, CanChat]

    def post(self, request, encounter_id):
        encounter, lado = _atencion(request, encounter_id)
        datos = MessageSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        mensaje, barrera = services.send(request.user, encounter, lado,
                                         datos.validated_data["body"])
        # La bitácora registra que hubo un mensaje, nunca lo que dice.
        bitacora.record(request, Action.CHAT_MESSAGE, "encounter_messages",
                        entity_id=mensaje.id,
                        detail={"lado": lado, "urgencia": mensaje.flagged_emergency})
        cuerpo = {"message": _mensaje(mensaje, lado), "emergency": None}
        if barrera is not None and barrera.is_emergency:
            cuerpo["emergency"] = {"message": barrera.message}
        return Response(cuerpo, status=201)


class CloseChatView(APIView):
    permission_classes = [IsAuthenticated, CanChat]

    def post(self, request, encounter_id):
        encounter, lado = _atencion(request, encounter_id)
        if lado != services.PRACTITIONER:
            raise Http404
        thread = services.close(request.user, encounter)
        bitacora.record(request, Action.CHAT_CLOSE, "encounter_threads", entity_id=thread.id)
        return Response(_conversacion(encounter, lado, thread))


class InboxView(APIView):
    permission_classes = [IsAuthenticated, CanChat]

    def get(self, request):
        hilos = services.inbox_for(request.user)
        filas = [{
            "encounter": str(h.encounter_id),
            "patient_name": h.patient.full_name,
            "encounter_date": _fecha(h.encounter.appointment.starts_at),
            "last_message_at": _fecha(h.last_message_at),
            "unread": h.unread,
            "unread_emergency": h.unread_emergency,
            "can_write": services.can_write(h.encounter, h),
        } for h in hilos[:200]]
        return Response({"results": filas,
                         "unread_total": sum(f["unread"] for f in filas)})
