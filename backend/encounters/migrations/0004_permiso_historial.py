"""US-25 — El permiso explícito para leer el historial longitudinal.

Lo reciben el Médico, para ver los encuentros previos de quien atiende, y el
Paciente, para ver los suyos y los de sus dependientes. Ni el administrador
ni recepción: la historia clínica no es suya. Y el permiso solo no abre nada:
hace falta además un alcance sobre el paciente (`services.history_scope`).
"""

from django.db import migrations

PERMISSION = ("encounters.history.read", "encounters",
              "Consultar el historial clínico longitudinal")
GRANTS = {"practitioner", "patient"}

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
    templates = {r.code: r for r in Role.objects.filter(
        organization__isnull=True, is_system=True)}
    _grant(RolePermission, templates, permission, None)

    for organization_id in list(Organization.objects.values_list("id", flat=True)):
        schema_editor.execute(PLATFORM_OFF)
        schema_editor.execute(
            "SELECT set_config('app.tenant_id', %s, true)", [str(organization_id)],
        )
        clones = {r.code: r for r in Role.objects.filter(organization_id=organization_id)}
        _grant(RolePermission, clones, permission, organization_id)

    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")
    schema_editor.execute(PLATFORM_ON)


def unseed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(code=PERMISSION[0]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("encounters", "0003_seed_permissions"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
