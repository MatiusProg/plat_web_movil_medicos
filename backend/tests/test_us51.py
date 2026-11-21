"""US-51: preconsulta segura, sin modificar el cobro de fichas."""
import pytest
from django.urls import reverse
from appointments.models import Appointment, AppointmentPreconsultation
from tenancy.context import tenant_context
from .fichas_comunes import (  # noqa: F401
    api_client, autenticar, paciente_a, otro_paciente_a, agenda_a, crear_ficha,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def pagada(paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    return crear_ficha(org_a, paciente_a, practitioner_a, branches_a['centro'],
                       agenda_a, status=Appointment.Status.CONFIRMED, expires_at=None)


def ruta(ficha):
    return reverse('appointments:preconsultation', args=[ficha.id])


def test_guardar_y_leer_preconsulta(api_client, paciente_a, org_a, pagada):
    cliente = autenticar(api_client, paciente_a)
    r = cliente.put(ruta(pagada), {'reason': 'Dolor de cabeza', 'questions': '¿Qué debo consultar?'}, format='json')
    assert r.status_code == 200, r.json()
    assert cliente.get(ruta(pagada)).json()['reason'] == 'Dolor de cabeza'
    with tenant_context(org_a.id):
        assert AppointmentPreconsultation.objects.filter(appointment=pagada).count() == 1


def test_no_puede_leer_ni_editar_la_preconsulta_ajena(api_client, otro_paciente_a, pagada):
    cliente = autenticar(api_client, otro_paciente_a)
    assert cliente.get(ruta(pagada)).status_code == 404
    assert cliente.put(ruta(pagada), {'reason': 'Otro', 'questions': ''}, format='json').status_code == 404


def test_reserva_sin_pagar_no_tiene_preconsulta(api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    ficha = crear_ficha(org_a, paciente_a, practitioner_a, branches_a['centro'], agenda_a)
    cliente = autenticar(api_client, paciente_a)
    assert cliente.get(ruta(ficha)).status_code == 404
    assert cliente.put(ruta(ficha), {'reason': 'Hola', 'questions': ''}, format='json').status_code == 404


def test_campos_tienen_limite(api_client, paciente_a, pagada):
    cliente = autenticar(api_client, paciente_a)
    r = cliente.put(ruta(pagada), {'reason': 'x' * 1201, 'questions': ''}, format='json')
    assert r.status_code == 400


def test_no_se_edita_despues_de_atencion(api_client, paciente_a, org_a, pagada):
    with tenant_context(org_a.id):
        pagada.status = Appointment.Status.ATTENDED
        pagada.save(update_fields=['status'])
    cliente = autenticar(api_client, paciente_a)
    assert cliente.put(ruta(pagada), {'reason': 'Nuevo', 'questions': ''}, format='json').status_code == 409
