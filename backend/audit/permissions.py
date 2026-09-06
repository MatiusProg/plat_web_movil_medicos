"""Clase de permiso de la app `audit`. US-06 (h).

Un solo código, ``audit.log.read``, porque la bitácora sólo se lee: el punto
(f) dice que no expone verbos de escritura ni siquiera al administrador, así
que no existe ``audit.log.create`` que otorgar.

**De dónde sale el código.** El catálogo del Sprint 0 declaró
``users.audit.read``, antes de que existiera esta app. El punto (h) de la
historia nombra ``audit.log.read``, que además es el que sale de aplicar la
convención ``modulo.recurso.accion`` con el módulo real. La migración
``accounts/0005_us06_audit`` crea el nuevo y borra el viejo, que nunca autorizó
nada: no había ni una vista que lo consultara.
"""

from rest_framework.permissions import BasePermission


class RequiresPermission(BasePermission):
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


class CanReadAuditLog(RequiresPermission):
    code = "audit.log.read"
