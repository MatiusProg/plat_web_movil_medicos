"""US-34 — Derivación a emergencia. La barrera de seguridad del asistente.

La historia pide **dos capas y las dos obligatorias**: las reglas duras en el
prompt del sistema y la validación en el backend. Esta es la segunda, y el
reparto explica por qué no alcanza con la primera: «la del prompt sola no
sirve —se la puede rodear conversando—; la del backend es la que se puede
probar con un test».

Hay una razón más, y es la que manda: **la detección corre antes de recuperar
y antes de llamar al modelo.** Si dependiera de la respuesta del modelo, una
caída del proveedor —que en este diseño degrada a «no puedo responder ahora»—
dejaría a alguien con un dolor de pecho sin la derivación. Acá, el aviso de
emergencia sale aunque no haya red, aunque no haya clave y aunque el catálogo
esté vacío.

**Es deliberadamente sensible al falso positivo.** Derivar a emergencia a
alguien que no la necesita cuesta una consulta de más. No derivar a alguien que
sí, cuesta otra cosa. Por eso los patrones son amplios y la nota lo dice: no es
un diagnóstico, es un «andá a que te vean ahora».

**No es un diagnóstico y el sistema no debe pretender que lo sea.** El texto
que devuelve no nombra ninguna enfermedad: dice que lo descrito puede ser una
urgencia y a dónde ir.
"""

import re
import unicodedata
from dataclasses import dataclass

# Cada patrón es una expresión regular sobre el texto ya normalizado
# —minúsculas, sin tildes—. Se agrupan por motivo para que el registro diga
# **qué** disparó la derivación y no sólo que se disparó: sin eso, revisar
# falsos positivos es imposible.
#
# Las expresiones admiten variantes de escritura porque esto lo escribe alguien
# asustado desde un teléfono: «no puedo respirar», «no puedo respira», «me
# falta el aire».
PATTERNS: list[tuple[str, str]] = [
    ("dolor_de_pecho",
     r"\bdolor(es)?\s+(fuerte\s+|intenso\s+|agudo\s+)?"
     r"(en\s+el\s+|de\s+|al\s+)?pecho\b"
     r"|\bopresion\s+en\s+el\s+pecho\b"
     r"|\bpuntada\s+en\s+el\s+pecho\b"),

    ("dificultad_para_respirar",
     r"\bno\s+puedo\s+respira"
     r"|\bme\s+falta\s+(el\s+)?aire\b"
     r"|\bdificultad\s+para\s+respirar\b"
     r"|\bme\s+ahogo\b|\bahogo\b|\basfixia"),

    ("perdida_de_conciencia",
     r"\bse\s+desmay|\bme\s+desmay|\bdesmayo\b"
     r"|\bperdi(o|do)?\s+(el\s+)?conocimiento\b"
     r"|\bno\s+(responde|reacciona)\b|\binconsciente\b"),

    ("signos_de_acv",
     r"\bno\s+puedo\s+hablar\b|\bse\s+le\s+trab(a|o)\s+la\s+lengua\b"
     r"|\bboca\s+torcida\b|\bcara\s+torcida\b"
     r"|\bno\s+(puedo|siento)\s+mover\s+(el|la|un|una)\b"
     r"|\bparalisis\b|\bparte\s+del\s+cuerpo\s+dormida\b"),

    ("sangrado_abundante",
     r"\bsangr(a|ado|e)\s+(mucho|abundante|sin\s+parar|a\s+chorros)\b"
     r"|\bhemorragia\b|\bno\s+para\s+de\s+sangrar\b"
     r"|\bvomito\s+sangre\b|\bvomita\s+sangre\b"),

    ("intoxicacion",
     r"\bse\s+(tomo|trago)\b.*\b(veneno|lavandina|pastillas|remedios)\b"
     r"|\bintoxic|\benvenen|\bsobredosis\b"),

    ("traumatismo_grave",
     r"\bse\s+(cayo|golpeo)\s+(la\s+)?cabeza\b|\bgolpe\s+en\s+la\s+cabeza\b"
     r"|\baccidente\s+(de\s+)?(transito|auto|moto)\b"
     r"|\bfractura\s+expuesta\b|\bhueso\s+(salido|expuesto)\b"),

    ("convulsiones",
     r"\bconvulsion|\bconvulsiona\b|\bataque\s+de\s+epilepsia\b"
     r"|\bespasmos\s+(fuertes|incontrolables)\b"),

    ("riesgo_autolesion",
     r"\bquiero\s+(matarme|morirme)\b|\bme\s+quiero\s+matar\b"
     r"|\bsuicid|\bhacerme\s+dano\b|\bno\s+quiero\s+vivir\b"),

    ("embarazo_de_riesgo",
     r"\bembarazada\b.*\b(sangr|perdida|dolor\s+fuerte|no\s+se\s+mueve)\b"
     r"|\bromp(i|io)\s+(la\s+)?(bolsa|fuente)\b"
     r"|\bcontracciones\b.*\b(fuertes|seguidas)\b"),

    ("fiebre_alta_en_lactante",
     r"\b(bebe|recien\s+nacido|lactante)\b.*\b(fiebre|convuls|no\s+despierta)\b"),
]

