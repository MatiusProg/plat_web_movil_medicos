"""Rutas del proyecto.

Sin ``django.contrib.admin`` a propósito: el admin no conoce el contexto de
inquilino, así que un administrador de una organización vería y editaría los
datos de todas. La administración va por la API y el frontend de React, con
los permisos de accounts.RolePermission.

Cada historia del Sprint 0 agrega su router acá:

    US-43, US-44, US-45  ->  api/platform/    (Luis Mateo, Daniel, Luis Miguel)
    US-01, US-02         ->  api/auth/        (Alexander, Karen)
    US-04                ->  api/accounts/    (Michael)
"""

from django.http import JsonResponse
from django.urls import path


def health(request):
    """Sonda de estado. Sirve para verificar que el contenedor responde."""
    return JsonResponse({
        "status": "ok",
        "tenant": str(getattr(request, "tenant_id", None) or ""),
        "platform_admin": getattr(request, "is_platform_admin", False),
    })


urlpatterns = [
    path("api/health/", health, name="health"),
]
