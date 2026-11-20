"""US-49 — RLS, claves compuestas y las reglas de las tomas.

El patrón de siempre (ver `0008_us48_rls_e_inmutabilidad.py`): `ENABLE` +
`FORCE` + `tenant_isolation`, y cada FK rehecha como `(x_id, organization_id)`
para que una toma no pueda colgar de un medicamento, un paciente o un usuario
de otra organización.

El medicamento recetado no tenía la clave única `(id, organization_id)`
porque hasta ahora nada colgaba de él: se agrega acá.

Y un **trigger**:
- **Sólo se marca una toma de una receta firmada.** Un borrador todavía no es
  una indicación del médico.
- **Una toma no se cambia ni se borra.** Es lo que el paciente dijo.
"""

from django.db import migrations

TABLE = "encounter_medication_intakes"

UNIQUE_ITEM = """
ALTER TABLE encounter_prescription_items
    ADD CONSTRAINT uq_prescription_item_id_org UNIQUE (id, organization_id);
"""

DROP_UNIQUE_ITEM = """
ALTER TABLE encounter_prescription_items
    DROP CONSTRAINT IF EXISTS uq_prescription_item_id_org;
"""

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


def _recreate_fk(parent, column):
    return f"""
    DO $do$
    DECLARE c text;
    BEGIN
        FOR c IN
            SELECT conname FROM pg_constraint
             WHERE conrelid = '{TABLE}'::regclass AND contype = 'f'
               AND confrelid = '{parent}'::regclass
               AND conkey = ARRAY[
                   (SELECT attnum FROM pg_attribute
                     WHERE attrelid = '{TABLE}'::regclass AND attname = '{column}')
               ]
        LOOP
            EXECUTE format('ALTER TABLE {TABLE} DROP CONSTRAINT %I', c);
        END LOOP;
    END
    $do$;

    ALTER TABLE {TABLE} ADD CONSTRAINT fk_intakes_{column}_same_org
        FOREIGN KEY ({column}, organization_id)
        REFERENCES {parent} (id, organization_id) ON DELETE RESTRICT;
    """


COMPOSITE_FKS = "\n".join([
    _recreate_fk("encounter_prescription_items", "prescription_item_id"),
    _recreate_fk("patients", "patient_id"),
    _recreate_fk("users", "recorded_by_id"),
])

TRIGGERS = f"""
CREATE OR REPLACE FUNCTION encounter_medication_intakes_guarda() RETURNS trigger AS $$
DECLARE estado text;
BEGIN
    IF TG_OP <> 'INSERT' THEN
        RAISE EXCEPTION 'Una toma marcada no se cambia ni se borra (US-49).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    SELECT e.status INTO estado
      FROM encounter_prescription_items i
      JOIN encounters e ON e.id = i.encounter_id
     WHERE i.id = NEW.prescription_item_id
       FOR SHARE OF e;
    IF estado IS DISTINCT FROM 'signed' THEN
        RAISE EXCEPTION 'Sólo se marcan tomas de una receta firmada (US-49).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_encounter_medication_intakes_guarda
    BEFORE INSERT OR UPDATE OR DELETE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION encounter_medication_intakes_guarda();
"""

DROP_TRIGGERS = f"""
DROP TRIGGER IF EXISTS trg_encounter_medication_intakes_guarda ON {TABLE};
DROP FUNCTION IF EXISTS encounter_medication_intakes_guarda();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("encounters", "0009_us49_tomas"),
        ("patients", "0004_us08_rls"),
        ("accounts", "0002_initial"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(UNIQUE_ITEM, DROP_UNIQUE_ITEM),
        migrations.RunSQL(POLICIES, DROP_POLICIES),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunSQL(TRIGGERS, DROP_TRIGGERS),
    ]
