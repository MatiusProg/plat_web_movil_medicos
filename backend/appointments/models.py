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
    ACTIVE_STATUSES = [
        Status.PENDING_PAYMENT,
        Status.CONFIRMED,
    ]

    class CancellationReason(models.TextChoices):
        PATIENT = "patient", "El paciente canceló"
        NO_SHOW_POLICY = "no_show_policy", "Vencida por falta de pago"
        ORGANIZATION = "organization", "La organización canceló"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    # A quién es la ficha: el titular o un dependiente a cargo (US-07).
    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    # Quién hizo la reserva. Puede no coincidir con `patient` cuando el titular
    # reserva para un dependiente sin cuenta propia.
    booked_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="booked_appointments",
    )

    practitioner = models.ForeignKey(
        "catalog.Practitioner",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    branch = models.ForeignKey(
        "catalog.Branch",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    # La regla de agenda de la que salió el turno (US-13). Junto con
    # `starts_at` identifica el turno de forma unívoca, igual que en
    # `scheduling.availability` (`(schedule.id, start_aware) in booked`).
    schedule = models.ForeignKey(
        "scheduling.Schedule",
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
    )

    # US-22 — fecha y hora real del check-in en recepción.
    # Queda NULL mientras la ficha todavía no haya sido validada.
    checked_in_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # US-21 — el paciente confirmó que va a asistir. NULL = no confirmó. Es
    # el desenlace *confirmó / no confirmó* que necesita el Sprint 4.
    attendance_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # US-28 — cuándo salió el recordatorio previo a la ficha. NULL = todavía
    # no salió. Es lo que impide mandarlo dos veces: se marca en la misma
    # transacción que lo envía (ver `appointments/reminders.py`).
    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # US-36 — cuándo salió el segundo recordatorio, el de las fichas con riesgo
    # alto de inasistencia (US-35). Marca propia, independiente de la anterior:
    # una ficha puede recibir los dos. Se pone en la misma transacción que lo
    # envía (ver `appointments/reminders.py`).
    reinforced_reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # Vence la reserva `pending_payment`: pasado este momento, el turno se
    # considera libre aunque la fila siga existiendo con este estado hasta que
    # algo la marque `expired` (lectura perezosa, sin tarea en segundo plano).
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    cancellation_reason = models.CharField(
        max_length=20,
        choices=CancellationReason.choices,
        blank=True,
        default="",
    )

    # Null hasta que se cancela. Es el punto de integración con la devolución
    # real que ejecuta US-18 (pago con Stripe): acá sólo se decide SI
    # corresponde, según la política de anticipación de la organización.
    refund_eligible = models.BooleanField(
        null=True,
        blank=True,
    )

    # Al reprogramar, la ficha vieja pasa a `rescheduled` y apunta a la nueva.
    rescheduled_from = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reschedules_to",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        db_table = "appointments"
        verbose_name = "ficha"
        verbose_name_plural = "fichas"
        ordering = ["-starts_at"]

        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"],
                name="uq_appointment_id_org",
            ),

            # La regla de concurrencia de US-17: un solo turno activo por
            # `(schedule, starts_at)`. `condition` hace que cancelar o
            # reprogramar libere el turno de inmediato para el índice.
            models.UniqueConstraint(
                fields=[
                    "schedule",
                    "starts_at",
                ],
                condition=models.Q(
                    status__in=[
                        "pending_payment",
                        "confirmed",
                    ],
                ),
                name="uq_appointment_active_slot",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    ends_at__gt=models.F("starts_at"),
                ),
                name="ck_appointment_time_order",
            ),

            models.CheckConstraint(
                condition=models.Q(
                    status__in=[
                        "pending_payment",
                        "confirmed",
                        "attended",
                        "cancelled",
                        "rescheduled",
                        "expired",
                        "no_show",
                    ],
                ),
                name="ck_appointment_status",
            ),
        ]

    def __str__(self):
        return (
            f"{self.patient_id} · "
            f"{self.practitioner_id} · "
            f"{self.starts_at}"
        )

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES


