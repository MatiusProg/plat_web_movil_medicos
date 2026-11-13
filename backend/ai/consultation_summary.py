"""US-39 — El resumen de la consulta, en palabras del paciente.

Al firmar la atención, la IA redacta un texto corto y llano —qué se encontró,
qué hay que hacer, cuándo volver— que el paciente lee en la app **después de
que su médico lo apruebe** (US-42, regla 14 del Sprint 4).

Tres decisiones, del reparto:

1. **Sale de la atención firmada y su receta, nada más.** El prompt lleva
   motivo, diagnóstico, indicaciones, tratamiento, receta y órdenes de *esa*
   atención. No va el nombre ni el documento del paciente, ni ninguna otra
   atención: el modelo no necesita saber quién es para explicarle lo que le
   dijeron.
2. **Sin proveedor, no se genera, y se dice.** No hay plantilla de reemplazo:
   un resumen armado por reglas se lee como si lo hubiera revisado alguien.
   El médico ve «no se generó» y puede reintentar más tarde.
3. **Nace en borrador.** Lo que devuelve el modelo va a la bandeja del médico
   tal cual, con las advertencias de :func:`warnings` a la vista. El médico es
   el filtro; este módulo sólo le facilita la revisión.

**Firmar nunca falla por el resumen.** La firma es la historia clínica; el
resumen es un servicio para el paciente. Si el modelo tarda, se cae o se
queda sin cuota, la atención queda firmada igual y el resumen se reintenta.
"""

from __future__ import annotations

import logging
import unicodedata

from django.conf import settings
from django.db import IntegrityError, transaction

from . import services
from .models import AiGeneratedText

logger = logging.getLogger(__name__)

KIND = AiGeneratedText.Kind.CONSULTATION_SUMMARY

# Por sección, para que una evolución larga no se coma el prompt ni la cuota.
MAX_FIELD_CHARS = 1500
# El resumen tiene que leerse en un minuto en el teléfono.
MAX_OUTPUT_TOKENS = 600
# Firmar espera al modelo: más que esto y el médico cree que se colgó.
TIMEOUT_MS = 20_000

# Los resultados posibles de :func:`generate`, que el médico ve al firmar.
GENERATED = "generated"          # quedó en su bandeja, pendiente de validar
EXISTS = "exists"                # ya había uno vivo para esta atención
UNAVAILABLE = "unavailable"      # no hay proveedor configurado
FAILED = "failed"                # el proveedor no respondió o respondió vacío

MESSAGES = {
    GENERATED: "El resumen para el paciente quedó en «Textos por validar».",
    EXISTS: "Esta atención ya tiene un resumen para el paciente.",
    UNAVAILABLE: "El resumen para el paciente no se generó: la IA no está "
                 "disponible en este momento.",
    FAILED: "El resumen para el paciente no se generó: la IA no respondió. "
            "Puedes reintentarlo más tarde.",
}

SYSTEM_PROMPT = """\
Eres un asistente que ayuda a un médico a explicarle a su paciente lo que pasó
en la consulta. Recibes los datos de UNA atención ya firmada por el médico.
Escribes, en español de Bolivia y tratando al paciente de tú, un resumen claro
para que lo lea en su teléfono.

Reglas, sin excepción:
- Usa SOLO lo que está en los datos. No agregues diagnósticos, medicamentos,
  dosis, estudios, causas, pronósticos ni consejos que no estén escritos ahí.
- Si un dato no está (por ejemplo, cuándo volver), no lo inventes: di que lo
  consulte con su médico.
- Copia los medicamentos con el mismo nombre, dosis, frecuencia y duración de
  la receta.
- Si el tratamiento describe lo mismo que la receta (por ejemplo, "analgésico
  por cinco días" y la receta dice cuál), nombra sólo el medicamento de la
  receta, una vez: que no parezcan dos medicamentos distintos.
- Explica las palabras médicas con palabras simples, sin cambiar su sentido.
- No saludes ni firmes. No uses el nombre del paciente.
- Escribe en texto plano, sin markdown ni asteriscos, con estos tres títulos
  exactos, cada uno en su línea y seguido de frases cortas:
Qué encontramos
Qué tienes que hacer
Cuándo volver
"""


def _cut(text: str) -> str:
    text = (text or "").strip()
    return text if len(text) <= MAX_FIELD_CHARS else text[:MAX_FIELD_CHARS] + "…"


def data_of(encounter) -> dict:
    """Los campos de esta atención que se le explican al paciente, y nada más."""
    return {
        "reason": encounter.reason,
        "diagnosis": encounter.diagnosis,
        "indications": encounter.indications,
        "treatment": encounter.treatment,
        "prescription": [
            {"medication": i.medication, "dose": i.dose, "frequency": i.frequency,
             "duration": i.duration, "instructions": i.instructions}
            for i in encounter.prescription_items.all()
        ],
        "orders": [
            {"kind": o.get_kind_display(), "description": o.description, "notes": o.notes}
            for o in encounter.orders.all()
        ],
    }


