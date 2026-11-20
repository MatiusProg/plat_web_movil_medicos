"""Entrada y salida de `/api/encounters/`."""

from decimal import Decimal

from rest_framework import serializers

from appointments.models import Appointment

from .models import Encounter, EncounterAmendment, MedicalOrder, PrescriptionItem, VitalSigns


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
    section = serializers.ChoiceField(choices=list(Encounter.AMENDABLE.items()))
    text = serializers.CharField(trim_whitespace=True, max_length=5000)


class PrescriptionItemSerializer(serializers.ModelSerializer):
    """US-26 — Un medicamento de la receta. Sirve para leer y para escribir."""

    medication = serializers.CharField(max_length=200, trim_whitespace=True)
    dose = serializers.CharField(max_length=80, trim_whitespace=True)
    frequency = serializers.CharField(max_length=80, trim_whitespace=True)
    duration = serializers.CharField(max_length=80, trim_whitespace=True)
    instructions = serializers.CharField(
        max_length=300, trim_whitespace=True, required=False, allow_blank=True,
    )

    class Meta:
        model = PrescriptionItem
        fields = ["id", "medication", "dose", "frequency", "duration",
                  "instructions", "created_at"]
        read_only_fields = ["id", "created_at"]

    def to_representation(self, instance):
        """US-49: el horario que sale de la frecuencia y el cumplimiento.

        ``schedule`` es ``None`` con su motivo cuando la indicación no tiene
        horario fijo («según dolor») o no dice por cuántos días: ahí la app no
        ofrece el recordatorio. ``adherence`` lo ven el paciente y el médico.
        """
        from .frequency import para_la_api
        from .intakes import cumplimiento

        datos = super().to_representation(instance)
        horario = para_la_api(instance.frequency, instance.duration)
        datos.update(horario)
        if instance.pk:
            datos["adherence"] = cumplimiento(instance, horario["schedule"])
        return datos


class MedicalOrderSerializer(serializers.ModelSerializer):
    """US-26 — Una orden de laboratorio o de estudio."""

    kind_display = serializers.CharField(source="get_kind_display", read_only=True)
    description = serializers.CharField(max_length=300, trim_whitespace=True)
    notes = serializers.CharField(
        max_length=300, trim_whitespace=True, required=False, allow_blank=True,
    )

    class Meta:
        model = MedicalOrder
        fields = ["id", "kind", "kind_display", "description", "notes", "created_at"]
        read_only_fields = ["id", "created_at"]


class VitalSignsSerializer(serializers.ModelSerializer):
    """US-53 — Los signos vitales, con el IMC y lo anormal ya calculados."""

    bmi = serializers.FloatField(read_only=True)
    alerts = serializers.DictField(child=serializers.CharField(), read_only=True)
    temperature = serializers.FloatField(allow_null=True)
    weight_kg = serializers.FloatField(allow_null=True)
    height_cm = serializers.FloatField(allow_null=True)

    class Meta:
        model = VitalSigns
        fields = [*VitalSigns.FIELDS, "bmi", "alerts"]
        read_only_fields = fields


def _rango(campo, decimales=False):
    minimo, maximo = VitalSigns.LIMITS[campo]
    # DRF formatea el mensaje con `%`: el «(%)» de la saturación lo rompía y
    # una SpO₂ de 101 devolvía un 500 en vez del mensaje (test_us53).
    nombre = str(VitalSigns._meta.get_field(campo).verbose_name).replace("%", "%%")
    mensajes = {
        "min_value": f"{nombre[:1].upper()}{nombre[1:]}: el mínimo posible es {minimo}.",
        "max_value": f"{nombre[:1].upper()}{nombre[1:]}: el máximo posible es {maximo}.",
    }
    if decimales:
        return serializers.DecimalField(
            max_digits=4, decimal_places=1, min_value=Decimal(str(minimo)),
            max_value=Decimal(str(maximo)), required=False, allow_null=True,
            error_messages=mensajes,
        )
    return serializers.IntegerField(min_value=minimo, max_value=maximo, required=False,
                                    allow_null=True, error_messages=mensajes)


class VitalSignsWriteSerializer(serializers.Serializer):
    """Lo que el médico carga. Todo opcional; lo imposible se rechaza."""

    systolic = _rango("systolic")
    diastolic = _rango("diastolic")
    heart_rate = _rango("heart_rate")
    temperature = _rango("temperature", decimales=True)
    spo2 = _rango("spo2")
    weight_kg = _rango("weight_kg", decimales=True)
    height_cm = _rango("height_cm", decimales=True)
    glucose = _rango("glucose")

    def validate(self, attrs):
        sistolica, diastolica = attrs.get("systolic"), attrs.get("diastolic")
        if sistolica is not None and diastolica is not None and sistolica <= diastolica:
            raise serializers.ValidationError(
                {"diastolic": ["La diastólica tiene que ser menor que la sistólica."]},
            )
        return attrs


class EncounterSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    patient = PatientSummarySerializer(read_only=True)
    practitioner_name = serializers.CharField(source="practitioner.full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    appointment_starts_at = serializers.DateTimeField(source="appointment.starts_at", read_only=True)
    signed_by_name = serializers.CharField(source="signed_by.full_name", read_only=True, default=None)
    amendments = AmendmentSerializer(many=True, read_only=True)
    prescription_items = PrescriptionItemSerializer(many=True, read_only=True)
    orders = MedicalOrderSerializer(many=True, read_only=True)
    vital_signs = serializers.SerializerMethodField()

    class Meta:
        model = Encounter
        fields = [
            "id", "status", "status_display", "appointment", "appointment_starts_at",
            "patient", "practitioner_name", "branch_name",
            "reason", "evolution", "diagnosis", "indications", "treatment",
            "signed_at", "signed_by_name", "amendments",
            "prescription_items", "orders", "vital_signs", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_vital_signs(self, encuentro):
        """US-53: ``None`` si no se tomaron; nunca un objeto con todo vacío."""
        try:
            signos = encuentro.vital_signs
        except VitalSigns.DoesNotExist:
            return None
        return None if signos.is_empty else VitalSignsSerializer(signos).data


class EncounterDraftSerializer(serializers.Serializer):
    """Lo editable de un borrador. Todo opcional: se guarda de a partes."""

    reason = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    evolution = serializers.CharField(required=False, allow_blank=True, max_length=10000)
    diagnosis = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    indications = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    treatment = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    # US-53: viajan con el borrador, así «Guardar» y «Firmar» los guardan sin
    # un paso aparte. `null` los borra (sólo mientras es borrador).
    vital_signs = VitalSignsWriteSerializer(required=False, allow_null=True)


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
