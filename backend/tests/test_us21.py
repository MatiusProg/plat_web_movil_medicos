"""US-21 — Confirmación de asistencia.

Desde la app y desde el enlace del correo. Lo que importa para el Sprint 4 es
que el desenlace quede asentado con fecha: `attendance_confirmed_at`.
"""

import datetime as dt
import re

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from appointments.attendance import attendance_link, send_confirmation_email
from appointments.models import Appointment

from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    otro_paciente_a,
    paciente_a,
    recargar,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def ficha_confirmada(paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    return crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                       agenda_a, status=Appointment.Status.CONFIRMED, expires_at=None)


def confirmar(api_client, user, ficha):
    return autenticar(api_client, user).post(
        reverse("appointments:appointment-confirm-attendance", args=[ficha.id]),
    )


def test_el_paciente_confirma_y_queda_asentado_con_fecha(
    api_client, paciente_a, org_a, ficha_confirmada,
):
    respuesta = confirmar(api_client, paciente_a, ficha_confirmada)

    assert respuesta.status_code == 200, respuesta.json()
    assert respuesta.json()["attendance_confirmed_at"] is not None
    assert recargar(org_a, ficha_confirmada).attendance_confirmed_at is not None


def test_confirmar_dos_veces_no_cambia_la_fecha(
    api_client, paciente_a, ficha_confirmada,
):
    primera = confirmar(api_client, paciente_a, ficha_confirmada).json()
    segunda = confirmar(api_client, paciente_a, ficha_confirmada).json()
    assert primera["attendance_confirmed_at"] == segunda["attendance_confirmed_at"]


def test_no_se_confirma_una_ficha_sin_pagar(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    pendiente = crear_ficha(org_a, paciente_a, practitioner_a,
                            branches_a["centro"], agenda_a)
    respuesta = confirmar(api_client, paciente_a, pendiente)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ficha_no_confirmada"


def test_no_se_confirma_una_ficha_pasada(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    pasada = crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                         agenda_a, status=Appointment.Status.CONFIRMED,
                         starts_at=timezone.now() - dt.timedelta(hours=1))
    respuesta = confirmar(api_client, paciente_a, pasada)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ficha_pasada"


def test_otro_paciente_no_confirma_una_ficha_ajena(
    api_client, otro_paciente_a, org_a, ficha_confirmada,
):
    assert confirmar(api_client, otro_paciente_a, ficha_confirmada).status_code == 404
    assert recargar(org_a, ficha_confirmada).attendance_confirmed_at is None


def test_el_correo_lleva_el_comprobante_y_el_enlace(org_a, ficha_confirmada):
    assert send_confirmation_email(ficha_confirmada.id, org_a.id) is True
    cuerpo = mail.outbox[0].body
    assert "MC1." in cuerpo
    assert "/api/appointments/attendance/" in cuerpo


def test_el_enlace_del_correo_confirma_solo_con_post(
    client, org_a, ficha_confirmada,
):
    """Los clientes de correo abren los enlaces solos para revisarlos: un GET
    no puede asentar una confirmación que nadie dio."""
    from tenancy.context import tenant_context

    with tenant_context(org_a.id):
        enlace = attendance_link(ficha_confirmada)
    ruta = re.sub(r"^https?://[^/]+", "", enlace)

    assert client.get(ruta).status_code == 200
    assert recargar(org_a, ficha_confirmada).attendance_confirmed_at is None

    assert client.post(ruta).status_code == 200
    assert recargar(org_a, ficha_confirmada).attendance_confirmed_at is not None


def test_un_enlace_adulterado_no_confirma(client):
    respuesta = client.post(
        reverse("appointments:attendance-link", args=["token-falso"]),
    )
    assert respuesta.status_code == 400
