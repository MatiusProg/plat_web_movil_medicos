"""Rutas de la app `appointments`. Prefijo `/api/appointments/`."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .calendar import CalendarView
from .preconsultation_views import PreconsultationView
from .booking import AppointmentViewSet
from .counter import CounterBookingView
from .changes import CancelAppointmentView, RescheduleAppointmentView
from .attendance import ConfirmAttendanceView, attendance_link_view
from .checkin import CheckInView
from .receipts import ReceiptView
from .waitlist_views import (
    WaitlistEntryView, WaitlistSummaryView, WaitlistView,
)

app_name = "appointments"

router = DefaultRouter()

# ---------- US-17 — Reserva de ficha ------------------------------------
router.register(
    "appointments",
    AppointmentViewSet,
    basename="appointment",
)

urlpatterns = router.urls + [
    path("appointments/<uuid:pk>/preconsultation/", PreconsultationView.as_view(), name="preconsultation"),
    # US-51: «Agregar a mi calendario».
    path("appointments/<uuid:pk>/calendar.ics", CalendarView.as_view(), name="calendar"),
    path("counter/book/", CounterBookingView.as_view(), name="counter-book"),
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

    # ---------- US-52 — Lista de espera ----------------------------------
    path("waitlist/", WaitlistView.as_view(), name="waitlist"),
    path("waitlist/summary/", WaitlistSummaryView.as_view(), name="waitlist-summary"),
    path("waitlist/<uuid:pk>/", WaitlistEntryView.as_view(), name="waitlist-entry"),
]
