"""Serializers del catálogo.

Sólo lectura por ahora: el ABM completo de sucursales, especialidades y
profesionales (US-11, US-12) es de otra historia. Acá vive lo que consumen
US-13 (selectores de agenda), US-15 y US-16.
"""

from rest_framework import serializers

from .models import Branch, Specialty


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "address", "phone", "timezone", "is_active"]


class SpecialtySerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ["id", "name", "description", "is_active"]


class SpecialtyRefSerializer(serializers.ModelSerializer):
    """Especialidad reducida, para anidar en la tarjeta de profesional."""

    class Meta:
        model = Specialty
        fields = ["id", "name"]


class BranchRefSerializer(serializers.ModelSerializer):
    """Sucursal reducida, para anidar."""

    class Meta:
        model = Branch
        fields = ["id", "name"]
