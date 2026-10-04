"""US-18 — El pago de una ficha.

Un `Payment` es **un intento de cobro**: el paciente puede abrir el checkout,
abandonarlo y volver a abrirlo, y cada vez nace una fila `pending`. Sólo una
puede terminar `succeeded` por ficha —lo garantiza `uq_payment_one_success`—,
así que un webhook repetido o dos pestañas pagando a la vez no cobran dos
veces la misma ficha sin que se note: la segunda queda registrada y devuelta.

**El importe se fija al crear el intento y no se recalcula.** Si el catálogo
cambia el precio mientras el paciente está en la pantalla de Stripe, se cobra
lo que se le mostró.
"""

import uuid

from django.db import models


class Payment(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        SUCCEEDED = "succeeded", "Pagado"
        FAILED = "failed", "Fallido"
        EXPIRED = "expired", "Vencido"
        REFUNDED = "refunded", "Devuelto"

    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        SIMULATED = "simulated", "Simulado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="payments",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.PROTECT,
        related_name="payments",
    )
    # Quién abrió el checkout: el paciente o el titular de un dependiente.
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="payments",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    provider = models.CharField(max_length=12, choices=Provider.choices)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING,
    )
    # Id de la sesión de Checkout (`cs_test_…`). Es lo que trae el webhook.
    provider_session_id = models.CharField(
        max_length=255, null=True, blank=True, unique=True,
    )
    # Id del PaymentIntent: es el que hace falta para devolver.
    provider_payment_id = models.CharField(max_length=255, blank=True, default="")
    checkout_url = models.TextField(blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    # Por qué se devolvió: la cancelación a tiempo (US-20) o que el pago llegó
    # cuando la ficha ya no existía (vencida o cancelada).
    refund_reason = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "payments"
        verbose_name = "pago"
        verbose_name_plural = "pagos"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_payment_id_org",
            ),
            models.UniqueConstraint(
                fields=["appointment"],
                condition=models.Q(status="succeeded"),
                name="uq_payment_one_success",
            ),
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_payment_amount",
            ),
        ]

    def __str__(self):
        return f"{self.appointment_id} · {self.amount} {self.currency} · {self.status}"
