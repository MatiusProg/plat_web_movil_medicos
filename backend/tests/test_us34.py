"""US-34 — Derivación a atención de emergencia.

Dos capas, y las dos se prueban acá:

1. **Las reglas** de ``assistant/triage.py``, que corren antes que todo.
2. **El prompt del sistema** de ``assistant/generation.py``: el modelo puede
   levantar ``EMERGENCY_MARK`` ante lo que la lista no nombra.

La segunda capa se prueba simulando al proveedor (``_call_model``), por lo
mismo que la suite de US-31 usa el proveedor local: una prueba que depende de
la red, de la cuota y del humor del modelo no prueba el cableado, prueba a
Google. Lo que sí se verifica es que **si** el modelo levanta la marca, el
endpoint deriva; y que el prompt se la pide.

Y la bitácora: cada derivación deja asiento, sin el texto de la consulta.
"""

import pytest

from accounts.models import AuditLog
from assistant import generation, triage
from audit.actions import Action
from tenancy.context import tenant_context

from .test_us31 import (  # noqa: F401 — fixtures
    api_client,
    catalogo_indexado_a,
    paciente_a,
    preguntar,
    proveedor_local,
)

pytestmark = pytest.mark.django_db


class ModeloSimulado(list):
    """Las consultas que recibió el modelo, y lo que va a contestar."""

    texto = ""

    def responder(self, texto):
        self.texto = texto

    def __call__(self, question, context):
        self.append(question)
        return self.texto


@pytest.fixture
def modelo_simulado(settings, monkeypatch):
    """Enciende el camino de Gemini con el proveedor reemplazado.

    Es una lista de las consultas recibidas, para poder afirmar cuándo el
    modelo **no** se consultó.
    """
    settings.ASSISTANT_CHAT_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "clave-de-prueba"
    simulado = ModeloSimulado()
    monkeypatch.setattr(generation, "_call_model", simulado)
    return simulado


# --------------------------------------------------------------------------
#  Primera capa — las reglas
# --------------------------------------------------------------------------

@pytest.mark.parametrize("pregunta", [
    "me quiero morir",
    "estoy pensando en quitarme la vida",
    "tengo ideas de suicidio",
    "se me cierra la garganta después de comer maní",
])
def test_las_senales_nuevas_derivan(
    api_client, catalogo_indexado_a, paciente_a, pregunta,
):
    """Salud mental y anafilaxia no estaban en la lista de US-31."""
    cuerpo = preguntar(api_client, paciente_a, pregunta).json()

    assert cuerpo["emergency"] is True, f"«{pregunta}» tendría que derivar"
    assert cuerpo["specialty"] is None
    assert cuerpo["fragments"] == []


@pytest.mark.parametrize("pregunta", [
    # Cada una de éstas derivaba antes de la revisión del 30/09.
    "me tomé la presión y está alta",
    "¿la vacuna puede hacerme daño?",
    "me sangra mucho la encía al cepillarme",
    "tengo un dolor muy fuerte de muelas",
    "no puedo hablar por teléfono en ese horario",
    # Y éstas no tienen que derivar aunque se parezcan a una combinación.
    "tengo migraña y veo lucecitas",
    "me golpeé la rodilla jugando fútbol",
    "tengo fiebre y dolor de garganta",
])
def test_una_consulta_normal_no_deriva(pregunta):
    """Una barrera que salta sin motivo deja de tomarse en serio."""
    resultado = triage.check(pregunta)
    assert not resultado.is_emergency, (
        f"«{pregunta}» no es una urgencia y disparó {resultado.matched}"
    )


@pytest.mark.parametrize("pregunta", [
    # Conjugaciones y tercera persona: muchas veces escribe un familiar.
    "a mi papá se le durmió la mitad de la cara",
    "mi hijo no puede respirar",
    "se tomó todas las pastillas",
    "se me hinchó la lengua después de comer maní",
    "siento como un peso en el pecho",
    # Las combinadas: ninguna de las dos partes deriva sola.
    "estoy embarazada y sangro un poco",
    "mi bebé de 2 meses tiene fiebre",
    "tengo fiebre y el cuello rígido",
    "se cayó y se golpeó la cabeza, ahora vomita",
])
def test_las_urgencias_de_la_revision_derivan(pregunta):
    resultado = triage.check(pregunta)
    assert resultado.is_emergency, f"«{pregunta}» tendría que derivar"


def test_una_combinada_dice_que_partes_dispararon():
    """Una barrera tiene que poder explicar por qué saltó."""
    resultado = triage.check("estoy embarazada y sangro")
    assert "embaraz + sangr" in resultado.matched


