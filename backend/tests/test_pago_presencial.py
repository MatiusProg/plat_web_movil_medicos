"""US-23 (lo que pone `payments`) — El cobro en efectivo en ventanilla.

Daniel arma el mostrador; esto es el medio de pago que su pantalla llama:
`POST /api/payments/appointments/{id}/cash/`. Lo que se prueba:

- Recepción cobra y la ficha queda confirmada en el acto, por el mismo
  camino que un pago en línea (`confirm_payment`): sale el correo de siempre.
- El importe lo decide el backend y el cobro queda en la bitácora a nombre
  de quien cobró.
- El paciente no puede «cobrarse» solo, y nadie cobra fichas de otra
  organización ni fichas que no esperan pago.
- No depende del pago en línea del plan.
- Cancelar a tiempo deja el pago `refunded`: recepción devuelve el efectivo.
"""

from decimal import Decimal

import pytest
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, RolePermission, User
from appointments.models import Appointment
from payments.models import Payment
from payments.providers import CashProvider, ProviderError
from tenancy.context import platform_admin_context, tenant_context
from tenancy.plans import current_plan

from .conftest import dar_rol
from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    ficha_pendiente,
    paciente_a,
    recargar,
)

pytestmark = pytest.mark.django_db

PERMISO = "payments.payment.register_cash"


def cobrar(api_client, user, ficha):
    return autenticar(api_client, user).post(
        reverse("payments:cash", args=[ficha.id]),
    )


def recepcionista(org, email, documento):
    with tenant_context(org.id):
        user = User.objects.create_user(
            email=email, password="clave-de-prueba-1", organization=org,
            first_name="Rita", last_name="Mostrador", document_number=documento,
        )
    dar_rol(user, org, "recepcion-caja", "Recepción", [PERMISO])
    return user


@pytest.fixture
def recepcion_a(org_a):
    return recepcionista(org_a, "caja@kolping.test", "CAJA-1")


@pytest.fixture
def recepcion_b(org_b):
    return recepcionista(org_b, "caja@sanluis.test", "CAJA-2")


def pagos(org, ficha):
    with tenant_context(org.id):
        return list(Payment.objects.filter(appointment=ficha).order_by("created_at"))


# ==========================================================================
#  El cobro
# ==========================================================================
def test_recepcion_cobra_en_efectivo_y_la_ficha_queda_confirmada(
    api_client, recepcion_a, org_a, ficha_pendiente,
    django_capture_on_commit_callbacks,
):
    with django_capture_on_commit_callbacks(execute=True):
        respuesta = cobrar(api_client, recepcion_a, ficha_pendiente)

    assert respuesta.status_code == 201, respuesta.json()
    cuerpo = respuesta.json()
    assert cuerpo["provider"] == "cash"
    assert cuerpo["status"] == "succeeded"
    assert cuerpo["appointment"]["status"] == "confirmed"
    assert cuerpo["appointment"]["payment_status"] == "succeeded"

    ficha = recargar(org_a, ficha_pendiente)
    assert ficha.status == Appointment.Status.CONFIRMED
    assert ficha.expires_at is None
    [pago] = pagos(org_a, ficha)
    assert pago.provider == Payment.Provider.CASH
    assert pago.created_by_id == recepcion_a.id
    assert pago.paid_at is not None
    # El importe sale del backend (`quote`), igual que en línea.
    assert (pago.amount, pago.currency) == (Decimal(cuerpo["amount"]), "BOB")
    # El correo de siempre, al paciente, con el comprobante.
    [correo] = mail.outbox
    assert correo.subject == "Tu ficha está confirmada"
    assert "MC1." in correo.body


def test_el_cobro_queda_en_la_bitacora_a_nombre_de_quien_cobro(
    api_client, recepcion_a, org_a, ficha_pendiente,
):
    cobrar(api_client, recepcion_a, ficha_pendiente)
    with tenant_context(org_a.id):
        eventos = list(
            AuditLog.objects.filter(action="payment.movement")
            .order_by("occurred_at").values_list("detail", "user_id")
        )
    assert [d["evento"] for d, _ in eventos] == ["cobro_en_ventanilla", "pagado"]
    assert {u for _, u in eventos} == {recepcion_a.id}
    assert all(d["proveedor"] == "cash" for d, _ in eventos)


