"""Fixtures compartidas.

Las pruebas se conectan como ``app_user``, igual que la aplicación. Correrlas
como ``postgres`` no probaría nada: ``postgres`` es superusuario y omite las
políticas RLS aunque las tablas tengan ``FORCE``. Es el punto 1 del README, y
ya nos costó cinco defectos.
"""

import pytest

from accounts.models import Permission, Role, RolePermission, User, UserRole
from catalog.models import (
    Branch,
    Practitioner,
    PractitionerBranch,
    PractitionerSpecialty,
    Specialty,
)
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization, Subscription, SubscriptionPlan


def dar_rol(user, organization, code, name, permission_codes):
    """Crea un rol con esos permisos en la organización y se lo asigna al
    usuario. Mismo ayudante que usa `tests/test_us04.py`."""
    with tenant_context(organization.id):
        role = Role.objects.create(
            organization=organization, code=code, name=name,
        )
        RolePermission.objects.bulk_create([
            RolePermission(
                role=role, permission=permission, organization=organization,
            )
            for permission in Permission.objects.filter(
                code__in=permission_codes,
            )
        ])
        UserRole.objects.create(user=user, role=role, organization=organization)
    return role


PERMISOS_STAFF = [
    "catalog.branch.read",
    "catalog.specialty.read",
    "catalog.professional.read",
    "scheduling.schedule.read",
    "scheduling.schedule.create",
    "scheduling.schedule.update",
    "scheduling.block.read",
    "scheduling.block.create",
    "scheduling.block.update",
    "scheduling.slot.read",
]

PERMISOS_PACIENTE = [
    "catalog.branch.read",
    "catalog.specialty.read",
    "catalog.professional.read",
    "scheduling.slot.read",
]


@pytest.fixture
def platform_admin(db):
    """El Superadministrador de Plataforma: sin organización, por definición."""
    with platform_admin_context():
        return User.objects.create_platform_admin(
            email="super@plataforma.test",
            password="clave-de-prueba-1",
            first_name="Super",
            last_name="Admin",
            document_number="0000001",
        )


@pytest.fixture
def plans(db):
    """Los planes vienen de la migración semilla."""
    return {plan.code: plan for plan in SubscriptionPlan.objects.all()}


@pytest.fixture
def org_a(db, plans, platform_admin):
    with platform_admin_context():
        org = Organization.objects.create(
            slug="kolping", name="Kolping",
            legal_name="Fundación Centro Multifuncional Adolfo Kolping",
            tax_id="1001", contact_email="contacto@kolping.test",
        )
        Subscription.objects.create(
            organization=org, plan=plans["premium"],
            starts_at="2026-08-01", assigned_by=platform_admin,
        )
    return org


@pytest.fixture
def org_b(db, plans, platform_admin):
    with platform_admin_context():
        org = Organization.objects.create(
            slug="sanluis", name="San Luis",
            legal_name="Clínica San Luis SRL",
            tax_id="1002", contact_email="contacto@sanluis.test",
        )
        Subscription.objects.create(
            organization=org, plan=plans["basic"],
            starts_at="2026-08-01", assigned_by=platform_admin,
        )
    return org


@pytest.fixture
def user_a(db, org_a):
    with tenant_context(org_a.id):
        return User.objects.create_user(
            email="ana@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Ana", last_name="Ríos",
            document_number="5001",
        )


@pytest.fixture
def user_b(db, org_b):
    with tenant_context(org_b.id):
        return User.objects.create_user(
            email="beto@sanluis.test", password="clave-de-prueba-1",
            organization=org_b, first_name="Beto", last_name="Cruz",
            document_number="5002",
        )


@pytest.fixture
def branch_b(db, org_b):
    with tenant_context(org_b.id):
        return Branch.objects.create(organization=org_b, name="Sucursal de B")


# --------------------------------------------------------------------------
#  Catálogo y agendas del Sprint 1 (US-12 a US-16)
# --------------------------------------------------------------------------

@pytest.fixture
def branches_a(db, org_a):
    """Las tres sucursales del caso de estudio, todas en la misma zona."""
    with tenant_context(org_a.id):
        return {
            "centro": Branch.objects.create(
                organization=org_a, name="Sede Centro",
                timezone="America/La_Paz",
            ),
            "norte": Branch.objects.create(
                organization=org_a, name="Sede Norte",
                timezone="America/La_Paz",
            ),
            "sur": Branch.objects.create(
                organization=org_a, name="Sede Sur",
                timezone="America/La_Paz",
            ),
        }


@pytest.fixture
def specialty_a(db, org_a):
    with tenant_context(org_a.id):
        return Specialty.objects.create(
            organization=org_a, name="Cardiología",
            description="Corazón y sistema circulatorio.",
        )


@pytest.fixture
def practitioner_a(db, org_a, branches_a, specialty_a):
    """Una profesional que atiende en las tres sucursales de A."""
    with tenant_context(org_a.id):
        profesional = Practitioner.objects.create(
            organization=org_a, first_name="Laura", last_name="Gómez",
            license_number="MP-1000",
        )
        for sucursal in branches_a.values():
            PractitionerBranch.objects.create(
                organization=org_a, practitioner=profesional, branch=sucursal,
            )
        PractitionerSpecialty.objects.create(
            organization=org_a, practitioner=profesional, specialty=specialty_a,
        )
    return profesional


@pytest.fixture
def staff_a(db, org_a, user_a):
    """`user_a` con permisos de catálogo, agenda, bloqueo y disponibilidad."""
    dar_rol(user_a, org_a, "staff", "Personal", PERMISOS_STAFF)
    return user_a


@pytest.fixture
def patient_a(db, org_a, user_a):
    """`user_a` con lo del rol Paciente: lecturas del catálogo y
    `scheduling.slot.read`."""
    dar_rol(user_a, org_a, "patient", "Paciente", PERMISOS_PACIENTE)
    return user_a


@pytest.fixture
def staff_b(db, org_b, user_b):
    dar_rol(user_b, org_b, "staff", "Personal", PERMISOS_STAFF)
    return user_b
