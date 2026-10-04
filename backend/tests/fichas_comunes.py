"""Ayudantes compartidos por las pruebas de US-18, US-19 y US-21.

Las fixtures se importan por nombre desde cada archivo de prueba.
"""

import datetime as dt

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from accounts.tokens import tokens_for_user
from appointments.models import Appointment
from patients.models import Patient
from scheduling.models import Schedule
from tenancy.context import tenant_context

from .conftest import PERMISOS_PACIENTE, dar_rol


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def perfil_paciente(user, org):
    with tenant_context(org.id):
        return Patient.objects.create(
            organization=org, user=user,
            document_type=Patient.DocumentType.CI,
            document_number=user.document_number,
            first_name=user.first_name, last_name=user.last_name,
            birth_date=dt.date(1990, 5, 20),
        )


@pytest.fixture
def paciente_a(patient_a, org_a):
    perfil_paciente(patient_a, org_a)
    return patient_a


@pytest.fixture
def otro_paciente_a(db, org_a):
    """Otro paciente de la misma organización: no puede tocar fichas ajenas."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="otro-paciente@centro.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Otro", last_name="Paciente",
            document_number="OTRO-18",
        )
    dar_rol(user, org_a, "patient-otro", "Paciente", PERMISOS_PACIENTE)
    perfil_paciente(user, org_a)
    return user


@pytest.fixture
def agenda_a(db, org_a, practitioner_a, branches_a):
    hoy = dt.date.today()
    with tenant_context(org_a.id):
        return Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=hoy.weekday(),
            start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=hoy - dt.timedelta(days=7),
        )


def crear_ficha(org, paciente, practitioner, branch, schedule, *,
                starts_at=None, **extra):
    starts_at = starts_at or timezone.now() + dt.timedelta(days=3)
    extra.setdefault("expires_at", timezone.now() + dt.timedelta(minutes=15))
    with tenant_context(org.id):
        return Appointment.objects.create(
            organization=org, patient=paciente.patient_profile,
            booked_by=paciente, practitioner=practitioner, branch=branch,
            schedule=schedule, starts_at=starts_at,
            ends_at=starts_at + dt.timedelta(hours=1),
            **extra,
        )


@pytest.fixture
def ficha_pendiente(paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    return crear_ficha(org_a, paciente_a, practitioner_a,
                       branches_a["centro"], agenda_a)


def recargar(org, obj):
    with tenant_context(org.id):
        obj.refresh_from_db()
    return obj
