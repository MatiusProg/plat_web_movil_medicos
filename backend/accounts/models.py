"""Usuarios, roles, permisos y auditoría.

Tres cosas que hay que tener presentes al tocar este módulo:

1. ``User.organization`` es NULL **exactamente** para el Superadministrador de
   Plataforma. Un CheckConstraint lo garantiza.
2. La autorización NO pasa por ``django.contrib.auth.Permission``: esas tablas
   no están aisladas por inquilino. Va por ``UserRole -> RolePermission``.
   Nada de ``user.has_perm()`` ni ``@permission_required``.
3. ``email`` y ``document_number`` son únicos **por organización**, no
   globales: la misma persona puede ser paciente en dos centros médicos.
"""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    """Sin ``username``: la identidad es el correo dentro de una organización."""

    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio.")
        user = self.model(email=self.normalize_email(email), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, *, organization, **extra):
        """Usuario de una organización. US-01 lo usa para el alta del paciente."""
        extra.setdefault("is_platform_admin", False)
        return self._create(email, password, organization=organization, **extra)

    def create_platform_admin(self, email, password=None, **extra):
        """Superadministrador de Plataforma: sin organización, por definición."""
        extra["is_platform_admin"] = True
        extra["organization"] = None
        return self._create(email, password, **extra)

    # Django llama a este método desde `createsuperuser`.
    def create_superuser(self, email, password=None, **extra):
        return self.create_platform_admin(email, password, **extra)


class User(AbstractBaseUser):
    """US-01 (alta) y US-02 (autenticación)."""

    class DocumentType(models.TextChoices):
        CI = "CI", "Cédula de identidad"
        PAS = "PAS", "Pasaporte"
        NIT = "NIT", "NIT"
        OTHER = "OTRO", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        null=True, blank=True, related_name="users",
        help_text="NULL sólo para el Superadministrador de Plataforma.",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="users",
    )

    email = models.EmailField(max_length=254)
    # `password` lo aporta AbstractBaseUser (hash Argon2, ver PASSWORD_HASHERS).

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    document_type = models.CharField(
        max_length=10, choices=DocumentType, default=DocumentType.CI,
    )
    document_number = models.CharField(max_length=20)
    phone = models.CharField(max_length=30, blank=True, default="")
    birth_date = models.DateField(null=True, blank=True)

    is_platform_admin = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    # RNF-07: bloqueo temporal tras 5 intentos fallidos.
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_login_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "document_number"]

    class Meta:
        db_table = "users"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email"], name="uq_user_email",
            ),
            models.UniqueConstraint(
                fields=["organization", "document_number"], name="uq_user_document",
            ),
            # UNIQUE(organization, email) no alcanza para los superadmins:
            # en una clave compuesta los NULL se consideran distintos.
            models.UniqueConstraint(
                fields=["email"], condition=models.Q(organization__isnull=True),
                name="uq_user_email_platform",
            ),
            # La necesitan las claves foráneas compuestas que apuntan a users
            # (por ejemplo patients.user), para impedir que una fila de un
            # inquilino referencie a un usuario de otro.
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_user_id_org",
            ),
            # El superadmin no pertenece a ninguna organización, y sólo él.
            models.CheckConstraint(
                condition=(
                    models.Q(is_platform_admin=True, organization__isnull=True)
                    | models.Q(is_platform_admin=False, organization__isnull=False)
                ),
                name="ck_user_scope",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_locked(self):
        """RNF-07. Se consulta antes de verificar la contraseña."""
        return self.locked_until is not None and self.locked_until > timezone.now()

    def permission_codes(self):
        """Los permisos efectivos del usuario, vía sus roles.

        Deliberadamente NO usa ``django.contrib.auth``: esas tablas no están
        aisladas por inquilino.
        """
        return set(
            Permission.objects.filter(
                role_permissions__role__user_roles__user=self,
                role_permissions__role__is_active=True,
            ).values_list("code", flat=True)
        )

    def has_permission(self, code: str) -> bool:
        return code in self.permission_codes()


class Permission(models.Model):
    """Catálogo global del sistema. Sin ``organization``: es el mismo para todos.

    Es la única tabla del modelo sin RLS, y es a propósito.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=80, unique=True,
        validators=[RegexValidator(
            r"^[a-z_]+\.[a-z_]+\.[a-z_]+$",
            "Formato: modulo.recurso.accion",
        )],
    )
    module = models.CharField(max_length=40)
    description = models.CharField(max_length=200, blank=True, default="")

    class Meta:
        db_table = "permissions"
        verbose_name = "permiso"
        verbose_name_plural = "permisos"
        ordering = ["module", "code"]

    def __str__(self):
        return self.code


class Role(models.Model):
    """US-04 — Roles administrables, no una lista fija en un ``varchar``.

    ``organization`` NULL identifica una plantilla del sistema. Al dar de alta
    una organización (US-43) se clonan las plantillas de nivel organización
    dentro del nuevo inquilino, para que su administrador pueda ajustarles los
    permisos sin afectar a los demás.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        null=True, blank=True, related_name="roles",
    )
    code = models.CharField(max_length=40)
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=200, blank=True, default="")
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "roles"
        verbose_name = "rol"
        verbose_name_plural = "roles"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "code"],
                condition=models.Q(organization__isnull=False),
                name="uq_role_code_org",
            ),
            models.UniqueConstraint(
                fields=["code"], condition=models.Q(organization__isnull=True),
                name="uq_role_code_system",
            ),
            models.CheckConstraint(
                condition=models.Q(is_system=False) | models.Q(organization__isnull=True),
                name="ck_role_system",
            ),
            # La necesitan las claves foráneas compuestas desde
            # role_permissions y user_roles: impiden que un inquilino se
            # asigne un rol de otro.
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_role_id_org",
            ),
        ]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    """Qué puede hacer cada rol.

    ``organization`` va denormalizado a propósito: toda tabla protegida por
    RLS necesita llevar el discriminador encima. Una política con subconsulta
    sería correcta, pero más lenta y mucho más difícil de probar.
    """

    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions",
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions",
    )
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        null=True, blank=True, related_name="role_permissions",
    )
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "role_permissions"
        verbose_name = "permiso de rol"
        verbose_name_plural = "permisos de rol"
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"], name="uq_role_permission",
            ),
        ]

    def __str__(self):
        return f"{self.role} → {self.permission}"


