"""US-40 — La preparación para un estudio, para el paciente.

Lo que se prueba es lo que la hace segura, no la prosa del modelo:

- sale del catálogo de *esta* organización; sin fuente no se genera, y un
  servicio de otra organización, inactivo o sin preparación no cuenta;
- al modelo le llega el estudio, la preparación y las observaciones del
  médico, nunca quién es el paciente;
- sin proveedor —o si el modelo falla— el borrador es el texto del catálogo,
  marcado como tal, y la firma no se cae;
- nace en borrador: el paciente no la ve hasta que el médico la aprueba;
- al médico se le avisa de los números que no están en la fuente;
- sólo el médico de la atención la reintenta.

El proveedor se simula siempre: estas pruebas no gastan cuota.
"""

import pytest
from django.urls import reverse

from ai import consultation_summary, study_preparation
from ai.models import AiGeneratedText
from catalog.models import Practitioner, Service
from encounters.models import Encounter, MedicalOrder
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    _medico,
    abrir,
    cliente,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)
from .test_us39 import CON_GEMINI, _revisor, firmar, laura  # noqa: F401

pytestmark = pytest.mark.django_db

ECO_PREP = "Ayuno de 6 horas y la vejiga llena. Traer estudios anteriores."
REDACTADO = ("Ven con 6 horas de ayuno.\nToma agua antes para llegar con la vejiga llena.\n"
             "Lleva tus estudios anteriores.")


def _servicio(org, nombre="Ecografía abdominal", preparacion=ECO_PREP, activo=True):
    with tenant_context(org.id):
        return Service.objects.create(organization=org, name=nombre, kind="study",
                                      preparation=preparacion, is_active=activo)


@pytest.fixture
def borrador_con_orden(laura, ficha_hoy):
    """Una atención en borrador con una orden de imagen, lista para firmar."""
    api = cliente(laura)
    encuentro_id = abrir(laura, ficha_hoy).json()["id"]
    api.patch(reverse("encounters:detail", args=[encuentro_id]),
              {"reason": "Dolor abdominal.", "diagnosis": "Dolor abdominal a estudiar."},
              format="json")
    api.post(reverse("encounters:orders", args=[encuentro_id]),
             {"kind": "imaging", "description": "Ecografía abdominal completa",
              "notes": "Sin suspender la metformina"}, format="json")
    return encuentro_id


def _simular(monkeypatch, respuesta=REDACTADO):
    vistos = []

    def falso(contexto):
        vistos.append(contexto)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(study_preparation, "_call_model", falso)
    # El resumen de US-39 también se genera al firmar: que no moleste.
    monkeypatch.setattr(consultation_summary, "_call_model",
                        lambda c: "Qué encontramos\nx\nQué tienes que hacer\nx\nCuándo volver\nx")
    return vistos


def _preparaciones(org):
    with tenant_context(org.id):
        return list(AiGeneratedText.objects.filter(kind="preparation"))


def _orden(org, encuentro_id):
    with tenant_context(org.id):
        return MedicalOrder.objects.get(encounter_id=encuentro_id)


def reintentar(user, orden):
    return cliente(user).post(reverse("ai:study-preparation", args=[orden.id]))


# --------------------------------------------------------------------------
#  Al firmar
# --------------------------------------------------------------------------

def test_al_firmar_se_genera_un_borrador_por_orden(borrador_con_orden, laura, org_a,
                                                   monkeypatch):
    _servicio(org_a)
    _simular(monkeypatch)
    with CON_GEMINI:
        respuesta = firmar(laura, borrador_con_orden)
    assert respuesta.status_code == 200
    [prep] = respuesta.json()["study_preparations"]
    assert prep["status"] == "generated"

    [texto] = _preparaciones(org_a)
    assert str(texto.id) == prep["text_id"]
    assert texto.status == "draft"
    assert texto.generated_text == REDACTADO
    assert texto.generated_by.startswith("gemini")
    assert texto.medical_order_id == _orden(org_a, borrador_con_orden).id
    assert str(texto.encounter_id) == borrador_con_orden


