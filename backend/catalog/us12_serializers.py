"""US-12 — Validación de escritura y respuesta administrativa del catálogo."""
from rest_framework import serializers
from django.db.models import Q
from .models import Branch, Specialty, Practitioner, PractitionerBranch, PractitionerSpecialty

class SpecialtyWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specialty
        fields = ["name", "description"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Ingresá el nombre de la especialidad.")
        org = self.context["request"].user.organization
        qs = Specialty.objects.filter(organization=org, name__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe una especialidad con ese nombre.")
        return value

class PractitionerWriteSerializer(serializers.ModelSerializer):
    specialties = serializers.PrimaryKeyRelatedField(
        queryset=Specialty.objects.none(), many=True, required=False,
    )
    branches = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.none(), many=True, required=False,
    )
    class Meta:
        model = Practitioner
        fields = ["first_name", "last_name", "license_number", "specialties", "branches"]

    def get_fields(self):
        fields = super().get_fields()
        org = self.context["request"].user.organization
        specialty_q = Q(is_active=True)
        branch_q = Q(is_active=True)
        if self.instance:
            specialty_q |= Q(practitioners=self.instance)
            branch_q |= Q(practitioners=self.instance)
        fields["specialties"].child_relation.queryset = Specialty.objects.filter(
            organization=org,
        ).filter(specialty_q).distinct()
        fields["branches"].child_relation.queryset = Branch.objects.filter(
            organization=org,
        ).filter(branch_q).distinct()
        return fields

    def validate(self, attrs):
        org = self.context["request"].user.organization
        if self.instance and self.instance.organization_id != org.id:
            raise serializers.ValidationError("El profesional no pertenece a esta organización.")
        for key in ("first_name", "last_name"):
            if key in attrs:
                attrs[key] = attrs[key].strip()
                if not attrs[key]:
                    raise serializers.ValidationError({key: "Este campo no puede estar vacío."})
        if "license_number" in attrs:
            attrs["license_number"] = attrs["license_number"].strip()
            if attrs["license_number"]:
                qs = Practitioner.objects.filter(
                    organization=org, license_number__iexact=attrs["license_number"],
                )
                if self.instance:
                    qs = qs.exclude(pk=self.instance.pk)
                if qs.exists():
                    raise serializers.ValidationError({"license_number": "La matrícula ya está registrada."})
        for key in ("specialties", "branches"):
            if key in attrs:
                ids = [obj.pk for obj in attrs[key]]
                if len(ids) != len(set(ids)):
                    raise serializers.ValidationError({key: "No repitas asociaciones."})
        return attrs

class PractitionerAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)
    specialties = serializers.SerializerMethodField()
    branches = serializers.SerializerMethodField()
    class Meta:
        model = Practitioner
        fields = ["id", "first_name", "last_name", "full_name", "license_number",
                  "is_active", "specialties", "branches"]

    def get_specialties(self, obj):
        return [{"id": str(s.id), "name": s.name} for s in obj.specialties.all()]

    def get_branches(self, obj):
        return [{"id": str(b.id), "name": b.name} for b in obj.branches.all()]
