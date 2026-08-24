"""US-02 — Inicio de sesión, renovación y cierre.

Todas entran por HTTP, con el cliente de DRF, como pide el punto 6 de las
convenciones: las pruebas que sólo tocan el ORM no pasan por el middleware ni
por la autenticación, y ahí es justamente donde vive el aislamiento.
"""

from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import LoginAttempt, Role, User, UserRole
from accounts.tokens import tokens_for_user
from tenancy.context import platform_admin_context, tenant_context

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def rol_recepcionista(org_a, user_a):
    """Un rol con un permiso, para comprobar que el login los devuelve."""
    from accounts.models import Permission, RolePermission

    with tenant_context(org_a.id):
        rol = Role.objects.create(
            organization=org_a, code="receptionist", name="Recepcionista",
        )
        permiso = Permission.objects.create(
            code="patients.patient.search", module="patients",
        )
        RolePermission.objects.create(
            role=rol, permission=permiso, organization=org_a,
        )
        UserRole.objects.create(user=user_a, role=rol, organization=org_a)
    return rol


def iniciar_sesion(api_client, org, email, password=CLAVE, **extra):
    return api_client.post(
        reverse("accounts:login"),
        {"organization": org.slug if org else "", "email": email,
         "password": password},
        format="json", **extra,
    )


# --------------------------------------------------------------------------
#  Criterio 1 — Un usuario válido entra y recibe su par de tokens
# --------------------------------------------------------------------------
def test_un_usuario_valido_recibe_los_dos_tokens(api_client, org_a, user_a):
    response = iniciar_sesion(api_client, org_a, user_a.email)

    assert response.status_code == 200, response.data
    cuerpo = response.json()
    assert cuerpo["access"] and cuerpo["refresh"]
    assert cuerpo["user"]["email"] == user_a.email
    assert cuerpo["user"]["organization"] == org_a.slug
    assert cuerpo["user"]["is_platform_admin"] is False


def test_el_token_emitido_lleva_el_contexto_de_inquilino(api_client, org_a, user_a):
    """Sin los claims del proyecto el token no puede autenticar: la búsqueda
    del usuario devuelve cero filas por RLS."""
    from rest_framework_simplejwt.tokens import AccessToken

    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()
    token = AccessToken(cuerpo["access"])

    assert token["organization_id"] == str(org_a.id)
    assert token["is_platform_admin"] is False


def test_el_token_del_login_sirve_para_pedir_datos(api_client, org_a, user_a):
    """El ciclo completo: iniciar sesión y usar el token en otra petición."""
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()

    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {cuerpo['access']}")
    response = api_client.post(reverse("accounts:logout"),
                               {"refresh": cuerpo["refresh"]}, format="json")

    assert response.status_code == 204


# --------------------------------------------------------------------------
#  "para acceder a las funciones según mi rol"
# --------------------------------------------------------------------------
def test_la_respuesta_trae_los_roles_y_los_permisos(
    api_client, org_a, user_a, rol_recepcionista,
):
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()

    assert cuerpo["user"]["roles"] == [
        {"code": "receptionist", "name": "Recepcionista"},
    ]
    assert cuerpo["user"]["permissions"] == ["patients.patient.search"]


def test_un_usuario_sin_roles_entra_igual_pero_sin_permisos(
    api_client, org_a, user_a,
):
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()

    assert cuerpo["user"]["roles"] == []
    assert cuerpo["user"]["permissions"] == []


# --------------------------------------------------------------------------
#  Credenciales incorrectas
# --------------------------------------------------------------------------
def test_una_contrasena_incorrecta_no_deja_entrar(api_client, org_a, user_a):
    response = iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    assert response.status_code == 401
    assert response.json()["code"] == "credenciales_invalidas"
    assert "access" not in response.json()


def test_un_correo_inexistente_responde_igual_que_una_clave_mala(
    api_client, org_a, user_a,
):
    """No se puede averiguar qué correos existen desde el formulario."""
    inexistente = iniciar_sesion(api_client, org_a, "nadie@kolping.test")
    clave_mala = iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    assert inexistente.status_code == clave_mala.status_code == 401
    assert inexistente.json() == clave_mala.json()


