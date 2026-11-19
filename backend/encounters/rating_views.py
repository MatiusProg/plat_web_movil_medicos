"""US-48 — Endpoints de la calificación con estrellas.

- ``GET   /api/encounters/<id>/rating/``  la calificación propia de esa
  atención (o ``null``).
- ``POST  /api/encounters/<id>/rating/``  calificar por primera vez.
- ``PATCH /api/encounters/<id>/rating/``  cambiarla, durante 7 días.
- ``GET   /api/encounters/ratings/mine/`` el médico: su promedio, sin nombres.

Calificar pide el permiso ``encounters.history.read`` **y** el alcance propio
sobre el paciente de la atención (el paciente, o el titular de su
dependiente). Un médico, aunque lea el historial, no califica: 404.

El tablero del administrador está en ``reporting`` (``/api/reporting/satisfaction/``).
"""

import uuid

from django.http import Http404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import ratings, services
from .history_views import CanReadHistory
from .models import Encounter, EncounterRating
from .permissions import CanReadEncounters


class RatingWriteSerializer(serializers.Serializer):
    stars = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        max_length=EncounterRating.MAX_COMMENT, required=False, allow_blank=True,
        trim_whitespace=True, default="",
    )


class RatingReadSerializer(serializers.Serializer):
    stars = serializers.IntegerField()
    comment = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    editable_until = serializers.DateTimeField()
    editable = serializers.BooleanField()


def leer(rating):
    datos = ratings.as_dict(rating)
    return None if datos is None else RatingReadSerializer(datos).data


def _atencion_propia(request, pk):
    """La atención firmada de un paciente sobre el que tengo alcance propio."""
    try:
        pk = uuid.UUID(str(pk))
    except ValueError:
        raise Http404
    encuentro = (Encounter.objects
                 .filter(organization=request.user.organization, pk=pk,
                         status=Encounter.Status.SIGNED)
                 .select_related("patient").first())
    if encuentro is None or services.history_scope(
        request.user, encuentro.patient,
    ) != services.OWN:
        raise Http404
    return encuentro


class EncounterRatingView(APIView):
    permission_classes = [IsAuthenticated, CanReadHistory]

    def get(self, request, pk):
        encuentro = _atencion_propia(request, pk)
        return Response({"rating": leer(
            EncounterRating.objects.filter(encounter=encuentro).first())})

    def post(self, request, pk):
        encuentro = _atencion_propia(request, pk)
        datos = RatingWriteSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        rating = ratings.rate(request.user, encuentro, **datos.validated_data)
        return Response({"rating": leer(rating)}, status=201)

    def patch(self, request, pk):
        encuentro = _atencion_propia(request, pk)
        datos = RatingWriteSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        rating = ratings.correct(encuentro, **datos.validated_data)
        return Response({"rating": leer(rating)})


class MyRatingsView(APIView):
    """El médico ve su promedio y la distribución. Nada de quién."""

    permission_classes = [IsAuthenticated, CanReadEncounters]

    def get(self, request):
        profesional = services.practitioner_of(request.user)
        if profesional is None:
            raise Http404
        return Response(ratings.for_practitioner(profesional))
