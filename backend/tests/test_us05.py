"""US-05 — Edición del propio perfil (CU6).

Los puntos de la historia, en el orden en que aparecen en
``docs/sprints/sprint-1/historias-de-usuario.md``:

    (a) el perfil sale del token, nunca de un identificador del cliente
    (b) se editan nombres, teléfono y correo, con las validaciones del alta
    (c) el cambio de contraseña acredita la actual y no cierra la sesión
    (d) documento, rol, organización y estado no son editables
    (e) el correo se rechaza si ya existe en esa organización
    (f) guardado parcial

Y la prueba de aislamiento que exige toda historia (regla 8 del Sprint 1).
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog, User
from accounts.tokens import tokens_for_user
from audit.actions import Action
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

CLAVE_ACTUAL = "clave-de-prueba-1"
CLAVE_NUEVA = "Otra-clave-segura-42"

PERFIL = reverse("accounts:profile")
CONTRASENA = reverse("accounts:profile-password")


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user, access=None):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {access or tokens_for_user(user)['access']}",
    )
    return api_client


@pytest.fixture
def paciente_a(db, org_a, user_a):
    """`user_a` con rol de paciente y su ficha demográfica titular, como la
    deja el alta de US-01."""
    dar_rol(user_a, org_a, "patient", "Paciente", [])
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, user=user_a,
            document_type=user_a.document_type,
            document_number=user_a.document_number,
            first_name=user_a.first_name, last_name=user_a.last_name,
            phone="70000000",
        )
    return user_a


def releer(user):
    with tenant_context(user.organization_id):
        return User.objects.get(pk=user.pk)


# --------------------------------------------------------------------------
#  (a) Consulta del propio perfil
# --------------------------------------------------------------------------

def test_el_perfil_es_el_de_quien_trae_el_token(api_client, paciente_a, org_a):
    respuesta = autenticar(api_client, paciente_a).get(PERFIL)

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["id"] == str(paciente_a.id)
    assert cuerpo["email"] == "ana@kolping.test"
    assert cuerpo["full_name"] == "Ana Ríos"
    assert cuerpo["organization"] == {"slug": "kolping", "name": "Kolping"}
    assert cuerpo["roles"] == [{"code": "patient", "name": "Paciente"}]
    assert cuerpo["is_active"] is True
    assert "password" not in cuerpo


def test_sin_sesion_no_hay_perfil(api_client):
    assert api_client.get(PERFIL).status_code == 401
    assert api_client.patch(PERFIL, {"phone": "1"}, format="json").status_code == 401
    assert api_client.post(CONTRASENA, {}, format="json").status_code == 401


def test_el_superadministrador_tambien_tiene_perfil(api_client, platform_admin):
    respuesta = autenticar(api_client, platform_admin).get(PERFIL)

    assert respuesta.status_code == 200
    assert respuesta.json()["organization"] is None
    assert respuesta.json()["is_platform_admin"] is True


def test_la_ruta_me_no_la_toma_el_listado_de_usuarios_de_us04(
    api_client, paciente_a,
):
    """`users/` es el router de US-04 y su detalle sólo acepta un UUID."""
    respuesta = autenticar(api_client, paciente_a).get(PERFIL)
    assert respuesta.json()["id"] == str(paciente_a.id)


# --------------------------------------------------------------------------
#  (b) y (f) Edición de datos de contacto, guardado parcial
# --------------------------------------------------------------------------

def test_editar_solo_el_telefono_no_obliga_a_mandar_lo_demas(
    api_client, paciente_a,
):
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"phone": "71234567"}, format="json",
    )

    assert respuesta.status_code == 200, respuesta.json()
    assert respuesta.json()["phone"] == "71234567"
    guardado = releer(paciente_a)
    assert guardado.phone == "71234567"
    assert guardado.first_name == "Ana"
    assert guardado.email == "ana@kolping.test"


def test_nombres_y_telefono_se_copian_a_la_ficha_de_paciente(
    api_client, paciente_a, org_a,
):
    """La ficha demográfica es la que ve recepción: no puede quedar vieja."""
    autenticar(api_client, paciente_a).patch(
        PERFIL,
        {"first_name": "  Ana María ", "last_name": "Ríos Paz", "phone": "71234567"},
        format="json",
    )

    with tenant_context(org_a.id):
        ficha = Patient.objects.get(user=paciente_a)
    assert ficha.first_name == "Ana María"
    assert ficha.last_name == "Ríos Paz"
    assert ficha.phone == "71234567"


def test_un_nombre_vacio_se_rechaza(api_client, paciente_a):
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"first_name": "   "}, format="json",
    )

    assert respuesta.status_code == 400
    assert "first_name" in respuesta.json()
    assert releer(paciente_a).first_name == "Ana"


def test_un_correo_mal_escrito_se_rechaza(api_client, paciente_a):
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"email": "ana-sin-arroba"}, format="json",
    )

    assert respuesta.status_code == 400
    assert "email" in respuesta.json()


def test_cambiar_el_correo_permite_entrar_con_el_nuevo(
    api_client, paciente_a,
):
    autenticar(api_client, paciente_a).patch(
        PERFIL, {"email": "ana.rios@kolping.test"}, format="json",
    )

    entrada = APIClient().post(
        reverse("accounts:login"),
        {"organization": "kolping", "email": "ana.rios@kolping.test",
         "password": CLAVE_ACTUAL},
        format="json",
    )
    assert entrada.status_code == 200, entrada.json()


def test_put_no_existe_porque_el_guardado_es_parcial(api_client, paciente_a):
    respuesta = autenticar(api_client, paciente_a).put(
        PERFIL, {"phone": "1"}, format="json",
    )
    assert respuesta.status_code == 405


# --------------------------------------------------------------------------
#  (d) Campos no editables
# --------------------------------------------------------------------------

@pytest.mark.parametrize("campo,valor", [
    ("document_number", "9999"),
    ("document_type", "PAS"),
    ("organization", "sanluis"),
    ("roles", [{"code": "org_admin"}]),
    ("is_active", False),
    ("is_platform_admin", True),
    ("id", "00000000-0000-0000-0000-000000000000"),
])
def test_un_campo_no_editable_se_rechaza_con_su_nombre(
    api_client, paciente_a, campo, valor,
):
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"phone": "71234567", campo: valor}, format="json",
    )

    assert respuesta.status_code == 400
    assert campo in respuesta.json()
    # Y no se guardó nada, tampoco lo que sí era editable.
    guardado = releer(paciente_a)
    assert guardado.phone == ""
    assert guardado.document_number == "5001"
    assert guardado.is_active is True


# --------------------------------------------------------------------------
#  (e) Unicidad del correo por organización
# --------------------------------------------------------------------------

def test_un_correo_que_ya_usa_otra_cuenta_del_centro_se_rechaza(
    api_client, paciente_a, org_a,
):
    with tenant_context(org_a.id):
        User.objects.create_user(
            email="carla@kolping.test", password=CLAVE_ACTUAL,
            organization=org_a, first_name="Carla", last_name="Vega",
            document_number="5003",
        )

    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"email": "CARLA@kolping.test"}, format="json",
    )

    assert respuesta.status_code == 400
    assert "email" in respuesta.json()
    assert releer(paciente_a).email == "ana@kolping.test"


def test_volver_a_mandar_el_correo_propio_no_choca_consigo_mismo(
    api_client, paciente_a,
):
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"email": "ana@kolping.test", "phone": "7"}, format="json",
    )
    assert respuesta.status_code == 200, respuesta.json()


def test_el_mismo_correo_en_otro_centro_medico_si_se_acepta(
    api_client, paciente_a, user_b,
):
    """Aislamiento: la unicidad es por inquilino, no global (decisión D-5).

    Que un correo de San Luis bloqueara a una paciente de Kolping sería,
    además, una forma de averiguar qué correos tiene registrados otro centro.
    """
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"email": user_b.email}, format="json",
    )

    assert respuesta.status_code == 200, respuesta.json()
    assert releer(paciente_a).email == user_b.email


def test_el_perfil_no_deja_ver_ni_tocar_a_otro_inquilino(
    api_client, paciente_a, user_b, org_b,
):
    """Aunque se mande el id de otro usuario, se edita el propio."""
    respuesta = autenticar(api_client, paciente_a).patch(
        PERFIL, {"id": str(user_b.id)}, format="json",
    )
    assert respuesta.status_code == 400

    with tenant_context(org_b.id):
        assert User.objects.get(pk=user_b.pk).first_name == "Beto"


# --------------------------------------------------------------------------
#  (c) Cambio de contraseña
# --------------------------------------------------------------------------

def cambiar(api_client, user, actual=CLAVE_ACTUAL, nueva=CLAVE_NUEVA,
            repetida=None, access=None):
    return autenticar(api_client, user, access).post(
        CONTRASENA,
        {"current_password": actual, "password": nueva,
         "password_confirmation": nueva if repetida is None else repetida},
        format="json",
    )


def test_cambiar_la_contrasena_con_la_actual_correcta(api_client, paciente_a):
    respuesta = cambiar(api_client, paciente_a)

    assert respuesta.status_code == 200, respuesta.json()
    guardado = releer(paciente_a)
    assert guardado.check_password(CLAVE_NUEVA)
    assert not guardado.check_password(CLAVE_ACTUAL)


def test_con_la_actual_equivocada_no_se_cambia(api_client, paciente_a):
    respuesta = cambiar(api_client, paciente_a, actual="no-es-esta")

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "contrasena_actual_incorrecta"
    assert "current_password" in respuesta.json()
    assert releer(paciente_a).check_password(CLAVE_ACTUAL)


def test_la_nueva_pasa_por_la_politica_de_passwords_py(api_client, paciente_a):
    respuesta = cambiar(api_client, paciente_a, nueva="12345678")

    assert respuesta.status_code == 400
    assert "password" in respuesta.json()
    assert releer(paciente_a).check_password(CLAVE_ACTUAL)


def test_la_nueva_no_puede_parecerse_al_correo(api_client, paciente_a):
    """La segunda pasada, la que necesita al usuario."""
    respuesta = cambiar(api_client, paciente_a, nueva="ana@kolping.test")

    assert respuesta.status_code == 400
    assert "password" in respuesta.json()


def test_la_repeticion_tiene_que_coincidir(api_client, paciente_a):
    respuesta = cambiar(api_client, paciente_a, repetida="Otra-cosa-42")

    assert respuesta.status_code == 400
    assert "password_confirmation" in respuesta.json()


def test_la_nueva_tiene_que_ser_distinta_de_la_actual(api_client, paciente_a):
    respuesta = cambiar(
        api_client, paciente_a, actual=CLAVE_ACTUAL, nueva=CLAVE_ACTUAL,
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "contrasena_repetida"


def test_la_sesion_en_curso_sigue_y_las_demas_se_cierran(
    api_client, paciente_a,
):
    """Punto (c), con el detalle de diseño de ``views/profile.py``.

    La sesión que hizo el cambio recibe un par nuevo y sigue adentro; las
    demás —otro dispositivo— no se pueden renovar más.
    """
    otro_dispositivo = tokens_for_user(paciente_a)
    este = tokens_for_user(paciente_a)

    respuesta = cambiar(api_client, paciente_a, access=este["access"])
    cuerpo = respuesta.json()
    assert respuesta.status_code == 200, cuerpo

    # El acceso con el que se hizo el cambio sigue sirviendo.
    assert autenticar(api_client, paciente_a, este["access"]).get(
        PERFIL,
    ).status_code == 200

    # El refresco nuevo se puede usar; el del otro dispositivo, no.
    refresco = reverse("accounts:token-refresh")
    assert APIClient().post(
        refresco, {"refresh": cuerpo["refresh"]}, format="json",
    ).status_code == 200
    assert APIClient().post(
        refresco, {"refresh": otro_dispositivo["refresh"]}, format="json",
    ).status_code == 401


# --------------------------------------------------------------------------
#  Bitácora de US-06
# --------------------------------------------------------------------------

def test_editar_el_perfil_deja_asiento_con_los_campos_cambiados(
    api_client, paciente_a, org_a,
):
    autenticar(api_client, paciente_a).patch(
        PERFIL, {"phone": "71234567", "email": "ana.rios@kolping.test"},
        format="json",
    )

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.PROFILE_UPDATE)
    assert asiento.user_id == paciente_a.id
    assert asiento.detail["fields"] == ["email", "phone"]
    assert asiento.detail["email"] == {
        "before": "ana@kolping.test", "after": "ana.rios@kolping.test",
    }


def test_guardar_sin_cambios_no_deja_asiento(api_client, paciente_a, org_a):
    autenticar(api_client, paciente_a).patch(
        PERFIL, {"first_name": "Ana"}, format="json",
    )

    with tenant_context(org_a.id):
        assert not AuditLog.objects.filter(action=Action.PROFILE_UPDATE).exists()


def test_el_cambio_de_contrasena_deja_asiento_sin_la_contrasena(
    api_client, paciente_a, org_a,
):
    cambiar(api_client, paciente_a, actual="no-es-esta")
    cambiar(api_client, paciente_a)

    with tenant_context(org_a.id):
        asientos = list(
            AuditLog.objects.filter(action=Action.PASSWORD_CHANGE)
            .order_by("occurred_at").values_list("detail", flat=True)
        )
    assert asientos[0] == {"succeeded": False}
    assert asientos[1]["succeeded"] is True
    assert CLAVE_NUEVA not in str(asientos)
    assert CLAVE_ACTUAL not in str(asientos)


def test_las_acciones_nuevas_aparecen_en_el_filtro_de_la_bitacora():
    """Sin etiqueta, una acción se registra igual pero no sale en el
    desplegable de la pantalla de US-06 (ver ``audit/actions.py``)."""
    from audit.actions import LABELS

    assert Action.PROFILE_UPDATE in LABELS
    assert Action.PASSWORD_CHANGE in LABELS
