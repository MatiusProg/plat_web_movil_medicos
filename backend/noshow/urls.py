"""Rutas de la app `noshow`. Prefijo `/api/noshow/`."""

from django.urls import path

from .views import NoShowAppointmentsView, NoShowModelView
from .retrain_views import NoShowVersionsView

app_name = "noshow"

urlpatterns = [
    path("appointments/", NoShowAppointmentsView.as_view(), name="appointments"),
    path("model/", NoShowModelView.as_view(), name="model"),
    path("versions/", NoShowVersionsView.as_view(), name="versions"),
]
