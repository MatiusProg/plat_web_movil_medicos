"""Rutas de la app `scheduling`.

Cada historia agrega su bloque acá. `config/urls.py` ya incluye esta app.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .availability import AvailabilityView
from .blocks import ScheduleBlockViewSet
from .schedules import ScheduleViewSet

app_name = "scheduling"

router = DefaultRouter()

# ---------- US-13 — Agendas médicas ------------------------------------
router.register("schedules", ScheduleViewSet, basename="schedule")

# ---------- US-14 — Bloqueo de agenda ---------------------------------
router.register("blocks", ScheduleBlockViewSet, basename="block")

urlpatterns = router.urls + [
    # ---------- US-15 — Disponibilidad consolidada ------------------
    path("availability/", AvailabilityView.as_view(), name="availability"),
]
