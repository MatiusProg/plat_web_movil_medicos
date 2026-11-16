"""US-35 — Predecir: del modelo guardado a la predicción de cada ficha futura.

Predecir es aritmética. El modelo se guarda como coeficientes en JSON
(``ModelVersion.params``), así que acá no hace falta scikit-learn ni ningún
objeto serializado: una suma ponderada y una función logística.

**Una organización a la vez, cada una en su ``tenant_context``** y sólo con su
modelo vigente (regla 16 del Sprint 4). Mismo esquema que
``appointments/reminders.py``: ``run_due`` recorre las organizaciones activas y
una que falla no frena a las demás.

**Sin modelo vigente no hay predicción.** No se rellena con un valor por
omisión: una ficha sin calificar es mejor que una calificada con nada.

**Qué se recalcula.** Las fichas ``pending_payment`` y ``confirmed`` de los
próximos ``HORIZON_DAYS`` días. Se recalcula porque las variables cambian (una
ficha que se paga cambia de riesgo). Las predicciones de fichas que ya pasaron
o se cancelaron se **dejan como están**: son lo que permite medir, después,
cuánto acertó el modelo.
"""

from __future__ import annotations

import datetime as dt
import logging
import math

from django.utils import timezone

from appointments.models import Appointment
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization
from tenancy.plans import current_plan

from . import features
from .models import ModelVersion, NoShowPrediction

logger = logging.getLogger(__name__)

FEATURE = "noshow_prediction"
HORIZON_DAYS = 60
MAX_FACTORS = 3
# Una razón que casi no pesa no se muestra.
MIN_FACTOR_WEIGHT = 0.05


def predict_proba(params: dict, values: list[float]) -> float:
    """Probabilidad de ausencia con los coeficientes guardados."""
    z = float(params["intercept"])
    for coef, media, escala, valor in zip(
        params["coef"], params["mean"], params["scale"], values,
    ):
        z += coef * (valor - media) / (escala or 1.0)
    # exp(-z) se desborda con z muy negativo; la logística ya es 0 o 1 ahí.
    if z >= 0:
        return 1.0 / (1.0 + math.exp(-z))
    e = math.exp(z)
    return e / (1.0 + e)


def level_for(probability: float, cutoffs: dict) -> str:
    if probability >= cutoffs["high"]:
        return NoShowPrediction.Level.HIGH
    if probability >= cutoffs["medium"]:
        return NoShowPrediction.Level.MEDIUM
    return NoShowPrediction.Level.LOW


def explain(params: dict, values: list[float]) -> list[dict]:
    """Las razones que más pesaron, en español: ``[{key, label, direction}]``.

    El peso de cada variable es ``coeficiente × valor estandarizado``: lo que
    esa variable suma o resta al puntaje del modelo para *esta* ficha.
    """
    pesos = []
    for nombre, coef, media, escala, valor in zip(
        params["features"], params["coef"], params["mean"], params["scale"], values,
    ):
        peso = coef * (valor - media) / (escala or 1.0)
        texto = features.describe(nombre, valor)
        if texto is None or abs(peso) < MIN_FACTOR_WEIGHT:
            continue
        pesos.append((abs(peso), nombre, texto, "up" if peso > 0 else "down"))
    pesos.sort(reverse=True)
    return [
        {"key": nombre, "label": texto, "direction": direccion}
        for _peso, nombre, texto, direccion in pesos[:MAX_FACTORS]
    ]


def active_version(organization) -> ModelVersion | None:
    """El modelo vigente. Supone el contexto de la organización."""
    return (
        ModelVersion.objects
        .filter(organization=organization, kind=ModelVersion.Kind.NOSHOW,
                status=ModelVersion.Status.ACTIVE)
        .first()
    )


def score_for(organization, now=None) -> int:
    """Calcula y guarda la predicción de las fichas futuras. Devuelve cuántas."""
    now = now or timezone.now()
    with tenant_context(organization.id):
        version = active_version(organization)
        if version is None:
            return 0
        fichas = list(
            Appointment.objects.filter(
                organization=organization,
                status__in=Appointment.ACTIVE_STATUSES,
                starts_at__gt=now,
                starts_at__lte=now + dt.timedelta(days=HORIZON_DAYS),
            )
        )
        if not fichas:
            return 0

        filas = features.build_rows(organization, fichas, now)
        existentes = {
            p.appointment_id: p
            for p in NoShowPrediction.objects.filter(
                organization=organization,
                appointment_id__in=[f.id for f in fichas],
            )
        }
        cortes = version.metrics["cutoffs"]
        nuevas, cambiadas = [], []
        for fila in filas:
            probabilidad = predict_proba(version.params, fila.values)
            campos = {
                "model_version": version,
                "probability": probabilidad,
                "level": level_for(probabilidad, cortes),
                "factors": explain(version.params, fila.values),
                "computed_at": now,
            }
            previa = existentes.get(fila.appointment_id)
            if previa is None:
                nuevas.append(NoShowPrediction(
                    organization=organization, appointment_id=fila.appointment_id,
                    **campos,
                ))
            else:
                for nombre, valor in campos.items():
                    setattr(previa, nombre, valor)
                cambiadas.append(previa)

        # `ignore_conflicts`: si dos procesos puntúan a la vez (el contenedor
        # viejo y el nuevo durante un despliegue), el segundo no rompe.
        NoShowPrediction.objects.bulk_create(nuevas, batch_size=500, ignore_conflicts=True)
        NoShowPrediction.objects.bulk_update(
            cambiadas,
            ["model_version", "probability", "level", "factors", "computed_at"],
            batch_size=500,
        )
        return len(nuevas) + len(cambiadas)


def has_feature(organization) -> bool:
    """¿El plan vigente de la organización incluye la predicción?"""
    plan = current_plan(organization)
    return plan is not None and plan.allows(FEATURE)


def eligible_organizations(slugs=None) -> list[Organization]:
    """Organizaciones activas cuyo plan incluye la predicción."""
    with platform_admin_context():
        consulta = Organization.objects.filter(status=Organization.Status.ACTIVE)
        if slugs:
            consulta = consulta.filter(slug__in=slugs)
        organizaciones = list(consulta)
    return [o for o in organizaciones if has_feature(o)]


def run_due(now=None) -> int:
    """Puntúa las fichas futuras de todas las organizaciones habilitadas.

    Una que falla no frena a las demás: se anota y se sigue.
    """
    total = 0
    for organizacion in eligible_organizations():
        try:
            total += score_for(organizacion, now)
        except Exception:  # noqa: BLE001 - una organización no frena al resto
            logger.exception("Falló la predicción de inasistencia de «%s».",
                             organizacion.slug)
    return total
