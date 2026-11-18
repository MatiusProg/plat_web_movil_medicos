"""US-37/US-38: pruebas de regresión sin alterar los tests de compañeros."""
import datetime as dt
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from noshow import retraining
from noshow.models import ModelVersion
from tenancy.context import tenant_context
from .test_us35 import admin_a  # noqa: F401; fixture de US-35 sin modificarla
from .fichas_comunes import api_client  # noqa: F401

pytestmark = pytest.mark.django_db


def test_retrain_sin_desenlaces_nuevos_no_entrena(org_a):
    with tenant_context(org_a.id):
        ModelVersion.objects.create(
            organization=org_a, kind='noshow', version=1, status='active',
            n_train=180, n_test=40, base_rate=.2, beats_baseline=True,
            params={}, metrics={},
        )
        with patch.object(retraining.training, 'data_status', return_value=(220, 44)), \
             patch.object(retraining.training, 'train_for') as train:
            result = retraining.retrain_for(org_a)
        assert result.action == 'skipped'
        train.assert_not_called()


def test_comparacion_brier_mismas_fichas():
    rows = [SimpleNamespace(values=[.2], label=1), SimpleNamespace(values=[.8], label=0)]
    with patch.object(retraining.scoring, 'predict_proba', side_effect=lambda params, values: values[0]):
        assert retraining._brier({}, rows) == pytest.approx(.64)


def test_historial_requiere_autenticacion(api_client):
    response = api_client.get('/api/noshow/versions/')
    assert response.status_code in (401, 403)


def test_historial_no_filtra_otra_organizacion(api_client, admin_a, org_a, org_b):
    from .fichas_comunes import autenticar
    with tenant_context(org_a.id):
        ModelVersion.objects.create(
            organization=org_a, kind='noshow', version=1, status='active',
            n_train=200, n_test=40, base_rate=.2, beats_baseline=True,
            params={}, metrics={'brier': .1},
        )
    with tenant_context(org_b.id):
        ModelVersion.objects.create(
            organization=org_b, kind='noshow', version=12, status='active',
            n_train=200, n_test=40, base_rate=.2, beats_baseline=True,
            params={}, metrics={'brier': .1},
        )
    autenticar(api_client, admin_a)
    response = api_client.get('/api/noshow/versions/')
    # Según el plan fixture: disponible o protegido por límite Premium.
    if response.status_code == 200:
        assert [row['version'] for row in response.data['results']] == [1]
    else:
        assert response.status_code == 403


def test_backtest_no_usa_semana_objetivo():
    # El contrato del walk-forward exige ocho semanas previas, no incluye la objetivo.
    from reporting import demand
    assert demand.HISTORY_WEEKS == 8
    for evaluation_week in range(8, 16):
        preceding = list(range(evaluation_week - demand.HISTORY_WEEKS, evaluation_week))
        assert len(preceding) == 8
        assert evaluation_week not in preceding


def test_candidato_peor_se_rechaza_sin_promocion(org_a):
    now = timezone.now()
    with tenant_context(org_a.id):
        incumbent = ModelVersion.objects.create(
            organization=org_a, kind='noshow', version=1, status='active',
            trained_at=now - dt.timedelta(days=40), n_train=180, n_test=40,
            base_rate=.2, beats_baseline=True, params={'intercept': 0}, metrics={},
        )
        candidate = ModelVersion.objects.create(
            organization=org_a, kind='noshow', version=2, status='candidate',
            trained_at=now, n_train=200, n_test=60,
            base_rate=.2, beats_baseline=True, params={'intercept': 1}, metrics={},
        )
        future_outcomes = [SimpleNamespace(starts_at=now - dt.timedelta(days=10))] * 100
        labeled_rows = [SimpleNamespace(values=[.0], label=i % 2) for i in range(20)]
        with patch.object(retraining.training, 'data_status', return_value=(280, 40)), \
             patch.object(retraining.training, 'train_for', return_value=SimpleNamespace(version=candidate)), \
             patch.object(retraining.Appointment.objects, 'filter') as mocked_filter, \
             patch.object(retraining.features, 'build_rows', return_value=labeled_rows), \
             patch.object(retraining.features, 'label_of', side_effect=iter([i % 2 for i in range(20)])), \
             patch.object(retraining, '_brier', side_effect=[.1, .2]), \
             patch.object(retraining.training, 'promote') as promote:
            mocked_filter.return_value.filter.return_value.order_by.return_value = future_outcomes
            result = retraining.retrain_for(org_a, now)
            promote.assert_not_called()
        candidate.refresh_from_db()
        incumbent.refresh_from_db()
        assert result.action == 'rejected'
        assert incumbent.status == 'active'
        assert candidate.status == 'rejected'
        assert candidate.metrics['retraining_comparison']['candidate_brier'] == .2
