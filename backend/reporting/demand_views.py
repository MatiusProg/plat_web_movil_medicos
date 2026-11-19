"""US-37: GET /api/reporting/demand/?weeks=4&branch=<uuid>."""
import uuid

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Branch
from .demand import MAX_WEEKS, project
from .permissions import CanReadKpis


class DemandProjectionView(APIView):
    permission_classes = [IsAuthenticated, CanReadKpis]

    def get(self, request):
        org = getattr(request.user, "organization", None)
        if org is None:
            return Response({"code": "sin_organizacion", "detail": "Se requiere una organización."},
                            status=status.HTTP_403_FORBIDDEN)
        try:
            weeks = int(request.query_params.get("weeks", "4"))
        except (ValueError, TypeError):
            weeks = 0
        if not 1 <= weeks <= MAX_WEEKS:
            return Response({"code": "invalid_weeks", "detail": "weeks debe estar entre 1 y 8."},
                            status=status.HTTP_400_BAD_REQUEST)
        branch = request.query_params.get("branch") or None
        if branch:
            try:
                branch = uuid.UUID(branch)
            except (ValueError, AttributeError):
                return Response({"code": "invalid_branch", "detail": "Sucursal inválida."},
                                status=status.HTTP_400_BAD_REQUEST)
            if not Branch.objects.filter(organization=org, pk=branch).exists():
                return Response({"code": "invalid_branch", "detail": "Sucursal desconocida."},
                                status=status.HTTP_400_BAD_REQUEST)
        return Response(project(org, weeks=weeks, branch_id=branch))
