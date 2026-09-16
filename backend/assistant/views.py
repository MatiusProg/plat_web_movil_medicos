"""US-31 — ``POST /api/assistant/suggest/``

El camino completo, en el orden en que importa:

    1. barrera de emergencia   (triage)      — antes que nada
    2. recuperación            (retrieval)   — filtrada por organización
    3. redacción               (generation)  — sólo sobre lo recuperado

**La barrera va primero y corta.** Si lo que describe la persona es una
urgencia, no se recupera nada, no se llama al modelo de lenguaje y no se
sugiere ninguna especialidad. Ponerla después de la recuperación tendría el
efecto de mostrarle a alguien con un dolor de pecho una tarjeta de
cardiología con un botón de reservar para el jueves.

**La organización sale del token, nunca del cuerpo de la petición.** Es la
misma regla que US-05 aplica al perfil. Un endpoint de IA que acepta el
inquilino por parámetro es la forma más corta de leer el catálogo de otra
organización.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import generation, triage
from .embeddings import EmbeddingError, active_model_name
from .permissions import CanUseAssistant
from .retrieval import rank_specialties, retrieve
from .serializers import (
    FragmentSerializer,
    SpecialtySuggestionSerializer,
    SuggestRequestSerializer,
)


class SuggestView(APIView):
    """Sugiere la especialidad que corresponde a lo que cuenta el paciente."""

    permission_classes = [IsAuthenticated, CanUseAssistant]

    def post(self, request):
        entrada = SuggestRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        question = entrada.validated_data["question"]

        organization = request.user.organization
        if organization is None:
            # El superadministrador no tiene organización, y por decisión de
            # alcance tampoco accede a datos de ninguna. No hay catálogo suyo
            # sobre el que orientar.
            return Response(
                {"detail": "El asistente funciona dentro de una organización."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 1. Barrera de seguridad. Semilla de US-34: ver triage.py.
        emergency = triage.check(question)
        if emergency.is_emergency:
            return Response({
                "emergency": True,
                "answer": emergency.message,
                "generated_by": "regla",
                "specialty": None,
                "alternatives": [],
                "fragments": [],
                "retrieval": {"embedding_model": active_model_name()},
            })

        # 2. Recuperación.
        try:
            fragments = retrieve(organization, question)
        except EmbeddingError as error:
            # El proveedor de embeddings no respondió. Sin vector no hay
            # búsqueda, y sin búsqueda no hay nada honesto que contestar.
            # 503 y no 500: no está roto, está caído.
            return Response(
                {
                    "emergency": False,
                    "answer": "No puedo responderte ahora. Probá en un rato.",
                    "generated_by": "regla",
                    "detail": str(error),
                    "specialty": None,
                    "alternatives": [],
                    "fragments": [],
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ranked = rank_specialties(fragments)
        mejor = ranked[0] if ranked else None

        # 3. Redacción, sólo sobre lo recuperado.
        redactado = generation.answer(
            question, fragments, mejor.name if mejor else "",
        )

        return Response({
            "emergency": False,
            "answer": redactado["text"],
            "generated_by": redactado["generated_by"],
            "specialty": (
                SpecialtySuggestionSerializer({
                    "id": mejor.id, "name": mejor.name,
                    "similarity": mejor.similarity,
                }).data if mejor else None
            ),
            "alternatives": SpecialtySuggestionSerializer(
                [
                    {"id": s.id, "name": s.name, "similarity": s.similarity}
                    for s in ranked[1:3]
                ],
                many=True,
            ).data,
            # La evidencia. Ver FragmentSerializer: es parte del contrato.
            "fragments": FragmentSerializer(fragments, many=True).data,
            "retrieval": {"embedding_model": active_model_name()},
        })
