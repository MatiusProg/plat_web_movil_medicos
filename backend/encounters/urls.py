"""Rutas de la atención médica: US-24 (registro), US-25 (historial), US-41 (resumen)
US-48 (calificación) y US-49 (tomas de la receta)."""

from django.urls import path

from .history_views import PatientHistorySummaryView, PatientHistoryView
from .intake_views import MedicationIntakesView, MyMedicationsView
from .rating_views import EncounterRatingView, MyRatingsView
from .views import (
    AgendaView,
    EncounterAmendView,
    EncounterChildDetailView,
    EncounterChildrenView,
    EncounterDetailView,
    EncounterOpenView,
    EncounterSignView,
    PrescriptionPdfView,
)

app_name = "encounters"

urlpatterns = [
    path("agenda/", AgendaView.as_view(), name="agenda"),
    path("", EncounterOpenView.as_view(), name="open"),
    path("<uuid:pk>/", EncounterDetailView.as_view(), name="detail"),
    path("<uuid:pk>/sign/", EncounterSignView.as_view(), name="sign"),
    path("<uuid:pk>/amendments/", EncounterAmendView.as_view(), name="amend"),
    # US-26: la receta y las órdenes del borrador, y la receta firmada en PDF.
    path("<uuid:pk>/prescription/",
         EncounterChildrenView.as_view(kind="prescription"), name="prescription"),
    path("<uuid:pk>/prescription/<uuid:child_pk>/",
         EncounterChildDetailView.as_view(kind="prescription"),
         name="prescription-item"),
    path("<uuid:pk>/orders/", EncounterChildrenView.as_view(kind="orders"),
         name="orders"),
    path("<uuid:pk>/orders/<uuid:child_pk>/",
         EncounterChildDetailView.as_view(kind="orders"), name="order"),
    path("<uuid:pk>/prescription.pdf", PrescriptionPdfView.as_view(),
         name="prescription-pdf"),
    # US-25: el historial longitudinal, todas las sucursales.
    path("history/<uuid:patient_id>/", PatientHistoryView.as_view(), name="history"),
    # US-41: el resumen del historial para el médico, antes de la consulta.
    path("history/<uuid:patient_id>/summary/", PatientHistorySummaryView.as_view(),
         name="history-summary"),
    # US-48: el paciente califica la atención; el médico ve su promedio.
    path("<uuid:pk>/rating/", EncounterRatingView.as_view(), name="rating"),
    path("ratings/mine/", MyRatingsView.as_view(), name="my-ratings"),
    # US-49: las tomas de la receta y *Mis medicamentos*.
    path("prescription/<uuid:item_pk>/intakes/", MedicationIntakesView.as_view(),
         name="intakes"),
    path("medications/<uuid:patient_id>/", MyMedicationsView.as_view(),
         name="medications"),
]
