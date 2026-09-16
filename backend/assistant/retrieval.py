"""US-31, pieza 2 — Recuperación por similitud, sin cruzar organizaciones.

Es la pieza donde un error no se ve. Una búsqueda vectorial que devuelve el
fragmento equivocado parece un problema de calidad del corpus; una que devuelve
el fragmento de **otro centro médico** parece exactamente lo mismo, y es una
fuga de datos.

**El filtro de organización va en el ``WHERE``, antes del ``ORDER BY``.** El
reparto lo dice con todas las letras y vale la pena explicar por qué no es lo
mismo que filtrar después:

    -- Correcto: PostgreSQL recorre sólo los vectores de este inquilino.
    SELECT ... WHERE organization_id = %s ORDER BY embedding <=> %s LIMIT 5

    -- Fuga: se ordena el índice de TODOS y se descarta al final. Devuelve lo
    -- mismo, y en el camino el proceso tuvo en memoria los vectores ajenos y
    -- el plan de consulta los leyó.
    SELECT * FROM (SELECT ... ORDER BY embedding <=> %s LIMIT 5) WHERE org = %s

La segunda además **devuelve menos de lo que debería**: si los cinco más
parecidos son de otro inquilino, el resultado sale vacío aunque el catálogo
propio tuviera respuesta. Un fallo de aislamiento que encima funciona mal.

Acá el ``filter()`` del ORM produce la primera forma. RLS lo garantiza otra vez
por debajo —``knowledge_chunks`` tiene su política—, y las dos cosas están a
propósito: el filtro explícito es lo que hace que la consulta sea *rápida*, RLS
es lo que hace que sea *correcta* aunque alguien borre el filtro.
"""

from dataclasses import dataclass

from pgvector.django import CosineDistance

from . import embeddings
from .models import KnowledgeChunk

# Cuántos fragmentos se le pasan al modelo. Cinco es suficiente para que la
# respuesta tenga contexto y poco para que el modelo no se distraiga con
# material que no viene al caso.
TOP_K = 5

# Distancia coseno por encima de la cual un fragmento se considera que no viene
# al caso. Va de 0 (idéntico) a 2 (opuesto); 1.0 es «sin relación ninguna».
#
# **Este umbral es lo que impide inventar.** Sin él, una pregunta que el
# catálogo no contesta igual recupera los cinco fragmentos menos malos, y el
# modelo —que sólo ve fragmentos— responde como si fueran pertinentes. Con él,
# la respuesta es «no tengo esa información», que es la respuesta correcta.
#
# **Es uno por proveedor, y esto costó una vuelta.** Un umbral único parecía lo
# natural y está mal: la escala de distancias depende del modelo.
#
# - Un modelo denso reparte el espacio y dos textos del mismo tema quedan a
#   0,2–0,5. Con 0,72 entra lo pertinente y queda fuera lo que no.
# - El proveedor local es una bolsa de palabras dispersa: dos textos que
#   comparten tres términos de veinte quedan a **0,90**, y dos que no comparten
#   ninguno, exactamente a 1,0. Con 0,72 no entra nada nunca — que fue
#   literalmente lo que pasó la primera vez que se corrió contra datos reales:
#   cero fragmentos para toda pregunta, indistinguible de un índice vacío.
#
# Para el proveedor local, entonces, el corte útil está pegado a 1,0. No es
# arbitrario: **1,0 significa cero términos en común**, así que el umbral real
# es «que comparta algo», y el margen deja fuera las coincidencias de una sola
# palabra genérica.
MAX_DISTANCE = {
    embeddings.OPENAI: 0.72,
    embeddings.LOCAL: 0.965,
}

# El de reserva, si mañana se agrega un proveedor y alguien olvida su umbral.
# Conservador a propósito: recupera de menos y no de más.
DEFAULT_MAX_DISTANCE = 0.72


def max_distance(provider: str | None = None) -> float:
    """El umbral del proveedor vigente."""
    return MAX_DISTANCE.get(
        provider or embeddings.provider_name(), DEFAULT_MAX_DISTANCE,
    )


