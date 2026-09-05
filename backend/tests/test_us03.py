"""US-03 — Recuperación de contraseña.

Todas entran por HTTP, como pide el punto 6 de las convenciones.

El bloque más importante es el primero: **que la respuesta no delate qué
correos están registrados**. Es el punto (b) de la historia y lo único que no
se puede arreglar después, porque una vez que el formulario funciona como
oráculo, cualquiera puede averiguar quién es paciente de qué centro médico
sin autenticarse.
"""

from datetime import timedelta

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AuditLog, PasswordResetToken, User
from accounts.services.password_reset import hash_token
from accounts.tokens import tokens_for_user
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"
CLAVE_NUEVA = "Recuperada-2026"


@pytest.fixture
def api_client():
    return APIClient()


def pedir_enlace(api_client, organization, email):
    return api_client.post(
        reverse("accounts:password-reset"),
        {"organization": organization.slug, "email": email},
        format="json",
    )


def token_del_correo():
    """Saca el token del enlace que se mandó, como haría quien lo recibe."""
    cuerpo = mail.outbox[-1].body
    _, _, resto = cuerpo.partition("?token=")
    token, _, _ = resto.partition("&")
    return token


# --------------------------------------------------------------------------
#  Punto (b) — la respuesta no dice si la cuenta existe
# --------------------------------------------------------------------------
def test_la_respuesta_es_identica_exista_o_no_la_cuenta(api_client, org_a, user_a):
    existente = pedir_enlace(api_client, org_a, user_a.email)
    inventado = pedir_enlace(api_client, org_a, "nadie@kolping.test")

    assert existente.status_code == inventado.status_code == 200
    assert existente.json() == inventado.json()


def test_a_un_correo_que_no_existe_no_se_le_manda_nada(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, "nadie@kolping.test")

    assert mail.outbox == []
    with tenant_context(org_a.id):
        assert not PasswordResetToken.objects.exists()


def test_una_cuenta_dada_de_baja_no_recibe_enlace(api_client, org_a, user_a):
    """Y la respuesta sigue siendo la misma: la baja tampoco se delata."""
    with tenant_context(org_a.id):
        User.objects.filter(id=user_a.id).update(is_active=False)

    respuesta = pedir_enlace(api_client, org_a, user_a.email)

    assert respuesta.status_code == 200
    assert mail.outbox == []