def test_una_organizacion_inexistente_no_deja_entrar(api_client, org_a, user_a):
    response = api_client.post(
        reverse("accounts:login"),
        {"organization": "no-existe", "email": user_a.email, "password": CLAVE},
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["code"] == "organizacion_no_disponible"


def test_una_cuenta_dada_de_baja_no_entra(api_client, org_a, user_a):
    with tenant_context(org_a.id):
        user_a.is_active = False
        user_a.save(update_fields=["is_active"])

    response = iniciar_sesion(api_client, org_a, user_a.email)

    assert response.status_code == 403
    assert response.json()["code"] == "cuenta_inactiva"


# --------------------------------------------------------------------------
#  RNF-08 — El aislamiento, en el propio login
# --------------------------------------------------------------------------
def test_el_usuario_de_una_organizacion_no_entra_por_la_otra(
    api_client, org_a, org_b, user_a,
):
    """El mismo correo y la misma clave, con el slug del centro médico vecino.

    Es el escenario que más se parece a una fuga: credenciales válidas, y lo
    único que cambia es el inquilino.
    """
    response = iniciar_sesion(api_client, org_b, user_a.email)

    assert response.status_code == 401
    assert response.json()["code"] == "credenciales_invalidas"


def test_dos_organizaciones_pueden_compartir_el_correo(
    api_client, org_a, org_b, user_a,
):
    """Decisión D-5: el correo es único por organización, no global.

    Es la razón por la que el login no puede usar
    ``django.contrib.auth.authenticate``.
    """
    with tenant_context(org_b.id):
        User.objects.create_user(
            email=user_a.email, password="otra-clave-distinta-1",
            organization=org_b, first_name="Homónima", last_name="Cruz",
            document_number="5099",
        )

    en_a = iniciar_sesion(api_client, org_a, user_a.email)
    en_b = iniciar_sesion(api_client, org_b, user_a.email, "otra-clave-distinta-1")

    assert en_a.status_code == 200, en_a.data
    assert en_b.status_code == 200, en_b.data
    assert en_a.json()["user"]["id"] != en_b.json()["user"]["id"]
    assert en_a.json()["user"]["organization"] == org_a.slug
    assert en_b.json()["user"]["organization"] == org_b.slug


# --------------------------------------------------------------------------
#  RNF-07 — Bloqueo temporal tras 5 intentos fallidos
# --------------------------------------------------------------------------
def test_cinco_intentos_fallidos_bloquean_la_cuenta(api_client, org_a, user_a):
    for _ in range(5):
        respuesta = iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")
        assert respuesta.status_code == 401

    with tenant_context(org_a.id):
        user_a.refresh_from_db()
    assert user_a.failed_login_attempts == 5
    assert user_a.is_locked


def test_la_cuenta_bloqueada_no_entra_ni_con_la_clave_correcta(
    api_client, org_a, user_a,
):
    for _ in range(5):
        iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    response = iniciar_sesion(api_client, org_a, user_a.email)

    assert response.status_code == 423
    assert response.json()["code"] == "cuenta_bloqueada"


def test_insistir_sobre_una_cuenta_bloqueada_no_extiende_el_bloqueo(
    api_client, org_a, user_a,
):
    """Si cada intento sumara, el bloqueo no vencería nunca."""
    for _ in range(5):
        iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")
    with tenant_context(org_a.id):
        user_a.refresh_from_db()
    vencimiento = user_a.locked_until

    for _ in range(3):
        iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    with tenant_context(org_a.id):
        user_a.refresh_from_db()
    assert user_a.failed_login_attempts == 5
    assert user_a.locked_until == vencimiento


def test_cuatro_intentos_fallidos_no_bloquean(api_client, org_a, user_a):
    for _ in range(4):
        iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    response = iniciar_sesion(api_client, org_a, user_a.email)

    assert response.status_code == 200, response.data


def test_un_login_valido_limpia_el_contador(api_client, org_a, user_a):
    for _ in range(3):
        iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    iniciar_sesion(api_client, org_a, user_a.email)

    with tenant_context(org_a.id):
        user_a.refresh_from_db()
    assert user_a.failed_login_attempts == 0
    assert user_a.locked_until is None
    assert user_a.last_login_at is not None


def test_vencido_el_bloqueo_la_cuenta_vuelve_a_entrar(api_client, org_a, user_a):
    with tenant_context(org_a.id):
        user_a.failed_login_attempts = 5
        user_a.locked_until = timezone.now() - timedelta(minutes=1)
        user_a.save(update_fields=["failed_login_attempts", "locked_until"])

    response = iniciar_sesion(api_client, org_a, user_a.email)

    assert response.status_code == 200, response.data


# --------------------------------------------------------------------------
#  La bitácora de intentos sobrevive al fallo
# --------------------------------------------------------------------------
def test_un_intento_fallido_queda_registrado(api_client, org_a, user_a):
    """El caso que se rompe si alguien cambia el Response por un raise: DRF
    llama a set_rollback() al manejar la excepción y la fila se descarta."""
    iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    with platform_admin_context():
        intento = LoginAttempt.objects.get(attempted_email=user_a.email)
    assert intento.succeeded is False
    assert intento.failure_reason == LoginAttempt.FailureReason.BAD_CREDENTIALS
    assert intento.organization_id == org_a.id


def test_un_login_valido_queda_registrado(api_client, org_a, user_a):
    iniciar_sesion(api_client, org_a, user_a.email)

    with platform_admin_context():
        intento = LoginAttempt.objects.get(attempted_email=user_a.email)
    assert intento.succeeded is True
    assert intento.user_id == user_a.id


def test_un_correo_desconocido_queda_registrado(api_client, org_a):
    iniciar_sesion(api_client, org_a, "nadie@kolping.test")

    with platform_admin_context():
        intento = LoginAttempt.objects.get(attempted_email="nadie@kolping.test")
    assert intento.failure_reason == LoginAttempt.FailureReason.UNKNOWN_USER
    assert intento.user_id is None


def test_una_organizacion_inventada_queda_registrada(api_client, user_a):
    api_client.post(
        reverse("accounts:login"),
        {"organization": "no-existe", "email": user_a.email, "password": CLAVE},
        format="json",
    )

    with platform_admin_context():
        intento = LoginAttempt.objects.get(attempted_email=user_a.email)
    assert intento.failure_reason == LoginAttempt.FailureReason.UNKNOWN_TENANT
    assert intento.organization_id is None


def test_solo_el_superadministrador_lee_los_intentos(api_client, org_a, user_a):
    """``login_attempts`` es un buzón: cualquiera inserta, sólo el superadmin lee."""
    iniciar_sesion(api_client, org_a, user_a.email, "no-es-esta")

    with tenant_context(org_a.id):
        assert LoginAttempt.objects.count() == 0
    with platform_admin_context():
        assert LoginAttempt.objects.count() == 1


# --------------------------------------------------------------------------
#  El Superadministrador de Plataforma
# --------------------------------------------------------------------------
def test_el_superadministrador_entra_sin_organizacion(api_client, platform_admin):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": platform_admin.email, "password": CLAVE},
        format="json",
    )

    assert response.status_code == 200, response.data
    cuerpo = response.json()
    assert cuerpo["user"]["is_platform_admin"] is True
    assert cuerpo["user"]["organization"] is None


