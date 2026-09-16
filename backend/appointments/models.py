"""US-17 y US-20 — La ficha.

Una ficha nace `pending_payment` sobre un turno concreto —`(schedule,
starts_at)`— derivado de la regla de agenda de `scheduling` (US-13/US-15).
Sólo se confirma cuando el Sprint 2 tenga el webhook de pago (US-18); acá se
deja el estado y el campo `refund_eligible` como punto de integración.

**La concurrencia se resuelve con un índice único parcial**, no comprobando
disponibilidad antes de insertar: `uq_appointment_active_slot` sólo permite una
ficha activa (`pending_payment` o `confirmed`) por `(schedule, starts_at)`. Dos
reservas simultáneas del mismo turno terminan en una fila y un
`IntegrityError` — nunca en dos fichas.
"""

import uuid

from django.db import models


class Appointment(models.Model):
    """Una ficha reservada sobre un turno derivado de `scheduling.Schedule`."""

    class Status(models.TextChoices):
        PENDING_PAYMENT = "pending_payment", "Pendiente de pago"
        CONFIRMED = "confirmed", "Confirmada"
        ATTENDED = "attended", "Atendida"
        CANCELLED = "cancelled", "Cancelada"
        RESCHEDULED = "rescheduled", "Reprogramada"
        EXPIRED = "expired", "Vencida"
        NO_SHOW = "no_show", "Ausente"

    # Estados que todavía ocupan el turno: los que cuenta la disponibilidad
    # (`scheduling.availability._booked_slots`) y los únicos que la unicidad
    # parcial de abajo protege.
    ACTIVE_STATUSES = [Status.PENDING_PAYMENT, Status.CONFIRMED]

    class CancellationReason(models.TextChoices):
        PATIENT = "patient", "El paciente canceló"
        NO_SHOW_POLICY = "no_show_policy", "Vencida por falta de pago"
        ORGANIZATION = "organization", "La organización canceló"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="appointments",
    )
    # A quién es la ficha: el titular o un dependiente a cargo (US-07).
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT,
        related_name="appointments",
    )
    # Quién hizo la reserva. Puede no coincidir con `patient` cuando el titular
    # reserva para un dependiente sin cuenta propia.
    booked_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="booked_appointments",
    )
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        related_name="appointments",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT, related_name="appointments",
    )
    # La regla de agenda de la que salió el turno (US-13). Junto con
    # `starts_at` identifica el turno de forma unívoca, igual que en
    # `scheduling.availability` (`(schedule.id, start_aware) in booked`).
    schedule = models.ForeignKey(
        "scheduling.Schedule", on_delete=models.PROTECT,
        related_name="appointments",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING_PAYMENT,
    )
    # Vence la reserva `pending_payment`: pasado este momento, el turno se
    # considera libre aunque la fila siga existiendo con este estado hasta que
    # algo la marque `expired` (lectura perezosa, sin tarea en segundo plano).
    expires_at = models.DateTimeField(null=True, blank=True)

    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.CharField(
        max_length=20, choices=CancellationReason.choices, blank=True, default="",
    )
    # Null hasta que se cancela. Es el punto de integración con la devolución
    # real que ejecuta US-18 (pago con Stripe): acá sólo se decide SI
    # corresponde, según la política de anticipación de la organización.
    refund_eligible = models.BooleanField(null=True, blank=True)

    # Al reprogramar, la ficha vieja pasa a `rescheduled` y apunta a la nueva.
    rescheduled_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reschedules_to",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointments"
        verbose_name = "ficha"
        verbose_name_plural = "fichas"
        ordering = ["-starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_appointment_id_org",
            ),
            # La regla de concurrencia de US-17: un solo turno activo por
            # `(schedule, starts_at)`. `condition` hace que cancelar o
            # reprogramar libere el turno de inmediato para el índice.
            models.UniqueConstraint(
                fields=["schedule", "starts_at"],
                condition=models.Q(
                    status__in=["pending_payment", "confirmed"],
                ),
                name="uq_appointment_active_slot",
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="ck_appointment_time_order",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=[
                    "pending_payment", "confirmed", "attended", "cancelled",
                    "rescheduled", "expired", "no_show",
                ]),
                name="ck_appointment_status",
            ),
        ]

    def __str__(self):
        return f"{self.patient_id} · {self.practitioner_id} · {self.starts_at}"

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES
