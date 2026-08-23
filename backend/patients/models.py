"""Pacientes.

Un paciente NO es un usuario. Un paciente a cargo —un menor, un adulto mayor—
existe como paciente sin tener cuenta (US-07). Si los datos del paciente
vivieran dentro de ``users``, el Sprint 1 tendría que migrar datos ya
cargados. Ver decisión D-6.

En el Sprint 0 esta tabla es mínima: US-01 crea la cuenta y el paciente
titular. El Sprint 1 le agrega los antecedentes clínicos (US-08) y el resto de
los datos demográficos.
"""

import uuid

from django.db import models


class Patient(models.Model):
    """US-01 (titular) y US-07 (pacientes a cargo)."""

    class DocumentType(models.TextChoices):
        CI = "CI", "Cédula de identidad"
        PAS = "PAS", "Pasaporte"
        OTHER = "OTRO", "Otro"

    class Sex(models.TextChoices):
        MALE = "M", "Masculino"
        FEMALE = "F", "Femenino"
        OTHER = "X", "Otro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="patients",
    )
    # NULL = paciente a cargo, sin cuenta propia.
    user = models.OneToOneField(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="patient_profile",
    )
    # Titular que lo administra. NULL = se administra a sí mismo.
    guardian = models.ForeignKey(
        "self", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="dependents",
    )

    document_type = models.CharField(
        max_length=10, choices=DocumentType, default=DocumentType.CI,
    )
    # Nulable a propósito: un recién nacido todavía no tiene documento.
    document_number = models.CharField(max_length=20, null=True, blank=True)

    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    birth_date = models.DateField(null=True, blank=True)
    sex = models.CharField(max_length=1, choices=Sex, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patients"
        verbose_name = "paciente"
        verbose_name_plural = "pacientes"
        ordering = ["last_name", "first_name"]
        constraints = [
            # Unicidad sólo entre los que sí tienen documento: varios menores
            # sin CI en la misma organización no deben chocar entre sí.
            models.UniqueConstraint(
                fields=["organization", "document_type", "document_number"],
                condition=models.Q(document_number__isnull=False),
                name="uq_patient_document",
            ),
            models.CheckConstraint(
                condition=~models.Q(guardian=models.F("id")),
                name="ck_patient_guardian",
            ),
            # La necesita la clave foránea compuesta del titular: un paciente
            # no puede tener por titular a un paciente de otra organización.
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_patient_id_org",
            ),
            # Un paciente sin documento debe tener un titular que responda por él.
            models.CheckConstraint(
                condition=(
                    models.Q(document_number__isnull=False)
                    | models.Q(guardian__isnull=False)
                ),
                name="ck_patient_doc_or_guardian",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
