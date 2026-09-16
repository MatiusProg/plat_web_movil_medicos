"""US-31 — La tabla de fragmentos del asistente.

La primera operación no crea nada: **se asegura de que pgvector exista** antes
de que Django intente usar el tipo `vector`. Sin eso, el error que aparece es

    django.db.utils.ProgrammingError: type "vector" does not exist

que no menciona pgvector, no dice quién tiene que instalarlo y manda a
cualquiera a buscar un error de Django que no existe.

El bloque intenta crear la extensión y, si no puede, explica por qué. Los dos
casos son reales y distintos:

- **PostgreSQL local**: quien migra suele ser superusuario, así que la crea y
  sigue —salvo que la extensión ni siquiera esté instalada en el servidor, que
  es lo que pasa con el instalador de EDB en Windows (docs/entorno/sin-docker.md).
- **Supabase**: `app_user` es NOSUPERUSER a propósito, porque es lo que hace
  que las pruebas de aislamiento signifiquen algo. Ahí la extensión la crea
  una vez `postgres` desde el SQL Editor, como dice docs/entorno/supabase.md.
"""

import uuid

import django.db.models.deletion
import pgvector.django
from django.db import migrations, models

ENSURE_VECTOR = """
DO $do$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector') THEN
        BEGIN
            CREATE EXTENSION vector;
        EXCEPTION
            WHEN insufficient_privilege THEN
                RAISE EXCEPTION 'pgvector esta instalada en el servidor pero '
                    'este rol no puede habilitarla. Ejecutala una vez como '
                    'superusuario:  CREATE EXTENSION IF NOT EXISTS vector;  '
                    '(en Supabase, desde el SQL Editor del panel). '
                    'Ver docs/entorno/supabase.md';
            -- Los tres codigos son el mismo problema visto desde tres
            -- lugares: el archivo de control de la extension no esta en el
            -- servidor. `feature_not_supported` es el que devuelve
            -- PostgreSQL 18 en Windows, y es el que mas confunde, porque el
            -- texto habla de una funcionalidad no soportada y no de un
            -- paquete que falta.
            WHEN feature_not_supported OR undefined_file OR undefined_object THEN
                RAISE EXCEPTION 'pgvector NO esta instalada en el servidor de '
                    'PostgreSQL. El paquete de Python no la instala: hay que '
                    'agregarla al servidor, o trabajar contra Supabase, que '
                    'ya la trae. Ver docs/entorno/sin-docker.md';
        END;
    END IF;
END
$do$;
"""


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=ENSURE_VECTOR,
            # No se desinstala al revertir: otra app podría estar usándola, y
            # DROP EXTENSION se llevaría sus columnas por delante.
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.CreateModel(
            name="CatalogFragment",
            fields=[
                ("id", models.UUIDField(
                    default=uuid.uuid4, editable=False, primary_key=True,
                    serialize=False,
                )),
                ("source_type", models.CharField(
                    choices=[
                        ("specialty", "Especialidad"),
                        ("branch", "Sucursal"),
                        ("service", "Servicio o estudio"),
                    ],
                    max_length=20,
                )),
                ("source_id", models.UUIDField()),
                ("position", models.PositiveSmallIntegerField(default=0)),
                ("text", models.TextField()),
                ("embedding", pgvector.django.VectorField(dimensions=768)),
                ("embedding_model", models.CharField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="catalog_fragments",
                    to="tenancy.organization",
                )),
            ],
            options={
                "verbose_name": "fragmento del catálogo",
                "verbose_name_plural": "fragmentos del catálogo",
                "db_table": "assistant_catalog_fragments",
                "ordering": ["source_type", "source_id", "position"],
            },
        ),
        migrations.AddIndex(
            model_name="catalogfragment",
            index=models.Index(
                fields=["organization", "source_type", "source_id"],
                name="ix_fragment_source",
            ),
        ),
        migrations.AddConstraint(
            model_name="catalogfragment",
            constraint=models.UniqueConstraint(
                fields=("organization", "source_type", "source_id", "position"),
                name="uq_fragment_source_position",
            ),
        ),
    ]
