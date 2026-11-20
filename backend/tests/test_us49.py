"""US-49 — Recordatorio para tomar los medicamentos.

Los avisos los programa el teléfono; lo que se prueba acá es lo que decide el
servidor:

- **el intérprete de frecuencias** (`encounters/frequency.py`): qué se
  convierte en horario y, sobre todo, qué **no** («según dolor», duración
  vacía), porque un horario inventado es peor que ninguno;
- las tomas marcadas y los bordes de la ampliación del 17/11: una toma de una
  receta ajena, la misma toma dos veces, un medicamento de un dependiente que
  maneja el titular, otra organización;
- **el cumplimiento** que ve el médico en el historial.

Que al cerrar sesión se cancelen los avisos se prueba en el móvil
(`mobile/test/medications_test.dart`).
"""

import pytest
from django.db import transaction
from django.db.utils import DatabaseError
from django.urls import reverse

from encounters.frequency import (
    DEMASIADAS_TOMAS,
    SIN_DURACION,
    SIN_HORARIO_FIJO,
    Horario,
    interpretar,
)
from encounters.models import MedicationIntake, PrescriptionItem
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


# --------------------------------------------------------------------------
#  El intérprete de frecuencias
# --------------------------------------------------------------------------

@pytest.mark.parametrize("frecuencia, duracion, intervalo, dias, total", [
    ("cada 8 horas", "5 días", 8, 5, 15),          # el ejemplo de la historia
    ("Cada 8 Horas", "5 DIAS", 8, 5, 15),
    ("c/12h", "7 dias", 12, 7, 14),
    ("cada 6 hs", "2 semanas", 6, 14, 56),
    ("cada ocho horas", "cinco días", 8, 5, 15),
    ("3 veces al día", "una semana", 8, 7, 21),
    ("tres veces por día", "10 días", 8, 10, 30),
    ("2 veces x día", "1 mes", 12, 30, 60),
    ("una vez al día", "10 días", 24, 10, 10),
    ("1 vez al dia", "30 dias", 24, 30, 30),
    ("cada 24 horas", "3 días", 24, 3, 3),
    ("diario", "por 7 días", 24, 7, 7),
    ("cada 2 días", "10 días", 48, 10, 5),
    ("cada 12 horas", "1 día", 12, 1, 2),
])
def test_frecuencias_que_se_entienden(frecuencia, duracion, intervalo, dias, total):
    horario, motivo = interpretar(frecuencia, duracion)
    assert motivo is None
    assert horario == Horario(interval_hours=intervalo, days=dias, total_doses=total)


@pytest.mark.parametrize("frecuencia", [
    "según dolor",
    "si hay fiebre",
    "cada 8 horas si hay dolor",       # tiene número, pero es condicional
    "a demanda",
    "PRN",
    "SOS",
    "en caso de náuseas",
    "5 veces al día",                  # no reparte el día en horas enteras
    "con las comidas",
    "",
    "   ",
])
def test_frecuencias_sin_horario_fijo_no_inventan_uno(frecuencia):
    horario, motivo = interpretar(frecuencia, "5 días")
    assert horario is None
    assert motivo == SIN_HORARIO_FIJO


@pytest.mark.parametrize("duracion", ["", "   ", "continuo", "indefinido",
                                      "hasta nuevo aviso", "tratamiento crónico",
                                      "hasta terminar la caja", "200 días"])
def test_sin_duracion_no_hay_horario(duracion):
    horario, motivo = interpretar("cada 8 horas", duracion)
    assert horario is None
    assert motivo == SIN_DURACION


def test_demasiadas_tomas_no_se_programan():
    assert interpretar("cada hora", "90 días") == (None, DEMASIADAS_TOMAS)


# --------------------------------------------------------------------------
#  Fixtures: una receta firmada de Pedro
# --------------------------------------------------------------------------

def _receta(medico, ficha, medicamentos, firmar=True):
    api = cliente(medico)
    encuentro_id = abrir(medico, ficha).json()["id"]
    api.patch(reverse("encounters:detail", args=[encuentro_id]), {
        "reason": "Rinitis.", "diagnosis": "Rinitis alérgica.",
    }, format="json")
    ids = []
    for m in medicamentos:
        r = api.post(reverse("encounters:prescription", args=[encuentro_id]),
                     {"medication": m[0], "dose": "1 comprimido",
                      "frequency": m[1], "duration": m[2]}, format="json")
        assert r.status_code == 201, r.content
        # Devuelve el encuentro entero: el medicamento nuevo es el último.
        ids.append(r.json()["prescription_items"][-1]["id"])
    if firmar:
        assert api.post(reverse("encounters:sign", args=[encuentro_id])).status_code == 200
    return encuentro_id, ids


