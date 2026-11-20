"""US-40 — Cómo prepararse para un estudio, en palabras del paciente.

Por cada orden de laboratorio o de imagen de una atención firmada (US-26), la
IA redacta qué hacer antes de ir: ayuno, qué medicación suspender, qué
llevar. El paciente lo lee junto a la orden **después de que su médico lo
apruebe** (US-42, regla 14 del Sprint 4).

Cuatro decisiones, del reparto:

1. **La preparación sale del catálogo de la organización, no del modelo.**
   Es lo que la clínica cargó en cada servicio (``Service.preparation``), el
   mismo texto que indexa el corpus administrativo de US-32. Primero se
   busca el servicio por nombre; si la orden lo nombra de otra forma, se
   busca en el corpus por parecido. **Si no hay fuente, no se genera:** una
   preparación inventada («ayuno de 12 horas» para un estudio que no lo
   pide) es peor que ninguna.
2. **El modelo sólo redacta sobre lo recuperado.** Recibe el texto del
   catálogo y las observaciones que el médico escribió en la orden, y nada
   del paciente. Al médico se le avisa si el texto trae un número que no
   está en la fuente: es la forma más común de inventar una preparación.
3. **Sin proveedor —o si el modelo falla— el borrador es el texto del
   catálogo tal cual.** No es una plantilla que parezca revisada: es lo que
   escribió la clínica, y se marca como tal (``generated_by="catalogo"``).
   Igual pasa por el médico antes de llegar al paciente.
4. **Firmar nunca falla por esto**, igual que con el resumen de US-39.
"""

from __future__ import annotations

import logging
import re
import unicodedata

from django.conf import settings
from django.db import IntegrityError, transaction

from . import services
from .models import AiGeneratedText

logger = logging.getLogger(__name__)

KIND = AiGeneratedText.Kind.PREPARATION

MAX_SOURCE_CHARS = 1500
MAX_OUTPUT_TOKENS = 400
TIMEOUT_MS = 20_000

# Qué tan parecido tiene que ser el nombre del servicio al de la orden cuando
# no está contenido uno en el otro: tres de cada cuatro palabras con
# contenido. Con la mitad, «Perfil lipídico» pasaba por «Perfil tiroideo».
MIN_NAME_OVERLAP = 0.75

GENERATED = "generated"        # el modelo lo redactó y quedó en la bandeja
FROM_CATALOG = "from_catalog"  # sin modelo: quedó el texto del catálogo
EXISTS = "exists"              # ya había una preparación viva para la orden
NO_SOURCE = "no_source"        # el catálogo no tiene preparación para eso

MESSAGES = {
    GENERATED: "La preparación quedó en «Textos por validar».",
    FROM_CATALOG: "La preparación quedó en «Textos por validar» con el texto "
                  "del catálogo: la IA no estaba disponible para redactarla.",
    EXISTS: "Esta orden ya tiene una preparación para el paciente.",
    NO_SOURCE: "El catálogo no tiene una preparación cargada para este "
               "estudio: no se generó una inventada.",
}

SYSTEM_PROMPT = """\
Eres un asistente que ayuda a un médico a explicarle a su paciente cómo
prepararse para un estudio. Recibes el nombre del estudio, la preparación que
la clínica tiene escrita para él y, a veces, observaciones del médico.
Escribes, en español de Bolivia y tratando al paciente de tú, instrucciones
claras para leer en el teléfono.

Reglas, sin excepción:
- Usa SOLO lo que dicen la preparación de la clínica y las observaciones del
  médico. No agregues horas de ayuno, medicamentos que suspender, documentos
  que llevar ni ningún otro paso que no esté escrito ahí.
- Copia tal cual los números (horas, días, cantidades).
- Si las observaciones del médico contradicen la preparación de la clínica,
  vale lo que dice el médico.
- Frases cortas, una indicación por línea, empezando con un verbo.
- No saludes ni firmes. No uses el nombre del paciente. Texto plano, sin
  markdown ni asteriscos.
"""


