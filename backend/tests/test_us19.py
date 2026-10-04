"""US-19 — Comprobante digital con QR.

Código **firmado**, único por ficha y de **un solo uso**, que valida el
check-in de US-22. Se prueba de punta a punta: el comprobante que entrega
esta historia es el que acepta el mostrador.
"""

import pytest
from django.urls import reverse

from appointments.models import Appointment
from appointments.receipts import PREFIX, issue_code

from .conftest import dar_rol
from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    otro_paciente_a,
    paciente_a,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ficha_confirmada(paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    return crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                       agenda_a, status=Appointment.Status.CONFIRMED, expires_at=None)


@pytest.fixture
def recepcion_a(staff_a, org_a):
    dar_rol(staff_a, org_a, "recepcion", "Recepción",
            ["appointments.appointment.read"])
    return staff_a


def comprobante(api_client, user, ficha):
    return autenticar(api_client, user).get(
        reverse("appointments:appointment-receipt", args=[ficha.id]),
    )


def check_in(api_client, user, codigo):
    return autenticar(api_client, user).post(
        reverse("appointments:checkin"), {"qr_code": codigo}, format="json",
    )


def test_la_ficha_pagada_tiene_comprobante_firmado(
    api_client, paciente_a, ficha_confirmada,
):
    respuesta = comprobante(api_client, paciente_a, ficha_confirmada)

    assert respuesta.status_code == 200, respuesta.json()
    datos = respuesta.json()
    assert datos["code"].startswith(PREFIX)
    assert datos["appointment_id"] == str(ficha_confirmada.id)
    # Todo lo que hace falta mostrar sin conexión viene en la misma respuesta.
    for campo in ("patient_name", "practitioner_name", "branch_name",
                  "starts_at", "organization_name"):
        assert datos[campo]


def test_el_codigo_es_unico_por_ficha(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a, ficha_confirmada,
):
    otra = crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                       agenda_a, status=Appointment.Status.CONFIRMED)
    assert issue_code(ficha_confirmada) != issue_code(otra)


def test_una_ficha_sin_pagar_no_tiene_comprobante(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    pendiente = crear_ficha(org_a, paciente_a, practitioner_a,
                            branches_a["centro"], agenda_a)
    respuesta = comprobante(api_client, paciente_a, pendiente)
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "ficha_no_confirmada"


def test_otro_paciente_no_ve_el_comprobante(
    api_client, otro_paciente_a, ficha_confirmada,
):
    assert comprobante(api_client, otro_paciente_a, ficha_confirmada).status_code == 404


def test_el_comprobante_habilita_el_check_in_una_sola_vez(
    api_client, paciente_a, recepcion_a, ficha_confirmada,
):
    codigo = comprobante(api_client, paciente_a, ficha_confirmada).json()["code"]

    primera = check_in(api_client, recepcion_a, codigo)
    assert primera.status_code == 200, primera.json()
    assert primera.json()["status"] == "attended"

    segunda = check_in(api_client, recepcion_a, codigo)
    assert segunda.status_code == 409
    assert segunda.json()["code"] == "comprobante_ya_utilizado"


def test_un_comprobante_alterado_se_rechaza(
    api_client, recepcion_a, ficha_confirmada,
):
    codigo = issue_code(ficha_confirmada)
    alterado = codigo[:-3] + ("AAA" if not codigo.endswith("AAA") else "BBB")
    respuesta = check_in(api_client, recepcion_a, alterado)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "comprobante_adulterado"


def test_el_id_de_la_ficha_solo_no_sirve_de_comprobante(
    api_client, recepcion_a, ficha_confirmada,
):
    """El id viaja en URLs y en respuestas: si alcanzara, el QR no sería
    firmado de verdad."""
    respuesta = check_in(api_client, recepcion_a, str(ficha_confirmada.id))
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "comprobante_invalido"


def test_el_comprobante_de_una_ficha_reprogramada_ya_no_sirve(
    api_client, recepcion_a, org_a, ficha_confirmada,
):
    from tenancy.context import tenant_context

    codigo = issue_code(ficha_confirmada)
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=ficha_confirmada.pk).update(status="rescheduled")
    respuesta = check_in(api_client, recepcion_a, codigo)
    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "ficha_no_confirmada"
