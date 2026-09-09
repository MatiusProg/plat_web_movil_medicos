"""US-11 — Validación de escritura de sucursales y horarios.

Los serializers de lectura existentes permanecen intactos.
La persistencia se implementa por separado en el servicio de US-11.
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.db.models import Q
from rest_framework import serializers

from .models import Branch, BranchHours


class BranchHoursWriteSerializer(serializers.ModelSerializer):
    """Valida una franja de atención de una sucursal."""

    class Meta:
        model = BranchHours
        fields = ["weekday", "opens_at", "closes_at"]

    def validate_weekday(self, value):
        if value < 0 or value > 6:
            raise serializers.ValidationError(
                "El día debe estar entre 0 (lunes) y 6 (domingo)."
            )
        return value

    def validate(self, attrs):
        opens_at = attrs.get("opens_at")
        closes_at = attrs.get("closes_at")

        if opens_at and closes_at and closes_at <= opens_at:
            raise serializers.ValidationError({
                "closes_at": "La hora de cierre debe ser posterior a la apertura."
            })

        return attrs


class BranchWriteSerializer(serializers.ModelSerializer):
    """Valida los datos de alta y edición de una sucursal."""

    hours = BranchHoursWriteSerializer(
        many=True,
        required=False,
        allow_empty=True,
    )

    class Meta:
        model = Branch
        fields = [
            "name",
            "address",
            "phone",
            "timezone",
            "latitude",
            "longitude",
            "hours",
        ]

    def validate_name(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "El nombre de la sucursal es obligatorio."
            )

        request = self.context.get("request")
        if request is None or request.user.organization_id is None:
            raise serializers.ValidationError(
                "No se pudo determinar la organización."
            )

        queryset = Branch.objects.filter(
            organization_id=request.user.organization_id,
            name__iexact=value,
        )

        if self.instance is not None:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError(
                "Ya existe una sucursal con ese nombre en la organización."
            )

        return value

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise serializers.ValidationError(
                "La zona horaria no es válida."
            )

        return value

    def validate_latitude(self, value):
        if value is not None and not -90 <= value <= 90:
            raise serializers.ValidationError(
                "La latitud debe estar entre -90 y 90."
            )
        return value

    def validate_longitude(self, value):
        if value is not None and not -180 <= value <= 180:
            raise serializers.ValidationError(
                "La longitud debe estar entre -180 y 180."
            )
        return value

    def validate_hours(self, value):
        """Evita franjas superpuestas dentro de un mismo día."""

        by_weekday = {}

        for hour in value:
            weekday = hour["weekday"]
            by_weekday.setdefault(weekday, []).append(hour)

        for weekday, ranges in by_weekday.items():
            ranges.sort(key=lambda item: item["opens_at"])

            for previous, current in zip(ranges, ranges[1:]):
                if current["opens_at"] < previous["closes_at"]:
                    raise serializers.ValidationError(
                        f"Existen horarios superpuestos para el día {weekday}."
                    )

        return value

    def validate(self, attrs):
        """Evita modificar una sucursal ajena al tenant."""

        request = self.context.get("request")

        if request is None or request.user.organization_id is None:
            raise serializers.ValidationError(
                "No se pudo determinar la organización."
            )

        if (
            self.instance is not None
            and self.instance.organization_id != request.user.organization_id
        ):
            raise serializers.ValidationError(
                "La sucursal no pertenece a la organización."
            )

        return attrs