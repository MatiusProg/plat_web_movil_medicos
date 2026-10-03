"""Permisos de la atención médica (US-24).

Los códigos se siembran en `encounters/migrations/0003_seed_permissions.py` y
sólo los tiene el rol Médico. **El permiso es condición necesaria, no
suficiente**: además hay que ser el profesional de la ficha, y eso lo decide
`services.is_own` con el objeto en la mano.
"""

from rest_framework.permissions import BasePermission


class RequiresPermission(BasePermission):
    code = ""
    message = "No tenés permiso para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and self.code
            and user.has_permission(self.code)
        )


class CanReadEncounters(RequiresPermission):
    code = "encounters.encounter.read"


class CanCreateEncounters(RequiresPermission):
    code = "encounters.encounter.create"


class CanAmendEncounters(RequiresPermission):
    code = "encounters.encounter.amend"
