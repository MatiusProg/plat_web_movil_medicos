"""US-43 — Registrar una nueva organización como inquilino independiente.

RF-W-01. Sólo el Superadministrador de Plataforma, que es quien da de alta a
los centros médicos cliente.

No hace falta envolver nada en ``platform_admin_context()``: cuando el token
lleva ``is_platform_admin``, ``TenantJWTAuthentication`` ya fijó ese contexto
antes de que corra la vista. El alta sí alterna contextos, pero eso pasa
dentro de ``tenancy.services.create_organization``, que es su lugar.
"""

from rest_framework import mixins, status
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Organization
from ..permissions import IsPlatformAdmin
from ..serializers.organizations import (
    OrganizationCreateSerializer,
    OrganizationSerializer,
)


class OrganizationViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """Alta y consulta de organizaciones.

    Sin ``update`` ni ``destroy`` a propósito: editar los datos de una
    organización y suspenderla son acciones distintas, con sus propias
    preguntas —qué pasa con las sesiones abiertas de un inquilino suspendido—
    y no entran en RF-W-01. Los permisos ``platform.organization.update`` y
    ``.suspend`` ya están sembrados esperando su historia.
    """

    permission_classes = [IsPlatformAdmin]
    queryset = Organization.objects.prefetch_related(
        "subscriptions__plan",
    ).order_by("name")

    def get_serializer_class(self):
        if self.action == "create":
            return OrganizationCreateSerializer
        return OrganizationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
