"""US-31, pieza 3 — La recuperación. Acá vive la regla 9 del sprint.

    9. La recuperación vectorial filtra por organización ANTES de ordenar por
       similitud.

No es una preferencia de estilo. Las dos formas devuelven lo mismo y una de
ellas es una fuga:

    -- Correcto: el filtro está en el WHERE. PostgreSQL descarta las filas de
    -- los otros inquilinos y ordena únicamente lo que queda.
    SELECT ... FROM assistant_catalog_fragments
     WHERE organization_id = %s
     ORDER BY embedding <=> %s LIMIT 5;

    -- Fuga: ordena el índice completo, de todos los inquilinos, y recién
    -- después se queda con los de uno. Devuelve el mismo resultado y ya
    -- recorrió datos ajenos. Con un LIMIT antes del filtro, además, devuelve
    -- menos filas de las pedidas o ninguna, sin explicar por qué.
    SELECT * FROM (
        SELECT ... ORDER BY embedding <=> %s LIMIT 5
    ) t WHERE organization_id = %s;

En Django la forma correcta es ``.filter(...)`` **antes** de ``.order_by()``,
porque el filtro termina en el WHERE y el orden en el ORDER BY, que es el
orden en que PostgreSQL los evalúa. Lo que está prohibido es traer filas y
descartarlas en Python.

RLS lo haría cumplir igual —``tenant_isolation`` está sobre la tabla— pero las
dos capas son a propósito: el filtro explícito documenta la intención y
sobrevive a que esto se llame desde un comando, donde el contexto lo fija
quien llama y puede olvidarse.

---

**El umbral.** Si nada se parece lo suficiente, esto devuelve lista vacía y el
asistente contesta que no sabe. Un RAG sin umbral siempre encuentra *algo*:
con cinco especialidades, la menos lejana de "quiero comprar un auto" es
alguna. Ese "algo" es lo que después el modelo de lenguaje convierte en una
recomendación médica inventada.

El valor correcto depende del proveedor —los espacios de Gemini y los del
proveedor local no tienen la misma escala—, así que es un parámetro de
configuración y no un número acá adentro.
"""

from dataclasses import dataclass

from pgvector.django import CosineDistance

from catalog.models import Specialty
from django.conf import settings

from .embeddings import embed_query
from .models import CatalogFragment, SourceType


@dataclass(frozen=True)
class RetrievedFragment:
    """Un fragmento recuperado, con de dónde salió y cuánto se parece."""

    id: str
    text: str
    source_type: str
    source_id: str
    source_name: str
    similarity: float


@dataclass(frozen=True)
class RankedSpecialty:
    """Una especialidad candidata y los fragmentos que la sostienen."""

    id: str
    name: str
    similarity: float
    fragments: list


def retrieve(organization, question: str, *, limit: int = 5) -> list:
    """Los fragmentos más parecidos a la pregunta, dentro de la organización.

    ``organization`` es obligatoria y no tiene valor por omisión: una función
    de recuperación con el inquilino opcional es una que alguien va a llamar
    sin él.
    """
    if organization is None:
        raise ValueError(
            "retrieve() necesita una organización. Sin ella no hay búsqueda "
            "que hacer: no existe un asistente 'de todos los inquilinos'."
        )

    question = (question or "").strip()
    if not question:
        return []

    vector = embed_query(question)

    # El orden de las llamadas ES la regla 9: filter primero, order_by después.
    fragments = list(
        CatalogFragment.objects
        .filter(organization=organization)
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")[:limit]
    )

    # Los nombres de las fuentes, en una sola consulta y también acotada a la
    # organización. `source_id` no es una FK (ver models.py), así que esto no
    # se puede resolver con un select_related.
    specialty_ids = [
        f.source_id for f in fragments if f.source_type == SourceType.SPECIALTY
    ]
    names = dict(
        Specialty.objects
        .filter(organization=organization, id__in=specialty_ids)
        .values_list("id", "name")
    )

    threshold = settings.ASSISTANT_MIN_SIMILARITY
    retrieved = []
    for fragment in fragments:
        # La distancia coseno va de 0 (idéntico) a 2 (opuesto). Con vectores
        # normalizados, 1 - distancia es la similitud coseno de siempre.
        similarity = 1.0 - float(fragment.distance)
        if similarity < threshold:
            continue
        retrieved.append(RetrievedFragment(
            id=str(fragment.id),
            text=fragment.text,
            source_type=fragment.source_type,
            source_id=str(fragment.source_id),
            source_name=names.get(fragment.source_id, ""),
            similarity=round(similarity, 4),
        ))

    return retrieved


def rank_specialties(fragments: list) -> list:
    """Agrupa los fragmentos por especialidad, conservando el orden.

    La especialidad se queda con la similitud de **su mejor fragmento**, no
    con el promedio de los suyos. El promedio castiga a la especialidad que
    contestó exactamente con una de sus oraciones y tiene otras tres que no
    venían al caso, que es justamente el caso que queremos premiar.
    """
    ranked: dict = {}
    for fragment in fragments:
        if fragment.source_type != SourceType.SPECIALTY or not fragment.source_name:
            continue
        current = ranked.get(fragment.source_id)
        if current is None:
            ranked[fragment.source_id] = RankedSpecialty(
                id=fragment.source_id,
                name=fragment.source_name,
                similarity=fragment.similarity,
                fragments=[fragment],
            )
        else:
            current.fragments.append(fragment)

    return sorted(ranked.values(), key=lambda s: s.similarity, reverse=True)
