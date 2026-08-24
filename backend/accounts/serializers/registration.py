"""US-01 — Registro de un paciente: cuenta de acceso y ficha demográfica."""

from django.db import transaction
from rest_framework import serializers

from patients.models import Patient
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ..models import Role, User, UserRole


class PatientRegistrationSerializer(serializers.Serializer):
    """Crea una cuenta de acceso y su ficha de paciente titular."""

    organization = serializers.CharField(max_length=40)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirmation = serializers.CharField(write_only=True)
    document_number = serializers.CharField(max_length=20)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    document_type = serializers.ChoiceField(
        choices=User.DocumentType.choices, required=False,
    )
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    birth_date = serializers.DateField(required=False, allow_null=True)
    sex = serializers.ChoiceField(
        choices=Patient.Sex.choices, required=False, allow_null=True,
    )

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("password_confirmation"):
            raise serializers.ValidationError({
                "password_confirmation": "Las contrasenas no coinciden.",
            })
        organization_slug = attrs["organization"]
        with platform_admin_context():
            organization = Organization.objects.filter(
                slug=organization_slug, status=Organization.Status.ACTIVE,
            ).first()
        if organization is None:
            raise serializers.ValidationError({
                "organization": "La organizacion no existe o no esta activa.",
            })
        attrs["organization"] = organization
        with tenant_context(organization.id):
            if User.objects.filter(
                organization=organization, email__iexact=attrs["email"],
            ).exists():
                raise serializers.ValidationError({
                    "email": "Ya existe una cuenta con este correo en la organizacion.",
                })
            if User.objects.filter(
                organization=organization,
                document_number=attrs["document_number"],
            ).exists():
                raise serializers.ValidationError({
                    "document_number": "Ya existe una cuenta con este documento en la organizacion.",
                })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        organization = validated_data.pop("organization")
        password = validated_data.pop("password")
        validated_data.pop("password_confirmation", None)
        sex = validated_data.pop("sex", None)
        with tenant_context(organization.id):
            user = User.objects.create_user(
                password=password, organization=organization, **validated_data,
            )
            role = (
                Role.objects.filter(
                    organization=organization, code="patient", is_active=True,
                ).first()
            )
            if role is None:
                raise serializers.ValidationError({
                    "organization": "La organizacion no tiene configurado el rol Paciente.",
                })
            UserRole.objects.create(
                user=user, role=role, organization=organization,
            )
            Patient.objects.create(
                organization=organization, user=user,
                document_type=user.document_type,
                document_number=user.document_number,
                first_name=user.first_name, last_name=user.last_name,
                birth_date=user.birth_date, sex=sex, phone=user.phone,
            )
        return user

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "email": instance.email,
            "organization": instance.organization.slug,
            "role": "patient",
            "patient_id": str(instance.patient_profile.id),
        }
