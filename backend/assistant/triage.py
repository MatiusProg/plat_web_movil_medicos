"""Barrera de seguridad del asistente — **semilla de US-34**.

US-34 (derivación a emergencia, 10 h, Must have, vence el 26/09) es una
historia entera y no es ésta. Lo que hay acá es su mitad imprescindible: la
validación **en el backend**, que es la que se puede probar con un test.

Está desde el primer día del endpoint por una razón práctica: mientras
``/suggest`` exista y no tenga esto, alguien puede escribir "me duele el pecho
y no puedo respirar" y el asistente contesta tranquilamente que reserve una
ficha de cardiología para la semana que viene. Publicar el endpoint sin la
barrera es publicar ese comportamiento.

Lo que US-34 todavía le debe a este módulo:

- las reglas duras **también en el prompt del sistema** —la del prompt sola no
  sirve, se la rodea conversando; la del backend sola no explica, corta—;
- el asiento en la bitácora de US-06 de cada derivación;
- el catálogo de señales revisado con alguien que sepa de clínica, porque lo
  de abajo lo escribió quien programa, no quien atiende;
- la pantalla que en el móvil corta el flujo de reserva y muestra a dónde ir.

**Cómo está escrito y por qué.** Coincidencia por texto normalizado, no por
similitud vectorial. Una barrera de seguridad tiene que ser explicable
—"disparó por esta frase"— y no puede depender de que un proveedor externo
responda ni de un umbral que se mueve. Se prefiere que sobre-derive: mandar a
emergencias a alguien que no lo necesitaba cuesta una consulta; no mandar a
quien sí, cuesta otra cosa.
"""

from dataclasses import dataclass

from .embeddings import normalize_text

# Señales que cortan el flujo. Normalizadas: sin tildes y en minúsculas, igual
# que lo que devuelve `normalize_text`.
EMERGENCY_SIGNALS = [
    # Cardiorrespiratorias.
    #
    # Las cuatro formas de decir lo mismo están todas, y no es redundancia:
    # la coincidencia es por subcadena, así que "me duele el pecho" no la
    # dispara por tener "dolor en el pecho" en la lista. Dos frases que un
    # paciente usa como sinónimos tienen que terminar en la misma respuesta;
    # que una derive a emergencias y la otra ofrezca una ficha de cardiología
    # para el jueves es peor que cualquiera de las dos decisiones tomada a
    # propósito. Verificado el 16/09 contra el endpoint: "me duele el pecho
    # cuando subo escaleras" contestaba Cardiología y "tengo dolor en el
    # pecho al subir escaleras" derivaba.
    #
    # Se derivan las dos, y la razón es clínica: el dolor de pecho que
    # aparece con el esfuerzo es el cuadro típico de la angina. Es la
    # política que este módulo ya declara arriba — se prefiere sobre-derivar.
    "dolor en el pecho", "dolor de pecho", "opresion en el pecho",
    "duele el pecho", "duele mucho el pecho", "presion en el pecho",
    "dolor en el torax", "dolor de torax",
    "no puedo respirar", "me falta el aire", "me cuesta respirar",
    "se me cierra el pecho",
    # Neurológicas.
    "no puedo hablar", "se me duerme medio cuerpo", "perdi la fuerza",
    "no siento el brazo", "se me tuerce la cara", "convulsion", "convulsiones",
    "desmayo", "me desmaye", "perdida de conocimiento",
    # Hemorragias y traumatismos.
    "sangrado que no para", "sangra mucho", "vomito con sangre",
    "me golpee la cabeza", "hueso salido", "fractura expuesta",
    # Otras.
    "intoxicacion", "me tome", "se tomo", "quemadura grave",
    "dolor muy fuerte", "dolor insoportable",
    "no reacciona", "esta inconsciente",
]


@dataclass(frozen=True)
class TriageResult:
    is_emergency: bool
    matched: list
    message: str


EMERGENCY_MESSAGE = (
    "Por lo que describís, esto no se resuelve con una ficha programada. "
    "Andá ahora mismo al servicio de emergencias más cercano o llamá al "
    "número de emergencias. No esperes a que te atiendan por consulta."
)


def check(question: str) -> TriageResult:
    """¿Lo que escribió el paciente exige emergencia en vez de una ficha?"""
    normalized = normalize_text(question)
    matched = [signal for signal in EMERGENCY_SIGNALS if signal in normalized]
    return TriageResult(
        is_emergency=bool(matched),
        matched=matched,
        message=EMERGENCY_MESSAGE if matched else "",
    )
