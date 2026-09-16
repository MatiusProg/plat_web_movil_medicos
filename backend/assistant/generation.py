"""US-31, pieza 3 — La respuesta, y qué pasa cuando el proveedor no está.

El modelo responde **sólo** sobre los fragmentos recuperados. No se le da
acceso a nada más, y el prompt del sistema se lo repite. Aun así, un modelo
puede completar con conocimiento general, y por eso la respuesta viaja siempre
con la lista de fragmentos que la sustentan: es lo que permite comprobar de
dónde salió cada afirmación sin creerle al modelo.

**Qué pasa cuando el proveedor no responde.** El reparto lo fija: «el chat
degrada a *no puedo responder ahora*, nunca a una respuesta inventada sin
contexto». Acá eso tiene un matiz que importa y que conviene defender:

- Si **no hay proveedor de lenguaje** —no hay clave—, no se degrada a nada
  parecido a una charla. Se devuelven los fragmentos recuperados con una
  redacción armada por plantilla, **diciendo que es una redacción del sistema y
  no de un modelo**. Es útil, es verificable y no inventa: cada oración sale de
  un fragmento que viaja en la misma respuesta.
- Si **hay proveedor y falla** —red, cuota, clave vencida—, eso sí es «no puedo
  responder ahora»: el usuario esperaba una respuesta redactada y recibió un
  error, y disfrazarlo de respuesta escondería una caída.

La diferencia no es cosmética. La primera es el modo normal de la demostración
del 16/09 y de cualquier máquina sin clave; la segunda es una falla y tiene que
verse como tal.
"""

import logging
import os

from django.conf import settings

from . import triage

logger = logging.getLogger(__name__)

OPENAI_MODEL = "gpt-4o-mini"

# Cómo se generó el texto. Viaja en la respuesta para que quien la lea sepa
# qué está mirando.
MODEL = "model"          # lo redactó un modelo de lenguaje
TEMPLATE = "template"    # lo armó el sistema con los fragmentos
UNAVAILABLE = "unavailable"  # había proveedor y no respondió

# Cuánto peor que la mejor puede ser una especialidad y todavía ofrecerse como
# alternativa. Es una diferencia de distancias, así que no depende de la escala
# absoluta del proveedor —que sí varía— sino de cuánto se despegó la primera.
ALTERNATIVE_MARGIN = 0.05

SIN_CONTEXTO = (
    "No tengo esa información en el catálogo de este centro médico. "
    "Te conviene llamar por teléfono para consultarlo."
)

NO_DISPONIBLE = (
    "No puedo responder en este momento porque el servicio de asistencia no "
    "está disponible. Los datos que encontré en el catálogo están más abajo."
)


def _api_key() -> str:
    return (
        getattr(settings, "OPENAI_API_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
    ).strip()


def answer(question: str, fragments) -> dict:
    """Redacta la respuesta sobre los fragmentos. Devuelve texto y origen."""
    if not fragments:
        # Sin contexto no se llama al modelo. Llamarlo con una lista vacía es
        # pedirle que conteste de memoria, que es justo lo que no se quiere.
        return {"text": SIN_CONTEXTO, "source": TEMPLATE}

    if not _api_key():
        return {"text": _plantilla(fragments), "source": TEMPLATE}

    try:
        return {"text": _modelo(question, fragments), "source": MODEL}
    except Exception as error:  # noqa: BLE001
        logger.warning("El modelo de lenguaje no respondió: %s", error)
        return {"text": NO_DISPONIBLE, "source": UNAVAILABLE}


def _modelo(question: str, fragments) -> str:
    try:
        from openai import OpenAI
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise RuntimeError("El paquete «openai» no está instalado.") from error

    contexto = "\n\n".join(
        f"[{i}] {f.title} ({f.source_label})\n{f.content}"
        for i, f in enumerate(fragments, start=1)
    )

    cliente = OpenAI(api_key=_api_key(), timeout=25.0)
    respuesta = cliente.chat.completions.create(
        model=OPENAI_MODEL,
        # Temperatura baja: acá no se quiere variedad, se quiere que la misma
        # pregunta sobre el mismo catálogo dé la misma respuesta. Un asistente
        # sanitario que contesta distinto cada vez no se puede defender.
        temperature=0.2,
        max_tokens=300,
        messages=[
            {"role": "system", "content": triage.SYSTEM_RULES},
            {"role": "user", "content":
                f"Fragmentos del catálogo de este centro médico:\n\n{contexto}"
                f"\n\nConsulta de la persona: {question}"},
        ],
    )
    return (respuesta.choices[0].message.content or "").strip()


def _plantilla(fragments) -> str:
    """La redacción del sistema, sin modelo. Ver el encabezado del módulo.

    Cada oración sale de un fragmento que viaja en la misma respuesta, así que
    es comprobable renglón a renglón. No pretende sonar conversacional: eso
    sería fingir un modelo que no está.
    """
    especialidades = [f for f in fragments if f.source_type == "specialty"]
    otros = [f for f in fragments if f.source_type != "specialty"]

    partes = []
    if especialidades:
        principal = especialidades[0]
        partes.append(
            f"Por lo que contás, la especialidad que corresponde es "
            f"{principal.title}.",
        )
        # **Sólo las que compiten de verdad.** Pasaron el umbral, pero pasar el
        # umbral no es empatar: para «dolor en el pecho», Cardiología queda a
        # 0,78 y Ginecología a 0,93. Listar la segunda como alternativa es
        # sugerirle a alguien con dolor de pecho que quizá le corresponda una
        # ginecóloga, y el sistema estaría diciéndolo con el mismo tono con el
        # que acertó. Se ofrecen alternativas sólo si están cerca de la mejor.
        cercanas = [
            f for f in especialidades[1:3]
            if f.distance - principal.distance <= ALTERNATIVE_MARGIN
        ]
        if cercanas:
            resto = ", ".join(f.title for f in cercanas)
            partes.append(f"También podría corresponder: {resto}.")

    for fragmento in otros[:2]:
        partes.append(f"Sobre {fragmento.title}: {fragmento.content}")

    if not partes:
        return SIN_CONTEXTO

    partes.append(
        "Esta respuesta la armó el sistema con la información del catálogo "
        "que ves abajo, sin un modelo de lenguaje.",
    )
    return " ".join(partes)
