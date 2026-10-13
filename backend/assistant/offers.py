"""US-33 — Los turnos que el asistente ofrece.

**Salen de la disponibilidad de US-15, nunca del modelo.** Se le pregunta a
``consolidated_availability`` —la misma función que alimenta la pantalla de
reserva— por cada profesional activo de la especialidad, y se ofrece lo que
devolvió. El modelo de lenguaje no participa: ni elige el turno ni lo
redacta, así que no puede ofrecer uno que no existe.

Ofrecer no es apartar. Entre que se muestra un turno y que el paciente toca
*Confirmar*, otro puede reservarlo; eso lo resuelve ``book_appointment`` con
su bloqueo y su índice único, y el paciente recibe un 409 y elige otro.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter

from django.core.exceptions import ValidationError
from django.utils import timezone

from catalog.models import Practitioner
from scheduling.availability import consolidated_availability

from .preferences import Preference

# Cuántos turnos se muestran. Más que esto ya no es una conversación, es la
# pantalla de reserva; para eso está la pantalla de reserva.
MAX_OFFERS = 6
# Cuántos de esos pueden ser del mismo profesional, para que el paciente
# tenga con quién elegir cuando la especialidad tiene más de uno.
MAX_PER_PRACTITIONER = 3


def offer_slots(
    organization, specialty, preference: Preference, *, branch_id=None,
    now: dt.datetime | None = None,
) -> list[dict]:
    """Los próximos turnos reservables de la especialidad que cumplen la
    preferencia, del más cercano al más lejano."""
    now = now or timezone.now()
    practitioners = (
        Practitioner.objects.filter(
            organization=organization, is_active=True, specialties=specialty,
        )
        .distinct()
        .order_by("last_name", "first_name")
    )

    candidatos = []
    for practitioner in practitioners:
        try:
            data = consolidated_availability(
                practitioner_id=practitioner.id,
                date_from=preference.date_from,
                date_to=preference.date_to,
                branch_id=branch_id,
                now=now,
            )
        except ValidationError:
            # Rango fuera del horizonte configurado: no hay nada que ofrecer
            # de este profesional, pero los demás pueden tener.
            continue
        for day in data["days"]:
            for slot in day["slots"]:
                if not slot["reservable"]:
                    continue
                inicio = dt.datetime.fromisoformat(slot["start"])
                if not preference.accepts(inicio):
                    continue
                candidatos.append({
                    "practitioner": {
                        "id": str(practitioner.id),
                        "full_name": practitioner.full_name,
                    },
                    "branch": slot["branch"],
                    "schedule": slot["schedule"],
                    "start": slot["start"],
                    "end": slot["end"],
                    "_inicio": inicio,
                })

    candidatos.sort(key=lambda c: (c["_inicio"], c["practitioner"]["full_name"]))
    por_profesional: Counter = Counter()
    elegidos, salteados = [], []
    for candidato in candidatos:
        quien = candidato["practitioner"]["id"]
        if por_profesional[quien] >= MAX_PER_PRACTITIONER:
            salteados.append(candidato)
            continue
        por_profesional[quien] += 1
        elegidos.append(candidato)
        if len(elegidos) == MAX_OFFERS:
            break
    # Si los demás no alcanzaron a llenar la lista —o la especialidad tiene
    # un solo profesional—, se completa con lo que se había salteado.
    if len(elegidos) < MAX_OFFERS:
        elegidos += salteados[: MAX_OFFERS - len(elegidos)]
        elegidos.sort(key=lambda c: (c["_inicio"], c["practitioner"]["full_name"]))
    for elegido in elegidos:
        elegido.pop("_inicio")
    return elegidos
