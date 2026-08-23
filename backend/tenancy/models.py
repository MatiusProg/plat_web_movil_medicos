"""Nivel plataforma: el registro de los inquilinos y su suscripción.

Estas tablas NO llevan ``organization_id``: son el registro de las
organizaciones, no un dato de una organización. El detalle está en la
decisión D-2 de ``docs/modelo-datos/sprint-0.md``.
"""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models


class SubscriptionPlan(models.Model):
    """US-44 — Planes Básico, Pro y Premium."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True, default="")
    monthly_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(max_length=3, default="BOB")

    # Límites cuantitativos. NULL = ilimitado. Se comparan contra UsageMetric
    # para el panel de US-45; por eso son columnas y no claves del JSON.
    max_branches = models.PositiveIntegerField(null=True, blank=True)
    max_users = models.PositiveIntegerField(null=True, blank=True)
    max_practitioners = models.PositiveIntegerField(null=True, blank=True)
    max_appointments_month = models.PositiveIntegerField(null=True, blank=True)
    max_ai_queries_month = models.PositiveIntegerField(null=True, blank=True)
    storage_mb = models.PositiveIntegerField(null=True, blank=True)

    # Interruptores por funcionalidad. Agregar una no debe requerir migración.
    features = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "subscription_plans"
        verbose_name = "plan de suscripción"
        verbose_name_plural = "planes de suscripción"
        ordering = ["monthly_price"]

    def __str__(self):
        return self.name

    def allows(self, feature: str) -> bool:
        """Si el plan habilita una funcionalidad. Ausente = no habilitada."""
        return bool(self.features.get(feature, False))


class Organization(models.Model):
    """US-43 — El inquilino. Su ``id`` es lo que viaja en ``app.tenant_id``."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        SUSPENDED = "suspended", "Suspendida"
        INACTIVE = "inactive", "Inactiva"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Identificador corto y estable: es lo que resuelve el inquilino en el
    # formulario de login, ANTES de autenticar. Ver decisión D-5.
    slug = models.SlugField(
        max_length=40, unique=True,
        validators=[RegexValidator(
            r"^[a-z0-9]([a-z0-9-]{1,38}[a-z0-9])$",
            "Sólo minúsculas, números y guiones; entre 3 y 40 caracteres.",
        )],
    )

    name = models.CharField(max_length=120)
    legal_name = models.CharField(max_length=160)
    tax_id = models.CharField("NIT", max_length=20, unique=True)

    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=30, blank=True, default="")
    address = models.CharField(max_length=200, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    country = models.CharField(max_length=2, default="BO")

    logo_url = models.URLField(max_length=300, blank=True, default="")
    primary_color = models.CharField(max_length=7, default="#0F766E")
    secondary_color = models.CharField(max_length=7, default="#134E4A")

    # Las agendas, los recordatorios y la ventana de cancelación se calculan
    # en la hora local de la organización, no la del servidor.
    timezone = models.CharField(max_length=40, default="America/La_Paz")

    status = models.CharField(max_length=12, choices=Status, default=Status.ACTIVE)
    onboarded_at = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "organizations"
        verbose_name = "organización"
        verbose_name_plural = "organizaciones"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=["active", "suspended", "inactive"]),
                name="ck_organization_status",
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def current_subscription(self):
        """La suscripción vigente. Hay a lo sumo una, garantizado en la base."""
        return self.subscriptions.filter(ends_at__isnull=True).select_related("plan").first()


