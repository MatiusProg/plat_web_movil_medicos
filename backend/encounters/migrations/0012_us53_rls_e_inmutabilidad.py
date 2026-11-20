"""US-53 — RLS, clave compuesta y la regla de lo firmado para los signos vitales.

Lo mismo que `0006_us26_rls_e_inmutabilidad.py` hizo con la receta:

- `ENABLE` + `FORCE` + `tenant_isolation`;
- la FK al encuentro rehecha como `(encounter_id, organization_id)`, para que
  unos signos vitales no puedan colgar de un encuentro de otra organización;
- un trigger que rechaza `INSERT`, `UPDATE` y `DELETE` cuando el encuentro está
  firmado. Lo lee con `FOR SHARE` por la misma carrera que la receta: si otra
  pestaña está firmando, espera y lee el estado nuevo.

Las pruebas de `tests/test_us53.py` lo verifican contra la base.
"""

from django.db import migrations

TABLE = "encounter_vital_signs"

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

COMPOSITE_FK = f"""
DO $do$
DECLARE c text;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = '{TABLE}'::regclass AND contype = 'f'
           AND confrelid = 'encounters'::regclass
    LOOP
        EXECUTE format('ALTER TABLE {TABLE} DROP CONSTRAINT %I', c);
    END LOOP;
END
$do$;

ALTER TABLE {TABLE} ADD CONSTRAINT fk_{TABLE}_encounter_same_org
    FOREIGN KEY (encounter_id, organization_id)
    REFERENCES encounters (id, organization_id) ON DELETE RESTRICT;
"""

TRIGGER = f"""
CREATE OR REPLACE FUNCTION vital_signs_solo_en_borrador() RETURNS trigger AS $$
DECLARE
    estado text;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        SELECT status INTO estado FROM encounters WHERE id = OLD.encounter_id FOR SHARE;
        IF estado = 'signed' THEN
            RAISE EXCEPTION 'El encuentro está firmado: los signos vitales se corrigen con una enmienda (US-53).'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO estado FROM encounters WHERE id = NEW.encounter_id FOR SHARE;
        IF estado = 'signed' THEN
            RAISE EXCEPTION 'El encuentro está firmado: los signos vitales se corrigen con una enmienda (US-53).'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vital_signs_solo_en_borrador
    BEFORE INSERT OR UPDATE OR DELETE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION vital_signs_solo_en_borrador();
"""

DROP_TRIGGER = f"""
DROP TRIGGER IF EXISTS trg_vital_signs_solo_en_borrador ON {TABLE};
DROP FUNCTION IF EXISTS vital_signs_solo_en_borrador();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("encounters", "0011_us53_signos_vitales"),
    ]

    operations = [
        migrations.RunSQL(POLICIES, DROP_POLICIES),
        migrations.RunSQL(COMPOSITE_FK, migrations.RunSQL.noop),
        migrations.RunSQL(TRIGGER, DROP_TRIGGER),
    ]
