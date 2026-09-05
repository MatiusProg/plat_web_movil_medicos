"""Clases de permiso de la app `accounts`. US-04.

Todas se apoyan en ``user.has_permission("modulo.recurso.accion")``, que
consulta ``UserRole -> RolePermission``.

**Nunca ``user.has_perm()``.** Es la primera regla que no se negocia del
reparto del Sprint 1, y no es una preferencia de estilo: las tablas de
``django.contrib.auth`` no llevan ``organization_id`` y no están protegidas por
RLS, así que responden contra los permisos de todas las organizaciones a la
vez. Un administrador de un centro médico pasaría el control con un permiso
que le concedió otro.

El Superadministrador de Plataforma no pasa ninguna de estas clases, y está
bien que así sea: su rol sólo lleva permisos del módulo ``platform``, y el
alcance del proyecto dice que no administra los datos internos de ningún
inquilino. Para lo suyo está ``tenancy.permissions.IsPlatformAdmin``.
"""

from rest_framework.permissions import BasePermission


class RequiresPermission(BasePermission):
    """Base: exige el código declarado en ``code``.

    Se hereda en lugar de instanciarse con un parámetro porque DRF recibe
    *clases* en ``permission_classes`` y las instancia él. Cada subclase se
    lee como una frase —``CanAssignRoles``— en la vista que la usa, que es lo
    que pide la convención de nombres.
    """

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


class CanReadRoles(RequiresPermission):
    code = "users.role.read"


class CanCreateRoles(RequiresPermission):
    code = "users.role.create"


class CanUpdateRoles(RequiresPermission):
    code = "users.role.update"


class CanDeleteRoles(RequiresPermission):
    code = "users.role.delete"


class CanAssignRoles(RequiresPermission):
    code = "users.role.assign"


class CanReadUsers(RequiresPermission):
    code = "users.user.read"
