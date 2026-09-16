"""Clases de permiso de DRF para fichas.

Los códigos se siembran en
`accounts/migrations/0004_seed_permissions_sprint_2_appointments.py`.
`appointments.appointment.create` y `.cancel` los tiene el rol *Paciente*: son
los que usan US-17 y US-20 desde la aplicación del paciente.
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


class CanReadAppointments(RequiresPermission):
    code = "appointments.appointment.read"


class CanCreateAppointments(RequiresPermission):
    code = "appointments.appointment.create"


class CanCancelAppointments(RequiresPermission):
    code = "appointments.appointment.cancel"


class CanRescheduleAppointments(RequiresPermission):
    code = "appointments.appointment.reschedule"
