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
from accounts.tokens import TokenDeInquilino, tokens_para
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import IsolationAlert

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]


@pytest.fixture
def cliente():
    return APIClient()


def acceso(user):
    return tokens_para(user)["access"]


# --------------------------------------------------------------------------
#  Que el backend arranque. Suena trivial; no lo era.
# --------------------------------------------------------------------------
def test_el_middleware_se_importa():
    """Un ImportError acá deja el backend sin arrancar, y ninguna prueba de
    base de datos lo detecta."""
    import tenancy.middleware  # noqa: F401

    assert hasattr(tenancy.middleware.TenantMiddleware, "process_request")


def test_una_peticion_sin_autenticar_responde(cliente):
    respuesta = cliente.get(reverse("health"))
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"


# --------------------------------------------------------------------------
#  El token lleva el contexto, y sin eso no se puede autenticar
# --------------------------------------------------------------------------
def test_el_token_lleva_la_organizacion(user_a, org_a):
    token = TokenDeInquilino.for_user(user_a)
    assert token["organization_id"] == str(org_a.id)
    assert token["is_platform_admin"] is False
    # El de acceso hereda los claims del de refresco.
    assert token.access_token["organization_id"] == str(org_a.id)


def test_el_token_del_superadmin_no_lleva_organizacion(platform_admin):
    token = TokenDeInquilino.for_user(platform_admin)
    assert token["organization_id"] is None
    assert token["is_platform_admin"] is True


def test_un_token_sin_los_claims_se_rechaza(user_a, cliente):
    """Un token emitido con AccessToken.for_user() a secas no sirve.

    Antes fallaba con "User not found", que no explica nada. Ahora se rechaza
    diciendo el motivo real.
    """
    from rest_framework_simplejwt.tokens import AccessToken

    crudo = str(AccessToken.for_user(user_a))
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {crudo}")
    respuesta = cliente.get(reverse("health"))
    assert respuesta.status_code == 401
    assert "organización" in str(respuesta.json()).lower()


# --------------------------------------------------------------------------
#  El escenario que planteó Karen: token de una organización, slug de otra
# --------------------------------------------------------------------------
def test_el_token_manda_sobre_el_encabezado(user_a, org_a, org_b, cliente):
    """Manda el token, no el slug. Si no fuera así, bastaría con cambiar un
    encabezado para leer los datos de otra organización."""
    cliente.credentials(
        HTTP_AUTHORIZATION=f"Bearer {acceso(user_a)}",
        HTTP_X_ORGANIZATION=org_b.slug,
    )
    respuesta = cliente.get(reverse("health"))
    assert respuesta.status_code == 200
    assert respuesta.json()["tenant"] == str(org_a.id)


def test_el_slug_solo_aplica_sin_token(org_a, cliente):
    cliente.credentials(HTTP_X_ORGANIZATION=org_a.slug)
    respuesta = cliente.get(reverse("health"))
    assert respuesta.json()["tenant"] == str(org_a.id)


def test_un_slug_inexistente_no_fija_contexto(cliente):
    cliente.credentials(HTTP_X_ORGANIZATION="no-existe")
    respuesta = cliente.get(reverse("health"))
    assert respuesta.json()["tenant"] == ""


# --------------------------------------------------------------------------
#  Defensa en profundidad: el claim tiene que coincidir con la realidad
# --------------------------------------------------------------------------
def test_un_token_con_otra_organizacion_se_rechaza_y_se_alerta(
    user_a, org_b, cliente
):
    """Un token firmado no se puede falsificar, pero sí podría quedar
    desactualizado o emitirse mal. La comprobación es la última barrera."""
    token = TokenDeInquilino.for_user(user_a)
    token["organization_id"] = str(org_b.id)      # manipulado a mano
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    respuesta = cliente.get(reverse("health"))
    assert respuesta.status_code == 401

    with platform_admin_context():
        alerta = IsolationAlert.objects.filter(
            alert_type=IsolationAlert.AlertType.JWT_MISMATCH
        ).first()
    assert alerta is not None
    assert alerta.severity == IsolationAlert.Severity.CRITICAL


def test_un_usuario_no_puede_pasar_por_superadmin(user_a, cliente):
    token = TokenDeInquilino.for_user(user_a)
    token["is_platform_admin"] = True             # manipulado a mano
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {token.access_token}")

    respuesta = cliente.get(reverse("health"))
    assert respuesta.status_code == 401


# --------------------------------------------------------------------------
#  El contexto no sobrevive a la petición
# --------------------------------------------------------------------------
def test_el_contexto_no_se_filtra_entre_peticiones(user_a, org_a, cliente):
    """Si el contexto sobreviviera, la petición siguiente leería datos ajenos.
    Es la fuga que evita usar SET LOCAL en lugar de SET."""
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso(user_a)}")
    assert cliente.get(reverse("health")).json()["tenant"] == str(org_a.id)

    limpio = APIClient()
    assert limpio.get(reverse("health")).json()["tenant"] == ""


def test_el_superadmin_se_autentica(platform_admin, cliente):
    cliente.credentials(HTTP_AUTHORIZATION=f"Bearer {acceso(platform_admin)}")
    respuesta = cliente.get(reverse("health"))
    assert respuesta.json()["platform_admin"] is True
    assert respuesta.json()["tenant"] == ""