@pytest.fixture
def receta(medico_a, ficha_hoy):
    """Loratadina cada 8 h por 5 días (15 tomas) e Ibuprofeno según dolor."""
    return _receta(medico_a, ficha_hoy, [
        ("Loratadina 10 mg", "cada 8 horas", "5 días"),
        ("Ibuprofeno 400 mg", "según dolor", "5 días"),
    ])


@pytest.fixture
def pedro(org_a, paciente, user_a):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-49", "Paciente", ["encounters.history.read"])
    return user_a


def marcar(user, item_id, dosis=1, estado="taken", **extra):
    return cliente(user).post(reverse("encounters:intakes", args=[item_id]),
                              {"dose_number": dosis, "status": estado, **extra},
                              format="json")


def mis_medicamentos(user, paciente_id):
    return cliente(user).get(reverse("encounters:medications", args=[paciente_id]))


# --------------------------------------------------------------------------
#  El horario viaja en la receta
# --------------------------------------------------------------------------

def test_la_receta_trae_el_horario_o_el_motivo(receta, pedro, paciente):
    datos = mis_medicamentos(pedro, paciente.id).json()
    lora, ibu = datos["medications"]
    assert lora["schedule"] == {"interval_hours": 8, "days": 5, "total_doses": 15}
    assert lora["schedule_reason"] is None
    assert ibu["schedule"] is None
    assert ibu["schedule_reason"] == "Esta indicación no tiene horario fijo."


def test_el_historial_tambien_trae_el_horario(receta, pedro, paciente):
    datos = cliente(pedro).get(reverse("encounters:history", args=[paciente.id])).json()
    items = datos["encounters"][0]["prescription_items"]
    assert items[0]["schedule"]["total_doses"] == 15
    assert items[0]["adherence"] == {"taken": 0, "skipped": 0, "total": 15, "rate": 0.0}


# --------------------------------------------------------------------------
#  Marcar tomas
# --------------------------------------------------------------------------

def test_el_paciente_marca_una_toma(receta, pedro, paciente, org_a):
    _, (lora, _) = receta
    r = marcar(pedro, lora, dosis=1, scheduled_at="2026-11-19T08:00:00-04:00")
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "taken"
    with tenant_context(org_a.id):
        toma = MedicationIntake.objects.get()
    assert toma.patient_id == paciente.id
    assert toma.recorded_by_id == pedro.id


def test_marcar_dos_veces_la_misma_toma(receta, pedro, org_a):
    _, (lora, _) = receta
    assert marcar(pedro, lora, dosis=3).status_code == 201
    r = marcar(pedro, lora, dosis=3, estado="skipped")
    assert r.status_code == 409
    assert r.json()["code"] == "already_recorded"
    with tenant_context(org_a.id):
        assert MedicationIntake.objects.get().status == "taken"


@pytest.mark.parametrize("dosis", [0, 16, -1])
def test_una_toma_fuera_del_horario(receta, pedro, dosis):
    _, (lora, _) = receta
    assert marcar(pedro, lora, dosis=dosis).status_code == 400


def test_un_estado_que_no_existe(receta, pedro):
    _, (lora, _) = receta
    assert marcar(pedro, lora, estado="olvidada").status_code == 400


def test_no_se_marca_una_toma_sin_horario_fijo(receta, pedro):
    _, (_, ibu) = receta
    r = marcar(pedro, ibu)
    assert r.status_code == 400
    assert r.json()["code"] == "no_schedule"


def test_no_se_marca_una_toma_de_una_receta_ajena(receta, org_a, user_a):
    _, (lora, _) = receta
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
    dar_rol(user_a, org_a, "paciente-49", "Paciente", ["encounters.history.read"])
    assert marcar(user_a, lora).status_code == 404
    assert cliente(user_a).get(reverse("encounters:intakes", args=[lora])).status_code == 404


def test_el_medico_no_marca_tomas(receta, medico_a):
    _, (lora, _) = receta
    assert marcar(medico_a, lora).status_code == 404


def test_no_se_marca_una_toma_de_un_borrador(medico_a, ficha_hoy, pedro):
    _, (lora,) = _receta(medico_a, ficha_hoy,
                         [("Loratadina 10 mg", "cada 8 horas", "5 días")], firmar=False)
    assert marcar(pedro, lora).status_code == 404


def test_otra_organizacion_no_marca(receta, org_b, user_b):
    _, (lora, _) = receta
    dar_rol(user_b, org_b, "paciente-49", "Paciente", ["encounters.history.read"])
    assert marcar(user_b, lora).status_code == 404


