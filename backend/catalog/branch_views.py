"""US-11 — Vistas de gestión de sucursales."""

from rest_framework import status
from rest_framework.generics import (
    CreateAPIView,
    RetrieveUpdateAPIView,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .branch_serializers import BranchWriteSerializer
from .branch_services import (
    create_branch,
    update_branch,
    deactivate_branch,
)
from .mixins import OrganizationScopedMixin
from .models import Branch
from .permissions import RequiresPermission
from .serializers import BranchSerializer
from .branch_detail_serializers import BranchDetailSerializer


class CanCreateBranches(RequiresPermission):
    code = "catalog.branch.create"


class CanUpdateBranches(RequiresPermission):
    code = "catalog.branch.update"


class CanDeactivateBranches(RequiresPermission):
    code = "catalog.branch.deactivate"


class BranchCreateView(CreateAPIView):
    """POST /api/catalog/branches/"""

    serializer_class = BranchWriteSerializer
    permission_classes = [IsAuthenticated, CanCreateBranches]

    def perform_create(self, serializer):
        self.branch = create_branch(
            organization=self.request.user.organization,
            data=serializer.validated_data,
            request=self.request,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            BranchSerializer(self.branch).data,
            status=status.HTTP_201_CREATED,
        )


class BranchDetailView(OrganizationScopedMixin, RetrieveUpdateAPIView):
    """GET y PATCH /api/catalog/branches/{id}/"""

    queryset = Branch.objects.all()
    serializer_class = BranchWriteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.scoped(Branch.objects.all())

    def get_permissions(self):
        if self.request.method == "GET":
            from .permissions import CanReadBranches
            return [IsAuthenticated(), CanReadBranches()]

        return [IsAuthenticated(), CanUpdateBranches()]

    def retrieve(self, request, *args, **kwargs):
        branch = self.get_object()
        return Response(BranchDetailSerializer(branch).data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        branch = self.get_object()

        serializer = self.get_serializer(
            branch,
            data=request.data,
            partial=partial,
        )
        serializer.is_valid(raise_exception=True)

        branch = update_branch(
            branch=branch,
            data=serializer.validated_data,
            request=request,
        )

        return Response(BranchDetailSerializer(branch).data)


class BranchDeactivateView(OrganizationScopedMixin, APIView):
    """POST /api/catalog/branches/{id}/deactivate/"""

    permission_classes = [IsAuthenticated, CanDeactivateBranches]

    def post(self, request, pk):
        branch = self.scoped(Branch.objects.all()).filter(pk=pk).first()

        if branch is None:
            return Response(
                {"detail": "Sucursal no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        branch = deactivate_branch(branch=branch, request=request)

        return Response(BranchDetailSerializer(branch).data)