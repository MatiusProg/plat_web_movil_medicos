"""Permiso del asistente.

Mismo patrón que ``catalog/permissions.py``: el código se resuelve por
``user.has_permission()``, que consulta ``UserRole → RolePermission``. **Nunca
``user.has_perm()``**, que lee las tablas de ``django.contrib.auth`` y ésas no
están aisladas por inquilino.
"""

from rest_framework.permissions import BasePermission


class CanUseAssistant(BasePermission):
    """US-31 — consultar al asistente de orientación."""

    code = "assistant.suggest.use"
    message = "No tenés permiso para consultar al asistente."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_permission(self.code))
