"""US-18 — Con quién se cobra.

Dos proveedores con la misma forma:

- **Stripe**, en modo prueba. El paciente paga en el Checkout alojado por
  Stripe —la tarjeta nunca pasa por nuestros servidores— y la ficha la
  confirma el **webhook firmado** (`views.stripe_webhook`).
- **Simulado**, cuando no hay clave. Es una página de pago propia que confirma
  llamando a `services.confirm_payment`, **la misma función que llama el
  webhook**. Así el resto del sistema —confirmación, comprobante, devolución—
  se prueba igual con o sin cuenta de Stripe, y el móvil no puede distinguir
  uno de otro: en los dos casos abre una URL y espera a que el backend diga
  que la ficha quedó confirmada.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core import signing
from django.urls import reverse

SIMULATED_SALT = "payments.simulated-checkout"


class ProviderError(Exception):
    """El proveedor rechazó la operación o no está configurado."""


@dataclass
class Checkout:
    session_id: str
    url: str


def active_provider() -> str:
    """El proveedor con el que se abren los checkouts nuevos."""
    modo = (settings.PAYMENTS_PROVIDER or "auto").lower()
    if modo == "auto":
        return "stripe" if settings.STRIPE_SECRET_KEY else "simulated"
    return modo


RETURN_TARGETS = ("app", "web")


def return_url(request, appointment_id, return_to) -> str:
    """La página de regreso, con la ficha y el origen. Sin `resultado`."""
    base = request.build_absolute_uri(reverse("payments:return"))
    return f"{base}?ficha={appointment_id}&origen={return_to}"


def _cents(amount) -> int:
    return int((amount * 100).to_integral_value())


class StripeProvider:
    name = "stripe"

    def _stripe(self):
        import stripe

        if not settings.STRIPE_SECRET_KEY:
            raise ProviderError("Stripe no está configurado (falta STRIPE_SECRET_KEY).")
        return stripe

    def create_checkout(self, payment, request, return_to="app") -> Checkout:
        stripe = self._stripe()
        appointment = payment.appointment
        metadata = {
            "payment_id": str(payment.id),
            "organization_id": str(payment.organization_id),
            "appointment_id": str(appointment.id),
        }
        regreso = return_url(request, appointment.id, return_to)
        try:
            session = stripe.checkout.Session.create(
                api_key=settings.STRIPE_SECRET_KEY,
                mode="payment",
                line_items=[{
                    "quantity": 1,
                    "price_data": {
                        "currency": payment.currency.lower(),
                        "unit_amount": _cents(payment.amount),
                        "product_data": {
                            "name": f"Ficha médica — {appointment.practitioner.full_name}",
                            "description": (
                                f"{appointment.branch.name} · "
                                f"{appointment.starts_at:%d/%m/%Y %H:%M} UTC"
                            ),
                        },
                    },
                }],
                client_reference_id=str(payment.id),
                metadata=metadata,
                payment_intent_data={"metadata": metadata},
                success_url=f"{regreso}&resultado=pagado",
                cancel_url=f"{regreso}&resultado=cancelado",
                # El mínimo que acepta Stripe son 30 minutos.
                expires_at=int(time.time()) + 31 * 60,
            )
        except stripe.StripeError as error:
            raise ProviderError(str(error.user_message or error)) from error
        return Checkout(session_id=session.id, url=session.url)

    def refund(self, payment) -> None:
        stripe = self._stripe()
        if not payment.provider_payment_id:
            raise ProviderError("El pago no tiene PaymentIntent: no se puede devolver.")
        try:
            stripe.Refund.create(
                api_key=settings.STRIPE_SECRET_KEY,
                payment_intent=payment.provider_payment_id,
                metadata={"payment_id": str(payment.id)},
            )
        except stripe.StripeError as error:
            raise ProviderError(str(error.user_message or error)) from error

    @staticmethod
    def parse_event(payload: bytes, signature: str):
        """Verifica la firma del webhook. Lanza `ProviderError` si no cierra.

        Sin `STRIPE_WEBHOOK_SECRET` no se acepta ningún evento: un webhook que
        confirma fichas sin verificar la firma es una forma de reservar gratis.
        """
        import stripe

        if not settings.STRIPE_WEBHOOK_SECRET:
            raise ProviderError("Falta STRIPE_WEBHOOK_SECRET: no se aceptan eventos.")
        try:
            return stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.SignatureVerificationError) as error:
            raise ProviderError("Firma de Stripe inválida.") from error


class SimulatedProvider:
    name = "simulated"

    def create_checkout(self, payment, request, return_to="app") -> Checkout:
        token = signing.dumps(
            {"p": str(payment.id), "o": str(payment.organization_id),
             "r": return_to},
            salt=SIMULATED_SALT,
        )
        url = request.build_absolute_uri(
            reverse("payments:simulated-checkout", args=[token]),
        )
        return Checkout(session_id=f"sim_cs_{uuid.uuid4().hex}", url=url)

    def refund(self, payment) -> None:
        # No hay dinero de por medio: devolver es sólo cambiar el estado.
        return None

    @staticmethod
    def read_token(token: str) -> dict:
        try:
            # Vale lo mismo que una sesión de Checkout de Stripe.
            return signing.loads(token, salt=SIMULATED_SALT, max_age=31 * 60)
        except signing.BadSignature as error:
            raise ProviderError("El enlace de pago no es válido o venció.") from error


def provider_for(name: str):
    if name == "stripe":
        return StripeProvider()
    if name == "simulated":
        return SimulatedProvider()
    raise ProviderError(f"Proveedor de pago desconocido: {name}")