def test_al_modelo_le_llega_el_estudio_y_la_fuente_sin_quien_es(borrador_con_orden, laura,
                                                                org_a, monkeypatch):
    _servicio(org_a)
    vistos = _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_con_orden)
    [contexto] = vistos
    assert "Ecografía abdominal completa" in contexto
    assert ECO_PREP in contexto
    assert "Sin suspender la metformina" in contexto
    assert "Pedro" not in contexto and "Mamani" not in contexto and "9001" not in contexto
    # Ni el diagnóstico: para prepararse no hace falta.
    assert "Dolor abdominal a estudiar" not in contexto


def test_sin_fuente_no_se_inventa(borrador_con_orden, laura, org_a, monkeypatch):
    llamado = _simular(monkeypatch)
    with CON_GEMINI:
        [prep] = firmar(laura, borrador_con_orden).json()["study_preparations"]
    assert prep["status"] == "no_source"
    assert "no se generó una inventada" in prep["message"]
    assert llamado == []
    assert _preparaciones(org_a) == []


@pytest.mark.parametrize("servicio", [
    {"activo": False},
    {"preparacion": ""},
    {"nombre": "Radiografía de tórax"},
])
def test_no_cuenta_un_servicio_inactivo_vacio_o_de_otro_estudio(
        borrador_con_orden, laura, org_a, monkeypatch, servicio):
    _servicio(org_a, **servicio)
    _simular(monkeypatch)
    with CON_GEMINI:
        [prep] = firmar(laura, borrador_con_orden).json()["study_preparations"]
    assert prep["status"] == "no_source"
    assert _preparaciones(org_a) == []


def test_el_catalogo_de_otra_organizacion_no_cuenta(borrador_con_orden, laura, org_a,
                                                    org_b, monkeypatch):
    _servicio(org_b)  # mismo estudio, otra clínica
    _simular(monkeypatch)
    with CON_GEMINI:
        [prep] = firmar(laura, borrador_con_orden).json()["study_preparations"]
    assert prep["status"] == "no_source"


def test_sin_proveedor_queda_el_texto_del_catalogo(borrador_con_orden, laura, org_a,
                                                   monkeypatch):
    _servicio(org_a)
    llamado = _simular(monkeypatch)
    respuesta = firmar(laura, borrador_con_orden)  # el conftest apaga a Gemini
    assert respuesta.status_code == 200
    [prep] = respuesta.json()["study_preparations"]
    assert prep["status"] == "from_catalog"
    assert llamado == []
    [texto] = _preparaciones(org_a)
    assert texto.generated_by == "catalogo"
    assert ECO_PREP in texto.generated_text
    assert "Sin suspender la metformina" in texto.generated_text
    assert texto.status == "draft"


@pytest.mark.parametrize("falla", [RuntimeError("503 UNAVAILABLE"), ""])
def test_si_el_modelo_falla_queda_el_catalogo_y_la_firma(borrador_con_orden, laura, org_a,
                                                        monkeypatch, falla):
    _servicio(org_a)
    _simular(monkeypatch, falla)
    with CON_GEMINI:
        respuesta = firmar(laura, borrador_con_orden)
    assert respuesta.status_code == 200
    assert respuesta.json()["study_preparations"][0]["status"] == "from_catalog"
    with tenant_context(org_a.id):
        assert Encounter.objects.get(pk=borrador_con_orden).status == "signed"


def test_una_falla_inesperada_no_tumba_la_firma(borrador_con_orden, laura, org_a,
                                                monkeypatch):
    _servicio(org_a)
    _simular(monkeypatch)

    def revienta(orden):
        raise RuntimeError("algo que nadie previó")

    monkeypatch.setattr(study_preparation, "generate", revienta)
    with CON_GEMINI:
        respuesta = firmar(laura, borrador_con_orden)
    assert respuesta.status_code == 200
    assert respuesta.json()["study_preparations"] == []
    with tenant_context(org_a.id):
        assert Encounter.objects.get(pk=borrador_con_orden).status == "signed"


