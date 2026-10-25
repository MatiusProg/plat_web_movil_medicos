"""US-26 — RLS, claves compuestas y la regla de la receta firmada.

Lo mismo que `0002_rls_e_inmutabilidad.py` hizo con el encuentro, aplicado a
sus dos tablas nuevas: `ENABLE` + `FORCE` + `tenant_isolation`, y la FK al
encuentro rehecha como `(encounter_id, organization_id)` para que un
medicamento no pueda colgar de un encuentro de otra organización.

**La receta comparte la regla del encuentro**: mientras es borrador se
edita; firmado, no. Un trigger por tabla rechaza `INSERT`, `UPDATE` y
`DELETE` cuando el encuentro padre ya está firmado. Lo mira con
`FOR SHARE`: si el médico agrega un medicamento justo mientras otra
pestaña firma, el trigger espera a que la firma termine y lee el estado
nuevo, en lugar de leer "borrador" y colar un renglón en una receta firmada.

En un `UPDATE` se mira el encuentro viejo **y** el nuevo: mover un renglón de
un borrador a un encuentro firmado, o al revés, tampoco pasa.

Las pruebas de `tests/test_us26.py` lo verifican contra la base.
"""

from django.db import migrations

TABLES = ["encounter_prescription_items", "encounter_orders"]


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


def _recreate_fk(child):
    return f"""
    DO $do$
    DECLARE c text;
    BEGIN
        FOR c IN
            SELECT conname FROM pg_constraint
             WHERE conrelid = '{child}'::regclass AND contype = 'f'
               AND confrelid = 'encounters'::regclass
        LOOP
            EXECUTE format('ALTER TABLE {child} DROP CONSTRAINT %I', c);
        END LOOP;
    END
    $do$;

    ALTER TABLE {child} ADD CONSTRAINT fk_{child}_encounter_same_org
        FOREIGN KEY (encounter_id, organization_id)
        REFERENCES encounters (id, organization_id) ON DELETE RESTRICT;
    """


COMPOSITE_FKS = "\n".join(_recreate_fk(t) for t in TABLES)


TRIGGERS = """
CREATE OR REPLACE FUNCTION encounter_children_solo_en_borrador() RETURNS trigger AS $$
DECLARE
    estado text;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        SELECT status INTO estado FROM encounters WHERE id = OLD.encounter_id FOR SHARE;
        IF estado = 'signed' THEN
            RAISE EXCEPTION 'El encuentro está firmado: la receta y las órdenes se corrigen con una enmienda (US-26).'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO estado FROM encounters WHERE id = NEW.encounter_id FOR SHARE;
        IF estado = 'signed' THEN
            RAISE EXCEPTION 'El encuentro está firmado: la receta y las órdenes se corrigen con una enmienda (US-26).'
                USING ERRCODE = 'integrity_constraint_violation';
        END IF;
        RETURN NEW;
    END IF;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_prescription_items_solo_en_borrador
    BEFORE INSERT OR UPDATE OR DELETE ON encounter_prescription_items
    FOR EACH ROW EXECUTE FUNCTION encounter_children_solo_en_borrador();

CREATE TRIGGER trg_orders_solo_en_borrador
    BEFORE INSERT OR UPDATE OR DELETE ON encounter_orders
    FOR EACH ROW EXECUTE FUNCTION encounter_children_solo_en_borrador();
"""

DROP_TRIGGERS = """
DROP TRIGGER IF EXISTS trg_orders_solo_en_borrador ON encounter_orders;
DROP TRIGGER IF EXISTS trg_prescription_items_solo_en_borrador ON encounter_prescription_items;
DROP FUNCTION IF EXISTS encounter_children_solo_en_borrador();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("encounters", "0005_us26_receta_y_ordenes"),
    ]

    operations = [
        migrations.RunSQL(_policies(), _drop_policies()),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunSQL(TRIGGERS, DROP_TRIGGERS),
    ]
