"""US-32 — Row Level Security y clave foránea compuesta de `services`.

Mismo patrón que `0003_rls_policies.py`: `ENABLE` + `FORCE` + política
`tenant_isolation`, y la FK a `specialties` rehecha como compuesta
`(specialty_id, organization_id)` para que un servicio no pueda colgar de la
especialidad de otra organización (RNF-08).

`ON DELETE SET NULL (specialty_id)` y no `SET NULL` a secas: el segundo
pondría en NULL también `organization_id`, que es parte de la clave.
"""

from django.db import migrations

TABLE = "services"

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
               AND confrelid = 'specialties'::regclass
        LOOP
            EXECUTE format('ALTER TABLE {TABLE} DROP CONSTRAINT %I', c);
        END LOOP;
    END
    $do$;

    ALTER TABLE {TABLE} ADD CONSTRAINT fk_services_specialties_same_org
        FOREIGN KEY (specialty_id, organization_id)
        REFERENCES specialties (id, organization_id)
        ON DELETE SET NULL (specialty_id);
"""


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_us32_servicios"),
    ]

    operations = [
        migrations.RunSQL(POLICIES, DROP_POLICIES),
        migrations.RunSQL(COMPOSITE_FK, migrations.RunSQL.noop),
    ]
