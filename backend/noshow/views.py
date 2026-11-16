"""US-35 — La API del riesgo de inasistencia, para la Administración.

    GET /api/noshow/appointments/?from=&to=&branch=&level=&page=&page_size=
    GET /api/noshow/model/

**El riesgo no viaja en el serializador de fichas** (``AppointmentSerializer``).
Ése lo leen el paciente, la app móvil y el mostrador; ponerlo ahí habría hecho
posible que un paciente viera cómo lo califica el centro. Acá es un endpoint
aparte, con su propio permiso (``appointments.noshow.read``, sólo la
Administración), y una prueba que comprueba que las fichas del paciente no
traen nada de esto.

Tres cerraduras, todas del lado del servidor: el permiso, el plan de la
organización (``noshow_prediction``, sólo Premium; ver ``tenancy/plans.py``) y
el alcance por organización, que además de RLS se filtra de forma explícita.
"""

from __future__ import annotations

import datetime as dt
import uuid
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments import kpis
from appointments.models import Appointment
from catalog.models import Branch
from config.pagination import Paginacion
from tenancy.plans import require_feature

from . import training
from .models import ModelVersion, NoShowPrediction
from .permissions import CanReadNoShow
from .scoring import active_version

DEFAULT_DAYS_AHEAD = 14
LEVELS = {nivel.value for nivel in NoShowPrediction.Level}
FEATURE_TEXT = "la predicción de inasistencia"


def _error(code, detail):
    return Response({"code": code, "detail": detail}, status=status.HTTP_400_BAD_REQUEST)


def _fecha(valor):
    try:
        return dt.date.fromisoformat(valor)
    except ValueError:
        return None


def _organization(request):
    """La organización de quien pide, o ``None`` si es la plataforma."""
    return getattr(request.user, "organization", None)


def _sin_organizacion():
    return Response(
        {"code": "sin_organizacion",
         "detail": "Esta información es de cada centro médico."},
        status=status.HTTP_403_FORBIDDEN,
    )


def _round(valor, cifras=4):
    return None if valor is None else round(float(valor), cifras)


def _metrics(metricas: dict) -> dict:
    return {
        "auc": _round(metricas.get("auc")),
        "brier": _round(metricas.get("brier")),
        "brier_baseline": _round(metricas.get("brier_baseline")),
        "accuracy_baseline": _round(metricas.get("accuracy_baseline")),
        "recall_high": _round(metricas.get("recall_high")),
        "precision_high": _round(metricas.get("precision_high")),
    }


