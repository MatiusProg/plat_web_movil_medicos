"""US-12 (parte) — Lectura de especialidades.

El ABM es de US-12 completa. Acá va el listado que usan la pantalla de entrada
por especialidad de US-16 y los selectores de la agenda.
"""

from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from .mixins import OrganizationScopedMixin
from .models import Specialty
from .permissions import CanReadSpecialties
from .serializers import SpecialtySerializer


class SpecialtyListView(OrganizationScopedMixin, ListAPIView):
    """`GET /api/catalog/specialties/` — especialidades de la organización."""

    serializer_class = SpecialtySerializer
    permission_classes = [IsAuthenticated, CanReadSpecialties]

    def get_queryset(self):
        queryset = self.scoped(Specialty.objects.all())
        activo = self.request.query_params.get("is_active")
        if activo in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        elif activo in {"false", "0"}:
            queryset = queryset.filter(is_active=False)
        return queryset
