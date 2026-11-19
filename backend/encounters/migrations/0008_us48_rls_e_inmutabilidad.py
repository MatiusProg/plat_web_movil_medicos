"""US-48 — RLS, claves compuestas y las reglas de la calificación.

El patrón de siempre (ver `messaging/0002_rls_e_inmutabilidad.py`): `ENABLE` +
`FORCE` + `tenant_isolation`, y cada FK a una tabla del inquilino rehecha como
`(x_id, organization_id)`, para que una calificación no pueda colgar de la
atención, el paciente, el médico, la sede o el usuario de otra organización.

Y un **trigger**, por la misma razón que la firma del encuentro: si sólo lo
cumpliera la vista, un `UPDATE` desde el shell lo saltearía.

- **Sólo se califica una atención firmada.** Se mira con `FOR SHARE`, como la
  receta en la 0006.
- **No se borra**, y no cambia de atención, paciente, médico, sede, autor ni
  fecha de creación.
- **Se corrige durante 7 días** desde que se calificó; después queda fija.
"""

from django.db import migrations

TABLE = "encounter_ratings"

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

    ALTER TABLE {TABLE} ADD CONSTRAINT fk_{TABLE}_{column}_same_org
        FOREIGN KEY ({column}, organization_id)
        REFERENCES {parent} (id, organization_id) ON DELETE RESTRICT;
    """


COMPOSITE_FKS = "\n".join([
    _recreate_fk("encounters", "encounter_id"),
    _recreate_fk("patients", "patient_id"),
    _recreate_fk("practitioners", "practitioner_id"),
    _recreate_fk("branches", "branch_id"),
    _recreate_fk("users", "rated_by_id"),
])

TRIGGERS = f"""
CREATE OR REPLACE FUNCTION encounter_ratings_guarda() RETURNS trigger AS $$
DECLARE estado text;
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Una calificación no se borra (US-48).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;

    IF TG_OP = 'INSERT' THEN
        SELECT status INTO estado FROM encounters
         WHERE id = NEW.encounter_id FOR SHARE;
        IF estado IS DISTINCT FROM 'signed' THEN
            RAISE EXCEPTION 'Sólo se califica una atención firmada (US-48).'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.encounter_id IS DISTINCT FROM OLD.encounter_id
       OR NEW.patient_id IS DISTINCT FROM OLD.patient_id
       OR NEW.practitioner_id IS DISTINCT FROM OLD.practitioner_id
       OR NEW.branch_id IS DISTINCT FROM OLD.branch_id
       OR NEW.rated_by_id IS DISTINCT FROM OLD.rated_by_id
       OR NEW.organization_id IS DISTINCT FROM OLD.organization_id
       OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
        RAISE EXCEPTION 'Una calificación no cambia de atención ni de autor (US-48).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF now() > OLD.created_at + interval '7 days' THEN
        RAISE EXCEPTION 'Pasaron los 7 días: la calificación ya no se corrige (US-48).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_encounter_ratings_guarda
    BEFORE INSERT OR UPDATE OR DELETE ON {TABLE}
    FOR EACH ROW EXECUTE FUNCTION encounter_ratings_guarda();
"""

DROP_TRIGGERS = f"""
DROP TRIGGER IF EXISTS trg_encounter_ratings_guarda ON {TABLE};
DROP FUNCTION IF EXISTS encounter_ratings_guarda();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("encounters", "0007_us48_calificacion"),
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
