"""US-41 — Resumen del historial para el médico antes de la consulta.

Lo que se prueba es lo que hace confiable al resumen, no la prosa del modelo:

- cada oración que llega a la pantalla cita una atención que existe, y la que
  no cita o cita una inventada se descarta;
- las alergias salen de la base aunque el modelo no las nombre;
- sin proveedor, el resumen se arma copiando los diagnósticos, no se inventa;
- sólo el médico con vínculo de atención lo recibe: ni el paciente, ni un
  médico sin ficha, ni otra organización.

El proveedor se simula siempre: estas pruebas no gastan cuota ni dependen de
la red.
"""

import pytest
from django.test import override_settings
from django.urls import reverse

from accounts.models import AuditLog
from audit.actions import Action
from encounters import summary
from patients.models import Patient, PatientHistoryEntry
from tenancy.context import tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    _medico,
    cliente,
    firmado,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)
from .test_us25 import atendido_en_dos_sedes  # noqa: F401

pytestmark = pytest.mark.django_db

CON_GEMINI = override_settings(ASSISTANT_CHAT_PROVIDER="gemini", GEMINI_API_KEY="clave-falsa")
SIN_GEMINI = override_settings(ASSISTANT_CHAT_PROVIDER="local", GEMINI_API_KEY="")


def resumen(user, paciente_id):
    return cliente(user).get(reverse("encounters:history-summary", args=[paciente_id]))


@pytest.fixture
def alergico(atendido_en_dos_sedes, org_a):
    with tenant_context(org_a.id):
        for kind, descripcion, severidad in [
            ("allergy", "Ibuprofeno", "mild"),
            ("allergy", "Penicilina", "anaphylactic"),
            ("condition", "Hipertensión", ""),
            ("allergy", "Látex", "severe"),
        ]:
            PatientHistoryEntry.objects.create(
                organization=org_a, patient=atendido_en_dos_sedes, kind=kind,
                description=descripcion, severity=severidad,
            )
        PatientHistoryEntry.objects.create(
            organization=org_a, patient=atendido_en_dos_sedes, kind="allergy",
            description="Polen", severity="mild", is_active=False,
        )
    return atendido_en_dos_sedes


# --------------------------------------------------------------------------
#  Las citas: lo que se verifica de lo que devuelve el modelo
# --------------------------------------------------------------------------

def test_la_oracion_sin_cita_o_con_cita_inventada_se_descarta():
    texto = ("Cefalea tensional recurrente [A1][A2]. Toma paracetamol 0.5 g. "
             "Se pidió una resonancia [A7]. Control en un mes [A2].")
    oraciones, descartadas = summary.verificar(texto, total=2)
    assert oraciones == [
        {"text": "Cefalea tensional recurrente.", "refs": ["A1", "A2"]},
        {"text": "Control en un mes.", "refs": ["A2"]},
    ]
    assert descartadas == 2


def test_la_cita_despues_del_punto_sigue_con_su_oracion():
    oraciones, _ = summary.verificar("Losartán 2.5 mg al día. [A1] Sin cambios [A1].", 1)
    assert [o["text"] for o in oraciones] == ["Losartán 2.5 mg al día.", "Sin cambios."]


def test_la_cita_cero_no_existe():
    assert summary.verificar("Algo [A0].", 1) == ([], 1)


# --------------------------------------------------------------------------
#  El resumen por la API
# --------------------------------------------------------------------------

def test_con_gemini_devuelve_solo_lo_citado(atendido_en_dos_sedes, medico_a, monkeypatch):
    vistos = {}

    def falso(contexto):
        vistos["contexto"] = contexto
        return "Cefalea tensional en dos consultas [A1][A2]. Tiene diabetes. Inventado [A3]."

    monkeypatch.setattr(summary, "_call_model", falso)
    with CON_GEMINI:
        datos = resumen(medico_a, atendido_en_dos_sedes.id).json()

    assert datos["generated_by"] == "gemini"
    assert datos["sentences"] == [
        {"text": "Cefalea tensional en dos consultas.", "refs": ["A1", "A2"]},
    ]
    assert datos["discarded"] == 2
    assert [f["ref"] for f in datos["sources"]] == ["A1", "A2"]
    assert {f["practitioner"] for f in datos["sources"]} == {"Laura Gómez", "Diego Ríos"}
    # Al modelo no le llega quién es el paciente: sólo lo clínico.
    assert "Pedro" not in vistos["contexto"] and "9001" not in vistos["contexto"]
    assert "Cefalea tensional." in vistos["contexto"]


def test_si_el_modelo_no_cita_nada_cae_a_la_plantilla(atendido_en_dos_sedes, medico_a, monkeypatch):
    monkeypatch.setattr(summary, "_call_model", lambda c: "Paciente estable, sin novedades.")
    with CON_GEMINI:
        datos = resumen(medico_a, atendido_en_dos_sedes.id).json()
    assert datos["generated_by"] == "plantilla"
    assert datos["discarded"] == 1
    assert len(datos["sentences"]) == 2


def test_si_el_proveedor_falla_cae_a_la_plantilla(atendido_en_dos_sedes, medico_a, monkeypatch):
    def cuota_agotada(contexto):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(summary, "_call_model", cuota_agotada)
    with CON_GEMINI:
        respuesta = resumen(medico_a, atendido_en_dos_sedes.id)
    assert respuesta.status_code == 200
    assert respuesta.json()["generated_by"] == "plantilla"


