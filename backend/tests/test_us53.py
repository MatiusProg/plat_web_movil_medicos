"""US-53 — Signos vitales en la atención.

Lo que se prueba, con los bordes de la regla 17:
- se cargan con el borrador (el mismo PATCH de «Guardar»), y se ven en la
  atención con el IMC y lo anormal ya calculados;
- se reemplazan enteros, y `null` o todo vacío los borra;
- lo **imposible** se rechaza (60 °C, 3 m, SpO₂ 101 %, la diastólica mayor que
  la sistólica, texto), y si se rechaza no se guarda nada del borrador;
- lo **anormal** se guarda y se marca: 39 °C existe y hay que poder anotarlo;
- firmada la atención no se tocan, ni por la API ni saltándola;
- otra organización no los ve, y el paciente los ve en su historia.

Lo que importa se prueba también **contra la base**: los rangos y el trigger
de lo firmado tienen que aguantar aunque alguien no pase por la API.
"""

from decimal import Decimal

import pytest
from django.db import transaction
from django.db.utils import DatabaseError
from django.urls import reverse

from encounters.models import Encounter, VitalSigns
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    _ficha,
    _medico,
    abrir,
    cliente,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)

pytestmark = pytest.mark.django_db

NORMALES = {
    "systolic": 120, "diastolic": 80, "heart_rate": 72, "temperature": "36.6",
    "spo2": 97, "weight_kg": "70.0", "height_cm": "175.0", "glucose": 95,
}


def guardar(medico, encuentro_id, signos, **otros):
    return cliente(medico).patch(
        reverse("encounters:detail", args=[encuentro_id]),
        {"vital_signs": signos, **otros}, format="json",
    )


def ver(medico, encuentro_id):
    return cliente(medico).get(reverse("encounters:detail", args=[encuentro_id])).json()


def firmar(medico, encuentro_id):
    api = cliente(medico)
    api.patch(reverse("encounters:detail", args=[encuentro_id]), {
        "reason": "Control.", "diagnosis": "Sano.", "treatment": "Ninguno.",
    }, format="json")
    assert api.post(reverse("encounters:sign", args=[encuentro_id])).status_code == 200


@pytest.fixture
def borrador(medico_a, ficha_hoy):
    return abrir(medico_a, ficha_hoy).json()["id"]


def _filas(org, encuentro_id):
    with tenant_context(org.id):
        return VitalSigns.objects.filter(encounter_id=encuentro_id).count()


# --------------------------------------------------------------------------
#  Cargar, ver y reemplazar
# --------------------------------------------------------------------------

def test_se_guardan_con_el_borrador_y_traen_el_imc(medico_a, borrador):
    assert guardar(medico_a, borrador, NORMALES).status_code == 200
    signos = ver(medico_a, borrador)["vital_signs"]
    assert signos["systolic"] == 120
    assert signos["diastolic"] == 80
    assert signos["temperature"] == 36.6
    assert signos["glucose"] == 95
    # 70 / 1,75² = 22,857…
    assert signos["bmi"] == 22.9
    assert signos["alerts"] == {}


def test_sin_tomar_es_null_y_no_un_objeto_vacio(medico_a, borrador):
    assert ver(medico_a, borrador)["vital_signs"] is None


def test_se_puede_cargar_solo_la_presion(medico_a, borrador):
    guardar(medico_a, borrador, {"systolic": 130, "diastolic": 85})
    signos = ver(medico_a, borrador)["vital_signs"]
    assert (signos["systolic"], signos["diastolic"]) == (130, 85)
    assert signos["temperature"] is None
    assert signos["bmi"] is None, "sin peso ni talla no hay IMC"


def test_sin_talla_no_hay_imc(medico_a, borrador):
    guardar(medico_a, borrador, {"weight_kg": "70"})
    assert ver(medico_a, borrador)["vital_signs"]["bmi"] is None


