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

from django.urls import path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from tenancy.context import current_context


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Sonda de estado.

    Es una vista de DRF y no de Django a propósito: así la autenticación
    —y con ella el contexto de inquilino— corre igual que en cualquier
    endpoint real. Devuelve el contexto tal como lo ve PostgreSQL, no lo que
    la aplicación cree haber fijado.
    """
    tenant, es_admin_plataforma = current_context()
    return Response({
        "status": "ok",
        "tenant": tenant,
        "platform_admin": es_admin_plataforma,
        "user": request.user.email if request.user.is_authenticated else None,
    })


urlpatterns = [
    path("api/health/", health, name="health"),
]
