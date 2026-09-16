"""US-31 — Almacén de fragmentos vectorizados del catálogo.

Una sola tabla: cada fila es **un fragmento de texto del catálogo con su
embedding**. El asistente no guarda conversaciones ni respuestas; guarda lo
que puede recuperar.

Tres decisiones que no son obvias:

1. **La tabla lleva `organization_id` y RLS, como cualquier otra tabla del
   inquilino.** No es una tabla auxiliar ni un índice técnico: contiene texto
   del catálogo de una organización, y recuperar el fragmento de otra es
   exactamente la fuga que el apartado 1.1.6 del documento prohíbe. El
   aislamiento se hace cumplir en la base, no en la consulta que escribimos.

2. **`source_id` no es una clave foránea.** Apunta a la fila de la que salió
   el fragmento, y esa fila hoy es una especialidad pero mañana será una
   sucursal (US-32). Una FK obligaría a una columna por tipo de fuente, o a
   una tabla por tipo. `source_type` + `source_id` mantiene una sola tabla y
   un solo índice vectorial, que es lo que hace barata a US-32.
   El precio es que la integridad referencial queda del lado de
   `embed_catalog`, que reindexa la fuente entera cada vez.

3. **La dimensión del vector está fijada en 768 y es irreversible.** Es la
   definición de la columna: cambiarla es `ALTER TABLE` más volver a calcular
   todos los embeddings. Por eso vive en una constante y no en un número
   suelto, y por eso `embeddings.py` valida el largo de lo que devuelve el
   proveedor antes de guardarlo.
"""

import uuid

from django.db import models
from pgvector.django import VectorField

# Dimensión del espacio de embeddings. Ver `embeddings.py` para el porqué de
# 768 y no los 3072 que el proveedor entrega por omisión.
EMBEDDING_DIMENSIONS = 768


class SourceType(models.TextChoices):
    """De qué parte del catálogo salió el fragmento.

    US-31 sólo usa `SPECIALTY`. Los otros dos están declarados desde ahora
    porque US-32 los va a cargar sobre esta misma tabla y este mismo índice, y
    agregar un valor a un `TextChoices` después obliga a una migración que no
    hace falta si el valor ya estaba.
    """

    SPECIALTY = "specialty", "Especialidad"
    BRANCH = "branch", "Sucursal"
    SERVICE = "service", "Servicio o estudio"


class CatalogFragment(models.Model):
    """Un fragmento recuperable del catálogo, con su vector."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="catalog_fragments",
    )
    source_type = models.CharField(max_length=20, choices=SourceType.choices)
    source_id = models.UUIDField()
    # Orden del fragmento dentro de su fuente. Sirve para reconstruir el texto
    # completo y para que la clave única no dependa del contenido.
    position = models.PositiveSmallIntegerField(default=0)

    # El texto tal como se vectorizó. Se guarda aunque sea redundante con el
    # catálogo: es lo que se le muestra al paciente como respaldo de la
    # respuesta, y tiene que ser *lo que el modelo vio*, no lo que la fuente
    # diga hoy. Si alguien edita la especialidad y todavía no se reindexó, la
    # diferencia entre ambos es justamente el aviso de que hay que reindexar.
    text = models.TextField()
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS)

    # Con qué modelo se calculó. Mezclar embeddings de dos modelos en el mismo
    # índice da distancias que no significan nada: los espacios no son
    # comparables. Guardarlo permite detectarlo en vez de sufrirlo.
    embedding_model = models.CharField(max_length=80)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "assistant_catalog_fragments"
        verbose_name = "fragmento del catálogo"
        verbose_name_plural = "fragmentos del catálogo"
        ordering = ["source_type", "source_id", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "source_type", "source_id", "position"],
                name="uq_fragment_source_position",
            ),
        ]
        indexes = [
            # Índice corriente, no vectorial: es el que usa `embed_catalog`
            # para borrar los fragmentos viejos de una fuente antes de
            # reescribirlos. El índice de similitud se crea en la migración
            # 0002, porque pgvector no se declara desde `Meta.indexes`.
            models.Index(
                fields=["organization", "source_type", "source_id"],
                name="ix_fragment_source",
            ),
        ]

    def __str__(self):
        return f"{self.get_source_type_display()} · {self.text[:60]}"
