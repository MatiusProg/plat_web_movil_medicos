"""Referencia médica del asistente — motivos de consulta por especialidad.

El asistente sugiere especialidad comparando lo que escribe el paciente contra
fragmentos de texto. Hasta ahora esos fragmentos eran sólo la descripción que
cada organización carga en su catálogo, escrita por quien programa o por quien
administra el centro, no por quien atiende. Este módulo agrega, para las
especialidades más comunes, **motivos de consulta tomados de fuentes de salud
públicas y verificables**.

**Qué es y qué no es.**

- Es texto para **recuperar**: sirve para que "me silba el pecho de noche"
  se parezca a Neumología. No es texto para diagnosticar, y el prompt del
  sistema le sigue prohibiendo al modelo diagnosticar, sugerir estudios o
  mencionar medicamentos.
- **No está validado por un profesional de la salud.** Está respaldado por
  fuentes, que no es lo mismo. Cada oración cita las páginas de donde salió,
  para que cualquiera pueda comprobarla, y la revisión clínica sigue
  pendiente.

**De dónde sale.** De MedlinePlus en español (Biblioteca Nacional de Medicina
de EE. UU.), sus páginas de *temas de salud* —dominio público— y de las notas
descriptivas de la OMS. Las oraciones están **redactadas con palabras propias**,
en lenguaje de paciente y con tuteo, no copiadas: el repositorio es público,
y la enciclopedia A.D.A.M. que MedlinePlus también aloja tiene derechos de
autor. Fuente: MedlinePlus, Biblioteca Nacional de Medicina de EE. UU.

**Cómo entra al índice.** Ver ``indexing.fragments_for``: sólo para las
especialidades que la organización **ya tiene**, reconocidas por su nombre o
por un alias, y siempre detrás de la descripción propia del centro. Una
especialidad que el centro no ofrece nunca aparece por venir de acá.

**Cómo se agrega una especialidad o una oración.** Cada oración tiene que
poder leerse sola —se vectoriza sola— y tiene que citar al menos una URL que
alguien haya leído. Sin URL no entra. Después de cambiar este archivo hay que
reindexar (``embed_catalog --all``) y volver a medir el umbral de similitud
(ver ``config/settings.py``).

**Las señales de alarma no van acá.** Ir a urgencias no es una especialidad:
eso lo decide ``triage.py`` antes de que se recupere nada.
"""

from dataclasses import dataclass

from .embeddings import normalize_text

# Fecha de la última revisión del contenido contra las fuentes.
REVIEWED_ON = "2026-09-30"


@dataclass(frozen=True)
class Sentence:
    """Una oración recuperable, con las páginas que la respaldan."""

    text: str
    sources: tuple


@dataclass(frozen=True)
class Reference:
    """Los motivos de consulta de una especialidad."""

    name: str
    # Otros nombres con que un centro puede llamar a la misma especialidad.
    # **No salen de ninguna fuente**: son convención de nombres, y la
    # coincidencia es exacta a propósito. "Cirugía cardiovascular" no es
    # Cardiología, y una coincidencia por subcadena la mezclaría.
    aliases: tuple
    sentences: tuple


MEDLINE = "https://medlineplus.gov/spanish/"
# Enciclopedia A.D.A.M.: sólo como fuente de hechos. Ninguna frase copiada.
ENCY = "https://medlineplus.gov/spanish/ency/article/"
WHO ="https://www.who.int/es/news-room/fact-sheets/detail/"


