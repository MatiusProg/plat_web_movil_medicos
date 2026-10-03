"""Rutas de la atención médica (US-24). US-25 agrega acá el historial."""

from django.urls import path

from .views import (
    AgendaView,
    EncounterAmendView,
    EncounterDetailView,
    EncounterOpenView,
    EncounterSignView,
)

app_name = "encounters"

urlpatterns = [
    path("agenda/", AgendaView.as_view(), name="agenda"),
    path("", EncounterOpenView.as_view(), name="open"),
    path("<uuid:pk>/", EncounterDetailView.as_view(), name="detail"),
    path("<uuid:pk>/sign/", EncounterSignView.as_view(), name="sign"),
    path("<uuid:pk>/amendments/", EncounterAmendView.as_view(), name="amend"),
]
