"""US-32 — ``POST /api/assistant/reindex/``

Lo mismo que ``embed_catalog --organization <la propia>``, pero desde la web:
el administrador carga un precio o una preparación y lo hace llegar al
asistente sin pedirle a nadie que abra una consola.

La organización sale del token, como en ``SuggestView``: no se puede
reindexar otra. El contexto de inquilino ya lo fijó el middleware, que es lo
que ``index_specialties`` e ``index_administrative`` exigen.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.actions import Action
from audit.services import record

from .embeddings import EmbeddingError
from .indexing import index_administrative, index_specialties
from .permissions import CanReindexCatalog


class ReindexView(APIView):
    permission_classes = [IsAuthenticated, CanReindexCatalog]

    def post(self, request):
        organization = request.user.organization
        if organization is None:
            return Response(
                {"detail": "La reindexación es de una organización."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            especialidades = index_specialties(organization)
            administrativo = index_administrative(organization)
        except EmbeddingError as error:
            return Response(
                {"detail": f"El proveedor de embeddings no respondió: {error}"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        resumen = {
            "specialties": especialidades["specialties"],
            "branches": administrativo["branches"],
            "services": administrativo["services"],
            "fragments": especialidades["fragments"] + administrativo["fragments"],
            "embedding_model": administrativo["model"],
        }
        record(request, Action.ASSISTANT_REINDEX, "assistant", detail=resumen)
        return Response(resumen)
