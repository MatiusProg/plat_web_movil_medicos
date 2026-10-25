"""Rutas de la atención médica: US-24 (registro) y US-25 (historial)."""

from django.urls import path

from .history_views import PatientHistoryView
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
]
