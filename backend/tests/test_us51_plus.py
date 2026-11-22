"""US-51 — El «plus» de la ficha pagada: calendario, cómo llegar y la
preconsulta que ve el médico.

Bordes de la historia (`docs/sprints/sprint-4/ampliacion-17-11.md`): el `.ics`
de una ficha ajena, de una cancelada o sin pagar; una sede sin coordenadas; un
`.ics` válido con la zona `America/La_Paz`; la ficha de un dependiente.
"""

import datetime as dt
from decimal import Decimal

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from appointments.attendance import send_confirmation_email
from appointments.calendar import build_ics, maps_url
from appointments.models import Appointment, AppointmentPreconsultation
from patients.models import Patient
from tenancy.context import tenant_context

from .fichas_comunes import (  # noqa: F401
    agenda_a, api_client, autenticar, crear_ficha, otro_paciente_a, paciente_a,
)
from .test_us24 import abrir, cliente, ficha_hoy, medico_a, paciente  # noqa: F401

pytestmark = pytest.mark.django_db

LA_PAZ = dt.timezone(dt.timedelta(hours=-4))


@pytest.fixture
def sede(org_a, branches_a):
    with tenant_context(org_a.id):
        sede = branches_a["centro"]
        sede.address = "Av. 6 de Agosto 2170, Sopocachi"
        sede.latitude, sede.longitude = Decimal("-16.509870"), Decimal("-68.126760")
        sede.save()
    return sede


@pytest.fixture
def pagada(paciente_a, org_a, practitioner_a, sede, agenda_a):
    inicio = dt.datetime(2026, 12, 3, 10, 30, tzinfo=LA_PAZ)
    return crear_ficha(org_a, paciente_a, practitioner_a, sede, agenda_a,
                       starts_at=inicio, status=Appointment.Status.CONFIRMED,
                       expires_at=None)


def ics(api, ficha):
    return api.get(reverse("appointments:calendar", args=[ficha.id]))


def _leer(texto):
    """Desdobla las líneas plegadas (RFC 5545) y devuelve {propiedad: valor}."""
    lineas = texto.replace("\r\n ", "").split("\r\n")
    return lineas, {ln.split(":", 1)[0]: ln.split(":", 1)[1] for ln in lineas if ":" in ln}


# ---------- Calendario ------------------------------------------------------

def test_el_titular_baja_un_ics_valido_en_hora_de_la_paz(api_client, paciente_a, pagada):
    r = ics(autenticar(api_client, paciente_a), pagada)
    assert r.status_code == 200
    assert r["Content-Type"].startswith("text/calendar")
    assert "ficha-2026-12-03-1030.ics" in r["Content-Disposition"]
    texto = r.content.decode("utf-8")
    lineas, campos = _leer(texto)
    assert lineas[0] == "BEGIN:VCALENDAR" and lineas[-2] == "END:VCALENDAR"
    # La hora local del turno, con su zona: no la de UTC.
    assert campos["DTSTART;TZID=America/La_Paz"] == "20261203T103000"
    assert campos["DTEND;TZID=America/La_Paz"] == "20261203T113000"
    assert "TZOFFSETTO" in campos and campos["TZOFFSETTO"] == "-0400"
    assert campos["LOCATION"] == "Sede Centro\\, Av. 6 de Agosto 2170\\, Sopocachi"
    assert campos["GEO"] == "-16.509870;-68.126760"
    assert campos["TRIGGER"] == "-PT24H"
    assert campos["UID"] == f"{pagada.id}@centromedico"


def test_ninguna_linea_pasa_de_75_octetos(org_a, pagada):
    with tenant_context(org_a.id):
        texto = build_ics(Appointment.objects.select_related(
            "practitioner", "branch", "organization").get(pk=pagada.id))
    assert all(len(ln.encode("utf-8")) <= 75 for ln in texto.split("\r\n"))


def test_el_ics_de_una_ficha_ajena_no_se_baja(api_client, otro_paciente_a, pagada):
    assert ics(autenticar(api_client, otro_paciente_a), pagada).status_code == 404


@pytest.mark.parametrize("estado", [Appointment.Status.CANCELLED,
                                    Appointment.Status.PENDING_PAYMENT,
                                    Appointment.Status.ATTENDED])