def test_el_superadministrador_no_entra_por_una_organizacion(
    api_client, org_a, platform_admin,
):
    """Su fila tiene ``organization_id`` NULL: bajo el contexto de un inquilino
    su propia política RLS lo deja fuera."""
    response = iniciar_sesion(api_client, org_a, platform_admin.email)

    assert response.status_code == 401


def test_un_usuario_de_organizacion_no_entra_como_plataforma(
    api_client, org_a, user_a,
):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": user_a.email, "password": CLAVE},
        format="json",
    )

    assert response.status_code == 401


# --------------------------------------------------------------------------
#  El encabezado X-Organization, que es lo que va a usar el frontend
# --------------------------------------------------------------------------
def test_la_organizacion_puede_venir_en_el_encabezado(api_client, org_a, user_a):
    response = api_client.post(
        reverse("accounts:login"),
        {"email": user_a.email, "password": CLAVE},
        format="json", HTTP_X_ORGANIZATION=org_a.slug,
    )

    assert response.status_code == 200, response.data
    assert response.json()["user"]["organization"] == org_a.slug


# --------------------------------------------------------------------------
#  RNF-06 — Renovación del token
# --------------------------------------------------------------------------
def test_el_refresco_devuelve_un_par_nuevo(api_client, org_a, user_a):
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()

    response = api_client.post(
        reverse("accounts:token-refresh"), {"refresh": cuerpo["refresh"]},
        format="json",
    )

    assert response.status_code == 200, response.data
    nuevo = response.json()
    assert nuevo["access"] != cuerpo["access"]
    assert nuevo["refresh"] != cuerpo["refresh"]


