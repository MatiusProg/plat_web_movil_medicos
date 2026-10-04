"""US-22 — Check-in en recepción."""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import (
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from accounts.tokens import tokens_for_user
from appointments.models import Appointment
from catalog.models import Branch, Practitioner
from patients.models import Patient
from scheduling.models import Schedule
from tenancy.context import tenant_context


pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def dar_rol(user, organization, code, name, permission_codes):
    with tenant_context(organization.id):
        role, creado = Role.objects.get_or_create(
            organization=organization,
            code=code,
            defaults={"name": name},
        )

        if creado:
            RolePermission.objects.bulk_create([
                RolePermission(
                    role=role,
                    permission=permission,
                    organization=organization,
                )
                for permission in Permission.objects.filter(
                    code__in=permission_codes,
                )
            ])

        UserRole.objects.create(
            user=user,
            role=role,
            organization=organization,
        )

    return role


@pytest.fixture
def recepcionista_a(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="recepcion-us22@centro.test",
            password=CLAVE,
            organization=org_a,
            first_name="Recepción",
            last_name="Uno",
            document_number="REC22",
        )

    dar_rol(
        user,
        org_a,
        "receptionist-us22",
        "Recepcionista US22",
        ["appointments.appointment.read"],
    )

    return user


@pytest.fixture
def usuario_sin_permiso(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="sin-us22@centro.test",
            password=CLAVE,
            organization=org_a,
            first_name="Sin",
            last_name="Permiso",
            document_number="SIN22",
        )

    dar_rol(
        user,
        org_a,
        "sin-permiso-us22",
        "Sin permiso",
        [],
    )

    return user


def crear_paciente(
    organization,
    documento="9001001",
    nombre="Ana",
    apellido="Rojas",
):
    with tenant_context(organization.id):
        return Patient.objects.create(
            organization=organization,
            document_type=Patient.DocumentType.CI,
            document_number=documento,
            first_name=nombre,
            last_name=apellido,
            birth_date=dt.date(1990, 1, 10),
            sex=Patient.Sex.FEMALE,
        )


def crear_contexto_cita(
    organization,
    paciente,
    usuario,
    status=Appointment.Status.CONFIRMED,
):
    with tenant_context(organization.id):
        branch = Branch.objects.create(
            organization=organization,
            name=f"Sucursal {paciente.document_number}",
            address="Av. Principal",
            phone="70000000",
            timezone="America/La_Paz",
        )

        practitioner_user = User.objects.create_user(
            email=f"medico-{paciente.document_number}@test.com",
            password=CLAVE,
            organization=organization,
            first_name="Laura",
            last_name="Médica",
            document_number=f"MED-{paciente.document_number}",
        )

        practitioner = Practitioner.objects.create(
            organization=organization,
            user=practitioner_user,
            first_name="Laura",
            last_name="Médica",
            license_number=f"MP-{paciente.document_number}",
        )

        schedule = Schedule.objects.create(
            organization=organization,
            practitioner=practitioner,
            branch=branch,
            weekday=timezone.now().weekday(),
            start_time=dt.time(8, 0),
            end_time=dt.time(12, 0),
            slot_minutes=30,
            valid_from=timezone.localdate(),
            valid_until=timezone.localdate() + dt.timedelta(days=30),
            is_active=True,
        )

        starts_at = timezone.now() + dt.timedelta(hours=1)

        return Appointment.objects.create(
            organization=organization,
            patient=paciente,
            booked_by=usuario,
            practitioner=practitioner,
            branch=branch,
            schedule=schedule,
            starts_at=starts_at,
            ends_at=starts_at + dt.timedelta(minutes=30),
            status=status,
        )


def test_checkin_por_documento(
    api_client,
    recepcionista_a,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        documento="9002001",
    )

    cita = crear_contexto_cita(
        org_a,
        paciente,
        recepcionista_a,
    )

    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "document_number": "9002001",
        },
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == Appointment.Status.ATTENDED

    with tenant_context(org_a.id):
        cita.refresh_from_db()

    assert cita.status == Appointment.Status.ATTENDED
    assert cita.checked_in_at is not None


