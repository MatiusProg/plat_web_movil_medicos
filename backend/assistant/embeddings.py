"""US-31, pieza 1 — Cómo se convierte un texto en un vector.

El resto de la app no sabe quién calcula los embeddings. Pide
``embed_documents()`` o ``embed_query()`` y recibe listas de 768 números
normalizadas. Eso permite dos cosas: cambiar de proveedor sin tocar la
recuperación, y **correr la demostración sin conexión**.

---

**Por qué Gemini.** El nivel gratuito incluye el modelo de embeddings, que es
lo que US-31 consume de verdad: un vector por fragmento del catálogo y otro
por cada pregunta. Chat gratuito ofrecen varios; embeddings gratuitos, no
tantos.

**Por qué 768 dimensiones y no las 3072 que entrega por omisión.** La
dimensión *es* la definición de la columna ``vector(N)``: cambiarla después es
un ALTER TABLE más recalcular todo el índice. 768 es uno de los tamaños que
Google recomienda para recuperación, ocupa la cuarta parte y no se nota en la
calidad con un corpus de este tamaño.

**Por qué se normaliza a mano.** ``gemini-embedding-001`` normaliza los
vectores de 3072, pero **no los truncados**. Guardados sin normalizar, la
distancia coseno sigue dando un orden razonable pero el producto interno no, y
un índice creado sobre otro operador deja de coincidir con lo que la consulta
calcula. Normalizar una sola vez acá evita esa clase de error, que no falla:
sólo devuelve mal.

**Por qué ``task_type``.** Google entrena el modelo para que la pregunta y el
documento caigan en lugares distintos del espacio: un fragmento se indexa como
RETRIEVAL_DOCUMENT y una consulta se calcula como RETRIEVAL_QUERY. Usar el
mismo valor para los dos funciona y recupera peor. Hacerlo bien es gratis.

---

**El proveedor local.** No es un simulacro vacío: proyecta el texto sobre 768
dimensiones con una función determinista de sus palabras y trigramas. No
entiende sinónimos —"infarto" no se parece a "ataque al corazón"—, pero sí
reconoce las palabras que comparten la pregunta y el fragmento, y con un
corpus escrito en el vocabulario del paciente eso alcanza para que la
demostración funcione.

Existe por un motivo concreto: si mañana a las 18:50 se cae la red de la
universidad o se agota la cuota, ``ASSISTANT_EMBEDDING_PROVIDER=local`` deja
el asistente en pie. Lo que **no** hace es disimular: ``active_model_name()``
devuelve ``local-hash-768``, ese nombre queda guardado en cada fragmento y
viaja en la respuesta del endpoint. Quien mire la demostración ve con qué se
calculó.
"""

import hashlib
import math
import re
import unicodedata

from django.conf import settings

from .models import EMBEDDING_DIMENSIONS

LOCAL_MODEL_NAME = f"local-hash-{EMBEDDING_DIMENSIONS}"


class EmbeddingError(RuntimeError):
    """El proveedor no pudo calcular los embeddings.

    Siempre se propaga: un vector inventado se guarda igual de bien que uno
    real y después recupera cualquier cosa, sin que nada avise.
    """


# --------------------------------------------------------------------------
#  Utilidades comunes
# --------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Minúsculas y sin tildes, igual que ``catalog.normalize_text``."""
    lowered = (text or "").strip().lower()
    decomposed = unicodedata.normalize("NFKD", lowered)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        # Un vector nulo deja indefinida toda distancia coseno. Se devuelve un
        # eje cualquiera: no se parece a nada, que es lo correcto para un
        # texto vacío.
        neutral = [0.0] * EMBEDDING_DIMENSIONS
        neutral[0] = 1.0
        return neutral
    return [value / norm for value in vector]


def _check_dimensions(vector: list[float]) -> list[float]:
    if len(vector) != EMBEDDING_DIMENSIONS:
        raise EmbeddingError(
            f"El proveedor devolvió un vector de {len(vector)} dimensiones y "
            f"la columna espera {EMBEDDING_DIMENSIONS}. Revisá "
            f"ASSISTANT_EMBEDDING_MODEL: mezclar dimensiones no da un error "
            f"claro de base de datos, da filas que no se pueden comparar."
        )
    return vector


# --------------------------------------------------------------------------
#  Proveedor local, determinista
# --------------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9]+")