class NoShowAppointmentsView(APIView):
    permission_classes = [IsAuthenticated, CanReadNoShow]

    def get(self, request):
        organizacion = _organization(request)
        if organizacion is None:
            return _sin_organizacion()
        require_feature(organizacion, "noshow_prediction", FEATURE_TEXT)

        tz = ZoneInfo(organizacion.timezone or "America/La_Paz")
        ahora = timezone.now()
        hoy = ahora.astimezone(tz).date()
        crudo_desde = request.query_params.get("from")
        crudo_hasta = request.query_params.get("to")
        desde = _fecha(crudo_desde) if crudo_desde else hoy
        hasta = (
            _fecha(crudo_hasta) if crudo_hasta
            else (desde + dt.timedelta(days=DEFAULT_DAYS_AHEAD) if desde else None)
        )
        if desde is None or hasta is None:
            return _error("invalid_date", "Las fechas deben tener el formato AAAA-MM-DD.")
        if hasta < desde:
            return _error("invalid_range", "El rango de fechas está invertido.")
        if (hasta - desde).days >= kpis.MAX_DIAS:
            return _error("range_too_long",
                          f"El rango no puede superar {kpis.MAX_DIAS} días.")

        nivel = request.query_params.get("level") or None
        if nivel is not None and nivel not in LEVELS:
            return _error("invalid_level", "El nivel debe ser low, medium o high.")

        branch_id = request.query_params.get("branch") or None
        if branch_id:
            try:
                branch_id = uuid.UUID(branch_id)
            except ValueError:
                return _error("invalid_branch", "La sucursal no es válida.")
            if not Branch.objects.filter(organization=organizacion, pk=branch_id).exists():
                return _error("invalid_branch",
                              "La sucursal no existe en esta organización.")

        inicio, fin = kpis.rango_utc(organizacion, desde, hasta)
        predicciones = (
            NoShowPrediction.objects
            .filter(
                organization=organizacion,
                # Sólo lo que dice el modelo vigente: la de una versión retirada
                # o la de una ficha que ya pasó o se canceló no se muestra.
                model_version__status=ModelVersion.Status.ACTIVE,
                appointment__status__in=Appointment.ACTIVE_STATUSES,
                appointment__starts_at__gt=ahora,
                appointment__starts_at__gte=inicio,
                appointment__starts_at__lt=fin,
            )
            .select_related("appointment__patient", "appointment__practitioner",
                            "appointment__branch")
            .order_by("appointment__starts_at", "appointment_id")
        )
        if nivel:
            predicciones = predicciones.filter(level=nivel)
        if branch_id:
            predicciones = predicciones.filter(appointment__branch_id=branch_id)

        paginador = Paginacion()
        pagina = paginador.paginate_queryset(predicciones, request, view=self)
        return paginador.get_paginated_response([self._fila(p) for p in pagina])

    @staticmethod
    def _fila(prediccion: NoShowPrediction) -> dict:
        ficha = prediccion.appointment
        return {
            "appointment_id": str(ficha.id),
            "patient_name": ficha.patient.full_name,
            "practitioner_name": ficha.practitioner.full_name,
            "branch_name": ficha.branch.name,
            "starts_at": ficha.starts_at,
            "status": ficha.status,
            "level": prediccion.level,
            "probability": _round(prediccion.probability),
            "factors": prediccion.factors,
            "computed_at": prediccion.computed_at,
        }


class NoShowModelView(APIView):
    """El estado del modelo de la organización, para la tarjeta de la pantalla."""

    permission_classes = [IsAuthenticated, CanReadNoShow]

    def get(self, request):
        organizacion = _organization(request)
        if organizacion is None:
            return _sin_organizacion()
        require_feature(organizacion, "noshow_prediction", FEATURE_TEXT)

        version = active_version(organizacion)
        if version is not None:
            return Response({
                "model": {
                    "version": version.version,
                    "status": version.status,
                    "trained_at": version.trained_at,
                    "n_train": version.n_train,
                    "n_test": version.n_test,
                    "base_rate": _round(version.base_rate),
                    "beats_baseline": version.beats_baseline,
                    "metrics": _metrics(version.metrics),
                    "cutoffs": {
                        "medium": _round(version.metrics["cutoffs"]["medium"]),
                        "high": _round(version.metrics["cutoffs"]["high"]),
                    },
                },
                "rejected": None, "reason": None, "message": None,
            })

        rechazada = (
            ModelVersion.objects
            .filter(organization=organizacion, kind=ModelVersion.Kind.NOSHOW,
                    status=ModelVersion.Status.REJECTED)
            .order_by("-version").first()
        )
        if rechazada is not None:
            return Response({
                "model": None,
                "rejected": {
                    "version": rechazada.version,
                    "trained_at": rechazada.trained_at,
                    "metrics": _metrics(rechazada.metrics),
                },
                "reason": "no_supera_base",
                "message": ("El último modelo entrenado no mejora a predecir que todos "
                            "asisten, así que no se usa para calificar fichas."),
            })

        etiquetadas, ausentes = training.data_status(organizacion)
        if etiquetadas < training.MIN_LABELED or ausentes < training.MIN_ABSENT:
            return Response({
                "model": None, "rejected": None, "reason": "sin_datos",
                "message": (
                    f"Todavía no hay datos suficientes: {etiquetadas} fichas con desenlace "
                    f"y {ausentes} ausencias. Se necesitan al menos {training.MIN_LABELED} "
                    f"y {training.MIN_ABSENT}."),
            })
        return Response({
            "model": None, "rejected": None, "reason": "sin_modelo",
            "message": "Todavía no se entrenó un modelo para este centro.",
        })
