"""US-34 — Derivación a emergencia. Primera capa: las reglas del backend.

Está desde el primer día del endpoint por una razón práctica: mientras
``/suggest`` exista y no tenga esto, alguien puede escribir "me duele el pecho
y no puedo respirar" y el asistente contesta tranquilamente que reserve una
ficha de cardiología para la semana que viene. Publicar el endpoint sin la
barrera es publicar ese comportamiento.

**Las dos capas que pide el reparto, y cómo se reparten el trabajo:**

1. **Esta, las reglas.** Corre antes que todo y no depende de nadie: ni del
   proveedor, ni de la red, ni de un umbral. Es la que se prueba con un test.
2. **El prompt del sistema** (``generation.py``). Atrapa lo que la lista no
   nombra —"siento que me voy a morir", dicho de una forma que ninguna
   subcadena prevé—. El modelo no redacta la derivación: sólo levanta una
   marca, y el mensaje sale de acá. **Una capa sólo puede escalar, nunca
   desescalar**: si estas reglas disparan, el modelo ni se consulta.

Cada derivación, sea de la capa que sea, queda asentada en la bitácora de
US-06 (``views.py::_audit``).

⚠️ **Pendiente fuera del código:** el catálogo de señales tiene que revisarlo
alguien que sepa de clínica. Lo de abajo lo escribió quien programa, no quien
atiende.

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
    # Revisadas el 30/09/26 contra MedlinePlus y la OMS: cada grupo cita las
    # páginas que lo respaldan. Es respaldo en fuentes, no validación
    # clínica: la revisión de arriba sigue pendiente.
    #
    # Dos reglas de redacción, que salieron de esa revisión:
    #
    # - **Todas las conjugaciones que un paciente usa**, y también en tercera
    #   persona: muchas veces escribe un familiar ("no puede respirar", "se le
    #   durmió la mitad"). La coincidencia es por subcadena y no conjuga sola.
    # - **Nada que aparezca en una consulta normal.** "me tome" derivaba "me
    #   tomé la presión", y "hacerme dano" derivaba "¿la vacuna puede hacerme
    #   daño?". Una barrera que salta sin motivo deja de tomarse en serio.

    # Cardíacas y respiratorias.
    #   medlineplus.gov/spanish/ency/article/001927.htm (reconocer emergencias)
    #   medlineplus.gov/spanish/ency/article/000195.htm (ataque cardíaco)
    #   medlineplus.gov/spanish/ency/patientinstructions/000593.htm
    #   medlineplus.gov/spanish/ency/article/000067.htm (vía aérea)
    #
    # Las cuatro formas de decir lo mismo están todas, y no es redundancia:
    # la coincidencia es por subcadena, así que "me duele el pecho" no la
    # dispara por tener "dolor en el pecho" en la lista. Verificado el 16/09
    # contra el endpoint: "me duele el pecho cuando subo escaleras" contestaba
    # Cardiología y "tengo dolor en el pecho al subir escaleras" derivaba. Se
    # derivan las dos: el dolor de pecho con el esfuerzo es el cuadro típico
    # de la angina, y este módulo prefiere sobre-derivar.
    "dolor en el pecho", "dolor de pecho", "opresion en el pecho",
    "duele el pecho", "duele mucho el pecho", "presion en el pecho",
    "dolor en el torax", "dolor de torax", "me aprieta el pecho",
    "peso en el pecho", "algo pesado en el pecho", "se me cierra el pecho",
    "se me va al brazo", "me baja al brazo", "me corre al brazo",
    "estoy sudando frio", "me esta dando un infarto",
    "le esta dando un infarto",
    "no puedo respirar", "no puede respirar", "me falta el aire",
    "le falta el aire", "me cuesta respirar", "le cuesta respirar",
    "no me entra aire", "no le entra aire", "dejo de respirar",
    "no esta respirando", "me estoy ahogando", "se esta ahogando",
    "se atraganto", "se atoro con", "labios morados", "se puso morado",
    "se esta poniendo morado", "unas moradas",

    # Accidente cerebrovascular.
    #   medlineplus.gov/spanish/stroke.html
    #   medlineplus.gov/spanish/ency/article/000726.htm
    #   who.int/es/news-room/fact-sheets/detail/stroke
    # "no puedo hablar" se reemplazó: derivaba "no puedo hablar por teléfono
    # en ese horario".
    "de repente no puedo hablar", "no me salen las palabras", "hablo raro",
    "habla raro", "arrastra las palabras", "no entiende lo que le hablan",
    "se me duerme medio cuerpo", "se me durmio medio cuerpo",
    "se me duerme la mitad", "se me durmio la mitad",
    "se le durmio la mitad", "no siento la mitad", "no siento el brazo",
    "no siento la pierna", "perdi la fuerza", "se me tuerce la cara",
    "se me torcio la cara", "se me cayo la cara", "cara caida",
    "se me torcio la boca", "boca torcida", "boca chueca",
    "de repente no veo", "perdi la vista", "no veo de un ojo",
    "de repente veo doble", "el peor dolor de cabeza",
    "me esta dando un derrame", "le esta dando un derrame",

    # Convulsiones y pérdida de conocimiento.
    #   medlineplus.gov/spanish/ency/article/001927.htm
    #   medlineplus.gov/spanish/seizures.html
    "convulsion", "ataque epileptico",
    "desmayo", "me desmaye", "se desmayo", "perdida de conocimiento",
    "perdio el conocimiento", "no reacciona", "esta inconsciente",
    "no se despierta", "no lo puedo despertar", "no la puedo despertar",
    "no lo podemos despertar", "no la podemos despertar",

    # Hemorragias, traumatismos y accidentes.
    #   medlineplus.gov/spanish/ency/patientinstructions/000593.htm
    #   medlineplus.gov/spanish/ency/article/001927.htm
    # "sangra mucho" se reemplazó: derivaba "me sangra mucho la encía" y
    # "sangra mucho mi menstruación".
    "sangrado que no para", "no para de sangrar", "no deja de sangrar",
    "estoy sangrando mucho", "esta sangrando mucho", "sangrado abundante",
    "vomito con sangre", "vomite sangre", "vomita sangre", "tosi sangre",
    "toso sangre", "escupo sangre",
    "me golpee la cabeza", "se cayo de cabeza",
    "hueso salido", "fractura expuesta", "herida profunda", "corte profundo",
    "quemadura grave", "me electrocute", "se electrocuto",
    "descarga electrica", "le cayo un rayo", "accidente de transito",
    "me atropellaron", "lo atropellaron", "la atropellaron",
    "casi se ahoga", "inhale humo", "respire gas", "monoxido",

    # Intoxicaciones.
    #   medlineplus.gov/spanish/ency/article/007579.htm
    # "me tome" y "se tomo" se eliminaron: derivaban "me tomé la presión" y
    # "se tomó el medicamento que le recetaron".
    "intoxicacion", "sobredosis", "todas las pastillas", "tome veneno",
    "tomo veneno", "un veneno", "tomo lavandina", "se tomo lavandina",
    "trago lavandina", "se trago una pila", "liquido de limpieza",
    "raticida", "insecticida",

    # Reacción alérgica grave: la garganta que se cierra es la vía aérea.
    #   medlineplus.gov/spanish/ency/article/000844.htm
    "se me cierra la garganta", "se me cerro la garganta",
    "se me hincha la garganta", "se me hincha la lengua",
    "se me hincho la lengua", "se le hincho la lengua", "lengua hinchada",
    "se me hincharon los labios", "reaccion alergica grave", "anafilaxia",
    "anafilactico", "no puedo tragar ni respirar",

    # Salud mental: las que menos admiten una especialidad y un horario.
    #   medlineplus.gov/spanish/suicide.html
    #   medlineplus.gov/spanish/ency/article/001554.htm
    #   who.int/es/news-room/questions-and-answers/item/suicide
    # "hacerme dano" se reemplazó: derivaba "¿la vacuna puede hacerme daño?".
    "quiero morir", "me quiero morir", "no quiero vivir",
    "no quiero seguir viviendo", "no tengo razones para vivir",
    "no tengo por que vivir", "mejor estaria muerto", "mejor estaria muerta",
    "nadie me va a extranar", "nadie me extranaria",
    "quitarme la vida", "quitarse la vida", "matarme", "me quiero matar",
    "me voy a matar", "se quiere matar", "suicid",
    "quiero hacerme dano", "voy a hacerme dano", "lastimarme a proposito",
    "me corte las venas", "se corto las venas", "tome pastillas para morir",
    "quiero matar a",

    # Niños.
    #   medlineplus.gov/spanish/ency/patientinstructions/000594.htm
    #   medlineplus.gov/spanish/ency/patientinstructions/000319.htm
    "no moja el panal", "no moja los panales", "llora sin lagrimas",

    # Embarazo, en las formas que no necesitan combinarse con nada.
    #   medlineplus.gov/spanish/ency/patientinstructions/000508.htm
    #   medlineplus.gov/spanish/ency/patientinstructions/000627.htm
    "sangrado en el embarazo", "rompi fuente", "rompi bolsa",
    "se me rompio la fuente", "se me rompio la bolsa",
    "el bebe no se mueve", "mi bebe no se mueve", "el bebe se mueve menos",
    "contracciones muy fuertes",

    # Otras.
    #   medlineplus.gov/spanish/ency/article/001927.htm
    #   medlineplus.gov/spanish/ency/article/000982.htm (deshidratación)
    # "dolor muy fuerte" se acotó: derivaba "dolor muy fuerte de muelas".
    "dolor muy fuerte de repente", "dolor repentino muy fuerte",
    "el peor dolor de mi vida", "dolor insoportable",
    "dolor abdominal intenso", "dolor de barriga muy fuerte",
    "dolor de panza muy fuerte", "no puedo parar de vomitar",
    "no para de vomitar", "vomito todo lo que tomo",
    "no he orinado en todo el dia", "no orino desde ayer",
    "no reconoce a nadie", "no sabe donde esta", "esta delirando",
]

# Señales que sólo son urgencia **juntas**. Cada regla es una lista de grupos:
# dispara si aparece al menos una frase de **cada** grupo. Son las que una
# subcadena sola no puede expresar sin derivar consultas normales: "veo
# lucecitas" es el aura de una migraña, salvo en una embarazada; "cuello
# rigido" es una tortícolis, salvo con fiebre.
COMBINED_SIGNALS = [
    # Sangrado, pérdida de líquido o signos de preeclampsia en el embarazo.
    #   medlineplus.gov/spanish/ency/patientinstructions/000614.htm
    #   medlineplus.gov/spanish/ency/article/000898.htm
    [("embaraz",),
     ("sangr", "liquido", "lucecitas", "puntitos", "veo luces",
      "dolor de cabeza que no se va", "no se mueve")],
    # Fiebre en un bebé de tres meses o menos.
    #   medlineplus.gov/spanish/ency/patientinstructions/000319.htm
    [("fiebre",),
     ("recien nacido", "semanas de nacido", "de un mes", "de 1 mes",
      "de dos meses", "de 2 meses", "de tres meses", "de 3 meses")],
    # Fiebre con cuello rígido, confusión, llanto que no se calma o
    # dificultad para despertar.
    #   medlineplus.gov/spanish/headache.html
    #   medlineplus.gov/spanish/ency/patientinstructions/000319.htm
    [("fiebre",),
     ("cuello rigido", "cuello duro", "nuca rigida", "confundid",
      "no se calma", "no para de llorar", "cuesta despertar")],
    # Un golpe en la cabeza con vómitos, confusión, desmayo o sangrado.
    #   medlineplus.gov/spanish/ency/patientinstructions/000593.htm
    [("golpe", "se cayo", "caida"), ("cabeza",),
     ("vomit", "confundid", "desmay", "sangr", "convuls")],
    # Deshidratación: ojos hundidos o falta de orina, con vómitos o diarrea.
    #   medlineplus.gov/spanish/ency/article/000982.htm
    [("ojos hundidos", "no orina", "no hace pis"),
     ("vomit", "diarrea")],
]


@dataclass(frozen=True)
class TriageResult:
    is_emergency: bool
    matched: list
    message: str


EMERGENCY_MESSAGE = (
    "Por lo que describes, esto no se resuelve con una ficha programada. "
    "Ve ahora mismo al servicio de emergencias más cercano o llama al "
    "número de emergencias. No esperes a que te atiendan por consulta."
)


def check(question: str) -> TriageResult:
    """¿Lo que escribió el paciente exige emergencia en vez de una ficha?"""
    normalized = normalize_text(question)
    matched = [signal for signal in EMERGENCY_SIGNALS if signal in normalized]
    for groups in COMBINED_SIGNALS:
        hits = [
            next((phrase for phrase in group if phrase in normalized), None)
            for group in groups
        ]
        if all(hits):
            matched.append(" + ".join(hits))
    return TriageResult(
        is_emergency=bool(matched),
        matched=matched,
        message=EMERGENCY_MESSAGE if matched else "",
    )
