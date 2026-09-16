"""US-31 — RLS y permiso del asistente.

Mismo patrón que ``reporting/0002`` y ``backups/0002``.

**Por qué el RLS importa acá más que en casi cualquier otra tabla.** El reparto
lo dice: «el riesgo del chatbot no es que responda mal, es que responda con
datos de otro inquilino». Una búsqueda vectorial mal acotada no devuelve un
error: devuelve el fragmento más parecido, y si el más parecido es de otro
centro médico, el asistente lo lee en voz alta como si fuera propio.

``retrieval.search`` filtra por organización en el ``WHERE``, antes del
``ORDER BY``. Esta política es la segunda cerradura: si alguien borra ese
filtro por optimizar, la consulta sigue sin ver nada ajeno.

**No hay clave foránea compuesta.** Es la única tabla nueva del proyecto sin
una, y no es un olvido: ``source_id`` apunta a tres tablas distintas según
``source_type`` —especialidades, sucursales y profesionales—, así que no hay
una sola columna a la que referenciar. La integridad se mantiene reindexando,
que es barato y es lo que ``embed_catalog`` hace en cada corrida al borrar los
fragmentos cuyo origen ya no existe.

**El permiso.** ``assistant.query.create``, y lo recibe el **Paciente** además
del personal. Es la excepción respecto de reportes y respaldos, y es el punto:
US-31 es una historia móvil, y el móvil es la aplicación del paciente. Es la
primera funcionalidad del proyecto pensada para quien no trabaja en el centro
médico.
"""

from django.db import migrations

NEW_TENANT_TABLES = ["knowledge_chunks"]

NEW_PERMISSIONS = [
    ("assistant.query.create", "assistant",
     "Consultar el asistente de orientación"),
]

GRANTS = {
    "org_admin": {"assistant.query.create"},
    "practitioner": {"assistant.query.create"},
    "receptionist": {"assistant.query.create"},
    # US-31 es MÓVIL: el destinatario es el paciente.
    "patient": {"assistant.query.create"},
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
        ("assistant", "0001_initial"),
        ("tenancy", "0002_rls_policies"),
        ("accounts", "0005_us06_audit"),
    ]

    operations = [
        migrations.RunSQL(_tenant_policies(), _drop_policies()),
        migrations.RunPython(seed, unseed),
    ]
