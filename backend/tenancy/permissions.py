"""Clases de permiso de la app `tenancy`."""

from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    """Sólo el Superadministrador de Plataforma.

    No delega en RLS: aunque la base ya filtra las tablas de nivel plataforma,
    esta clase evita que un inquilino autenticado reciba un 200 con datos
    vacíos en vez de un 403 explícito.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_platform_admin
        )
