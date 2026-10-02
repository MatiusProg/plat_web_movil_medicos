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

**US-32: el mismo endpoint contesta consultas administrativas.** No hay un
clasificador de intención aparte: la búsqueda ya lo decide. Si el fragmento
más parecido es de una sede, un servicio o una política, la pregunta era
administrativa y se contesta con ese dato, sin sugerir especialidad. Si es de
una especialidad, sigue el camino de siempre. La respuesta lo dice en
``kind``: ``"orientacion"`` o ``"administrativa"``. Es un campo nuevo, así que
el cliente que no lo lee sigue funcionando igual.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action

from . import generation, triage
from .embeddings import EmbeddingError, active_model_name
from .permissions import CanUseAssistant
from .retrieval import is_administrative, rank_specialties, retrieve
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

        # 1. Barrera de seguridad, primera capa de US-34: ver triage.py.
        emergency = triage.check(question)
        if emergency.is_emergency:
            _audit(request, emergency_layer="regla")
            return _emergency_response("regla")

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

        # US-32: la pregunta es administrativa si lo más parecido lo es.
        if fragments and is_administrative(fragments[0]):
            return self._administrativa(request, question, fragments)

        # Lo administrativo que haya quedado más abajo no respalda una
        # sugerencia de especialidad: no viaja ni al modelo ni como evidencia.
        fragments = [f for f in fragments if not is_administrative(f)]
        ranked = rank_specialties(fragments)
        mejor = ranked[0] if ranked else None

        # 3. Redacción, sólo sobre lo recuperado.
        redactado = generation.answer(
            question, fragments, mejor.name if mejor else "",
        )

        # Segunda capa de US-34: el modelo reconoció una urgencia que la lista
        # de reglas no nombra. Se corta igual que con la primera, con el mismo
        # mensaje, y se descarta todo lo recuperado.
        if redactado["emergency"]:
            _audit(request, emergency_layer="modelo")
            return _emergency_response("gemini")

        _audit(request, specialty_suggested=mejor is not None)
        return Response({
            "emergency": False,
            "kind": "orientacion",
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

    def _administrativa(self, request, question, fragments):
        """US-32 — Dónde, cuándo, cuánto o cómo. Ninguna especialidad."""
        fragments = [f for f in fragments if is_administrative(f)]
        redactado = generation.answer_administrative(question, fragments)

        # La segunda capa de US-34 vale también acá: "¿a qué hora abre la
        # guardia? mi papá no respira" es una pregunta de horario.
        if redactado["emergency"]:
            _audit(request, emergency_layer="modelo")
            return _emergency_response("gemini")

        _audit(request, kind="administrativa")
        return Response({
            "emergency": False,
            "kind": "administrativa",
            "answer": redactado["text"],
            "generated_by": redactado["generated_by"],
            "specialty": None,
            "alternatives": [],
            "fragments": FragmentSerializer(fragments, many=True).data,
            "retrieval": {"embedding_model": active_model_name()},
        })


def _emergency_response(generated_by: str) -> Response:
    """La respuesta de una derivación, igual venga de la capa que venga.

    El mensaje es siempre el de ``triage.py``, también cuando la marca la
    levantó el modelo: una urgencia no se contesta con la redacción que el
    proveedor elija ese día.
    """
    return Response({
        "emergency": True,
        "answer": triage.EMERGENCY_MESSAGE,
        "generated_by": generated_by,
        "specialty": None,
        "alternatives": [],
        "fragments": [],
        "retrieval": {"embedding_model": active_model_name()},
    })


def _audit(request, *, emergency_layer: str = "", specialty_suggested=False,
           kind: str = "orientacion"):
    """Asiento de US-06 por cada consulta respondida (US-34).

    **Nunca se guarda el texto de la consulta, ni las señales que dispararon.**
    Quien le cuenta sus síntomas a un chatbot está escribiendo información de
    salud, y una bitácora que la copie es una historia clínica paralela sin
    ninguna de sus protecciones. Lo que queda es quién, cuándo, y si derivó
    —y por cuál de las dos capas—, que es lo que hace falta para auditar la
    barrera sin leer lo que escribió el paciente.
    """
    if emergency_layer:
        bitacora.record(
            request, Action.ASSISTANT_EMERGENCY, "assistant",
            detail={"layer": emergency_layer},
        )
    else:
        bitacora.record(
            request, Action.ASSISTANT_QUERY, "assistant",
            detail={"specialty_suggested": specialty_suggested, "kind": kind},
        )
