"""US-32 — Permisos del ABM de servicios y de la reindexación del asistente.

Mismo mecanismo que `assistant/migrations/0003_seed_permission.py`: el
permiso se da de alta en el catálogo y se reparte a las plantillas de rol
**y** a las copias que cada organización ya tiene, que son las que consulta
`has_permission()`.

**Quién recibe qué.** El administrador de la organización, todo: es quien
carga precios y preparaciones. Recepción lee, porque es la que atiende el
teléfono cuando alguien pregunta cuánto cuesta un estudio. La reindexación
es sólo del administrador: vuelve a calcular el índice completo del
asistente y consume cuota del proveedor.
"""

from django.db import migrations

PERMISSIONS = [
    ("catalog.service.read", "catalog", "Consultar servicios y estudios"),
    ("catalog.service.create", "catalog", "Registrar servicios y estudios"),
    ("catalog.service.update", "catalog", "Editar y desactivar servicios y estudios"),
    ("assistant.catalog.reindex", "assistant",
     "Reindexar el catálogo para el asistente"),
]

GRANTS = {
    "org_admin": {code for code, _, _ in PERMISSIONS},
    "receptionist": {"catalog.service.read"},
    "patient": set(),
    "practitioner": set(),
    "platform_admin": set(),
}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _set_tenant(schema_editor, organization_id):
    schema_editor.execute(PLATFORM_OFF)
    schema_editor.execute(
        "SELECT set_config('app.tenant_id', %s, true)", [str(organization_id)],
    )


def _grant(RolePermission, roles, permissions, organization_id):
    for code, granted in GRANTS.items():
        role = roles.get(code)
        if role is None:
            continue
        for permission in permissions:
            if permission.code not in granted:
                continue
            if not RolePermission.objects.filter(
                role=role, permission=permission,
            ).exists():
                RolePermission.objects.create(
                    role=role, permission=permission,
                    organization_id=organization_id,
                )


def seed(apps, schema_editor):
    Organization = apps.get_model("tenancy", "Organization")
    Permission = apps.get_model("accounts", "Permission")
    Role = apps.get_model("accounts", "Role")
    RolePermission = apps.get_model("accounts", "RolePermission")

    schema_editor.execute(PLATFORM_ON)

    permissions = [
        Permission.objects.update_or_create(
            code=code, defaults={"module": module, "description": description},
        )[0]
        for code, module, description in PERMISSIONS
    ]

    templates = {
        role.code: role
        for role in Role.objects.filter(organization__isnull=True, is_system=True)
    }
    _grant(RolePermission, templates, permissions, organization_id=None)

    for organization_id in list(Organization.objects.values_list("id", flat=True)):
        _set_tenant(schema_editor, organization_id)
        clones = {
            role.code: role
            for role in Role.objects.filter(organization_id=organization_id)
        }
        _grant(RolePermission, clones, permissions, organization_id=organization_id)

    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")
    schema_editor.execute(PLATFORM_ON)


def unseed(apps, schema_editor):
    """Borrar la fila del catálogo arrastra sus role_permissions por la FK."""
    Permission = apps.get_model("accounts", "Permission")
    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(code__in=[c for c, _, _ in PERMISSIONS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0006_us32_servicios_rls"),
        ("accounts", "0003_seed_permissions_sprint_1"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
