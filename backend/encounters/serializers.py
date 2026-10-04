"""Entrada y salida de `/api/encounters/`."""

from rest_framework import serializers

from appointments.models import Appointment

from .models import Encounter, EncounterAmendment


class PatientSummarySerializer(serializers.Serializer):
    """Lo que el médico necesita para saber a quién atiende. Nada clínico."""

    id = serializers.UUIDField()
    full_name = serializers.CharField()
    document_number = serializers.CharField(allow_null=True)
    birth_date = serializers.DateField(allow_null=True)
    sex = serializers.CharField(allow_null=True)


class AmendmentSerializer(serializers.ModelSerializer):
    section_display = serializers.CharField(source="get_section_display", read_only=True)
    author_name = serializers.CharField(source="author.full_name", read_only=True)

    class Meta:
        model = EncounterAmendment
        fields = ["id", "section", "section_display", "text", "author_name", "created_at"]


class AmendmentWriteSerializer(serializers.Serializer):
    section = serializers.ChoiceField(choices=list(Encounter.SECTIONS.items()))
    text = serializers.CharField(trim_whitespace=True, max_length=5000)


class EncounterSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    patient = PatientSummarySerializer(read_only=True)
    practitioner_name = serializers.CharField(source="practitioner.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    appointment_starts_at = serializers.DateTimeField(source="appointment.starts_at", read_only=True)
    signed_by_name = serializers.CharField(source="signed_by.full_name", read_only=True, default=None)
    amendments = AmendmentSerializer(many=True, read_only=True)

    class Meta:
        model = Encounter
        fields = [
            "id", "status", "status_display", "appointment", "appointment_starts_at",
            "patient", "practitioner_name", "branch_name",
            "reason", "evolution", "diagnosis", "indications", "treatment",
            "signed_at", "signed_by_name", "amendments", "created_at", "updated_at",
        ]
        read_only_fields = fields


class EncounterDraftSerializer(serializers.Serializer):
    """Lo editable de un borrador. Todo opcional: se guarda de a partes."""

    reason = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    evolution = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    diagnosis = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    indications = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    treatment = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class OpenEncounterSerializer(serializers.Serializer):
    appointment = serializers.PrimaryKeyRelatedField(queryset=Appointment.objects.all())


class AgendaItemSerializer(serializers.ModelSerializer):
    """Una ficha de la agenda del día del profesional, con su encuentro."""

    status_display = serializers.CharField(source="get_status_display", read_only=True)
    patient = PatientSummarySerializer(read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    encounter = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = ["id", "starts_at", "ends_at", "status", "status_display",
                  "branch_name", "patient", "encounter"]

    def get_encounter(self, ficha):
        encuentro = getattr(ficha, "encounter", None)
        if encuentro is None:
            return None
        return {"id": str(encuentro.id), "status": encuentro.status,
                "status_display": encuentro.get_status_display()}
