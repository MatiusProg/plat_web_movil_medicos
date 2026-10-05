"""US-18 — Pago en línea con Stripe.

Lo que se prueba es lo que el reparto declara no negociable:

- La ficha la confirma el webhook **firmado**, no la pantalla del paciente:
  abrir el checkout no confirma nada, y un evento sin firma válida tampoco.
- El webhook llega sin usuario y fija el contexto de inquilino con la
  organización de la metadata firmada.
- El importe lo decide el backend.
- Pagar dos veces, o pagar una ficha que ya no espera el pago, devuelve el
  dinero en el acto. Y la cancelación a tiempo (US-20) también.
"""

import hashlib
import hmac
import json
import time
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from appointments.models import Appointment
from catalog.models import Service
from payments.models import Payment
from tenancy.context import platform_admin_context, tenant_context
from tenancy.plans import current_plan

from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    ficha_pendiente,
    otro_paciente_a,
    paciente_a,
    recargar,
)

pytestmark = pytest.mark.django_db

WEBHOOK_SECRET = "whsec_prueba_local"


def checkout(api_client, user, ficha):
    return autenticar(api_client, user).post(
        reverse("payments:checkout", args=[ficha.id]),
    )


def pagar_simulado(client, url):
    return client.post(url, {"accion": "pagar"})


def firmar(payload: bytes, secret=WEBHOOK_SECRET, timestamp=None):
    """La cabecera `Stripe-Signature`, armada como la arma Stripe."""
    timestamp = timestamp or int(time.time())
    firma = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + payload, hashlib.sha256,
    ).hexdigest()
    return f"t={timestamp},v1={firma}"


def evento_pagado(payment, tipo="checkout.session.completed"):
    return json.dumps({
        "id": "evt_prueba", "object": "event", "type": tipo,
        "data": {"object": {
            "id": payment.provider_session_id, "object": "checkout.session",
            "payment_status": "paid", "payment_intent": "pi_prueba",
            "metadata": {
                "payment_id": str(payment.id),
                "organization_id": str(payment.organization_id),
                "appointment_id": str(payment.appointment_id),
            },
        }},
    }).encode()


def pago_stripe(org, ficha, user):
    with tenant_context(org.id):
        return Payment.objects.create(
            organization=org, appointment=ficha, created_by=user,
            amount=Decimal("100.00"), currency="BOB",
            provider=Payment.Provider.STRIPE, provider_session_id="cs_test_1",
        )


# ---------- Abrir el checkout ---------------------------------------------

def test_abrir_el_checkout_no_confirma_la_ficha(
    api_client, paciente_a, org_a, ficha_pendiente,
):
    respuesta = checkout(api_client, paciente_a, ficha_pendiente)

    assert respuesta.status_code == 201, respuesta.json()
    datos = respuesta.json()
    assert datos["provider"] == "simulated"
    assert datos["checkout_url"].startswith("http")
    assert datos["amount"] == "100.00" and datos["currency"] == "BOB"
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


def test_el_importe_sale_del_servicio_de_consulta_de_la_especialidad(
    api_client, paciente_a, org_a, specialty_a, ficha_pendiente,
):
    with tenant_context(org_a.id):
        Service.objects.create(
            organization=org_a, name="Consulta general",
            kind=Service.Kind.CONSULTATION, specialty=specialty_a,
            price=Decimal("150.00"),
        )
    respuesta = checkout(api_client, paciente_a, ficha_pendiente)
    assert respuesta.json()["amount"] == "150.00"


def test_no_se_paga_la_ficha_de_otro_paciente(
    api_client, otro_paciente_a, ficha_pendiente,
):
    respuesta = checkout(api_client, otro_paciente_a, ficha_pendiente)
    assert respuesta.status_code == 403


def test_no_se_paga_una_ficha_de_otra_organizacion(
    api_client, paciente_a, org_b, ficha_pendiente,
):
    """RLS: el paciente de A ni siquiera ve una ficha de B. Acá, a la inversa:
    la ficha es de A y quien paga es de B → no existe para él."""
    from accounts.models import User

    from .conftest import PERMISOS_PACIENTE, dar_rol

    with tenant_context(org_b.id):
        ajeno = User.objects.create_user(
            email="ajeno@b.test", password="clave-de-prueba-1", organization=org_b,
            first_name="Ajeno", last_name="B", document_number="B-18",
        )
    dar_rol(ajeno, org_b, "patient", "Paciente", PERMISOS_PACIENTE)
    respuesta = checkout(api_client, ajeno, ficha_pendiente)
    assert respuesta.status_code == 404


def test_una_ficha_confirmada_no_se_vuelve_a_cobrar(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    ficha = crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                        agenda_a, status=Appointment.Status.CONFIRMED)
    respuesta = checkout(api_client, paciente_a, ficha)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ficha_no_pendiente"


