"""Da de alta el permiso del asistente y se lo reparte a los roles.

Mismo mecanismo que `accounts/migrations/0003_seed_permissions_sprint_1.py`,
al que conviene ir a leer antes de tocar esto: el catálogo de permisos no
tiene RLS pero las plantillas de rol sí, y las copias que cada organización se
llevó al darse de alta son las que consulta `has_permission()`. Sembrar sólo
las plantillas dejaría el permiso sin efecto para todas las organizaciones que
ya existen, que en este proyecto son todas.

**Quién lo recibe.** El paciente, obviamente, porque el asistente es suyo. Y
recepción, porque el mostrador va a querer preguntarle al asistente a qué
especialidad mandar a alguien que llega sin saber —es el caso de US-23—. El
profesional no: no orienta, atiende. El superadministrador tampoco, por la
misma razón de alcance por la que no ve datos de ninguna organización.
"""

from django.db import migrations

PERMISSION = (
    "assistant.suggest.use",
    "assistant",
    "Consultar al asistente de orientación",
)

GRANTS = {
    "org_admin": {PERMISSION[0]},
    "receptionist": {PERMISSION[0]},
    "patient": {PERMISSION[0]},
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


def _grant(RolePermission, roles, permission, organization_id):
    for code, granted in GRANTS.items():
        role = roles.get(code)
        if role is None or not granted:
            continue
        ya_lo_tiene = RolePermission.objects.filter(
            role=role, permission=permission,
        ).exists()
        if not ya_lo_tiene:
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

    code, module, description = PERMISSION
    permission, _ = Permission.objects.update_or_create(
        code=code, defaults={"module": module, "description": description},
    )

    templates = {
        role.code: role
        for role in Role.objects.filter(organization__isnull=True, is_system=True)
    }
    _grant(RolePermission, templates, permission, organization_id=None)

    for organization_id in list(Organization.objects.values_list("id", flat=True)):
        _set_tenant(schema_editor, organization_id)
        clones = {
            role.code: role
            for role in Role.objects.filter(organization_id=organization_id)
        }
        _grant(RolePermission, clones, permission, organization_id=organization_id)

    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")
    schema_editor.execute(PLATFORM_ON)


def unseed(apps, schema_editor):
    """Borrar la fila del catálogo arrastra sus role_permissions por la FK."""
    Permission = apps.get_model("accounts", "Permission")
    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(code=PERMISSION[0]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0002_rls_policies"),
        ("accounts", "0003_seed_permissions_sprint_1"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
