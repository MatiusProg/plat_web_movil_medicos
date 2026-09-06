"""Clases de permiso de DRF para el catálogo.

Mismo patrón que `accounts/permissions.py`: cada clase declara su código y la
autorización pasa por `user.has_permission(...)`, que consulta
`UserRole → RolePermission`. **Nunca `user.has_perm()`**: las tablas de
`django.contrib.auth` no están aisladas por inquilino.

Los códigos ya están sembrados en `accounts/migrations/0003_seed_permissions_sprint_1.py`
y el rol *Paciente* los tiene: el móvil los consume en US-16.
"""

from rest_framework.permissions import BasePermission


class RequiresPermission(BasePermission):
    """Base: exige el código declarado en ``code``."""

    code = ""
    message = "No tenés permiso para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and self.code
            and user.has_permission(self.code)
        )


class CanReadBranches(RequiresPermission):
    code = "catalog.branch.read"


class CanReadSpecialties(RequiresPermission):
    code = "catalog.specialty.read"


class CanReadProfessionals(RequiresPermission):
    code = "catalog.professional.read"