# --------------------------------------------------------------------------
#  La fuente: el catálogo de la organización
# --------------------------------------------------------------------------

def _normalize(text: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", (text or "").lower())
    return " ".join("".join(c for c in sin_tildes if not unicodedata.combining(c)).split())


_PALABRA = re.compile(r"[a-z0-9]+")
# Palabras que no distinguen un estudio de otro.
_VACIAS = {"de", "del", "la", "el", "los", "las", "y", "en", "con", "por", "para",
           "un", "una", "estudio", "examen", "analisis", "control"}


def _palabras(text: str) -> set[str]:
    return {p for p in _PALABRA.findall(_normalize(text)) if p not in _VACIAS and len(p) > 2}


def _parecido(nombre: str, pedido: str) -> float:
    """Qué tanto se parece el nombre de un servicio a lo que pide la orden."""
    n, p = _normalize(nombre), _normalize(pedido)
    if not n or not p:
        return 0.0
    if n in p or p in n:
        # Contenido entero: «Ecografía abdominal» en «Ecografía abdominal
        # completa». Gana el nombre más largo, que es el más específico.
        return 1.0 + len(n) / 1000
    a, b = _palabras(nombre), _palabras(pedido)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a)


def find_by_name(order):
    """El servicio activo con preparación cuyo nombre corresponde a la orden.

    El filtro por organización es una segunda defensa: la primera es el RLS
    de ``services``, que dentro de ``tenant_context`` ya no deja ver otra
    clínica (lo prueba ``test_el_catalogo_de_otra_organizacion_no_cuenta``).
    """
    from catalog.models import Service

    candidatos = (Service.objects
                  .filter(organization_id=order.organization_id, is_active=True)
                  .exclude(preparation=""))
    mejor, puntaje = None, 0.0
    for servicio in candidatos:
        valor = _parecido(servicio.name, order.description)
        if valor > puntaje:
            mejor, puntaje = servicio, valor
    return mejor if puntaje >= MIN_NAME_OVERLAP else None


def find_in_corpus(order):
    """El servicio que el corpus de US-32 encuentra más parecido a la orden.

    Necesita el proveedor (la búsqueda es por embeddings). Si no está o
    falla, no hay fuente por este lado: la búsqueda por nombre ya se hizo.
    """
    if not provider_available():
        return None
    from assistant.models import CatalogFragment, SourceType
    from assistant.retrieval import retrieve
    from catalog.models import Service

    # Sin servicios indexados no hay nada que buscar, y no se gasta una
    # llamada de embeddings en descubrirlo.
    if not CatalogFragment.objects.filter(
            organization_id=order.organization_id,
            source_type=SourceType.SERVICE).exists():
        return None
    try:
        fragmentos = retrieve(order.organization,
                              f"Preparación para {order.get_kind_display()}: "
                              f"{order.description}", limit=5)
    except Exception:
        logger.warning("US-40: no se pudo buscar en el corpus para la orden %s",
                       order.pk, exc_info=True)
        return None
    for fragmento in fragmentos:
        if fragmento.source_type != SourceType.SERVICE:
            continue
        servicio = (Service.objects
                    .filter(organization_id=order.organization_id, pk=fragmento.source_id,
                            is_active=True)
                    .exclude(preparation="")
                    .first())
        if servicio is not None:
            return servicio
    return None


def source_for(order):
    return find_by_name(order) or find_in_corpus(order)


# --------------------------------------------------------------------------
#  Lo que ve el modelo y lo que se le avisa al médico
# --------------------------------------------------------------------------

def _cut(text: str) -> str:
    text = (text or "").strip()
    return text if len(text) <= MAX_SOURCE_CHARS else text[:MAX_SOURCE_CHARS] + "…"


