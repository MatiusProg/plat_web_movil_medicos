"""US-42 — El permiso para validar los textos generados.

Mismo mecanismo que `encounters/0003_seed_permissions.py`: el permiso entra
al catálogo y se reparte a las plantillas **y** a las copias de rol que cada
organización ya tiene.

**Sólo el rol Médico lo recibe**, y el permiso solo no alcanza: además hay que
ser el médico de la atención de la que sale el texto (ver `ai/services.py`).
El paciente no necesita uno nuevo: lee sus textos aprobados con el permiso
del historial (`encounters.history.read`), como lee sus atenciones.
"""

from django.db import migrations

PERMISSION = ("ai.text.review", "ai",
              "Validar, editar o descartar los textos generados por IA")
GRANTS = {"practitioner"}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _grant(RolePermission, roles, permission, organization_id):
    for code in GRANTS:
        role = roles.get(code)
        if role is not None and not RolePermission.objects.filter(
            role=role, permission=permission,
        ).exists():
            RolePermission.objects.create(
                role=role, permission=permission, organization_id=organization_id,
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
        schema_editor.execute(PLATFORM_OFF)
        schema_editor.execute(
            "SELECT set_config('app.tenant_id', %s, true)", [str(organization_id)],
        )
        clones = {
            role.code: role
            for role in Role.objects.filter(organization_id=organization_id)
        }
        _grant(RolePermission, clones, permission, organization_id=organization_id)

    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")
    schema_editor.execute(PLATFORM_ON)


def unseed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(code=PERMISSION[0]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0002_rls_e_inmutabilidad"),
        ("encounters", "0004_permiso_historial"),
        ("accounts", "0003_seed_permissions_sprint_1"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
