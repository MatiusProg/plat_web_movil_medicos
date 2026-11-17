"""Permisos de `payments`. Se siembran en `migrations/0003_seed_permissions.py`
y `migrations/0005_seed_cash_permission.py`."""

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from appointments.permissions import RequiresPermission


class CanCreatePayments(RequiresPermission):
    code = "payments.payment.create"


class CanRegisterCashPayments(RequiresPermission):
    """US-23: cobrar en efectivo en el mostrador. Recepción y administración."""

    code = "payments.payment.register_cash"


class IsPatientProfile(BasePermission):
    """US-46: quien consulta sus comprobantes es un paciente con perfil activo.

    El personal del centro no usa «mis comprobantes», y sin perfil no hay a
    quién acotar la consulta. Va después de `IsAuthenticated`: un usuario sin
    sesión recibe 401, no esto.
    """

    def has_permission(self, request, view):
        perfil = getattr(request.user, "patient_profile", None)
        if perfil is None or not perfil.is_active:
            raise PermissionDenied({
                "code": "sin_perfil_de_paciente",
                "detail": "Esta consulta es para pacientes con perfil activo.",
            })
        return True
