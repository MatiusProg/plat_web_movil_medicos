"""US-47 — Chat entre el paciente atendido y el médico que lo atendió.

Lo pidió la ingeniera el 12/11/26: *«si un paciente es atendido, debe tener la
opción de tener un chat con su doctor, para consultas sobre medicamentos u
otras similares»*.

**El chat nace de una atención firmada, no de una persona.** Hay una
conversación por atención (``encounter_threads``), entre el paciente de esa
atención —o el titular, si es un dependiente— y el médico de esa atención.
No es un canal para pedir consultas nuevas: es el seguimiento de una que ya
pasó, y por eso la conversación muestra la receta y las órdenes de esa
atención.

Tres reglas que sostiene la base y no sólo la vista:

1. **Un mensaje no se edita ni se borra** (trigger): queda como parte del
   registro de la atención, con su autor y su hora.
2. **Una conversación no se borra**, y lo único que cambia de ella es quién
   leyó hasta cuándo y si el médico la cerró.
3. **RLS y claves compuestas con la organización**, como toda tabla del
   inquilino.
"""

import uuid

from django.db import models
from django.db.models import Q


class EncounterThread(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="encounter_threads",
    )
    encounter = models.OneToOneField(
        "encounters.Encounter", on_delete=models.PROTECT, related_name="thread",
    )
    # Copiados de la atención al crear la conversación, para filtrar la
    # bandeja del médico y la lista del paciente sin pasar por la atención.
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT, related_name="encounter_threads",
    )
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        related_name="encounter_threads",
    )
    # Hasta cuándo leyó cada lado: de acá salen los «sin leer».
    patient_read_at = models.DateTimeField(null=True, blank=True)
    practitioner_read_at = models.DateTimeField(null=True, blank=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    # El médico puede cerrarla antes de que venza la ventana.
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, blank=True,
        related_name="closed_threads",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encounter_threads"
        verbose_name = "conversación"
        verbose_name_plural = "conversaciones"
        indexes = [
            models.Index(fields=["practitioner", "last_message_at"],
                         name="ix_thread_bandeja"),
            models.Index(fields=["patient"], name="ix_thread_paciente"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["id", "organization"], name="uq_thread_id_org"),
            models.CheckConstraint(
                condition=Q(closed_at__isnull=True, closed_by__isnull=True)
                | Q(closed_at__isnull=False, closed_by__isnull=False),
                name="ck_thread_closed",
            ),
        ]

    def __str__(self):
        return f"Conversación de la atención {self.encounter_id}"


class EncounterMessage(models.Model):

    class Side(models.TextChoices):
        PATIENT = "patient", "Paciente"
        PRACTITIONER = "practitioner", "Médico"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="encounter_messages",
    )
    thread = models.ForeignKey(
        EncounterThread, on_delete=models.PROTECT, related_name="messages",
    )
    author = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="encounter_messages",
    )
    side = models.CharField("lado", max_length=12, choices=Side.choices)
    body = models.TextField("mensaje")
    # La barrera de US-34 disparó con este mensaje: el paciente vio primero la
    # derivación a emergencias y el médico lo ve marcado. Se guarda la marca,
    # no las frases que coincidieron.
    flagged_emergency = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encounter_messages"
        verbose_name = "mensaje"
        verbose_name_plural = "mensajes"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["thread", "created_at"], name="ix_message_thread")]
        constraints = [
            models.CheckConstraint(
                condition=Q(side__in=["patient", "practitioner"]),
                name="ck_message_side",
            ),
            models.CheckConstraint(
                condition=~Q(body=""), name="ck_message_body",
            ),
            models.CheckConstraint(
                condition=Q(flagged_emergency=False) | Q(side="patient"),
                name="ck_message_flag_patient",
            ),
        ]

    def __str__(self):
        return f"{self.get_side_display()} · {self.created_at:%d/%m %H:%M}"
