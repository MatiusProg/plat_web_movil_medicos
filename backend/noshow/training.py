"""US-35 — Entrenar el modelo de inasistencia de una organización.

**Un modelo simple y explicable**: regresión logística sobre las variables de
``features.py``, entrenada con las fichas de **una sola organización**, dentro
de su ``tenant_context`` (regla 16). Se eligió regresión logística y no un
árbol ni nada más complejo porque cada coeficiente se puede decir en una frase
(«cada día de anticipación suma tanto») y porque con unos cientos de fichas por
centro un modelo más flexible sólo memoriza.

**Cómo se mide, y contra qué.**

- *Corte temporal:* el 80 % más antiguo entrena y el 20 % más reciente mide.
  Un corte al azar dejaría que el modelo «vea el futuro»: mediría con fichas
  de la misma semana que aprendió.
- *Línea base:* «predecir siempre que asiste». Con una tasa de ausencias del
  12 % ya acierta casi el 88 %, así que la exactitud no sirve para juzgar al
  modelo. Se reportan el **Brier** (error de las probabilidades) contra el de
  predecir siempre la tasa base, el **AUC** y, para el nivel alto, **recall** y
  **precisión**. Si el modelo no le gana a la base, se dice: la versión queda
  ``rejected``, nunca se usa y la pantalla lo explica.

**Los umbrales son relativos a la tasa base de cada organización**: *alto* desde
2 veces la tasa base y *medio* desde 1,2 veces. Un corte fijo (0,4, por
ejemplo) casi nunca marcaría «alto» en un centro con 10 % de ausencias.

**Mínimos.** Con menos de ``MIN_LABELED`` fichas o ``MIN_ABSENT`` ausencias no
se entrena: no hay de dónde aprender y una métrica sobre eso sería ruido. No
se crea versión y se dice «sin datos suficientes».

**Quién más lo usa.** ``train_for`` es la función que reutiliza el
reentrenamiento de US-38: crea la versión y, si ya hay una vigente, la deja como
*candidata* sin reemplazarla. Compararla y promoverla (``promote``) es de esa
historia.

scikit-learn se importa **dentro** de la función que lo usa, como las demás
librerías pesadas del proyecto: un despliegue al que le falte falla sólo acá y
no al arrancar el proceso.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.db.models import Count, Max
from django.utils import timezone

from appointments.kpis import debian_atenderse_q, inasistencia_q
from appointments.models import Appointment
from tenancy.context import tenant_context

from . import features
from .models import ModelVersion
from .scoring import predict_proba

MIN_LABELED = 200
MIN_ABSENT = 20
TEST_FRACTION = 0.2
HIGH_FACTOR = 2.0
MEDIUM_FACTOR = 1.2
# Un umbral por encima de esto no marcaría nunca a nadie.
MAX_MEDIUM_CUTOFF = 0.95
MAX_HIGH_CUTOFF = 0.98


@dataclass
class TrainResult:
    version: ModelVersion | None
    reason: str | None          # None, o "sin_datos"
    message: str
    labeled: int = 0
    absent: int = 0


def data_status(organization, now=None) -> tuple[int, int]:
    """Cuántas fichas ya se pueden etiquetar y cuántas de ellas fueron ausencias.

    Supone el contexto de la organización.
    """
    now = now or timezone.now()
    cuenta = (
        Appointment.objects.filter(organization=organization)
        .filter(debian_atenderse_q(now))
        .aggregate(n=Count("id"), ausentes=Count("id", filter=inasistencia_q(now)))
    )
    return cuenta["n"], cuenta["ausentes"]


def _insufficient(message, labeled, absent) -> TrainResult:
    return TrainResult(None, "sin_datos", message, labeled, absent)


def train_for(organization, now=None) -> TrainResult:
    """Entrena y guarda una versión nueva. Abre el contexto de la organización."""
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    from sklearn.preprocessing import StandardScaler

    now = now or timezone.now()
    with tenant_context(organization.id):
        fichas = list(
            Appointment.objects.filter(organization=organization)
            .filter(debian_atenderse_q(now))
            .order_by("starts_at", "id")
        )
        total = len(fichas)
        ausentes = sum(features.label_of(f) for f in fichas)
        if total < MIN_LABELED or ausentes < MIN_ABSENT:
            return _insufficient(
                f"Sin datos suficientes: hay {total} fichas con desenlace y {ausentes} "
                f"ausencias; se necesitan al menos {MIN_LABELED} y {MIN_ABSENT}.",
                total, ausentes,
            )

        filas = features.build_rows(organization, fichas, now)
        for fila, ficha in zip(filas, fichas):
            fila.label = features.label_of(ficha)

        corte = int(total * (1 - TEST_FRACTION))
        entrenamiento, prueba = filas[:corte], filas[corte:]
        y_train = np.array([f.label for f in entrenamiento])
        y_test = np.array([f.label for f in prueba])
        if y_train.sum() == 0 or y_test.sum() == 0 or y_test.sum() == len(y_test):
            return _insufficient(
                "Sin datos suficientes: las ausencias no alcanzan para entrenar y "
                "medir con un corte en el tiempo.", total, ausentes,
            )

        x_train = np.array([f.values for f in entrenamiento])
        escalador = StandardScaler().fit(x_train)
        regresion = LogisticRegression(C=1.0, max_iter=1000).fit(
            escalador.transform(x_train), y_train,
        )
        params = {
            "features": features.FEATURE_NAMES,
            "coef": [float(c) for c in regresion.coef_[0]],
            "intercept": float(regresion.intercept_[0]),
            "mean": [float(m) for m in escalador.mean_],
            "scale": [float(s) for s in escalador.scale_],
        }

        # Se mide con la misma función que usa el sistema al predecir, no con
        # `regresion.predict_proba`: lo que se mide es lo que se va a usar.
        probabilidades = np.array([predict_proba(params, f.values) for f in prueba])
        base = float(y_train.mean())
        medio = min(MEDIUM_FACTOR * base, MAX_MEDIUM_CUTOFF)
        alto = min(max(HIGH_FACTOR * base, medio + 0.01), MAX_HIGH_CUTOFF)
        cortes = {"medium": medio, "high": alto}

        brier = float(np.mean((probabilidades - y_test) ** 2))
        brier_base = float(np.mean((base - y_test) ** 2))
        auc = float(roc_auc_score(y_test, probabilidades))
        marcadas = probabilidades >= alto
        aciertos = int((marcadas & (y_test == 1)).sum())
        metricas = {
            "auc": auc,
            "brier": brier,
            "brier_baseline": brier_base,
            # «Siempre asiste»: la línea base del reparto. Se muestra, pero no
            # decide: con pocas ausencias casi siempre acierta mucho.
            "accuracy_baseline": float(1 - y_test.mean()),
            "absent_rate_test": float(y_test.mean()),
            "recall_high": aciertos / int(y_test.sum()),
            "precision_high": (aciertos / int(marcadas.sum())) if marcadas.any() else None,
            "flagged_high": int(marcadas.sum()),
            "cutoffs": cortes,
        }
        supera = brier < brier_base and auc > 0.5

        version = _save_version(
            organization, params, metricas, supera,
            n_train=len(entrenamiento), n_test=len(prueba), base_rate=base, now=now,
        )
        if version.status == ModelVersion.Status.REJECTED:
            mensaje = (
                f"El modelo v{version.version} no supera la línea base "
                f"(Brier {brier:.3f} contra {brier_base:.3f}, AUC {auc:.2f}): no se usa."
            )
        elif version.status == ModelVersion.Status.CANDIDATE:
            mensaje = (
                f"El modelo v{version.version} supera la línea base y queda como candidato: "
                "ya hay uno vigente y reemplazarlo lo decide el reentrenamiento (US-38)."
            )
        else:
            mensaje = (
                f"El modelo v{version.version} supera la línea base "
                f"(Brier {brier:.3f} contra {brier_base:.3f}, AUC {auc:.2f}) y quedó vigente."
            )
        return TrainResult(version, None, mensaje, total, ausentes)


def _save_version(organization, params, metricas, supera, *, n_train, n_test,
                  base_rate, now) -> ModelVersion:
    with transaction.atomic():
        ultima = (
            ModelVersion.objects
            .filter(organization=organization, kind=ModelVersion.Kind.NOSHOW)
            .aggregate(m=Max("version"))["m"] or 0
        )
        hay_vigente = ModelVersion.objects.filter(
            organization=organization, kind=ModelVersion.Kind.NOSHOW,
            status=ModelVersion.Status.ACTIVE,
        ).exists()
        if not supera:
            estado = ModelVersion.Status.REJECTED
        elif hay_vigente:
            estado = ModelVersion.Status.CANDIDATE
        else:
            estado = ModelVersion.Status.ACTIVE
        return ModelVersion.objects.create(
            organization=organization, kind=ModelVersion.Kind.NOSHOW,
            version=ultima + 1, status=estado, trained_at=now,
            n_train=n_train, n_test=n_test, base_rate=base_rate,
            params=params, metrics=metricas, beats_baseline=supera,
        )


def promote(version: ModelVersion) -> ModelVersion:
    """Hace vigente a una versión candidata y retira a la que lo era.

    Un modelo que no le ganó a la línea base no se promueve nunca. La decisión
    de *cuándo* promover es de US-38; acá sólo está el mecanismo, y es seguro:
    en una sola transacción, y con el índice único parcial a favor (retira
    primero, activa después).
    """
    with tenant_context(version.organization_id), transaction.atomic():
        fila = ModelVersion.objects.select_for_update().get(pk=version.pk)
        if not fila.beats_baseline:
            raise ValueError("Un modelo que no supera la línea base no se promueve.")
        ModelVersion.objects.filter(
            organization_id=fila.organization_id, kind=fila.kind,
            status=ModelVersion.Status.ACTIVE,
        ).exclude(pk=fila.pk).update(status=ModelVersion.Status.RETIRED)
        fila.status = ModelVersion.Status.ACTIVE
        fila.save(update_fields=["status", "updated_at"])
    return fila
