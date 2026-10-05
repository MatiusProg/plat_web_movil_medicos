"""US-18 — Vistas del pago.

Tres de las cuatro no tienen usuario autenticado, y es a propósito: las abre
el navegador (la página de regreso y la del proveedor simulado) o Stripe (el
webhook). Ninguna confía en lo que le dicen sin verificarlo: el webhook
verifica la firma de Stripe y la página simulada un token firmado con la
`SECRET_KEY`. Las dos fijan el contexto de inquilino con la organización que
viene **dentro** de lo firmado.
"""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.mixins import owns_appointment
from appointments.models import Appointment
from tenancy.context import tenant_context
from tenancy.plans import require_feature

from .models import Payment
from .permissions import CanCreatePayments
from .providers import (
    RETURN_TARGETS,
    ProviderError,
    SimulatedProvider,
    StripeProvider,
    active_provider,
)
from .services import confirm_payment, start_checkout

logger = logging.getLogger(__name__)


class CheckoutView(APIView):
    """`POST /payments/appointments/{id}/checkout/`.

    Devuelve la URL donde se paga. **No confirma nada**: la ficha sigue
    `pending_payment` hasta que llegue el webhook. El móvil abre la URL y
    después vuelve a pedir la ficha.
    """

    permission_classes = [IsAuthenticated, CanCreatePayments]

    def post(self, request, pk=None):
        appointment = (
            Appointment.objects
            .select_related("patient", "practitioner", "branch")
            .filter(pk=pk, organization=request.user.organization)
            .first()
        )
        if appointment is None:
            return Response({"detail": "La ficha no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        if (getattr(request.user, "patient_profile", None) is not None
                and not owns_appointment(request.user, appointment)):
            return Response({"detail": "No podés pagar una ficha que no es tuya."},
                            status=status.HTTP_403_FORBIDDEN)

        # Lo que promete el plan se cumple (tenancy/plans.py).
        require_feature(request.user.organization, "online_payment",
                        "el pago en línea")

        # De dónde se pidió el pago: decide adónde vuelve el paciente. Un
        # valor desconocido cae en "app", el único cliente que paga hoy.
        return_to = request.data.get("return_to", "app")
        if return_to not in RETURN_TARGETS:
            return_to = "app"

        try:
            payment = start_checkout(appointment, user=request.user,
                                     request=request, return_to=return_to)
        except ValidationError as error:
            return Response({"code": error.code, "detail": error.messages[0]},
                            status=status.HTTP_400_BAD_REQUEST)
        except ProviderError as error:
            logger.warning("El proveedor rechazó el checkout: %s", error)
            return Response(
                {"code": "proveedor_de_pago",
                 "detail": "No se pudo iniciar el pago. Intentá de nuevo en un momento."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response({
            "payment_id": str(payment.id),
            "provider": payment.provider,
            "checkout_url": payment.checkout_url,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
        }, status=status.HTTP_201_CREATED)


# Eventos de Checkout que significan "el dinero entró".
PAID_EVENTS = {"checkout.session.completed", "checkout.session.async_payment_succeeded"}


@csrf_exempt
def stripe_webhook(request):
    """`POST /payments/webhooks/stripe/` — lo único que confirma una ficha."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    try:
        event = StripeProvider.parse_event(
            request.body, request.headers.get("Stripe-Signature", ""),
        )
    except ProviderError as error:
        logger.warning("Webhook de Stripe rechazado: %s", error)
        return HttpResponse(status=400)

    tipo = event["type"]
    if tipo not in PAID_EVENTS and tipo != "checkout.session.expired":
        # Stripe manda muchos tipos; los que no interesan se aceptan y se
        # ignoran, o los reintentaría durante tres días.
        return HttpResponse(status=200)

    session = event["data"]["object"]
    metadata = session.get("metadata") or {}
    try:
        organization_id = uuid.UUID(metadata.get("organization_id", ""))
        payment_id = uuid.UUID(metadata.get("payment_id", ""))
    except ValueError:
        logger.warning("Evento %s sin metadata de pago", event.get("id"))
        return HttpResponse(status=200)

    with tenant_context(organization_id):
        payment = Payment.objects.filter(
            pk=payment_id, provider=Payment.Provider.STRIPE,
            provider_session_id=session["id"],
        ).first()
        if payment is None:
            logger.warning("Evento %s de un pago que no existe", event.get("id"))
            return HttpResponse(status=200)

        if tipo == "checkout.session.expired":
            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.EXPIRED
                payment.save(update_fields=["status", "updated_at"])
        elif session.get("payment_status") == "paid":
            confirm_payment(
                payment,
                provider_payment_id=session.get("payment_intent") or "",
                request=request,
            )
    return HttpResponse(status=200)


def _pagina(titulo, cuerpo):
    return format_html(
        """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{}</title>
<style>
 body{{font-family:system-ui,sans-serif;background:#f4f6f8;color:#1b2430;margin:0;padding:24px}}
 main{{max-width:420px;margin:40px auto;background:#fff;border-radius:14px;padding:28px;
       box-shadow:0 4px 20px rgba(0,0,0,.08)}}
 h1{{font-size:1.3rem;margin:0 0 8px}} .importe{{font-size:2rem;font-weight:700;margin:16px 0}}
 .aviso{{background:#fff7e0;border-radius:8px;padding:10px 12px;font-size:.9rem}}
 button{{width:100%;padding:14px;border:0;border-radius:10px;font-size:1rem;margin-top:12px;cursor:pointer}}
 .pagar{{background:#0f7b6c;color:#fff}} .cancelar{{background:#e8ebef;color:#1b2430}}
 dl{{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;font-size:.95rem}} dt{{color:#5b6675}}
</style></head><body><main>{}</main></body></html>""",
        titulo, cuerpo,
    )


def _volver(resultado, ficha="", origen="app"):
    return redirect(
        f"{reverse('payments:return')}?resultado={resultado}"
        f"&ficha={ficha}&origen={origen}",
    )


def return_page(request):
    """Adonde vuelve el navegador después de pagar o de cancelar.

    **No confirma nada**: la ficha la confirma el webhook. Sólo lleva al
    paciente de vuelta a donde estaba:

    - `origen=web` → redirige a "Mis fichas" de la web.
    - `origen=app` → abre la app en la ficha (`MOBILE_DEEP_LINK_BASE`), con un
      botón por si el navegador no deja abrirla sola: varios exigen un toque
      del usuario para pasar a otra aplicación.

    La ficha se valida como UUID y los destinos salen de `settings`: nada de
    lo que viene en la URL se usa como dirección.
    """
    pagado = request.GET.get("resultado") == "pagado"
    origen = request.GET.get("origen", "")
    try:
        ficha = str(uuid.UUID(request.GET.get("ficha", "")))
    except ValueError:
        ficha = ""

    if origen == "web":
        destino = f"{settings.FRONTEND_BASE_URL}/mis-fichas"
        if ficha:
            destino += f"?ficha={ficha}&pago={'pagado' if pagado else 'cancelado'}"
        return redirect(destino)

    if pagado:
        titulo, texto = "Pago recibido", (
            "Tu ficha aparece confirmada en la aplicación en cuanto el "
            "procesador de pagos lo notifique, en general en unos segundos.")
    else:
        titulo, texto = "Pago cancelado", (
            "No se cobró nada. Podés intentarlo de nuevo desde la aplicación "
            "mientras la reserva siga vigente.")

    if origen != "app" or not ficha:
        return HttpResponse(_pagina("Pago de la ficha", format_html(
            "<h1>{}</h1><p>{}</p>", titulo, texto)))

    enlace = f"{settings.MOBILE_DEEP_LINK_BASE}/appointments/{ficha}"
    cuerpo = format_html(
        """<h1>{}</h1><p>{}</p>
<a href="{}"><button class="pagar" type="button">Volver a la aplicación</button></a>
<script>setTimeout(function(){{ window.location.href = {}; }}, 600);</script>""",
        titulo, texto, enlace, _js_string(enlace),
    )
    return HttpResponse(_pagina("Pago de la ficha", cuerpo))


def _js_string(valor):
    """Cadena JS segura dentro de <script>: JSON y sin `<`."""
    import json

    from django.utils.safestring import mark_safe

    return mark_safe(json.dumps(valor).replace("<", "\\u003c"))


@csrf_exempt
def simulated_checkout(request, token):
    """La página de pago del proveedor simulado.

    Sólo funciona mientras el proveedor activo sea el simulado: con las claves
    de Stripe cargadas, un enlace simulado viejo ya no cobra nada.
    """
    if active_provider() != "simulated":
        return HttpResponse(_pagina("Pago no disponible", format_html(
            "<h1>Pago no disponible</h1><p>Este enlace de pago ya no es válido.</p>")),
            status=410)
    try:
        datos = SimulatedProvider.read_token(token)
        organization_id = uuid.UUID(datos["o"])
        payment_id = uuid.UUID(datos["p"])
        origen = datos.get("r", "app")
    except (ProviderError, KeyError, ValueError):
        return HttpResponse(_pagina("Enlace inválido", format_html(
            "<h1>Enlace inválido</h1><p>El enlace de pago no es válido o venció.</p>")),
            status=400)

    with tenant_context(organization_id):
        payment = (
            Payment.objects
            .select_related("appointment__practitioner", "appointment__branch",
                            "appointment__patient")
            .filter(pk=payment_id, provider=Payment.Provider.SIMULATED)
            .first()
        )
        if payment is None:
            return HttpResponse(status=404)

        if request.method == "POST":
            if request.POST.get("accion") == "pagar":
                confirm_payment(payment, provider_payment_id=f"sim_pi_{uuid.uuid4().hex}",
                                request=request)
                return _volver("pagado", payment.appointment_id, origen)
            if payment.status == Payment.Status.PENDING:
                payment.status = Payment.Status.FAILED
                payment.save(update_fields=["status", "updated_at"])
            return _volver("cancelado", payment.appointment_id, origen)

        if payment.status != Payment.Status.PENDING:
            return HttpResponse(_pagina("Pago ya procesado", format_html(
                "<h1>Este pago ya fue procesado</h1><p>Estado: {}.</p>",
                payment.get_status_display())))

        ficha = payment.appointment
        cuerpo = format_html(
            """<h1>Pagar la ficha</h1>
<p class="aviso">Pasarela <b>simulada</b> de pruebas: no se cobra dinero real.
Confirma la ficha por el mismo camino que el webhook de Stripe.</p>
<div class="importe">{} {}</div>
<dl><dt>Paciente</dt><dd>{}</dd><dt>Profesional</dt><dd>{}</dd>
<dt>Sucursal</dt><dd>{}</dd><dt>Tarjeta</dt><dd>4242 4242 4242 4242 (prueba)</dd></dl>
<form method="post"><button class="pagar" name="accion" value="pagar">Pagar</button>
<button class="cancelar" name="accion" value="cancelar">Cancelar</button></form>""",
            payment.currency, payment.amount, ficha.patient.full_name,
            ficha.practitioner.full_name, ficha.branch.name,
        )
        return HttpResponse(_pagina("Pagar la ficha", cuerpo))
