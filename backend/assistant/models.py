"""US-31 y US-32 — El índice de fragmentos sobre el que responde el asistente.

Una tabla. Cada fila es un **fragmento** de texto del catálogo de una
organización, con su vector.

**Por qué una tabla de fragmentos y no vectorizar la fila del catálogo.** Una
especialidad con una descripción de dos párrafos, vectorizada entera, produce
un vector que es el promedio de todo lo que dice: la consulta «dolor de pecho»
se parece poco a un texto que además habla de horarios y de preparación previa.
Partir en fragmentos y vectorizar cada uno es lo que hace que la recuperación
apunte al pedazo que contesta, y es también lo que permite mostrar **qué
pedazo** sostiene la respuesta, que es el punto 3 de la historia.

**El fragmento guarda su texto.** Podría sólo apuntar a la fila de origen y
leerla al responder, pero entonces la respuesta se sostendría en el texto de
*hoy* mientras el vector es el de *cuando se indexó*. Con el texto guardado,
lo que se le muestra al usuario es exactamente lo que se recuperó.

**Y guarda con qué proveedor se vectorizó.** El porqué está en
``embeddings``: dos modelos producen vectores incomparables del mismo tamaño, y
mezclarlos no da error, da resultados absurdos.
"""

import uuid

from django.db import models
from pgvector.django import HnswIndex, VectorField

from .embeddings import DIMENSIONS


class KnowledgeChunk(models.Model):
    """Un fragmento indexado del catálogo de una organización."""

    class Source(models.TextChoices):
        """De dónde salió el fragmento.

        Sirve para dos cosas concretas: reindexar sólo una parte del corpus
        —volver a vectorizar las especialidades sin tocar las sucursales— y
        acotar la búsqueda por tipo de pregunta, que es lo que US-32 necesita
        para que «¿a qué hora abren?» no recupere una descripción clínica.
        """

        SPECIALTY = "specialty", "Especialidad"
        BRANCH = "branch", "Sucursal"
        PRACTITIONER = "practitioner", "Profesional"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="knowledge_chunks",
    )
    source_type = models.CharField(max_length=20, choices=Source)
    # El uuid de la fila de la que salió. Sin clave foránea a propósito: apunta
    # a tres tablas distintas según `source_type`, y una FK por tipo sería tres
    # columnas nulables para no ganar nada. La integridad se resuelve
    # reindexando, que es barato.
    source_id = models.UUIDField()
    # Lo que se muestra como origen del fragmento: «Cardiología», «Sede Norte».
    title = models.CharField(max_length=200)
    content = models.TextField()
    embedding = VectorField(dimensions=DIMENSIONS)
    provider = models.CharField(max_length=20)
    indexed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "knowledge_chunks"
        verbose_name = "fragmento de conocimiento"
        verbose_name_plural = "fragmentos de conocimiento"
        ordering = ["source_type", "title"]
        constraints = [
            # Reindexar tiene que reemplazar, no acumular. Sin esto, correr
            # `embed_catalog` dos veces duplica el corpus y la respuesta cita
            # dos veces el mismo texto.
            models.UniqueConstraint(
                fields=["organization", "source_type", "source_id", "title"],
                name="uq_knowledge_chunk",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "source_type"],
                         name="ix_knowledge_chunk_source"),
            # HNSW y no IVFFlat: IVFFlat necesita estar construido sobre datos
            # ya cargados para elegir sus listas, y acá el corpus se crea vacío
            # y se llena después. HNSW no tiene ese problema.
            #
            # `vector_cosine_ops` porque la búsqueda usa distancia coseno, que
            # es lo correcto para embeddings normalizados. Con el operador
            # equivocado el índice existe y no se usa: la consulta hace un
            # recorrido secuencial sin avisar.
            HnswIndex(
                name="ix_knowledge_chunk_vec",
                fields=["embedding"],
                m=16, ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self):
        return f"{self.get_source_type_display()} · {self.title}"