def test_sin_proveedor_copia_los_diagnosticos_tal_cual(atendido_en_dos_sedes, medico_a, monkeypatch):
    def no_se_llama(contexto):
        raise AssertionError("sin clave no se llama al proveedor")

    monkeypatch.setattr(summary, "_call_model", no_se_llama)
    with SIN_GEMINI:
        datos = resumen(medico_a, atendido_en_dos_sedes.id).json()
    assert datos["generated_by"] == "plantilla"
    assert all(o["text"].endswith("Cefalea tensional.") for o in datos["sentences"])
    assert [o["refs"] for o in datos["sentences"]] == [["A1"], ["A2"]]


def test_las_alergias_salen_de_la_base_y_las_graves_primero(alergico, medico_a, monkeypatch):
    monkeypatch.setattr(summary, "_call_model", lambda c: "Cefalea tensional [A1].")
    with CON_GEMINI:
        datos = resumen(medico_a, alergico.id).json()
    # El modelo no las nombró y están igual; la dada de baja no.
    assert [a["description"] for a in datos["alerts"]["allergies"]] == [
        "Penicilina", "Látex", "Ibuprofeno",
    ]
    assert [a["description"] for a in datos["alerts"]["conditions"]] == ["Hipertensión"]


def test_sin_atenciones_firmadas_no_hay_resumen(paciente, medico_a, ficha_hoy, monkeypatch):
    def no_se_llama(contexto):
        raise AssertionError("sin atenciones no hay nada que resumir")

    monkeypatch.setattr(summary, "_call_model", no_se_llama)
    with CON_GEMINI:
        datos = resumen(medico_a, paciente.id).json()
    assert datos["generated_by"] == "sin_datos"
    assert datos["sentences"] == [] and datos["sources"] == []


def test_la_enmienda_llega_al_resumen(medico_a, ficha_hoy, paciente, monkeypatch):
    encuentro_id = firmado(medico_a, ficha_hoy)
    cliente(medico_a).post(reverse("encounters:amend", args=[encuentro_id]),
                           {"section": "diagnosis", "text": "Migraña sin aura."},
                           format="json")
    with SIN_GEMINI:
        datos = resumen(medico_a, paciente.id).json()
    assert "Migraña sin aura." in datos["sources"][0]["diagnosis"]


def test_cada_resumen_queda_en_la_bitacora_sin_contenido(atendido_en_dos_sedes, medico_a, org_a):
    with SIN_GEMINI:
        resumen(medico_a, atendido_en_dos_sedes.id)
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.RECORD_READ,
                                       detail__origen="resumen")
    assert asiento.detail == {"origen": "resumen", "alcance": "professional",
                              "encuentros": 2, "generado_por": "plantilla"}


# --------------------------------------------------------------------------
#  Quién NO lo recibe
# --------------------------------------------------------------------------

def test_el_paciente_no_recibe_el_resumen_aunque_lea_su_historial(
    atendido_en_dos_sedes, org_a, user_a,
):
    """Regla 14: un texto generado no llega al paciente sin aprobación."""
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=atendido_en_dos_sedes.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-hist", "Paciente", ["encounters.history.read"])
    url = reverse("encounters:history", args=[atendido_en_dos_sedes.id])
    assert cliente(user_a).get(url).status_code == 200
    assert resumen(user_a, atendido_en_dos_sedes.id).status_code == 404


def test_un_medico_sin_ficha_con_el_paciente_no_lo_recibe(atendido_en_dos_sedes, org_a):
    from catalog.models import Practitioner
    with tenant_context(org_a.id):
        ajeno = Practitioner.objects.create(
            organization=org_a, first_name="Rosa", last_name="Vargas",
            license_number="MP-3000",
        )
    rosa = _medico(org_a, ajeno, "rosa@kolping.test", "7003")
    dar_rol(rosa, org_a, "hist-7003", "Historial", ["encounters.history.read"])
    assert resumen(rosa, atendido_en_dos_sedes.id).status_code == 404


def test_otra_organizacion_no_lo_recibe(atendido_en_dos_sedes, org_b):
    from catalog.models import Practitioner
    with tenant_context(org_b.id):
        ajeno = Practitioner.objects.create(
            organization=org_b, first_name="Ana", last_name="Paz",
            license_number="MP-9000",
        )
    medico_b = _medico(org_b, ajeno, "ana@otra.test", "8001")
    dar_rol(medico_b, org_b, "hist-8001", "Historial", ["encounters.history.read"])
    assert resumen(medico_b, atendido_en_dos_sedes.id).status_code == 404


def test_sin_el_permiso_no_se_entra(atendido_en_dos_sedes, org_a, user_a):
    assert resumen(user_a, atendido_en_dos_sedes.id).status_code == 403


def test_un_medico_dado_de_baja_lo_pierde_en_el_acto(
    atendido_en_dos_sedes, medico_a, practitioner_a, org_a,
):
    with SIN_GEMINI:
        assert resumen(medico_a, atendido_en_dos_sedes.id).status_code == 200
    with tenant_context(org_a.id):
        practitioner_a.is_active = False
        practitioner_a.save()
    assert resumen(medico_a, atendido_en_dos_sedes.id).status_code == 404
