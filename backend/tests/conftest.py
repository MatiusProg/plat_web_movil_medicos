"""Fixtures compartidas.

Las pruebas se conectan como ``app_user``, igual que la aplicación. Correrlas
como ``postgres`` no probaría nada: ``postgres`` es superusuario y omite las
políticas RLS aunque las tablas tengan ``FORCE``. Es el punto 1 del README, y
ya nos costó cinco defectos.
"""

import pytest

from accounts.models import User
from catalog.models import Branch
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization, Subscription, SubscriptionPlan


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
