"""US-42 — Todo texto que escribe la IA para un paciente, y su validación.

**Una sola tabla para todo texto generado** (``ai_generated_texts``, la que
el modelo de datos del Sprint 0 reservó para el Sprint 4). US-39 (resumen de
la consulta) y US-40 (preparación para estudios) escriben acá; nadie crea su
propia tabla. Así la regla 14 del sprint —*ningún texto generado llega al
paciente sin aprobación de un médico*— se cumple en un solo lugar.

Tres decisiones:

1. **Se guardan los dos textos:** el que escribió el modelo
   (``generated_text``), que no se toca nunca, y el que aprobó el médico
   (``final_text``). Si el médico lo corrigió, la diferencia queda. Es la
   respuesta a «¿y si la IA se equivoca?»: se ve qué dijo y qué se corrigió.
2. **El estado se decide una vez.** ``draft`` → ``approved`` o
   ``discarded``, y desde ahí la fila no cambia. Como el encuentro firmado
   (US-24), lo garantiza un trigger de la base, no la vista.
3. **El texto lo valida el médico de la atención**, el de ``practitioner``.
   Otro médico del centro tiene el mismo permiso y no por eso firma lo que
   otro atendió.
"""

import uuid

from django.db import models
from django.db.models import Q


class AiGeneratedText(models.Model):

    class Kind(models.TextChoices):
        CONSULTATION_SUMMARY = "consultation_summary", "Resumen de la consulta"
        PREPARATION = "preparation", "Preparación para un estudio"
        HISTORY_SUMMARY = "history_summary", "Resumen del historial"

    class Status(models.TextChoices):
        DRAFT = "draft", "Pendiente de validación"
        APPROVED = "approved", "Aprobado"
        DISCARDED = "discarded", "Descartado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="ai_generated_texts",
    )
    kind = models.CharField("tipo", max_length=24, choices=Kind.choices)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT,
        related_name="ai_generated_texts",
    )
    # El médico que tiene que validarlo: el de la atención de la que sale.
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        related_name="ai_generated_texts",
    )
    # De qué sale. El resumen de la consulta sale de una atención; la
    # preparación, de una orden (y de su atención). El resumen del historial
    # no tiene una sola atención, por eso puede quedar vacío.
    encounter = models.ForeignKey(
        "encounters.Encounter", on_delete=models.PROTECT, null=True, blank=True,
        related_name="ai_generated_texts",
    )
    medical_order = models.ForeignKey(
        "encounters.MedicalOrder", on_delete=models.PROTECT, null=True, blank=True,
        related_name="ai_generated_texts",
    )

    generated_text = models.TextField("texto del modelo")
    final_text = models.TextField("texto validado", blank=True, default="")
    # Qué lo escribió: "gemini", con el nombre del modelo si se conoce.
    generated_by = models.CharField(max_length=60, blank=True, default="")

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT,
    )
    reviewed_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True,
        related_name="ai_texts_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "ai_generated_texts"
        verbose_name = "texto generado por IA"
        verbose_name_plural = "textos generados por IA"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["practitioner", "status"], name="ix_ai_text_bandeja"),
            models.Index(fields=["patient", "status"], name="ix_ai_text_paciente"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_ai_text_id_org",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=["consultation_summary", "preparation",
                                      "history_summary"]),
                name="ck_ai_text_kind",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["draft", "approved", "discarded"]),
                name="ck_ai_text_status",
            ),
            # El resumen de la consulta necesita su atención; la preparación,
            # su orden y su atención.
            models.CheckConstraint(
                condition=~Q(kind="consultation_summary") | Q(encounter__isnull=False),
                name="ck_ai_text_summary_encounter",
            ),
            models.CheckConstraint(
                condition=~Q(kind="preparation")
                | Q(medical_order__isnull=False, encounter__isnull=False),
                name="ck_ai_text_preparation_order",
            ),
            # Decidido es decidido por alguien y en un momento; aprobado es,
            # además, con un texto que el paciente pueda leer.
            models.CheckConstraint(
                condition=Q(status="draft")
                | Q(reviewed_by__isnull=False, reviewed_at__isnull=False),
                name="ck_ai_text_reviewed",
            ),
            models.CheckConstraint(
                condition=~Q(status="approved") | ~Q(final_text=""),
                name="ck_ai_text_approved_text",
            ),
            # Un solo resumen vivo por atención y una sola preparación viva por
            # orden. Uno descartado no cuenta: se puede volver a generar.
            models.UniqueConstraint(
                fields=["encounter"],
                condition=Q(kind="consultation_summary") & ~Q(status="discarded"),
                name="uq_ai_text_summary_vivo",
            ),
            models.UniqueConstraint(
                fields=["medical_order"],
                condition=Q(kind="preparation") & ~Q(status="discarded"),
                name="uq_ai_text_preparation_viva",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.get_status_display()}"

    @property
    def was_edited(self) -> bool:
        return bool(self.final_text) and self.final_text != self.generated_text
