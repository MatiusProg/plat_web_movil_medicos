"""Rutas de la app `reporting`. Característica general 5.

`config/urls.py` la incluye bajo `/api/reporting/`. Es una app **nueva**, que
es la única excepción que ese archivo admite según su propio encabezado.

    GET    /api/reporting/datasets/          el catálogo para el constructor
    POST   /api/reporting/run/               ejecutar una definición suelta
    POST   /api/reporting/interpret/         traducir un pedido dictado
    GET    /api/reporting/reports/           los guardados que puedo ver
    POST   /api/reporting/reports/           guardar uno
    GET    /api/reporting/reports/{id}/
    PATCH  /api/reporting/reports/{id}/      sólo el dueño
    DELETE /api/reporting/reports/{id}/      sólo el dueño
    POST   /api/reporting/reports/{id}/run/  ejecutar uno guardado
    GET    /api/reporting/kpis/              el panel de indicadores (US-29)
    GET    /api/reporting/satisfaction/      las estrellas de la atención (US-48)
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import finance_views
from .demand_views import DemandProjectionView
from .kpi_views import KpiView, SatisfactionView
from .views import (
    DatasetListView,
    InterpretVoiceView,
    RunReportView,
    SavedReportViewSet,
)

app_name = "reporting"

router = DefaultRouter()
router.register("reports", SavedReportViewSet, basename="saved_report")

urlpatterns = [
    path("datasets/", DatasetListView.as_view(), name="datasets"),
    path("run/", RunReportView.as_view(), name="run"),
    path("interpret/", InterpretVoiceView.as_view(), name="interpret"),
    path("kpis/", KpiView.as_view(), name="kpis"),
    path("demand/", DemandProjectionView.as_view(), name="demand"),
    path("satisfaction/", SatisfactionView.as_view(), name="satisfaction"),
    # US-50 — la contabilidad (ver finance_views.py).
    path("finance/summary/", finance_views.SummaryView.as_view(), name="finance-summary"),
    path("finance/series/", finance_views.SeriesView.as_view(), name="finance-series"),
    path("finance/export/", finance_views.ExportView.as_view(), name="finance-export"),
    path("finance/interpret/", finance_views.InterpretView.as_view(), name="finance-interpret"),
    path("finance/expenses/", finance_views.ExpenseListView.as_view(), name="finance-expenses"),
    path("finance/expenses/<uuid:pk>/", finance_views.ExpenseDetailView.as_view(),
         name="finance-expense"),
    path("finance/settings/", finance_views.SettingsView.as_view(), name="finance-settings"),
    *router.urls,
]