def test_dos_ordenes_dos_preparaciones(laura, ficha_hoy, org_a, monkeypatch):
    _servicio(org_a)
    _servicio(org_a, nombre="Glucosa en ayunas", preparacion="Ayuno de 8 horas.")
    api = cliente(laura)
    encuentro_id = abrir(laura, ficha_hoy).json()["id"]
    api.patch(reverse("encounters:detail", args=[encuentro_id]),
              {"reason": "Control.", "diagnosis": "Control."}, format="json")
    for kind, desc in [("imaging", "Ecografía abdominal"), ("laboratory", "Glucosa en ayunas"),
                       ("laboratory", "Perfil tiroideo")]:
        api.post(reverse("encounters:orders", args=[encuentro_id]),
                 {"kind": kind, "description": desc}, format="json")
    _simular(monkeypatch)
    with CON_GEMINI:
        preps = firmar(laura, encuentro_id).json()["study_preparations"]
    assert sorted(p["status"] for p in preps) == ["generated", "generated", "no_source"]
    assert len(_preparaciones(org_a)) == 2


# --------------------------------------------------------------------------
#  Reintentar
# --------------------------------------------------------------------------

def test_reintentar_cuando_el_catalogo_se_completo(borrador_con_orden, laura, org_a,
                                                   monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_con_orden)
        _servicio(org_a)
        respuesta = reintentar(laura, _orden(org_a, borrador_con_orden))
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "generated"
    assert len(_preparaciones(org_a)) == 1


def test_no_hay_dos_preparaciones_vivas_y_descartada_se_rehace(borrador_con_orden, laura,
                                                              org_a, monkeypatch):
    _servicio(org_a)
    _simular(monkeypatch)
    with CON_GEMINI:
        texto_id = firmar(laura, borrador_con_orden).json()["study_preparations"][0]["text_id"]
        orden = _orden(org_a, borrador_con_orden)
        assert reintentar(laura, orden).json()["status"] == "exists"
        cliente(laura).post(reverse("ai:discard", args=[texto_id]))
        assert reintentar(laura, orden).json()["status"] == "generated"
    assert len(_preparaciones(org_a)) == 2


def test_sobre_una_atencion_sin_firmar_no_se_genera(borrador_con_orden, laura, org_a,
                                                    monkeypatch):
    _servicio(org_a)
    _simular(monkeypatch)
    with CON_GEMINI:
        assert reintentar(laura, _orden(org_a, borrador_con_orden)).status_code == 409
    assert _preparaciones(org_a) == []


def test_otro_medico_del_centro_no_la_reintenta(borrador_con_orden, laura, otro_medico_a,
                                                org_a, monkeypatch):
    _servicio(org_a)
    firmar(laura, borrador_con_orden)
    _simular(monkeypatch)
    otro = _revisor(otro_medico_a, org_a)
    with CON_GEMINI:
        assert reintentar(otro, _orden(org_a, borrador_con_orden)).status_code == 404


def test_otra_organizacion_no_la_reintenta(borrador_con_orden, laura, org_a, org_b, branch_b,
                                           monkeypatch):
    _servicio(org_a)
    firmar(laura, borrador_con_orden)
    with tenant_context(org_b.id):
        ajena = Practitioner.objects.create(organization=org_b, first_name="Ana",
                                            last_name="Paz", license_number="MP-9000")
    medica_b = _revisor(_medico(org_b, ajena, "ana@otra.test", "8001"), org_b)
    _simular(monkeypatch)
    with CON_GEMINI:
        assert reintentar(medica_b, _orden(org_a, borrador_con_orden)).status_code == 404


