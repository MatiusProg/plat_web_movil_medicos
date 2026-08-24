"""US-43 — Alta y consulta de organizaciones (centros médicos cliente)."""

from rest_framework import serializers

from accounts.models import User

from ..models import Organization, SubscriptionPlan
from ..services import create_organization


class OrganizationAdminSerializer(serializers.Serializer):
    """El primer usuario de la organización, el que va a administrarla.

    No lleva contraseña: la genera el sistema y vuelve una sola vez en la
    respuesta del alta. Que la eligiera el superadministrador significaría que
    conoce la clave del administrador de su cliente, y no hay motivo para eso.
    """

    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=80)
    last_name = serializers.CharField(max_length=80)
    document_number = serializers.CharField(max_length=20)
    document_type = serializers.ChoiceField(
        choices=User.DocumentType.choices,
        required=False, default=User.DocumentType.CI,
    )
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True,
                                  default="")


class OrganizationSerializer(serializers.ModelSerializer):
    """Lectura. Agrega el plan vigente, que es lo primero que se mira.

    El plan sale de `v_organization_current_plan`... o saldría, si el ORM
    supiera de esa vista. Acá se resuelve con la suscripción sin fecha de fin,
    que es la misma definición y evita agregar un modelo no gestionado.
    """

    current_plan = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = [
            "id", "slug", "name", "legal_name", "tax_id",
            "contact_email", "contact_phone", "address", "city", "country",
            "logo_url", "primary_color", "secondary_color", "timezone",
            "status", "onboarded_at", "current_plan", "created_at",
        ]
        read_only_fields = fields

    def get_current_plan(self, organization):
        subscription = next(
            (s for s in organization.subscriptions.all() if s.ends_at is None),
            None,
        )
        if subscription is None:
            return None
        return {
            "code": subscription.plan.code,
            "name": subscription.plan.name,
            "starts_at": subscription.starts_at,
        }


class OrganizationCreateSerializer(serializers.ModelSerializer):
    """El alta. RF-W-01.

    Toma el plan por **código** (`basic`, `pro`, `premium`) y no por uuid: en
    el formulario de alta el superadministrador elige "Premium", no un
    identificador, y los tres códigos los garantiza la migración semilla.

    Las validaciones de formato —el slug, los colores— son validadores del
    modelo y la base no las repite, así que acá es donde se hacen cumplir.
    Por eso `validate_slug` no está: `Organization.slug` ya trae su
    `RegexValidator` y el ModelSerializer lo arrastra solo.
    """

    plan_code = serializers.SlugField(write_only=True)
    admin = OrganizationAdminSerializer(write_only=True)

    class Meta:
        model = Organization
        fields = [
            "slug", "name", "legal_name", "tax_id", "contact_email",
            "contact_phone", "address", "city", "country",
            "logo_url", "primary_color", "secondary_color", "timezone",
            "plan_code", "admin",
        ]

    def validate_plan_code(self, value):
        try:
            plan = SubscriptionPlan.objects.get(code=value)
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError(
                f"No existe un plan con el código «{value}»."
            )
        if not plan.is_active:
            raise serializers.ValidationError(
                "No se puede dar de alta una organización con un plan inactivo."
            )
        # Se guarda resuelto para no volver a consultarlo en `create`.
        self._plan = plan
        return value

    def create(self, validated_data):
        validated_data.pop("plan_code")
        admin_data = validated_data.pop("admin")

        organization, admin_user, temporary_password = create_organization(
            organization_data=validated_data,
            admin_data=admin_data,
            plan=self._plan,
            created_by=self.context["request"].user,
        )

        # La contraseña viaja fuera del modelo: se muestra una vez y no se
        # vuelve a poder consultar.
        self._admin_user = admin_user
        self._temporary_password = temporary_password
        return organization

    def to_representation(self, organization):
        data = OrganizationSerializer(organization, context=self.context).data
        data["admin"] = {
            "id": str(self._admin_user.id),
            "email": self._admin_user.email,
            "role": "org_admin",
            # Única vez que se ve. Después queda sólo el hash.
            "temporary_password": self._temporary_password,
        }
        return data
