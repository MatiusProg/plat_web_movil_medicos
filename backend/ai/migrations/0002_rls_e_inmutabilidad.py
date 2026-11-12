"""US-42 — RLS, claves compuestas y la decisión del médico que no se deshace.

Lo primero es el patrón de siempre (ver `encounters/0002_rls_e_inmutabilidad.py`):
`ENABLE` + `FORCE` + `tenant_isolation`, y cada FK a una tabla del inquilino
rehecha como `(x_id, organization_id)`, para que un texto no pueda colgar del
paciente, el médico o la atención de otra organización.

`encounter_orders` no tiene `UNIQUE (id, organization_id)`, así que la orden
queda con su FK simple: la preparación lleva además su atención, que sí está
atada a la organización, y el servicio exige que la orden sea de esa atención.

Lo segundo es propio de esta historia y va en **triggers**, por la misma razón
que la firma del encuentro: si sólo lo cumpliera la vista, un `UPDATE` desde
el shell lo saltearía sin que nada avise.

- El texto del modelo (`generated_text`) **no cambia nunca**: es la prueba de
  qué escribió la IA.
- Una fila **aprobada o descartada no se modifica**.
- **Nada se borra.** Un texto equivocado se descarta y queda el registro.
"""

from django.db import migrations

TABLE = "ai_generated_texts"

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


COMPOSITE_FKS = "\n".join([
    _recreate_fk(TABLE, "patients", "patient_id", "ON DELETE RESTRICT"),
    _recreate_fk(TABLE, "practitioners", "practitioner_id", "ON DELETE RESTRICT"),
    # MATCH SIMPLE: con encounter_id o reviewed_by_id en NULL no se evalúa.
    _recreate_fk(TABLE, "encounters", "encounter_id", "ON DELETE RESTRICT"),
    _recreate_fk(TABLE, "users", "reviewed_by_id", "ON DELETE RESTRICT"),
])

TRIGGERS = f"""
CREATE OR REPLACE FUNCTION ai_generated_texts_inmutable() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Un texto generado no se borra: se descarta (US-42).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF OLD.status <> 'draft' THEN
        RAISE EXCEPTION 'El texto ya fue validado o descartado y no se modifica (US-42).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.generated_text IS DISTINCT FROM OLD.generated_text THEN
        RAISE EXCEPTION 'El texto que escribió el modelo no se modifica (US-42).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_ai_generated_texts_inmutable
    BEFORE UPDATE OR DELETE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION ai_generated_texts_inmutable();
"""

DROP_TRIGGERS = f"""
DROP TRIGGER IF EXISTS trg_ai_generated_texts_inmutable ON {TABLE};
DROP FUNCTION IF EXISTS ai_generated_texts_inmutable();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("ai", "0001_initial"),
        ("encounters", "0006_us26_rls_e_inmutabilidad"),
        ("patients", "0004_us08_rls"),
        ("catalog", "0003_rls_policies"),
        ("accounts", "0002_initial"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(POLICIES, DROP_POLICIES),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunSQL(TRIGGERS, DROP_TRIGGERS),
    ]
