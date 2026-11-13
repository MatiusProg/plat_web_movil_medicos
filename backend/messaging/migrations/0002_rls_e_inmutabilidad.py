"""US-47 — RLS, claves compuestas y lo que el chat no deja cambiar.

El patrón de siempre (ver `ai/0002_rls_e_inmutabilidad.py`): `ENABLE` +
`FORCE` + `tenant_isolation`, y cada FK a una tabla del inquilino rehecha como
`(x_id, organization_id)`, para que una conversación no pueda colgar de la
atención, el paciente o el médico de otra organización, ni un mensaje de la
conversación o el usuario de otra.

Y en **triggers**, por la misma razón que la firma del encuentro: si sólo lo
cumpliera la vista, un `UPDATE` desde el shell lo saltearía.

- **Un mensaje no se modifica ni se borra.** Es lo que se le dijo al paciente.
- **Una conversación no se borra**, no cambia de atención, de paciente ni de
  médico, y una vez cerrada no se reabre.
"""

from django.db import migrations

TABLES = ("encounter_threads", "encounter_messages")


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


def _recreate_fk(child, parent, column, on_delete="ON DELETE RESTRICT"):
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
    _recreate_fk("encounter_threads", "encounters", "encounter_id"),
    _recreate_fk("encounter_threads", "patients", "patient_id"),
    _recreate_fk("encounter_threads", "practitioners", "practitioner_id"),
    # MATCH SIMPLE: con closed_by_id en NULL no se evalúa.
    _recreate_fk("encounter_threads", "users", "closed_by_id"),
    _recreate_fk("encounter_messages", "encounter_threads", "thread_id"),
    _recreate_fk("encounter_messages", "users", "author_id"),
])

TRIGGERS = """
CREATE OR REPLACE FUNCTION encounter_messages_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Un mensaje del chat no se modifica ni se borra (US-47).'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_encounter_messages_inmutable
    BEFORE UPDATE OR DELETE ON encounter_messages
    FOR EACH ROW EXECUTE FUNCTION encounter_messages_inmutable();

CREATE OR REPLACE FUNCTION encounter_threads_guarda() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Una conversación no se borra (US-47).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF NEW.encounter_id IS DISTINCT FROM OLD.encounter_id
       OR NEW.patient_id IS DISTINCT FROM OLD.patient_id
       OR NEW.practitioner_id IS DISTINCT FROM OLD.practitioner_id
       OR NEW.organization_id IS DISTINCT FROM OLD.organization_id THEN
        RAISE EXCEPTION 'Una conversación no cambia de atención ni de participantes (US-47).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF OLD.closed_at IS NOT NULL AND (NEW.closed_at IS DISTINCT FROM OLD.closed_at
                                      OR NEW.closed_by_id IS DISTINCT FROM OLD.closed_by_id) THEN
        RAISE EXCEPTION 'Una conversación cerrada no se reabre (US-47).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_encounter_threads_guarda
    BEFORE UPDATE OR DELETE ON encounter_threads
    FOR EACH ROW EXECUTE FUNCTION encounter_threads_guarda();
"""

DROP_TRIGGERS = """
DROP TRIGGER IF EXISTS trg_encounter_messages_inmutable ON encounter_messages;
DROP FUNCTION IF EXISTS encounter_messages_inmutable();
DROP TRIGGER IF EXISTS trg_encounter_threads_guarda ON encounter_threads;
DROP FUNCTION IF EXISTS encounter_threads_guarda();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("messaging", "0001_initial"),
        ("encounters", "0006_us26_rls_e_inmutabilidad"),
        ("patients", "0004_us08_rls"),
        ("catalog", "0003_rls_policies"),
        ("accounts", "0002_initial"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        *[migrations.RunSQL(_policies(t), _drop_policies(t)) for t in TABLES],
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunSQL(TRIGGERS, DROP_TRIGGERS),
    ]
