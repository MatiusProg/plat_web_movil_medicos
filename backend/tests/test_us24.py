"""US-24 — Registro de la atención médica.

Lo que más importa de esta historia se prueba **contra la base**, no contra
la vista: que un encuentro firmado no se pueda modificar ni borrar aunque
alguien salte la API. Si esas pruebas pasaran sólo porque la vista devuelve
409, cualquier `UPDATE` desde un comando de gestión las rompería sin aviso.

Las fichas se crean directo con el ORM: el camino de reserva ya lo prueba
US-17, y acá lo que interesa es qué pasa después.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.db import transaction
from django.db.utils import DatabaseError
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AuditLog, User
from accounts.tokens import tokens_for_user
from appointments.models import Appointment
from audit.actions import Action
from catalog.models import Practitioner
from encounters.models import Encounter, EncounterAmendment
from patients.models import Patient
from scheduling.models import Schedule
from tenancy.context import platform_admin_context, tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

PERMISOS_MEDICO = [
    "encounters.encounter.read",
    "encounters.encounter.create",
    "encounters.encounter.amend",
    # US-25: el rol Médico también lee el historial de quien atiende.
    "encounters.history.read",
]
LA_PAZ = ZoneInfo("America/La_Paz")


def cliente(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}")
    return client


def _medico(org, practitioner, email, documento):
    with tenant_context(org.id):
        user = User.objects.create_user(
            email=email, password="clave-de-prueba-1", organization=org,
            first_name="Laura", last_name="Gómez", document_number=documento,
        )
        practitioner.user = user
        practitioner.save()
    dar_rol(user, org, f"medico-{documento}", "Médico", PERMISOS_MEDICO)
    return user


@pytest.fixture
def medico_a(org_a, practitioner_a):
    return _medico(org_a, practitioner_a, "laura@kolping.test", "7001")


@pytest.fixture
def otro_medico_a(org_a, branches_a):
    """Un médico del mismo centro, con el mismo permiso, que no es el de la ficha."""
    with tenant_context(org_a.id):
        otro = Practitioner.objects.create(
            organization=org_a, first_name="Diego", last_name="Ríos",
            license_number="MP-2000",
        )
    return _medico(org_a, otro, "diego@kolping.test", "7002")


@pytest.fixture
def paciente(org_a):
    with tenant_context(org_a.id):
        return Patient.objects.create(
            organization=org_a, document_type=Patient.DocumentType.CI,
            document_number="9001", first_name="Pedro", last_name="Mamani",
            birth_date=dt.date(1980, 3, 10),
        )


def _ficha(org, practitioner, branch, paciente, reservo, cuando, estado=Appointment.Status.CONFIRMED):
    with tenant_context(org.id):
        agenda = Schedule.objects.create(
            organization=org, practitioner=practitioner, branch=branch,
            weekday=cuando.weekday(), start_time="00:00", end_time="23:59",
            slot_minutes=30, valid_from=cuando.date() - dt.timedelta(days=7),
        )
        return Appointment.objects.create(
            organization=org, patient=paciente, booked_by=reservo,
            practitioner=practitioner, branch=branch, schedule=agenda,
            starts_at=cuando, ends_at=cuando + dt.timedelta(minutes=30),
            status=estado,
        )


@pytest.fixture
def ficha_hoy(org_a, practitioner_a, branches_a, paciente, user_a, medico_a):
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    return _ficha(org_a, practitioner_a, branches_a["centro"], paciente, user_a, ahora)


def abrir(medico, ficha):
    return cliente(medico).post(reverse("encounters:open"),
                                {"appointment": str(ficha.id)}, format="json")


def firmado(medico, ficha):
    encuentro = abrir(medico, ficha).json()
    api = cliente(medico)
    api.patch(reverse("encounters:detail", args=[encuentro["id"]]), {
        "reason": "Dolor de cabeza de tres días.",
        "diagnosis": "Cefalea tensional.",
        "treatment": "Paracetamol 500 mg cada 8 horas.",
    }, format="json")
    assert api.post(reverse("encounters:sign", args=[encuentro["id"]])).status_code == 200
    return encuentro["id"]


# --------------------------------------------------------------------------
#  La agenda y la apertura
# --------------------------------------------------------------------------

def test_la_agenda_del_dia_muestra_la_ficha_sin_atencion(medico_a, ficha_hoy):
    datos = cliente(medico_a).get(reverse("encounters:agenda")).json()
    assert [f["id"] for f in datos["appointments"]] == [str(ficha_hoy.id)]
    assert datos["appointments"][0]["encounter"] is None
    assert datos["appointments"][0]["patient"]["full_name"] == "Pedro Mamani"


def test_abrir_la_atencion_crea_un_borrador_y_reabrir_devuelve_el_mismo(
    medico_a, ficha_hoy, org_a,
):
    primera = abrir(medico_a, ficha_hoy)
    assert primera.status_code == 201
    assert primera.json()["status"] == "draft"
    segunda = abrir(medico_a, ficha_hoy)
    assert segunda.status_code == 200
    assert segunda.json()["id"] == primera.json()["id"]
    with tenant_context(org_a.id):
        assert Encounter.objects.count() == 1
        assert AuditLog.objects.filter(action=Action.ENCOUNTER_OPEN).count() == 1


def test_otro_medico_del_mismo_centro_no_abre_ni_ve_la_atencion(
    medico_a, otro_medico_a, ficha_hoy,
):
    assert abrir(otro_medico_a, ficha_hoy).status_code == 400
    encuentro = abrir(medico_a, ficha_hoy).json()
    ajeno = cliente(otro_medico_a)
    assert ajeno.get(reverse("encounters:detail", args=[encuentro["id"]])).status_code == 404
    assert ajeno.post(reverse("encounters:sign", args=[encuentro["id"]])).status_code == 404


def test_sin_el_permiso_no_se_entra(patient_a, ficha_hoy):
    assert abrir(patient_a, ficha_hoy).status_code == 403
    assert cliente(patient_a).get(reverse("encounters:agenda")).status_code == 403


def test_una_ficha_cancelada_no_se_atiende(org_a, practitioner_a, branches_a, paciente, user_a, medico_a):
    ficha = _ficha(org_a, practitioner_a, branches_a["norte"], paciente, user_a,
                   timezone.now(), Appointment.Status.CANCELLED)
    assert abrir(medico_a, ficha).status_code == 409


def test_una_ficha_de_otro_dia_no_se_atiende_todavia(org_a, practitioner_a, branches_a, paciente, user_a, medico_a):
    ficha = _ficha(org_a, practitioner_a, branches_a["norte"], paciente, user_a,
                   timezone.now() + dt.timedelta(days=3))
    assert abrir(medico_a, ficha).status_code == 409


# --------------------------------------------------------------------------
#  La bitácora
# --------------------------------------------------------------------------

def test_abrir_la_historia_queda_en_la_bitacora_sin_su_contenido(medico_a, ficha_hoy, org_a):
    encuentro_id = firmado(medico_a, ficha_hoy)
    assert cliente(medico_a).get(reverse("encounters:detail", args=[encuentro_id])).status_code == 200
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.RECORD_READ)
    assert asiento.user_id == medico_a.id
    assert asiento.entity_id == encuentro_id
    assert asiento.detail == {"patient": str(ficha_hoy.patient_id)}
    assert "Cefalea" not in str(asiento.detail)


# --------------------------------------------------------------------------
#  Borrador, firma y enmienda
# --------------------------------------------------------------------------

def test_sin_motivo_ni_diagnostico_no_se_firma(medico_a, ficha_hoy):
    encuentro = abrir(medico_a, ficha_hoy).json()
    respuesta = cliente(medico_a).post(reverse("encounters:sign", args=[encuentro["id"]]))
    assert respuesta.status_code == 400
    assert set(respuesta.json()) == {"reason", "diagnosis"}


def test_firmar_cierra_el_encuentro_y_marca_la_ficha_atendida(medico_a, ficha_hoy, org_a):
    encuentro_id = firmado(medico_a, ficha_hoy)
    detalle = cliente(medico_a).get(reverse("encounters:detail", args=[encuentro_id])).json()
    assert detalle["status"] == "signed"
    assert detalle["signed_by_name"] == "Laura Gómez"
    with tenant_context(org_a.id):
        ficha_hoy.refresh_from_db()
    assert ficha_hoy.status == Appointment.Status.ATTENDED


def test_un_encuentro_firmado_no_se_edita_por_la_api(medico_a, ficha_hoy):
    encuentro_id = firmado(medico_a, ficha_hoy)
    respuesta = cliente(medico_a).patch(
        reverse("encounters:detail", args=[encuentro_id]),
        {"diagnosis": "Otra cosa"}, format="json",
    )
    assert respuesta.status_code == 409


def test_la_correccion_va_como_enmienda_y_el_original_queda(medico_a, ficha_hoy):
    encuentro_id = firmado(medico_a, ficha_hoy)
    api = cliente(medico_a)
    respuesta = api.post(reverse("encounters:amend", args=[encuentro_id]), {
        "section": "treatment", "text": "Corrijo: paracetamol cada 6 horas.",
    }, format="json")
    assert respuesta.status_code == 201
    detalle = api.get(reverse("encounters:detail", args=[encuentro_id])).json()
    assert detalle["treatment"] == "Paracetamol 500 mg cada 8 horas."
    assert detalle["amendments"][0]["section_display"] == "Tratamiento"


def test_un_borrador_no_se_enmienda(medico_a, ficha_hoy):
    encuentro = abrir(medico_a, ficha_hoy).json()
    respuesta = cliente(medico_a).post(reverse("encounters:amend", args=[encuentro["id"]]), {
        "section": "reason", "text": "x",
    }, format="json")
    assert respuesta.status_code == 409


# --------------------------------------------------------------------------
#  La base hace cumplir la regla, no sólo la vista
# --------------------------------------------------------------------------

def test_la_base_rechaza_modificar_un_encuentro_firmado(medico_a, ficha_hoy, org_a):
    encuentro_id = firmado(medico_a, ficha_hoy)
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            Encounter.objects.filter(pk=encuentro_id).update(diagnosis="Reescrito")


def test_la_base_rechaza_borrar_un_encuentro(medico_a, ficha_hoy, org_a):
    encuentro = abrir(medico_a, ficha_hoy).json()
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            Encounter.objects.filter(pk=encuentro["id"]).delete()


def test_la_base_rechaza_tocar_una_enmienda(medico_a, ficha_hoy, org_a):
    encuentro_id = firmado(medico_a, ficha_hoy)
    cliente(medico_a).post(reverse("encounters:amend", args=[encuentro_id]), {
        "section": "reason", "text": "Agrego: también náuseas.",
    }, format="json")
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterAmendment.objects.update(text="Otra")


# --------------------------------------------------------------------------
#  Aislamiento y permisos sembrados
# --------------------------------------------------------------------------

def test_un_medico_de_otra_organizacion_no_ve_el_encuentro(medico_a, ficha_hoy, org_b, branch_b):
    encuentro = abrir(medico_a, ficha_hoy).json()
    with tenant_context(org_b.id):
        ajeno = Practitioner.objects.create(
            organization=org_b, first_name="Ana", last_name="Paz",
            license_number="MP-9000",
        )
    medico_b = _medico(org_b, ajeno, "ana@otra.test", "8001")
    respuesta = cliente(medico_b).get(reverse("encounters:detail", args=[encuentro["id"]]))
    assert respuesta.status_code == 404


def test_solo_el_rol_medico_recibe_los_permisos(db):
    from accounts.models import RolePermission
    with platform_admin_context():
        def codigos(rol):
            return set(RolePermission.objects.filter(
                role__organization__isnull=True, role__code=rol,
            ).values_list("permission__code", flat=True))
        medico, admin = codigos("practitioner"), codigos("org_admin")
    assert set(PERMISOS_MEDICO) <= medico
    assert not set(PERMISOS_MEDICO) & admin
