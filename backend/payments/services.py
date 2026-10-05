"""US-18 — Abrir el cobro, confirmarlo y devolverlo.

`confirm_payment` es **el único lugar donde una ficha pasa a `confirmed` por
un pago**. Lo llaman el webhook de Stripe y la página del proveedor simulado,
nunca una vista que use el paciente (regla 10 del Sprint 2).

Todas las funciones de acá suponen que el contexto de inquilino ya está
fijado: en una petición autenticada lo fija la autenticación; en el webhook,
que llega sin usuario, `views` lo abre con `tenant_context` a partir de la
organización que viaja en la metadata **firmada** del evento.
"""

from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from appointments.models import Appointment
from audit.actions import Action
from audit.services import record

from .models import Payment
from .pricing import quote
from .providers import ProviderError, active_provider, provider_for

logger = logging.getLogger(__name__)


def start_checkout(appointment: Appointment, *, user, request,
                   return_to: str = "app") -> Payment:
    """Crea un intento de cobro y la sesión del proveedor.

    Lanza `ValidationError` si la ficha no está esperando pago, y
    `ProviderError` si el proveedor no la acepta.
    """
    now = timezone.now()
    if appointment.status != Appointment.Status.PENDING_PAYMENT:
        raise ValidationError(
            "Esta ficha no está pendiente de pago.", code="ficha_no_pendiente",
        )
    if appointment.expires_at and appointment.expires_at <= now:
        raise ValidationError(
            "La reserva venció antes de pagarla. Elegí el turno de nuevo.",
            code="ficha_vencida",
        )

    amount, currency = quote(appointment)
    nombre = active_provider()
    with transaction.atomic():
        payment = Payment.objects.create(
            organization_id=appointment.organization_id,
            appointment=appointment,
            created_by=user,
            amount=amount,
            currency=currency,
            provider=nombre,
        )
        checkout = provider_for(nombre).create_checkout(payment, request, return_to)
        payment.provider_session_id = checkout.session_id
        payment.checkout_url = checkout.url
        payment.save(update_fields=["provider_session_id", "checkout_url", "updated_at"])

    record(
        request, Action.PAYMENT_MOVEMENT, "payment", payment.id,
        detail={"evento": "checkout", "ficha": str(appointment.id),
                "importe": str(amount), "moneda": currency, "proveedor": nombre},
    )
    return payment


def confirm_payment(payment: Payment, *, provider_payment_id: str = "",
                    request=None) -> Payment:
    """El cobro se concretó: confirma la ficha. Idempotente.

    Stripe reintenta los webhooks, así que el mismo evento puede llegar más de
    una vez: la segunda no hace nada. Y el pago puede llegar cuando la ficha ya
    no lo espera —se canceló, venció, o se pagó dos veces desde dos
    pestañas—: en ese caso el dinero se devuelve en el acto, no se queda.
    """
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status in (Payment.Status.SUCCEEDED, Payment.Status.REFUNDED):
            return payment

        # `of=("self",)`: FOR UPDATE sobre un JOIN bloquea también las filas
        # unidas, y PostgreSQL les exige la política de UPDATE. La de
        # `organizations` es sólo de plataforma: sin esto, la fila desaparece.
        appointment = (
            Appointment.objects.select_for_update(of=("self",))
            .select_related("patient", "practitioner", "branch", "organization")
            .get(pk=payment.appointment_id)
        )
        if provider_payment_id:
            payment.provider_payment_id = provider_payment_id
        payment.paid_at = timezone.now()

        ya_pagada = Payment.objects.filter(
            appointment_id=appointment.id, status=Payment.Status.SUCCEEDED,
        ).exists()
        if ya_pagada or appointment.status != Appointment.Status.PENDING_PAYMENT:
            motivo = "pago_duplicado" if ya_pagada else "ficha_no_disponible"
            payment.save(update_fields=["provider_payment_id", "paid_at", "updated_at"])
            return refund_payment(payment, reason=motivo, request=request)

        payment.status = Payment.Status.SUCCEEDED
        payment.save(update_fields=[
            "status", "provider_payment_id", "paid_at", "updated_at",
        ])

        appointment.status = Appointment.Status.CONFIRMED
        appointment.expires_at = None
        appointment.save(update_fields=["status", "expires_at", "updated_at"])

        # US-21: el aviso por correo con el comprobante y el enlace para
        # confirmar asistencia. Después del COMMIT: si la transacción se
        # revierte, no se manda un correo de una ficha que no quedó confirmada.
        from appointments.attendance import send_confirmation_email

        transaction.on_commit(lambda: send_confirmation_email(appointment.id,
                                                              appointment.organization_id))

    _asentar(request, payment, "pagado")
    return payment