def test_si_las_reglas_disparan_el_modelo_ni_se_consulta(
    api_client, catalogo_indexado_a, paciente_a, modelo_simulado,
):
    """Una capa sólo puede escalar. Si la regla ya derivó, no hay nada que
    el modelo pueda decir para deshacerlo."""
    modelo_simulado.responder("Te conviene Cardiología.")

    cuerpo = preguntar(
        api_client, paciente_a, "me duele el pecho y no puedo respirar",
    ).json()

    assert cuerpo["emergency"] is True
    assert cuerpo["generated_by"] == "regla"
    assert modelo_simulado == []


# --------------------------------------------------------------------------
#  Segunda capa — el prompt del sistema
# --------------------------------------------------------------------------

def test_el_prompt_pide_la_marca_ante_una_urgencia():
    assert generation.EMERGENCY_MARK in generation.SYSTEM_PROMPT
    # La regla va antes que las de redacción: si quedara al final, compite
    # con "respondé sólo con los fragmentos" y puede perder.
    assert (
        generation.SYSTEM_PROMPT.index(generation.EMERGENCY_MARK)
        < generation.SYSTEM_PROMPT.index("Reglas, sin excepción")
    )


def test_si_el_modelo_levanta_la_marca_se_deriva(
    api_client, catalogo_indexado_a, paciente_a, modelo_simulado,
):
    """Lo que ninguna subcadena de la lista prevé, y el modelo sí reconoce."""
    modelo_simulado.responder(generation.EMERGENCY_MARK)

    cuerpo = preguntar(
        api_client, paciente_a, "tengo palpitaciones y siento que me apago",
    ).json()

    assert cuerpo["emergency"] is True
    assert cuerpo["specialty"] is None
    assert cuerpo["fragments"] == [], (
        "con una urgencia no se muestra el catálogo recuperado"
    )
    # El mensaje es el revisado de triage.py, no uno que redacte el modelo.
    assert cuerpo["answer"] == triage.EMERGENCY_MESSAGE


def test_la_marca_manda_aunque_venga_acompanada(
    api_client, catalogo_indexado_a, paciente_a, modelo_simulado,
):
    modelo_simulado.responder(
        f"Te sugiero Cardiología. {generation.EMERGENCY_MARK}",
    )

    cuerpo = preguntar(api_client, paciente_a, "tengo palpitaciones").json()

    assert cuerpo["emergency"] is True
    assert cuerpo["specialty"] is None


def test_sin_fragmentos_igual_se_consulta_la_marca(
    api_client, catalogo_indexado_a, paciente_a, modelo_simulado,
):
    """Lo que no se parece a nada del catálogo es lo que más probablemente sea
    una urgencia; sin esta consulta, la segunda capa no correría nunca ahí."""
    modelo_simulado.responder(generation.EMERGENCY_MARK)

    cuerpo = preguntar(api_client, paciente_a, "xqzv wbrt plmk").json()

    assert modelo_simulado, "el modelo tendría que haberse consultado"
    assert cuerpo["emergency"] is True


def test_sin_fragmentos_el_texto_del_modelo_se_descarta(
    api_client, catalogo_indexado_a, paciente_a, modelo_simulado,
):
    """Consultarlo sin contexto sólo sirve para la marca. Lo que redacte sin
    fragmentos es invención y no llega al paciente."""
    modelo_simulado.responder("Te conviene Neurología, que atiende los martes.")

    cuerpo = preguntar(api_client, paciente_a, "xqzv wbrt plmk").json()

    assert cuerpo["emergency"] is False
    assert "Neurología" not in cuerpo["answer"]
    assert cuerpo["generated_by"] == "plantilla"


# --------------------------------------------------------------------------
#  Bitácora de US-06
# --------------------------------------------------------------------------

def test_cada_derivacion_deja_asiento_sin_el_texto_de_la_consulta(
    api_client, catalogo_indexado_a, paciente_a, org_a,
):
    pregunta = "me duele el pecho y no puedo respirar"
    preguntar(api_client, paciente_a, pregunta)

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.ASSISTANT_EMERGENCY)

    assert asiento.user_id == paciente_a.id
    assert asiento.detail == {"layer": "regla"}
    assert "pecho" not in str(asiento.detail)


def test_la_derivacion_del_modelo_queda_distinguida(
    api_client, catalogo_indexado_a, paciente_a, org_a, modelo_simulado,
):
    modelo_simulado.responder(generation.EMERGENCY_MARK)
    preguntar(api_client, paciente_a, "tengo palpitaciones")

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.ASSISTANT_EMERGENCY)

    assert asiento.detail == {"layer": "modelo"}


def test_una_consulta_normal_queda_como_consulta_y_no_como_derivacion(
    api_client, catalogo_indexado_a, paciente_a, org_a,
):
    preguntar(api_client, paciente_a, "tengo manchas en la piel y picazón")

    with tenant_context(org_a.id):
        acciones = list(AuditLog.objects.values_list("action", flat=True))

    assert Action.ASSISTANT_QUERY in acciones
    assert Action.ASSISTANT_EMERGENCY not in acciones
