"""Característica general 6 — RLS y permisos de las copias de seguridad.

Mismo patrón que ``reporting/0002`` y ``patients/0004_us08_rls``, que es lo que
pide el apartado 5 de ``docs/convenciones-de-codigo.md``.

**Los permisos van sólo al Administrador de la organización, los dos.** Es más
restrictivo que los de reportes y es deliberado:

- ``backup.create`` produce un archivo con **todo** lo del inquilino en claro:
  el padrón, los antecedentes, los correos. Es la exportación más completa que
  existe en el sistema. Quien puede bajarla puede llevársela.
- ``backup.restore`` **reemplaza** los datos de la organización y no se puede
  deshacer.

Si mañana una organización quiere que su recepción baje la copia sin poder
restaurar, el ABM de roles de US-04 se lo permite sin tocar código: por eso son
dos permisos y no uno. Lo que esta migración fija es el **punto de partida**,
no una regla.
"""

from django.db import migrations

NEW_TENANT_TABLES = ["backup_records"]

NEW_PERMISSIONS = [
    ("backups.backup.create", "backups",
     "Generar y descargar copias de seguridad"),
    ("backups.backup.restore", "backups",
     "Restaurar la organización desde una copia"),
]

GRANTS = {
    "org_admin": {"backups.backup.create", "backups.backup.restore"},
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


# `performed_by` es nulable —el registro sobrevive a la baja de la cuenta— así
# que la clave compuesta no se comprueba cuando va en NULL, que es lo buscado.
COMPOSITE_FKS = """
DO $do$
DECLARE c text;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'backup_records'::regclass AND contype = 'f'
           AND confrelid = 'users'::regclass
           AND conkey = ARRAY[
               (SELECT attnum FROM pg_attribute
                 WHERE attrelid = 'backup_records'::regclass
                   AND attname = 'performed_by_id')
           ]
    LOOP
        EXECUTE format('ALTER TABLE backup_records DROP CONSTRAINT %I', c);
    END LOOP;
END
$do$;

ALTER TABLE backup_records ADD CONSTRAINT fk_backup_records_users_same_org
    FOREIGN KEY (performed_by_id, organization_id)
    REFERENCES users (id, organization_id) ON DELETE SET NULL;
"""


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
        ("backups", "0001_initial"),
        ("tenancy", "0002_rls_policies"),
        ("accounts", "0005_us06_audit"),
    ]

    operations = [
        migrations.RunSQL(_tenant_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunPython(seed, unseed),
    ]
