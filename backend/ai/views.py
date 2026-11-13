"""US-42 — La bandeja del médico y lo que lee el paciente.

Médico (permiso ``ai.text.review`` **y** ser el médico de la atención):

- ``GET  /api/ai/texts/?status=draft``        su bandeja (por defecto, pendientes)
- ``GET  /api/ai/texts/<id>/``                un texto, con la diferencia
- ``PATCH /api/ai/texts/<id>/``               guarda la corrección, sigue pendiente
- ``POST /api/ai/texts/<id>/approve/``        aprueba (con o sin corrección)
- ``POST /api/ai/texts/<id>/discard/``        descarta
- ``POST /api/ai/encounters/<id>/summary/``   US-39: reintenta el resumen

Paciente (permiso ``encounters.history.read``):

- ``GET  /api/ai/texts/mine/``                sus textos **aprobados** y los
  de sus dependientes; ``?patient=``, ``?encounter=`` o ``?kind=`` para
  filtrar.

El texto de otro médico, o de otra organización, da 404 y no 403: decir que
existe ya es decir algo de un paciente ajeno.
"""

import uuid

from django.http import Http404
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action
from encounters.permissions import RequiresPermission

from . import services
from .models import AiGeneratedText
from .serializers import (
    ApproveSerializer,
    FinalTextSerializer,
    PatientTextSerializer,
    ReviewSerializer,
)


class CanReviewTexts(RequiresPermission):
    code = "ai.text.review"


class CanReadOwnHistory(RequiresPermission):
    code = "encounters.history.read"


def _texto_propio(request, pk):
    texto = services.inbox_for(request.user).filter(pk=pk).first()
    if texto is None:
        raise Http404
    return texto


def _asiento(request, action, texto, **extra):
    bitacora.record(
        request, action, "ai_generated_texts", entity_id=texto.pk,
        detail={"tipo": texto.kind, **extra},
    )


class InboxView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, CanReviewTexts]
    serializer_class = ReviewSerializer

    def get_queryset(self):
        estado = self.request.query_params.get("status", AiGeneratedText.Status.DRAFT)
        textos = services.inbox_for(self.request.user)
        if estado != "all":
            if estado not in AiGeneratedText.Status.values:
                return textos.none()
            textos = textos.filter(status=estado)
        # Lo pendiente, del más viejo al más nuevo: lo que más espera va primero.
        orden = "created_at" if estado == AiGeneratedText.Status.DRAFT else "-reviewed_at"
        return textos.order_by(orden)


class TextDetailView(APIView):
    permission_classes = [IsAuthenticated, CanReviewTexts]

    def get(self, request, pk):
        return Response(ReviewSerializer(_texto_propio(request, pk)).data)

    def patch(self, request, pk):
        texto = _texto_propio(request, pk)
        datos = FinalTextSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        texto = services.edit(texto, datos.validated_data["final_text"])
        _asiento(request, Action.AI_TEXT_EDIT, texto)
        return Response(ReviewSerializer(texto).data)


class ApproveView(APIView):
    permission_classes = [IsAuthenticated, CanReviewTexts]

    def post(self, request, pk):
        texto = _texto_propio(request, pk)
        datos = ApproveSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        texto = services.approve(texto, request.user,
                                 datos.validated_data.get("final_text"))
        _asiento(request, Action.AI_TEXT_APPROVE, texto, corregido=texto.was_edited)
        return Response(ReviewSerializer(texto).data)


class DiscardView(APIView):
    permission_classes = [IsAuthenticated, CanReviewTexts]

    def post(self, request, pk):
        texto = services.discard(_texto_propio(request, pk), request.user)
        _asiento(request, Action.AI_TEXT_DISCARD, texto)
        return Response(ReviewSerializer(texto).data)


class ConsultationSummaryView(APIView):
    """US-39 — ``POST /api/ai/encounters/<id>/summary/``

    Vuelve a pedir el resumen de una atención firmada: cuando al firmar la IA
    no estaba disponible, o cuando el médico descartó el anterior. Sólo el
    médico de la atención. Si ya hay uno vivo, no genera otro.
    """

    permission_classes = [IsAuthenticated, CanReviewTexts]

    def post(self, request, encounter_id):
        from encounters.models import Encounter
        from encounters.services import is_own

        from .consultation_summary import generate

        encuentro = (Encounter.objects
                     .filter(organization=request.user.organization, pk=encounter_id)
                     .prefetch_related("prescription_items", "orders")
                     .first())
        if encuentro is None or not is_own(request.user, encuentro):
            raise Http404
        if not encuentro.is_signed:
            raise services.Conflict("El resumen se genera sobre una atención firmada.")
        resultado = generate(encuentro)
        bitacora.record(
            request, Action.AI_TEXT_GENERATE, "encounters", entity_id=encuentro.pk,
            detail={"tipo": "consultation_summary", "resultado": resultado["status"]},
        )
        return Response(resultado)


class PatientTextsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, CanReadOwnHistory]
    serializer_class = PatientTextSerializer

    def get_queryset(self):
        textos = services.approved_for(self.request.user)
        encuentro = self.request.query_params.get("encounter")
        if encuentro:
            # Un id que no es UUID llegaba al ORM y devolvía un 500.
            try:
                encuentro = uuid.UUID(encuentro)
            except ValueError:
                raise ValidationError({"encounter": "No es un identificador válido."})
            textos = textos.filter(encounter_id=encuentro)
        tipo = self.request.query_params.get("kind")
        if tipo:
            textos = textos.filter(kind=tipo)
        # El titular elige de quién ver (él o un dependiente). Igual sólo
        # puede elegir entre los suyos: el filtro va sobre `approved_for`.
        paciente = self.request.query_params.get("patient")
        if paciente:
            textos = textos.filter(patient_id=paciente)
        return textos.order_by("-reviewed_at")
