"""US-10 — ABM administrativo de pacientes."""

import datetime as dt

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from accounts.tokens import tokens_for_user
from audit.actions import Action
from patients.models import Patient, PatientHistoryEntry
from tenancy.context import tenant_context


pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"

PERMISOS_ADMIN = [
    "patients.patient.create",
    "patients.patient.update",
    "patients.patient.deactivate",
    "patients.patient.merge",
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
def admin_a(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="admin-us10@centro.test",
            password=CLAVE,
            organization=org_a,
            first_name="Admin",
            last_name="Pacientes",
            document_number="ADM10",
        )

    dar_rol(
        user,
        org_a,
        "admin-pacientes-us10",
        "Administrador pacientes",
        PERMISOS_ADMIN,
    )

    return user


@pytest.fixture
def usuario_sin_permiso(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="sin-us10@centro.test",
            password=CLAVE,
            organization=org_a,
            first_name="Sin",
            last_name="Permiso",
            document_number="SIN10",
        )

    dar_rol(
        user,
        org_a,
        "sin-permisos-us10",
        "Sin permisos",
        [],
    )

    return user


def crear_paciente(
    organization,
    documento,
    nombre="Carlos",
    apellido="Pérez",
    activo=True,
    guardian=None,
    relationship="",
):
    with tenant_context(organization.id):
        return Patient.objects.create(
            organization=organization,
            document_type=Patient.DocumentType.CI,
            document_number=documento,
            first_name=nombre,
            last_name=apellido,
            birth_date=dt.date(1990, 1, 15),
            sex=Patient.Sex.MALE,
            phone="70000000",
            is_active=activo,
            guardian=guardian,
            relationship=relationship,
        )


# -------------------------------------------------------------------------
# Alta
# -------------------------------------------------------------------------

def test_admin_puede_crear_paciente(
    api_client,
    admin_a,
    org_a,
):
    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-list"),
        {
            "document_type": "CI",
            "document_number": "7001001",
            "first_name": "Lucía",
            "last_name": "Rojas",
            "birth_date": "1995-04-10",
            "sex": "F",
            "phone": "71111111",
        },
        format="json",
    )

    assert respuesta.status_code == 201

    with tenant_context(org_a.id):
        paciente = Patient.objects.get(
            document_number="7001001",
        )

    assert paciente.first_name == "Lucía"
    assert paciente.last_name == "Rojas"
    assert paciente.organization_id == org_a.id
    assert paciente.is_active is True


def test_no_permite_documento_duplicado(
    api_client,
    admin_a,
    org_a,
):
    crear_paciente(
        org_a,
        "7001002",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-list"),
        {
            "document_type": "CI",
            "document_number": "7001002",
            "first_name": "Otro",
            "last_name": "Paciente",
        },
        format="json",
    )

    assert respuesta.status_code == 400
    assert "document_number" in respuesta.json()


# -------------------------------------------------------------------------
# Edición
# -------------------------------------------------------------------------

def test_admin_puede_corregir_datos(
    api_client,
    admin_a,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        "7002001",
        nombre="Carlos",
        apellido="Peres",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).patch(
        reverse(
            "patients:patient-admin-detail",
            args=[paciente.id],
        ),
        {
            "last_name": "Pérez",
            "phone": "72222222",
        },
        format="json",
    )

    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        paciente.refresh_from_db()

    assert paciente.last_name == "Pérez"
    assert paciente.phone == "72222222"

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(
            action=Action.PATIENT_UPDATE,
            entity_id=str(paciente.id),
        )

    assert asiento.detail["before"]["last_name"] == "Peres"
    assert asiento.detail["after"]["last_name"] == "Pérez"


# -------------------------------------------------------------------------
# Baja lógica
# -------------------------------------------------------------------------

def test_baja_es_logica(
    api_client,
    admin_a,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        "7003001",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).delete(
        reverse(
            "patients:patient-admin-detail",
            args=[paciente.id],
        ),
    )

    assert respuesta.status_code == 204

    with tenant_context(org_a.id):
        paciente.refresh_from_db()

    assert paciente.is_active is False

    with tenant_context(org_a.id):
        assert Patient.objects.filter(
            id=paciente.id,
        ).exists()

        asiento = AuditLog.objects.get(
            action=Action.PATIENT_DEACTIVATE,
            entity_id=str(paciente.id),
        )

    assert asiento.detail["after"]["is_active"] is False


# -------------------------------------------------------------------------
# Permisos
# -------------------------------------------------------------------------

