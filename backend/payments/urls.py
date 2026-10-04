"""Rutas de la app `payments`. Prefijo `/api/payments/`."""

from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    # ---------- US-18 — Pago en línea -----------------------------------
    path(
        "appointments/<uuid:pk>/checkout/",
        views.CheckoutView.as_view(),
        name="checkout",
    ),
    # Lo llama Stripe, sin usuario: se autentica con la firma del evento.
    path("webhooks/stripe/", views.stripe_webhook, name="stripe-webhook"),
    # Adonde vuelve el navegador después de pagar o de cancelar.
    path("return/", views.return_page, name="return"),
    # Página de pago del proveedor simulado (sin claves de Stripe).
    path(
        "simulated/<str:token>/",
        views.simulated_checkout,
        name="simulated-checkout",
    ),
]
