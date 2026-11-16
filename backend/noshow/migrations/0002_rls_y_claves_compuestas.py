"""US-35 — RLS y claves compuestas de `model_versions` y `noshow_predictions`.

El patrón de siempre (ver `ai/migrations/0002_rls_e_inmutabilidad.py`):
`ENABLE` + `FORCE` + `tenant_isolation`, y cada clave foránea a una tabla del
inquilino rehecha como `(x_id, organization_id)`. Con eso una predicción no
puede colgar de una ficha ni de un modelo de **otra organización**, aunque
alguien escribiera la fila sin pasar por la aplicación.

Dos claves compuestas:

- `appointment` → `appointments (id, organization_id)`, `ON DELETE CASCADE`: la
  predicción se deriva de la ficha.
- `model_version` → `model_versions (id, organization_id)`, `ON DELETE RESTRICT`:
  una versión con predicciones no se borra, y el modelo queda como prueba de qué
  se predijo y con qué.
"""

from django.db import migrations

TABLES = ("model_versions", "noshow_predictions")


def _policies(table):
    return f"""
    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {table} FORCE  ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON {table}
        USING (organization_id = app_current_tenant())
        WITH CHECK (organization_id = app_current_tenant());
    """


def _drop_policies(table):
    return f"""
    DROP POLICY IF EXISTS tenant_isolation ON {table};
    ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
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


POLICIES = "\n".join(_policies(t) for t in TABLES)
DROP_POLICIES = "\n".join(_drop_policies(t) for t in TABLES)

COMPOSITE_FKS = "\n".join([
    _recreate_fk("noshow_predictions", "appointments", "appointment_id", "ON DELETE CASCADE"),
    _recreate_fk("noshow_predictions", "model_versions", "model_version_id", "ON DELETE RESTRICT"),
])


class Migration(migrations.Migration):

    dependencies = [
        ("noshow", "0001_initial"),
        ("appointments", "0006_seed_counter_booking_permission"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(POLICIES, DROP_POLICIES),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
    ]