def context(order, service) -> str:
    """Lo que sale hacia el proveedor. Pública para que la prueba lo mire."""
    partes = [
        f"Estudio pedido: {order.description}",
        f"Preparación de la clínica para «{service.name}»: {_cut(service.preparation)}",
    ]
    if (order.notes or "").strip():
        partes.append(f"Observaciones del médico: {_cut(order.notes)}")
    return "\n".join(partes)


def catalog_text(order, service) -> str:
    """El borrador sin modelo: lo que escribió la clínica, sin reescribir."""
    texto = f"Para tu estudio «{order.description}»:\n{service.preparation.strip()}"
    if (order.notes or "").strip():
        texto += f"\nIndicación de tu médico: {order.notes.strip()}"
    return texto


_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")


def warnings_for(text: str, source: str) -> list[str]:
    """Los números del texto que no están en la fuente.

    Es lo que se puede comprobar sin entender el texto, y es justo lo que más
    daño hace si se inventa: horas de ayuno, días sin un medicamento.
    """
    en_fuente = set(_NUMERO.findall(source or ""))
    avisos = []
    for numero in dict.fromkeys(_NUMERO.findall(text or "")):
        if numero not in en_fuente:
            avisos.append(f"Dice «{numero}», que no está en la preparación del "
                          "catálogo ni en la orden.")
    return avisos


def warnings(texto) -> list[str]:
    """Las advertencias de un borrador de preparación ya guardado."""
    orden = texto.medical_order
    if orden is None:
        return []
    servicio = source_for(orden)
    fuente = " ".join(filter(None, [
        orden.description, orden.notes, servicio.preparation if servicio else ""]))
    return warnings_for(texto.final_text or texto.generated_text, fuente)


# --------------------------------------------------------------------------
#  Generar
# --------------------------------------------------------------------------

def provider_available() -> bool:
    return settings.ASSISTANT_CHAT_PROVIDER == "gemini" and bool(settings.GEMINI_API_KEY)


def generate(order) -> dict:
    """Deja en borrador la preparación de una orden de una atención firmada.

    Devuelve ``{"order": ..., "status": ..., "message": ..., "text_id": ...}``.
    **Nunca lanza:** lo llama la firma.
    """
    def resultado(estado, texto=None):
        return {"order": str(order.pk), "description": order.description,
                "status": estado, "message": MESSAGES[estado],
                "text_id": str(texto.id) if texto else None}

    vivo = (AiGeneratedText.objects
            .filter(kind=KIND, medical_order=order)
            .exclude(status=AiGeneratedText.Status.DISCARDED)
            .first())
    if vivo is not None:
        return resultado(EXISTS, vivo)

    servicio = source_for(order)
    if servicio is None:
        return resultado(NO_SOURCE)

    texto, autor, estado = "", "", GENERATED
    if provider_available():
        try:
            texto = _call_model(context(order, servicio))
        except Exception:
            logger.warning("US-40: el proveedor no respondió para la orden %s",
                           order.pk, exc_info=True)
            texto = ""
        autor = f"gemini:{settings.ASSISTANT_CHAT_MODEL}"
    if not texto:
        texto, autor, estado = catalog_text(order, servicio), "catalogo", FROM_CATALOG

    try:
        with transaction.atomic():
            creado = services.create_draft(kind=KIND, medical_order=order,
                                           text=texto, generated_by=autor)
    except IntegrityError:
        return resultado(EXISTS)
    return resultado(estado, creado)


def generate_for_encounter(encounter) -> list[dict]:
    """Las preparaciones de todas las órdenes de una atención firmada."""
    resultados = []
    for orden in encounter.orders.all():
        try:
            resultados.append(generate(orden))
        except Exception:
            # Ni una orden rara puede tumbar la firma.
            logger.exception("US-40: falló la preparación de la orden %s", orden.pk)
    return resultados


def _call_model(contexto: str) -> str:
    """La llamada al proveedor, sola, para que las pruebas la simulen."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY,
                          http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    response = client.models.generate_content(
        model=settings.ASSISTANT_CHAT_MODEL,
        contents=contexto,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )
    return (response.text or "").strip()