def test_una_reserva_vencida_no_se_cobra(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    ficha = crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                        agenda_a, expires_at=timezone.now() - timezone.timedelta(minutes=1))
    respuesta = checkout(api_client, paciente_a, ficha)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ficha_vencida"


def test_el_plan_sin_pago_en_linea_no_abre_el_checkout(
    api_client, paciente_a, org_a, ficha_pendiente,
):
    plan = current_plan(org_a)
    with platform_admin_context():
        plan.features = {**plan.features, "online_payment": False}
        plan.save(update_fields=["features"])
    respuesta = checkout(api_client, paciente_a, ficha_pendiente)
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "plan_limit"


@override_settings(STRIPE_SECRET_KEY="sk_test_prueba")
def test_con_clave_de_stripe_crea_la_sesion_con_la_metadata_y_el_importe(
    api_client, paciente_a, org_a, ficha_pendiente, monkeypatch,
):
    import stripe

    llamada = {}

    def crear(**kwargs):
        llamada.update(kwargs)
        return SimpleNamespace(id="cs_test_abc", url="https://checkout.stripe.com/c/pay/cs_test_abc")

    monkeypatch.setattr(stripe.checkout.Session, "create", crear)
    respuesta = checkout(api_client, paciente_a, ficha_pendiente)

    assert respuesta.status_code == 201, respuesta.json()
    assert respuesta.json()["provider"] == "stripe"
    assert respuesta.json()["checkout_url"].startswith("https://checkout.stripe.com")
    assert llamada["line_items"][0]["price_data"]["unit_amount"] == 10000
    assert llamada["line_items"][0]["price_data"]["currency"] == "bob"
    assert llamada["metadata"]["organization_id"] == str(org_a.id)
    assert llamada["metadata"]["appointment_id"] == str(ficha_pendiente.id)
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


# ---------- El webhook ------------------------------------------------------

@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
def test_el_webhook_firmado_confirma_la_ficha(
    client, paciente_a, org_a, ficha_pendiente, django_capture_on_commit_callbacks,
):
    pago = pago_stripe(org_a, ficha_pendiente, paciente_a)
    cuerpo = evento_pagado(pago)
    with django_capture_on_commit_callbacks(execute=True):
        respuesta = client.post(
            reverse("payments:stripe-webhook"), cuerpo,
            content_type="application/json", HTTP_STRIPE_SIGNATURE=firmar(cuerpo),
        )

    assert respuesta.status_code == 200
    ficha = recargar(org_a, ficha_pendiente)
    assert ficha.status == "confirmed"
    assert ficha.expires_at is None
    pago = recargar(org_a, pago)
    assert pago.status == "succeeded" and pago.provider_payment_id == "pi_prueba"
    # US-21: el aviso por correo, con el comprobante.
    assert len(mail.outbox) == 1
    assert "MC1." in mail.outbox[0].body


@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
def test_un_webhook_sin_firma_valida_no_confirma_nada(
    client, paciente_a, org_a, ficha_pendiente,
):
    """Si esto pasara, cualquiera podría reservar gratis con un POST."""
    pago = pago_stripe(org_a, ficha_pendiente, paciente_a)
    cuerpo = evento_pagado(pago)
    for firma in ["", firmar(cuerpo, secret="whsec_otro"), "t=1,v1=deadbeef"]:
        respuesta = client.post(
            reverse("payments:stripe-webhook"), cuerpo,
            content_type="application/json", HTTP_STRIPE_SIGNATURE=firma,
        )
        assert respuesta.status_code == 400
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


@override_settings(STRIPE_WEBHOOK_SECRET="")
def test_sin_secreto_de_webhook_no_se_acepta_ningun_evento(
    client, paciente_a, org_a, ficha_pendiente,
):
    pago = pago_stripe(org_a, ficha_pendiente, paciente_a)
    cuerpo = evento_pagado(pago)
    respuesta = client.post(
        reverse("payments:stripe-webhook"), cuerpo,
        content_type="application/json", HTTP_STRIPE_SIGNATURE=firmar(cuerpo, secret=""),
    )
    assert respuesta.status_code == 400
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
def test_el_webhook_repetido_no_hace_nada_la_segunda_vez(
    client, paciente_a, org_a, ficha_pendiente,
):
    pago = pago_stripe(org_a, ficha_pendiente, paciente_a)
    cuerpo = evento_pagado(pago)
    for _ in range(2):
        respuesta = client.post(
            reverse("payments:stripe-webhook"), cuerpo,
            content_type="application/json", HTTP_STRIPE_SIGNATURE=firmar(cuerpo),
        )
        assert respuesta.status_code == 200
    with tenant_context(org_a.id):
        assert Payment.objects.filter(status="succeeded").count() == 1