_COMPILADOS = [(motivo, re.compile(patron)) for motivo, patron in PATTERNS]

# Lo que se responde. No nombra ninguna enfermedad a propósito: el asistente no
# diagnostica, y decir «puede ser un infarto» sería exactamente eso.
MESSAGE = (
    "Por lo que describís, esto puede ser una urgencia médica. "
    "No esperes a sacar una ficha: acudí de inmediato al servicio de "
    "emergencias más cercano o llamá al número de emergencias de tu zona. "
    "Si la persona está inconsciente, no respira o sangra sin parar, pedí "
    "ayuda ahora mismo."
)


@dataclass
class Triage:
    """El resultado de la evaluación previa."""

    is_emergency: bool
    reasons: list[str]

    def as_dict(self) -> dict:
        return {
            "is_emergency": self.is_emergency,
            "reasons": self.reasons,
            "message": MESSAGE if self.is_emergency else "",
        }


def normalize(texto: str) -> str:
    """Minúsculas, sin tildes y con los espacios colapsados.

    Mismo criterio que ``embeddings._normalizar`` y que la búsqueda de US-16.
    Sin colapsar los espacios, «dolor  de   pecho» —lo que sale de escribir
    apurado— no coincide con ningún patrón.
    """
    plano = unicodedata.normalize("NFKD", (texto or "").lower())
    sin_tildes = "".join(c for c in plano if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes).strip()


def evaluate(question: str) -> Triage:
    """¿Lo que describe esta persona es una urgencia?

    Devuelve **todos** los motivos que coincidieron, no el primero: «dolor de
    pecho y no puedo respirar» son dos, y quien después revise los falsos
    positivos necesita ver los dos para entender qué disparó.
    """
    texto = normalize(question)
    motivos = [motivo for motivo, patron in _COMPILADOS if patron.search(texto)]
    return Triage(is_emergency=bool(motivos), reasons=motivos)


# El bloque que se le antepone al modelo de lenguaje. Es la **primera** capa:
# no reemplaza a `evaluate`, la acompaña. Si las dos discrepan, manda el
# backend, porque es la que no se puede rodear conversando.
SYSTEM_RULES = """\
Sos el asistente de orientación de un centro médico. Tenés tres reglas y
ninguna admite excepción:

1. Respondé ÚNICAMENTE con la información de los fragmentos que te paso. Si la
   respuesta no está ahí, decí que no tenés esa información y sugerí llamar al
   centro médico. No completes con conocimiento general.
2. NO diagnostiques, no nombres enfermedades y no indiques tratamientos ni
   medicamentos. Tu trabajo es orientar hacia la especialidad adecuada.
3. Si lo que describe la persona puede ser una urgencia —dolor de pecho,
   dificultad para respirar, pérdida de conocimiento, sangrado abundante,
   convulsiones, intoxicación, riesgo de autolesión—, dejá todo lo demás y
   decile que acuda de inmediato a emergencias.

Escribí en español rioplatense, en dos o tres oraciones, sin listas y sin
saludos largos.\
"""
