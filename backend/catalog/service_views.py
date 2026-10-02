"""US-32 — ABM de servicios y estudios: precio y preparación.

Mismo patrón que el ABM de especialidades de US-12 (`us12_views.py`):
listar y crear en `services/`, ver y editar en `services/<id>/`, baja lógica
en `services/<id>/deactivate/`. Cada escritura deja asiento en la bitácora.

**Lo que se guarda acá no llega solo al asistente.** El índice se recalcula
con `POST /api/assistant/reindex/` o con `embed_catalog`: reindexar en cada
guardado gastaría una llamada al proveedor por cada precio corregido. La
pantalla lo avisa y ofrece el botón.
"""

from django.db import transaction
from rest_framework import serializers, status
from rest_framework.generics import GenericAPIView, ListCreateAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.actions import Action
from audit.services import record

from .mixins import OrganizationScopedMixin
from .models import Service, Specialty
from .permissions import RequiresPermission


class CanReadServices(RequiresPermission):
    code = "catalog.service.read"


class CanCreateServices(RequiresPermission):
    code = "catalog.service.create"


class CanUpdateServices(RequiresPermission):
    code = "catalog.service.update"


class ServiceSerializer(serializers.ModelSerializer):
    """Lectura y escritura. La especialidad se acota a la organización."""

    specialty = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.none(), allow_null=True, required=False,
    )
    specialty_name = serializers.CharField(
        source="specialty.name", read_only=True, default=None,
    )
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = Service
        fields = [
            "id", "name", "kind", "kind_display", "specialty", "specialty_name",
            "description", "preparation", "price", "currency", "is_active",
        ]
        read_only_fields = ["id", "is_active"]

    def get_fields(self):
        fields = super().get_fields()
        org = self.context["request"].user.organization
        # Sólo especialidades de la propia organización. La FK compuesta lo
        # impide igual en la base; esto lo convierte en un 400 legible.
        fields["specialty"].queryset = Specialty.objects.filter(organization=org)
        return fields

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ingresá el nombre del servicio.")
        org = self.context["request"].user.organization
        qs = Service.objects.filter(organization=org, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un servicio con ese nombre.")
        return value

    def validate_price(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return value


def _audit(request, action, obj):
    record(request, action, "services", entity_id=obj.pk,
           detail={"name": obj.name}, organization=obj.organization)


class ServiceListView(OrganizationScopedMixin, ListCreateAPIView):
    serializer_class = ServiceSerializer
    pagination_class = None

    def get_permissions(self):
        cls = CanCreateServices if self.request.method == "POST" else CanReadServices
        return [IsAuthenticated(), cls()]

    def get_queryset(self):
        qs = self.scoped(Service.objects.select_related("specialty")).order_by("name")
        active = self.request.query_params.get("is_active")
        if active in ("true", "1"):
            qs = qs.filter(is_active=True)
        elif active in ("false", "0"):
            qs = qs.filter(is_active=False)
        return qs

    @transaction.atomic
    def perform_create(self, serializer):
        obj = serializer.save(organization=self.request.user.organization)
        _audit(self.request, Action.SERVICE_CREATE, obj)


class ServiceDetailView(OrganizationScopedMixin, RetrieveUpdateAPIView):
    serializer_class = ServiceSerializer
    http_method_names = ["get", "put", "patch", "head", "options"]

    def get_permissions(self):
        cls = (CanReadServices if self.request.method in ("GET", "HEAD", "OPTIONS")
               else CanUpdateServices)
        return [IsAuthenticated(), cls()]

    def get_queryset(self):
        return self.scoped(Service.objects.select_related("specialty"))

    @transaction.atomic
    def perform_update(self, serializer):
        obj = serializer.save()
        _audit(self.request, Action.SERVICE_UPDATE, obj)


class ServiceDeactivateView(OrganizationScopedMixin, GenericAPIView):
    serializer_class = ServiceSerializer
    permission_classes = [IsAuthenticated, CanUpdateServices]
    http_method_names = ["post", "options"]

    def get_queryset(self):
        return self.scoped(Service.objects.select_related("specialty"))

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_active:
            obj.is_active = False
            obj.save(update_fields=["is_active", "updated_at"])
            _audit(request, Action.SERVICE_DEACTIVATE, obj)
        return Response(self.get_serializer(obj).data, status=status.HTTP_200_OK)