def test_la_organizacion_inexistente_si_se_informa(api_client, org_a):
    """El slug no es un secreto: hace falta conocerlo para poder entrar."""
    respuesta = api_client.post(
        reverse("accounts:password-reset"),
        {"organization": "no-existe", "email": "quien@sea.test"},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "organizacion_no_disponible"


# --------------------------------------------------------------------------
#  Puntos (c) y (d) — el token y su registro
# --------------------------------------------------------------------------
def test_se_manda_el_enlace_con_la_marca_de_la_organizacion(
    api_client, org_a, user_a,
):
    pedir_enlace(api_client, org_a, user_a.email)

    assert len(mail.outbox) == 1
    correo = mail.outbox[0]
    assert correo.to == [user_a.email]
    assert org_a.name in correo.subject
    assert org_a.name in correo.body
    assert f"organization={org_a.slug}" in correo.body


def test_en_la_base_queda_el_hash_y_no_el_token(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)
    token = token_del_correo()

    with tenant_context(org_a.id):
        guardado = PasswordResetToken.objects.get()

    assert guardado.token_hash == hash_token(token)
    assert token not in guardado.token_hash
    assert len(guardado.token_hash) == 64


def test_el_enlace_vence_en_treinta_minutos(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)

    with tenant_context(org_a.id):
        guardado = PasswordResetToken.objects.get()

    faltan = guardado.expires_at - timezone.now()
    assert timedelta(minutes=29) < faltan <= timedelta(minutes=30)


def test_la_solicitud_queda_en_la_bitacora(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action="password.reset.request")

    assert asiento.organization_id == org_a.id
    assert asiento.detail["email"] == user_a.email


def test_pedir_otro_enlace_invalida_el_anterior(api_client, org_a, user_a):
    """Sin esto, pedir diez veces deja diez enlaces utilizables."""
    pedir_enlace(api_client, org_a, user_a.email)
    primero = token_del_correo()

    pedir_enlace(api_client, org_a, user_a.email)

    respuesta = api_client.post(
        reverse("accounts:password-reset-verify"),
        {"organization": org_a.slug, "token": primero},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "enlace_vencido"


# --------------------------------------------------------------------------
#  Punto (h) — un mensaje distinto por cada motivo
# --------------------------------------------------------------------------
def test_un_enlace_valido_se_puede_comprobar(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)

    respuesta = api_client.post(
        reverse("accounts:password-reset-verify"),
        {"organization": org_a.slug, "token": token_del_correo()},
        format="json",
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["valid"] is True
    # El correo se ve enmascarado: alcanza para reconocer la cuenta propia y
    # no para aprenderse una ajena.
    assert cuerpo["email"] == "a**@kolping.test"


def test_un_enlace_inventado_es_invalido(api_client, org_a, user_a):
    respuesta = api_client.post(
        reverse("accounts:password-reset-verify"),
        {"organization": org_a.slug, "token": "esto-no-es-un-token"},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "enlace_invalido"


def test_un_enlace_vencido_lo_dice(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)
    token = token_del_correo()

    with tenant_context(org_a.id):
        PasswordResetToken.objects.update(
            expires_at=timezone.now() - timedelta(minutes=1),
        )

    respuesta = api_client.post(
        reverse("accounts:password-reset-verify"),
        {"organization": org_a.slug, "token": token},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "enlace_vencido"


# --------------------------------------------------------------------------
#  Puntos (e) y (g) — la contraseña nueva y el consumo del enlace
# --------------------------------------------------------------------------
def confirmar(api_client, org_a, token, password=CLAVE_NUEVA):
    return api_client.post(
        reverse("accounts:password-reset-confirm"),
        {"organization": org_a.slug, "token": token,
         "password": password, "password_confirmation": password},
        format="json",
    )


def test_la_contrasena_se_reemplaza_y_sirve_para_entrar(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)
    respuesta = confirmar(api_client, org_a, token_del_correo())

    assert respuesta.status_code == 200

    entrada = api_client.post(
        reverse("accounts:login"),
        {"organization": org_a.slug, "email": user_a.email,
         "password": CLAVE_NUEVA},
        format="json",
    )
    assert entrada.status_code == 200


def test_la_contrasena_vieja_deja_de_servir(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)
    confirmar(api_client, org_a, token_del_correo())

    entrada = api_client.post(
        reverse("accounts:login"),
        {"organization": org_a.slug, "email": user_a.email, "password": CLAVE},
        format="json",
    )
    assert entrada.status_code == 401


def test_el_enlace_se_consume_al_primer_uso(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)
    token = token_del_correo()

    assert confirmar(api_client, org_a, token).status_code == 200
    segundo = confirmar(api_client, org_a, token)

    assert segundo.status_code == 400
    assert segundo.json()["code"] == "enlace_usado"


def test_una_contrasena_debil_se_rechaza(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)

    respuesta = confirmar(api_client, org_a, token_del_correo(), password="12345678")

    assert respuesta.status_code == 400
    assert "password" in respuesta.json()


def test_la_repeticion_tiene_que_coincidir(api_client, org_a, user_a):
    pedir_enlace(api_client, org_a, user_a.email)

    respuesta = api_client.post(
        reverse("accounts:password-reset-confirm"),
        {"organization": org_a.slug, "token": token_del_correo(),
         "password": CLAVE_NUEVA, "password_confirmation": "otra-cosa-2026"},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "password_confirmation" in respuesta.json()


def test_recuperar_el_acceso_desbloquea_la_cuenta(api_client, org_a, user_a):
    """RNF-07. Quien llegó acá por olvidarse la contraseña ya se bloqueó
    intentándola, y dejarlo bloqueado con la contraseña nueva no tendría
    sentido."""
    with tenant_context(org_a.id):
        User.objects.filter(id=user_a.id).update(
            failed_login_attempts=5,
            locked_until=timezone.now() + timedelta(minutes=15),
        )

    pedir_enlace(api_client, org_a, user_a.email)
    confirmar(api_client, org_a, token_del_correo())

    with tenant_context(org_a.id):
        user_a.refresh_from_db()

    assert user_a.failed_login_attempts == 0
    assert user_a.locked_until is None


# --------------------------------------------------------------------------
#  Punto (f) — se cierran todas las sesiones abiertas
# --------------------------------------------------------------------------
def test_cambiar_la_contrasena_invalida_las_sesiones_abiertas(
    api_client, org_a, user_a,
):
    """La lista negra que construyó US-02, aplicada a todos los tokens."""
    with tenant_context(org_a.id):
        sesion_vieja = tokens_for_user(user_a)

    pedir_enlace(api_client, org_a, user_a.email)
    confirmar(api_client, org_a, token_del_correo())

    renovacion = api_client.post(
        reverse("accounts:token-refresh"),
        {"refresh": sesion_vieja["refresh"]},
        format="json",
    )

    assert renovacion.status_code == 401
    assert renovacion.json()["code"] == "refresh_invalido"


def test_la_bitacora_registra_cuantas_sesiones_se_cerraron(
    api_client, org_a, user_a,
):
    with tenant_context(org_a.id):
        tokens_for_user(user_a)
        tokens_for_user(user_a)

    pedir_enlace(api_client, org_a, user_a.email)
    confirmar(api_client, org_a, token_del_correo())

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action="password.reset.complete")

    assert asiento.detail["sesiones_invalidadas"] == 2


# --------------------------------------------------------------------------
#  Aislamiento (RNF-08) — criterio 4 de la Definition of Done
# --------------------------------------------------------------------------
@pytest.mark.isolation
def test_un_enlace_de_a_no_sirve_en_b(api_client, org_a, org_b, user_a, user_b):
    pedir_enlace(api_client, org_a, user_a.email)
    token_de_a = token_del_correo()

    respuesta = api_client.post(
        reverse("accounts:password-reset-verify"),
        {"organization": org_b.slug, "token": token_de_a},
        format="json",
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "enlace_invalido"


@pytest.mark.isolation
def test_el_mismo_correo_en_dos_organizaciones_no_se_cruza(
    api_client, org_a, org_b, user_a,
):
    """El correo es único por inquilino, no global: por eso hace falta el
    slug, y por eso el enlace tiene que ser el de la cuenta correcta."""
    with tenant_context(org_b.id):
        homonimo = User.objects.create_user(
            email=user_a.email, password=CLAVE, organization=org_b,
            first_name="Ana", last_name="Otra", document_number="7001",
        )

    pedir_enlace(api_client, org_b, homonimo.email)

    with tenant_context(org_b.id):
        assert PasswordResetToken.objects.get().user_id == homonimo.id
    with tenant_context(org_a.id):
        assert not PasswordResetToken.objects.exists()


@pytest.mark.isolation
def test_el_token_no_puede_apuntar_al_usuario_de_otra_organizacion(
    org_a, org_b, user_b,
):
    """La clave foránea compuesta `fk_password_reset_user_same_org`."""
    from django.db import IntegrityError, transaction as tx

    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with tx.atomic():
                PasswordResetToken.objects.create(
                    organization=org_a,
                    user=user_b,
                    token_hash="0" * 64,
                    expires_at=timezone.now() + timedelta(minutes=30),
                )
