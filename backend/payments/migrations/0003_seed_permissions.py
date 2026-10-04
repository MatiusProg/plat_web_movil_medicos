"""US-18 y US-21 — Permisos del pago y de la confirmación de asistencia.

Mismo mecanismo que `encounters/0003_seed_permissions.py`: el permiso entra al
catálogo y se reparte a las plantillas **y** a las copias de rol que cada
organización ya tiene.

- `payments.payment.create` — abrir el checkout. Lo tiene el **Paciente**:
  paga su ficha o la de un dependiente.
- `appointments.appointment.confirm_attendance` — US-21, también del
  Paciente. Vive en este archivo y no en `appointments` para sembrar los
  permisos del sprint de Alexander en un solo lugar.
"""

from django.db import migrations

PERMISSIONS = [
    ("payments.payment.create", "payments",
     "Pagar en línea una ficha propia o de un dependiente"),
    ("appointments.appointment.confirm_attendance", "appointments",
     "Confirmar la asistencia a una ficha propia"),
]

GRANTS = {
    "org_admin": set(),
    "receptionist": set(),
    "patient": {code for code, _, _ in PERMISSIONS},
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
        ("payments", "0002_rls_policies"),
        ("accounts", "0007_user_roles_con_orden"),
        ("tenancy", "0003_seed_catalog"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
