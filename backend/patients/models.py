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

    class Relationship(models.TextChoices):
        """Parentesco con el titular. US-07 (a).

        Es una lista cerrada y no texto libre porque el Sprint 4 reporta sobre
        ella —cuántas fichas se reservan para terceros y de qué vínculo—, y
        sobre texto libre eso no se puede agrupar. ``OTHER`` está para que la
        lista no obligue a mentir, que es lo que pasa cuando el caso real no
        figura.
        """

        CHILD = "child", "Hijo/a"
        SPOUSE = "spouse", "Cónyuge"
        PARENT = "parent", "Padre/Madre"
        SIBLING = "sibling", "Hermano/a"
        GRANDPARENT = "grandparent", "Abuelo/a"
        GRANDCHILD = "grandchild", "Nieto/a"
        WARD = "ward", "Bajo tutela"
        OTHER = "other", "Otro"

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
    # Qué es del titular. Vacío cuando no hay titular, y obligatorio cuando lo
    # hay: lo garantiza `ck_patient_relationship`. US-07 (a).
    relationship = models.CharField(
        max_length=20, choices=Relationship, blank=True, default="",
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
            # US-07 (a): un dependiente sin parentesco no dice nada, y un
            # parentesco sin titular no significa nada. Los dos van juntos o no
            # va ninguno.
            models.CheckConstraint(
                condition=(
                    models.Q(guardian__isnull=True, relationship="")
                    | models.Q(guardian__isnull=False)
                    & ~models.Q(relationship="")
                ),
                name="ck_patient_relationship",
            ),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class PatientHistoryEntry(models.Model):
    """US-08 — Un antecedente declarado por el paciente.

    **Declarado, no diagnosticado.** Es la distinción que sostiene toda la
    historia: lo que hay acá lo escribió el paciente o su titular desde el
    teléfono, y no equivale a un diagnóstico clínico. El diagnóstico lo registra
    el médico en el Sprint 3, en la app ``records``, en otra tabla. Mezclarlos
    haría que "el paciente dice que es alérgico a la penicilina" y "el médico
    diagnosticó alergia a la penicilina" se leyeran igual, y no valen lo mismo.

    Por eso ``source`` existe desde ahora aunque en el Sprint 1 tenga un solo
    valor posible: la columna que distingue el origen tiene que estar el día que
    aparezca el segundo, o habrá que salir a adivinar cuál era cuál.

    Los tres tipos van en una sola tabla y no en tres. Una alergia, una
    condición crónica y una medicación habitual tienen los mismos campos, se
    listan juntas, se dan de baja igual y el módulo de atención las lee de una
    sola vez; tres tablas serían tres consultas para dibujar una pantalla.
    """

    class Kind(models.TextChoices):
        ALLERGY = "allergy", "Alergia"
        CONDITION = "condition", "Condición crónica"
        MEDICATION = "medication", "Medicación habitual"

    class Severity(models.TextChoices):
        """Sólo para las alergias. Punto (b).

        Distinguir una intolerancia leve de una reacción anafiláctica es la
        diferencia entre una nota al margen y algo que el profesional tiene que
        ver antes de recetar.
        """

        MILD = "mild", "Leve"
        MODERATE = "moderate", "Moderada"
        SEVERE = "severe", "Grave"
        ANAPHYLACTIC = "anaphylactic", "Anafiláctica"

    class Source(models.TextChoices):
        SELF_REPORTED = "self_reported", "Declarado por el paciente"
        # Lo escribe el Sprint 3. Declarado acá para que la columna nazca con
        # los dos valores y no haya que migrar datos cuando llegue.
        PRACTITIONER = "practitioner", "Registrado por un profesional"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="patient_history_entries",
    )
    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name="history_entries",
    )

    kind = models.CharField(max_length=20, choices=Kind)
    description = models.CharField(max_length=200)
    # Vacío salvo en las alergias. Lo hace cumplir `ck_history_severity`.
    severity = models.CharField(
        max_length=20, choices=Severity, blank=True, default="",
    )
    source = models.CharField(
        max_length=20, choices=Source, default=Source.SELF_REPORTED,
    )

    # Quién lo cargó: el propio paciente o el titular que lo tiene a cargo.
    # NULL si esa cuenta se dio de baja; el antecedente no se va con ella.
    declared_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="declared_history_entries",
    )
    # Punto (a): la fecha de registro. Separada de `created_at` porque es un
    # dato clínico que se muestra —"declarado en marzo de 2024"— y no una marca
    # técnica de la fila.
    recorded_at = models.DateField(auto_now_add=True)

    # Punto (e): baja lógica. Lo declarado no se pierde, deja de estar vigente.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "patient_history_entries"
        verbose_name = "antecedente"
        verbose_name_plural = "antecedentes"
        ordering = ["kind", "-recorded_at"]
        indexes = [
            models.Index(fields=["patient", "is_active"],
                         name="ix_history_patient"),
        ]
        constraints = [
            # La severidad es de las alergias y de nadie más: una medicación
            # "grave" no significa nada, y dejarla entrar haría que la pantalla
            # tuviera que decidir cuándo mostrarla.
            models.CheckConstraint(
                condition=(
                    models.Q(kind="allergy")
                    | models.Q(severity="")
                ),
                name="ck_history_severity",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.description}"