def test_otra_organizacion_no_ve_las_tomas(receta, pedro, org_b):
    _, (lora, _) = receta
    marcar(pedro, lora)
    with tenant_context(org_b.id):
        assert MedicationIntake.objects.count() == 0


def test_el_titular_maneja_el_medicamento_de_su_dependiente(
    receta, org_a, paciente, user_a,
):
    _, (lora, _) = receta
    with tenant_context(org_a.id):
        titular = Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
        Patient.objects.filter(pk=paciente.pk).update(
            guardian=titular, relationship=Patient.Relationship.OTHER)
    dar_rol(user_a, org_a, "titular-49", "Paciente", ["encounters.history.read"])

    assert mis_medicamentos(user_a, paciente.id).status_code == 200
    assert marcar(user_a, lora).status_code == 201
    # Y sus propios medicamentos son otra lista.
    assert mis_medicamentos(user_a, titular.id).json()["medications"] == []


def test_sin_el_permiso_no_se_entra(receta, org_a, paciente, user_a):
    _, (lora, _) = receta
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    assert marcar(user_a, lora).status_code == 403
    assert mis_medicamentos(user_a, paciente.id).status_code == 403


def test_mis_medicamentos_de_otro_paciente(receta, pedro, org_a):
    with tenant_context(org_a.id):
        otro = Patient.objects.create(
            organization=org_a, document_type=Patient.DocumentType.CI,
            document_number="9100", first_name="Rosa", last_name="Vargas",
        )
    assert mis_medicamentos(pedro, otro.id).status_code == 404


# --------------------------------------------------------------------------
#  Lo que la base hace cumplir
# --------------------------------------------------------------------------

def test_la_base_no_deja_cambiar_ni_borrar_una_toma(receta, pedro, org_a):
    _, (lora, _) = receta
    marcar(pedro, lora)
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            MedicationIntake.objects.update(status="skipped")
        with pytest.raises(DatabaseError), transaction.atomic():
            MedicationIntake.objects.all().delete()


def test_la_base_no_deja_marcar_en_un_borrador(medico_a, ficha_hoy, pedro, org_a,
                                               paciente):
    _, (lora,) = _receta(medico_a, ficha_hoy,
                         [("Loratadina 10 mg", "cada 8 horas", "5 días")], firmar=False)
    with tenant_context(org_a.id):
        item = PrescriptionItem.objects.get(pk=lora)
        with pytest.raises(DatabaseError), transaction.atomic():
            MedicationIntake.objects.create(
                organization=org_a, prescription_item=item, patient=paciente,
                dose_number=1, status="taken", recorded_by=pedro,
            )


def test_la_base_no_deja_dos_veces_la_misma_toma(receta, pedro, org_a, paciente):
    _, (lora, _) = receta
    marcar(pedro, lora, dosis=1)
    with tenant_context(org_a.id):
        item = PrescriptionItem.objects.get(pk=lora)
        with pytest.raises(DatabaseError), transaction.atomic():
            MedicationIntake.objects.create(
                organization=org_a, prescription_item=item, patient=paciente,
                dose_number=1, status="skipped", recorded_by=pedro,
            )


# --------------------------------------------------------------------------
#  El cumplimiento
# --------------------------------------------------------------------------

def test_el_medico_ve_el_cumplimiento_en_el_historial(receta, pedro, medico_a, paciente):
    _, (lora, _) = receta
    for dosis in range(1, 13):
        marcar(pedro, lora, dosis=dosis)
    marcar(pedro, lora, dosis=13, estado="skipped")

    datos = cliente(medico_a).get(reverse("encounters:history", args=[paciente.id])).json()
    items = datos["encounters"][0]["prescription_items"]
    assert items[0]["adherence"] == {"taken": 12, "skipped": 1, "total": 15, "rate": 0.8}
    # El de «según dolor» no tiene total ni porcentaje.
    assert items[1]["adherence"] == {"taken": 0, "skipped": 0, "total": None, "rate": None}


def test_mis_medicamentos_trae_las_tomas_marcadas(receta, pedro, paciente):
    _, (lora, _) = receta
    marcar(pedro, lora, dosis=1)
    marcar(pedro, lora, dosis=2, estado="skipped")
    datos = mis_medicamentos(pedro, paciente.id).json()["medications"][0]
    assert [(t["dose_number"], t["status"]) for t in datos["intakes"]] == [
        (1, "taken"), (2, "skipped"),
    ]
    assert datos["adherence"]["taken"] == 1
    assert datos["practitioner_name"] == "Laura Gómez"
