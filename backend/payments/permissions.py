"""Permisos de `payments`. Se siembran en `migrations/0003_seed_permissions.py`
y `migrations/0005_seed_cash_permission.py`."""

from appointments.permissions import RequiresPermission


class CanCreatePayments(RequiresPermission):
    code = "payments.payment.create"


class CanRegisterCashPayments(RequiresPermission):
    """US-23: cobrar en efectivo en el mostrador. Recepción y administración."""

    code = "payments.payment.register_cash"
