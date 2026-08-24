"""Lógica de negocio de `tenancy` que no entra en una vista.

US-43 — Alta de una organización. No está acá por prolijidad: el alta **cruza
dos contextos de aislamiento** dentro de una sola transacción, y eso no se
puede escribir dentro de un serializer sin que se vuelva ilegible.

Qué contexto exige cada paso, y por qué:

    organizations, subscriptions   plataforma   sus políticas son
                                                platform_admin_all
    plantillas de rol (leer)       cualquiera   system_templates_read
    roles y permisos clonados      INQUILINO    tenant_isolation compara
    usuario administrador                       organization_id contra
    user_roles                                  app_current_tenant()
    audit_log (organization NULL)  plataforma   sólo el superadmin escribe
                                                filas de nivel plataforma

O sea que el servicio alterna: plataforma → inquilino → plataforma. Los
gestores de ``tenancy.context`` guardan el valor anterior y lo restauran al
salir, así que anidarlos dentro de la transacción exterior es seguro; lo que
no se puede es fijar el contexto a mano con ``set_context`` y confiar en que
alguien lo devuelva a su lugar. Ver la decisión D-06 en el registro de
defectos.
"""

from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from accounts.models import AuditLog, Role, RolePermission, User, UserRole

from .context import platform_admin_context, tenant_context
from .models import Organization, Subscription

# El rol de plataforma no se clona: pertenece al superadministrador, que no
# vive dentro de ninguna organización. Se clonan las otras cuatro plantillas.
PLATFORM_ROLE_CODE = "platform_admin"

# El rol que recibe el primer usuario de la organización.
ADMIN_ROLE_CODE = "org_admin"

# Sin ambigüedades a la vista: la contraseña se dicta por teléfono o se copia
# de un correo, así que fuera I, l, 1, O y 0.
PASSWORD_ALPHABET = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PASSWORD_LENGTH = 14


def generate_temporary_password() -> str:
    """Contraseña de un solo uso para el administrador recién creado.

    Se devuelve **una vez** en la respuesta del alta y no se guarda en ningún
    lado en claro: en la base queda sólo su hash. Si se pierde, se resuelve
    por el flujo de recuperación (US-03), no consultándola.
    """
    return get_random_string(PASSWORD_LENGTH, PASSWORD_ALPHABET)


def _clone_system_roles(organization):
    """Copia las plantillas de rol del sistema dentro de la organización.

    Las plantillas viven a nivel plataforma (``organization`` NULL) y las lee
    cualquier contexto gracias a la política ``system_templates_read``. Las
    copias, en cambio, se insertan bajo el contexto del inquilino, que es lo
    que exige ``tenant_isolation``.

    Van con ``is_system=False``, y no es un detalle estético: el CHECK
    ``ck_role_system`` dice ``NOT is_system OR organization_id IS NULL``, así
    que copiar la plantilla tal cual —con su ``is_system=True``— hace fallar
    el INSERT. La copia es del inquilino y su administrador puede ajustarle
    los permisos (RF-W-02); la plantilla es del sistema y nadie la toca.

    Devuelve las copias indexadas por código.
    """
    templates = (
        Role.objects.filter(organization__isnull=True, is_system=True)
        .exclude(code=PLATFORM_ROLE_CODE)
        .prefetch_related("role_permissions")
    )

    clones = {}
    for template in templates:
        clone = Role.objects.create(
            organization=organization,
            code=template.code,
            name=template.name,
            description=template.description,
            is_system=False,
            is_active=True,
        )
        RolePermission.objects.bulk_create([
            RolePermission(
                role=clone,
                permission_id=granted.permission_id,
                organization=organization,
            )
            for granted in template.role_permissions.all()
        ])
        clones[clone.code] = clone

    return clones


def create_organization(*, organization_data, admin_data, plan, created_by):
    """Da de alta una organización y la deja lista para usarse. US-43.

    En una sola transacción crea la organización, su suscripción al plan
    elegido, las plantillas de rol clonadas dentro del inquilino, el primer
    usuario administrador con su rol, y la entrada de auditoría a nivel
    plataforma.

    El usuario administrador es lo que convierte a la organización en un
    inquilino **utilizable**: sin él, el alta deja un centro médico al que
    nadie puede entrar, y ninguna otra historia del backlog crea esa primera
    cuenta.

    Devuelve ``(organization, admin_user, temporary_password)``. La
    contraseña vuelve en claro una única vez, para que el superadministrador
    se la entregue a su cliente; después sólo existe su hash.
    """
    temporary_password = generate_temporary_password()

    with transaction.atomic():
        # ---- Nivel plataforma: la organización y su suscripción -----------
        with platform_admin_context():
            organization = Organization.objects.create(**organization_data)
            Subscription.objects.create(
                organization=organization,
                plan=plan,
                # localdate() y no date.today(): la fecha del servidor puede
                # ser la de mañana. Ver `docs/entorno/` sobre la zona horaria.
                starts_at=timezone.localdate(),
                status=Subscription.Status.ACTIVE,
                change_reason="Alta de la organización",
                assigned_by=created_by,
            )

        # ---- Nivel inquilino: roles, administrador y su asignación --------
        with tenant_context(organization.id):
            roles = _clone_system_roles(organization)

            admin_user = User.objects.create_user(
                organization=organization,
                password=temporary_password,
                **admin_data,
            )

            # Sin rol, el administrador no puede hacer nada y la
            # organizacion nace rota. Que falte la plantilla significa que la
            # migracion semilla no corrio o que alguien borro el catalogo del
            # sistema: no es algo que el superadministrador pueda arreglar
            # cambiando el formulario, asi que revienta fuerte y la
            # transaccion entera se deshace.
            if ADMIN_ROLE_CODE not in roles:
                raise ImproperlyConfigured(
                    f"No existe la plantilla de rol '{ADMIN_ROLE_CODE}'. "
                    "Sin ella la organizacion queda sin administrador: "
                    "revisar la migracion tenancy/0003_seed_catalog."
                )
            UserRole.objects.create(
                user=admin_user,
                role=roles[ADMIN_ROLE_CODE],
                organization=organization,
                assigned_by=created_by,
            )

        # ---- Nivel plataforma otra vez: la bitácora -----------------------
        # organization=None a propósito: es una acción del superadministrador
        # sobre la plataforma, no de la organización sobre sí misma. Con el
        # organization_id puesto, quien la audita no podría leerla nunca.
        with platform_admin_context():
            AuditLog.objects.create(
                organization=None,
                user=created_by,
                action="organization.create",
                entity="organizations",
                entity_id=str(organization.id),
                detail={
                    "slug": organization.slug,
                    "name": organization.name,
                    "tax_id": organization.tax_id,
                    "plan": plan.code,
                    "admin_email": admin_user.email,
                    "cloned_roles": sorted(roles),
                },
            )

    return organization, admin_user, temporary_password
