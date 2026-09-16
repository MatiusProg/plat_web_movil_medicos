"""Rutas de la app `appointments`. Prefijo `/api/appointments/`."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .booking import AppointmentViewSet
from .changes import CancelAppointmentView, RescheduleAppointmentView

app_name = "appointments"

router = DefaultRouter()

# ---------- US-17 — Reserva de ficha ------------------------------------
router.register("appointments", AppointmentViewSet, basename="appointment")

urlpatterns = router.urls + [
    # ---------- US-20 — Cancelación y reprogramación --------------------
    path(
        "appointments/<uuid:pk>/cancel/",
        CancelAppointmentView.as_view(),
        name="appointment-cancel",
    ),
    path(
        "appointments/<uuid:pk>/reschedule/",
        RescheduleAppointmentView.as_view(),
        name="appointment-reschedule",
    ),
]
