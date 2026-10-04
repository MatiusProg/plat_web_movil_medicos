"""US-24 — RLS, claves compuestas y la inmutabilidad del encuentro firmado.

Lo primero es el patrón de siempre (ver `appointments/0002_rls_policies.py`):
`ENABLE` + `FORCE` + `tenant_isolation`, y cada FK a una tabla del inquilino
rehecha como `(x_id, organization_id)` para que un encuentro no pueda
referenciar la ficha, el paciente o el profesional de otra organización.

Lo segundo es propio de esta historia. "Una vez firmado no se edita" y "el
encuentro se cierra, no se borra" son reglas de la historia clínica, no de
una pantalla: si sólo las cumpliera la vista, un `UPDATE` desde el shell, un
comando de gestión o una vista futura las saltearía sin que nada avise. Por
eso son **triggers**:

- `encounters`: rechaza todo `DELETE`, y todo `UPDATE` de una fila que ya
  estaba firmada. El `UPDATE` que la firma (borrador → firmado) sí pasa.
- `encounter_amendments`: rechaza `UPDATE` y `DELETE`. Una enmienda
  equivocada se corrige con otra enmienda.

Las pruebas de `tests/test_us24.py` lo verifican contra la base, no contra
la vista.
"""

from django.db import migrations

TABLES = ["encounters", "encounter_amendments"]


def _policies():
    return "\n".join(f"""
        ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;
        ALTER TABLE {t} FORCE  ROW LEVEL SECURITY;
        CREATE POLICY tenant_isolation ON {t}
            USING (organization_id = app_current_tenant())
            WITH CHECK (organization_id = app_current_tenant());
    """ for t in TABLES)


def _drop_policies():
    return "\n".join(f"""
        DROP POLICY IF EXISTS tenant_isolation ON {t};
        ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY;
        ALTER TABLE {t} DISABLE ROW LEVEL SECURITY;
    """ for t in TABLES)


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
    _recreate_fk("encounters", "appointments", "appointment_id", "ON DELETE RESTRICT"),
    _recreate_fk("encounters", "patients", "patient_id", "ON DELETE RESTRICT"),
    _recreate_fk("encounters", "practitioners", "practitioner_id", "ON DELETE RESTRICT"),
    _recreate_fk("encounters", "branches", "branch_id", "ON DELETE RESTRICT"),
    # MATCH SIMPLE: mientras es borrador, signed_by_id es NULL y no se evalúa.
    _recreate_fk("encounters", "users", "signed_by_id", "ON DELETE RESTRICT"),
    _recreate_fk("encounter_amendments", "encounters", "encounter_id", "ON DELETE RESTRICT"),
    _recreate_fk("encounter_amendments", "users", "author_id", "ON DELETE RESTRICT"),
])


TRIGGERS = """
CREATE OR REPLACE FUNCTION encounters_inmutable() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Un encuentro clínico no se borra (US-24).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    IF OLD.status = 'signed' THEN
        RAISE EXCEPTION 'El encuentro está firmado: las correcciones van como enmienda (US-24).'
            USING ERRCODE = 'integrity_constraint_violation';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_encounters_inmutable
    BEFORE UPDATE OR DELETE ON encounters
    FOR EACH ROW EXECUTE FUNCTION encounters_inmutable();

CREATE OR REPLACE FUNCTION encounter_amendments_inmutable() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'Una enmienda no se modifica ni se borra: se agrega otra (US-24).'
        USING ERRCODE = 'integrity_constraint_violation';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_encounter_amendments_inmutable
    BEFORE UPDATE OR DELETE ON encounter_amendments
    FOR EACH ROW EXECUTE FUNCTION encounter_amendments_inmutable();
"""

DROP_TRIGGERS = """
DROP TRIGGER IF EXISTS trg_encounter_amendments_inmutable ON encounter_amendments;
DROP FUNCTION IF EXISTS encounter_amendments_inmutable();
DROP TRIGGER IF EXISTS trg_encounters_inmutable ON encounters;
DROP FUNCTION IF EXISTS encounters_inmutable();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("encounters", "0001_initial"),
        ("appointments", "0002_rls_policies"),
        ("patients", "0004_us08_rls"),
        ("catalog", "0007_us32_permisos_servicios"),
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunSQL(TRIGGERS, DROP_TRIGGERS),
    ]