def test_checkin_por_qr_temporal(
    api_client,
    recepcionista_a,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        documento="9002002",
    )

    cita = crear_contexto_cita(
        org_a,
        paciente,
        recepcionista_a,
    )

    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "qr_code": str(cita.id),
        },
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == str(cita.id)

    with tenant_context(org_a.id):
        cita.refresh_from_db()

    assert cita.status == Appointment.Status.ATTENDED
    assert cita.checked_in_at is not None


def test_no_permite_reutilizar_comprobante(
    api_client,
    recepcionista_a,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        documento="9002003",
    )

    cita = crear_contexto_cita(
        org_a,
        paciente,
        recepcionista_a,
    )

    cliente = autenticar(
        api_client,
        recepcionista_a,
    )

    primera = cliente.post(
        reverse("appointments:checkin"),
        {
            "qr_code": str(cita.id),
        },
        format="json",
    )

    assert primera.status_code == 200

    segunda = cliente.post(
        reverse("appointments:checkin"),
        {
            "qr_code": str(cita.id),
        },
        format="json",
    )

    assert segunda.status_code == 409
    assert segunda.json()["code"] == "comprobante_ya_utilizado"


@pytest.mark.parametrize(
    "estado",
    [
        Appointment.Status.PENDING_PAYMENT,
        Appointment.Status.CANCELLED,
        Appointment.Status.RESCHEDULED,
        Appointment.Status.EXPIRED,
        Appointment.Status.NO_SHOW,
    ],
)
def test_solo_se_hace_checkin_a_ficha_confirmada(
    api_client,
    recepcionista_a,
    org_a,
    estado,
):
    paciente = crear_paciente(
        org_a,
        documento=f"91{abs(hash(estado)) % 100000:05d}",
    )

    cita = crear_contexto_cita(
        org_a,
        paciente,
        recepcionista_a,
        status=estado,
    )

    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "qr_code": str(cita.id),
        },
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "ficha_no_confirmada"


def test_documento_inexistente_devuelve_404(
    api_client,
    recepcionista_a,
):
    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "document_number": "NO-EXISTE",
        },
        format="json",
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "ficha_no_encontrada"


def test_qr_invalido_devuelve_404(
    api_client,
    recepcionista_a,
):
    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "qr_code": "esto-no-es-un-uuid",
        },
        format="json",
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "ficha_no_encontrada"


def test_no_permite_enviar_qr_y_documento_juntos(
    api_client,
    recepcionista_a,
):
    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "qr_code": "00000000-0000-4000-8000-000000000000",
            "document_number": "9003001",
        },
        format="json",
    )

    assert respuesta.status_code == 400


def test_sin_permiso_no_puede_hacer_checkin(
    api_client,
    usuario_sin_permiso,
):
    respuesta = autenticar(
        api_client,
        usuario_sin_permiso,
    ).post(
        reverse("appointments:checkin"),
        {
            "document_number": "9004001",
        },
        format="json",
    )

    assert respuesta.status_code == 403


def test_no_puede_hacer_checkin_de_otra_organizacion(
    api_client,
    recepcionista_a,
    org_b,
):
    paciente_b = crear_paciente(
        org_b,
        documento="9005001",
    )

    with tenant_context(org_b.id):
        usuario_b = User.objects.create_user(
            email="usuario-b-us22@test.com",
            password=CLAVE,
            organization=org_b,
            first_name="Paciente",
            last_name="B",
            document_number="USR-B-22",
        )

    cita_b = crear_contexto_cita(
        org_b,
        paciente_b,
        usuario_b,
    )

    respuesta = autenticar(
        api_client,
        recepcionista_a,
    ).post(
        reverse("appointments:checkin"),
        {
            "qr_code": str(cita_b.id),
        },
        format="json",
    )

    assert respuesta.status_code == 404