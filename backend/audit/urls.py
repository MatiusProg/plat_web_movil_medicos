"""Rutas de la app `audit`.

`config/urls.py` ya incluye esta app bajo `/api/audit/`. Es la última app
nueva del Sprint 1 y la segunda —y última— vez que ese archivo se abre, como
dice el reparto.

    GET /api/audit/logs/                  listado paginado con filtros
    GET /api/audit/logs/actions/          catálogo de acciones para el filtro
    GET /api/audit/logs/{id}/             un asiento

No hay POST, PUT, PATCH ni DELETE, y no es un olvido: es el punto (f).
"""

from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet

app_name = "audit"

router = DefaultRouter()

# ---------- US-06 (SM): bitácora de auditoría ---------------------------
router.register("logs", AuditLogViewSet, basename="log")

urlpatterns = router.urls
