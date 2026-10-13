"""US-33 — Lo que el paciente pide del horario, dicho con sus palabras.

"El jueves por la tarde", "mañana temprano", "la semana que viene". Se lee
con reglas y no con el modelo de lenguaje, por la misma razón que la barrera
de urgencias: **el horario es lo único de la reserva que el modelo no toca.**
El reparto lo pide así —los turnos salen de la disponibilidad, no del texto
del modelo— y la forma más corta de cumplirlo es que el modelo ni siquiera
traduzca la preferencia. Además no gasta cuota, y una prueba lo verifica sin
red.

Lo que no se entiende se ignora: una preferencia vacía es "lo más próximo",
que es una respuesta útil. Una preferencia mal entendida no lo es, así que
ante la duda las reglas prefieren no filtrar.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

from .embeddings import normalize_text

# Cuántos días hacia adelante se buscan turnos si el paciente no dice cuándo.
# Igual que la tarjeta de US-16 (`next_available_slot`).
DEFAULT_HORIZON_DAYS = 14

WEEKDAYS = {
    "lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
    "viernes": 4, "sabado": 5, "domingo": 6,
}

# Franjas del día, en la hora local de la sucursal: [desde, hasta).
PARTS_OF_DAY = {
    "manana": (dt.time(0, 0), dt.time(12, 0)),
    "tarde": (dt.time(12, 0), dt.time(19, 0)),
    "noche": (dt.time(19, 0), dt.time.max),
}

# "mañana" es el día siguiente salvo que vaya con artículo: "en la mañana",
# "por la mañana", "de la mañana", "a la mañana". "temprano" también es la
# mañana; "mañana temprano" es las dos cosas a la vez.
_MORNING = re.compile(r"\b(?:en|por|de|a) la manana\b|\btemprano\b")
_AFTERNOON = re.compile(r"\b(?:en|por|de|a) la tarde\b|\bpor la tarde\b|\btarde\b")
_NIGHT = re.compile(r"\b(?:en|por|de|a) la noche\b|\bnoche\b")
_TOMORROW = re.compile(r"(?<!la )(?<!pasado )\bmanana\b")
_DAY_AFTER_TOMORROW = re.compile(r"\bpasado manana\b")
_TODAY = re.compile(r"\bhoy\b")
_NEXT_WEEK = re.compile(
    r"\b(?:la )?(?:proxima semana|semana que viene|siguiente semana)\b",
)
_THIS_WEEK = re.compile(r"\besta semana\b")
_WEEKEND = re.compile(r"\bfin de semana\b")
_WEEKDAY = re.compile(r"\b(" + "|".join(WEEKDAYS) + r")\b")


@dataclass(frozen=True)
class Preference:
    """Qué turnos le sirven al paciente.

    ``days`` vacío es cualquier día de la ventana. ``part_of_day`` vacío es
    cualquier hora.
    """

    date_from: dt.date
    date_to: dt.date
    days: frozenset[dt.date] = frozenset()
    part_of_day: str = ""

    @property
    def is_empty(self) -> bool:
        return not self.days and not self.part_of_day

    def accepts(self, start: dt.datetime) -> bool:
        """¿Ese inicio de turno —con la zona de su sucursal— le sirve?"""
        local_day = start.date()
        if self.days and local_day not in self.days:
            return False
        if self.part_of_day:
            desde, hasta = PARTS_OF_DAY[self.part_of_day]
            if not (desde <= start.time() < hasta):
                return False
        return True

    def as_dict(self) -> dict:
        return {
            "date_from": self.date_from.isoformat(),
            "date_to": self.date_to.isoformat(),
            "days": sorted(day.isoformat() for day in self.days),
            "part_of_day": self.part_of_day or None,
        }


def _next_weekday(today: dt.date, weekday: int) -> dt.date:
    """El próximo día con ese nombre, contando hoy: "el jueves" dicho un
    jueves a las 8 es hoy, si todavía queda algún turno."""
    return today + dt.timedelta(days=(weekday - today.weekday()) % 7)


def _week_of(day: dt.date) -> set[dt.date]:
    lunes = day - dt.timedelta(days=day.weekday())
    return {lunes + dt.timedelta(days=offset) for offset in range(7)}


def parse(text: str, *, today: dt.date) -> Preference:
    """Interpreta la preferencia. Nunca falla: lo que no entiende, no filtra."""
    normalized = normalize_text(text)
    days: set[dt.date] = set()

    if _DAY_AFTER_TOMORROW.search(normalized):
        days.add(today + dt.timedelta(days=2))
    elif _TOMORROW.search(normalized):
        days.add(today + dt.timedelta(days=1))
    if _TODAY.search(normalized):
        days.add(today)

    weekdays = {WEEKDAYS[name] for name in _WEEKDAY.findall(normalized)}
    if _NEXT_WEEK.search(normalized):
        semana = _week_of(today + dt.timedelta(days=7))
        # "el martes de la semana que viene": sólo ese día de esa semana.
        days |= {d for d in semana if not weekdays or d.weekday() in weekdays}
        weekdays = set()
    elif _THIS_WEEK.search(normalized):
        semana = {d for d in _week_of(today) if d >= today}
        days |= {d for d in semana if not weekdays or d.weekday() in weekdays}
        weekdays = set()
    if _WEEKEND.search(normalized):
        weekdays |= {5, 6}
    days |= {_next_weekday(today, weekday) for weekday in weekdays}

    part_of_day = ""
    if _MORNING.search(normalized):
        part_of_day = "manana"
    elif _NIGHT.search(normalized):
        part_of_day = "noche"
    elif _AFTERNOON.search(normalized):
        part_of_day = "tarde"

    date_from = today
    date_to = today + dt.timedelta(days=DEFAULT_HORIZON_DAYS)
    if days:
        # Todo lo que se arma arriba cae de hoy en adelante.
        date_from, date_to = min(days), max(days)
    return Preference(
        date_from=date_from,
        date_to=date_to,
        days=frozenset(days),
        part_of_day=part_of_day,
    )


# Lo que hace que una consulta de orientación sea, además, un pedido de
# reserva: "quiero sacar ficha", "necesito un turno con cardiología".
_BOOKING_INTENT = re.compile(
    r"\b(?:reserv\w*|agend\w*|sacar (?:una )?(?:ficha|cita|turno|hora)"
    r"|(?:una|la|mi) (?:ficha|cita|turno)|turnos?|horarios?|disponib\w*"
    r"|cuando (?:atiende|hay))\b",
)


def has_booking_intent(text: str) -> bool:
    """¿El paciente pide reservar, además de contar lo que le pasa?"""
    return bool(_BOOKING_INTENT.search(normalize_text(text)))
