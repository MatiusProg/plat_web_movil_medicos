"""US-01 - Registro de usuario paciente y ficha demografica."""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Role, User
from patients.models import Patient
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def patient_role(platform_admin, org_a):
    with tenant_context(org_a.id):
        return Role.objects.create(
            organization=org_a, code="patient", name="Paciente",
        )


def registration_payload(org):
    return {
        "organization": org.slug,
        "email": "nuevo@kolping.test",
        "password": "clave-segura-1",
        "password_confirmation": "clave-segura-1",
        "document_number": "7001",
        "first_name": "Nuevo",
        "last_name": "Paciente",
        "phone": "70000000",
        "birth_date": "1995-04-12",
        "sex": "F",
    }


def test_registro_crea_usuario_rol_y_ficha(api_client, org_a, patient_role):
    response = api_client.post(
        reverse("accounts:register"), registration_payload(org_a), format="json",
    )

    assert response.status_code == 201, response.data
    with tenant_context(org_a.id):
        user = User.objects.get(email="nuevo@kolping.test")
        patient = Patient.objects.get(user=user)
        user_role = user.user_roles.get()
    assert user.organization_id == org_a.id
    assert user.check_password("clave-segura-1")
    assert user.password != "clave-segura-1"
    assert user_role.role_id == patient_role.id
    assert patient.first_name == "Nuevo"
    assert patient.birth_date.isoformat() == "1995-04-12"
    assert response.json()["patient_id"] == str(patient.id)


def test_registro_no_crea_usuario_si_falta_rol(api_client, org_a):
    response = api_client.post(
        reverse("accounts:register"), registration_payload(org_a), format="json",
    )

    assert response.status_code == 400
    assert not User.objects.filter(email="nuevo@kolping.test").exists()
    assert not Patient.objects.filter(document_number="7001").exists()
