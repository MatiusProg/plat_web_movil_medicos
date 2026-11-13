"""US-42 — Cómo sale un texto generado: para el médico y para el paciente.

Son dos serializers a propósito. El del médico lleva el texto del modelo, el
corregido y la diferencia; el del paciente, **sólo el texto aprobado**. Si un
día alguien agrega un campo al del médico, no aparece solo en la app del
paciente.
"""

from rest_framework import serializers

from . import services
from .models import AiGeneratedText


def _fecha_atencion(texto):
    encuentro = texto.encounter
    if encuentro is None or encuentro.appointment is None:
        return None
    return encuentro.appointment.starts_at


class ReviewSerializer(serializers.ModelSerializer):
    """Una fila de la bandeja del médico."""

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    encounter_date = serializers.SerializerMethodField()
    order_description = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    was_edited = serializers.BooleanField(read_only=True)
    diff = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = AiGeneratedText
        fields = [
            "id", "kind", "kind_display", "status", "status_display",
            "patient", "patient_name", "encounter", "encounter_date",
            "medical_order", "order_description",
            "generated_text", "final_text", "generated_by", "was_edited", "diff",
            "warnings",
            "reviewed_by_name", "reviewed_at", "created_at",
        ]
        read_only_fields = fields

    def get_encounter_date(self, obj):
        fecha = _fecha_atencion(obj)
        return serializers.DateTimeField().to_representation(fecha) if fecha else None

    def get_order_description(self, obj):
        return obj.medical_order.description if obj.medical_order_id else None

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by_id else None

    def get_diff(self, obj):
        return services.diff(obj.generated_text, obj.final_text)

    def get_warnings(self, obj):
        """US-39: lo que conviene mirar dos veces. Sólo en lo pendiente."""
        if (obj.status != AiGeneratedText.Status.DRAFT
                or obj.kind != AiGeneratedText.Kind.CONSULTATION_SUMMARY
                or obj.encounter is None):
            return []
        from .consultation_summary import warnings
        return warnings(obj.encounter, obj.final_text or obj.generated_text)


class FinalTextSerializer(serializers.Serializer):
    final_text = serializers.CharField(
        allow_blank=True, trim_whitespace=False,
        max_length=services.MAX_TEXT_CHARS,
    )


class ApproveSerializer(serializers.Serializer):
    # Opcional: sin él se aprueba la última corrección o el texto del modelo.
    final_text = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False,
        max_length=services.MAX_TEXT_CHARS,
    )


class PatientTextSerializer(serializers.ModelSerializer):
    """Lo que ve el paciente: el texto que aprobó su médico, y nada más."""

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    text = serializers.CharField(source="final_text", read_only=True)
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    practitioner_name = serializers.CharField(source="practitioner.full_name",
                                              read_only=True)
    encounter_date = serializers.SerializerMethodField()
    order_description = serializers.SerializerMethodField()
    approved_at = serializers.DateTimeField(source="reviewed_at", read_only=True)

    class Meta:
        model = AiGeneratedText
        fields = [
            "id", "kind", "kind_display", "text", "patient", "patient_name",
            "practitioner_name", "encounter", "encounter_date",
            "medical_order", "order_description", "approved_at",
        ]
        read_only_fields = fields

    def get_encounter_date(self, obj):
        fecha = _fecha_atencion(obj)
        return serializers.DateTimeField().to_representation(fecha) if fecha else None

    def get_order_description(self, obj):
        return obj.medical_order.description if obj.medical_order_id else None
