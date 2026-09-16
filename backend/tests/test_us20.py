"""US-20 — Cancelación y reprogramación de fichas.

Dentro de la política de anticipación de la organización
(`Organization.cancellation_notice_hours`, 24 h por omisión): cancelar con
más anticipación que el umbral marca `refund_eligible=True`; con menos, no.
Reprogramar es atómico: si el turno nuevo ya está tomado, la ficha original
no se toca.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from appointments.models import Appointment
from patients.models import Patient
from scheduling.models import Schedule
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db

LAPAZ = ZoneInfo("America/La_Paz")


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def proximo_lunes():
    hoy = dt.date.today()
    return hoy + dt.timedelta(days=(7 - hoy.weekday()) % 7 or 7)


@pytest.fixture
def paciente_a(patient_a, org_a):
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, user=patient_a,
            document_type=Patient.DocumentType.CI,
            document_number=patient_a.document_number,
            first_name=patient_a.first_name, last_name=patient_a.last_name,
            birth_date=dt.date(1990, 5, 20),
        )
    return patient_a


@pytest.fixture
def agenda_lunes(db, org_a, practitioner_a, branches_a):
    """Dos espacios, 09:00 y 10:00, el próximo lunes."""
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        return Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=lunes.weekday(),
            start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=lunes - dt.timedelta(days=7),
        )


def _crear_ficha(org, paciente, practitioner, branch, schedule, starts_at, **extra):
    with tenant_context(org.id):
        return Appointment.objects.create(
            organization=org, patient=paciente.patient_profile,
            booked_by=paciente, practitioner=practitioner, branch=branch,
            schedule=schedule, starts_at=starts_at,
            ends_at=starts_at + dt.timedelta(hours=1),
            **extra,
        )


def test_cancelar_con_mas_de_24_horas_marca_reembolso_elegible(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    inicio = timezone.now() + dt.timedelta(days=3)
    ficha = _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, inicio,
    )
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha.id]),
    )
    assert respuesta.status_code == 200, respuesta.json()
    assert respuesta.json()["status"] == "cancelled"
    assert respuesta.json()["refund_eligible"] is True


def test_cancelar_con_menos_de_24_horas_no_da_reembolso(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    inicio = timezone.now() + dt.timedelta(hours=2)
    ficha = _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, inicio,
    )
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha.id]),
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["refund_eligible"] is False


def test_cancelar_libera_el_turno_en_la_disponibilidad(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    lunes = proximo_lunes()
    inicio = dt.datetime.combine(lunes, dt.time(9, 0), tzinfo=LAPAZ)
    ficha = _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, inicio,
    )
    api = autenticar(api_client, paciente_a)
    api.post(reverse("appointments:appointment-cancel", args=[ficha.id]))

    disponibilidad = api.get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": lunes.isoformat(), "to": lunes.isoformat(),
        },
    )
    horas = [s["start"][11:16] for d in disponibilidad.json()["days"] for s in d["slots"]]
    assert "09:00" in horas


def test_no_se_puede_cancelar_dos_veces(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    inicio = timezone.now() + dt.timedelta(days=3)
    ficha = _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, inicio,
    )
    api = autenticar(api_client, paciente_a)
    api.post(reverse("appointments:appointment-cancel", args=[ficha.id]))
    segunda = api.post(reverse("appointments:appointment-cancel", args=[ficha.id]))
    assert segunda.status_code == 400


def test_reprogramar_libera_el_turno_viejo_y_ocupa_el_nuevo(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    lunes = proximo_lunes()
    inicio = dt.datetime.combine(lunes, dt.time(9, 0), tzinfo=LAPAZ)
    ficha = _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, inicio,
        status=Appointment.Status.CONFIRMED,
    )
    nuevo_inicio = dt.datetime.combine(lunes, dt.time(10, 0), tzinfo=LAPAZ)
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-reschedule", args=[ficha.id]),
        {
            "branch": str(branches_a["centro"].id),
            "schedule": str(agenda_lunes.id),
            "starts_at": nuevo_inicio.isoformat(),
        },
        format="json",
    )
    assert respuesta.status_code == 200, respuesta.json()
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "confirmed"
    assert cuerpo["rescheduled_from"] == str(ficha.id)

    with tenant_context(org_a.id):
        ficha.refresh_from_db()
    assert ficha.status == Appointment.Status.RESCHEDULED

    disponibilidad = autenticar(api_client, paciente_a).get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": lunes.isoformat(), "to": lunes.isoformat(),
        },
    )
    horas = [s["start"][11:16] for d in disponibilidad.json()["days"] for s in d["slots"]]
    assert "09:00" in horas  # el turno viejo se liberó
    assert "10:00" not in horas  # el nuevo está ocupado


def test_reprogramar_a_un_turno_ya_tomado_no_toca_la_ficha_original(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    lunes = proximo_lunes()
    inicio = dt.datetime.combine(lunes, dt.time(9, 0), tzinfo=LAPAZ)
    ficha = _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, inicio,
    )
    ocupado = dt.datetime.combine(lunes, dt.time(10, 0), tzinfo=LAPAZ)
    _crear_ficha(
        org_a, paciente_a, practitioner_a,
        branches_a["centro"], agenda_lunes, ocupado,
    )

    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-reschedule", args=[ficha.id]),
        {
            "branch": str(branches_a["centro"].id),
            "schedule": str(agenda_lunes.id),
            "starts_at": ocupado.isoformat(),
        },
        format="json",
    )
    assert respuesta.status_code == 409

    with tenant_context(org_a.id):
        ficha.refresh_from_db()
    assert ficha.status == Appointment.Status.PENDING_PAYMENT
    assert ficha.starts_at == inicio


@pytest.mark.isolation
def test_no_se_puede_cancelar_una_ficha_de_otra_organizacion(
    api_client, paciente_a, org_b,
):
    from catalog.models import Branch, Practitioner

    with tenant_context(org_b.id):
        sede_b = Branch.objects.create(organization=org_b, name="Sede B")
        profesional_b = Practitioner.objects.create(
            organization=org_b, first_name="Otra", last_name="Médica",
        )
        agenda_b = Schedule.objects.create(
            organization=org_b, practitioner=profesional_b, branch=sede_b,
            weekday=proximo_lunes().weekday(), start_time="09:00",
            end_time="11:00", slot_minutes=60,
            valid_from=proximo_lunes() - dt.timedelta(days=7),
        )
        from accounts.models import User

        titular_b = User.objects.create_user(
            email="titular@sanluis.test", password="clave-de-prueba-1",
            organization=org_b, first_name="Titular", last_name="B",
            document_number="9002",
        )
        paciente_b = Patient.objects.create(
            organization=org_b, user=titular_b,
            document_type=Patient.DocumentType.CI, document_number="9002",
            first_name="Titular", last_name="B", birth_date=dt.date(1990, 1, 1),
        )
        inicio_b = dt.datetime.combine(proximo_lunes(), dt.time(9, 0), tzinfo=LAPAZ)
        ficha_b = Appointment.objects.create(
            organization=org_b, patient=paciente_b, booked_by=titular_b,
            practitioner=profesional_b, branch=sede_b, schedule=agenda_b,
            starts_at=inicio_b, ends_at=inicio_b + dt.timedelta(hours=1),
        )

    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha_b.id]),
    )
    assert respuesta.status_code == 404
