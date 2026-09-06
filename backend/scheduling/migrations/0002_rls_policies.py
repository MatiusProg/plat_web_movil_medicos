"""Row Level Security y claves foráneas compuestas de `scheduling`.

Mismo patrón que `tenancy/migrations/0002_rls_policies.py` y
`catalog/migrations/0003_rls_policies.py`: `ENABLE` + `FORCE` + política
`tenant_isolation` por tabla, y FKs compuestas `(x_id, organization_id)` para
que una agenda o un bloqueo no pueda referenciar un profesional o una sucursal
de otra organización (RNF-08).
"""

from django.db import migrations

NEW_TENANT_TABLES = ["schedules", "schedule_blocks"]


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


COMPOSITE_FKS = "\n".join([
    _recreate_fk("schedules", "practitioners", "practitioner_id",
                 "ON DELETE RESTRICT"),
    _recreate_fk("schedules", "branches", "branch_id", "ON DELETE RESTRICT"),
    _recreate_fk("schedule_blocks", "practitioners", "practitioner_id",
                 "ON DELETE RESTRICT"),
    _recreate_fk("schedule_blocks", "branches", "branch_id",
                 "ON DELETE RESTRICT"),
])


class Migration(migrations.Migration):

    dependencies = [
        ("scheduling", "0001_initial"),
        ("catalog", "0003_rls_policies"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(_tenant_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
    ]
