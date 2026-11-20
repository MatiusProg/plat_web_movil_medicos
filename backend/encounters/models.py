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

    # US-26: lo que se puede enmendar es más que las secciones de texto. La
    # receta y las órdenes de un encuentro firmado tampoco se tocan: se
    # corrigen con una enmienda, igual que el diagnóstico.
    AMENDABLE = {
        **SECTIONS,
        "prescription": "Receta",
        "orders": "Órdenes",
        # US-53: firmados, los signos vitales también se corrigen así.
        "vital_signs": "Signos vitales",
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
    section = models.CharField(max_length=20, choices=list(Encounter.AMENDABLE.items()))
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


# --------------------------------------------------------------------------
#  US-26 — Receta digital y órdenes
# --------------------------------------------------------------------------
#
# Las dos cuelgan del encuentro y comparten su regla: mientras el encuentro es
# borrador se agregan, se corrigen y se quitan; firmado, no se tocan. Igual
# que con el encuentro, eso no queda en manos de la vista: lo imponen los
# triggers de la migración 0006, que miran el estado del encuentro padre.
#
# No hay una tabla "receta" con sus renglones colgando: un encuentro tiene a
# lo sumo una receta, así que la receta *es* el conjunto de medicamentos del
# encuentro. Una tabla intermedia sólo agregaría un estado más que sincronizar.


class PrescriptionItem(models.Model):
    """Un medicamento recetado en una atención."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="prescription_items",
    )
    encounter = models.ForeignKey(
        Encounter, on_delete=models.PROTECT, related_name="prescription_items",
    )
    medication = models.CharField("medicamento", max_length=200)
    dose = models.CharField("dosis", max_length=80)
    frequency = models.CharField("frecuencia", max_length=80)
    duration = models.CharField("duración", max_length=80)
    instructions = models.CharField(
        "indicaciones de toma", max_length=300, blank=True, default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encounter_prescription_items"
        verbose_name = "medicamento recetado"
        verbose_name_plural = "medicamentos recetados"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.medication} {self.dose}"


class MedicalOrder(models.Model):
    """Una orden de laboratorio o de estudio emitida en una atención."""

    class Kind(models.TextChoices):
        LABORATORY = "laboratory", "Laboratorio"
        IMAGING = "imaging", "Imagenología"
        OTHER = "other", "Otro estudio"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="medical_orders",
    )
    encounter = models.ForeignKey(
        Encounter, on_delete=models.PROTECT, related_name="orders",
    )
    kind = models.CharField("tipo", max_length=12, choices=Kind.choices)
    description = models.CharField("estudio", max_length=300)
    notes = models.CharField("observaciones", max_length=300, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encounter_orders"
        verbose_name = "orden médica"
        verbose_name_plural = "órdenes médicas"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(kind__in=["laboratory", "imaging", "other"]),
                name="ck_order_kind",
            ),
        ]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.description}"


# --------------------------------------------------------------------------
#  US-48 — Calificación de la atención con estrellas
# --------------------------------------------------------------------------
#
# Es la única señal de *cómo* se atendió (US-29 mide cuánto). Va en su propia
# tabla porque el encuentro firmado no se toca: el trigger de la migración
# 0002 rechaza cualquier `UPDATE` sobre él.
#
# `practitioner` y `branch` repiten lo que dice el encuentro, igual que el
# encuentro repite lo de la ficha: el promedio por médico y por sede se cuenta
# sin pasar por él. `services.rate_encounter` los copia; nunca vienen del
# cliente.
#
# Lo que la base hace cumplir (migración 0007), y no sólo la vista:
# - una calificación por atención (`OneToOneField`);
# - sólo sobre una atención firmada;
# - de 1 a 5 estrellas y hasta 500 caracteres de comentario;
# - se corrige durante 7 días, después queda fija, y nunca se borra.


class EncounterRating(models.Model):
    """La calificación que el paciente deja sobre una atención firmada."""

    # Días durante los que el paciente puede cambiar lo que calificó.
    EDITABLE_DAYS = 7
    MAX_COMMENT = 500

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="encounter_ratings",
    )
    encounter = models.OneToOneField(
        Encounter, on_delete=models.PROTECT, related_name="rating",
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT,
        related_name="encounter_ratings",
    )
    practitioner = models.ForeignKey(
        "catalog.Practitioner", on_delete=models.PROTECT,
        related_name="encounter_ratings",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT,
        related_name="encounter_ratings",
    )
    # Quién calificó: el paciente o el titular de su dependiente.
    rated_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="encounter_ratings",
    )
    stars = models.PositiveSmallIntegerField("estrellas")
    comment = models.CharField(
        "comentario", max_length=MAX_COMMENT, blank=True, default="",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "encounter_ratings"
        verbose_name = "calificación de la atención"
        verbose_name_plural = "calificaciones de la atención"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(stars__gte=1, stars__lte=5),
                name="ck_rating_stars",
            ),
        ]
        indexes = [
            models.Index(fields=["practitioner", "-created_at"],
                         name="ix_rating_practitioner"),
        ]

    def __str__(self):
        return f"{self.encounter_id} · {self.stars}★"

    @property
    def editable_until(self):
        import datetime as dt
        return self.created_at + dt.timedelta(days=self.EDITABLE_DAYS)


# --------------------------------------------------------------------------
#  US-49 — Las tomas de los medicamentos de la receta
# --------------------------------------------------------------------------
#
# Los avisos son **locales** del teléfono: no dependen del servidor ni de la
# conexión. Lo que sí llega al servidor es cada toma que el paciente marca,
# para que el médico vea el cumplimiento del tratamiento («12 de 15 tomas»).
#
# `dose_number` es el número de toma dentro del horario que sale de
# `frequency.interpretar` (1 a `total_doses`). Es lo que hace imposible marcar
# dos veces la misma toma: `(prescription_item, dose_number)` es único, aunque
# el teléfono reintente después de perder la conexión.
#
# Una toma marcada no se cambia ni se borra (migración 0010): es un registro
# de lo que el paciente dijo, igual que un mensaje del chat.


class MedicationIntake(models.Model):
    """Una toma de un medicamento recetado, marcada por el paciente."""

    class Status(models.TextChoices):
        TAKEN = "taken", "Tomada"
        SKIPPED = "skipped", "Salteada"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="medication_intakes",
    )
    prescription_item = models.ForeignKey(
        PrescriptionItem, on_delete=models.PROTECT, related_name="intakes",
    )
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.PROTECT,
        related_name="medication_intakes",
    )
    dose_number = models.PositiveSmallIntegerField("número de toma")
    status = models.CharField(max_length=8, choices=Status.choices)
    # Cuándo tocaba según el horario que eligió el paciente. Puede ser nulo:
    # la toma se marca igual aunque el teléfono no lo mande.
    scheduled_at = models.DateTimeField(null=True, blank=True)
    # El paciente o el titular de su dependiente.
    recorded_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT,
        related_name="medication_intakes",
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encounter_medication_intakes"
        verbose_name = "toma de medicamento"
        verbose_name_plural = "tomas de medicamentos"
        ordering = ["prescription_item", "dose_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["prescription_item", "dose_number"],
                name="uq_intake_item_dose",
            ),
            models.CheckConstraint(
                condition=models.Q(status__in=["taken", "skipped"]),
                name="ck_intake_status",
            ),
            models.CheckConstraint(
                condition=models.Q(dose_number__gte=1),
                name="ck_intake_dose_number",
            ),
        ]

    def __str__(self):
        return f"{self.prescription_item_id} · toma {self.dose_number} · {self.status}"

# --------------------------------------------------------------------------
#  US-53 — Signos vitales
# --------------------------------------------------------------------------
#
# Hasta acá la historia no tenía un solo número: si se anotaba la presión,
# quedaba como texto en «Evolución» y no se podía ver su tendencia.
#
# Uno a uno con el encuentro, en su propia tabla, como la receta: se cargan
# mientras es borrador y se firman con él. Lo que la base hace cumplir
# (migraciones 0011 y 0012), y no sólo la vista:
# - todos los campos son opcionales, pero lo **imposible** no se guarda: una
#   temperatura de 60 °C o una talla de 3 m son un error de tipeo, no un dato;
# - la sistólica es mayor que la diastólica;
# - firmado el encuentro, no se tocan (trigger, igual que la receta).
#
# Lo **anormal** no se bloquea: se marca (`alerts`). Un paciente con 39 °C
# existe, y el médico tiene que poder registrarlo.


# Lo posible: fuera de esto es un error de tipeo. (mínimo, máximo)
VITAL_LIMITS = {
    "systolic": (50, 300),
    "diastolic": (20, 200),
    "heart_rate": (20, 250),
    "temperature": (30, 45),
    "spo2": (50, 100),
    "weight_kg": (0.5, 400),
    "height_cm": (30, 250),
    "glucose": (10, 1000),
}


class VitalSigns(models.Model):
    """Los signos vitales tomados en una atención."""

    LIMITS = VITAL_LIMITS
    FIELDS = tuple(VITAL_LIMITS)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="vital_signs",
    )
    encounter = models.OneToOneField(
        Encounter, on_delete=models.PROTECT, related_name="vital_signs",
    )
    systolic = models.PositiveSmallIntegerField("presión sistólica (mmHg)", null=True, blank=True)
    diastolic = models.PositiveSmallIntegerField("presión diastólica (mmHg)", null=True, blank=True)
    heart_rate = models.PositiveSmallIntegerField("frecuencia cardíaca (lpm)", null=True, blank=True)
    temperature = models.DecimalField("temperatura (°C)", max_digits=3, decimal_places=1,
                                      null=True, blank=True)
    spo2 = models.PositiveSmallIntegerField("saturación de oxígeno (%)", null=True, blank=True)
    weight_kg = models.DecimalField("peso (kg)", max_digits=4, decimal_places=1,
                                    null=True, blank=True)
    height_cm = models.DecimalField("talla (cm)", max_digits=4, decimal_places=1,
                                    null=True, blank=True)
    glucose = models.PositiveSmallIntegerField("glucosa (mg/dL)", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "encounter_vital_signs"
        verbose_name = "signos vitales"
        verbose_name_plural = "signos vitales"
        constraints = [
            *[
                models.CheckConstraint(
                    condition=models.Q(**{f"{campo}__isnull": True})
                    | models.Q(**{f"{campo}__gte": minimo, f"{campo}__lte": maximo}),
                    name=f"ck_vitals_{campo}_posible",
                )
                for campo, (minimo, maximo) in VITAL_LIMITS.items()
            ],
            models.CheckConstraint(
                condition=models.Q(systolic__isnull=True) | models.Q(diastolic__isnull=True)
                | models.Q(systolic__gt=models.F("diastolic")),
                name="ck_vitals_sistolica_mayor",
            ),
        ]

    def __str__(self):
        return f"Signos vitales de {self.encounter_id}"

    @property
    def bmi(self):
        """El IMC, con un decimal. Sin peso o sin talla no se calcula."""
        if self.weight_kg is None or self.height_cm is None:
            return None
        metros = float(self.height_cm) / 100
        return round(float(self.weight_kg) / (metros * metros), 1)

    @property
    def alerts(self) -> dict[str, str]:
        """Lo anormal, para marcarlo sin bloquearlo. Clave → «Alta»/«Baja»."""
        alertas = {}
        if (self.systolic is not None and self.systolic >= 140) or (
            self.diastolic is not None and self.diastolic >= 90
        ):
            alertas["blood_pressure"] = "Alta"
        if self.spo2 is not None and self.spo2 < 92:
            alertas["spo2"] = "Baja"
        if self.temperature is not None and self.temperature >= 38:
            alertas["temperature"] = "Alta"
        return alertas

    @property
    def is_empty(self) -> bool:
        return all(getattr(self, campo) is None for campo in self.FIELDS)
