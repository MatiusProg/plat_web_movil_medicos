"""US-09 — Búsqueda y consulta de pacientes en ventanilla.

La recepción puede buscar pacientes por documento o nombre, filtrar por
sucursal/estado y consultar datos demográficos y próximas fichas.

No expone antecedentes ni información clínica.
"""

import unicodedata

from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from appointments.models import Appointment

from .models import Patient
from .permissions import CanReadPatients


UUID_REGEX = (
    "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y espacios normalizados."""
    plano = unicodedata.normalize("NFKD", texto or "")
    plano = "".join(
        caracter
        for caracter in plano
        if not unicodedata.combining(caracter)
    )
    return " ".join(plano.lower().split())


class PatientSearchPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class PatientSearchSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "first_name",
            "last_name",
            "full_name",
            "document_type",
            "document_number",
            "birth_date",
            "phone",
            "is_active",
        ]
        read_only_fields = fields


class UpcomingAppointmentSerializer(serializers.ModelSerializer):
    practitioner_name = serializers.CharField(
        source="practitioner.full_name",
        read_only=True,
    )
    branch_name = serializers.CharField(
        source="branch.name",
        read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Appointment
        fields = [
            "id",
            "branch",
            "branch_name",
            "practitioner",
            "practitioner_name",
            "starts_at",
            "ends_at",
            "status",
            "status_label",
        ]
        read_only_fields = fields


class PatientDetailSerializer(PatientSearchSerializer):
    upcoming_appointments = serializers.SerializerMethodField()

    class Meta(PatientSearchSerializer.Meta):
        fields = PatientSearchSerializer.Meta.fields + [
            "sex",
            "created_at",
            "updated_at",
            "upcoming_appointments",
        ]

    def get_upcoming_appointments(self, patient):
        ahora = timezone.now()

        fichas = (
            patient.appointments
            .filter(
                organization=patient.organization,
                starts_at__gte=ahora,
            )
            .exclude(
                status__in=[
                    Appointment.Status.CANCELLED,
                    Appointment.Status.RESCHEDULED,
                    Appointment.Status.EXPIRED,
                ],
            )
            .select_related("practitioner", "branch")
            .order_by("starts_at")[:10]
        )

        return UpcomingAppointmentSerializer(
            fichas,
            many=True,
        ).data


class PatientSearchViewSet(viewsets.ReadOnlyModelViewSet):
    """Consulta de pacientes para recepción.

    GET /api/patients/search/
    GET /api/patients/search/{id}/
    """

    serializer_class = PatientSearchSerializer
    pagination_class = PatientSearchPagination
    lookup_value_regex = UUID_REGEX

    permission_classes = [
        IsAuthenticated,
        CanReadPatients,
    ]

    def organization(self):
        return self.request.user.organization

    def get_serializer_class(self):
        if self.action == "retrieve":
            return PatientDetailSerializer
        return PatientSearchSerializer

    def get_queryset(self):
        organization = self.organization()

        if organization is None:
            return Patient.objects.none()

        queryset = Patient.objects.filter(
            organization=organization,
        )

        texto = (self.request.query_params.get("q") or "").strip()
        documento = (
            self.request.query_params.get("document") or ""
        ).strip()
        estado = (
            self.request.query_params.get("status") or ""
        ).strip().lower()
        sucursal = (
            self.request.query_params.get("branch") or ""
        ).strip()

        # Documento: coincidencia exacta.
        if documento:
            queryset = queryset.filter(
                document_number=documento,
            )

        # Búsqueda general:
        # si coincide exactamente con documento, lo encuentra;
        # si no, busca nombre/apellido de forma parcial.
        if texto:
            texto_normalizado = normalizar(texto)

            ids_nombre = []

            # La comparación normalizada se hace en Python sólo sobre las filas
            # ya acotadas a la organización. Más abajo agregaremos el índice
            # persistente para la prueba de 10.000 registros.
            candidatos = queryset.only(
                "id",
                "first_name",
                "last_name",
                "document_number",
            )

            for paciente in candidatos.iterator(chunk_size=500):
                nombre = normalizar(
                    f"{paciente.first_name} {paciente.last_name}"
                )
                apellido_nombre = normalizar(
                    f"{paciente.last_name} {paciente.first_name}"
                )

                if (
                    texto_normalizado in nombre
                    or texto_normalizado in apellido_nombre
                ):
                    ids_nombre.append(paciente.id)

            queryset = queryset.filter(
                Q(document_number=texto)
                | Q(id__in=ids_nombre)
            )

        if estado == "active":
            queryset = queryset.filter(is_active=True)
        elif estado == "inactive":
            queryset = queryset.filter(is_active=False)

        # Un paciente pertenece al filtro de sucursal cuando tiene fichas
        # asociadas a esa sucursal.
        if sucursal:
            queryset = queryset.filter(
                appointments__branch_id=sucursal,
            )

        return (
            queryset
            .distinct()
            .order_by("last_name", "first_name")
        )

    def retrieve(self, request, *args, **kwargs):
        patient = self.get_object()

        serializer = self.get_serializer(patient)

        return Response(serializer.data)