@dataclass
class Fragment:
    """Un fragmento recuperado, con lo que hace falta para mostrarlo.

    **No lleva un «porcentaje de coincidencia», y es a propósito.** La tentación
    es devolver ``1 - distancia`` como si fuera una confianza —«coincide un
    82 %»—, y es un número inventado: la escala depende del modelo. Con el
    proveedor local, el fragmento *correcto* da 0,04, y mostrar «coincide un
    4 %» al lado de la respuesta correcta es peor que no mostrar nada.

    Lo que sí es verdad y sí se muestra es el **orden** —``rank``, que es lo que
    la búsqueda realmente produce— y la **distancia cruda**, para quien quiera
    mirarla. Un ranking no necesita fingir una probabilidad.
    """

    id: str
    source_type: str
    source_label: str
    source_id: str
    title: str
    content: str
    distance: float
    rank: int = 0

    def as_dict(self) -> dict:
        return {
            "id": str(self.id),
            "rank": self.rank,
            "source_type": self.source_type,
            "source_label": self.source_label,
            "source_id": str(self.source_id),
            "title": self.title,
            "content": self.content,
            "distance": round(self.distance, 4),
        }


def search(organization, question: str, top_k: int = TOP_K,
           source_types=None) -> list[Fragment]:
    """Los fragmentos más parecidos a la pregunta, dentro de la organización.

    Se llama **dentro** de ``tenant_context`` o del ciclo de una petición, que
    es donde el contexto ya está fijado. Sin contexto, RLS deja la consulta en
    cero filas y el asistente contesta que no sabe — que es el modo de fallo
    correcto.
    """
    vector = embeddings.embed(question)
    proveedor = embeddings.provider_name()

    consulta = (
        KnowledgeChunk.objects
        # Los tres filtros van en el WHERE. El de organización es el que
        # importa para el aislamiento; el de proveedor, para no comparar
        # vectores de dos modelos distintos (ver `embeddings`).
        .filter(organization=organization, provider=proveedor)
    )
    if source_types:
        consulta = consulta.filter(source_type__in=list(source_types))

    consulta = (
        consulta
        .annotate(distance=CosineDistance("embedding", vector))
        .order_by("distance")[:top_k]
    )

    tope = max_distance(proveedor)
    etiquetas = dict(KnowledgeChunk.Source.choices)
    pertinentes = [
        fila for fila in consulta
        if fila.distance is not None and float(fila.distance) <= tope
    ]

    # Segundo filtro, **sólo para el proveedor local**: que compartan términos
    # de verdad. El porqué está en ``embeddings.shares_terms`` — la proyección
    # por hashing produce parecidos espurios que ningún umbral puede separar de
    # los buenos. Con el proveedor denso no corre, y no debe correr: ahí dos
    # textos se parecen sin compartir una sola palabra, que es justamente para
    # lo que sirve un modelo.
    if proveedor == embeddings.LOCAL:
        pertinentes = [
            fila for fila in pertinentes
            if embeddings.shares_terms(question, fila.content)
        ]
    return [
        Fragment(
            id=fila.id,
            rank=posicion,
            source_type=fila.source_type,
            source_label=etiquetas.get(fila.source_type, fila.source_type),
            source_id=fila.source_id,
            title=fila.title,
            content=fila.content,
            distance=float(fila.distance),
        )
        for posicion, fila in enumerate(pertinentes, start=1)
    ]


def suggested_specialty(fragments: list[Fragment]) -> dict | None:
    """La especialidad sugerida: el fragmento de especialidad mejor puntuado.

    Se elige acá y no se le pregunta al modelo. La razón es que la sugerencia
    tiene que apuntar a una **fila real del catálogo** —con su uuid, para que
    la pantalla pueda ofrecer «reservar con esta especialidad»—, y un modelo de
    lenguaje devuelve un nombre, no una clave. Un nombre casi correcto
    —«Cardiología clínica» en vez de «Cardiología»— no encuentra nada al
    reservar, y el error aparece dos pantallas después.
    """
    for fragmento in fragments:
        if fragmento.source_type == KnowledgeChunk.Source.SPECIALTY:
            return {
                "id": str(fragmento.source_id),
                "name": fragmento.title,
                "rank": fragmento.rank,
            }
    return None
