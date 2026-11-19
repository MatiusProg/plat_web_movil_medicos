"""US-38: reentrenamiento seguro por organización sin modificar US-35/US-36.

La evaluación emparejada utiliza el 20 % cronológicamente más reciente de
``train_for`` y sólo desenlaces POSTERIORES al entrenamiento del vigente.
El candidato nunca se entrena con esas observaciones. Sin un conjunto
independiente adecuado se rechaza el candidato (no se promueve).
"""
from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from appointments.kpis import debian_atenderse_q
from appointments.models import Appointment
from tenancy.context import platform_admin_context, tenant_context

from . import features, scoring, training
from .models import ModelVersion

MIN_NEW_OUTCOMES = 20
MIN_EVALUATION = 20
MIN_IMPROVEMENT = 0.000001


@dataclass
class RetrainResult:
    action: str
    message: str
    version: ModelVersion | None = None
    new_outcomes: int = 0


def _brier(params, rows):
    return sum((scoring.predict_proba(params, row.values) - row.label) ** 2
               for row in rows) / len(rows)


def retrain_for(organization, now=None, *, min_new=MIN_NEW_OUTCOMES):
    now = now or timezone.now()
    # Organization es una entidad global: su manager puede ocultarla dentro de
    # tenant_context (RLS). Bloquearla antes, con privilegio de plataforma,
    # pero conservar el mismo transaction.atomic para serializar el entrenamiento.
    with transaction.atomic():
        from tenancy.models import Organization
        with platform_admin_context():
            Organization.objects.select_for_update().get(pk=organization.pk)
        with tenant_context(organization.id):
            active = scoring.active_version(organization)
            latest = (ModelVersion.objects.filter(
                organization=organization, kind=ModelVersion.Kind.NOSHOW)
                .order_by('-version').first())
            labeled, _ = training.data_status(organization, now)
            previous = (latest.n_train + latest.n_test) if latest else 0
            new = max(0, labeled - previous)
            if latest and new < min_new:
                return RetrainResult('skipped', 'No hay suficientes desenlaces nuevos.', new_outcomes=new)

            result = training.train_for(organization, now=now)
            if result.version is None:
                return RetrainResult('insufficient', result.message, new_outcomes=new)
            candidate = result.version
            if active is None or candidate.status == ModelVersion.Status.REJECTED:
                return RetrainResult(candidate.status, result.message, candidate, new)

            # Reproducir exactamente el orden y corte temporal usados por train_for.
            appointments = list(Appointment.objects.filter(
                organization=organization).filter(debian_atenderse_q(now))
                .order_by('starts_at', 'id'))
            cut = int(len(appointments) * (1 - training.TEST_FRACTION))
            held_out = [a for a in appointments[cut:] if a.starts_at > active.trained_at]
            rows = features.build_rows(organization, held_out, now)
            for row, appointment in zip(rows, held_out):
                row.label = features.label_of(appointment)

            detail = {'holdout_n': len(rows), 'incumbent_version': active.version,
                      'evaluation_after': active.trained_at.isoformat(),
                      'method': 'paired_chronological_holdout'}
            if len(rows) < MIN_EVALUATION or len({r.label for r in rows}) < 2:
                detail['reason'] = 'sin_evaluacion_independiente'
                _reject(candidate, detail)
                return RetrainResult('rejected', 'No hay suficientes desenlaces posteriores al modelo vigente para comparar sin fuga.', candidate, new)

            old_brier = _brier(active.params, rows)
            new_brier = _brier(candidate.params, rows)
            detail.update({'incumbent_brier': round(old_brier, 8),
                           'candidate_brier': round(new_brier, 8),
                           'improvement': round(old_brier - new_brier, 8)})
            candidate.metrics = {**candidate.metrics, 'retraining_comparison': detail}
            candidate.save(update_fields=['metrics', 'updated_at'])
            if new_brier >= old_brier - MIN_IMPROVEMENT:
                _reject(candidate, {**detail, 'reason': 'no_mejora_vigente'})
                return RetrainResult('rejected', 'El candidato no mejora el Brier del vigente en los mismos desenlaces.', candidate, new)

            training.promote(candidate)
            # Las predicciones futuras se recalculan en el job existente score_noshow.
            return RetrainResult('promoted', 'El candidato mejora al vigente y fue promovido.', candidate, new)


def _reject(candidate, comparison):
    candidate.metrics = {**candidate.metrics, 'retraining_comparison': comparison}
    candidate.status = ModelVersion.Status.REJECTED
    candidate.save(update_fields=['metrics', 'status', 'updated_at'])


def run_due(now=None, slugs=None, *, min_new=MIN_NEW_OUTCOMES):
    """Sólo organizaciones activas y con la función habilitada."""
    results = []
    for organization in scoring.eligible_organizations(slugs):
        try:
            results.append((organization.slug, retrain_for(
                organization, now=now, min_new=min_new)))
        except Exception:  # Una organización no interrumpe las otras.
            import logging
            logging.getLogger(__name__).exception('Error reentrenando %s', organization.slug)
            results.append((organization.slug, RetrainResult('error', 'Error al reentrenar.')))
    return results
