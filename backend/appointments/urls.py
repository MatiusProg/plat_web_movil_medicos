"""Rutas de la app `appointments`. Prefijo `/api/appointments/`."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .booking import AppointmentViewSet
from .changes import CancelAppointmentView, RescheduleAppointmentView
from .attendance import ConfirmAttendanceView, attendance_link_view
from .checkin import CheckInView
from .receipts import ReceiptView

app_name = "appointments"

router = DefaultRouter()

# ---------- US-17 — Reserva de ficha ------------------------------------
router.register(
    "appointments",
    AppointmentViewSet,
    basename="appointment",
)

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

    # ---------- US-19 — Comprobante digital con QR ---------------------
    path(
        "appointments/<uuid:pk>/receipt/",
        ReceiptView.as_view(),
        name="appointment-receipt",
    ),

    # ---------- US-21 — Confirmación de asistencia ----------------------
    path(
        "appointments/<uuid:pk>/confirm-attendance/",
        ConfirmAttendanceView.as_view(),
        name="appointment-confirm-attendance",
    ),
    # El enlace del correo: sin sesión, autenticado por la firma.
    path(
        "attendance/<str:token>/",
        attendance_link_view,
        name="attendance-link",
    ),

    # ---------- US-22 — Check-in en recepción ---------------------------
    path(
        "checkin/",
        CheckInView.as_view(),
        name="checkin",
    ),
]