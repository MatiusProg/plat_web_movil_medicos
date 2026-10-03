"""Qué permite el plan de una organización.

Hasta acá los planes (`SubscriptionPlan`) declaraban límites y funciones
—`max_users`, `ai_chatbot`, `report_export`…— que ningún código consultaba.
Este módulo es el punto único donde se pregunta "¿qué permite el plan de esta
organización?". La primera regla que lo usa es la frecuencia de las copias de
seguridad (característica general 6); el resto de los límites puede colgarse
de acá sin repetir cómo se busca el plan vigente.

**La suscripción es una tabla de plataforma** (`subscriptions` tiene RLS de
alcance plataforma): un inquilino no la lee. Por eso se consulta dentro de
`platform_admin_context`, que restaura el contexto del inquilino al salir.
"""

from django.utils import timezone

from .context import platform_admin_context
from .models import Subscription


def current_plan(organization):
    """El plan de la suscripción vigente, o ``None`` si no tiene ninguna."""
    if organization is None:
        return None
    hoy = timezone.localdate()
    with platform_admin_context():
        suscripcion = (
            Subscription.objects
            .filter(organization_id=organization.id,
                    status=Subscription.Status.ACTIVE, starts_at__lte=hoy)
            .exclude(ends_at__lt=hoy)
            .select_related("plan")
            .order_by("-starts_at")
            .first()
        )
    return suscripcion.plan if suscripcion else None
