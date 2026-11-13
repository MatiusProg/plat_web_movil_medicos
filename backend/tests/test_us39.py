"""US-39 — El resumen de la consulta para el paciente.

Lo que se prueba es lo que lo hace seguro, no la prosa del modelo:

- sale de la atención firmada y su receta, y al modelo no le llega quién es
  el paciente ni otra atención;
- sin proveedor no se genera, se dice, y la firma no se cae;
- si el modelo falla, la atención queda firmada igual y se puede reintentar;
- nace en borrador: el paciente no lo ve hasta que el médico lo aprueba;
- sólo el médico de la atención lo reintenta.

El proveedor se simula siempre: estas pruebas no gastan cuota.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

from accounts.models import AuditLog
from ai import consultation_summary
from ai.models import AiGeneratedText
from audit.actions import Action
from encounters.models import Encounter
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

pytestmark = pytest.mark.django_db

CON_GEMINI = override_settings(ASSISTANT_CHAT_PROVIDER="gemini", GEMINI_API_KEY="clave-falsa")

RESUMEN = """Qué encontramos
Tienes una cefalea tensional: un dolor de cabeza por tensión muscular.
Qué tienes que hacer
Toma Paracetamol 500 mg cada 8 horas durante 5 días.
Hazte el hemograma completo.
Cuándo volver
Vuelve a control en un mes."""


def _revisor(user, org):
    dar_rol(user, org, f"revisor-{user.document_number}", "Revisor", ["ai.text.review"])
    return user


@pytest.fixture
def laura(medico_a, org_a):
    return _revisor(medico_a, org_a)


@pytest.fixture
def borrador_clinico(laura, ficha_hoy):
    """Una atención en borrador con receta y una orden, lista para firmar."""
    api = cliente(laura)
    encuentro_id = abrir(laura, ficha_hoy).json()["id"]
    api.patch(reverse("encounters:detail", args=[encuentro_id]), {
        "reason": "Dolor de cabeza de tres días.",
        "evolution": "Contractura cervical a la palpación.",
        "diagnosis": "Cefalea tensional.",
        "indications": "Control en un mes.",
    }, format="json")
    api.post(reverse("encounters:prescription", args=[encuentro_id]), {
        "medication": "Paracetamol 500 mg", "dose": "1 comprimido",
        "frequency": "cada 8 horas", "duration": "5 días",
        "instructions": "Después de las comidas",
    }, format="json")
    api.post(reverse("encounters:orders", args=[encuentro_id]),
             {"kind": "laboratory", "description": "Hemograma completo"}, format="json")
    return encuentro_id


def firmar(user, encuentro_id):
    return cliente(user).post(reverse("encounters:sign", args=[encuentro_id]))


def reintentar(user, encuentro_id):
    return cliente(user).post(reverse("ai:consultation-summary", args=[encuentro_id]))


def _simular(monkeypatch, respuesta=RESUMEN):
    vistos = []

    def falso(contexto):
        vistos.append(contexto)
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    monkeypatch.setattr(consultation_summary, "_call_model", falso)
    return vistos


def _textos(org):
    with tenant_context(org.id):
        return list(AiGeneratedText.objects.all())


# --------------------------------------------------------------------------
#  Al firmar
# --------------------------------------------------------------------------

def test_al_firmar_se_genera_un_borrador_para_el_medico(borrador_clinico, laura, org_a,
                                                        monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        respuesta = firmar(laura, borrador_clinico)
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["status"] == "signed"
    assert datos["patient_summary"]["status"] == "generated"

    [texto] = _textos(org_a)
    assert str(texto.id) == datos["patient_summary"]["text_id"]
    assert texto.kind == "consultation_summary"
    assert texto.status == "draft"
    assert texto.generated_text == RESUMEN
    assert texto.generated_by.startswith("gemini")
    assert str(texto.encounter_id) == borrador_clinico


def test_al_modelo_le_llega_solo_esta_atencion_sin_quien_es(borrador_clinico, laura,
                                                           monkeypatch):
    vistos = _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_clinico)
    [contexto] = vistos
    assert "Cefalea tensional." in contexto
    assert "Paracetamol 500 mg, 1 comprimido, cada 8 horas, durante 5 días" in contexto
    assert "Laboratorio: Hemograma completo" in contexto
    # Ni el nombre ni el documento del paciente.
    assert "Pedro" not in contexto and "Mamani" not in contexto and "9001" not in contexto
    # La evolución es nota del médico, no se le explica al paciente.
    assert "Contractura" not in contexto


def test_sin_proveedor_no_se_genera_y_se_dice(borrador_clinico, laura, org_a, monkeypatch):
    llamado = _simular(monkeypatch)
    respuesta = firmar(laura, borrador_clinico)  # el conftest apaga a Gemini
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "signed"
    resumen = respuesta.json()["patient_summary"]
    assert resumen["status"] == "unavailable"
    assert "no se generó" in resumen["message"]
    assert llamado == []
    # Ni plantilla de reemplazo: no hay ningún texto.
    assert _textos(org_a) == []


@pytest.mark.parametrize("falla", [RuntimeError("503 UNAVAILABLE"), ""])
def test_si_el_modelo_falla_la_atencion_queda_firmada(borrador_clinico, laura, org_a,
                                                     monkeypatch, falla):
    _simular(monkeypatch, falla)
    with CON_GEMINI:
        respuesta = firmar(laura, borrador_clinico)
    assert respuesta.status_code == 200
    assert respuesta.json()["patient_summary"]["status"] == "failed"
    with tenant_context(org_a.id):
        assert Encounter.objects.get(pk=borrador_clinico).status == "signed"
    assert _textos(org_a) == []


def test_la_bitacora_registra_el_pedido_sin_el_texto(borrador_clinico, laura, org_a,
                                                     monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_clinico)
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.AI_TEXT_GENERATE)
    assert asiento.detail == {"tipo": "consultation_summary", "resultado": "generated"}


# --------------------------------------------------------------------------
#  Reintentar
# --------------------------------------------------------------------------

def test_reintentar_genera_cuando_no_se_pudo_al_firmar(borrador_clinico, laura, org_a,
                                                       monkeypatch):
    firmar(laura, borrador_clinico)  # sin proveedor
    _simular(monkeypatch)
    with CON_GEMINI:
        datos = reintentar(laura, borrador_clinico).json()
    assert datos["status"] == "generated"
    assert len(_textos(org_a)) == 1


def test_no_se_generan_dos_resumenes_vivos(borrador_clinico, laura, org_a, monkeypatch):
    llamados = _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_clinico)
        datos = reintentar(laura, borrador_clinico).json()
    assert datos["status"] == "exists"
    assert len(llamados) == 1  # ni siquiera se le preguntó otra vez al modelo
    assert len(_textos(org_a)) == 1


def test_descartado_se_puede_volver_a_generar(borrador_clinico, laura, org_a, monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        texto_id = firmar(laura, borrador_clinico).json()["patient_summary"]["text_id"]
        cliente(laura).post(reverse("ai:discard", args=[texto_id]))
        assert reintentar(laura, borrador_clinico).json()["status"] == "generated"
    assert sorted(t.status for t in _textos(org_a)) == ["discarded", "draft"]


def test_sobre_un_borrador_no_se_genera(borrador_clinico, laura, monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        assert reintentar(laura, borrador_clinico).status_code == 409


def test_otro_medico_no_lo_reintenta(borrador_clinico, laura, otro_medico_a, org_a,
                                     monkeypatch):
    firmar(laura, borrador_clinico)
    diego = _revisor(otro_medico_a, org_a)
    _simular(monkeypatch)
    with CON_GEMINI:
        assert reintentar(diego, borrador_clinico).status_code == 404
    assert _textos(org_a) == []


def test_otra_organizacion_no_lo_reintenta(borrador_clinico, laura, org_b, branch_b,
                                           monkeypatch):
    from catalog.models import Practitioner
    firmar(laura, borrador_clinico)
    with tenant_context(org_b.id):
        ajena = Practitioner.objects.create(organization=org_b, first_name="Ana",
                                            last_name="Paz", license_number="MP-9000")
    medica_b = _revisor(_medico(org_b, ajena, "ana@otra.test", "8001"), org_b)
    _simular(monkeypatch)
    with CON_GEMINI:
        assert reintentar(medica_b, borrador_clinico).status_code == 404


# --------------------------------------------------------------------------
#  El médico lo revisa; el paciente lo lee aprobado
# --------------------------------------------------------------------------

def test_la_bandeja_avisa_lo_que_falta(borrador_clinico, laura, monkeypatch):
    _simular(monkeypatch, "Qué encontramos\nDolor de cabeza por tensión.\n"
                          "Cuándo volver\nEn un mes.")
    with CON_GEMINI:
        firmar(laura, borrador_clinico)
    [fila] = cliente(laura).get(reverse("ai:inbox")).json()["results"]
    assert fila["warnings"] == [
        "No menciona «Paracetamol 500 mg», que está en la receta.",
        "Falta el apartado «Qué tienes que hacer».",
    ]


def test_un_resumen_completo_no_tiene_advertencias(borrador_clinico, laura, monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        firmar(laura, borrador_clinico)
    [fila] = cliente(laura).get(reverse("ai:inbox")).json()["results"]
    assert fila["warnings"] == []


def test_el_paciente_lo_lee_solo_aprobado(borrador_clinico, laura, paciente, org_a,
                                          user_a, monkeypatch):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-39", "Paciente", ["encounters.history.read"])
    _simular(monkeypatch)
    with CON_GEMINI:
        texto_id = firmar(laura, borrador_clinico).json()["patient_summary"]["text_id"]

    mios = lambda: cliente(user_a).get(reverse("ai:mine"), {  # noqa: E731
        "patient": str(paciente.id), "kind": "consultation_summary"}).json()["results"]
    assert mios() == []

    cliente(laura).post(reverse("ai:approve", args=[texto_id]),
                        {"final_text": RESUMEN.replace("un mes", "dos semanas")},
                        format="json")
    [fila] = mios()
    assert fila["encounter"] == borrador_clinico
    assert "dos semanas" in fila["text"]


def test_el_filtro_por_paciente_no_abre_a_otro(borrador_clinico, laura, paciente, org_a,
                                               user_a, monkeypatch):
    _simular(monkeypatch)
    with CON_GEMINI:
        texto_id = firmar(laura, borrador_clinico).json()["patient_summary"]["text_id"]
    cliente(laura).post(reverse("ai:approve", args=[texto_id]))
    # Ana es paciente del centro, pero no es Pedro ni lo tiene a cargo.
    with tenant_context(org_a.id):
        Patient.objects.create(organization=org_a, user=user_a,
                               document_type=Patient.DocumentType.CI,
                               document_number="5001", first_name="Ana", last_name="Ríos")
    dar_rol(user_a, org_a, "paciente-ana", "Paciente", ["encounters.history.read"])
    respuesta = cliente(user_a).get(reverse("ai:mine"), {"patient": str(paciente.id)})
    assert respuesta.json()["results"] == []


# --------------------------------------------------------------------------
#  El evaluador de los 10 casos (regla 15): que mida lo que dice medir
# --------------------------------------------------------------------------

def _caso(nombre):
    from ai.management.commands.evaluate_consultation_summary import CASOS
    return next(c for c in CASOS if c["nombre"] == nombre)


def test_el_evaluador_acepta_un_buen_resumen():
    from ai.management.commands.evaluate_consultation_summary import evaluar
    assert evaluar(_caso("Cefalea tensional con control al mes"), RESUMEN) == []


def test_el_evaluador_detecta_lo_inventado():
    from ai.management.commands.evaluate_consultation_summary import evaluar
    caso = _caso("Faringitis bacteriana sin fecha de control")
    texto = ("Qué encontramos\nTienes una infección de garganta.\n"
             "Qué tienes que hacer\nToma Amoxicilina 500 mg cada 8 horas. "
             "Para la fiebre, ibuprofeno.\n"
             "Cuándo volver\nVuelve en una semana.")
    fallas = evaluar(caso, texto)
    assert "Nombra medicamentos que no están: ibuprofeno." in fallas
    assert "Inventa un plazo para volver que la atención no dice." in fallas


def test_el_evaluador_exige_remitir_al_medico_sin_plazo():
    from ai.management.commands.evaluate_consultation_summary import evaluar
    caso = _caso("Control de niño sano sin receta")
    bien = ("Qué encontramos\nTu hijo está sano.\nQué tienes que hacer\nSigue con su "
            "alimentación.\nCuándo volver\nConsulta con tu médico cuándo volver.")
    assert evaluar(caso, bien) == []
    assert evaluar(caso, bien.replace("Consulta con tu médico cuándo volver.", "Cuando quieras.")) == [
        "Sin plazo en la atención, no remite a consultar con el médico."]
    assert "Trata de usted." in evaluar(caso, bien + " Usted puede llamar.")