@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
def test_la_metadata_de_otra_organizacion_no_encuentra_el_pago(
    client, paciente_a, org_a, org_b, ficha_pendiente,
):
    """Aun con firma válida, el contexto se fija con la organización del
    evento: si no coincide con la del pago, RLS no lo deja ver."""
    pago = pago_stripe(org_a, ficha_pendiente, paciente_a)
    evento = json.loads(evento_pagado(pago))
    evento["data"]["object"]["metadata"]["organization_id"] = str(org_b.id)
    cuerpo = json.dumps(evento).encode()
    client.post(
        reverse("payments:stripe-webhook"), cuerpo,
        content_type="application/json", HTTP_STRIPE_SIGNATURE=firmar(cuerpo),
    )
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


@override_settings(STRIPE_WEBHOOK_SECRET=WEBHOOK_SECRET)
def test_el_pago_de_una_ficha_cancelada_se_devuelve(
    client, paciente_a, org_a, ficha_pendiente, monkeypatch,
):
    import stripe

    devoluciones = []
    monkeypatch.setattr(stripe.Refund, "create", lambda **kw: devoluciones.append(kw))
    with override_settings(STRIPE_SECRET_KEY="sk_test_prueba"):
        pago = pago_stripe(org_a, ficha_pendiente, paciente_a)
        with tenant_context(org_a.id):
            Appointment.objects.filter(pk=ficha_pendiente.pk).update(status="cancelled")
        cuerpo = evento_pagado(pago)
        client.post(
            reverse("payments:stripe-webhook"), cuerpo,
            content_type="application/json", HTTP_STRIPE_SIGNATURE=firmar(cuerpo),
        )

    pago = recargar(org_a, pago)
    assert pago.status == "refunded"
    assert pago.refund_reason == "ficha_no_disponible"
    assert devoluciones[0]["payment_intent"] == "pi_prueba"
    assert recargar(org_a, ficha_pendiente).status == "cancelled"


# ---------- El proveedor simulado -------------------------------------------

def test_el_pago_simulado_confirma_por_el_mismo_camino(
    api_client, client, paciente_a, org_a, ficha_pendiente,
    django_capture_on_commit_callbacks,
):
    url = checkout(api_client, paciente_a, ficha_pendiente).json()["checkout_url"]

    pagina = client.get(url)
    assert pagina.status_code == 200
    assert "simulada" in pagina.content.decode()

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = pagar_simulado(client, url)
    assert respuesta.status_code == 302
    assert recargar(org_a, ficha_pendiente).status == "confirmed"
    assert len(mail.outbox) == 1

    # El mismo enlace no cobra dos veces.
    pagar_simulado(client, url)
    with tenant_context(org_a.id):
        assert Payment.objects.filter(status="succeeded").count() == 1


def test_el_enlace_simulado_adulterado_no_sirve(client):
    respuesta = client.get(reverse("payments:simulated-checkout", args=["no-es-un-token"]))
    assert respuesta.status_code == 400


def test_con_stripe_activo_el_enlace_simulado_deja_de_cobrar(
    api_client, client, paciente_a, org_a, ficha_pendiente,
):
    url = checkout(api_client, paciente_a, ficha_pendiente).json()["checkout_url"]
    with override_settings(STRIPE_SECRET_KEY="sk_test_prueba"):
        respuesta = pagar_simulado(client, url)
    assert respuesta.status_code == 410
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


# ---------- La política de devolución (US-20 → US-18) -----------------------

def test_cancelar_a_tiempo_una_ficha_pagada_devuelve_el_pago(
    api_client, client, paciente_a, org_a, ficha_pendiente,
):
    url = checkout(api_client, paciente_a, ficha_pendiente).json()["checkout_url"]
    pagar_simulado(client, url)

    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha_pendiente.id]),
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["refund_eligible"] is True
    with tenant_context(org_a.id):
        pago = Payment.objects.get(appointment=ficha_pendiente, status="refunded")
    assert pago.refund_reason == "cancelacion_a_tiempo"
    detalle = autenticar(api_client, paciente_a).get(
        reverse("appointments:appointment-detail", args=[ficha_pendiente.id]),
    )
    assert detalle.json()["payment_status"] == "refunded"


def test_cancelar_sin_anticipacion_no_devuelve(
    api_client, client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    ficha = crear_ficha(org_a, paciente_a, practitioner_a, branches_a["centro"],
                        agenda_a, starts_at=timezone.now() + timezone.timedelta(hours=2))
    url = checkout(api_client, paciente_a, ficha).json()["checkout_url"]
    pagar_simulado(client, url)

    autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha.id]),
    )
    with tenant_context(org_a.id):
        assert Payment.objects.get(appointment=ficha).status == "succeeded"


