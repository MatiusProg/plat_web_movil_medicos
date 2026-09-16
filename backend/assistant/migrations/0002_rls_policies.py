"""RLS y el índice de similitud de la tabla del asistente.

**La tabla del asistente no es una excepción.** Mismo patrón que
`catalog/migrations/0003_rls_policies.py`: `ENABLE` **y** `FORCE ROW LEVEL
SECURITY` más la política `tenant_isolation`. Es el criterio 4 de la
Definición de Terminado y, acá, además, la única garantía de que una fuga de
la recuperación se corte en la base aunque alguien escriba mal la consulta.

Es lo que hace que la prueba de la sección 2 del reparto —la misma pregunta en
dos organizaciones devuelve catálogos distintos— sea una propiedad del sistema
y no una consecuencia de que la consulta esté bien escrita hoy.

---

**El índice HNSW.** Con veinticinco fragmentos PostgreSQL va a recorrer la
tabla entera igual, y va a hacer bien: un índice sobre veinticinco filas es
más caro que leerlas. Se crea igual, por tres motivos:

1. Es la estructura que sostiene la historia cuando el catálogo crezca, y
   crearla después sobre datos ya cargados es una migración larga en una base
   en uso.
2. Es HNSW y no IVFFlat **porque IVFFlat necesita datos para construirse**:
   sobre una tabla vacía se arma con listas vacías y recupera mal hasta que se
   reconstruye. HNSW se construye incremental y no tiene ese problema.
3. `vector_cosine_ops` tiene que coincidir con el operador que usa la
   consulta. `retrieval.py` ordena por `CosineDistance`, que es `<=>`. Un
   índice creado con otra clase de operadores no se usa nunca, no avisa, y
   deja a todos convencidos de que está indexado.
"""

from django.db import migrations

TABLE = "assistant_catalog_fragments"

ENABLE_RLS = f"""
    ALTER TABLE {TABLE} ENABLE ROW LEVEL SECURITY;
    ALTER TABLE {TABLE} FORCE  ROW LEVEL SECURITY;
    CREATE POLICY tenant_isolation ON {TABLE}
        USING (organization_id = app_current_tenant())
        WITH CHECK (organization_id = app_current_tenant());
"""

DISABLE_RLS = f"""
    DO $do$
    DECLARE p text;
    BEGIN
        FOR p IN SELECT policyname FROM pg_policies
                  WHERE schemaname = 'public' AND tablename = '{TABLE}'
        LOOP
            EXECUTE format('DROP POLICY %I ON {TABLE}', p);
        END LOOP;
    END
    $do$;
    ALTER TABLE {TABLE} NO FORCE ROW LEVEL SECURITY;
    ALTER TABLE {TABLE} DISABLE ROW LEVEL SECURITY;
"""

CREATE_INDEX = f"""
    CREATE INDEX IF NOT EXISTS ix_fragment_embedding_cosine
        ON {TABLE} USING hnsw (embedding vector_cosine_ops);
"""

DROP_INDEX = "DROP INDEX IF EXISTS ix_fragment_embedding_cosine;"


class Migration(migrations.Migration):

    dependencies = [
        ("assistant", "0001_initial"),
        # `app_current_tenant()` la define el Sprint 0. Sin esta dependencia,
        # el orden de las migraciones no garantiza que la función exista
        # cuando se crea la política.
        ("tenancy", "0002_rls_policies"),
    ]

    operations = [
        migrations.RunSQL(sql=ENABLE_RLS, reverse_sql=DISABLE_RLS),
        migrations.RunSQL(sql=CREATE_INDEX, reverse_sql=DROP_INDEX),
    ]
