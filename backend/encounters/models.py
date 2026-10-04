"""US-24 — El encuentro clínico: lo que el médico registra al atender.

Tres decisiones del reparto, y cómo se hacen cumplir:

1. **El encuentro cuelga de la ficha** (US-17), no del paciente suelto. Es
   lo que después permite cruzar la atención con la sucursal, la
   especialidad y la inasistencia. Una ficha tiene a lo sumo un encuentro:
   `OneToOneField`.

2. **Se cierra, no se borra.** Mientras es borrador el médico lo edita; al
   firmarlo queda fijo, y una corrección posterior es una *enmienda* que
   referencia al original y lleva su propio autor y fecha. Esto no queda
   librado a que la vista se acuerde: lo impone la base con dos triggers
   (migración 0002) que rechazan modificar un encuentro firmado, borrar
   cualquier encuentro y tocar una enmienda ya escrita.

3. **Toda apertura va a la bitácora** de US-06 (`record.read`). Eso vive en
   las vistas, que es donde se sabe quién abrió qué.

`patient`, `practitioner` y `branch` repiten lo que ya dice la ficha. Es
deliberado: el historial longitudinal de US-25 lista encuentros de un
paciente en todas las sucursales, y esa consulta no tiene que pasar por la
ficha para saber de dónde es cada uno. Las tres van con clave compuesta con la
organización, y `services.open_encounter` las copia de la ficha: nunca vienen
del cliente.
"""

import uuid

from django.db import models


class Encounter(models.Model):
    """La atención registrada sobre una ficha."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        SIGNED = "signed", "Firmado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="encounters",
    )
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.PROTECT,
        related_name="encounter",
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="encounters",
    )
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        related_name="encounters",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT, related_name="encounters",
    )

    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT,
    )

    # Las cinco secciones de la historia, en el orden en que se escriben.
    reason = models.TextField("motivo de consulta", blank=True, default="")
    evolution = models.TextField("evolución", blank=True, default="")
    diagnosis = models.TextField("diagnóstico", blank=True, default="")
    indications = models.TextField("indicaciones", blank=True, default="")
    treatment = models.TextField("tratamiento", blank=True, default="")

    signed_at = models.DateTimeField(null=True, blank=True)
    signed_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True,
        related_name="signed_encounters",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Las secciones que se pueden enmendar, con su nombre para mostrar.
    SECTIONS = {
        "reason": "Motivo de consulta",
        "evolution": "Evolución",
        "diagnosis": "Diagnóstico",
        "indications": "Indicaciones",
        "treatment": "Tratamiento",
    }

    class Meta:
        db_table = "encounters"
        verbose_name = "encuentro clínico"
        verbose_name_plural = "encuentros clínicos"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_encounter_id_org",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["draft", "signed"]),
                name="ck_encounter_status",
            ),
            # Firmado si y sólo si tiene fecha y autor de la firma.
            models.CheckConstraint(
                condition=(
                    models.Q(status="draft", signed_at__isnull=True,
                             signed_by__isnull=True)
                    | models.Q(status="signed", signed_at__isnull=False,
                               signed_by__isnull=False)
                ),
                name="ck_encounter_signature",
            ),
        ]
        indexes = [
            # El historial de US-25: los encuentros de un paciente, por fecha.
            models.Index(fields=["patient", "-created_at"],
                         name="ix_encounter_patient"),
        ]

    def __str__(self):
        return f"{self.patient_id} · {self.get_status_display()}"

    @property
    def is_signed(self) -> bool:
        return self.status == self.Status.SIGNED


class EncounterAmendment(models.Model):
    """Una corrección a un encuentro ya firmado.

    No reemplaza el texto original: se muestra junto a él, con quién la hizo y
    cuándo. Es lo que separa una historia clínica de un documento editable.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="encounter_amendments",
    )
    encounter = models.ForeignKey(
        Encounter, on_delete=models.PROTECT, related_name="amendments",
    )
    section = models.CharField(max_length=20, choices=list(Encounter.SECTIONS.items()))
    text = models.TextField()
    author = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="encounter_amendments",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encounter_amendments"
        verbose_name = "enmienda"
        verbose_name_plural = "enmiendas"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.encounter_id} · {self.section}"