# Palabras que aparecen en casi toda frase en español y por lo tanto no
# distinguen nada. Sin filtrarlas, un fragmento con muchas palabras de relleno
# —"es la consulta a la que traen los padres cuando quien está enfermo…"— se
# parece un poco a cualquier pregunta, y con un corpus chico ese "un poco"
# alcanza para ganarle a la especialidad correcta.
#
# Sólo afecta al proveedor local: Gemini resuelve esto solo, y mucho mejor.
_STOPWORDS = frozenset("""
    que como cuando quien quienes cual cuales donde porque para por con sin
    los las del una uno unos unas este esta esto estos estas ese esa eso esos
    esas aquel sus mis tus nos les lel son ser soy eres est estan estoy estar
    esta estas tengo tiene tienen tener hacer hace hago haya hay mas muy pero
    tambien desde hasta entre sobre todo toda todos todas otra otro otros
    otras cada ante bajo segun tras ya sea ni ni o u y a al de en el la lo le
    se me te su mi tu un
""".split())


def _tokens(text: str) -> list[str]:
    """Palabras de tres letras o más, más sus trigramas.

    Los trigramas son los que hacen que "cardiaco" se parezca a "cardiologia"
    y que un error de tipeo no rompa la búsqueda.
    """
    words = [
        w for w in _WORD.findall(normalize_text(text))
        if len(w) >= 3 and w not in _STOPWORDS
    ]
    trigrams = [
        word[i:i + 3]
        for word in words
        for i in range(len(word) - 2)
    ]
    return words + trigrams


def _local_embedding(text: str) -> list[float]:
    vector = [0.0] * EMBEDDING_DIMENSIONS
    for token in _tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % EMBEDDING_DIMENSIONS
        # El signo sale de otro byte del mismo resumen. Sin él, dos textos
        # cualesquiera dan vectores con todas las componentes positivas y
        # terminan pareciéndose entre sí.
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    return _l2_normalize(vector)


# --------------------------------------------------------------------------
#  Proveedor Gemini
# --------------------------------------------------------------------------

def _gemini_client():
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise EmbeddingError(
            "Falta GEMINI_API_KEY en el .env. La clave no se versiona (regla "
            "11 del Sprint 2). Para trabajar sin ella: "
            "ASSISTANT_EMBEDDING_PROVIDER=local"
        )
    try:
        from google import genai
    except ImportError as error:
        raise EmbeddingError(
            "Falta el paquete google-genai. Corré "
            "pip install -r requirements.txt"
        ) from error
    return genai.Client(api_key=api_key)


def _gemini_embeddings(texts: list[str], task_type: str) -> list[list[float]]:
    from google.genai import types

    client = _gemini_client()
    try:
        result = client.models.embed_content(
            model=settings.ASSISTANT_EMBEDDING_MODEL,
            contents=texts,
            config=types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=EMBEDDING_DIMENSIONS,
            ),
        )
    except Exception as error:
        # Se envuelve a propósito: quien llama sólo necesita saber que el
        # proveedor falló, no distinguir entre cuota agotada, DNS y clave mal
        # copiada. El mensaje original viaja adentro.
        raise EmbeddingError(f"Gemini no respondió: {error}") from error

    return [
        _l2_normalize(_check_dimensions(list(item.values)))
        for item in result.embeddings
    ]


# --------------------------------------------------------------------------
#  Interfaz pública
# --------------------------------------------------------------------------

def active_model_name() -> str:
    """Con qué se están calculando los vectores, ahora mismo."""
    if settings.ASSISTANT_EMBEDDING_PROVIDER == "gemini":
        return settings.ASSISTANT_EMBEDDING_MODEL
    return LOCAL_MODEL_NAME


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Vectoriza fragmentos del catálogo, para guardar."""
    if not texts:
        return []
    if settings.ASSISTANT_EMBEDDING_PROVIDER == "gemini":
        return _gemini_embeddings(texts, task_type="RETRIEVAL_DOCUMENT")
    return [_local_embedding(text) for text in texts]


def embed_query(text: str) -> list[float]:
    """Vectoriza lo que escribió el paciente, para buscar."""
    if settings.ASSISTANT_EMBEDDING_PROVIDER == "gemini":
        return _gemini_embeddings([text], task_type="RETRIEVAL_QUERY")[0]
    return _local_embedding(text)
