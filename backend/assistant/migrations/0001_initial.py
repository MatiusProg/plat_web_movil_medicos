"""US-31 — La tabla de fragmentos del asistente, con su columna `vector`.

Sólo la tabla y el índice vectorial. El RLS y los permisos van en
``0002_rls_and_permissions``, igual que en el resto del proyecto.

**Sobre ``VectorExtension``.** Django la salta si la extensión ya existe, así
que es un no-op en la base local —``init-db`` la crea— y en Supabase, donde
viene habilitada. Queda escrita igual porque es lo que hace que esta migración
se explique sola: la columna `vector` no es de PostgreSQL, es de pgvector.

**El índice HNSW se crea acá, con la tabla vacía.** Es la razón de haber
elegido HNSW y no IVFFlat: IVFFlat necesita datos cargados para decidir sus
listas, y crearlo sobre una tabla vacía produce un índice que no sirve y que
nadie vuelve a mirar.
"""

import uuid

import django.db.models.deletion
import pgvector.django.indexes
import pgvector.django.vector
from django.db import migrations, models
from pgvector.django import VectorExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('tenancy', '0003_seed_catalog'),
    ]

    operations = [
        VectorExtension(),
        migrations.CreateModel(
            name='KnowledgeChunk',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('source_type', models.CharField(choices=[('specialty', 'Especialidad'), ('branch', 'Sucursal'), ('practitioner', 'Profesional')], max_length=20)),
                ('source_id', models.UUIDField()),
                ('title', models.CharField(max_length=200)),
                ('content', models.TextField()),
                ('embedding', pgvector.django.vector.VectorField(dimensions=1536)),
                ('provider', models.CharField(max_length=20)),
                ('indexed_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='knowledge_chunks', to='tenancy.organization')),
            ],
            options={
                'verbose_name': 'fragmento de conocimiento',
                'verbose_name_plural': 'fragmentos de conocimiento',
                'db_table': 'knowledge_chunks',
                'ordering': ['source_type', 'title'],
                'indexes': [models.Index(fields=['organization', 'source_type'], name='ix_knowledge_chunk_source'), pgvector.django.indexes.HnswIndex(ef_construction=64, fields=['embedding'], m=16, name='ix_knowledge_chunk_vec', opclasses=['vector_cosine_ops'])],
                'constraints': [models.UniqueConstraint(fields=('organization', 'source_type', 'source_id', 'title'), name='uq_knowledge_chunk')],
            },
        ),
    ]
