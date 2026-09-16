"""Rutas de la app `backups`. Característica general 6.

`config/urls.py` la incluye bajo `/api/backups/`, en la misma apertura que
`reporting`.

    GET  /api/backups/records/    historial de copias y restauraciones
    POST /api/backups/create/     genera la copia y la descarga
    POST /api/backups/inspect/    qué contiene un archivo, sin escribir nada
    POST /api/backups/restore/    reemplaza los datos con los del archivo
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BackupRecordViewSet,
    CreateBackupView,
    InspectBackupView,
    RestoreBackupView,
)

app_name = "backups"

router = DefaultRouter()
router.register("records", BackupRecordViewSet, basename="record")

urlpatterns = [
    path("create/", CreateBackupView.as_view(), name="create"),
    path("inspect/", InspectBackupView.as_view(), name="inspect"),
    path("restore/", RestoreBackupView.as_view(), name="restore"),
    *router.urls,
]
