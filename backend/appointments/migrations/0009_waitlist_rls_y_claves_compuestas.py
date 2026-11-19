"""US-52 — RLS y claves compuestas de `waitlist_entries`.

El patrón de siempre (ver `noshow/migrations/0002_rls_y_claves_compuestas.py`):
`ENABLE` + `FORCE` + `tenant_isolation`, y cada clave foránea a una tabla del
inquilino rehecha como `(x_id, organization_id)`. Con eso una entrada de la
lista de espera no puede apuntar a un paciente, profesional, especialidad,
sucursal ni ficha de **otra organización**, aunque alguien escribiera la fila
sin pasar por la aplicación.

Todas son `ON DELETE RESTRICT`: ninguna de esas filas se borra mientras haya
una entrada que la use. (No `SET NULL`: con una clave compuesta anularía
también `organization_id`.) Las claves nulas —profesional, especialidad,
sucursal, ficha ofrecida— no se comprueban mientras estén vacías.
"""

from django.db import migrations

TABLE = "waitlist_entries"

POLICIES = f"""
ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {TABLE} FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON {TABLE}
    USING (organization_id = app_current_tenant())
    WITH CHECK (organization_id = app_current_tenant());
"""

DROP_POLICIES = f"""
DROP POLICY IF EXISTS tenant_isolation ON {TABLE};
ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
"""


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

    ALTER TABLE {child} ADD CONSTRAINT fk_{child}_{column}_same_org
        FOREIGN KEY ({column}, organization_id)
        REFERENCES {parent} (id, organization_id) {on_delete};
    """


COMPOSITE_FKS = "\n".join(
    _recreate_fk(TABLE, parent, column, "ON DELETE RESTRICT")
    for parent, column in [
        ("patients", "patient_id"),
        ("users", "requested_by_id"),
        ("practitioners", "practitioner_id"),
        ("specialties", "specialty_id"),
        ("branches", "branch_id"),
        ("appointments", "offered_appointment_id"),
    ]
)


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0008_waitlist_entries"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(POLICIES, DROP_POLICIES),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
    ]
