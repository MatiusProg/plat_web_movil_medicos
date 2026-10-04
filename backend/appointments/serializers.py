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
    # US-18: cuánto cuesta y en qué quedó el pago. Lo calcula el backend; el
    # móvil sólo lo muestra (regla 10 del Sprint 2).
    fee = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()

    def get_fee(self, obj):
        from payments.pricing import quote

        amount, currency = quote(obj)
        return {"amount": str(amount), "currency": currency}

    def get_payment_status(self, obj):
        # El último intento: un `succeeded` o `refunded` siempre es el último,
        # porque después de pagar no se abren intentos nuevos.
        ultimo = obj.payments.order_by("-created_at").first()
        return ultimo.status if ultimo else None

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
            "checked_in_at", "attendance_confirmed_at",
            "fee", "payment_status",
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
