"""Lo que promete el plan, se cumple. Regla fundamental del repositorio.

Hasta el 03/10/26 los planes (`SubscriptionPlan`) declaraban límites y
funciones —`max_users`, `ai_chatbot`, `report_export`…— que **ningún código
consultaba**: un plan Básico podía usar todo lo de un Premium. Este módulo es
el único lugar donde se pregunta "¿qué permite el plan de esta
organización?", y ``PLAN_RULES`` dice dónde se hace cumplir cada cosa.

**La regla**: todo límite o función que un plan declare se hace cumplir en el
backend. ``tests/test_planes.py`` falla si alguien agrega un campo ``max_*``
o una función a un plan sin registrarla acá. Ver la Definición de Terminado
en ``CONTRIBUTING.md``.

Tres decisiones:

- **Lo que ya existe no se borra ni se bloquea.** Una organización que ya pasa
  un límite —porque bajó de plan, o porque se sembró antes de que existiera
  esta regla— conserva lo que tiene: sólo no puede crear más.
- **Los pacientes son usuarios, pero no cuentan para el límite del plan.**
  ``max_users`` es el personal: quien tiene algún rol que no es Paciente. Un
  centro médico Básico no puede tener quince pacientes.
- **Sin plan vigente, no hay nada habilitado**: no hay contrato que diga
  cuánto le toca.

**La suscripción es una tabla de plataforma** (RLS de alcance plataforma): un
inquilino no la lee. Por eso se consulta dentro de ``platform_admin_context``,
que restaura el contexto del inquilino al salir.
"""

import datetime as dt

from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from .context import platform_admin_context
from .models import Subscription

# Dónde se hace cumplir cada cosa que un plan declara. ``tests/test_planes.py``
# exige que todo campo ``max_*``, ``storage_mb`` y toda clave de ``features``
# de los planes del sistema figure acá. ``estado``:
#   aplicado   — el backend lo hace cumplir donde dice ``donde``
#   pendiente  — la funcionalidad todavía no existe; se aplica al construirla
#   no_aplica  — el sistema no tiene lo que el campo limita (se explica)
PLAN_RULES = {
    "max_branches": ("aplicado", "catalog/branches.py · alta de sucursal"),
    "max_users": ("aplicado", "accounts/serializers/roles.py · asignar un rol de personal"),
    "max_practitioners": ("aplicado", "catalog/us12_views.py · alta de profesional"),
    "max_appointments_month": ("aplicado", "appointments/booking.py · reserva de ficha"),
    "max_ai_queries_month": ("aplicado", "assistant/views.py · consulta al asistente"),
    "ai_chatbot": ("aplicado", "assistant/views.py y reindex_views.py · asistente y reindexado"),
    "report_export": ("aplicado", "reporting/views.py · salidas CSV, Excel, HTML y PDF y envío por correo"),
    "backup_interval_hours": ("aplicado", "backups/policy.py y automatic.py · frecuencia de copias manuales y automáticas"),
    "backup_retention": ("aplicado", "backups/automatic.py · cuántas copias automáticas se conservan"),
    "noshow_prediction": ("pendiente", "predicción de inasistencia, US-35 a US-38 (Sprint 4)"),
    "ai_summaries": ("pendiente", "resúmenes por IA, US-39 a US-42 (Sprint 4)"),
    "online_payment": ("aplicado", "payments/views.py · checkout del pago en línea (US-18)"),
    "storage_mb": ("no_aplica", "el sistema no guarda archivos de la organización: "
                                "las copias manuales se descargan, y las automáticas "
                                "las limita backup_retention, no el espacio"),
}

# Rol que no cuenta como personal para ``max_users``.
PATIENT_ROLE = "patient"


class PlanLimitExceeded(APIException):
    """403 con un mensaje que dice qué permite el plan y qué hacer."""

    status_code = status.HTTP_403_FORBIDDEN
    default_code = "plan_limit"
    default_detail = "Tu plan no permite esta operación."

    def __init__(self, detail):
        # El código va en el cuerpo, como en el resto de los errores de la
        # API: es lo que la web y el móvil miran para mostrar el aviso de plan.
        super().__init__(detail={"detail": detail, "code": "plan_limit"})


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


def _sin_plan():
    return PlanLimitExceeded(
        "La organización no tiene un plan vigente: hablá con el administrador de la plataforma.",
    )


def require_feature(organization, feature, que):
    """Corta si el plan no incluye ``feature``. ``que``: "el asistente"…"""
    plan = current_plan(organization)
    if plan is None:
        raise _sin_plan()
    if not plan.allows(feature):
        raise PlanLimitExceeded(
            # "de tu centro médico": quien lee puede ser un paciente, y el plan
            # no es suyo.
            f"El plan {plan.name} de tu centro médico no incluye {que}. "
            f"Para tenerlo, el centro tiene que cambiar a un plan superior.",
        )
    return plan


def check_limit(organization, field, usados, que, singular=None):
    """Corta si ya se llegó al tope ``field`` del plan.

    ``usados`` es cuántos hay hoy; ``que`` lo nombra en plural ("sucursales
    activas") y ``singular`` para cuando el tope es 1. ``None`` en el plan es
    ilimitado.
    """
    plan = current_plan(organization)
    if plan is None:
        raise _sin_plan()
    tope = getattr(plan, field)
    if tope is not None and usados >= tope:
        raise PlanLimitExceeded(
            f"El plan {plan.name} de tu centro médico permite hasta {tope} "
            f"{singular if tope == 1 and singular else que}. "
            f"Para agregar más, el centro tiene que cambiar a un plan superior.",
        )
    return plan


# --------------------------------------------------------------------------
#  Cuánto usa hoy una organización
# --------------------------------------------------------------------------

def _inicio_de_mes():
    hoy = timezone.localdate()
    return timezone.make_aware(dt.datetime(hoy.year, hoy.month, 1))


def staff_count(organization):
    """Usuarios activos con algún rol que no es Paciente."""
    return _staff_queryset(organization).count()


def _staff_queryset(organization):
    from accounts.models import User, UserRole

    con_rol_de_personal = (
        UserRole.objects
        .filter(organization=organization, role__is_active=True)
        .exclude(role__code=PATIENT_ROLE)
        .values("user_id")
    )
    return User.objects.filter(organization=organization, is_active=True,
                               id__in=con_rol_de_personal)


def is_staff_member(organization, user):
    return _staff_queryset(organization).filter(id=user.id).exists()


def appointments_this_month(organization):
    from appointments.models import Appointment

    return Appointment.objects.filter(
        organization=organization, created_at__gte=_inicio_de_mes(),
    ).count()


def ai_queries_this_month(organization):
    """Consultas al asistente del mes: las cuenta la bitácora (US-34)."""
    from accounts.models import AuditLog
    from audit.actions import Action

    return AuditLog.objects.filter(
        organization=organization,
        action__in=[Action.ASSISTANT_QUERY, Action.ASSISTANT_EMERGENCY],
        occurred_at__gte=_inicio_de_mes(),
    ).count()
