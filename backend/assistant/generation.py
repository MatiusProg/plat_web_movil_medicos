"""US-31, pieza 4 — La respuesta. Lo último que pasa, y lo menos importante.

El orden del RAG es recuperar y después responder. Si la recuperación
funciona, la redacción es casi decorativa; si la recuperación falla, ningún
modelo de lenguaje lo arregla: inventa.

Por eso este módulo hace **una sola cosa**, y es negarse:

- el prompt del sistema prohíbe usar cualquier cosa que no esté en los
  fragmentos, y prohíbe nombrar una especialidad que no aparezca en ellos;
- si no hay fragmentos, no se llama al proveedor. No hay nada que redactar, y
  llamarlo igual es pedirle explícitamente que se invente la respuesta;
- si el proveedor no responde, **se degrada**, nunca se improvisa.

**Qué significa degradar acá.** El reparto exige que el chat caiga a "no puedo
responder ahora" y jamás a una respuesta inventada sin contexto. La frase de
respaldo de ``_grounded_fallback`` cumple eso: no la escribe un modelo, la
arma esta función con el nombre de la especialidad que ya salió de la
búsqueda por similitud. No agrega ni un dato que no estuviera en el índice.
Y la respuesta del endpoint dice ``generated_by: "plantilla"``, así que quien
la lee sabe que el modelo de lenguaje no participó.
"""

from django.conf import settings

SYSTEM_PROMPT = """\
Sos el asistente de orientación de un centro médico. Tu única tarea es decir a
qué especialidad del centro le corresponde la consulta de la persona.

Reglas, sin excepción:
- Respondé usando SÓLO la información de los fragmentos que siguen. No uses
  conocimiento propio.
- No nombres ninguna especialidad que no aparezca en los fragmentos.
- No diagnostiques, no sugieras estudios y no menciones medicamentos.
- Si los fragmentos no alcanzan para decidir, decí que no podés orientar y
  recomendá Medicina general.
- Dos o tres oraciones, en español rioplatense neutro, tuteando.
- Cerrá diciendo que la sugerencia es orientativa y que la confirma el
  profesional.
"""


def _grounded_fallback(specialty_name: str) -> str:
    """Frase de respaldo, armada con lo recuperado y con nada más."""
    if not specialty_name:
        return (
            "No puedo orientarte con lo que me contaste. Te conviene sacar "
            "una ficha de Medicina general, que es la consulta de primer "
            "contacto."
        )
    return (
        f"Por lo que me contás, la especialidad que mejor corresponde es "
        f"{specialty_name}. Es una sugerencia orientativa: la confirma el "
        f"profesional cuando te atienda."
    )


def answer(question: str, fragments: list, specialty_name: str = "") -> dict:
    """Redacta la respuesta sobre los fragmentos recuperados.

    Devuelve ``{"text": str, "generated_by": "gemini"|"plantilla"}``. Nunca
    lanza: una falla del proveedor no puede tumbar el endpoint, sólo bajar la
    calidad de la redacción de forma visible.
    """
    if not fragments:
        return {"text": _grounded_fallback(""), "generated_by": "plantilla"}

    if settings.ASSISTANT_CHAT_PROVIDER != "gemini" or not settings.GEMINI_API_KEY:
        return {
            "text": _grounded_fallback(specialty_name),
            "generated_by": "plantilla",
        }

    context = "\n".join(f"- {fragment.text}" for fragment in fragments)
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.ASSISTANT_CHAT_MODEL,
            contents=(
                f"Fragmentos del catálogo:\n{context}\n\n"
                f"Consulta de la persona: {question}"
            ),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                # Baja y no cero: cero no garantiza determinismo y tampoco
                # hace falta. Lo que se busca es que no adorne.
                temperature=0.2,
                max_output_tokens=300,
            ),
        )
        text = (response.text or "").strip()
    except Exception:
        # Se traga a propósito y sin registrar el detalle en la respuesta: el
        # paciente no tiene por qué leer un error de cuota. Queda el
        # `generated_by` para que se note desde afuera.
        text = ""

    if not text:
        return {
            "text": _grounded_fallback(specialty_name),
            "generated_by": "plantilla",
        }
    return {"text": text, "generated_by": "gemini"}
