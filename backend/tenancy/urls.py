"""Rutas de la app `tenancy`.

Cada historia agrega su router o su `path` **acá**, nunca en
`config/urls.py`. Ese archivo ya incluye esta app y no hay que volver a
tocarlo: si los seis editaran el mismo archivo, cada pull request traeria un
conflicto.

Convencion del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views

app_name = "tenancy"

router = DefaultRouter()
router.register("alerts", views.IsolationAlertViewSet, basename="alert")

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
] + router.urls
