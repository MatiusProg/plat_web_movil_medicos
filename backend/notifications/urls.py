"""Rutas de la app `notifications` (US-28). Prefijo `/api/notifications/`."""

from django.urls import path

from .views import DeviceTokenView

app_name = "notifications"

urlpatterns = [
    path("devices/", DeviceTokenView.as_view(), name="devices"),
]
