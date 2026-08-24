"""Aislamiento en el ciclo real de una petición HTTP.

Las pruebas de ``test_isolation.py`` verifican las políticas de la base, pero
ninguna pasa por el middleware ni por la autenticación. Por eso el backend
podía estar roto —un ImportError en el middleware— con las 21 en verde.

Estas pruebas cubren ese hueco: entran por el cliente HTTP, como un cliente
real. Reportadas por Karen en la revisión del 2026-08-23.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from accounts.tokens import TenantRefreshToken, tokens_for_user
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import IsolationAlert

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]


@pytest.fixture
def api_client():
    return APIClient()


def access_token_for(user):
    return tokens_for_user(user)["access"]


# --------------------------------------------------------------------------
#  Que el backend arranque. Suena trivial; no lo era.
# --------------------------------------------------------------------------
def test_el_middleware_se_importa():
    """Un ImportError acá deja el backend sin arrancar, y ninguna prueba de
    base de datos lo detecta."""
    import tenancy.middleware  # noqa: F401

    assert hasattr(tenancy.middleware.TenantMiddleware, "process_request")


def test_una_peticion_sin_autenticar_responde(api_client):
    response = api_client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


# --------------------------------------------------------------------------
#  El token lleva el contexto, y sin eso no se puede autenticar
# --------------------------------------------------------------------------
def test_el_token_lleva_la_organizacion(user_a, org_a):
    token = TenantRefreshToken.for_user(user_a)
    assert token["organization_id"] == str(org_a.id)
    assert token["is_platform_admin"] is False
    # El de acceso hereda los claims del de refresco.
    assert token.access_token["organization_id"] == str(org_a.id)


def test_el_token_del_superadmin_no_lleva_organizacion(platform_admin):
    token = TenantRefreshToken.for_user(platform_admin)
    assert token["organization_id"] is None
    assert token["is_platform_admin"] is True


def test_un_token_sin_los_claims_se_rechaza(user_a, api_client):
    """Un token emitido con AccessToken.for_user() a secas no sirve.

    Antes fallaba con "User not found", que no explica nada. Ahora se rechaza
    diciendo el motivo real.
    """
    from rest_framework_simplejwt.tokens import AccessToken

    raw = str(AccessToken.for_user(user_a))
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {raw}")
    response = api_client.get(reverse("health"))
    assert response.status_code == 401
    assert "organización" in str(response.json()).lower()


# --------------------------------------------------------------------------
#  El escenario que planteó Karen: token de una organización, slug de otra
# --------------------------------------------------------------------------
def test_el_token_manda_sobre_el_encabezado(user_a, org_a, org_b, api_client):
    """Manda el token, no el slug. Si no fuera así, bastaría con cambiar un
    encabezado para leer los datos de otra organización."""
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access_token_for(user_a)}",
        HTTP_X_ORGANIZATION=org_b.slug,
    )
    response = api_client.get(reverse("health"))
    assert response.status_code == 200
    assert response.json()["tenant"] == str(org_a.id)


def test_el_slug_solo_aplica_sin_token(org_a, api_client):
    api_client.credentials(HTTP_X_ORGANIZATION=org_a.slug)
    response = api_client.get(reverse("health"))
    assert response.json()["tenant"] == str(org_a.id)


def test_un_slug_inexistente_no_fija_contexto(api_client):
    api_client.credentials(HTTP_X_ORGANIZATION="no-existe")
    response = api_client.get(reverse("health"))
    assert response.json()["tenant"] == ""


# --------------------------------------------------------------------------
#  Defensa en profundidad: el claim tiene que coincidir con la realidad
# --------------------------------------------------------------------------
def test_un_token_con_otra_organizacion_se_rechaza_y_se_alerta(
    user_a, org_b, api_client
):
    """Un token firmado no se puede falsificar, pero sí podría quedar
    desactualizado o emitirse mal. La comprobación es la última barrera."""
    token = TenantRefreshToken.for_user(user_a)
    token["organization_id"] = str(org_b.id)      # manipulado a mano
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    response = api_client.get(reverse("health"))
    assert response.status_code == 401

    with platform_admin_context():
        alert = IsolationAlert.objects.filter(
            alert_type=IsolationAlert.AlertType.JWT_MISMATCH
        ).first()
    assert alert is not None
    assert alert.severity == IsolationAlert.Severity.CRITICAL


def test_un_usuario_no_puede_pasar_por_superadmin(user_a, api_client):
    token = TenantRefreshToken.for_user(user_a)
    token["is_platform_admin"] = True             # manipulado a mano
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    response = api_client.get(reverse("health"))
    assert response.status_code == 401


# --------------------------------------------------------------------------
#  El contexto no sobrevive a la petición
# --------------------------------------------------------------------------
def test_el_contexto_no_se_filtra_entre_peticiones(user_a, org_a, api_client):
    """Si el contexto sobreviviera, la petición siguiente leería datos ajenos.
    Es la fuga que evita usar SET LOCAL en lugar de SET."""
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token_for(user_a)}")
    assert api_client.get(reverse("health")).json()["tenant"] == str(org_a.id)

    clean = APIClient()
    assert clean.get(reverse("health")).json()["tenant"] == ""


def test_el_superadmin_se_autentica(platform_admin, api_client):
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token_for(platform_admin)}")
    response = api_client.get(reverse("health"))
    assert response.json()["platform_admin"] is True
    assert response.json()["tenant"] == ""
