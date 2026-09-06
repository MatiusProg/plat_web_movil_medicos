"""Clases de permiso de DRF para agendas, bloqueos y disponibilidad.

Los códigos ya están sembrados en
`accounts/migrations/0003_seed_permissions_sprint_1.py`. `scheduling.slot.read`
lo tiene también el rol *Paciente*: es lo que la app móvil consume en US-15 y
US-16.
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


class CanReadSchedules(RequiresPermission):
    code = "scheduling.schedule.read"


class CanCreateSchedules(RequiresPermission):
    code = "scheduling.schedule.create"


class CanUpdateSchedules(RequiresPermission):
    code = "scheduling.schedule.update"


class CanReadBlocks(RequiresPermission):
    code = "scheduling.block.read"


class CanCreateBlocks(RequiresPermission):
    code = "scheduling.block.create"


class CanUpdateBlocks(RequiresPermission):
    code = "scheduling.block.update"


class CanReadSlots(RequiresPermission):
    code = "scheduling.slot.read"
