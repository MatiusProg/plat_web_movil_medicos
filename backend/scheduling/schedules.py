"""US-13 — Agendas médicas.

La agenda se define como regla (`Schedule`); de ella se derivan los espacios
reservables. Además de un ABM, la vista expone `calendar/`, que es lo que la
pantalla dibuja como calendario semanal (US-13 g).
"""

import datetime as dt
from collections import defaultdict
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .availability import generate_slots
from .mixins import UUID_REGEX, OrganizationScopedMixin
from .models import Schedule
from .permissions import (
    CanCreateSchedules,
    CanReadSchedules,
    CanUpdateSchedules,
)
from .serializers import ScheduleSerializer
from .validators import validate_no_overlap, validate_within_branch_hours


class ScheduleViewSet(OrganizationScopedMixin, viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    lookup_value_regex = UUID_REGEX
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    permission_classes_by_action = {
        "list": [CanReadSchedules],
        "retrieve": [CanReadSchedules],
        "calendar": [CanReadSchedules],
        "create": [CanCreateSchedules],
        "partial_update": [CanUpdateSchedules],
        "destroy": [CanUpdateSchedules],
    }

    def get_permissions(self):
        clases = self.permission_classes_by_action.get(
            self.action, [CanReadSchedules],
        )
        return [IsAuthenticated()] + [clase() for clase in clases]

    def get_queryset(self):
        queryset = self.scoped(
            Schedule.objects.select_related("practitioner", "branch"),
        )
        params = self.request.query_params
        if practitioner := params.get("practitioner"):
            queryset = queryset.filter(practitioner_id=practitioner)
        if branch := params.get("branch"):
            queryset = queryset.filter(branch_id=branch)
        if (weekday := params.get("weekday")) is not None and weekday != "":
            queryset = queryset.filter(weekday=weekday)
        activo = params.get("is_active")
        if activo in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        elif activo in {"false", "0"}:
            queryset = queryset.filter(is_active=False)
        return queryset

    def _reglas_de_negocio(self, serializer):
        """US-13 c y d: solapamiento entre sucursales y horario de la sucursal.

        Devuelve un `Response` con `code` si algo falla, o `None` si todo bien.
        """
        datos = serializer.validated_data
        instancia = serializer.instance

        def campo(nombre):
            if nombre in datos:
                return datos[nombre]
            return getattr(instancia, nombre, None)

        organization = self.request.user.organization
        try:
            validate_within_branch_hours(
                organization=organization,
                branch_id=campo("branch").id,
                weekday=campo("weekday"),
                start_time=campo("start_time"),
                end_time=campo("end_time"),
            )
            validate_no_overlap(
                organization=organization,
                practitioner_id=campo("practitioner").id,
                weekday=campo("weekday"),
                start_time=campo("start_time"),
                end_time=campo("end_time"),
                valid_from=campo("valid_from"),
                valid_until=campo("valid_until"),
                exclude_id=instancia.id if instancia else None,
            )
        except DjangoValidationError as error:
            return Response(
                {"code": error.code or "agenda_invalida",
                 "detail": error.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if (error := self._reglas_de_negocio(serializer)) is not None:
            return error
        self.perform_create(serializer)
        cabeceras = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=cabeceras,
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instancia = self.get_object()
        serializer = self.get_serializer(
            instancia, data=request.data, partial=partial,
        )
        serializer.is_valid(raise_exception=True)
        if (error := self._reglas_de_negocio(serializer)) is not None:
            return error
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        # Baja lógica: las fichas ya reservadas bajo la regla siguen valiendo.
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])

    @action(detail=False, methods=["get"])
    def calendar(self, request):
        """`GET .../schedules/calendar/?practitioner=&branch=&week=<lunes ISO>`

        Los espacios que derivan las reglas para esa semana, agrupados por día.
        Sin restar bloqueos: es la vista de configuración, no la de reserva.
        """
        practitioner = request.query_params.get("practitioner")
        if not practitioner:
            return Response(
                {"detail": "Falta el parámetro practitioner."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        semana = request.query_params.get("week")
        try:
            lunes = dt.date.fromisoformat(semana) if semana else dt.date.today()
        except ValueError:
            return Response(
                {"detail": "week debe ser una fecha ISO (YYYY-MM-DD)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        lunes = lunes - dt.timedelta(days=lunes.weekday())
        domingo = lunes + dt.timedelta(days=6)

        queryset = self.get_queryset().filter(
            practitioner_id=practitioner, is_active=True,
        )
        por_dia = defaultdict(list)
        for schedule in queryset:
            tz = ZoneInfo(schedule.branch.timezone or "America/La_Paz")
            for day, inicio, fin in generate_slots(
                schedule, lunes, domingo, tz=tz,
            ):
                por_dia[day].append({
                    "start": inicio.isoformat(),
                    "end": fin.isoformat(),
                    "branch": {
                        "id": str(schedule.branch_id),
                        "name": schedule.branch.name,
                    },
                    "capacity": schedule.capacity,
                })

        dias = [
            {
                "date": (lunes + dt.timedelta(days=i)).isoformat(),
                "slots": sorted(
                    por_dia.get(lunes + dt.timedelta(days=i), []),
                    key=lambda s: s["start"],
                ),
            }
            for i in range(7)
        ]
        return Response({"week": lunes.isoformat(), "days": dias})
