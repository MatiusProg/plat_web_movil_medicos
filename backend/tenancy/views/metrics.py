"""Vistas de la app `tenancy`.

US-45 — Panel del superadministrador de plataforma: métricas globales de
todas las organizaciones activas (tenants, uso por plan, alertas de
aislamiento).

No hace falta envolver estas vistas en ``platform_admin_context()``: cuando el
token lleva ``is_platform_admin``, ``TenantJWTAuthentication`` ya fija ese
contexto antes de que la vista se ejecute. Ver ``accounts/authentication.py``.
"""

from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from ..models import IsolationAlert, Organization, Subscription
from ..permissions import IsPlatformAdmin
from ..serializers.metrics import IsolationAlertSerializer


@api_view(["GET"])
@permission_classes([IsPlatformAdmin])
def dashboard(request):
    """US-45 — Resumen de salud operativa de la plataforma.

    Tres secciones: cuántas organizaciones hay por estado, cuántas
    suscripciones vigentes hay por plan, y cuántas alertas de aislamiento
    están pendientes.
    """
    org_counts = Organization.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status=Organization.Status.ACTIVE)),
        suspended=Count("id", filter=Q(status=Organization.Status.SUSPENDED)),
        inactive=Count("id", filter=Q(status=Organization.Status.INACTIVE)),
    )

    by_plan = list(
        Subscription.objects.filter(ends_at__isnull=True)
        .values("plan__code", "plan__name")
        .annotate(count=Count("id"))
        .order_by("plan__name")
    )
    by_plan = [
        {
            "plan_code": row["plan__code"],
            "plan_name": row["plan__name"],
            "count": row["count"],
        }
        for row in by_plan
    ]

    alert_counts = IsolationAlert.objects.aggregate(
        pending=Count(
            "id", filter=Q(status=IsolationAlert.Status.PENDING),
        ),
        critical_pending=Count(
            "id",
            filter=Q(
                status=IsolationAlert.Status.PENDING,
                severity=IsolationAlert.Severity.CRITICAL,
            ),
        ),
    )

    return Response({
        "organizations": org_counts,
        "by_plan": by_plan,
        "alerts": alert_counts,
    })


class IsolationAlertViewSet(ReadOnlyModelViewSet):
    """US-45 — Sólo lectura: las alertas las genera el sistema, no se crean a mano.

    Filtros por query param: ``?status=pending`` y/o ``?severity=critical``.
    """

    serializer_class = IsolationAlertSerializer
    permission_classes = [IsPlatformAdmin]
    queryset = IsolationAlert.objects.select_related(
        "source_organization", "target_organization",
    )

    def get_queryset(self):
        queryset = super().get_queryset()
        status_param = self.request.query_params.get("status")
        if status_param:
            queryset = queryset.filter(status=status_param)
        severity_param = self.request.query_params.get("severity")
        if severity_param:
            queryset = queryset.filter(severity=severity_param)
        return queryset