class WaitlistEntry(models.Model):
    """US-52 — Un paciente esperando que se libere un turno.

    Se anota por un **profesional** o por una **especialidad** (cualquiera de
    sus profesionales), con el rango de fechas que le sirve y, si quiere, una
    sucursal. Cuando se cancela una ficha que encaja, `waitlist.offer_freed_slot`
    le guarda el turno 15 minutos como una ficha `pending_payment` real
    (`offered_appointment`): así el turno lo protege el mismo índice único de
    siempre, el pago es el de siempre y el vencimiento es el de las reservas
    (`holds.release_expired_holds`).

    Estados:

    - `waiting`    esperando; cuenta para la posición en la fila.
    - `offered`    se le guardó un turno y tiene 15 minutos para pagarlo.
    - `booked`     pagó el turno ofrecido.
    - `expired`    no lo tomó a tiempo, o pasó su rango de fechas.
    - `cancelled`  salió de la lista.
    """

    class Status(models.TextChoices):
        WAITING = "waiting", "Esperando"
        OFFERED = "offered", "Turno ofrecido"
        BOOKED = "booked", "Tomó el turno"
        EXPIRED = "expired", "Venció"
        CANCELLED = "cancelled", "Salió de la lista"

    # Los que cuentan para la unicidad y la posición: la entrada sigue viva.
    LIVE_STATUSES = [Status.WAITING, Status.OFFERED]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="waitlist_entries",
    )

    # Para quién es el turno: el titular o un dependiente a cargo (US-07).
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT,
        related_name="waitlist_entries",
    )
    # Quién se anotó. El aviso va al paciente o, si es un dependiente sin
    # cuenta, a su titular (`attendance.recipient_user`).
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="waitlist_entries",
    )

    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        null=True, blank=True, related_name="waitlist_entries",
    )
    specialty = models.ForeignKey(
        "catalog.Specialty", on_delete=models.PROTECT,
        null=True, blank=True, related_name="waitlist_entries",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT,
        null=True, blank=True, related_name="waitlist_entries",
    )

    # Los días (en la zona de la sede) en que le sirve el turno, ambos incluidos.
    date_from = models.DateField()
    date_to = models.DateField()

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.WAITING,
    )

    # La ficha `pending_payment` que se le guardó, y desde cuándo.
    offered_appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.PROTECT,
        null=True, blank=True, related_name="waitlist_offers",
    )
    offered_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "waitlist_entries"
        verbose_name = "entrada de lista de espera"
        verbose_name_plural = "entradas de lista de espera"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_waitlist_id_org",
            ),
            # Una sola entrada viva por paciente y profesional, y otra por
            # paciente y especialidad: anotarse dos veces no adelanta lugar.
            models.UniqueConstraint(
                fields=["patient", "practitioner"],
                condition=models.Q(
                    status__in=["waiting", "offered"],
                    practitioner__isnull=False,
                ),
                name="uq_waitlist_live_patient_practitioner",
            ),
            models.UniqueConstraint(
                fields=["patient", "specialty"],
                condition=models.Q(
                    status__in=["waiting", "offered"],
                    specialty__isnull=False,
                ),
                name="uq_waitlist_live_patient_specialty",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(practitioner__isnull=False)
                    | models.Q(specialty__isnull=False)
                ),
                name="ck_waitlist_target",
            ),
            models.CheckConstraint(
                condition=models.Q(date_to__gte=models.F("date_from")),
                name="ck_waitlist_date_order",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=["waiting", "offered", "booked", "expired",
                                "cancelled"],
                ),
                name="ck_waitlist_status",
            ),
        ]

    def __str__(self):
        return f"{self.patient_id} · {self.status} · {self.date_from}–{self.date_to}"


class AppointmentPreconsultation(models.Model):
    """US-51: notas voluntarias previas a la atención; nunca un diagnóstico."""

    appointment = models.OneToOneField(
        Appointment, on_delete=models.PROTECT, related_name="preconsultation",
    )
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="appointment_preconsultations",
    )
    reason = models.TextField(blank=True, default="")
    questions = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "appointment_preconsultations"
        constraints = [
            models.UniqueConstraint(fields=["appointment", "organization"],
                                    name="uq_preconsult_appointment_org"),
        ]
