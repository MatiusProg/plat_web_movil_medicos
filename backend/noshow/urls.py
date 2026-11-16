"""Rutas de la app `noshow`. Prefijo `/api/noshow/`."""

from django.urls import path

from .views import NoShowAppointmentsView, NoShowModelView

app_name = "noshow"

urlpatterns = [
    path("appointments/", NoShowAppointmentsView.as_view(), name="appointments"),
    path("model/", NoShowModelView.as_view(), name="model"),
]
