"""US-09 — Búsqueda y consulta de pacientes.

Prueba:
- búsqueda por documento exacto;
- búsqueda parcial por nombre/apellido;
- búsqueda sin distinguir mayúsculas ni tildes;
- filtros por estado y sucursal;
- paginación;
- detalle demográfico;
- aislamiento entre organizaciones;
- permisos.
"""

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

PERMISOS_RECEPCION = [
    "patients.patient.read",
    "catalog.branch.read",
]


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
def recepcion_a(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="recepcion@centro.test",
            password=CLAVE,
            organization=org_a,
            first_name="Ana",
            last_name="Recepcion",
            document_number="R001",
        )

    dar_rol(
        user,
        org_a,
        "recepcion-us09",
        "Recepción US09",
        PERMISOS_RECEPCION,
    )

    return user


@pytest.fixture
def recepcion_sin_permiso(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="sinpermiso@centro.test",
            password=CLAVE,
            organization=org_a,
            first_name="Sin",
            last_name="Permiso",
            document_number="R002",
        )

    dar_rol(
        user,
        org_a,
        "sin-permiso-us09",
        "Sin permiso US09",
        [],
    )

    return user


def crear_paciente(
    organization,
    documento,
    nombre,
    apellido,
    activo=True,
):
    with tenant_context(organization.id):
        return Patient.objects.create(
            organization=organization,
            document_type=Patient.DocumentType.CI,
            document_number=documento,
            first_name=nombre,
            last_name=apellido,
            birth_date=dt.date(1990, 5, 20),
            sex=Patient.Sex.MALE,
            phone="70000000",
            is_active=activo,
        )


@pytest.fixture
def pacientes_a(db, org_a):
    return [
        crear_paciente(
            org_a,
            "1111111",
            "José",
            "Pérez",
        ),
        crear_paciente(
            org_a,
            "2222222",
            "María",
            "Gómez",
        ),
        crear_paciente(
            org_a,
            "3333333",
            "Carlos",
            "Suárez",
            activo=False,
        ),
    ]


@pytest.fixture
def paciente_b(db, org_b):
    return crear_paciente(
        org_b,
        "9999999",
        "José",
        "Pérez",
    )


# -------------------------------------------------------------------------
# Búsqueda
# -------------------------------------------------------------------------

def test_busca_por_documento_exacto(
    api_client,
    recepcion_a,
    pacientes_a,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"document": "2222222"},
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()

    assert cuerpo["count"] == 1
    assert cuerpo["results"][0]["document_number"] == "2222222"
    assert cuerpo["results"][0]["first_name"] == "María"


def test_documento_no_hace_coincidencia_parcial(
    api_client,
    recepcion_a,
    pacientes_a,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"document": "222"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["count"] == 0


def test_busca_nombre_parcial_sin_importar_mayusculas_ni_tildes(
    api_client,
    recepcion_a,
    pacientes_a,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"q": "jose"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["count"] == 1

    paciente = respuesta.json()["results"][0]

    assert paciente["first_name"] == "José"
    assert paciente["last_name"] == "Pérez"


def test_busca_por_apellido_parcial_sin_tildes(
    api_client,
    recepcion_a,
    pacientes_a,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"q": "gome"},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["count"] == 1
    assert respuesta.json()["results"][0]["last_name"] == "Gómez"


# -------------------------------------------------------------------------
# Estado
# -------------------------------------------------------------------------

def test_filtra_pacientes_activos(
    api_client,
    recepcion_a,
    pacientes_a,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"status": "active"},
    )

    assert respuesta.status_code == 200

    resultados = respuesta.json()["results"]

    assert len(resultados) == 2
    assert all(p["is_active"] is True for p in resultados)


def test_filtra_pacientes_inactivos(
    api_client,
    recepcion_a,
    pacientes_a,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"status": "inactive"},
    )

    assert respuesta.status_code == 200

    resultados = respuesta.json()["results"]

    assert len(resultados) == 1
    assert resultados[0]["document_number"] == "3333333"
    assert resultados[0]["is_active"] is False


# -------------------------------------------------------------------------
# Sucursal
# -------------------------------------------------------------------------

