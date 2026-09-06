"""Serializers de agendas y bloqueos.

Las validaciones de forma —orden de horas, orden de fechas— van acá y salen
como errores de campo. Las tres reglas de negocio de US-13 (solapamiento,
horario de sucursal, vigencia) las corre la vista, para poder responder con un
`code` propio, como hace el resto del proyecto.
"""

from rest_framework import serializers

from .models import Schedule, ScheduleBlock


class ScheduleSerializer(serializers.ModelSerializer):
    practitioner_name = serializers.CharField(
        source="practitioner.full_name", read_only=True,
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = Schedule
        fields = [
            "id",
            "practitioner", "practitioner_name",
            "branch", "branch_name",
            "weekday", "start_time", "end_time",
            "slot_minutes", "capacity",
            "valid_from", "valid_until",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def _campo(self, attrs, nombre):
        if nombre in attrs:
            return attrs[nombre]
        return getattr(self.instance, nombre, None)

    def validate(self, attrs):
        start_time = self._campo(attrs, "start_time")
        end_time = self._campo(attrs, "end_time")
        valid_from = self._campo(attrs, "valid_from")
        valid_until = self._campo(attrs, "valid_until")

        if start_time is not None and end_time is not None and end_time <= start_time:
            raise serializers.ValidationError(
                {"end_time": "Debe ser posterior a la hora de inicio."}
            )
        if valid_until and valid_from and valid_until < valid_from:
            raise serializers.ValidationError(
                {"valid_until": "No puede ser anterior a la fecha de inicio."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.organization
        return super().create(validated_data)


class ScheduleBlockSerializer(serializers.ModelSerializer):
    practitioner_name = serializers.CharField(
        source="practitioner.full_name", read_only=True,
    )
    branch_name = serializers.CharField(source="branch.name", read_only=True)

    class Meta:
        model = ScheduleBlock
        fields = [
            "id",
            "practitioner", "practitioner_name",
            "branch", "branch_name",
            "starts_at", "ends_at",
            "reason", "note",
            "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        starts_at = attrs.get("starts_at", getattr(self.instance, "starts_at", None))
        ends_at = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        if starts_at and ends_at and ends_at <= starts_at:
            raise serializers.ValidationError(
                {"ends_at": "El fin del bloqueo debe ser posterior al inicio."}
            )
        return attrs

    def create(self, validated_data):
        validated_data["organization"] = self.context["request"].user.organization
        return super().create(validated_data)
