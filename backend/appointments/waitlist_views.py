"""US-52 — La API de la lista de espera. Prefijo `/api/appointments/waitlist/`.

    GET    waitlist/                mis entradas y las de mis dependientes
    POST   waitlist/                anotarme (o anotar a un dependiente)
    DELETE waitlist/<id>/           salir de la lista
    GET    waitlist/summary/        administración: anotados, tomaron y tasa
                                    de recuperación (`reporting.kpi.read`)

La lista es de los planes Pro y Premium (`tenancy.plans`, clave `waitlist`).
Quien no la tiene recibe `plan_limit` al anotarse, y la lista le llega vacía
con `enabled: false` para que la pantalla no muestre una sección sin sentido.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from reporting.permissions import CanReadKpis
from tenancy.plans import current_plan, require_feature

from . import kpis, waitlist
from .models import WaitlistEntry
from .permissions import CanCreateAppointments, CanReadAppointments

DIAS_POR_DEFECTO = 30


class WaitlistEntrySerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    practitioner_name = serializers.SerializerMethodField()
    specialty_name = serializers.SerializerMethodField()
    branch_name = serializers.SerializerMethodField()
    position = serializers.SerializerMethodField()
    # La ficha que se le guardó y hasta cuándo: es lo que dibuja la cuenta
    # regresiva. Nada de otros pacientes.
    offered_expires_at = serializers.SerializerMethodField()

    class Meta:
        model = WaitlistEntry
        fields = [
            "id", "patient", "patient_name",
            "practitioner", "practitioner_name",
            "specialty", "specialty_name",
            "branch", "branch_name",
            "date_from", "date_to", "status", "position",
            "offered_appointment", "offered_expires_at", "created_at",
        ]
        read_only_fields = fields

    def get_patient_name(self, obj):
        return f"{obj.patient.first_name} {obj.patient.last_name}".strip()

    def get_practitioner_name(self, obj):
        return obj.practitioner.full_name if obj.practitioner_id else None

    def get_specialty_name(self, obj):
        return obj.specialty.name if obj.specialty_id else None

    def get_branch_name(self, obj):
        return obj.branch.name if obj.branch_id else None

    def get_position(self, obj):
        return waitlist.position(obj)

    def get_offered_expires_at(self, obj):
        ficha = obj.offered_appointment
        if ficha is None or ficha.status != "pending_payment":
            return None
        return ficha.expires_at


class JoinWaitlistSerializer(serializers.Serializer):
    patient = serializers.UUIDField()
    practitioner = serializers.UUIDField(required=False, allow_null=True)
    specialty = serializers.UUIDField(required=False, allow_null=True)
    branch = serializers.UUIDField(required=False, allow_null=True)
    date_from = serializers.DateField()
    date_to = serializers.DateField()


def _error(codigo, detalle, http=status.HTTP_400_BAD_REQUEST):
    return Response({"code": codigo, "detail": detalle}, status=http)


def _mias(request):
    """Las entradas del propio paciente y las de sus dependientes."""
    organizacion = request.user.organization
    perfil = getattr(request.user, "patient_profile", None)
    consulta = WaitlistEntry.objects.filter(organization=organizacion)
    if perfil is None:
        return consulta.none()
    return consulta.filter(
        Q(patient_id=perfil.id) | Q(patient__guardian_id=perfil.id),
    )


class WaitlistView(APIView):
    """`GET`/`POST /api/appointments/waitlist/`."""

    def get_permissions(self):
        clase = CanCreateAppointments if self.request.method == "POST" \
            else CanReadAppointments
        return [IsAuthenticated(), clase()]

    def get(self, request):
        plan = current_plan(request.user.organization)
        habilitada = plan is not None and plan.allows(waitlist.FEATURE)
        entradas = (
            _mias(request)
            .filter(status__in=WaitlistEntry.LIVE_STATUSES)
            .select_related("patient", "practitioner", "specialty", "branch",
                            "offered_appointment")
            .order_by("-created_at")
        ) if habilitada else []
        return Response({
            "enabled": habilitada,
            "results": WaitlistEntrySerializer(entradas, many=True).data,
        })

    def post(self, request):
        organizacion = request.user.organization
        require_feature(organizacion, waitlist.FEATURE, waitlist.FEATURE_TEXT)

        entrada = JoinWaitlistSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        try:
            creada = waitlist.join(
                organization=organizacion, user=request.user,
                patient_id=datos["patient"],
                practitioner_id=datos.get("practitioner"),
                specialty_id=datos.get("specialty"),
                branch_id=datos.get("branch"),
                date_from=datos["date_from"], date_to=datos["date_to"],
            )
        except ValidationError as error:
            return _error(error.code or "lista_invalida", error.messages[0])
        return Response(
            WaitlistEntrySerializer(creada).data, status=status.HTTP_201_CREATED,
        )


class WaitlistEntryView(APIView):
    """`DELETE /api/appointments/waitlist/<id>/`: salir de la lista."""

    permission_classes = [IsAuthenticated, CanReadAppointments]

    def delete(self, request, pk=None):
        entrada = _mias(request).filter(pk=pk).first()
        if entrada is None:
            return _error("entrada_inexistente", "Esa entrada no existe.",
                          status.HTTP_404_NOT_FOUND)
        with transaction.atomic():
            soltada = waitlist.leave(entrada)
        if soltada is not None:
            # Tenia un turno guardado y lo solto: se le ofrece al siguiente.
            transaction.on_commit(lambda: waitlist.offer_freed_slot(
                soltada.id, soltada.organization_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


def _fecha(valor):
    try:
        return dt.date.fromisoformat(valor)
    except ValueError:
        return None


class WaitlistSummaryView(APIView):
    """`GET /api/appointments/waitlist/summary/?from=&to=` (administración)."""

    permission_classes = [IsAuthenticated, CanReadKpis]

    def get(self, request):
        organizacion = request.user.organization
        if organizacion is None:
            return Response({"plataforma": True})
        require_feature(organizacion, waitlist.FEATURE, waitlist.FEATURE_TEXT)

        zona = ZoneInfo(organizacion.timezone or "America/La_Paz")
        hoy = timezone.now().astimezone(zona).date()
        crudo_desde = request.query_params.get("from")
        crudo_hasta = request.query_params.get("to")
        hasta = _fecha(crudo_hasta) if crudo_hasta else hoy
        desde = (
            _fecha(crudo_desde) if crudo_desde
            else hasta - dt.timedelta(days=DIAS_POR_DEFECTO - 1) if hasta else None
        )
        if desde is None or hasta is None:
            return _error("invalid_date",
                          "Las fechas deben tener el formato AAAA-MM-DD.")
        if hasta < desde:
            return _error("invalid_range", "El rango de fechas está invertido.")
        if (hasta - desde).days >= kpis.MAX_DIAS:
            return _error("range_too_long",
                          f"El rango no puede superar {kpis.MAX_DIAS} días.")
        return Response(waitlist.summary(organizacion, desde, hasta))
