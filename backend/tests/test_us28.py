"""US-28 — Notificaciones push y correo.

Lo que se prueba es lo que la historia tiene que cumplir:

- La app registra el token de su teléfono al iniciar sesión y lo borra al
  cerrarla. Un token por teléfono, no por persona.
- Pagar la ficha avisa por push y por correo; cancelarla, también, diciendo
  si se devolvió el pago.
- La ficha de mañana recibe **un solo** recordatorio, aunque el proceso corra
  dos veces.
- Cada organización avisa sólo sus fichas y sólo a sus teléfonos.
- Sin credencial de Firebase, o con FCM caído, nada se rompe y el correo sale.

FCM nunca se llama de verdad: un FCM falso reemplaza la sesión autenticada,
y las pruebas de la credencial interceptan la llamada HTTP, igual que
`test_correo_brevo.py` hace con Brevo.
"""

import datetime as dt
import json
from decimal import Decimal

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from appointments import reminders
from appointments.attendance import attendance_link
from appointments.models import Appointment
from catalog.models import Practitioner, PractitionerBranch
from notifications import push
from notifications.models import DeviceToken
from patients.models import Patient
from payments.models import Payment
from payments.services import confirm_payment
from scheduling.models import Schedule
from tenancy.context import no_tenant_context, tenant_context

from .conftest import PERMISOS_PACIENTE, dar_rol
from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    ficha_pendiente,
    otro_paciente_a,
    paciente_a,
    perfil_paciente,
    recargar,
)

pytestmark = pytest.mark.django_db

DEVICES = "notifications:devices"


# ==========================================================================
#  El FCM falso
# ==========================================================================
class RespuestaHTTP:
    def __init__(self, status_code=200, cuerpo=None):
        self.status_code = status_code
        self._cuerpo = cuerpo if cuerpo is not None else {
            "name": "projects/proyecto-prueba/messages/1",
        }
        self.text = json.dumps(self._cuerpo)
        self.content = self.text.encode()
        self.headers = {"content-type": "application/json"}

    def json(self):
        return self._cuerpo


TOKEN_DESINSTALADO = RespuestaHTTP(404, {"error": {
    "code": 404, "status": "NOT_FOUND",
    "message": "Requested entity was not found.",
    "details": [{"@type": "type.googleapis.com/google.firebase.fcm.v1.FcmError",
                 "errorCode": "UNREGISTERED"}],
}})


class FCMFalso:
    def __init__(self):
        self.enviados = []
        self.desinstalados = set()
        self.caido = False

    def post(self, url, json=None, timeout=None):
        if self.caido:
            raise ConnectionError("FCM no contesta")
        self.enviados.append({"url": url, **json["message"]})
        if json["message"]["token"] in self.desinstalados:
            return TOKEN_DESINSTALADO
        return RespuestaHTTP()

    def a(self, token):
        return [m for m in self.enviados if m["token"] == token]


@pytest.fixture(autouse=True)
def sin_sesion_guardada():
    """La sesión de FCM se guarda por proceso: cada prueba empieza de cero."""
    push._session = None
    yield
    push._session = None


@pytest.fixture
def fcm(monkeypatch):
    falso = FCMFalso()
    monkeypatch.setattr(push, "_authorized_session",
                        lambda: ("proyecto-prueba", falso))
    return falso


# ==========================================================================
#  Ayudantes
# ==========================================================================
def telefono(user, org, token="token-del-telefono"):
    with tenant_context(org.id):
        return DeviceToken.objects.create(organization=org, user=user, token=token)


def tokens(org):
    with tenant_context(org.id):
        return list(DeviceToken.objects.values_list("token", "user_id"))


def pagar(org, ficha, user):
    with tenant_context(org.id):
        pago = Payment.objects.create(
            organization=org, appointment=ficha, created_by=user,
            amount=Decimal("100.00"), currency="BOB",
            provider=Payment.Provider.SIMULATED,
        )
        return confirm_payment(pago)