class UserRole(models.Model):
    """US-04 — Asignación de roles. Una persona puede tener más de uno."""

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="user_roles",
    )
    role = models.ForeignKey(
        Role, on_delete=models.PROTECT, related_name="user_roles",
    )
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        null=True, blank=True, related_name="user_roles",
    )
    assigned_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="role_assignments_made",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "user_roles"
        verbose_name = "rol de usuario"
        verbose_name_plural = "roles de usuario"
        constraints = [
            models.UniqueConstraint(fields=["user", "role"], name="uq_user_role"),
        ]

    def __str__(self):
        return f"{self.user} → {self.role}"


class AuditLog(models.Model):
    """US-06 (Sprint 1) y RNF-18 — Bitácora inalterable.

    La estructura existe desde el Sprint 0 porque asignar un rol (US-04) ya es
    una acción sensible. ``organization`` NULL identifica una acción de nivel
    plataforma (alta de organización, asignación de plan).

    Se inserta, nunca se modifica: ``app_user`` no tiene UPDATE ni DELETE
    sobre esta tabla.
    """

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        null=True, blank=True, related_name="audit_entries",
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="audit_entries",
    )
    action = models.CharField(max_length=60)       # 'role.assign'
    entity = models.CharField(max_length=60)       # 'user_roles'
    entity_id = models.CharField(max_length=64, blank=True, default="")
    detail = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "audit_log"
        verbose_name = "entrada de bitácora"
        verbose_name_plural = "bitácora"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["organization", "-occurred_at"],
                         name="ix_audit_log_org"),
        ]

    def __str__(self):
        return f"{self.action} · {self.occurred_at:%Y-%m-%d %H:%M}"


class LoginAttempt(models.Model):
    """US-02 y RNF-07 — Registro de intentos de inicio de sesión.

    Se escribe ANTES de saber si el usuario existe y a qué organización
    pertenece; por eso ``organization`` es opcional y la tabla nunca se filtra
    por inquilino.
    """

    # Clave UUID generada en Python, no bigserial. No es capricho: esta tabla
    # es un buzón de sólo escritura (cualquiera inserta, sólo el
    # superadministrador lee) y Django usa `INSERT ... RETURNING id` para
    # recuperar una clave autogenerada. RETURNING exige que la fila pase
    # además la política de SELECT, que acá deniega. Con la clave puesta desde
    # Python, Django hace un INSERT a secas y el buzón funciona.
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class FailureReason(models.TextChoices):
        NONE = "", "Sin fallo"
        BAD_CREDENTIALS = "bad_credentials", "Credenciales incorrectas"
        UNKNOWN_USER = "unknown_user", "Usuario inexistente"
        INACTIVE_USER = "inactive_user", "Usuario dado de baja"
        LOCKED = "locked", "Cuenta bloqueada"
        UNKNOWN_TENANT = "unknown_tenant", "Organización inexistente"
        INACTIVE_TENANT = "inactive_tenant", "Organización inactiva"

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        null=True, blank=True, related_name="login_attempts",
    )
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="login_attempts",
    )
    attempted_email = models.CharField(max_length=254)
    succeeded = models.BooleanField()
    failure_reason = models.CharField(
        max_length=40, choices=FailureReason, blank=True, default="",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True, default="")
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "login_attempts"
        verbose_name = "intento de inicio de sesión"
        verbose_name_plural = "intentos de inicio de sesión"
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["attempted_email", "-occurred_at"],
                         name="ix_login_attempts_email"),
        ]

    def __str__(self):
        estado = "éxito" if self.succeeded else self.failure_reason
        return f"{self.attempted_email} · {estado}"
