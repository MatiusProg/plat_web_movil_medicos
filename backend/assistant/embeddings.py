"""US-31 — De un texto a su vector.

El proveedor es **enchufable** y eso no es una floritura de diseño: la clave de
OpenAI no se versiona (regla del reparto) y no está en la máquina de todos los
integrantes. Sin un camino alternativo, ni las pruebas ni la demostración
podrían correr en una máquina sin clave, y la historia sería imposible de
revisar.

Dos proveedores:

- ``openai`` — ``text-embedding-3-small``, 1536 dimensiones. Se usa cuando hay
  ``OPENAI_API_KEY``. Es el de producción.
- ``local`` — proyección por *hashing* sobre la misma cantidad de dimensiones,
  sin red y sin clave. **No es un modelo de lenguaje**: es una bolsa de
  palabras proyectada y normalizada, así que sólo captura solapamiento léxico
  —«dolor de cabeza» recupera «dolores de cabeza», pero no «cefalea»—. Alcanza
  para probar el aislamiento y el camino completo, que es lo que se muestra el
  16/09, y **no alcanza para producción**. Está dicho acá y en la respuesta de
  la API, que devuelve qué proveedor la generó.

**Cada fragmento guarda con qué proveedor se vectorizó, y la búsqueda sólo mira
los del proveedor vigente.** Es la trampa que más caro sale en un RAG: dos
modelos distintos producen vectores del mismo tamaño y completamente
incomparables, así que mezclarlos no da ningún error — da resultados absurdos
que parecen un problema de calidad del corpus. Con el filtro por proveedor,
cambiar de modelo deja el índice viejo invisible hasta que se reindexe, que es
lo correcto.
"""

import hashlib
import logging
import math
import os
import re
import unicodedata

from django.conf import settings

logger = logging.getLogger(__name__)

# `text-embedding-3-small` de OpenAI. El proveedor local usa la misma cantidad
# para que las dos poblaciones convivan en la misma columna sin ALTER TABLE.
DIMENSIONS = 1536

OPENAI = "openai"
LOCAL = "local"

OPENAI_MODEL = "text-embedding-3-small"


class EmbeddingError(Exception):
    """No se pudo vectorizar. La vista la traduce a «no puedo responder»."""


def provider_name() -> str:
    """Qué proveedor está vigente ahora mismo.

    Se resuelve en cada llamada y no una vez al importar: en las pruebas se
    cambia la variable de entorno con ``monkeypatch`` y el módulo ya está
    importado.
    """
    if _api_key():
        return OPENAI
    return LOCAL


def embed(text: str) -> list[float]:
    """El vector de un texto, con el proveedor vigente."""
    return embed_many([text])[0]


def embed_many(texts: list[str]) -> list[list[float]]:
    """Vectoriza en lote. Una llamada de red para todo el corpus, no una por
    fragmento: indexar cien fragmentos de a uno son cien viajes."""
    limpios = [(t or "").strip() for t in texts]
    if provider_name() == OPENAI:
        return _openai(limpios)
    return [_local(t) for t in limpios]


# --------------------------------------------------------------------------
#  OpenAI
# --------------------------------------------------------------------------
def _api_key() -> str:
    """La clave, del entorno. Nunca del código ni del repositorio."""
    return (
        getattr(settings, "OPENAI_API_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
    ).strip()


def _openai(texts: list[str]) -> list[list[float]]:
    """Llama a la API de *embeddings*.

    El import va adentro por lo mismo que en ``reporting.exporters``: si falta
    el paquete, falla el endpoint que lo necesita y no el arranque del proceso.
    """
    try:
        from openai import OpenAI
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise EmbeddingError(
            "El paquete «openai» no está instalado en este entorno.",
        ) from error

    try:
        cliente = OpenAI(api_key=_api_key(), timeout=20.0)
        respuesta = cliente.embeddings.create(
            model=OPENAI_MODEL, input=texts,
        )
    except Exception as error:  # noqa: BLE001
        # Cualquier fallo del proveedor —red, cuota, clave vencida— llega acá.
        # No se degrada solo a `local`: mezclar dos poblaciones de vectores en
        # el mismo índice es exactamente lo que el filtro por proveedor
        # existe para impedir. Se falla, y la vista responde «no puedo
        # responder ahora».
        logger.warning("El proveedor de embeddings no respondió: %s", error)
        raise EmbeddingError(str(error)) from error

    return [dato.embedding for dato in respuesta.data]


# --------------------------------------------------------------------------
#  Local, sin red
# --------------------------------------------------------------------------
# Se parte en palabras y en bigramas. Los bigramas son los que hacen que
# «dolor de pecho» se parezca más a «dolor de pecho» que a un texto que
# mencione «dolor» y «pecho» separados por tres párrafos.
_PALABRA = re.compile(r"[a-z0-9]+")

# Palabras que aparecen en todos los fragmentos y no distinguen ninguno. Con
# ellas dentro, todo se parece a todo.
_VACIAS = frozenset("""
a al algo ante antes aqui con como cual cuando de del desde donde dos el ella
ellas ellos en entre era es esa ese eso esta este esto ha hace hasta hay la las
le les lo los mas me mi mucho muy no nos o para pero por porque que quien se
ser si sin sobre son su sus tambien tiene todo todos tu un una uno unos y ya
""".split())


def _normalizar(texto: str) -> str:
    """Minúsculas y sin tildes.

    Es el mismo criterio que ``catalog.normalize_text`` usa para la búsqueda de
    US-16, y por la misma razón: nadie escribe «cefalea» con tilde dos veces
    igual, y «Neurología» y «neurologia» tienen que caer en el mismo término.
    """
    plano = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in plano if not unicodedata.combining(c))