REFERENCES = (
    # ------------------------------------------------------------------
    Reference(
        name="Medicina general",
        aliases=(
            "medicina familiar", "medicina interna", "consulta externa",
            "clinica medica", "clinica general", "medico general",
        ),
        sentences=(
            Sentence(
                "Fiebre, escalofríos, dolor de cuerpo o de músculos, dolor de "
                "cabeza y cansancio que empezaron de golpe, como en una gripe.",
                (MEDLINE + "flu.html", MEDLINE + "fever.html"),
            ),
            Sentence(
                "Estornudos, nariz tapada o con mocos, dolor de garganta y tos "
                "de pocos días, como en un resfrío.",
                (MEDLINE + "commoncold.html", MEDLINE + "sorethroat.html",
                 MEDLINE + "cough.html"),
            ),
            Sentence(
                "Ardor o dolor al orinar, ganas de orinar muy seguido, presión "
                "en la parte baja de la barriga u orina turbia, rojiza o con "
                "mal olor.",
                (MEDLINE + "urinarytractinfections.html",),
            ),
            Sentence(
                "Dolor de barriga leve que dura una semana o más, o que viene "
                "acompañado de otras molestias.",
                (MEDLINE + "abdominalpain.html",),
            ),
            Sentence(
                "Cansancio, agotamiento o falta de energía que no mejora "
                "después de varias semanas, o dolores de cabeza comunes que se "
                "repiten.",
                (MEDLINE + "fatigue.html", MEDLINE + "headache.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Cardiología",
        aliases=("cardiologia clinica", "cardiologo"),
        sentences=(
            Sentence(
                "Dolor, presión u opresión en el pecho que aparece al hacer "
                "esfuerzo, como caminar o subir escaleras, y que puede irse "
                "hacia los hombros, los brazos, el cuello, la mandíbula o la "
                "espalda.",
                (MEDLINE + "angina.html", MEDLINE + "chestpain.html"),
            ),
            Sentence(
                "Palpitaciones: sentir que el corazón late muy rápido, muy "
                "lento, muy fuerte, que se salta latidos o que aletea, a veces "
                "con mareos.",
                (MEDLINE + "arrhythmia.html",),
            ),
            Sentence(
                "Hinchazón de los tobillos, las piernas o la barriga, subida "
                "de peso por líquido, y problemas para dormir estando "
                "acostado.",
                (MEDLINE + "heartfailure.html",),
            ),
            Sentence(
                "Falta de aire, cansancio o debilidad que no se pasan ni "
                "después de descansar.",
                (MEDLINE + "heartfailure.html", MEDLINE + "arrhythmia.html"),
            ),
            Sentence(
                "Presión arterial alta encontrada en un control, aunque no "
                "tengas molestias, porque la presión alta casi nunca da "
                "síntomas.",
                (MEDLINE + "highbloodpressure.html",),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Neumología",
        aliases=(
            "neumonologia", "neumologia clinica", "enfermedades respiratorias",
            "neumologo",
        ),
        sentences=(
            Sentence(
                "Tos que dura más de dos o tres semanas, con flema o sin ella.",
                (MEDLINE + "cough.html", MEDLINE + "copd.html"),
            ),
            Sentence(
                "Silbido en el pecho al soltar el aire, pecho apretado y tos "
                "que empeora de noche o temprano en la mañana.",
                (MEDLINE + "asthma.html", WHO + "asthma"),
            ),
            Sentence(
                "Falta de aire o ahogo al hacer esfuerzo, tos frecuente con "
                "mucha flema y cansancio, sobre todo si fumas o fumaste.",
                (MEDLINE + "copd.html",
                 WHO + "chronic-obstructive-pulmonary-disease-(copd)",
                 MEDLINE + "breathingproblems.html"),
            ),
            Sentence(
                "Tos que no se va, a veces con sangre, junto con fiebre, "
                "sudores de noche, pérdida de peso y cansancio.",
                (WHO + "tuberculosis",),
            ),
            Sentence(
                "Ronquidos muy fuertes, pausas en la respiración mientras "
                "duermes y mucho sueño durante el día.",
                (MEDLINE + "sleepapnea.html",),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Endocrinología",
        aliases=(
            "endocrinologia y metabolismo", "endocrinologia y nutricion",
            "diabetologia", "endocrinologo",
        ),
        sentences=(
            Sentence(
                "Mucha sed, mucha hambre, orinar muy seguido incluso de noche, "
                "y bajar de peso sin intentarlo.",
                (MEDLINE + "diabetes.html", WHO + "diabetes"),
            ),
            Sentence(
                "Visión borrosa, hormigueo o adormecimiento en las manos o los "
                "pies, y heridas que tardan mucho en sanar.",
                (MEDLINE + "diabetes.html", WHO + "diabetes"),
            ),
            Sentence(
                "Nerviosismo, irritabilidad, temblores, no aguantar el calor, "
                "problemas para dormir, corazón acelerado y bajar de peso.",
                (MEDLINE + "hyperthyroidism.html",),
            ),
            Sentence(
                "Cansancio, subida de peso, cara hinchada, mucho frío, piel y "
                "cabello secos, estreñimiento y reglas irregulares.",
                (MEDLINE + "hypothyroidism.html",),
            ),
            Sentence(
                "Bulto o agrandamiento en la parte de adelante del cuello, "
                "donde está la tiroides.",
                (MEDLINE + "thyroiddiseases.html",
                 MEDLINE + "hyperthyroidism.html",
                 MEDLINE + "hypothyroidism.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Dermatología",
        aliases=("dermatologia clinica", "dermatologo"),
        sentences=(
            Sentence(
                "Granos, barros o espinillas en la cara, el cuello, la "
                "espalda, el pecho o los hombros, y miedo a que dejen marcas.",
                (MEDLINE + "acne.html",),
            ),
            Sentence(
                "Una zona de la piel roja, irritada o inflamada que pica, arde "
                "o duele, a veces con ampollas, partes en carne viva o ronchas "
                "rojizas que pican.",
                (MEDLINE + "rashes.html", MEDLINE + "itching.html",
                 MEDLINE + "skinconditions.html", MEDLINE + "hives.html"),
            ),
            Sentence(
                "Manchas rojas con escamas que pican, el cuero cabelludo que "
                "se descama, o la piel seca, enrojecida e irritada.",
                (MEDLINE + "skinconditions.html", MEDLINE + "itching.html"),
            ),
            Sentence(
                "Un lunar que crece, cambia de color o de forma o se ve "
                "irregular, una llaga que no sana, o cualquier cambio raro en "
                "el aspecto de la piel.",
                (MEDLINE + "moles.html", MEDLINE + "skincancer.html"),
            ),
            Sentence(
                "Se te cae más cabello de lo normal, o las uñas cambiaron de "
                "color, se pusieron gruesas o amarillas, tienen hongos o se "
                "encarnaron.",
                (MEDLINE + "hairloss.html", MEDLINE + "naildiseases.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Traumatología",
        aliases=(
            "ortopedia", "ortopedia y traumatologia",
            "traumatologia y ortopedia", "traumatologo",
        ),
        sentences=(
            Sentence(
                "Te torciste el tobillo, la muñeca, el pie, el codo o el "
                "pulgar, y está hinchado, con moretón, duele y no lo puedes "
                "mover bien; a veces se sintió un chasquido al lastimarte.",
                (MEDLINE + "sprainsandstrains.html",),
            ),
            Sentence(
                "Un tirón en un músculo de la espalda, de la parte de atrás "
                "del muslo o de la cadera, con dolor, espasmos, hinchazón y "
                "dificultad para moverlo.",
                (MEDLINE + "sprainsandstrains.html",),
            ),
            Sentence(
                "Dolor de espalda sordo y constante o de golpe e intenso, que "
                "empezó hace poco, que dura más de tres meses, o que apareció "
                "después de una lesión.",
                (MEDLINE + "backpain.html",),
            ),
            Sentence(
                "Articulaciones que duelen, están rígidas, enrojecidas o "
                "hinchadas, que se sienten flojas o se ven raras, o que duelen "
                "al moverlas.",
                (MEDLINE + "jointdisorders.html",),
            ),
            Sentence(
                "Dolor de rodilla, sobre todo por delante o después de un giro "
                "brusco haciendo deporte, o dolor de hombro después de una "
                "torcedura o de que se saliera de su lugar.",
                (MEDLINE + "kneeinjuriesanddisorders.html",
                 MEDLINE + "shoulderinjuriesanddisorders.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Neurología",
        aliases=("neurologia clinica", "neurologo"),
        sentences=(
            Sentence(
                "Dolores de cabeza frecuentes, a veces con tensión en el "
                "cuello, los hombros o la mandíbula, o un dolor que late en un "
                "lado de la cabeza con náuseas y molestia con la luz y el "
                "ruido, a veces anunciado por luces o líneas en zigzag.",
                (MEDLINE + "headache.html", MEDLINE + "migraine.html"),
            ),
            Sentence(
                "Hormigueo, adormecimiento o dolor en las manos y los pies, "
                "debilidad o calambres en los músculos, o dificultad para "
                "mantener el equilibrio, caminar o usar las manos.",
                (MEDLINE + "peripheralnervedisorders.html",
                 MEDLINE + "neurologicdiseases.html"),
            ),
            Sentence(
                "Temblor en las manos, los brazos, las piernas, la cabeza o la "
                "voz, que hace difícil escribir o sostener una cuchara.",
                (MEDLINE + "tremor.html",),
            ),
            Sentence(
                "Mareo o sensación de que tú o la habitación dan vueltas, "
                "inestabilidad al caminar, que empeora al levantarte o al "
                "mover la cabeza.",
                (MEDLINE + "dizzinessandvertigo.html",),
            ),
            Sentence(
                "Olvidar cosas más seguido que otras personas de tu edad, "
                "costar aprender, olvidar cómo usar cosas como el teléfono o "
                "desorientarte.",
                (MEDLINE + "memory.html", MEDLINE + "neurologicdiseases.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Oftalmología",
        aliases=("oculista", "oftalmologo", "clinica de ojos"),
        sentences=(
            Sentence(
                "Ves borroso, tienes que entrecerrar los ojos para ver bien, "
                "ves halos o te deslumbran las luces, o te duele la cabeza "
                "después de forzar la vista.",
                (MEDLINE + "refractiveerrors.html",),
            ),
            Sentence(
                "Ojo rojo, con picazón, hinchazón, secreción o lagañas, o que "
                "molesta mucho la luz.",
                (MEDLINE + "eyeinfections.html", MEDLINE + "eyediseases.html"),
            ),
            Sentence(
                "Ardor en los ojos, sensación de arenilla, vista cansada o "
                "dificultad para enfocar al leer o usar la computadora.",
                (MEDLINE + "eyediseases.html", MEDLINE + "refractiveerrors.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Gastroenterología",
        aliases=(
            "gastroenterologo", "aparato digestivo", "digestivo",
            "gastroenterologia clinica",
        ),
        sentences=(
            Sentence(
                "Acidez o ardor que sube del estómago al pecho o a la "
                "garganta, a veces con sabor agrio en la boca, tos seca, voz "
                "ronca o dificultad para tragar.",
                (MEDLINE + "heartburn.html", MEDLINE + "gerd.html"),
            ),
            Sentence(
                "Molestia o ardor en la boca del estómago, con eructos, "
                "hinchazón, náuseas o vómitos, que dura más de dos semanas.",
                (MEDLINE + "indigestion.html",
                 MEDLINE + "nauseaandvomiting.html"),
            ),
            Sentence(
                "Estreñimiento: vas al baño menos de tres veces por semana, "
                "las heces son duras y secas, duele al evacuar o cambió tu "
                "ritmo de siempre.",
                (MEDLINE + "constipation.html",),
            ),
            Sentence(
                "Diarrea con cólicos o dolor de barriga y ganas urgentes de ir "
                "al baño, que en un adulto no se quita en más de dos días.",
                (MEDLINE + "diarrhea.html",),
            ),
            Sentence(
                "Barriga hinchada o con gases que siguen molestando, o un "
                "dolor de barriga leve que dura una semana o más.",
                (MEDLINE + "gas.html", MEDLINE + "abdominalpain.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Otorrinolaringología",
        aliases=(
            "otorrino", "orl", "otorrinolaringologo",
            "oido, nariz y garganta",
        ),
        sentences=(
            Sentence(
                "Dolor de oído, en uno o en los dos, o líquido que sale del "
                "oído; en niños pequeños se nota porque se jalan la oreja, "
                "lloran más o duermen mal.",
                (MEDLINE + "earinfections.html",),
            ),
            Sentence(
                "Escuchas menos por uno o los dos oídos, te cuesta seguir una "
                "conversación con ruido, sientes presión en el oído o "
                "escuchas un zumbido o silbido que no viene de afuera.",
                (MEDLINE + "hearingdisordersanddeafness.html",
                 MEDLINE + "tinnitus.html"),
            ),
            Sentence(
                "Vértigo: sientes que todo da vueltas, a veces con náuseas o "
                "zumbido en los oídos.",
                (MEDLINE + "dizzinessandvertigo.html",),
            ),
            Sentence(
                "Nariz tapada o con moco, moco que baja por la garganta, "
                "presión o dolor en la cara o detrás de los ojos, pérdida del "
                "olfato o sangrados de nariz frecuentes.",
                (MEDLINE + "sinusitis.html",
                 MEDLINE + "noseinjuriesanddisorders.html"),
            ),
            Sentence(
                "Dolor de garganta al tragar, ganglios inflamados en el cuello, "
                "o voz ronca o apagada que no mejora en dos o tres semanas.",
                (MEDLINE + "throatdisorders.html",
                 ENCY + "003054.htm"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Psicología",
        # Psicología y Psiquiatría son especialidades distintas, pero los
        # motivos por los que alguien busca ayuda son los mismos, y es el
        # centro el que después deriva. Si una organización tiene las dos,
        # las dos reciben estos fragmentos.
        aliases=(
            "psicologia clinica", "psicologo", "psiquiatria", "psiquiatra",
            "salud mental",
        ),
        sentences=(
            Sentence(
                "Te sientes triste, vacío o sin esperanza casi todos los días, "
                "perdiste el interés por lo que antes disfrutabas y te sientes "
                "muy cansado, irritable o culpable.",
                (MEDLINE + "depression.html", WHO + "depression"),
            ),
            Sentence(
                "Te preocupas de más casi todos los días por la salud, el "
                "dinero, el trabajo o la familia, o tienes ataques de miedo "
                "intenso con el corazón acelerado, sudor o temblor sin un "
                "peligro real.",
                (MEDLINE + "anxiety.html", WHO + "anxiety-disorders"),
            ),
            Sentence(
                "Te cuesta dormirte, te despiertas muchas veces o muy temprano "
                "y no descansas, o duermes o comes mucho más o mucho menos que "
                "antes.",
                (MEDLINE + "insomnia.html", MEDLINE + "depression.html"),
            ),
            Sentence(
                "Cambios de humor fuertes que afectan tus relaciones, te "
                "alejas de la familia y los amigos, bebes o usas drogas más de "
                "lo habitual, o no logras cumplir con el trabajo, el estudio o "
                "la casa.",
                (MEDLINE + "mentalhealth.html", MEDLINE + "depression.html"),
            ),
            Sentence(
                "Pensamientos o recuerdos que no puedes sacarte de la cabeza, "
                "o te cuesta concentrarte o tomar decisiones.",
                (MEDLINE + "mentalhealth.html", MEDLINE + "depression.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Pediatría",
        aliases=("pediatria general", "consulta pediatrica", "pediatra"),
        sentences=(
            Sentence(
                "Tu hijo o hija tiene fiebre de 38 °C o más que dura más de "
                "uno o dos días, o que viene con dolor de garganta, dolor de "
                "oído o tos.",
                (ENCY + "003090.htm", ENCY + "001982.htm"),
            ),
            Sentence(
                "El niño se jala la oreja, llora más de lo normal, le sale "
                "líquido del oído, duerme mal, pierde el equilibrio o parece "
                "que no escucha bien.",
                (MEDLINE + "earinfections.html",),
            ),
            Sentence(
                "El niño tiene diarrea que dura más de un día, o con fiebre "
                "alta, o con sangre o pus.",
                (MEDLINE + "diarrhea.html",),
            ),
            Sentence(
                "El niño tiene la boca seca, llora sin lágrimas, moja poco el "
                "pañal, tiene los ojos hundidos o está más irritable o "
                "dormido de lo normal.",
                (MEDLINE + "dehydration.html",),
            ),
            Sentence(
                "El niño tose, respira rápido o le silba el pecho, con fiebre "
                "o sin ella.",
                (WHO + "pneumonia",),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Ginecología",
        aliases=(
            "ginecologia y obstetricia", "gineco-obstetricia",
            "ginecoobstetricia", "obstetricia", "control prenatal",
            "salud de la mujer", "ginecologo",
        ),
        sentences=(
            Sentence(
                "Reglas con sangrado muy abundante, que duran más de ocho "
                "días, muy dolorosas, que no llegan o que se volvieron "
                "irregulares.",
                (MEDLINE + "menstruation.html",),
            ),
            Sentence(
                "Sangrado vaginal entre una regla y otra, o después de la "
                "menopausia.",
                (MEDLINE + "vaginalbleeding.html",),
            ),
            Sentence(
                "Flujo vaginal blanco, gris o verdoso, espeso o con mal olor, "
                "o picazón, ardor, enrojecimiento o dolor en la vagina o la "
                "vulva.",
                (MEDLINE + "vaginitis.html",),
            ),
            Sentence(
                "Dolor en la parte baja del vientre, constante o que va y "
                "viene, que aparece con la regla o durante las relaciones "
                "sexuales.",
                (MEDLINE + "pelvicpain.html",),
            ),
            Sentence(
                "Bochornos o calores repentinos con sudor, reglas "
                "irregulares, sequedad vaginal, problemas para dormir o "
                "cambios de ánimo, como en la menopausia.",
                (MEDLINE + "menopause.html",),
            ),
            Sentence(
                "Control del embarazo, o molestias del embarazo como náuseas, "
                "acidez, dolor de espalda o problemas para dormir.",
                (MEDLINE + "pregnancy.html",
                 MEDLINE + "healthproblemsinpregnancy.html"),
            ),
        ),
    ),
    # ------------------------------------------------------------------
    Reference(
        name="Urología",
        aliases=("urologia general", "urologo"),
        sentences=(
            Sentence(
                "Dolor o ardor al orinar, ganas frecuentes o urgentes de "
                "orinar, u orina turbia, rojiza o con mal olor.",
                (MEDLINE + "urinarytractinfections.html",),
            ),
            Sentence(
                "Cuesta empezar a orinar, el chorro es débil o se corta, "
                "gotea al final, sientes que no vacías la vejiga o te "
                "levantas muchas veces de noche a orinar.",
                (MEDLINE + "enlargedprostatebph.html",),
            ),
            Sentence(
                "Se te escapa la orina al toser, estornudar, reír o levantar "
                "peso, o no alcanzas a llegar al baño.",
                (MEDLINE + "urinaryincontinence.html",),
            ),
            Sentence(
                "Sangre en la orina, aunque sea poca, u orina de color rojizo.",
                (ENCY + "003138.htm", MEDLINE + "urinarytractinfections.html"),
            ),
            Sentence(
                "Dolor, hinchazón, bulto o enrojecimiento en un testículo o en "
                "el escroto, o dificultad para lograr o mantener una erección.",
                (MEDLINE + "testiculardisorders.html",
                 MEDLINE + "erectiledysfunction.html"),
            ),
            Sentence(
                "Dolor fuerte en la espalda o en un costado que no se va, con "
                "sangre en la orina, náuseas o vómitos.",
                (MEDLINE + "kidneystones.html",),
            ),
        ),
    ),
)


def _index():
    indice = {}
    for reference in REFERENCES:
        for name in (reference.name, *reference.aliases):
            indice[normalize_text(name)] = reference
    return indice


_BY_NAME = _index()


def find_reference(specialty_name: str):
    """La referencia de una especialidad, por su nombre o un alias, o None.

    Coincidencia exacta sobre el texto normalizado (sin tildes, minúsculas).
    """
    return _BY_NAME.get(normalize_text(specialty_name))


def reference_texts(specialty_name: str) -> list[str]:
    """Las oraciones a vectorizar para esa especialidad, o lista vacía."""
    reference = find_reference(specialty_name)
    return [s.text for s in reference.sentences] if reference else []
