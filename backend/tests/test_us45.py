"""US-45 — Panel del superadministrador: métricas globales de la plataforma.

Entra por HTTP, como un cliente real (convención del proyecto, ver
docs/convenciones-de-codigo.md §6).
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from tenancy.context import platform_admin_context
from tenancy.models import IsolationAlert

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]


@pytest.fixture
def api_client():
    return APIClient()


def access_token_for(user):
    return tokens_for_user(user)["access"]


def authed(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token_for(user)}")
    return api_client


# --------------------------------------------------------------------------
#  Acceso
# --------------------------------------------------------------------------
def test_sin_autenticar_no_entra_al_dashboard(api_client):
    response = api_client.get(reverse("tenancy:dashboard"))
    assert response.status_code == 401


def test_un_inquilino_normal_no_entra_al_dashboard(api_client, user_a):
    authed(api_client, user_a)
    response = api_client.get(reverse("tenancy:dashboard"))
    assert response.status_code == 403


def test_el_superadmin_entra_al_dashboard(api_client, platform_admin):
    authed(api_client, platform_admin)
    response = api_client.get(reverse("tenancy:dashboard"))
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"organizations", "by_plan", "alerts"}


def test_un_inquilino_normal_no_entra_a_las_alertas(api_client, user_a):
    authed(api_client, user_a)
    response = api_client.get(reverse("tenancy:alert-list"))
    assert response.status_code == 403


# --------------------------------------------------------------------------
#  Datos reales
# --------------------------------------------------------------------------
def test_el_dashboard_refleja_las_organizaciones_y_planes(
    api_client, platform_admin, org_a, org_b,
):
    authed(api_client, platform_admin)
    body = api_client.get(reverse("tenancy:dashboard")).json()

    assert body["organizations"]["total"] == 2
    assert body["organizations"]["active"] == 2

    planes = {row["plan_code"]: row["count"] for row in body["by_plan"]}
    assert planes["premium"] == 1  # org_a
    assert planes["basic"] == 1    # org_b


def test_el_dashboard_cuenta_alertas_pendientes(api_client, platform_admin, org_a):
    with platform_admin_context():
        IsolationAlert.objects.create(
            source_organization=org_a,
            alert_type=IsolationAlert.AlertType.RLS_DENIED,
            severity=IsolationAlert.Severity.CRITICAL,
            description="prueba",
        )

    authed(api_client, platform_admin)
    body = api_client.get(reverse("tenancy:dashboard")).json()

    assert body["alerts"]["pending"] == 1
    assert body["alerts"]["critical_pending"] == 1


def test_el_superadmin_lista_las_alertas(api_client, platform_admin, org_a):
    with platform_admin_context():
        IsolationAlert.objects.create(
            source_organization=org_a,
            alert_type=IsolationAlert.AlertType.NO_CONTEXT,
            severity=IsolationAlert.Severity.MEDIUM,
            description="prueba",
        )

    authed(api_client, platform_admin)
    response = api_client.get(reverse("tenancy:alert-list"))
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_el_filtro_de_estado_funciona(api_client, platform_admin, org_a):
    with platform_admin_context():
        IsolationAlert.objects.create(
            source_organization=org_a,
            alert_type=IsolationAlert.AlertType.NO_CONTEXT,
            severity=IsolationAlert.Severity.LOW,
            description="pendiente",
            status=IsolationAlert.Status.PENDING,
        )
        IsolationAlert.objects.create(
            source_organization=org_a,
            alert_type=IsolationAlert.AlertType.NO_CONTEXT,
            severity=IsolationAlert.Severity.LOW,
            description="resuelta",
            status=IsolationAlert.Status.RESOLVED,
            resolved_at="2026-08-01T00:00:00Z",
        )

    authed(api_client, platform_admin)
    response = api_client.get(reverse("tenancy:alert-list"), {"status": "pending"})
    assert response.json()["count"] == 1
    assert response.json()["results"][0]["description"] == "pendiente"


def test_una_alerta_del_middleware_aparece_en_la_lista(
    api_client, user_a, org_b, platform_admin,
):
    """El mismo escenario de test_peticiones.py: token de una organización,
    slug de otra. La alerta que deja el middleware debe verse en el panel."""
    from accounts.tokens import TenantRefreshToken

    token = TenantRefreshToken.for_user(user_a)
    token["organization_id"] = str(org_b.id)
    intruso = APIClient()
    intruso.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")
    intruso.get(reverse("health"))  # dispara el rechazo y la alerta pendiente

    authed(api_client, platform_admin)
    response = api_client.get(
        reverse("tenancy:alert-list"), {"severity": "critical"},
    )
    assert response.json()["count"] == 1
