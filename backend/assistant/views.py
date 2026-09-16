"""US-31 y US-34 — El endpoint del asistente.

    POST /api/assistant/suggest/   la consulta
    GET  /api/assistant/status/    si el índice está armado y con qué proveedor

La respuesta de ``suggest`` lleva siempre cuatro cosas, y ninguna es opcional:

- ``triage`` — la evaluación de urgencia (US-34). Va **primero** y se calcula
  antes de recuperar nada, así que sale aunque todo lo demás falle.
- ``answer`` — el texto, con ``source`` diciendo si lo redactó un modelo, el
  sistema por plantilla, o si no se pudo.
- ``specialty`` — la especialidad sugerida, **con su uuid**, para que la
  pantalla pueda ofrecer reservar.
- ``fragments`` — los fragmentos que sostienen la respuesta. Es el punto 3 de
  la historia: «sin esa lista no hay cómo demostrar que no alucinó».

**Cuando hay emergencia, no se sugiere especialidad.** US-34 dice que el
asistente «corta el flujo de reserva», y devolver igual una especialidad
reservable sería no cortarlo: la pantalla mostraría el botón de reservar justo
debajo del aviso de ir a emergencias.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action

from . import embeddings, generation, retrieval, triage
from .models import KnowledgeChunk
from .permissions import CanUseAssistant
from .serializers import SuggestSerializer


class SuggestView(APIView):
    """La consulta al asistente. US-31 + US-34."""

    permission_classes = [IsAuthenticated, CanUseAssistant]

    def post(self, request):
        serializer = SuggestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        pregunta = serializer.validated_data["question"]
        tipos = serializer.validated_data.get("source_types")

        organization = getattr(request.user, "organization", None)
        if organization is None:
            return Response(
                {"code": "sin_organizacion",
                 "detail": "El asistente responde sobre el catálogo de una "
                           "organización."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # US-34 primero y sin depender de nada: ni del índice, ni de la red,
        # ni de que haya clave del proveedor.
        evaluacion = triage.evaluate(pregunta)

        try:
            fragmentos = retrieval.search(
                organization, pregunta, source_types=tipos,
            )
        except embeddings.EmbeddingError as error:
            # No se pudo vectorizar la pregunta. Se contesta lo que sí se sabe
            # —la derivación, si corresponde— y se dice que el resto no está
            # disponible. Nunca una respuesta inventada sin contexto.
            self._audit(request, pregunta, evaluacion, [], None,
                        generation.UNAVAILABLE)
            return Response({
                "triage": evaluacion.as_dict(),
                "answer": {"text": generation.NO_DISPONIBLE,
                           "source": generation.UNAVAILABLE},
                "specialty": None,
                "fragments": [],
                "provider": embeddings.provider_name(),
                "detail": str(error),
            })

        if evaluacion.is_emergency:
            # Se corta el flujo: ni especialidad sugerida ni llamada al modelo.
            # Los fragmentos se devuelven igual —pueden incluir la sucursal más
            # cercana, que acá sí sirve— pero la respuesta es la derivación.
            respuesta = {"text": triage.MESSAGE, "source": generation.TEMPLATE}
            especialidad = None
        else:
            respuesta = generation.answer(pregunta, fragmentos)
            especialidad = retrieval.suggested_specialty(fragmentos)

        self._audit(request, pregunta, evaluacion, fragmentos, especialidad,
                    respuesta["source"])

        return Response({
            "triage": evaluacion.as_dict(),
            "answer": respuesta,
            "specialty": especialidad,
            "fragments": [f.as_dict() for f in fragmentos],
            "provider": embeddings.provider_name(),
        })

    def _audit(self, request, pregunta, evaluacion, fragmentos, especialidad,
               origen):
        """El asiento de una consulta al asistente.

        **La pregunta no se guarda entera.** Alguien que le cuenta sus síntomas
        a un chatbot está escribiendo información de salud, y una bitácora que
        la copie convierte la tabla de auditoría en una historia clínica
        paralela sin ninguna de las protecciones de una. Se guarda el largo,
        qué recuperó y qué se le contestó, que es lo que hace falta para
        auditar el comportamiento del asistente.

        **La derivación a emergencia sí queda registrada.** Es lo único que
        alguien podría necesitar reconstruir después.
        """
        bitacora.record(
            request, Action.ASSISTANT_QUERY, "knowledge_chunks", "",
            {
                "question_length": len(pregunta),
                "emergency": evaluacion.is_emergency,
                "emergency_reasons": evaluacion.reasons,
                "fragments": [
                    {"title": f.title, "source_type": f.source_type,
                     "rank": f.rank}
                    for f in fragmentos
                ],
                "specialty": (especialidad or {}).get("name"),
                "answer_source": origen,
                "provider": embeddings.provider_name(),
            },
        )


class StatusView(APIView):
    """Si el asistente puede responder, y con qué.

    Existe porque las dos formas de que el asistente conteste «no sé» son
    indistinguibles desde afuera: que el catálogo no tenga la respuesta y que
    **nadie haya indexado nada**. Esto separa las dos, y es lo primero que hay
    que mirar cuando el asistente no encuentra nada.
    """

    permission_classes = [IsAuthenticated, CanUseAssistant]

    def get(self, request):
        organization = getattr(request.user, "organization", None)
        if organization is None:
            return Response({"indexed": False, "chunks": 0,
                             "provider": embeddings.provider_name()})

        proveedor = embeddings.provider_name()
        propios = KnowledgeChunk.objects.filter(organization=organization)

        por_tipo = {}
        for tipo, etiqueta in KnowledgeChunk.Source.choices:
            por_tipo[tipo] = {
                "label": etiqueta,
                "chunks": propios.filter(source_type=tipo,
                                         provider=proveedor).count(),
            }

        vigentes = propios.filter(provider=proveedor).count()
        return Response({
            "indexed": vigentes > 0,
            "chunks": vigentes,
            # Fragmentos indexados con OTRO proveedor: invisibles para la
            # búsqueda. Si este número es alto y `chunks` es cero, lo que pasa
            # es que se cambió de modelo y falta reindexar — que es un
            # diagnóstico imposible de hacer sin este dato.
            "stale_chunks": propios.exclude(provider=proveedor).count(),
            "provider": proveedor,
            "by_source": por_tipo,
            "last_indexed_at": (
                propios.order_by("-indexed_at")
                .values_list("indexed_at", flat=True)
                .first()
            ),
        })
