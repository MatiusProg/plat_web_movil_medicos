"""US-43 — Alta de una organización como inquilino independiente.

Entra por HTTP, como un cliente real (convención §6). Las aserciones sobre la
base van **siempre dentro de un contexto**: fuera de él, RLS devuelve cero
filas y la prueba pasaría aunque el alta no hubiera hecho nada.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog, Role, User, UserRole
from accounts.tokens import tokens_for_user
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization, Subscription

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]


@pytest.fixture
def api_client():
    return APIClient()


def authed(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def alta(slug="nuevo-centro", tax_id="9001", email="admin@nuevo.test", **extra):
    payload = {
        "slug": slug,
        "name": "Centro Nuevo",
        "legal_name": "Centro Médico Nuevo SRL",
        "tax_id": tax_id,
        "contact_email": "contacto@nuevo.test",
        "city": "Santa Cruz",
        "plan_code": "pro",
        "admin": {
            "email": email,
            "first_name": "Marta",
            "last_name": "Vaca",
            "document_number": "8001",
        },
    }
    payload.update(extra)
    return payload


# --------------------------------------------------------------------------
#  Acceso
# --------------------------------------------------------------------------
def test_sin_autenticar_no_se_puede_dar_de_alta(api_client):
    response = api_client.post(
        reverse("tenancy:organization-list"), alta(), format="json",
    )
    assert response.status_code == 401


def test_un_inquilino_no_puede_dar_de_alta_organizaciones(api_client, user_a):
    authed(api_client, user_a)
    response = api_client.post(
        reverse("tenancy:organization-list"), alta(), format="json",
    )
    assert response.status_code == 403


def test_un_inquilino_no_puede_listar_organizaciones(api_client, user_a):
    authed(api_client, user_a)
    response = api_client.get(reverse("tenancy:organization-list"))
    assert response.status_code == 403


# --------------------------------------------------------------------------
#  El alta
# --------------------------------------------------------------------------
def test_el_alta_deja_la_organizacion_lista_para_usarse(api_client, platform_admin):
    authed(api_client, platform_admin)
    response = api_client.post(
        reverse("tenancy:organization-list"), alta(), format="json",
    )

    assert response.status_code == 201, response.data
    body = response.json()
    assert body["slug"] == "nuevo-centro"
    assert body["status"] == "active"
    assert body["current_plan"]["code"] == "pro"

    with platform_admin_context():
        organization = Organization.objects.get(slug="nuevo-centro")
        subscription = Subscription.objects.get(organization=organization)
    assert subscription.ends_at is None
    assert subscription.assigned_by_id == platform_admin.id

    with tenant_context(organization.id):
        # Filtrado por organización a propósito: `roles` tiene DOS políticas
        # permisivas y se suman, así que un `.all()` bajo contexto de inquilino
        # devuelve también las plantillas del sistema, que cualquiera puede
        # leer justamente para poder clonarlas. Sin el filtro, esta prueba
        # mediría la semilla en vez del alta.
        roles = {
            role.code: role
            for role in Role.objects.filter(organization=organization)
        }
        admin_user = User.objects.get(email="admin@nuevo.test")
        assignment = UserRole.objects.get(user=admin_user)
        # Adentro del contexto también esto: `role_permissions` es una
        # consulta perezosa, y afuera devolvería cero filas por RLS aunque los
        # permisos estuvieran clonados.
        permisos_del_admin = roles["org_admin"].role_permissions.count()

    # Las cuatro plantillas de organización, nunca la de plataforma.
    assert set(roles) == {"org_admin", "practitioner", "receptionist", "patient"}
    # is_system False: el CHECK ck_role_system rechaza una copia del sistema
    # dentro de un inquilino.
    assert all(not role.is_system for role in roles.values())
    # El org_admin clonado llega con los permisos de su plantilla.
    assert permisos_del_admin > 0

    assert admin_user.organization_id == organization.id
    assert assignment.role_id == roles["org_admin"].id


def test_la_contrasena_temporal_vuelve_una_vez_y_sirve_para_entrar(
    api_client, platform_admin,
):
    authed(api_client, platform_admin)
    body = api_client.post(
        reverse("tenancy:organization-list"), alta(), format="json",
    ).json()

    temporal = body["admin"]["temporary_password"]
    assert temporal

    with platform_admin_context():
        organization = Organization.objects.get(slug="nuevo-centro")
    with tenant_context(organization.id):
        admin_user = User.objects.get(email="admin@nuevo.test")
        # En la base sólo queda el hash.
        assert admin_user.password != temporal
        assert admin_user.check_password(temporal)

    # Y al consultarla después, la contraseña no aparece por ningún lado.
    detalle = api_client.get(
        reverse("tenancy:organization-detail", args=[organization.id]),
    ).json()
    assert "temporary_password" not in str(detalle)


def test_el_alta_queda_registrada_en_la_bitacora(api_client, platform_admin):
    authed(api_client, platform_admin)
    api_client.post(reverse("tenancy:organization-list"), alta(), format="json")

    with platform_admin_context():
        entrada = AuditLog.objects.get(action="organization.create")
    # organization NULL: es una acción del superadministrador sobre la
    # plataforma. Con el inquilino puesto, no podría volver a leerla.
    assert entrada.organization_id is None
    assert entrada.user_id == platform_admin.id
    assert entrada.detail["slug"] == "nuevo-centro"
    assert entrada.detail["plan"] == "pro"


# --------------------------------------------------------------------------
#  Lo que tiene que fallar
# --------------------------------------------------------------------------
def test_un_slug_repetido_no_deja_nada_a_medias(api_client, platform_admin, org_a):
    authed(api_client, platform_admin)
    response = api_client.post(
        reverse("tenancy:organization-list"),
        alta(slug=org_a.slug), format="json",
    )

    assert response.status_code == 400
    assert "slug" in response.data

    # Y no quedó un usuario administrador huérfano de la organización que no
    # llegó a crearse. Se consulta con contexto: sin él, RLS devuelve cero
    # filas y esta aserción no probaría nada.
    with tenant_context(org_a.id):
        assert not User.objects.filter(email="admin@nuevo.test").exists()


def test_un_nit_repetido_se_rechaza(api_client, platform_admin, org_a):
    authed(api_client, platform_admin)
    response = api_client.post(
        reverse("tenancy:organization-list"),
        alta(tax_id=org_a.tax_id), format="json",
    )
    assert response.status_code == 400
    assert "tax_id" in response.data


def test_un_slug_con_formato_invalido_se_rechaza(api_client, platform_admin):
    authed(api_client, platform_admin)
    response = api_client.post(
        reverse("tenancy:organization-list"),
        alta(slug="Centro Nuevo"), format="json",
    )
    assert response.status_code == 400
    assert "slug" in response.data


def test_un_plan_inexistente_se_rechaza(api_client, platform_admin):
    authed(api_client, platform_admin)
    response = api_client.post(
        reverse("tenancy:organization-list"),
        alta(plan_code="inexistente"), format="json",
    )
    assert response.status_code == 400
    assert "plan_code" in response.data


# --------------------------------------------------------------------------
#  Aislamiento: el punto 4 de la Definición de Terminado
# --------------------------------------------------------------------------
def test_el_inquilino_recien_creado_no_ve_datos_de_otro(
    api_client, platform_admin, org_a, user_a,
):
    authed(api_client, platform_admin)
    api_client.post(reverse("tenancy:organization-list"), alta(), format="json")

    with platform_admin_context():
        nueva = Organization.objects.get(slug="nuevo-centro")

    # Desde el contexto de la organización nueva, la otra no existe: ni sus
    # usuarios, ni sus roles, ni su ficha.
    with tenant_context(nueva.id):
        assert not User.objects.filter(id=user_a.id).exists()
        assert not Role.objects.filter(organization=org_a).exists()
        assert not Organization.objects.filter(id=org_a.id).exists()

    # Y al revés: los roles clonados son suyos y no se ven desde la otra.
    with tenant_context(org_a.id):
        assert not Role.objects.filter(organization=nueva).exists()


def test_el_superadministrador_no_ve_los_usuarios_del_inquilino_que_creo(
    api_client, platform_admin,
):
    """Decisión D-3: el superadmin administra la plataforma, no los datos.

    Crea la organización y su administrador, y acto seguido deja de poder
    verlo. Es a propósito y lo hace cumplir la base, no la aplicación.
    """
    authed(api_client, platform_admin)
    api_client.post(reverse("tenancy:organization-list"), alta(), format="json")

    with platform_admin_context():
        assert not User.objects.filter(email="admin@nuevo.test").exists()
