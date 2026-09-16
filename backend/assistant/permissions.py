"""Clase de permiso de la app `assistant`. US-31.

Un solo código: el asistente se consulta y nada más. No hay nada que crear ni
que editar por la API — el índice lo arma ``embed_catalog``, que es un comando
de consola y por lo tanto no necesita permiso de aplicación.

**Lo recibe el rol Paciente**, que es la excepción respecto de reportes y
respaldos: US-31 es una historia MÓVIL y el móvil es la aplicación del
paciente. Es, de hecho, la primera funcionalidad de este proyecto pensada para
que la use quien no trabaja en el centro médico.
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


class CanUseAssistant(RequiresPermission):
    code = "assistant.query.create"
