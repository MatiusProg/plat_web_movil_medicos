"""US-11 — Lectura y registro de sucursales.

El listado conserva su comportamiento para US-13, US-15 y US-16.
La escritura utiliza los serializers y servicios propios de US-11.
"""

from rest_framework import status
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .branch_serializers import BranchWriteSerializer
from .branch_services import create_branch
from .mixins import OrganizationScopedMixin
from .models import Branch
from .permissions import CanReadBranches
from .serializers import BranchSerializer
from .branch_detail_serializers import BranchDetailSerializer


class BranchListView(OrganizationScopedMixin, ListCreateAPIView):
    """GET y POST /api/catalog/branches/"""

    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, CanReadBranches]

    # Son unas pocas por organización y las dibuja entero un selector.
    pagination_class = None

    def get_queryset(self):
        queryset = self.scoped(Branch.objects.all())
        activo = self.request.query_params.get("is_active")

        if activo in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        elif activo in {"false", "0"}:
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BranchWriteSerializer
        return BranchSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            from .branch_views import CanCreateBranches
            return [IsAuthenticated(), CanCreateBranches()]

        return [IsAuthenticated(), CanReadBranches()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        branch = create_branch(
            organization=request.user.organization,
            data=serializer.validated_data,
            request=request,
        )

        return Response(
            BranchDetailSerializer(branch).data,
            status=status.HTTP_201_CREATED,
        )