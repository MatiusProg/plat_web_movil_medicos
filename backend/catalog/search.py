"""US-16 — Búsqueda de profesionales.

Búsqueda por nombre (parcial, sin distinguir mayúsculas ni tildes) y filtros
por especialidad y por sucursal. Cada resultado trae el dato que decide la
elección: nombre, especialidades, sucursales y **próximo espacio disponible**
(del endpoint de US-15). Búsqueda vacía devuelve el catálogo paginado.

El módulo se acordó con el dueño de `catalog`: la búsqueda vive acá y no en
`professionals.py`, que es el ABM de US-12.
"""

from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated

from scheduling.availability import next_available_slot

from .mixins import OrganizationScopedMixin
from .models import Practitioner, normalize_text
from .permissions import CanReadProfessionals
from .serializers import BranchRefSerializer, SpecialtyRefSerializer


class ProfessionalCardSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    specialties = SpecialtyRefSerializer(many=True, read_only=True)
    branches = BranchRefSerializer(many=True, read_only=True)
    next_available_slot = serializers.SerializerMethodField()

    class Meta:
        model = Practitioner
        fields = [
            "id", "full_name", "specialties", "branches", "next_available_slot",
        ]

    def get_next_available_slot(self, obj):
        # Una llamada por tarjeta (≤ 25 por página) con horizonte corto: es
        # aceptable para el listado. La reserva del Sprint 2 pedirá el detalle
        # completo aparte.
        return next_available_slot(obj.id, horizon_days=14)


class ProfessionalSearchView(OrganizationScopedMixin, ListAPIView):
    """`GET /api/catalog/professionals/?q=&specialty=&branch=&page=`"""

    serializer_class = ProfessionalCardSerializer
    permission_classes = [IsAuthenticated, CanReadProfessionals]

    def get_queryset(self):
        queryset = self.scoped(
            Practitioner.objects.filter(is_active=True)
            .prefetch_related("specialties", "branches")
        )
        params = self.request.query_params

        buscado = (params.get("q") or "").strip()
        if buscado:
            queryset = queryset.filter(
                search_name__contains=normalize_text(buscado),
            )
        if especialidad := params.get("specialty"):
            queryset = queryset.filter(specialties__id=especialidad)
        if sucursal := params.get("branch"):
            queryset = queryset.filter(branches__id=sucursal)

        return queryset.distinct()
