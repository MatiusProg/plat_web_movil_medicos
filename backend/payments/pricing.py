"""US-18 — Cuánto cuesta una ficha.

El catálogo ya tiene precios desde US-32 (`catalog.Service`), y es lo que el
asistente le informa al paciente. **El cobro tiene que decir lo mismo que el
asistente**: si el chat contesta "la consulta de especialidad cuesta Bs 150",
la ficha no puede cobrar Bs 100.

En la práctica los servicios de consulta casi nunca están asociados a una
especialidad (el dataset los carga como "Consulta de Medicina general" y
"Consulta de especialidad", sin `specialty`). Por eso se busca en este orden,
siempre entre servicios de tipo **consulta**, activos y con precio:

1. el asociado a alguna especialidad del profesional;
2. el que **nombra** alguna de sus especialidades ("Consulta de Medicina
   general" para un médico general);
3. la consulta genérica: la que no está asociada ni nombra a ninguna
   especialidad del catálogo ("Consulta de especialidad");
4. el arancel por omisión de `settings.APPOINTMENT_DEFAULT_FEE`.

Si hay varios candidatos en el mismo paso, el más barato: una ficha no dice de
cuál especialidad es, y cobrar el más caro sería cobrar de más.

Lo decide el backend (regla 10 del Sprint 2): el móvil y la web sólo lo
muestran.
"""

from decimal import Decimal

from django.conf import settings

from catalog.models import Service, Specialty


def _mas_barato(servicios):
    con_precio = [s for s in servicios if s.price]
    return min(con_precio, key=lambda s: s.price) if con_precio else None


def quote(appointment) -> tuple[Decimal, str]:
    """Devuelve `(importe, moneda)` de la ficha."""
    consultas = list(
        Service.objects.filter(
            organization_id=appointment.organization_id,
            kind=Service.Kind.CONSULTATION,
            is_active=True,
            price__gt=0,
        )
    )
    especialidades = list(appointment.practitioner.specialties.all())
    ids = {e.id for e in especialidades}
    nombres = [e.name.lower() for e in especialidades]

    servicio = (
        _mas_barato([s for s in consultas if s.specialty_id in ids])
        or _mas_barato([s for s in consultas
                        if any(n in s.name.lower() for n in nombres)])
    )
    if servicio is None:
        todas = [
            n.lower() for n in Specialty.objects.filter(
                organization_id=appointment.organization_id,
            ).values_list("name", flat=True)
        ]
        servicio = _mas_barato([
            s for s in consultas
            if s.specialty_id is None and not any(n in s.name.lower() for n in todas)
        ])

    if servicio is not None:
        return servicio.price, servicio.currency
    return (
        Decimal(settings.APPOINTMENT_DEFAULT_FEE),
        settings.APPOINTMENT_FEE_CURRENCY,
    )
