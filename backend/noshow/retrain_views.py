"""US-38: historial de modelos, sólo administración de la organización."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.plans import require_feature
from .models import ModelVersion
from .permissions import CanReadNoShow
from .views import FEATURE_TEXT


class NoShowVersionsView(APIView):
    permission_classes = [IsAuthenticated, CanReadNoShow]

    def get(self, request):
        organization = getattr(request.user, 'organization', None)
        if organization is None:
            return Response({'code': 'sin_organizacion'}, status=403)
        require_feature(organization, 'noshow_prediction', FEATURE_TEXT)
        versions = ModelVersion.objects.filter(
            organization=organization, kind=ModelVersion.Kind.NOSHOW,
        ).order_by('-version')[:30]
        return Response({'results': [{
            'version': v.version, 'status': v.status,
            'trained_at': v.trained_at, 'n_train': v.n_train,
            'n_test': v.n_test, 'beats_baseline': v.beats_baseline,
            'auc': v.metrics.get('auc'), 'brier': v.metrics.get('brier'),
            'comparison': v.metrics.get('retraining_comparison'),
        } for v in versions]})