def test_el_token_renovado_conserva_el_contexto(api_client, org_a, user_a):
    """Si se perdieran los claims, el token nuevo fallaría en la petición
    siguiente con un confuso "User not found"."""
    from rest_framework_simplejwt.tokens import AccessToken

    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()
    nuevo = api_client.post(
        reverse("accounts:token-refresh"), {"refresh": cuerpo["refresh"]},
        format="json",
    ).json()

    token = AccessToken(nuevo["access"])
    assert token["organization_id"] == str(org_a.id)
    assert token["is_platform_admin"] is False


def test_el_refresco_usado_no_sirve_dos_veces(api_client, org_a, user_a):
    """ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION."""
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()
    api_client.post(reverse("accounts:token-refresh"),
                    {"refresh": cuerpo["refresh"]}, format="json")

    segundo = api_client.post(reverse("accounts:token-refresh"),
                              {"refresh": cuerpo["refresh"]}, format="json")

    assert segundo.status_code == 401


def test_un_refresco_inventado_no_sirve(api_client):
    response = api_client.post(
        reverse("accounts:token-refresh"), {"refresh": "esto-no-es-un-token"},
        format="json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "refresh_invalido"


def test_un_token_sin_los_claims_del_proyecto_se_rechaza(api_client, user_a):
    """Un token emitido con RefreshToken.for_user() en vez de tokens_for_user()."""
    from rest_framework_simplejwt.tokens import RefreshToken

    crudo = RefreshToken.for_user(user_a)

    response = api_client.post(
        reverse("accounts:token-refresh"), {"refresh": str(crudo)}, format="json",
    )

    assert response.status_code == 401
    assert response.json()["code"] == "token_sin_organizacion"


# --------------------------------------------------------------------------
#  CU4 — Cierre de sesión
# --------------------------------------------------------------------------
def test_el_cierre_de_sesion_invalida_el_refresco(api_client, org_a, user_a):
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {cuerpo['access']}")

    cierre = api_client.post(reverse("accounts:logout"),
                             {"refresh": cuerpo["refresh"]}, format="json")
    renovacion = api_client.post(reverse("accounts:token-refresh"),
                                 {"refresh": cuerpo["refresh"]}, format="json")

    assert cierre.status_code == 204
    assert renovacion.status_code == 401


def test_no_se_puede_cerrar_la_sesion_sin_autenticar(api_client, org_a, user_a):
    cuerpo = iniciar_sesion(api_client, org_a, user_a.email).json()

    response = api_client.post(reverse("accounts:logout"),
                               {"refresh": cuerpo["refresh"]}, format="json")

    assert response.status_code == 401


def test_no_se_puede_cerrar_la_sesion_de_otro(api_client, org_a, org_b, user_a, user_b):
    """Sin esta comprobación, un refresh ajeno permitiría echar a cualquiera."""
    de_b = tokens_for_user(user_b)["refresh"]
    mio = iniciar_sesion(api_client, org_a, user_a.email).json()
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {mio['access']}")

    response = api_client.post(reverse("accounts:logout"),
                               {"refresh": de_b}, format="json")

    assert response.status_code == 403
    assert response.json()["code"] == "refresh_ajeno"