def test_sin_ficha_pagada_y_vigente_no_hay_ics(api_client, paciente_a, org_a, pagada, estado):
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=pagada.id).update(status=estado)
    assert ics(autenticar(api_client, paciente_a), pagada).status_code == 404


def test_el_titular_baja_el_ics_de_su_dependiente(
        api_client, paciente_a, org_a, practitioner_a, sede, agenda_a):
    with tenant_context(org_a.id):
        hijo = Patient.objects.create(
            organization=org_a, guardian=paciente_a.patient_profile,
            relationship="child", first_name="Mateo", last_name="Ríos",
            birth_date=dt.date(2020, 3, 15),
        )
        inicio = timezone.now() + dt.timedelta(days=2)
        ficha = Appointment.objects.create(
            organization=org_a, patient=hijo, booked_by=paciente_a,
            practitioner=practitioner_a, branch=sede, schedule=agenda_a,
            starts_at=inicio, ends_at=inicio + dt.timedelta(minutes=30),
            status=Appointment.Status.CONFIRMED)
    assert ics(autenticar(api_client, paciente_a), ficha).status_code == 200


# ---------- Cómo llegar -----------------------------------------------------

def test_la_ficha_trae_la_direccion_y_el_mapa(api_client, paciente_a, pagada):
    r = autenticar(api_client, paciente_a).get(
        reverse("appointments:appointment-detail", args=[pagada.id]))
    assert r.status_code == 200
    datos = r.json()
    assert datos["branch_address"] == "Av. 6 de Agosto 2170, Sopocachi"
    assert datos["branch_maps_url"] == (
        "https://www.google.com/maps/search/?api=1&query=-16.509870,-68.126760")


def test_una_sede_sin_coordenadas_no_tiene_mapa(api_client, paciente_a, org_a, pagada, sede):
    with tenant_context(org_a.id):
        sede.latitude = sede.longitude = None
        sede.save()
        assert maps_url(sede) is None
    api = autenticar(api_client, paciente_a)
    r = api.get(reverse("appointments:appointment-detail", args=[pagada.id]))
    assert r.json()["branch_maps_url"] is None
    _, campos = _leer(ics(api, pagada).content.decode("utf-8"))
    assert "GEO" not in campos
    assert "Cómo llegar" not in campos["DESCRIPTION"]


# ---------- Correo de confirmación -----------------------------------------

def test_el_correo_trae_el_calendario_adjunto_y_como_llegar(org_a, pagada):
    assert send_confirmation_email(pagada.id, org_a.id) is True
    correo = mail.outbox[-1]
    assert "Cómo llegar a Sede Centro" in correo.body
    assert "google.com/maps" in correo.body
    (nombre, contenido, tipo), = correo.attachments
    assert nombre == "ficha-2026-12-03-1030.ics"
    assert tipo == "text/calendar"
    assert "DTSTART;TZID=America/La_Paz:20261203T103000" in contenido


# ---------- La preconsulta la ve el médico ---------------------------------

def test_el_medico_ve_la_preconsulta_en_la_atencion(org_a, medico_a, ficha_hoy):
    with tenant_context(org_a.id):
        AppointmentPreconsultation.objects.create(
            organization=org_a, appointment=ficha_hoy,
            reason="Dolor de cabeza", questions="¿Puedo tomar ibuprofeno?")
    encuentro = abrir(medico_a, ficha_hoy).json()
    assert encuentro["preconsultation"]["reason"] == "Dolor de cabeza"
    assert encuentro["preconsultation"]["questions"] == "¿Puedo tomar ibuprofeno?"


def test_sin_preconsulta_o_vacia_no_aparece(org_a, medico_a, ficha_hoy):
    assert abrir(medico_a, ficha_hoy).json()["preconsultation"] is None
    with tenant_context(org_a.id):
        AppointmentPreconsultation.objects.create(
            organization=org_a, appointment=ficha_hoy, reason="", questions="")
    detalle = cliente(medico_a).get(
        reverse("encounters:detail", args=[abrir(medico_a, ficha_hoy).json()["id"]]))
    assert detalle.json()["preconsultation"] is None