def test_sin_pago_en_linea_en_el_plan_igual_se_cobra_en_ventanilla(
    api_client, recepcion_a, org_a, ficha_pendiente,
):
    """El plan Básico no trae pago en línea: es el que cobra en ventanilla."""
    plan = current_plan(org_a)
    with platform_admin_context():
        plan.features = {**plan.features, "online_payment": False}
        plan.save(update_fields=["features"])

    assert cobrar(api_client, recepcion_a, ficha_pendiente).status_code == 201


# ==========================================================================
#  Lo que no se puede
# ==========================================================================
def test_el_paciente_no_puede_cobrarse_en_ventanilla(
    api_client, paciente_a, org_a, ficha_pendiente,
):
    assert cobrar(api_client, paciente_a, ficha_pendiente).status_code == 403
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"
    assert pagos(org_a, ficha_pendiente) == []


def test_no_se_cobra_dos_veces_la_misma_ficha(
    api_client, recepcion_a, org_a, ficha_pendiente,
):
    assert cobrar(api_client, recepcion_a, ficha_pendiente).status_code == 201
    segunda = cobrar(api_client, recepcion_a, ficha_pendiente)
    assert segunda.status_code == 400
    assert segunda.json()["code"] == "ficha_no_pendiente"
    assert len(pagos(org_a, ficha_pendiente)) == 1


def test_no_se_cobra_una_reserva_vencida(
    api_client, recepcion_a, org_a, paciente_a, practitioner_a, branches_a,
    agenda_a,
):
    vencida = crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        expires_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    respuesta = cobrar(api_client, recepcion_a, vencida)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "ficha_vencida"
    assert pagos(org_a, vencida) == []


@pytest.mark.isolation
def test_no_se_cobra_una_ficha_de_otra_organizacion(
    api_client, recepcion_b, org_a, ficha_pendiente,
):
    assert cobrar(api_client, recepcion_b, ficha_pendiente).status_code == 404
    assert recargar(org_a, ficha_pendiente).status == "pending_payment"


def test_dos_cobros_simultaneos_el_segundo_queda_devuelto(
    api_client, recepcion_a, org_a, ficha_pendiente,
):
    """Dos recepcionistas cobran a la vez: el primero ya confirmó cuando el
    segundo entra a `confirm_payment`. Se simula dejando un pago exitoso con
    la ficha todavía `pending_payment`, que es lo que ve el segundo."""
    with tenant_context(org_a.id):
        Payment.objects.create(
            organization=org_a, appointment=ficha_pendiente,
            created_by=recepcion_a, amount=Decimal("100.00"), currency="BOB",
            provider=Payment.Provider.CASH, status=Payment.Status.SUCCEEDED,
            paid_at=timezone.now(),
        )

    respuesta = cobrar(api_client, recepcion_a, ficha_pendiente)

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "ficha_ya_pagada"
    segundo = pagos(org_a, ficha_pendiente)[-1]
    assert segundo.status == Payment.Status.REFUNDED
    assert segundo.refund_reason == "pago_duplicado"


# ==========================================================================
#  La devolución y el proveedor
# ==========================================================================
def test_cancelar_a_tiempo_lo_cobrado_en_efectivo_lo_deja_para_devolver(
    api_client, recepcion_a, paciente_a, org_a, ficha_pendiente,
):
    cobrar(api_client, recepcion_a, ficha_pendiente)

    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha_pendiente.id]),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["refund_eligible"] is True
    [pago] = pagos(org_a, ficha_pendiente)
    assert pago.status == Payment.Status.REFUNDED
    assert pago.refund_reason == "cancelacion_a_tiempo"


def test_el_efectivo_no_abre_un_checkout_en_linea():
    with pytest.raises(ProviderError):
        CashProvider().create_checkout(payment=None, request=None)


def test_el_permiso_se_siembra_para_recepcion_y_administracion(db):
    with platform_admin_context():
        roles = set(
            RolePermission.objects
            .filter(permission__code=PERMISO, role__organization__isnull=True)
            .values_list("role__code", flat=True)
        )
    assert roles == {"receptionist", "org_admin"}
