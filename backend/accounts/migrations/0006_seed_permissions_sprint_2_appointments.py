"""US-17/US-20 — Permisos de fichas.

Mismo patrón que ``accounts/migrations/0003_seed_permissions_sprint_1``: se
declara el catálogo nuevo una sola vez y se propaga a las plantillas del
sistema **y** a las copias que ya tiene cada organización dada de alta, porque
esas copias no se enteran solas de un permiso nuevo.

**Quién recibe qué.** El rol *Paciente* es quien reserva y cancela sobre sí
mismo y sus dependientes (US-17, US-20): recibe `create`, `read`, `cancel` y
`reschedule` —reprogramar en la propia historia es liberar y volver a tomar,
la misma acción que reservar—. El personal de mostrador (`receptionist`) y el
administrador de la organización sólo reciben `read`: consultar fichas de la
organización, por ejemplo para el check-in de US-22. Reservar o cancelar
**por** un paciente desde el mostrador es US-23 (agendamiento asistido), que
todavía no entra: no tiene sentido darles el verbo antes de que exista la
pantalla que lo use, y el permiso de más quedaría sin ninguna interfaz que lo
frene si alguien lo llamara directo a la API.
"""

from django.db import migrations

NEW_PERMISSIONS = [
    ("appointments.appointment.create", "appointments", "Reservar una ficha"),
    ("appointments.appointment.read", "appointments", "Consultar fichas"),
    ("appointments.appointment.cancel", "appointments", "Cancelar una ficha"),
    ("appointments.appointment.reschedule", "appointments",
     "Reprogramar una ficha"),
]

GRANTS = {
    "org_admin": {
        "appointments.appointment.read",
    },
    "practitioner": set(),
    "receptionist": {
        "appointments.appointment.read",
    },
    "patient": {
        "appointments.appointment.create",
        "appointments.appointment.read",
        "appointments.appointment.cancel",
        "appointments.appointment.reschedule",
    },
    "platform_admin": set(),
}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _set_tenant(schema_editor, organization_id):
    schema_editor.execute(PLATFORM_OFF)
    schema_editor.execute(
        "SELECT set_config('app.tenant_id', %s, true)", [str(organization_id)],
    )


def _clear_tenant(schema_editor):
    schema_editor.execute("SELECT set_config('app.tenant_id', '', true)")


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
                role=role, permission=permissions[permission_code],
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
        permission.code: permission
        for permission in Permission.objects.filter(
            code__in=[code for code, _m, _d in NEW_PERMISSIONS],
        )
    }

    templates = {
        role.code: role
        for role in Role.objects.filter(organization__isnull=True, is_system=True)
    }
    _grant(RolePermission, templates, permissions, organization_id=None)

    organization_ids = list(Organization.objects.values_list("id", flat=True))
    for organization_id in organization_ids:
        _set_tenant(schema_editor, organization_id)
        clones = {
            role.code: role
            for role in Role.objects.filter(organization_id=organization_id)
        }
        _grant(RolePermission, clones, permissions, organization_id=organization_id)

    _clear_tenant(schema_editor)
    schema_editor.execute(PLATFORM_ON)


def unseed(apps, schema_editor):
    Permission = apps.get_model("accounts", "Permission")
    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(
        code__in=[code for code, _module, _description in NEW_PERMISSIONS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_us06_audit"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
