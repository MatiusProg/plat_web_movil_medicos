"""US-12 — ABM administrativo, separado de la búsqueda US-16."""
from rest_framework import status
from rest_framework.generics import (
    GenericAPIView, RetrieveUpdateAPIView, ListCreateAPIView,
)
from rest_framework.mixins import CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .mixins import OrganizationScopedMixin
from .models import Specialty, Practitioner
from .permissions import (
    RequiresPermission, CanReadSpecialties, CanReadProfessionals,
)
from .serializers import SpecialtySerializer
from .specialties import SpecialtyListView
from .us12_serializers import (
    SpecialtyWriteSerializer, PractitionerWriteSerializer, PractitionerAdminSerializer,
)
from .us12_services import (
    save_specialty, deactivate_specialty, save_practitioner, deactivate_practitioner,
)

class CanCreateSpecialties(RequiresPermission):
    code = "catalog.specialty.create"

class CanUpdateSpecialties(RequiresPermission):
    code = "catalog.specialty.update"

class CanCreateProfessionals(RequiresPermission):
    code = "catalog.professional.create"

class CanUpdateProfessionals(RequiresPermission):
    code = "catalog.professional.update"

class SpecialtyManageListView(CreateModelMixin, SpecialtyListView):
    """Conserva el GET y los filtros de US-16; agrega POST de US-12."""
    def get_permissions(self):
        classes = [IsAuthenticated, CanCreateSpecialties if self.request.method == "POST"
                   else CanReadSpecialties]
        return [cls() for cls in classes]

    def get_serializer_class(self):
        return SpecialtyWriteSerializer if self.request.method == "POST" else SpecialtySerializer

    def create(self, request, *args, **kwargs):
        serializer = SpecialtyWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        obj = save_specialty(organization=request.user.organization,
                             data=serializer.validated_data, request=request)
        return Response(SpecialtySerializer(obj).data, status=status.HTTP_201_CREATED)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

class SpecialtyDetailView(OrganizationScopedMixin, RetrieveUpdateAPIView):
    queryset = Specialty.objects.all()
    serializer_class = SpecialtyWriteSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        return self.scoped(super().get_queryset())

    def get_permissions(self):
        cls = CanReadSpecialties if self.request.method in ("GET", "HEAD", "OPTIONS") else CanUpdateSpecialties
        return [IsAuthenticated(), cls()]

    def retrieve(self, request, *args, **kwargs):
        return Response(SpecialtySerializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data,
                                         partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        obj = save_specialty(organization=request.user.organization,
                             instance=obj, data=serializer.validated_data, request=request)
        return Response(SpecialtySerializer(obj).data)

class SpecialtyDeactivateView(OrganizationScopedMixin, GenericAPIView):
    queryset = Specialty.objects.all()
    permission_classes = [IsAuthenticated, CanUpdateSpecialties]
    http_method_names = ["post", "options"]

    def get_queryset(self):
        return self.scoped(super().get_queryset())

    def post(self, request, *args, **kwargs):
        obj = deactivate_specialty(instance=self.get_object(), request=request)
        return Response(SpecialtySerializer(obj).data)

class PractitionerManageListView(OrganizationScopedMixin, ListCreateAPIView):
    """Administración, incluidas las bajas; no modifica la búsqueda pública."""
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = self.scoped(Practitioner.objects.all()).prefetch_related("specialties", "branches")
        active = self.request.query_params.get("is_active")
        if active in ("true", "1"):
            qs = qs.filter(is_active=True)
        elif active in ("false", "0"):
            qs = qs.filter(is_active=False)
        return qs

    def get_permissions(self):
        cls = CanCreateProfessionals if self.request.method == "POST" else CanReadProfessionals
        return [IsAuthenticated(), cls()]

    def get_serializer_class(self):
        return PractitionerWriteSerializer if self.request.method == "POST" else PractitionerAdminSerializer

    def create(self, request, *args, **kwargs):
        serializer = PractitionerWriteSerializer(data=request.data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        obj = save_practitioner(organization=request.user.organization,
                                data=serializer.validated_data, request=request)
        obj = self.get_queryset().get(pk=obj.pk)
        return Response(PractitionerAdminSerializer(obj).data, status=status.HTTP_201_CREATED)

class PractitionerDetailView(OrganizationScopedMixin, RetrieveUpdateAPIView):
    queryset = Practitioner.objects.all()
    serializer_class = PractitionerWriteSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_queryset(self):
        return self.scoped(super().get_queryset()).prefetch_related("specialties", "branches")

    def get_permissions(self):
        cls = CanReadProfessionals if self.request.method in ("GET", "HEAD", "OPTIONS") else CanUpdateProfessionals
        return [IsAuthenticated(), cls()]

    def retrieve(self, request, *args, **kwargs):
        return Response(PractitionerAdminSerializer(self.get_object()).data)

    def update(self, request, *args, **kwargs):
        obj = self.get_object()
        serializer = self.get_serializer(obj, data=request.data,
                                         partial=kwargs.get("partial", False))
        serializer.is_valid(raise_exception=True)
        obj = save_practitioner(organization=request.user.organization,
                                instance=obj, data=serializer.validated_data, request=request)
        obj = self.get_queryset().get(pk=obj.pk)
        return Response(PractitionerAdminSerializer(obj).data)

class PractitionerDeactivateView(OrganizationScopedMixin, GenericAPIView):
    queryset = Practitioner.objects.all()
    permission_classes = [IsAuthenticated, CanUpdateProfessionals]
    http_method_names = ["post", "options"]

    def get_queryset(self):
        return self.scoped(super().get_queryset())

    def post(self, request, *args, **kwargs):
        obj = deactivate_practitioner(instance=self.get_object(), request=request)
        return Response(PractitionerAdminSerializer(obj).data)
