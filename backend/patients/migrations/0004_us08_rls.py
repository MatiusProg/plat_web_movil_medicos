"""US-08 — RLS, clave foránea compuesta y permisos de los antecedentes.

Mismo patrón que `scheduling/migrations/0002_rls_policies.py` y
`catalog/migrations/0003_rls_policies.py`, que es lo que pide la regla del
apartado 5 de `convenciones-de-codigo.md` para **toda tabla nueva con
`organization_id`**:

1. `ENABLE` **y** `FORCE ROW LEVEL SECURITY`,
2. política `tenant_isolation` con `USING` y `WITH CHECK`,
3. clave foránea **compuesta** `(patient_id, organization_id)`,
4. su caso en `tests/test_isolation.py`.

**Por qué la FK compuesta importa acá más que en otras tablas.** Sin ella,
`patient_history_entries` podría apuntar a un paciente de otra organización: la
fila quedaría visible para el inquilino equivocado —el suyo es el que dice
`organization_id`— y estaría describiendo a alguien de otro centro médico. Con
datos clínicos eso no es una inconsistencia, es una filtración.

**Los permisos.** El Paciente escribe y lee los suyos y los de sus
dependientes; el Médico sólo lee, que es lo que necesita para ver los
antecedentes destacados al abrir la consulta (punto f), y esa lectura queda en
la bitácora (punto g). La Recepcionista no recibe nada: el punto (g) dice
paciente, titular y profesionales, y el Capítulo 2 le da acceso demográfico,
no clínico.
"""

from django.db import migrations

NEW_TENANT_TABLES = ["patient_history_entries"]

NEW_PERMISSIONS = [
    ("patients.history.read", "patients", "Consultar antecedentes del paciente"),
    ("patients.history.write", "patients", "Registrar y editar antecedentes"),
]

GRANTS = {
    "patient": {"patients.history.read", "patients.history.write"},
    "practitioner": {"patients.history.read"},
}

PLATFORM_ON = "SELECT set_config('app.is_platform_admin', 'on', true)"
PLATFORM_OFF = "SELECT set_config('app.is_platform_admin', '', true)"


def _tenant_policies():
    sql = []
    for table in NEW_TENANT_TABLES:
        sql.append(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE  ROW LEVEL SECURITY;
            CREATE POLICY tenant_isolation ON {table}
                USING (organization_id = app_current_tenant())
                WITH CHECK (organization_id = app_current_tenant());
        """)
    return "\n".join(sql)


def _drop_policies():
    sql = []
    for table in NEW_TENANT_TABLES:
        sql.append(f"""
            DO $do$
            DECLARE p text;
            BEGIN
                FOR p IN SELECT policyname FROM pg_policies
                          WHERE schemaname = 'public' AND tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY %I ON {table}', p);
                END LOOP;
            END
            $do$;
            ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """)
    return "\n".join(sql)


def _recreate_fk(child, parent, column, on_delete):
    return f"""
    DO $do$
    DECLARE c text;
    BEGIN
        FOR c IN
            SELECT conname FROM pg_constraint
             WHERE conrelid = '{child}'::regclass AND contype = 'f'
               AND confrelid = '{parent}'::regclass
               AND conkey = ARRAY[
                   (SELECT attnum FROM pg_attribute
                     WHERE attrelid = '{child}'::regclass AND attname = '{column}')
               ]
        LOOP
            EXECUTE format('ALTER TABLE {child} DROP CONSTRAINT %I', c);
        END LOOP;
    END
    $do$;

    ALTER TABLE {child} ADD CONSTRAINT fk_{child}_{parent}_same_org
        FOREIGN KEY ({column}, organization_id)
        REFERENCES {parent} (id, organization_id) {on_delete};
    """


COMPOSITE_FKS = _recreate_fk(
    "patient_history_entries", "patients", "patient_id", "ON DELETE CASCADE",
)


def _set_tenant(schema_editor, organization_id):
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
        ("patients", "0003_us08_history"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(_tenant_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunPython(seed, unseed),
    ]
