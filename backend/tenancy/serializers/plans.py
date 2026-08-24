"""US-44 — Planes de suscripción y su asignación a una organización."""

from datetime import date

from django.db import transaction
from rest_framework import serializers

from accounts.models import AuditLog
from tenancy.models import (
    Organization,
    Subscription,
    SubscriptionPlan,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            "id",
            "code",
            "name",
            "description",
            "monthly_price",
            "currency",
            "max_branches",
            "max_users",
            "max_practitioners",
            "max_appointments_month",
            "max_ai_queries_month",
            "storage_mb",
            "features",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]


class SubscriptionSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    organization_slug = serializers.CharField(
        source="organization.slug",
        read_only=True,
    )

    plan_code = serializers.CharField(
        source="plan.code",
        read_only=True,
    )

    plan_name = serializers.CharField(
        source="plan.name",
        read_only=True,
    )

    assigned_by_email = serializers.EmailField(
        source="assigned_by.email",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Subscription
        fields = [
            "id",
            "organization",
            "organization_name",
            "organization_slug",
            "plan",
            "plan_code",
            "plan_name",
            "starts_at",
            "ends_at",
            "status",
            "change_reason",
            "assigned_by",
            "assigned_by_email",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "assigned_by",
            "created_at",
        ]


class AssignPlanSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField()
    plan_id = serializers.UUIDField()

    starts_at = serializers.DateField(
        required=False,
        default=date.today,
    )

    change_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=200,
        default="",
    )

    def validate(self, attrs):
        organization_id = attrs["organization_id"]
        plan_id = attrs["plan_id"]

        try:
            organization = Organization.objects.get(
                id=organization_id
            )
        except Organization.DoesNotExist:
            raise serializers.ValidationError({
                "organization_id": "La organización no existe."
            })

        try:
            plan = SubscriptionPlan.objects.get(
                id=plan_id
            )
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError({
                "plan_id": "El plan de suscripción no existe."
            })

        if not plan.is_active:
            raise serializers.ValidationError({
                "plan_id": "No se puede asignar un plan inactivo."
            })

        current_subscription = (
            Subscription.objects
            .filter(
                organization=organization,
                ends_at__isnull=True,
            )
            .select_related("plan")
            .first()
        )

        if (
            current_subscription
            and current_subscription.plan_id == plan.id
        ):
            raise serializers.ValidationError({
                "plan_id": (
                    "La organización ya tiene este plan "
                    "como suscripción vigente."
                )
            })

        starts_at = attrs["starts_at"]

        if (
            current_subscription
            and starts_at < current_subscription.starts_at
        ):
            raise serializers.ValidationError({
                "starts_at": (
                    "La fecha del nuevo plan no puede ser anterior "
                    "al inicio de la suscripción vigente."
                )
            })

        attrs["organization"] = organization
        attrs["plan"] = plan
        attrs["current_subscription"] = current_subscription

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]

        organization = validated_data["organization"]
        plan = validated_data["plan"]

        starts_at = validated_data["starts_at"]
        change_reason = validated_data["change_reason"]

        current_subscription = validated_data.get(
            "current_subscription"
        )

        previous_plan = None

        if current_subscription:
            previous_plan = current_subscription.plan.code

            current_subscription.ends_at = starts_at
            current_subscription.status = (
                Subscription.Status.CANCELLED
            )

            current_subscription.save(
                update_fields=[
                    "ends_at",
                    "status",
                ]
            )

        subscription = Subscription.objects.create(
            organization=organization,
            plan=plan,
            starts_at=starts_at,
            status=Subscription.Status.ACTIVE,
            change_reason=change_reason,
            assigned_by=request.user,
        )

        AuditLog.objects.create(
            organization=None,
            user=request.user,
            action="plan.assign",
            entity="subscriptions",
            entity_id=str(subscription.id),
            detail={
                "organization_id": str(organization.id),
                "organization_slug": organization.slug,
                "previous_plan": previous_plan,
                "new_plan": plan.code,
                "starts_at": str(starts_at),
                "change_reason": change_reason,
            },
        )

        return subscription

    def to_representation(self, instance):
        return SubscriptionSerializer(
            instance,
            context=self.context,
        ).data
