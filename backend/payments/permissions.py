"""Permisos de `payments`. Se siembran en `migrations/0003_seed_permissions.py`."""

from appointments.permissions import RequiresPermission


class CanCreatePayments(RequiresPermission):
    code = "payments.payment.create"