def refund_payment(payment: Payment, *, reason: str, request=None) -> Payment:
    """Devuelve el cobro con el proveedor y lo deja `refunded`."""
    if payment.status == Payment.Status.REFUNDED:
        return payment
    provider_for(payment.provider).refund(payment)
    payment.status = Payment.Status.REFUNDED
    payment.refunded_at = timezone.now()
    payment.refund_reason = reason
    payment.save(update_fields=["status", "refunded_at", "refund_reason", "updated_at"])
    _asentar(request, payment, "devuelto", motivo=reason)
    return payment


def refund_for_cancellation(appointment: Appointment, *, request=None) -> Payment | None:
    """US-20 → US-18: la política de devolución.

    **Política** (definida por el PO en US-18): si el paciente cancela con al
    menos `Organization.cancellation_notice_hours` de anticipación
    —`refund_eligible`, que decide US-20—, se le devuelve el **100 %**. Con
    menos anticipación no se devuelve nada. Sin pago previo no hay nada que
    devolver.

    Si el proveedor falla, la ficha igual queda cancelada y el pago sigue
    `succeeded`: se registra en el log para devolverlo a mano. Una cancelación
    no puede quedar a medias porque Stripe no contestó.
    """
    if not appointment.refund_eligible:
        return None
    payment = Payment.objects.filter(
        appointment_id=appointment.id, status=Payment.Status.SUCCEEDED,
    ).first()
    if payment is None:
        return None
    try:
        return refund_payment(payment, reason="cancelacion_a_tiempo", request=request)
    except ProviderError:
        logger.exception("No se pudo devolver el pago %s de la ficha %s",
                         payment.id, appointment.id)
        return payment


def transfer_payment(origen: Appointment, destino: Appointment, *,
                     request=None) -> Payment | None:
    """US-20 → US-18: el pago acompaña a la ficha cuando se reprograma.

    Reprogramar crea una ficha **nueva** y deja la vieja `rescheduled`; es la
    misma compra movida de horario. El `Payment` se enlaza por ficha, así que
    si se quedara en la vieja, la nueva figuraría pagada sin pago: no mostraría
    `payment_status` y, al cancelarla a tiempo, `refund_for_cancellation` no
    encontraría qué devolver.

    Mueve el pago `succeeded` de [origen] a [destino]; si no hay —la ficha no
    estaba pagada— no hace nada. `uq_payment_one_success` no estorba: la ficha
    nueva todavía no tiene ningún pago. Los intentos abandonados (`pending`)
    quedan en la vieja: si alguien los paga después, `confirm_payment` los
    devuelve solo, porque esa ficha ya no espera pago.

    Debe llamarse dentro de la transacción de la reprogramación: bloquea la
    fila del pago, y si algo falla después, el pago vuelve a la ficha original.
    """
    payment = (
        Payment.objects.select_for_update()
        .filter(appointment_id=origen.id, status=Payment.Status.SUCCEEDED)
        .first()
    )
    if payment is None:
        return None
    payment.appointment = destino
    payment.save(update_fields=["appointment", "updated_at"])
    _asentar(request, payment, "reprogramado", ficha_origen=str(origen.id))
    return payment


def _asentar(request, payment, evento, **extra):
    if request is None:
        return
    record(
        request, Action.PAYMENT_MOVEMENT, "payment", payment.id,
        detail={"evento": evento, "ficha": str(payment.appointment_id),
                "importe": str(payment.amount), "moneda": payment.currency,
                "proveedor": payment.provider, **extra},
        organization=payment.organization, user=payment.created_by,
    )
