"""US-07 — Lo que los pacientes a cargo necesitan de la base.

Tres cosas:

1. **``patients.relationship``**, el parentesco del punto (a). Columna nueva con
   valor por omisión, así que no reescribe las fichas ya cargadas.

2. **``ck_patient_relationship``**, que impide las dos incoherencias posibles:
   un dependiente sin parentesco —que no dice de quién es qué— y un parentesco
   sin titular, que no significa nada. La restricción se puede agregar sobre la
   tabla con datos porque toda ficha existente tiene ``guardian`` NULL y
   ``relationship`` vacío, que es el primer caso de la disyunción.

3. **Los dos permisos de la historia**, sembrados y propagados a las
   organizaciones ya dadas de alta. Se hace desde ``patients`` y no desde
   ``accounts`` siguiendo lo que ya hacía ``tenancy/0003_seed_catalog``: el
   catálogo de permisos es de ``accounts``, pero quien sabe qué permisos hacen
   falta es la app que los va a exigir.

**Quién los recibe: sólo el Paciente.** El caso de uso es del titular desde su
teléfono, y los endpoints resuelven de quién son los dependientes **desde el
token**, nunca desde un identificador que mande el cliente. Dárselos al
Administrador o a la Recepcionista sería un permiso muerto: sus cuentas no
tienen ficha de paciente, así que preguntar por "sus" dependientes no devuelve
nada. Corregir un vínculo mal cargado desde el mostrador es trabajo del ABM de
pacientes (US-10), y va con los permisos de US-10.
"""

from django.conf import settings
from django.db import migrations, models

NEW_PERMISSIONS = [
    ("patients.dependent.read", "patients", "Consultar los pacientes a cargo"),
    ("patients.dependent.write", "patients", "Registrar y editar pacientes a cargo"),
]

GRANTS = {
    "patient": {"patients.dependent.read", "patients.dependent.write"},
}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _set_tenant(schema_editor, organization_id):
    """Regla 4 del reparto: fuera del ciclo HTTP el contexto se fija a mano."""
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
    Permission = apps.get_model("accounts", "Permission")

    schema_editor.execute(PLATFORM_ON)
    Permission.objects.filter(
        code__in=[code for code, _module, _description in NEW_PERMISSIONS],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0001_initial"),
        ("tenancy", "0003_seed_catalog"),
        # Las plantillas ya tienen que existir para poder sumarles permisos.
        ("accounts", "0005_us06_audit"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="relationship",
            field=models.CharField(
                blank=True,
                choices=[
                    ("child", "Hijo/a"),
                    ("spouse", "Cónyuge"),
                    ("parent", "Padre/Madre"),
                    ("sibling", "Hermano/a"),
                    ("grandparent", "Abuelo/a"),
                    ("grandchild", "Nieto/a"),
                    ("ward", "Bajo tutela"),
                    ("other", "Otro"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="patient",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    models.Q(("guardian__isnull", True), ("relationship", "")),
                    models.Q(
                        ("guardian__isnull", False),
                        models.Q(("relationship", ""), _negated=True),
                    ),
                    _connector="OR",
                ),
                name="ck_patient_relationship",
            ),
        ),
        migrations.RunPython(seed, unseed),
    ]
