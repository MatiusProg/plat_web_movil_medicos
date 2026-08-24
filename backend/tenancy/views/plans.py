"""US-44 — Planes de suscripción: catálogo, historial y asignación."""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from tenancy.models import (
    Organization,
    Subscription,
    SubscriptionPlan,
)
from tenancy.permissions import IsPlatformAdmin
from tenancy.serializers.plans import (
    AssignPlanSerializer,
    SubscriptionPlanSerializer,
    SubscriptionSerializer,
)


class SubscriptionPlanViewSet(ModelViewSet):
    queryset = SubscriptionPlan.objects.all()
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        is_active = self.request.query_params.get(
            "is_active"
        )

        if is_active is not None:
            if is_active.lower() in {
                "true",
                "1",
            }:
                queryset = queryset.filter(
                    is_active=True
                )

            elif is_active.lower() in {
                "false",
                "0",
            }:
                queryset = queryset.filter(
                    is_active=False
                )

        return queryset


class SubscriptionViewSet(ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsPlatformAdmin]

    queryset = (
        Subscription.objects
        .select_related(
            "organization",
            "plan",
            "assigned_by",
        )
        .all()
    )

    def get_queryset(self):
        queryset = super().get_queryset()

        organization_id = (
            self.request.query_params.get(
                "organization"
            )
        )

        plan_id = (
            self.request.query_params.get(
                "plan"
            )
        )

        status_value = (
            self.request.query_params.get(
                "status"
            )
        )

        current = (
            self.request.query_params.get(
                "current"
            )
        )

        if organization_id:
            queryset = queryset.filter(
                organization_id=organization_id
            )

        if plan_id:
            queryset = queryset.filter(
                plan_id=plan_id
            )

        if status_value:
            queryset = queryset.filter(
                status=status_value
            )

        if current is not None:
            if current.lower() in {
                "true",
                "1",
            }:
                queryset = queryset.filter(
                    ends_at__isnull=True
                )

            elif current.lower() in {
                "false",
                "0",
            }:
                queryset = queryset.filter(
                    ends_at__isnull=False
                )

        return queryset

    @action(
        detail=False,
        methods=["post"],
        url_path="assign",
    )
    def assign(self, request):
        serializer = AssignPlanSerializer(
            data=request.data,
            context={
                "request": request,
            },
        )

        serializer.is_valid(
            raise_exception=True
        )

        subscription = serializer.save()

        return Response(
            SubscriptionSerializer(
                subscription,
                context={
                    "request": request,
                },
            ).data,
            status=status.HTTP_201_CREATED,
        )


class OrganizationSubscriptionViewSet(
    ReadOnlyModelViewSet
):
    serializer_class = SubscriptionSerializer
    permission_classes = [IsPlatformAdmin]

    def get_queryset(self):
        organization_id = self.kwargs.get(
            "organization_id"
        )

        return (
            Subscription.objects
            .select_related(
                "organization",
                "plan",
                "assigned_by",
            )
            .filter(
                organization_id=organization_id
            )
        )

    def list(self, request, *args, **kwargs):
        organization_id = self.kwargs.get(
            "organization_id"
        )

        if not Organization.objects.filter(
            id=organization_id
        ).exists():
            return Response(
                {
                    "detail": (
                        "La organización no existe."
                    )
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        return super().list(
            request,
            *args,
            **kwargs,
        )
