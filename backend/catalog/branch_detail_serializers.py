"""US-11 — Respuesta de detalle sin cambiar los serializers de lectura compartidos."""

from rest_framework import serializers

from .models import Branch, BranchHours


class BranchHoursReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchHours
        fields = ["id", "weekday", "opens_at", "closes_at"]


class BranchDetailSerializer(serializers.ModelSerializer):
    hours = BranchHoursReadSerializer(many=True, read_only=True)

    class Meta:
        model = Branch
        fields = [
            "id", "name", "address", "phone", "timezone",
            "latitude", "longitude", "is_active", "hours",
        ]
