"""US-17 — Reserva de ficha.

Sucursal, profesional, fecha y hora sobre el endpoint de disponibilidad de
US-15. Lo que hace difícil la historia es la concurrencia: dos pacientes
pidiendo el mismo turno al mismo tiempo tienen que terminar en una reserva y
un rechazo, nunca en dos reservas —comprobado contra el índice único parcial
`uq_appointment_active_slot`, no contra un mock—.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from appointments.models import Appointment
from patients.models import Patient
from scheduling.models import Schedule
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db


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


def ficha_de(user, organization):
    """La ficha de paciente titular de la cuenta, igual que en US-07."""
    with tenant_context(organization.id):
        return Patient.objects.create(
            organization=organization, user=user,
            document_type=Patient.DocumentType.CI,
            document_number=user.document_number,
            first_name=user.first_name, last_name=user.last_name,
            birth_date=dt.date(1990, 5, 20),
        )


@pytest.fixture
def paciente_a(patient_a, org_a):
    """`patient_a` (permisos) con su ficha de paciente enlazada."""
    ficha_de(patient_a, org_a)
    return patient_a


@pytest.fixture
def agenda_lunes(db, org_a, practitioner_a, branches_a):
    """Un turno de una hora los lunes, de 09:00 a 11:00 (dos espacios)."""
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        return Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=lunes.weekday(),
            start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=lunes - dt.timedelta(days=7),
        )


def _payload(paciente_a, practitioner_a, branches_a, agenda_lunes):
    lunes = proximo_lunes()
    inicio = dt.datetime.combine(
        lunes, dt.time(9, 0), tzinfo=ZoneInfo("America/La_Paz"),
    )
    return {
        "patient": str(paciente_a.patient_profile.id),
        "practitioner": str(practitioner_a.id),
        "branch": str(branches_a["centro"].id),
        "schedule": str(agenda_lunes.id),
        "starts_at": inicio.isoformat(),
    }


def test_reserva_exitosa_queda_pendiente_de_pago(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    datos = _payload(paciente_a, practitioner_a, branches_a, agenda_lunes)
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-list"), datos, format="json",
    )
    assert respuesta.status_code == 201, respuesta.json()
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "pending_payment"
    with tenant_context(org_a.id):
        assert Appointment.objects.count() == 1


def test_dos_reservas_del_mismo_turno_una_gana_y_la_otra_recibe_409(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_lunes,
):
    datos = _payload(paciente_a, practitioner_a, branches_a, agenda_lunes)
    api = autenticar(api_client, paciente_a)

    primera = api.post(reverse("appointments:appointment-list"), datos, format="json")
    segunda = api.post(reverse("appointments:appointment-list"), datos, format="json")

    codigos = sorted([primera.status_code, segunda.status_code])
    assert codigos == [201, 409]
    with tenant_context(org_a.id):
        assert Appointment.objects.filter(
            status__in=["pending_payment", "confirmed"],
        ).count() == 1


def test_el_turno_reservado_desaparece_de_la_disponibilidad(
    api_client, paciente_a, practitioner_a, branches_a, agenda_lunes,
):
    datos = _payload(paciente_a, practitioner_a, branches_a, agenda_lunes)
    api = autenticar(api_client, paciente_a)
    api.post(reverse("appointments:appointment-list"), datos, format="json")

    lunes = proximo_lunes()
    disponibilidad = api.get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": lunes.isoformat(), "to": lunes.isoformat(),
        },
    )
    horas = [s["start"][11:16] for d in disponibilidad.json()["days"] for s in d["slots"]]
    assert "09:00" not in horas
    assert "10:00" in horas


def test_reservar_un_horario_que_no_corresponde_a_la_agenda_da_400(
    api_client, paciente_a, practitioner_a, branches_a, agenda_lunes,
):
    datos = _payload(paciente_a, practitioner_a, branches_a, agenda_lunes)
    datos["starts_at"] = dt.datetime.combine(
        proximo_lunes(), dt.time(23, 0), tzinfo=dt.timezone.utc,
    ).isoformat()
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-list"), datos, format="json",
    )
    assert respuesta.status_code == 400


@pytest.mark.isolation
def test_un_paciente_no_reserva_sobre_un_profesional_de_otra_organizacion(
    api_client, paciente_a, org_a, org_b,
):
    with tenant_context(org_b.id):
        from catalog.models import Branch, Practitioner

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
    datos = {
        "patient": str(paciente_a.patient_profile.id),
        "practitioner": str(profesional_b.id),
        "branch": str(sede_b.id),
        "schedule": str(agenda_b.id),
        "starts_at": dt.datetime.combine(
            proximo_lunes(), dt.time(9, 0), tzinfo=dt.timezone.utc,
        ).isoformat(),
    }
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-list"), datos, format="json",
    )
    # RLS deja invisibles al profesional, la sucursal y la agenda de B.
    assert respuesta.status_code == 400
    with tenant_context(org_a.id):
        assert Appointment.objects.count() == 0


@pytest.mark.isolation
def test_un_paciente_no_ve_las_fichas_de_otra_organizacion(
    api_client, paciente_a, org_b,
):
    from catalog.models import Branch, Practitioner

    with tenant_context(org_b.id):
        from accounts.models import User

        otro_usuario = User.objects.create_user(
            email="otra@sanluis.test", password="clave-de-prueba-1",
            organization=org_b, first_name="Otra", last_name="Paciente",
            document_number="9001",
        )
        dar_rol(otro_usuario, org_b, "patient", "Paciente", [
            "appointments.appointment.read",
        ])
        otra_ficha = ficha_de(otro_usuario, org_b)

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
        inicio_b = dt.datetime.combine(
            proximo_lunes(), dt.time(9, 0), tzinfo=ZoneInfo("America/La_Paz"),
        )
        Appointment.objects.create(
            organization=org_b, patient=otra_ficha, booked_by=otro_usuario,
            practitioner=profesional_b, branch=sede_b, schedule=agenda_b,
            starts_at=inicio_b, ends_at=inicio_b + dt.timedelta(hours=1),
        )

    respuesta = autenticar(api_client, paciente_a).get(
        reverse("appointments:appointment-list"),
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == []
