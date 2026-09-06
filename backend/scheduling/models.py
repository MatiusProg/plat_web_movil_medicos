"""Agendas médicas y sus bloqueos.

La agenda se guarda como **regla y no como lista** (US-13 a): de un `Schedule`
—profesional, sucursal, día de la semana, franja horaria, duración de consulta
y cupo— se derivan los espacios reservables para el horizonte que pida cada
consulta. Guardar cada espacio suelto haría inmanejable el cambio de horario.

Los `ScheduleBlock` (US-14) tapan rangos de la agenda por vacaciones, feriados
o ausencias, sin tocar la regla: al levantar el bloqueo, la agenda vuelve sola.
"""

import uuid

from django.db import models


class Schedule(models.Model):
    """US-13 — La regla de agenda de un profesional en una sucursal."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="schedules",
    )
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT, related_name="schedules",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT, related_name="schedules",
    )
    # 0 = lunes … 6 = domingo (isoweekday - 1).
    weekday = models.PositiveSmallIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    # Duración de la consulta, en minutos: el paso entre un espacio y el
    # siguiente.
    slot_minutes = models.PositiveSmallIntegerField()
    # Cupo por franja (US-13 f): mayor a uno para las especialidades que
    # atienden por orden de llegada dentro de un bloque.
    capacity = models.PositiveSmallIntegerField(default=1)
    # Vigencia (US-13 e): cambiar el horario a partir de una fecha no altera
    # las fichas ya reservadas bajo la regla anterior.
    valid_from = models.DateField()
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "schedules"
        verbose_name = "agenda"
        verbose_name_plural = "agendas"
        ordering = ["practitioner_id", "weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_schedule_id_org",
            ),
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="ck_schedule_time_order",
            ),
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0) & models.Q(weekday__lte=6),
                name="ck_schedule_weekday",
            ),
            models.CheckConstraint(
                condition=models.Q(slot_minutes__gt=0),
                name="ck_schedule_slot_minutes",
            ),
            models.CheckConstraint(
                condition=models.Q(capacity__gte=1),
                name="ck_schedule_capacity",
            ),
        ]

    def __str__(self):
        return (
            f"{self.practitioner_id} · {self.branch_id} · día {self.weekday} "
            f"{self.start_time}–{self.end_time}"
        )


class ScheduleBlock(models.Model):
    """US-14 — Bloqueo de la agenda por vacaciones, feriado o ausencia.

    Tapa un rango `[starts_at, ends_at)` (tz-aware). Si `practitioner` es NULL
    es un feriado de toda la organización y afecta a todos (US-14 c). La regla
    de agenda no se toca: al poner `is_active=False` (levantar el bloqueo,
    US-14 f), la agenda vuelve sola.
    """

    class Reason(models.TextChoices):
        VACATION = "vacation", "Vacaciones"
        HOLIDAY = "holiday", "Feriado"
        LEAVE = "leave", "Licencia"
        ABSENCE = "absence", "Ausencia imprevista"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="schedule_blocks",
    )
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        null=True, blank=True, related_name="schedule_blocks",
    )
    # Opcional: un bloqueo puede limitarse a una sede.
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT,
        null=True, blank=True, related_name="schedule_blocks",
    )
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    reason = models.CharField(max_length=12, choices=Reason.choices)
    note = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "schedule_blocks"
        verbose_name = "bloqueo de agenda"
        verbose_name_plural = "bloqueos de agenda"
        ordering = ["-starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_schedule_block_id_org",
            ),
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="ck_schedule_block_time_order",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    reason__in=["vacation", "holiday", "leave", "absence"],
                ),
                name="ck_schedule_block_reason",
            ),
        ]

    def __str__(self):
        alcance = self.practitioner_id or "toda la organización"
        return f"{alcance} · {self.starts_at:%Y-%m-%d %H:%M}–{self.ends_at:%Y-%m-%d %H:%M}"