def context(encounter) -> str:
    """Lo que ve el modelo. Aparte y pública para que la prueba verifique qué
    sale hacia el proveedor."""
    return context_from(data_of(encounter))


def context_from(datos: dict) -> str:
    """El texto del prompt a partir de los datos de una atención.

    Separado de :func:`context` para que el conjunto de casos de la regla 15
    (`evaluate_consultation_summary`) arme atenciones sin tocar la base.
    """
    partes = []
    for campo, titulo in [
        ("reason", "Motivo de consulta"),
        ("diagnosis", "Diagnóstico"),
        ("indications", "Indicaciones"),
        ("treatment", "Tratamiento"),
    ]:
        valor = _cut(datos.get(campo, ""))
        if valor:
            partes.append(f"{titulo}: {valor}")

    receta = datos.get("prescription") or []
    if receta:
        partes.append("Receta:")
        for item in receta:
            linea = (f"- {item['medication']}, {item['dose']}, {item['frequency']}, "
                     f"durante {item['duration']}")
            if item.get("instructions"):
                linea += f". {item['instructions']}"
            partes.append(linea)

    ordenes = datos.get("orders") or []
    if ordenes:
        partes.append("Estudios pedidos:")
        for orden in ordenes:
            linea = f"- {orden['kind']}: {orden['description']}"
            if orden.get("notes"):
                linea += f" ({orden['notes']})"
            partes.append(linea)
    return "\n".join(partes)


def _normalize(text: str) -> str:
    sin_tildes = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in sin_tildes if not unicodedata.combining(c))


def warnings(encounter, text: str) -> list[str]:
    """Lo que el médico debería mirar dos veces antes de aprobar.

    No se descarta nada por esto: la regla de qué llega al paciente es la
    aprobación del médico. Sólo se le avisa de lo que se puede comprobar sin
    entender el texto: que falte un medicamento de la receta o uno de los
    tres apartados.
    """
    return warnings_for([i.medication for i in encounter.prescription_items.all()], text)


SECTIONS = ("Qué encontramos", "Qué tienes que hacer", "Cuándo volver")


def warnings_for(medications: list[str], text: str) -> list[str]:
    normal = _normalize(text)
    avisos = [
        f"No menciona «{medicamento}», que está en la receta."
        for medicamento in medications
        if medicamento.split() and _normalize(medicamento.split()[0]) not in normal
    ]
    for titulo in SECTIONS:
        if _normalize(titulo) not in normal:
            avisos.append(f"Falta el apartado «{titulo}».")
    return avisos


def provider_available() -> bool:
    return settings.ASSISTANT_CHAT_PROVIDER == "gemini" and bool(settings.GEMINI_API_KEY)


def generate(encounter) -> dict:
    """Genera el resumen de una atención firmada y lo deja en borrador.

    Devuelve ``{"status": ..., "message": ..., "text_id": ...}``. **Nunca
    lanza:** lo llama la firma, y la firma no puede caerse por esto.
    """
    def resultado(estado, texto=None):
        return {"status": estado, "message": MESSAGES[estado],
                "text_id": str(texto.id) if texto else None}

    vivo = (AiGeneratedText.objects
            .filter(kind=KIND, encounter=encounter)
            .exclude(status=AiGeneratedText.Status.DISCARDED)
            .first())
    if vivo is not None:
        return resultado(EXISTS, vivo)
    if not provider_available():
        return resultado(UNAVAILABLE)

    try:
        texto = _call_model(context(encounter))
    except Exception:
        # Cuota, red, 503: el médico no lee la traza, lee «no se generó».
        logger.warning("US-39: el proveedor no respondió para la atención %s",
                       encounter.pk, exc_info=True)
        texto = ""
    if not texto:
        return resultado(FAILED)

    try:
        with transaction.atomic():
            creado = services.create_draft(kind=KIND, encounter=encounter, text=texto,
                                           generated_by=f"gemini:{settings.ASSISTANT_CHAT_MODEL}")
    except IntegrityError:
        # Dos pedidos a la vez para la misma atención: ganó el otro.
        return resultado(EXISTS)
    return resultado(GENERATED, creado)


def _call_model(contexto: str) -> str:
    """La llamada al proveedor, sola, para que las pruebas la simulen."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY,
                          http_options=types.HttpOptions(timeout=TIMEOUT_MS))
    response = client.models.generate_content(
        model=settings.ASSISTANT_CHAT_MODEL,
        contents=f"Datos de la atención:\n\n{contexto}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    )
    return (response.text or "").strip()