def ficha_confirmada(org, paciente, practitioner, branch, agenda, *,
                     en_horas, reservada_hace_horas=72, **extra):
    """Una ficha pagada que empieza en `en_horas`, reservada hace tanto."""
    ficha = crear_ficha(
        org, paciente, practitioner, branch, agenda,
        starts_at=timezone.now() + dt.timedelta(hours=en_horas),
        status=extra.pop("status", Appointment.Status.CONFIRMED),
        expires_at=None, **extra,
    )
    with tenant_context(org.id):
        Appointment.objects.filter(pk=ficha.pk).update(
            created_at=timezone.now() - dt.timedelta(hours=reservada_hace_horas),
        )
    return ficha


@pytest.fixture
def manana(paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    return ficha_confirmada(org_a, paciente_a, practitioner_a,
                            branches_a["centro"], agenda_a, en_horas=20)


@pytest.fixture
def paciente_b(org_b, user_b):
    dar_rol(user_b, org_b, "patient", "Paciente", PERMISOS_PACIENTE)
    perfil_paciente(user_b, org_b)
    return user_b


@pytest.fixture
def ficha_b(paciente_b, org_b, branch_b):
    with tenant_context(org_b.id):
        profesional = Practitioner.objects.create(
            organization=org_b, first_name="Pedro", last_name="Vaca",
            license_number="MP-2000",
        )
        PractitionerBranch.objects.create(
            organization=org_b, practitioner=profesional, branch=branch_b,
        )
        agenda = Schedule.objects.create(
            organization=org_b, practitioner=profesional, branch=branch_b,
            weekday=dt.date.today().weekday(), start_time="09:00",
            end_time="11:00", slot_minutes=60,
            valid_from=dt.date.today() - dt.timedelta(days=7),
        )
    return ficha_confirmada(org_b, paciente_b, profesional, branch_b, agenda,
                            en_horas=20)


# ==========================================================================
#  El token del teléfono
# ==========================================================================
def test_la_app_registra_el_token_de_su_telefono(api_client, paciente_a, org_a):
    respuesta = autenticar(api_client, paciente_a).post(
        reverse(DEVICES), {"token": "token-1", "platform": "android"}, format="json",
    )
    assert respuesta.status_code == 201, respuesta.json()
    assert tokens(org_a) == [("token-1", paciente_a.id)]


def test_registrar_dos_veces_el_mismo_telefono_no_lo_duplica(
    api_client, paciente_a, org_a,
):
    api = autenticar(api_client, paciente_a)
    api.post(reverse(DEVICES), {"token": "token-1"}, format="json")
    segunda = api.post(reverse(DEVICES), {"token": "token-1"}, format="json")
    assert segunda.status_code == 200
    assert len(tokens(org_a)) == 1


def test_dos_telefonos_de_la_misma_persona_son_dos_tokens(
    api_client, paciente_a, org_a,
):
    api = autenticar(api_client, paciente_a)
    api.post(reverse(DEVICES), {"token": "celular"}, format="json")
    api.post(reverse(DEVICES), {"token": "tablet"}, format="json")
    assert sorted(t for t, _ in tokens(org_a)) == ["celular", "tablet"]


def test_si_el_telefono_pasa_a_otra_cuenta_el_token_se_mueve(
    api_client, paciente_a, otro_paciente_a, org_a,
):
    telefono(paciente_a, org_a, "compartido")
    autenticar(api_client, otro_paciente_a).post(
        reverse(DEVICES), {"token": "compartido"}, format="json",
    )
    assert tokens(org_a) == [("compartido", otro_paciente_a.id)]


def test_cerrar_sesion_borra_el_token(api_client, paciente_a, org_a):
    telefono(paciente_a, org_a, "token-1")
    respuesta = autenticar(api_client, paciente_a).delete(
        reverse(DEVICES), {"token": "token-1"}, format="json",
    )
    assert respuesta.status_code == 204
    assert tokens(org_a) == []


def test_no_se_borra_el_token_de_otra_persona(
    api_client, paciente_a, otro_paciente_a, org_a,
):
    telefono(paciente_a, org_a, "token-de-ana")
    autenticar(api_client, otro_paciente_a).delete(
        reverse(DEVICES), {"token": "token-de-ana"}, format="json",
    )
    assert tokens(org_a) == [("token-de-ana", paciente_a.id)]


def test_sin_sesion_no_se_registra_nada(api_client):
    respuesta = api_client.post(reverse(DEVICES), {"token": "x"}, format="json")
    assert respuesta.status_code == 401


def test_el_superadministrador_no_registra_telefonos(api_client, platform_admin):
    respuesta = autenticar(api_client, platform_admin).post(
        reverse(DEVICES), {"token": "x"}, format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "sin_organizacion"


@pytest.mark.isolation
def test_los_tokens_de_una_organizacion_no_se_ven_desde_otra(
    api_client, paciente_a, paciente_b, org_a, org_b,
):
    """El mismo teléfono puede estar registrado en dos organizaciones: cada
    una ve sólo su fila, y sin contexto no se ve ninguna."""
    telefono(paciente_a, org_a, "mismo-telefono")
    respuesta = autenticar(api_client, paciente_b).post(
        reverse(DEVICES), {"token": "mismo-telefono"}, format="json",
    )
    assert respuesta.status_code == 201
    assert tokens(org_a) == [("mismo-telefono", paciente_a.id)]
    assert tokens(org_b) == [("mismo-telefono", paciente_b.id)]
    with no_tenant_context():
        assert DeviceToken.objects.count() == 0


# ==========================================================================
#  Confirmación y cancelación
# ==========================================================================
def test_pagar_la_ficha_avisa_por_push_y_por_correo(
    fcm, paciente_a, org_a, ficha_pendiente, django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a)
    with django_capture_on_commit_callbacks(execute=True):
        pagar(org_a, ficha_pendiente, paciente_a)

    [aviso] = fcm.enviados
    assert aviso["url"].endswith("/projects/proyecto-prueba/messages:send")
    assert aviso["notification"]["title"] == "Tu ficha quedó confirmada"
    assert "Laura Gómez" in aviso["notification"]["body"]
    # Lo que la app usa para abrir esa ficha al tocar el aviso.
    assert aviso["data"] == {"appointment_id": str(ficha_pendiente.id),
                             "event": "confirmacion"}
    assert aviso["android"]["notification"]["channel_id"] == push.ANDROID_CHANNEL
    # El correo de siempre (US-21), uno solo.
    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == "Tu ficha está confirmada"


def test_sin_confirmar_el_pago_no_sale_ningun_aviso(
    fcm, paciente_a, org_a, ficha_pendiente, django_capture_on_commit_callbacks,
):
    """El aviso sale después del COMMIT: si el pago se revierte, no hay aviso."""
    telefono(paciente_a, org_a)
    with django_capture_on_commit_callbacks(execute=False) as pendientes:
        pagar(org_a, ficha_pendiente, paciente_a)
    assert pendientes
    assert fcm.enviados == [] and mail.outbox == []


def test_el_aviso_de_un_dependiente_le_llega_al_titular(
    fcm, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
    django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a, "telefono-del-titular")
    with tenant_context(org_a.id):
        hijo = Patient.objects.create(
            organization=org_a, guardian=paciente_a.patient_profile,
            relationship="child", first_name="Tito", last_name="Ríos",
            birth_date=dt.date(2018, 3, 1),
        )
        ficha = Appointment.objects.create(
            organization=org_a, patient=hijo, booked_by=paciente_a,
            practitioner=practitioner_a, branch=branches_a["centro"],
            schedule=agenda_a, starts_at=timezone.now() + dt.timedelta(days=3),
            ends_at=timezone.now() + dt.timedelta(days=3, hours=1),
            expires_at=timezone.now() + dt.timedelta(minutes=15),
        )
    with django_capture_on_commit_callbacks(execute=True):
        pagar(org_a, ficha, paciente_a)

    assert len(fcm.a("telefono-del-titular")) == 1
    assert mail.outbox[0].to == [paciente_a.email]


def test_cancelar_a_tiempo_avisa_y_dice_que_se_devolvio_el_pago(
    fcm, api_client, paciente_a, org_a, ficha_pendiente,
    django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a)
    pagar(org_a, ficha_pendiente, paciente_a)

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = autenticar(api_client, paciente_a).post(
            reverse("appointments:appointment-cancel", args=[ficha_pendiente.id]),
        )
    assert respuesta.status_code == 200

    [aviso] = fcm.enviados
    assert aviso["notification"]["title"] == "Tu ficha fue cancelada"
    assert "Te devolvimos el pago de 100.00 BOB." in aviso["notification"]["body"]
    assert aviso["data"]["event"] == "cancelacion"
    [correo] = mail.outbox
    assert correo.subject.endswith("fue cancelada")
    assert "Te devolvimos el pago" in correo.body


def test_cancelar_tarde_avisa_que_el_pago_no_se_devuelve(
    fcm, api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
    django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a)
    ficha = crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                        agenda_a, starts_at=timezone.now() + dt.timedelta(hours=2))
    pagar(org_a, ficha, paciente_a)

    with django_capture_on_commit_callbacks(execute=True):
        autenticar(api_client, paciente_a).post(
            reverse("appointments:appointment-cancel", args=[ficha.id]),
        )

    assert "el pago no se devuelve" in fcm.enviados[0]["notification"]["body"]
    assert "menos de 24 horas" in mail.outbox[0].body


def test_una_cancelacion_rechazada_no_avisa(
    fcm, api_client, paciente_a, otro_paciente_a, org_a, ficha_pendiente,
    django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a)
    with django_capture_on_commit_callbacks(execute=True):
        respuesta = autenticar(api_client, otro_paciente_a).post(
            reverse("appointments:appointment-cancel", args=[ficha_pendiente.id]),
        )
    assert respuesta.status_code == 403
    assert fcm.enviados == [] and mail.outbox == []


# ==========================================================================
#  Lo que no se puede romper
# ==========================================================================
def test_el_token_de_una_app_desinstalada_se_borra(
    fcm, paciente_a, org_a, ficha_pendiente, django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a, "vigente")
    telefono(paciente_a, org_a, "desinstalada")
    fcm.desinstalados.add("desinstalada")

    with django_capture_on_commit_callbacks(execute=True):
        pagar(org_a, ficha_pendiente, paciente_a)

    assert len(fcm.enviados) == 2
    assert tokens(org_a) == [("vigente", paciente_a.id)]


@override_settings(FIREBASE_CREDENTIALS="")
def test_sin_credencial_de_firebase_nada_se_rompe_y_el_correo_sale(
    paciente_a, org_a, ficha_pendiente, django_capture_on_commit_callbacks,
):
    telefono(paciente_a, org_a)
    with django_capture_on_commit_callbacks(execute=True):
        pagar(org_a, ficha_pendiente, paciente_a)

    assert recargar(org_a, ficha_pendiente).status == "confirmed"
    assert len(mail.outbox) == 1
    # El token no se toca: sin credencial no se sabe si está vigente.
    assert len(tokens(org_a)) == 1


def test_con_fcm_caido_el_pago_queda_confirmado_y_el_correo_sale(
    fcm, paciente_a, org_a, ficha_pendiente, django_capture_on_commit_callbacks,
):
    fcm.caido = True
    telefono(paciente_a, org_a)
    with django_capture_on_commit_callbacks(execute=True):
        pagar(org_a, ficha_pendiente, paciente_a)

    assert recargar(org_a, ficha_pendiente).status == "confirmed"
    assert len(mail.outbox) == 1


# ==========================================================================
#  La credencial de servicio
# ==========================================================================
@pytest.fixture
def credencial():
    """Una credencial de servicio con una clave RSA de verdad, hecha en el acto."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return {
        "type": "service_account",
        "project_id": "proyecto-prueba",
        "private_key_id": "clave-1",
        "private_key": clave.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ).decode(),
        "client_email": "push@proyecto-prueba.iam.gserviceaccount.com",
        "client_id": "1",
        "token_uri": "https://oauth2.googleapis.com/token",
    }


@pytest.fixture
def red(monkeypatch):
    """Intercepta las llamadas HTTP: Google da un token de acceso y FCM acepta."""
    import requests

    llamadas = []

    def request(self, method, url, **kwargs):
        llamadas.append({"method": method, "url": url, **kwargs})
        if url == "https://oauth2.googleapis.com/token":
            return RespuestaHTTP(200, {"access_token": "ya29.prueba",
                                       "expires_in": 3600, "token_type": "Bearer"})
        return RespuestaHTTP()

    monkeypatch.setattr(requests.Session, "request", request)
    return llamadas


def mandar_de_prueba(user, org):
    with tenant_context(org.id):
        return push.send_to_user(user, push.Message("Hola", "Prueba"))


def test_con_la_credencial_el_push_sale_firmado_a_fcm(
    credencial, red, paciente_a, org_a,
):
    telefono(paciente_a, org_a)
    with override_settings(FIREBASE_CREDENTIALS=json.dumps(credencial)):
        assert mandar_de_prueba(paciente_a, org_a) == 1

    # google-auth puede hacer otras consultas propias (p. ej. `allowedLocations`):
    # importa que pidió el token a Google y que el push salió con él.
    assert any(c["url"] == "https://oauth2.googleapis.com/token" for c in red)
    [envio] = [c for c in red if c["url"].startswith("https://fcm.googleapis.com/")]
    assert envio["url"] == ("https://fcm.googleapis.com/v1/projects/"
                            "proyecto-prueba/messages:send")
    assert envio["headers"]["authorization"] == "Bearer ya29.prueba"
    assert envio["json"]["message"]["token"] == "token-del-telefono"


def test_la_credencial_puede_ser_la_ruta_a_un_archivo(
    credencial, red, paciente_a, org_a, tmp_path,
):
    archivo = tmp_path / "proyecto-firebase-adminsdk.json"
    archivo.write_text(json.dumps(credencial), encoding="utf-8")
    telefono(paciente_a, org_a)
    with override_settings(FIREBASE_CREDENTIALS=str(archivo)):
        assert mandar_de_prueba(paciente_a, org_a) == 1


def test_una_credencial_rota_no_tira_el_aviso(red, paciente_a, org_a):
    telefono(paciente_a, org_a)
    with override_settings(FIREBASE_CREDENTIALS="{esto no es json"):
        assert mandar_de_prueba(paciente_a, org_a) == 0
    assert red == []


# ==========================================================================
#  Recordatorios
# ==========================================================================
def test_la_ficha_de_manana_recibe_su_recordatorio(fcm, paciente_a, org_a, manana):
    telefono(paciente_a, org_a)

    assert reminders.run_due() == 1

    [aviso] = fcm.enviados
    assert aviso["notification"]["title"] == "Recordatorio de tu ficha"
    assert "Laura Gómez" in aviso["notification"]["body"]
    assert aviso["data"] == {"appointment_id": str(manana.id),
                             "event": "recordatorio"}
    [correo] = mail.outbox
    assert correo.subject.startswith("Recordatorio: tu ficha del")
    assert recargar(org_a, manana).reminder_sent_at is not None


def test_correr_dos_veces_no_repite_el_recordatorio(fcm, paciente_a, org_a, manana):
    telefono(paciente_a, org_a)
    assert reminders.run_due() == 1
    assert reminders.run_due() == 0
    assert len(fcm.enviados) == 1 and len(mail.outbox) == 1


def test_el_recordatorio_pide_confirmar_solo_si_no_confirmo(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    sin_confirmar = ficha_confirmada(org_a, paciente_a, practitioner_a,
                                     branches_a["centro"], agenda_a, en_horas=20)
    ficha_confirmada(org_a, paciente_a, practitioner_a, branches_a["centro"],
                     agenda_a, en_horas=21, attendance_confirmed_at=timezone.now())
    assert reminders.run_due() == 2

    with tenant_context(org_a.id):
        enlace = attendance_link(sin_confirmar)
    con_enlace = [c for c in mail.outbox if "/api/appointments/attendance/" in c.body]
    assert len(mail.outbox) == 2
    assert len(con_enlace) == 1
    assert enlace in con_enlace[0].body


def test_no_se_recuerda_lo_que_no_corresponde(
    fcm, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    telefono(paciente_a, org_a)
    centro = branches_a["centro"]
    args = (org_a, paciente_a, practitioner_a, centro, agenda_a)
    ficha_confirmada(*args, en_horas=48)                         # falta mucho
    ficha_confirmada(*args, en_horas=20,                          # sin pagar
                     status=Appointment.Status.PENDING_PAYMENT)
    ficha_confirmada(*args, en_horas=21,                          # cancelada
                     status=Appointment.Status.CANCELLED)
    ficha_confirmada(*args, en_horas=-2,                          # ya pasó
                     status=Appointment.Status.CONFIRMED)
    # Reservada hace una hora para dentro de cinco: el aviso de confirmación
    # acaba de salir, recordarla sería repetirlo.
    ficha_confirmada(*args, en_horas=5, reservada_hace_horas=1)

    assert reminders.run_due() == 0
    assert fcm.enviados == [] and mail.outbox == []


@pytest.mark.isolation
def test_cada_organizacion_recuerda_sus_fichas_a_sus_telefonos(
    fcm, paciente_a, paciente_b, org_a, org_b, manana, ficha_b,
):
    telefono(paciente_a, org_a, "telefono-a")
    telefono(paciente_b, org_b, "telefono-b")

    assert reminders.run_due() == 2

    [aviso_a] = fcm.a("telefono-a")
    [aviso_b] = fcm.a("telefono-b")
    assert aviso_a["data"]["appointment_id"] == str(manana.id)
    assert aviso_b["data"]["appointment_id"] == str(ficha_b.id)
    assert sorted(c.to[0] for c in mail.outbox) == sorted(
        [paciente_a.email, paciente_b.email],
    )


def test_si_una_organizacion_falla_las_demas_reciben_su_recordatorio(
    fcm, monkeypatch, paciente_a, paciente_b, org_a, org_b, manana, ficha_b,
):
    original = reminders.run_for

    def falla_en_a(organization, now=None):
        if organization.id == org_a.id:
            raise RuntimeError("la organización A falló")
        return original(organization, now)

    monkeypatch.setattr(reminders, "run_for", falla_en_a)
    assert reminders.run_due() == 1
    assert recargar(org_a, manana).reminder_sent_at is None
    assert recargar(org_b, ficha_b).reminder_sent_at is not None


def test_el_comando_manda_los_recordatorios(org_a, manana, capsys):
    call_command("send_appointment_reminders")
    assert "1 enviado(s)" in capsys.readouterr().out
    assert recargar(org_a, manana).reminder_sent_at is not None


@override_settings(APPOINTMENT_REMINDERS="off")
def test_con_los_recordatorios_apagados_no_sale_nada(org_a, manana, capsys):
    call_command("send_appointment_reminders")
    assert "apagados" in capsys.readouterr().out
    assert recargar(org_a, manana).reminder_sent_at is None
    assert mail.outbox == []


def test_un_usuario_sin_ficha_no_recibe_avisos_de_otro(
    fcm, paciente_a, otro_paciente_a, org_a, manana,
):
    telefono(otro_paciente_a, org_a, "telefono-de-otro")
    telefono(paciente_a, org_a, "telefono-de-ana")
    reminders.run_due()
    assert fcm.a("telefono-de-otro") == []
    assert len(fcm.a("telefono-de-ana")) == 1