class Subscription(models.Model):
    """US-44 — Historial de planes por organización.

    Es una tabla y no un ``plan_id`` dentro de Organization porque US-45 pide
    "uso por plan", y sin fechas eso no se puede reconstruir (decisión D-7).
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Activa"
        CANCELLED = "cancelled", "Cancelada"
        EXPIRED = "expired", "Vencida"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.PROTECT, related_name="subscriptions",
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions",
    )
    starts_at = models.DateField()
    ends_at = models.DateField(null=True, blank=True)  # NULL = vigente
    status = models.CharField(max_length=12, choices=Status, default=Status.ACTIVE)
    change_reason = models.CharField(max_length=200, blank=True, default="")
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="assigned_subscriptions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "subscriptions"
        verbose_name = "suscripción"
        verbose_name_plural = "suscripciones"
        ordering = ["-starts_at"]
        constraints = [
            # Una sola suscripción vigente por organización, garantizado por
            # la base y no por la aplicación.
            models.UniqueConstraint(
                fields=["organization"], condition=models.Q(ends_at__isnull=True),
                name="uq_subscription_active",
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__isnull=True)
                | models.Q(ends_at__gte=models.F("starts_at")),
                name="ck_subscription_period",
            ),
        ]

    def __str__(self):
        return f"{self.organization} · {self.plan}"


class UsageMetric(models.Model):
    """US-45 — Instantáneas precalculadas del consumo de cada inquilino.

    El panel del superadministrador se alimenta de acá y NO cuenta filas en
    vivo sobre las tablas de los inquilinos: no puede (ver R-2) y no
    escalaría. Una tarea programada las calcula recorriendo organización por
    organización.
    """

    class Granularity(models.TextChoices):
        DAY = "day", "Diaria"
        MONTH = "month", "Mensual"

    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="usage_metrics",
    )
    # Sólo se valida el formato, no una lista cerrada: cada sprint agrega
    # métricas y una lista fija obligaría a un ALTER en la base compartida.
    metric_code = models.CharField(
        max_length=40,
        validators=[RegexValidator(r"^[a-z][a-z0-9_]{2,39}$")],
    )
    granularity = models.CharField(
        max_length=10, choices=Granularity, default=Granularity.DAY,
    )
    period_start = models.DateField()
    value = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "usage_metrics"
        verbose_name = "métrica de uso"
        verbose_name_plural = "métricas de uso"
        ordering = ["-period_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "metric_code", "granularity", "period_start"],
                name="uq_usage_metric",
            ),
        ]
        indexes = [
            models.Index(fields=["-period_start", "metric_code"],
                         name="ix_usage_metrics_period"),
        ]

    def __str__(self):
        return f"{self.metric_code}={self.value} ({self.period_start})"


class IsolationAlert(models.Model):
    """US-45 — Alertas de aislamiento entre inquilinos.

    Cualquier contexto puede INSERTAR (lo hace el middleware, que en ese
    momento está en el contexto de un inquilino cualquiera). Leer y resolver
    es exclusivo del superadministrador. Ver la política ``anyone_reports``.
    """

    # Clave UUID generada en Python, no bigserial: ver la nota de
    # accounts.LoginAttempt. `INSERT ... RETURNING` sobre un buzón de sólo
    # escritura falla, porque RETURNING exige pasar también la política de
    # SELECT.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class AlertType(models.TextChoices):
        CROSS_TENANT = "cross_tenant_access", "Acceso cruzado entre inquilinos"
        NO_CONTEXT = "missing_tenant_context", "Petición sin contexto de inquilino"
        JWT_MISMATCH = "jwt_tenant_mismatch", "El token no coincide con el inquilino"
        RLS_DENIED = "rls_denied", "Rechazado por Row Level Security"
        PLAN_LIMIT = "plan_limit_exceeded", "Límite del plan superado"

    class Severity(models.TextChoices):
        LOW = "low", "Baja"
        MEDIUM = "medium", "Media"
        HIGH = "high", "Alta"
        CRITICAL = "critical", "Crítica"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        REVIEWING = "reviewing", "En revisión"
        RESOLVED = "resolved", "Resuelta"
        DISMISSED = "dismissed", "Descartada"

    source_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="isolation_alerts_raised",
    )
    target_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="isolation_alerts_targeted",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="isolation_alerts",
    )

    alert_type = models.CharField(max_length=40, choices=AlertType)
    severity = models.CharField(max_length=10, choices=Severity)
    description = models.CharField(max_length=300)
    endpoint = models.CharField(max_length=200, blank=True, default="")
    http_method = models.CharField(max_length=10, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    detail = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=12, choices=Status, default=Status.PENDING)
    occurred_at = models.DateTimeField(auto_now_add=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="resolved_isolation_alerts",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_note = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        db_table = "isolation_alerts"
        verbose_name = "alerta de aislamiento"
        verbose_name_plural = "alertas de aislamiento"
        ordering = ["-occurred_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(status__in=["resolved", "dismissed"],
                             resolved_at__isnull=False)
                    | (~models.Q(status__in=["resolved", "dismissed"])
                       & models.Q(resolved_at__isnull=True))
                ),
                name="ck_alert_resolution",
            ),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.get_alert_type_display()}"
