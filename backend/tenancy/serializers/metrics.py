"""Serializers de la app `tenancy`."""

from rest_framework import serializers

from ..models import IsolationAlert


class IsolationAlertSerializer(serializers.ModelSerializer):
    """US-45 — Alertas de aislamiento para el panel del superadministrador."""

    source_organization_name = serializers.CharField(
        source="source_organization.name", read_only=True, default=None,
    )
    target_organization_name = serializers.CharField(
        source="target_organization.name", read_only=True, default=None,
    )

    class Meta:
        model = IsolationAlert
        fields = [
            "id",
            "alert_type",
            "severity",
            "status",
            "description",
            "endpoint",
            "http_method",
            "ip_address",
            "detail",
            "source_organization",
            "source_organization_name",
            "target_organization",
            "target_organization_name",
            "occurred_at",
            "resolved_at",
            "resolution_note",
        ]
        read_only_fields = fields
