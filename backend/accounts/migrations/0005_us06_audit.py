"""US-06 — Lo que la bitácora necesita de la base: una columna y un permiso.

Va en ``accounts`` y no en ``audit`` porque ahí viven las dos tablas que toca:
``audit_log`` y ``permissions``. La app ``audit`` no declara modelos —lee los de
al lado—, así que no tiene ni carpeta de migraciones.

**Una sola migración para las dos cosas.** Es el mismo criterio de
``0003_seed_permissions_sprint_1``: la regla 5 del reparto dice que la base
compartida se toca lo menos posible, y el modelo del Sprint 0 ya está aplicado
en local y en Supabase.

Tres cosas hace:

1. **Agrega ``audit_log.user_agent``.** El punto (b) pide "desde qué dirección
   IP y con qué agente"; la IP ya estaba, el agente no. Es una columna nueva
   con valor por omisión, así que no reescribe las filas ya cargadas.

2. **Crea el permiso ``audit.log.read``** (punto h) y se lo da al Administrador
   de Organización, en la plantilla y en las copias de las organizaciones ya
   dadas de alta. Al Médico y a la Recepcionista **no**: la bitácora dice quién
   miró qué historia clínica, y darle eso a quien puede aparecer registrado en
   ella invita a que la primera consulta sea la propia.

3. **Borra ``users.audit.read``**, que el catálogo del Sprint 0 declaró antes
   de que existiera esta app. Nunca autorizó nada —no hay una sola vista que lo
   consulte— y dejarlo sería peor que borrarlo: un permiso que dice "Consultar
   la bitácora de auditoría" y no consulta nada es una trampa para el próximo
   que arme un rol.

**La clave primaria sigue siendo ``bigserial``.** El punto (d) pide UUID
generado en Python, con el argumento de ``login_attempts``: una tabla de sólo
inserción bajo RLS, donde ``INSERT ... RETURNING`` exigiría abrir también la
política de lectura. En ``audit_log`` ese argumento no se sostiene: su política
``tenant_isolation`` **sí** deja leer los asientos de la propia organización
—es exactamente lo que hace el punto (e)—, así que el RETURNING pasa y la
inserción funciona. Cambiar el tipo de la clave primaria de una tabla con datos
en dos bases distintas, para resolver un problema que no se tiene, es
justamente lo que la regla 5 pide no hacer. Queda anotado en
``docs/registro-de-defectos.md``.
"""

from django.db import migrations, models

NEW_PERMISSIONS = [
    ("audit.log.read", "audit", "Consultar la bitácora de auditoría"),
]

# El código que reemplaza. Ver el punto 3 del docstring.
SUPERSEDED = ["users.audit.read"]

# Sólo el Administrador de Organización. La plantilla del Superadministrador no
# recibe nada: no lee la bitácora de ningún inquilino, y su política RLS
# tampoco se lo permitiría.
GRANTS = {
    "org_admin": {code for code, _module, _description in NEW_PERMISSIONS},
}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _set_tenant(schema_editor, organization_id):
    """Regla 4 del reparto: fuera del ciclo HTTP hay que fijar el contexto.

    Sin esto ``role_permissions`` devuelve cero filas y el INSERT lo rechaza
    ``tenant_isolation``.
    """
    schema_editor.execute(PLATFORM_OFF)
    schema_editor.execute(
        "SELECT set_config('app.tenant_id', %s, true)", [str(organization_id)],
    )


def _grant(RolePermission, roles, permissions, organization_id):
    for code, granted_codes in GRANTS.items():
        role = roles.get(code)
        if role is None or not granted_codes:
            continue

        already = set(
            RolePermission.objects
            .filter(role=role)
            .values_list("permission__code", flat=True)
        )
        RolePermission.objects.bulk_create([
            RolePermission(
                role=role,
                permission=permissions[permission_code],
                organization_id=organization_id,
            )
            for permission_code in sorted(granted_codes - already)
        ])


def seed(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    schema_editor.execute(PLATFORM_ON)

    for code, module, description in NEW_PERMISSIONS:
        Permission.objects.update_or_create(
            code=code, defaults={"module": module, "description": description},
        )

    permissions = {
        permission.code: permission for permission in Permission.objects.all()
    }

    templates = {
        role.code: role
        for role in Role.objects.filter(organization__isnull=True, is_system=True)
    }
    _grant(RolePermission, templates, permissions, organization_id=None)

    # Las organizaciones ya dadas de alta tienen sus propias copias de las
    # plantillas, y son ésas las que consulta `has_permission`. Sin este
    # recorrido, el administrador de Kolping no podría abrir la bitácora hasta
    # que alguien le diera el permiso a mano.
    for organization_id in list(Organization.objects.values_list("id", flat=True)):
        _set_tenant(schema_editor, organization_id)
        clones = {
            role.code: role
            for role in Role.objects.filter(organization_id=organization_id)
        }
        _grant(RolePermission, clones, permissions, organization_id=organization_id)

    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")
    schema_editor.execute(PLATFORM_ON)

    # Borrar la fila de `permissions` arrastra sus `role_permissions` por la
    # clave foránea. Va al final: si fallara algo de arriba, el catálogo queda
    # con el permiso viejo, que es el estado en el que estaba.
    Permission.objects.filter(code__in=SUPERSEDED).delete()


def unseed(apps, schema_editor):
    """Devuelve el catálogo a como estaba: sin `audit.log.read` y con el
    `users.audit.read` que este proyecto nunca llegó a usar."""
    Permission = apps.get_model("accounts", "Permission")

    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(
        code__in=[code for code, _module, _description in NEW_PERMISSIONS],
    ).delete()
    Permission.objects.update_or_create(
        code="users.audit.read",
        defaults={"module": "users",
                  "description": "Consultar la bitácora de auditoría"},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_password_reset_token"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="auditlog",
            name="user_agent",
            field=models.CharField(blank=True, default="", max_length=300),
        ),
        migrations.RunPython(seed, unseed),
    ]
