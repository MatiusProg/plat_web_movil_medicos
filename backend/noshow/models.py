"""US-35 — El modelo de inasistencia y lo que predice, por organización.

Dos tablas, las que el modelo de datos del Sprint 0 reservó para el Sprint 4:

- ``model_versions``: cada modelo que se entrenó, con sus coeficientes **en
  JSON** y las métricas con las que se lo midió. No se guarda ningún objeto de
  Python serializado (pickle): el disco de Railway es efímero, y leer de la
  base un objeto serializado es ejecutar lo que alguien haya escrito ahí. Con
  los coeficientes alcanza: predecir es una suma y una función logística
  (``scoring.predict_proba``).
- ``noshow_predictions``: la predicción vigente de cada ficha futura. Una fila
  por ficha; al recalcular se actualiza. Las filas de fichas que ya pasaron
  **no se borran**: son lo que permite medir, después, cuánto acertó el modelo.

**Un modelo por organización** (regla 16 del Sprint 4): se entrena y se usa
dentro de su ``tenant_context``. Un modelo entrenado con las fichas de todos
los centros mezclaría datos de clientes distintos.

**Quién más usa esto.** US-36 (recordatorio reforzado) lee
``NoShowPrediction.level``; US-38 (reentrenamiento) escribe versiones nuevas en
``ModelVersion`` y decide cuál queda vigente.
"""

import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class ModelVersion(models.Model):

    class Kind(models.TextChoices):
        NOSHOW = "noshow", "Inasistencia"

    class Status(models.TextChoices):
        # El que usa el sistema. Una sola por (organización, tipo).
        ACTIVE = "active", "Vigente"
        # Entrenado y bueno, pero hay otro vigente: lo decide US-38.
        CANDIDATE = "candidate", "Candidato"
        # No le ganó a la línea base: nunca se usó.
        REJECTED = "rejected", "Rechazado"
        # Fue el vigente y lo reemplazó otro.
        RETIRED = "retired", "Retirado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="model_versions",
    )
    kind = models.CharField("tipo", max_length=16, choices=Kind.choices)
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices)
    trained_at = models.DateTimeField(default=timezone.now)

    # Con cuántas fichas se entrenó y con cuántas se midió (corte temporal: se
    # entrena con lo más antiguo y se mide con lo más reciente).
    n_train = models.PositiveIntegerField()
    n_test = models.PositiveIntegerField()
    # Fracción de ausentes en lo que se entrenó. De ella salen los umbrales.
    base_rate = models.FloatField()

    # Nombres de las variables, coeficientes, intercepto, media y escala.
    params = models.JSONField(default=dict)
    # AUC, Brier, Brier de la línea base, exactitud de «siempre asiste»,
    # recall y precisión del nivel alto, y los umbrales.
    metrics = models.JSONField(default=dict)
    # ¿Le ganó a la línea base? Si no, queda `rejected` y se dice.
    beats_baseline = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "model_versions"
        verbose_name = "versión de modelo"
        verbose_name_plural = "versiones de modelo"
        ordering = ["-version"]
        constraints = [
            # Para las claves foráneas compuestas `(model_version_id, organization_id)`.
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_model_version_id_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "kind", "version"],
                name="uq_model_version_numero",
            ),
            # Una sola versión vigente por organización y tipo.
            models.UniqueConstraint(
                fields=["organization", "kind"],
                condition=Q(status="active"),
                name="uq_model_version_vigente",
            ),
            models.CheckConstraint(
                condition=Q(kind__in=["noshow"]), name="ck_model_version_kind",
            ),
            models.CheckConstraint(
                condition=Q(status__in=["active", "candidate", "rejected", "retired"]),
                name="ck_model_version_status",
            ),
            # Un modelo que no le ganó a la línea base nunca es el vigente.
            models.CheckConstraint(
                condition=~Q(status__in=["active", "candidate"]) | Q(beats_baseline=True),
                name="ck_model_version_supera_base",
            ),
        ]

    def __str__(self):
        return f"{self.kind} v{self.version} · {self.get_status_display()}"


class NoShowPrediction(models.Model):

    class Level(models.TextChoices):
        LOW = "low", "Riesgo bajo"
        MEDIUM = "medium", "Riesgo medio"
        HIGH = "high", "Riesgo alto"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="noshow_predictions",
    )
    # Derivada de la ficha: si la ficha desapareciera, la predicción también.
    appointment = models.OneToOneField(
        "appointments.Appointment", on_delete=models.CASCADE,
        related_name="noshow_prediction",
    )
    model_version = models.ForeignKey(
        ModelVersion, on_delete=models.PROTECT, related_name="predictions",
    )
    probability = models.FloatField()
    level = models.CharField(max_length=6, choices=Level.choices)
    # Hasta tres razones, ya en español: [{key, label, direction}].
    factors = models.JSONField(default=list)
    computed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "noshow_predictions"
        verbose_name = "predicción de inasistencia"
        verbose_name_plural = "predicciones de inasistencia"
        indexes = [
            models.Index(fields=["organization", "level"], name="ix_noshow_pred_nivel"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(level__in=["low", "medium", "high"]),
                name="ck_noshow_pred_level",
            ),
            models.CheckConstraint(
                condition=Q(probability__gte=0, probability__lte=1),
                name="ck_noshow_pred_probability",
            ),
        ]

    def __str__(self):
        return f"{self.appointment_id} · {self.level} · {self.probability:.2f}"