def _terminos(texto: str) -> list[str]:
    palabras = [
        p for p in _PALABRA.findall(_normalizar(texto))
        if len(p) > 2 and p not in _VACIAS
    ]
    bigramas = [
        f"{a}_{b}" for a, b in zip(palabras, palabras[1:])
    ]
    return palabras + bigramas


def shares_terms(a: str, b: str, minimum: int = 2) -> bool:
    """¿Estos dos textos comparten al menos ``minimum`` términos de verdad?

    **Existe por una limitación real del proveedor local, medida y no supuesta.**
    Proyectar sobre 1536 dimensiones con la función de hash hace que dos
    términos distintos caigan a veces en el mismo casillero. Con un fragmento de
    unos 40 términos y una consulta de unos 15, la probabilidad de al menos una
    colisión ronda el 35 %: una de cada tres preguntas se parece un poco a un
    fragmento con el que no comparte una sola palabra.

    Eso rompe lo único que el umbral de distancia tenía que garantizar —que una
    pregunta ajena al catálogo no recupere nada—. Se vio con «cuánto cuesta un
    pasaje en avión a Madrid», que recuperaba una especialidad.

    Bajar el umbral no lo arregla: una colisión pesa exactamente lo mismo que
    una coincidencia real, así que no hay corte que separe una de la otra. Lo
    que sí las separa es **mirar los términos**, que acá se puede porque el
    proveedor local *es* léxico. No aplica al proveedor denso, donde compartir
    palabras no es lo que hace que dos textos se parezcan —«cefalea» y «dolor de
    cabeza» no comparten ninguna— y este filtro estaría de más.

    Dos y no uno: un solo término compartido suele ser una palabra genérica que
    sobrevivió a la lista de vacías —«centro», «consulta», «médico»—.
    """
    comunes = set(_terminos(a)) & set(_terminos(b))
    return len(comunes) >= minimum


def _local(texto: str) -> list[float]:
    """La proyección por hashing, normalizada a longitud 1.

    Normalizar es imprescindible: pgvector ordena por distancia coseno, que es
    ``1 - producto punto`` **sólo** entre vectores unitarios. Sin normalizar,
    un fragmento largo gana por tener más masa y no por parecerse más, que es
    el defecto que hace que el RAG devuelva siempre el texto más extenso.
    """
    vector = [0.0] * DIMENSIONS
    for termino in _terminos(texto):
        digest = hashlib.blake2b(termino.encode("utf-8"), digest_size=8).digest()
        indice = int.from_bytes(digest[:4], "big") % DIMENSIONS
        # El bit de signo reparte los términos entre valores positivos y
        # negativos; sin eso, todos los vectores apuntan al mismo octante y
        # cualquier par de textos da una similitud alta.
        signo = 1.0 if digest[4] & 1 else -1.0
        vector[indice] += signo

    norma = math.sqrt(sum(v * v for v in vector))
    if norma == 0.0:
        # Un texto sin términos útiles —«hola», puntuación suelta—. Se devuelve
        # el vector nulo: su distancia a todo es la misma, así que no recupera
        # nada por parecido y la vista contesta que no encontró contexto. Es
        # mejor que inventar un vector al azar, que recuperaría cualquier cosa.
        return vector
    return [v / norma for v in vector]
