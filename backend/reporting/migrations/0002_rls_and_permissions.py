"""Característica general 5 — RLS y permisos de los reportes guardados.

Mismo patrón que ``patients/0004_us08_rls`` y ``scheduling/0002_rls_policies``,
que es lo que pide el apartado 5 de ``docs/convenciones-de-codigo.md`` para
**toda tabla nueva con `organization_id`**:

1. ``ENABLE`` **y** ``FORCE ROW LEVEL SECURITY``,
2. política ``tenant_isolation`` con ``USING`` y ``WITH CHECK``,
3. clave foránea **compuesta** hacia el dueño,
4. su caso en ``tests/test_isolation.py``.

**Por qué la clave compuesta importa en esta tabla.** ``saved_reports`` apunta
a ``users``. Sin la clave compuesta, un reporte podría quedar a nombre de un
usuario de otra organización: la fila sería visible para el inquilino que dice
``organization_id`` —el suyo— pero su ``owner`` sería alguien de otro centro
médico, y ``is_mine`` daría falso para todos. Peor: al compartirlo, aparecería
en la lista de una organización con el correo de una persona de otra, que es
una filtración de directorio.

**Los permisos.** Tres, y el reparto sigue al Capítulo 2:

- ``report.run`` lo reciben Administrador, Médico y Recepcionista. El Paciente
  **no**: su aplicación es la móvil, donde no hay constructor de reportes, y
  darle uno sería darle una vista tabular de sus propios datos que no pidió
  nadie.
- ``report.save`` lo reciben los mismos tres. Guardar lo propio no afecta a
  nadie más.
- ``report.share`` **sólo el Administrador**. Compartir cambia lo que ve el
  resto de la organización, y eso es una decisión de quien administra.
"""

from django.db import migrations

NEW_TENANT_TABLES = ["saved_reports"]

NEW_PERMISSIONS = [
    ("reporting.report.run", "reporting",
     "Generar reportes y exportarlos"),
    ("reporting.report.save", "reporting",
     "Guardar reportes propios"),
    ("reporting.report.share", "reporting",
     "Compartir reportes con la organización"),
]

GRANTS = {
    "org_admin": {"reporting.report.run", "reporting.report.save",
                  "reporting.report.share"},
    "practitioner": {"reporting.report.run", "reporting.report.save"},
    "receptionist": {"reporting.report.run", "reporting.report.save"},
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


# `owner_id` es nulable —un reporte compartido sobrevive a la baja de su
# dueño—, así que la clave va con MATCH SIMPLE, que es el comportamiento
# predeterminado: con una de las dos columnas en NULL, la restricción no se
# comprueba. Es lo que se quiere: un reporte huérfano sigue perteneciendo a su
# organización.
COMPOSITE_FKS = """
DO $do$
DECLARE c text;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'saved_reports'::regclass AND contype = 'f'
           AND confrelid = 'users'::regclass
           AND conkey = ARRAY[
               (SELECT attnum FROM pg_attribute
                 WHERE attrelid = 'saved_reports'::regclass
                   AND attname = 'owner_id')
           ]
    LOOP
        EXECUTE format('ALTER TABLE saved_reports DROP CONSTRAINT %I', c);
    END LOOP;
END
$do$;

ALTER TABLE saved_reports ADD CONSTRAINT fk_saved_reports_users_same_org
    FOREIGN KEY (owner_id, organization_id)
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
        ("reporting", "0001_initial"),
        ("tenancy", "0002_rls_policies"),
        ("accounts", "0005_us06_audit"),
    ]

    operations = [
        migrations.RunSQL(_tenant_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunPython(seed, unseed),
    ]
