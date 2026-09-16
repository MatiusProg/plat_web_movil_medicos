"""Rutas de la app `reporting`. Característica general 5.

`config/urls.py` la incluye bajo `/api/reporting/`. Es una app **nueva**, que
es la única excepción que ese archivo admite según su propio encabezado.

    GET    /api/reporting/datasets/          el catálogo para el constructor
    POST   /api/reporting/run/               ejecutar una definición suelta
    GET    /api/reporting/reports/           los guardados que puedo ver
    POST   /api/reporting/reports/           guardar uno
    GET    /api/reporting/reports/{id}/
    PATCH  /api/reporting/reports/{id}/      sólo el dueño
    DELETE /api/reporting/reports/{id}/      sólo el dueño
    POST   /api/reporting/reports/{id}/run/  ejecutar uno guardado
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import DatasetListView, RunReportView, SavedReportViewSet

app_name = "reporting"

router = DefaultRouter()
router.register("reports", SavedReportViewSet, basename="saved_report")

urlpatterns = [
    path("datasets/", DatasetListView.as_view(), name="datasets"),
    path("run/", RunReportView.as_view(), name="run"),
    *router.urls,
]
