"""US-14 — Bloqueo de agenda.

Los bloqueos tapan rangos de la agenda por vacaciones, feriados o ausencias.
Un bloqueo sin `practitioner` es un feriado de toda la organización (US-14 c).
Levantar un bloqueo antes de tiempo es `POST .../lift/` (US-14 f); avisa qué
fichas caen dentro es `GET .../affected/` (US-14 e).
"""

import datetime as dt

from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .mixins import UUID_REGEX, OrganizationScopedMixin
from .models import ScheduleBlock
from .permissions import CanCreateBlocks, CanReadBlocks, CanUpdateBlocks
from .serializers import ScheduleBlockSerializer


class ScheduleBlockViewSet(OrganizationScopedMixin, viewsets.ModelViewSet):
    serializer_class = ScheduleBlockSerializer
    lookup_value_regex = UUID_REGEX
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    permission_classes_by_action = {
        "list": [CanReadBlocks],
        "retrieve": [CanReadBlocks],
        "affected": [CanReadBlocks],
        "create": [CanCreateBlocks],
        "partial_update": [CanUpdateBlocks],
        "lift": [CanUpdateBlocks],
        "destroy": [CanUpdateBlocks],
    }

    def get_permissions(self):
        clases = self.permission_classes_by_action.get(
            self.action, [CanReadBlocks],
        )
        return [IsAuthenticated()] + [clase() for clase in clases]

    def get_queryset(self):
        queryset = self.scoped(
            ScheduleBlock.objects.select_related("practitioner", "branch"),
        )
        params = self.request.query_params
        if practitioner := params.get("practitioner"):
            queryset = queryset.filter(practitioner_id=practitioner)
        if reason := params.get("reason"):
            queryset = queryset.filter(reason=reason)
        if desde := params.get("from"):
            try:
                queryset = queryset.filter(
                    ends_at__gte=dt.date.fromisoformat(desde),
                )
            except ValueError:
                pass
        if hasta := params.get("to"):
            try:
                queryset = queryset.filter(
                    starts_at__lte=dt.datetime.combine(
                        dt.date.fromisoformat(hasta), dt.time.max,
                    ),
                )
            except ValueError:
                pass
        activo = params.get("is_active")
        if activo in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        elif activo in {"false", "0"}:
            queryset = queryset.filter(is_active=False)
        return queryset

    @action(detail=True, methods=["get"])
    def affected(self, request, pk=None):
        """Las fichas ya reservadas que caen dentro del bloqueo (US-14 e).

        El sistema no las cancela solo: sólo las lista para que el
        administrador decida. El Sprint 2 trae la tabla de fichas; hasta
        entonces esto responde vacío.
        """
        self.get_object()  # 404 si no es de la organización
        return Response({"count": 0, "appointments": []})

    @action(detail=True, methods=["post"])
    def lift(self, request, pk=None):
        """Levanta el bloqueo antes de tiempo (US-14 f)."""
        block = self.get_object()
        block.is_active = False
        block.save(update_fields=["is_active", "updated_at"])
        return Response(
            self.get_serializer(block).data, status=status.HTTP_200_OK,
        )

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
