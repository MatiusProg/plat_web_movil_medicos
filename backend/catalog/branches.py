"""US-11 (parte) — Lectura de sucursales.

El alta, la edición y la baja son de US-11 completa. Acá va sólo el listado que
necesitan la agenda (US-13), la disponibilidad (US-15) y la búsqueda (US-16),
accesible también al rol *Paciente* (`catalog.branch.read`).
"""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .mixins import OrganizationScopedMixin
from .models import Branch
from .permissions import CanReadBranches
from .serializers import BranchSerializer


class BranchListView(OrganizationScopedMixin, ListAPIView):
    """`GET /api/catalog/branches/` — sucursales de la organización."""

    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, CanReadBranches]

    def get_queryset(self):
        queryset = self.scoped(Branch.objects.all())
        activo = self.request.query_params.get("is_active")
        if activo in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        elif activo in {"false", "0"}:
            queryset = queryset.filter(is_active=False)
        return queryset