def test_se_reemplazan_enteros_y_no_se_mezclan(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    guardar(medico_a, borrador, {"heart_rate": 90})
    signos = ver(medico_a, borrador)["vital_signs"]
    assert signos["heart_rate"] == 90
    assert signos["systolic"] is None, "lo que no viene queda vacío"
    assert _filas(org_a, borrador) == 1, "una sola fila por atención"


def test_null_los_borra(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    assert guardar(medico_a, borrador, None).status_code == 200
    assert _filas(org_a, borrador) == 0
    assert ver(medico_a, borrador)["vital_signs"] is None


def test_todo_vacio_los_borra(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    guardar(medico_a, borrador, {campo: None for campo in VitalSigns.FIELDS})
    assert _filas(org_a, borrador) == 0


def test_todo_vacio_sin_cargados_no_crea_nada(medico_a, borrador, org_a):
    assert guardar(medico_a, borrador, {}).status_code == 200
    assert _filas(org_a, borrador) == 0


def test_un_patch_sin_signos_no_los_toca(medico_a, borrador):
    guardar(medico_a, borrador, NORMALES)
    cliente(medico_a).patch(reverse("encounters:detail", args=[borrador]),
                            {"reason": "Otro motivo."}, format="json")
    assert ver(medico_a, borrador)["vital_signs"]["systolic"] == 120


# --------------------------------------------------------------------------
#  Lo imposible se rechaza; lo anormal se marca
# --------------------------------------------------------------------------

@pytest.mark.parametrize("campo, valor", [
    ("temperature", "60"),
    ("temperature", "29.9"),
    ("height_cm", "300"),
    ("weight_kg", "0.4"),
    ("spo2", 101),
    ("spo2", 49),
    ("systolic", 301),
    ("heart_rate", 0),
    ("glucose", -5),
    ("heart_rate", "setenta"),
    ("heart_rate", 72.5),
])
def test_lo_imposible_se_rechaza(medico_a, borrador, org_a, campo, valor):
    r = guardar(medico_a, borrador, {campo: valor})
    assert r.status_code == 400
    assert campo in r.json()["vital_signs"]
    assert _filas(org_a, borrador) == 0


@pytest.mark.parametrize("campo, valor", [
    ("temperature", "30"), ("temperature", "45"), ("spo2", 100), ("spo2", 50),
    ("height_cm", "250"), ("weight_kg", "0.5"), ("glucose", 1000),
])
def test_los_limites_posibles_se_aceptan(medico_a, borrador, campo, valor):
    assert guardar(medico_a, borrador, {campo: valor}).status_code == 200


def test_el_mensaje_dice_el_limite(medico_a, borrador):
    r = guardar(medico_a, borrador, {"temperature": "60"})
    assert r.json()["vital_signs"]["temperature"] == [
        "Temperatura (°C): el máximo posible es 45."]


@pytest.mark.parametrize("sistolica, diastolica", [(80, 120), (90, 90)])
def test_la_diastolica_no_puede_ser_mayor_ni_igual(medico_a, borrador, sistolica,
                                                   diastolica):
    r = guardar(medico_a, borrador, {"systolic": sistolica, "diastolic": diastolica})
    assert r.status_code == 400
    assert "diastolic" in r.json()["vital_signs"]


def test_si_se_rechazan_no_se_guarda_nada_del_borrador(medico_a, borrador, org_a):
    r = guardar(medico_a, borrador, {"temperature": "60"}, reason="No debería quedar.")
    assert r.status_code == 400
    with tenant_context(org_a.id):
        assert Encounter.objects.get(pk=borrador).reason != "No debería quedar."


def test_lo_anormal_se_guarda_y_se_marca(medico_a, borrador):
    r = guardar(medico_a, borrador, {
        "systolic": 150, "diastolic": 95, "temperature": "39.2", "spo2": 88,
    })
    assert r.status_code == 200
    assert ver(medico_a, borrador)["vital_signs"]["alerts"] == {
        "blood_pressure": "Alta", "temperature": "Alta", "spo2": "Baja",
    }


@pytest.mark.parametrize("signos, alerta", [
    ({"systolic": 140, "diastolic": 70}, "blood_pressure"),
    ({"systolic": 120, "diastolic": 90}, "blood_pressure"),
    ({"temperature": "38.0"}, "temperature"),
    ({"spo2": 91}, "spo2"),
])
def test_el_borde_de_cada_alerta(medico_a, borrador, signos, alerta):
    guardar(medico_a, borrador, signos)
    assert alerta in ver(medico_a, borrador)["vital_signs"]["alerts"]


@pytest.mark.parametrize("signos", [
    {"systolic": 139, "diastolic": 89},
    {"temperature": "37.9"},
    {"spo2": 92},
])
def test_justo_debajo_del_borde_no_hay_alerta(medico_a, borrador, signos):
    guardar(medico_a, borrador, signos)
    assert ver(medico_a, borrador)["vital_signs"]["alerts"] == {}


# --------------------------------------------------------------------------
#  Firmada la atención
# --------------------------------------------------------------------------

def test_firmada_la_api_no_deja_cambiarlos(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    firmar(medico_a, borrador)
    r = guardar(medico_a, borrador, {"systolic": 180, "diastolic": 100})
    assert r.status_code == 409
    assert ver(medico_a, borrador)["vital_signs"]["systolic"] == 120


def test_firmada_la_api_no_deja_borrarlos(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    firmar(medico_a, borrador)
    assert guardar(medico_a, borrador, None).status_code == 409
    assert _filas(org_a, borrador) == 1


def test_los_firmados_siguen_en_la_atencion(medico_a, borrador):
    guardar(medico_a, borrador, NORMALES)
    firmar(medico_a, borrador)
    assert ver(medico_a, borrador)["vital_signs"]["bmi"] == 22.9


def test_firmada_se_corrigen_con_una_enmienda(medico_a, borrador):
    """«Signos vitales» es una de las secciones que se pueden enmendar."""
    assert Encounter.AMENDABLE["vital_signs"] == "Signos vitales"
    field = Encounter._meta.apps.get_model("encounters", "EncounterAmendment") \
        ._meta.get_field("section")
    assert "vital_signs" in dict(field.choices)


# --------------------------------------------------------------------------
#  Lo que la base hace cumplir, aunque se salte la API
# --------------------------------------------------------------------------

def _crear(org, encuentro_id, **valores):
    with tenant_context(org.id):
        e = Encounter.objects.get(pk=encuentro_id)
        return VitalSigns.objects.create(organization=org, encounter=e, **valores)


def test_la_base_no_deja_cambiarlos_firmada(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    firmar(medico_a, borrador)
    with tenant_context(org_a.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            VitalSigns.objects.filter(encounter_id=borrador).update(systolic=180)


def test_la_base_no_deja_borrarlos_firmada(medico_a, borrador, org_a):
    guardar(medico_a, borrador, NORMALES)
    firmar(medico_a, borrador)
    with tenant_context(org_a.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            VitalSigns.objects.filter(encounter_id=borrador).delete()


def test_la_base_no_deja_agregarlos_firmada(medico_a, borrador, org_a):
    firmar(medico_a, borrador)
    with pytest.raises(DatabaseError), transaction.atomic():
        _crear(org_a, borrador, systolic=120, diastolic=80)


def test_en_borrador_la_base_si_deja(medico_a, borrador, org_a):
    """El control del trigger: sin esto, los tres de arriba no prueban nada."""
    signos = _crear(org_a, borrador, systolic=120, diastolic=80)
    with tenant_context(org_a.id):
        VitalSigns.objects.filter(pk=signos.pk).update(systolic=125)
        VitalSigns.objects.filter(pk=signos.pk).delete()


@pytest.mark.parametrize("valores", [
    {"temperature": Decimal("60")},
    {"spo2": 101},
    {"height_cm": Decimal("300")},
    {"systolic": 80, "diastolic": 120},
    {"systolic": 90, "diastolic": 90},
])
def test_la_base_rechaza_lo_imposible(medico_a, borrador, org_a, valores):
    with pytest.raises(DatabaseError), transaction.atomic():
        _crear(org_a, borrador, **valores)


def test_la_base_no_deja_dos_por_atencion(medico_a, borrador, org_a):
    _crear(org_a, borrador, systolic=120, diastolic=80)
    with pytest.raises(DatabaseError), transaction.atomic():
        _crear(org_a, borrador, heart_rate=70)


def test_no_cuelgan_de_una_atencion_de_otra_organizacion(medico_a, borrador, org_a,
                                                          org_b):
    """La FK compuesta: con la organización de B no se apunta a una atención de A."""
    with tenant_context(org_b.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            VitalSigns.objects.create(organization=org_b, encounter_id=borrador,
                                      systolic=120, diastolic=80)


# --------------------------------------------------------------------------
#  Quién los ve
# --------------------------------------------------------------------------

def test_otra_organizacion_no_los_ve(medico_a, borrador, org_a, org_b):
    guardar(medico_a, borrador, NORMALES)
    with tenant_context(org_b.id):
        assert VitalSigns.objects.count() == 0
    assert _filas(org_a, borrador) == 1


def test_el_medico_de_otra_organizacion_no_los_carga(borrador, org_b, user_b, org_a):
    dar_rol(user_b, org_b, "medico-53", "Médico",
            ["encounters.encounter.write", "encounters.encounter.read"])
    r = guardar(user_b, borrador, NORMALES)
    assert r.status_code in (403, 404)
    assert _filas(org_a, borrador) == 0


def test_otro_medico_no_los_carga_en_una_atencion_ajena(otro_medico_a, borrador, org_a):
    r = guardar(otro_medico_a, borrador, NORMALES)
    assert r.status_code in (403, 404)
    assert _filas(org_a, borrador) == 0


def test_el_paciente_los_ve_en_su_historia(medico_a, borrador, org_a, paciente, user_a):
    guardar(medico_a, borrador, {"systolic": 150, "diastolic": 95})
    firmar(medico_a, borrador)
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-53", "Paciente", ["encounters.history.read"])
    r = cliente(user_a).get(reverse("encounters:history", args=[paciente.pk]))
    assert r.status_code == 200
    atencion = next(e for e in r.json()["encounters"] if e["id"] == borrador)
    assert atencion["vital_signs"]["systolic"] == 150
    assert atencion["vital_signs"]["alerts"] == {"blood_pressure": "Alta"}


def test_el_mensaje_de_la_saturacion_no_rompe(medico_a, borrador):
    """El «(%)» del nombre rompía el formateo de DRF: devolvía un 500."""
    r = guardar(medico_a, borrador, {"spo2": 101})
    assert r.status_code == 400
    assert r.json()["vital_signs"]["spo2"] == [
        "Saturación de oxígeno (%): el máximo posible es 100."]


def test_una_fila_vacia_se_muestra_como_null(medico_a, borrador, org_a):
    """La API nunca la deja así, pero si una fila queda con todo vacío (una
    migración, un script), la atención no muestra un recuadro en blanco."""
    _crear(org_a, borrador)
    assert _filas(org_a, borrador) == 1
    assert ver(medico_a, borrador)["vital_signs"] is None
