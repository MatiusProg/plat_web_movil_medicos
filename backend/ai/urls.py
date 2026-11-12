"""Rutas de los textos generados por IA: US-42 (validación del médico)."""

from django.urls import path

from .views import ApproveView, DiscardView, InboxView, PatientTextsView, TextDetailView

app_name = "ai"

urlpatterns = [
    path("texts/", InboxView.as_view(), name="inbox"),
    path("texts/mine/", PatientTextsView.as_view(), name="mine"),
    path("texts/<uuid:pk>/", TextDetailView.as_view(), name="detail"),
    path("texts/<uuid:pk>/approve/", ApproveView.as_view(), name="approve"),
    path("texts/<uuid:pk>/discard/", DiscardView.as_view(), name="discard"),
]