def test_filtra_por_sucursal(
    api_client,
    recepcion_a,
    pacientes_a,
    org_a,
):
    paciente = pacientes_a[0]

    with tenant_context(org_a.id):
        branch_a = Branch.objects.create(
            organization=org_a,
            name="Sucursal Centro",
        )

        branch_b = Branch.objects.create(
            organization=org_a,
            name="Sucursal Norte",
        )

        profesional = Practitioner.objects.create(
            organization=org_a,
            first_name="Laura",
            last_name="Méndez",
            license_number="MP-US09",
        )

        agenda = Schedule.objects.create(
            organization=org_a,
            practitioner=profesional,
            branch=branch_a,
            weekday=0,
            start_time=dt.time(8, 0),
            end_time=dt.time(12, 0),
            slot_minutes=30,
            valid_from=dt.date.today(),
        )

        ahora = timezone.now() + dt.timedelta(days=2)

        Appointment.objects.create(
            organization=org_a,
            patient=paciente,
            booked_by=recepcion_a,
            practitioner=profesional,
            branch=branch_a,
            schedule=agenda,
            starts_at=ahora,
            ends_at=ahora + dt.timedelta(minutes=30),
            status=Appointment.Status.CONFIRMED,
        )

    respuesta_a = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"branch": str(branch_a.id)},
    )

    respuesta_b = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"branch": str(branch_b.id)},
    )

    assert respuesta_a.status_code == 200
    assert respuesta_a.json()["count"] == 1
    assert respuesta_a.json()["results"][0]["id"] == str(paciente.id)

    assert respuesta_b.status_code == 200
    assert respuesta_b.json()["count"] == 0


# -------------------------------------------------------------------------
# Paginación
# -------------------------------------------------------------------------

def test_listado_esta_paginado(
    api_client,
    recepcion_a,
    org_a,
):
    for numero in range(30):
        crear_paciente(
            org_a,
            f"80{numero:05d}",
            f"Paciente{numero}",
            "Prueba",
        )

    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()

    assert cuerpo["count"] == 30
    assert len(cuerpo["results"]) == 20
    assert cuerpo["next"] is not None


def test_page_size_personalizable(
    api_client,
    recepcion_a,
    org_a,
):
    for numero in range(12):
        crear_paciente(
            org_a,
            f"90{numero:05d}",
            f"Persona{numero}",
            "Prueba",
        )

    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"page_size": 5},
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()["results"]) == 5


# -------------------------------------------------------------------------
# Detalle
# -------------------------------------------------------------------------

def test_detalle_muestra_datos_demograficos(
    api_client,
    recepcion_a,
    pacientes_a,
):
    paciente = pacientes_a[0]

    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse(
            "patients:patient-search-detail",
            args=[paciente.id],
        ),
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()

    assert cuerpo["id"] == str(paciente.id)
    assert cuerpo["first_name"] == "José"
    assert cuerpo["last_name"] == "Pérez"
    assert cuerpo["document_number"] == "1111111"
    assert cuerpo["birth_date"] == "1990-05-20"
    assert cuerpo["phone"] == "70000000"

    assert "upcoming_appointments" in cuerpo

    # US-09 no debe exponer información clínica.
    assert "history_entries" not in cuerpo
    assert "allergies" not in cuerpo
    assert "conditions" not in cuerpo
    assert "medications" not in cuerpo


# -------------------------------------------------------------------------
# Seguridad y multi-tenant
# -------------------------------------------------------------------------

def test_sin_permiso_no_puede_buscar(
    api_client,
    recepcion_sin_permiso,
):
    respuesta = autenticar(
        api_client,
        recepcion_sin_permiso,
    ).get(
        reverse("patients:patient-search-list"),
    )

    assert respuesta.status_code == 403


def test_no_devuelve_pacientes_de_otra_organizacion(
    api_client,
    recepcion_a,
    pacientes_a,
    paciente_b,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse("patients:patient-search-list"),
        {"q": "jose"},
    )

    assert respuesta.status_code == 200

    ids = {
        paciente["id"]
        for paciente in respuesta.json()["results"]
    }

    assert str(pacientes_a[0].id) in ids
    assert str(paciente_b.id) not in ids


def test_no_puede_abrir_detalle_de_otra_organizacion(
    api_client,
    recepcion_a,
    paciente_b,
):
    respuesta = autenticar(
        api_client,
        recepcion_a,
    ).get(
        reverse(
            "patients:patient-search-detail",
            args=[paciente_b.id],
        ),
    )

    assert respuesta.status_code == 404