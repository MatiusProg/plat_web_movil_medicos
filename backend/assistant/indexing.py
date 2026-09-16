"""US-31, pieza 2 — De catálogo a fragmentos indexados.

Acá se decide **qué se vectoriza**, que es la decisión que más pesa sobre la
calidad de la recuperación. El modelo de embeddings no se puede mejorar; el
texto que le damos, sí.

Dos reglas, y las dos vienen de haber visto fallar lo contrario:

1. **Un fragmento por idea, no uno por fila.** La descripción de una
   especialidad trae qué atiende, sus motivos de consulta y a quién. Metido
   todo en un solo vector, el promedio queda en el medio de las tres cosas y
   no se parece bien a ninguna. Partido por oración, "me duele el pecho"
   encuentra la oración de los motivos cardiológicos y no compite contra el
   resto del párrafo. Es la misma granularidad que el reparto le exige al
   corpus administrativo de US-32: un fragmento por sucursal, no las tres
   juntas.

2. **Todo fragmento se basta a sí mismo.** Cada uno se guarda prefijado con el
   nombre de la especialidad. Sin eso, el fragmento recuperado dice "dolor u
   opresión en el pecho, palpitaciones…" y no dice de qué especialidad salió,
   ni al modelo de lenguaje, ni al paciente que lo ve como respaldo. Un
   fragmento que hay que ir a completar a otra tabla no es un fragmento.

La reindexación **borra y reescribe** los fragmentos de cada fuente en vez de
compararlos. Con un catálogo de este tamaño es más barato que detectar
cambios, y sobre todo no deja fragmentos huérfanos cuando una descripción se
acorta.
"""

import re

from catalog.models import Specialty

from .embeddings import active_model_name, embed_documents
from .models import CatalogFragment, SourceType

# Corta después de . ! o ? seguidos de espacio. No intenta ser un analizador
# de oraciones: el texto del catálogo lo escribimos nosotros y no tiene
# abreviaturas con punto.
_SENTENCE = re.compile(r"(?<=[.!?])\s+")

# Una oración más corta que esto no aporta nada como fragmento propio: se
# descarta en vez de ocupar una fila y competir en la búsqueda.
MIN_FRAGMENT_CHARS = 25


def split_into_fragments(name: str, description: str) -> list[str]:
    """Convierte una especialidad en la lista de textos a vectorizar.

    El primero es siempre el nombre solo: es lo que hace que preguntar
    literalmente "cardiología" recupere cardiología sin depender de que
    alguno de los motivos coincida.
    """
    name = (name or "").strip()
    fragments = [f"Especialidad: {name}."]

    for sentence in _SENTENCE.split((description or "").strip()):
        sentence = sentence.strip()
        if len(sentence) >= MIN_FRAGMENT_CHARS:
            fragments.append(f"Especialidad: {name}. {sentence}")

    return fragments


def index_specialties(organization, *, stdout=None) -> dict:
    """Reindexa las especialidades activas de una organización.

    **Tiene que llamarse dentro de un ``tenant_context()``.** Es la regla 4
    del reparto: fuera del ciclo HTTP el contexto no lo fija nadie, y sin él
    RLS devuelve cero especialidades y el comando informa alegremente que
    indexó nada.

    Devuelve el resumen para que el comando lo imprima; no imprime él.
    """
    specialties = list(
        Specialty.objects.filter(organization=organization, is_active=True)
        .order_by("name")
    )

    texts, rows = [], []
    for specialty in specialties:
        for position, text in enumerate(
            split_into_fragments(specialty.name, specialty.description)
        ):
            texts.append(text)
            rows.append((specialty, position, text))

    if not rows:
        return {
            "specialties": 0, "fragments": 0, "model": active_model_name(),
            "empty": [s.name for s in specialties],
        }

    # Una sola llamada al proveedor para todos los fragmentos: el nivel
    # gratuito limita por peticiones por minuto, no por texto enviado.
    if stdout is not None:
        stdout.write(f"  vectorizando {len(texts)} fragmentos…")
    vectors = embed_documents(texts)

    model = active_model_name()
    CatalogFragment.objects.filter(
        organization=organization, source_type=SourceType.SPECIALTY,
    ).delete()
    CatalogFragment.objects.bulk_create([
        CatalogFragment(
            organization=organization,
            source_type=SourceType.SPECIALTY,
            source_id=specialty.id,
            position=position,
            text=text,
            embedding=vector,
            embedding_model=model,
        )
        for (specialty, position, text), vector in zip(rows, vectors)
    ])

    return {
        "specialties": len(specialties),
        "fragments": len(rows),
        "model": model,
        # Una especialidad sin descripción entra al índice con un solo
        # fragmento —su nombre— y prácticamente no se recupera. Se avisa, no
        # se falla: el catálogo es de otra persona.
        "empty": [s.name for s in specialties if not (s.description or "").strip()],
    }
