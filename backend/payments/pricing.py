"""US-18 — Cuánto cuesta una ficha.

El catálogo ya tiene precios desde US-32 (`catalog.Service`). El arancel de
una ficha es el servicio de tipo **consulta** con precio de alguna de las
especialidades del profesional; si tiene varias, el más bajo —una ficha no
dice de cuál especialidad es, y cobrar el más caro sería cobrar de más—. Sin
ninguno, el arancel por omisión de `settings.APPOINTMENT_DEFAULT_FEE`.

Lo decide el backend (regla 10 del Sprint 2): el móvil sólo lo muestra.
"""

from decimal import Decimal

from django.conf import settings

from catalog.models import Service


def quote(appointment) -> tuple[Decimal, str]:
    """Devuelve `(importe, moneda)` de la ficha."""
    servicio = (
        Service.objects
        .filter(
            organization_id=appointment.organization_id,
            kind=Service.Kind.CONSULTATION,
            is_active=True,
            price__gt=0,
            specialty__in=appointment.practitioner.specialties.all(),
        )
        .order_by("price")
        .first()
    )
    if servicio is not None:
        return servicio.price, servicio.currency
    return (
        Decimal(settings.APPOINTMENT_DEFAULT_FEE),
        settings.APPOINTMENT_FEE_CURRENCY,
    )