def test_sin_permiso_no_puede_crear(
    api_client,
    usuario_sin_permiso,
):
    respuesta = autenticar(
        api_client,
        usuario_sin_permiso,
    ).post(
        reverse("patients:patient-admin-list"),
        {
            "document_type": "CI",
            "document_number": "7004001",
            "first_name": "No",
            "last_name": "Autorizado",
        },
        format="json",
    )

    assert respuesta.status_code == 403


def test_sin_permiso_no_puede_editar(
    api_client,
    usuario_sin_permiso,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        "7004002",
    )

    respuesta = autenticar(
        api_client,
        usuario_sin_permiso,
    ).patch(
        reverse(
            "patients:patient-admin-detail",
            args=[paciente.id],
        ),
        {
            "phone": "73333333",
        },
        format="json",
    )

    assert respuesta.status_code == 403


# -------------------------------------------------------------------------
# Aislamiento entre organizaciones
# -------------------------------------------------------------------------

def test_no_puede_editar_paciente_de_otra_organizacion(
    api_client,
    admin_a,
    org_b,
):
    paciente_b = crear_paciente(
        org_b,
        "8001001",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).patch(
        reverse(
            "patients:patient-admin-detail",
            args=[paciente_b.id],
        ),
        {
            "phone": "74444444",
        },
        format="json",
    )

    assert respuesta.status_code == 404


def test_no_puede_dar_baja_paciente_de_otra_organizacion(
    api_client,
    admin_a,
    org_b,
):
    paciente_b = crear_paciente(
        org_b,
        "8001002",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).delete(
        reverse(
            "patients:patient-admin-detail",
            args=[paciente_b.id],
        ),
    )

    assert respuesta.status_code == 404


# -------------------------------------------------------------------------
# Merge
# -------------------------------------------------------------------------

def test_merge_inactiva_origen_y_conserva_destino(
    api_client,
    admin_a,
    org_a,
):
    source = crear_paciente(
        org_a,
        "7005001",
        nombre="Juan",
        apellido="Duplicado",
    )

    target = crear_paciente(
        org_a,
        "7005002",
        nombre="Juan",
        apellido="Correcto",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-merge"),
        {
            "source_patient": str(source.id),
            "target_patient": str(target.id),
        },
        format="json",
    )

    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        source.refresh_from_db()
        target.refresh_from_db()

    assert source.is_active is False
    assert target.is_active is True

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(
            action=Action.PATIENT_MERGE,
            entity_id=str(target.id),
        )

    assert asiento.detail["before"]["source_patient"] == str(source.id)
    assert asiento.detail["after"]["source_active"] is False


def test_merge_reasigna_antecedentes(
    api_client,
    admin_a,
    org_a,
):
    source = crear_paciente(
        org_a,
        "7006001",
    )

    target = crear_paciente(
        org_a,
        "7006002",
    )

    with tenant_context(org_a.id):
        antecedente = PatientHistoryEntry.objects.create(
            organization=org_a,
            patient=source,
            kind=PatientHistoryEntry.Kind.CONDITION,
            description="Hipertensión",
        )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-merge"),
        {
            "source_patient": str(source.id),
            "target_patient": str(target.id),
        },
        format="json",
    )

    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        antecedente.refresh_from_db()

    assert antecedente.patient_id == target.id


def test_merge_reasigna_dependientes(
    api_client,
    admin_a,
    org_a,
):
    source = crear_paciente(
        org_a,
        "7007001",
    )

    target = crear_paciente(
        org_a,
        "7007002",
    )

    dependiente = crear_paciente(
        org_a,
        None,
        nombre="Mateo",
        apellido="Menor",
        guardian=source,
        relationship=Patient.Relationship.CHILD,
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-merge"),
        {
            "source_patient": str(source.id),
            "target_patient": str(target.id),
        },
        format="json",
    )

    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        dependiente.refresh_from_db()

    assert dependiente.guardian_id == target.id


def test_no_permite_merge_consigo_mismo(
    api_client,
    admin_a,
    org_a,
):
    paciente = crear_paciente(
        org_a,
        "7008001",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-merge"),
        {
            "source_patient": str(paciente.id),
            "target_patient": str(paciente.id),
        },
        format="json",
    )

    assert respuesta.status_code == 400


def test_no_puede_fusionar_con_paciente_de_otra_organizacion(
    api_client,
    admin_a,
    org_a,
    org_b,
):
    source = crear_paciente(
        org_a,
        "7009001",
    )

    target_ajeno = crear_paciente(
        org_b,
        "8009001",
    )

    respuesta = autenticar(
        api_client,
        admin_a,
    ).post(
        reverse("patients:patient-admin-merge"),
        {
            "source_patient": str(source.id),
            "target_patient": str(target_ajeno.id),
        },
        format="json",
    )

    assert respuesta.status_code == 404