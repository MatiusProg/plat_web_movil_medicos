"""Rutas de la app `backups`. Característica general 6.

`config/urls.py` la incluye bajo `/api/backups/`, en la misma apertura que
`reporting`.

    GET  /api/backups/records/    historial de copias y restauraciones
    GET  /api/backups/policy/     qué permite el plan y cuándo es la próxima copia
    POST /api/backups/create/     genera la copia y la descarga (según el plan)
    POST /api/backups/inspect/    qué contiene un archivo, sin escribir nada
    POST /api/backups/restore/    reemplaza los datos con los del archivo
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    BackupPolicyView,
    BackupRecordViewSet,
    CreateBackupView,
    InspectBackupView,
    RestoreBackupView,
)

app_name = "backups"

router = DefaultRouter()
router.register("records", BackupRecordViewSet, basename="record")

urlpatterns = [
    path("policy/", BackupPolicyView.as_view(), name="policy"),
    path("create/", CreateBackupView.as_view(), name="create"),
    path("inspect/", InspectBackupView.as_view(), name="inspect"),
    path("restore/", RestoreBackupView.as_view(), name="restore"),
    *router.urls,
]