# --------------------------------------------------------------------------
#  El médico la revisa; el paciente la lee aprobada
# --------------------------------------------------------------------------

def test_la_bandeja_avisa_los_numeros_que_no_estan_en_la_fuente(borrador_con_orden, laura,
                                                                org_a, monkeypatch):
    _servicio(org_a)
    _simular(monkeypatch, "Ven con 12 horas de ayuno.\nLlega con la vejiga llena.")
    with CON_GEMINI:
        firmar(laura, borrador_con_orden)
    filas = cliente(laura).get(reverse("ai:inbox")).json()["results"]
    [fila] = [f for f in filas if f["kind"] == "preparation"]
    assert fila["order_description"] == "Ecografía abdominal completa"
    assert fila["warnings"] == [
        "Dice «12», que no está en la preparación del catálogo ni en la orden.",
    ]


def test_una_preparacion_fiel_no_tiene_advertencias(borrador_con_orden, laura, org_a,
                                                    monkeypatch):
    _servicio(org_a)
    _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_con_orden)
    filas = cliente(laura).get(reverse("ai:inbox")).json()["results"]
    [fila] = [f for f in filas if f["kind"] == "preparation"]
    assert fila["warnings"] == []


def test_el_paciente_la_lee_solo_aprobada_y_junto_a_su_orden(borrador_con_orden, laura,
                                                             paciente, org_a, user_a,
                                                             monkeypatch):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-40", "Paciente", ["encounters.history.read"])
    _servicio(org_a)
    _simular(monkeypatch)
    with CON_GEMINI:
        texto_id = firmar(laura, borrador_con_orden).json()["study_preparations"][0]["text_id"]

    mios = lambda: cliente(user_a).get(reverse("ai:mine"), {  # noqa: E731
        "patient": str(paciente.id), "kind": "preparation"}).json()["results"]
    assert mios() == []

    cliente(laura).post(reverse("ai:approve", args=[texto_id]),
                        {"final_text": REDACTADO.replace("6 horas", "seis horas")},
                        format="json")
    [fila] = mios()
    assert fila["medical_order"] == str(_orden(org_a, borrador_con_orden).id)
    assert fila["order_description"] == "Ecografía abdominal completa"
    assert "seis horas" in fila["text"]


# --------------------------------------------------------------------------
#  Las piezas sueltas
# --------------------------------------------------------------------------

@pytest.mark.parametrize("nombre,pedido,coincide", [
    ("Ecografía abdominal", "Ecografía abdominal completa", True),
    ("Ecografía abdominal", "ECOGRAFIA ABDOMINAL", True),
    ("Hemograma completo", "Hemograma", True),
    ("Glucosa en ayunas", "Glucosa basal en ayunas", True),
    ("Ecografía abdominal", "Radiografía de tórax", False),
    ("Perfil lipídico", "Perfil tiroideo", False),
])
def test_el_parecido_de_nombres(nombre, pedido, coincide):
    assert (study_preparation._parecido(nombre, pedido)
            >= study_preparation.MIN_NAME_OVERLAP) is coincide


def test_gana_el_servicio_mas_especifico(borrador_con_orden, org_a):
    _servicio(org_a, nombre="Ecografía", preparacion="Sin preparación especial.")
    especifico = _servicio(org_a)
    orden = _orden(org_a, borrador_con_orden)
    with tenant_context(org_a.id):
        assert study_preparation.find_by_name(orden) == especifico


def test_las_advertencias_comparan_numeros_con_la_fuente():
    fuente = "Ayuno de 6 horas. Suspender 2 días antes."
    assert study_preparation.warnings_for("6 horas de ayuno, 2 días antes.", fuente) == []
    assert study_preparation.warnings_for("8 horas de ayuno y 8 vasos.", fuente) == [
        "Dice «8», que no está en la preparación del catálogo ni en la orden.",
    ]