# ---------- La vuelta a la app o a la web ------------------------------------

def test_despues_de_pagar_la_pagina_abre_la_app_en_la_ficha(
    api_client, client, paciente_a, ficha_pendiente,
):
    url = checkout(api_client, paciente_a, ficha_pendiente).json()["checkout_url"]
    respuesta = pagar_simulado(client, url)
    assert f"ficha={ficha_pendiente.id}" in respuesta["Location"]
    assert "origen=app" in respuesta["Location"]

    pagina = client.get(respuesta["Location"]).content.decode()
    assert f"centromedico://app/appointments/{ficha_pendiente.id}" in pagina
    assert "Volver a la aplicación" in pagina


@override_settings(FRONTEND_BASE_URL="https://web.ejemplo.test")
def test_si_el_pago_se_pidio_desde_la_web_vuelve_a_mis_fichas(
    api_client, client, paciente_a, ficha_pendiente,
):
    url = autenticar(api_client, paciente_a).post(
        reverse("payments:checkout", args=[ficha_pendiente.id]),
        {"return_to": "web"}, format="json",
    ).json()["checkout_url"]
    respuesta = client.get(pagar_simulado(client, url)["Location"])
    assert respuesta.status_code == 302
    assert respuesta["Location"] == (
        f"https://web.ejemplo.test/mis-fichas?ficha={ficha_pendiente.id}&pago=pagado"
    )


def test_la_pagina_de_regreso_no_redirige_a_donde_diga_la_url(client):
    """Ni la ficha ni el origen se usan como dirección: un valor ajeno cae en
    la página genérica, sin enlace a ningún lado."""
    respuesta = client.get(reverse("payments:return"), {
        "resultado": "pagado", "origen": "https://sitio-falso.test",
        "ficha": "javascript:alert(1)",
    })
    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "sitio-falso" not in contenido and "javascript:" not in contenido
    assert "centromedico://" not in contenido


@override_settings(STRIPE_SECRET_KEY="sk_test_prueba")
def test_stripe_recibe_la_url_de_regreso_con_la_ficha_y_el_origen(
    api_client, paciente_a, ficha_pendiente, monkeypatch,
):
    import stripe

    llamada = {}
    monkeypatch.setattr(stripe.checkout.Session, "create", lambda **kw: (
        llamada.update(kw) or SimpleNamespace(id="cs_test_x", url="https://checkout.stripe.com/x")))
    autenticar(api_client, paciente_a).post(
        reverse("payments:checkout", args=[ficha_pendiente.id]),
        {"return_to": "cualquier-cosa"}, format="json",
    )
    assert f"ficha={ficha_pendiente.id}" in llamada["success_url"]
    # Un origen desconocido cae en la app, no se pasa tal cual.
    assert "origen=app" in llamada["success_url"]
    assert llamada["success_url"].endswith("resultado=pagado")
    assert llamada["cancel_url"].endswith("resultado=cancelado")


def test_reprogramar_una_ficha_pagada_muda_el_pago_y_cancelarla_lo_devuelve(
    api_client, client, paciente_a, org_a, branches_a, agenda_a, ficha_pendiente,
):
    """Defecto encontrado probando en un teléfono: el pago se quedaba en la
    ficha vieja, y cancelar la reprogramada decía "corresponde devolución"
    sin devolver nada."""
    import datetime as dt
    from zoneinfo import ZoneInfo

    pagar_simulado(client, checkout(api_client, paciente_a, ficha_pendiente).json()["checkout_url"])

    proxima = dt.date.today() + dt.timedelta(days=7)
    nuevo_turno = dt.datetime.combine(proxima, dt.time(10, 0), tzinfo=ZoneInfo("America/La_Paz"))
    api = autenticar(api_client, paciente_a)
    nueva = api.post(
        reverse("appointments:appointment-reschedule", args=[ficha_pendiente.id]),
        {"branch": str(branches_a["centro"].id), "schedule": str(agenda_a.id),
         "starts_at": nuevo_turno.isoformat()},
        format="json",
    )
    assert nueva.status_code == 200, nueva.json()
    assert nueva.json()["status"] == "confirmed"
    assert nueva.json()["payment_status"] == "succeeded"

    cancelada = api.post(
        reverse("appointments:appointment-cancel", args=[nueva.json()["id"]]),
    )
    assert cancelada.json()["refund_eligible"] is True
    assert cancelada.json()["payment_status"] == "refunded"
    with tenant_context(org_a.id):
        assert Payment.objects.get().refund_reason == "cancelacion_a_tiempo"
