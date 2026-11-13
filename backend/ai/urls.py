"""Rutas de los textos generados por IA: US-42 (validación) y US-39 (resumen)."""

from django.urls import path

from .views import (
    ApproveView,
    ConsultationSummaryView,
    DiscardView,
    InboxView,
    PatientTextsView,
    TextDetailView,
)

app_name = "ai"

urlpatterns = [
    path("texts/", InboxView.as_view(), name="inbox"),
    path("texts/mine/", PatientTextsView.as_view(), name="mine"),
    path("texts/<uuid:pk>/", TextDetailView.as_view(), name="detail"),
    path("texts/<uuid:pk>/approve/", ApproveView.as_view(), name="approve"),
    path("texts/<uuid:pk>/discard/", DiscardView.as_view(), name="discard"),
    # US-39: reintentar el resumen de una atención firmada.
    path("encounters/<uuid:encounter_id>/summary/", ConsultationSummaryView.as_view(),
         name="consultation-summary"),
]
