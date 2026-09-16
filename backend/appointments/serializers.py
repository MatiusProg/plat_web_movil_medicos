"""Serializers de fichas.

La reserva y la reprogramación no son un `ModelSerializer` de escritura
directa: la validación de negocio (slot real, disponible, política de
anticipación) la corren `booking.py` y `changes.py`, que son quienes conocen
el turno derivado de la agenda. Acá sólo se valida la forma del pedido.
"""

from rest_framework import serializers

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source="patient.full_name", read_only=True,
    )
    practitioner_name = serializers.CharField(
        source="practitioner.full_name", read_only=True,
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "patient", "patient_name",
            "practitioner", "practitioner_name",
            "branch", "branch_name",
            "starts_at", "ends_at",
            "status",
            "expires_at",
            "cancelled_at", "cancellation_reason", "refund_eligible",
            "rescheduled_from",
            "created_at", "updated_at",
        ]
        read_only_fields = fields


class BookAppointmentSerializer(serializers.Serializer):
    """Entrada de `POST /appointments/appointments/` (US-17)."""

    patient = serializers.UUIDField()
    practitioner = serializers.UUIDField()
    branch = serializers.UUIDField()
    schedule = serializers.UUIDField()
    starts_at = serializers.DateTimeField()


class RescheduleAppointmentSerializer(serializers.Serializer):
    """Entrada de `POST /appointments/appointments/{id}/reschedule/` (US-20)."""

    branch = serializers.UUIDField()
    schedule = serializers.UUIDField()
    starts_at = serializers.DateTimeField()
