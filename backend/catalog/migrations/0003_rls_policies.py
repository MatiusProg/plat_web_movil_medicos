"""Row Level Security y claves foráneas compuestas del catálogo del Sprint 1.

Mismo patrón que `tenancy/migrations/0002_rls_policies.py`: cada tabla nueva
con `organization_id` lleva `ENABLE` **y** `FORCE ROW LEVEL SECURITY` más una
política `tenant_isolation`, y toda FK a otra tabla del inquilino se rehace
como clave compuesta `(x_id, organization_id)` para que no se pueda cruzar de
organización. Es el criterio 4 de la Definición de Terminado (RNF-08).
"""

from django.db import migrations

# Tablas nuevas con organization_id: sólo se ven las filas del inquilino.
NEW_TENANT_TABLES = [
    "branch_hours",
    "specialties",
    "practitioners",
    "practitioner_specialties",
    "practitioner_branches",
]


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


# Cada FK a una tabla del inquilino se rehace incluyendo organization_id.
# MATCH SIMPLE (por omisión): si alguna columna es NULL la restricción no se
# evalúa — lo que necesita `practitioners.user_id`, que es opcional.
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
    _recreate_fk("practitioners", "users", "user_id",
                 "ON DELETE SET NULL (user_id)"),
    _recreate_fk("branch_hours", "branches", "branch_id", "ON DELETE CASCADE"),
    _recreate_fk("practitioner_specialties", "practitioners", "practitioner_id",
                 "ON DELETE CASCADE"),
    _recreate_fk("practitioner_specialties", "specialties", "specialty_id",
                 "ON DELETE CASCADE"),
    _recreate_fk("practitioner_branches", "practitioners", "practitioner_id",
                 "ON DELETE CASCADE"),
    _recreate_fk("practitioner_branches", "branches", "branch_id",
                 "ON DELETE CASCADE"),
])


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_catalogo_sprint_1"),
        ("tenancy", "0002_rls_policies"),
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(_tenant_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
    ]
