"""US-35 — Las variables del modelo y la etiqueta, en un solo lugar.

**La etiqueta es la inasistencia de US-29**, no una definición nueva: se
reutilizan ``debian_atenderse_q`` e ``inasistencia_q`` de ``appointments/kpis.py``.
Una ficha cancelada a tiempo no cuenta; una confirmada que ya pasó sin check-in
sí. Así el modelo intenta anticipar el mismo número que muestra el panel.

**Qué variables y por qué** (las que el reparto del Sprint 4 nombra):

=================  ==========================================================
``lead_days``      Días entre que se reservó y el turno. Reservar con mucha
                   anticipación deja tiempo para olvidarse.
``paid_early``     Pagó al menos 24 h antes. Pagar en ventanilla el mismo día
                   no compromete a nadie de antemano.
``prior_no_shows`` Faltas del paciente en fichas que terminaron antes de ésta.
``prior_visits``   Veces que sí fue, con el mismo criterio.
``dow_0``..``5``   Día de la semana (lunes a sábado; el domingo es la base).
``afternoon``      El turno es de las 14:00 en adelante.
=================  ==========================================================

**Lo que no entra, a propósito.** ``attendance_confirmed_at`` cambia con el
tiempo: en una ficha vieja ya tiene su valor final, en una futura todavía no.
Entrenar con él enseñaría al modelo algo que al predecir no existe (fuga de
datos). Queda para una versión posterior, con su propia medición.

**Sin fuga.** «Faltas previas» cuenta sólo fichas del mismo paciente cuyo turno
*terminó* antes de que empezara ésta; nunca la propia ficha ni las posteriores.
En entrenamiento y al predecir se calcula con el mismo código.
"""

from __future__ import annotations

import bisect
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass
from zoneinfo import ZoneInfo

from appointments.kpis import debian_atenderse_q
from appointments.models import Appointment
from payments.models import Payment

LEAD_DAYS_CAP = 60
PAID_EARLY_HOURS = 24
PRIOR_NO_SHOWS_CAP = 5
PRIOR_VISITS_CAP = 20
AFTERNOON_FROM = 14

# Lunes a sábado. El domingo no tiene columna: es lo que queda cuando todas valen 0.
DAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]

FEATURE_NAMES = [
    "lead_days", "paid_early", "prior_no_shows", "prior_visits",
    *[f"dow_{i}" for i in range(len(DAYS))],
    "afternoon",
]

# `__in` con miles de valores es legal pero lento de planificar: se trocea.
_CHUNK = 1000


@dataclass
class Row:
    appointment_id: object
    values: list[float]
    label: int | None = None


def label_of(ficha: Appointment) -> int:
    """1 si la ficha fue una inasistencia. Sólo vale para fichas que ya debían atenderse."""
    ausente = ficha.status == Appointment.Status.NO_SHOW or (
        ficha.status == Appointment.Status.CONFIRMED and ficha.checked_in_at is None
    )
    return int(ausente)


def _chunks(items, size=_CHUNK):
    items = list(items)
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _earliest_payments(organization, appointment_ids) -> dict:
    """El primer pago exitoso de cada ficha."""
    paid = {}
    for grupo in _chunks(appointment_ids):
        filas = Payment.objects.filter(
            organization=organization, appointment_id__in=grupo,
            status=Payment.Status.SUCCEEDED, paid_at__isnull=False,
        ).values_list("appointment_id", "paid_at")
        for appointment_id, paid_at in filas:
            if appointment_id not in paid or paid_at < paid[appointment_id]:
                paid[appointment_id] = paid_at
    return paid


def _histories(organization, patient_ids, as_of) -> dict:
    """Por paciente: fichas terminadas, ordenadas por fin, con su acumulado de faltas.

    Devuelve ``{paciente: (fines, faltas_acumuladas)}``: ``faltas_acumuladas[i]``
    son las faltas entre las primeras ``i`` fichas, de modo que las previas a un
    instante salen con una búsqueda binaria y sin recorrer la lista cada vez.
    """
    por_paciente = defaultdict(list)
    for grupo in _chunks(patient_ids):
        filas = (
            Appointment.objects
            .filter(organization=organization, patient_id__in=grupo)
            .filter(debian_atenderse_q(as_of))
            .values_list("patient_id", "ends_at", "status", "checked_in_at")
        )
        for patient_id, ends_at, status, checked_in_at in filas:
            ausente = status == Appointment.Status.NO_SHOW or (
                status == Appointment.Status.CONFIRMED and checked_in_at is None
            )
            por_paciente[patient_id].append((ends_at, int(ausente)))

    historias = {}
    for patient_id, fichas in por_paciente.items():
        fichas.sort()
        fines = [f[0] for f in fichas]
        acumulado = [0]
        for _fin, ausente in fichas:
            acumulado.append(acumulado[-1] + ausente)
        historias[patient_id] = (fines, acumulado)
    return historias


def build_rows(organization, fichas, as_of) -> list[Row]:
    """Las variables de cada ficha. Supone el ``tenant_context`` de la organización.

    ``as_of`` es el instante «desde el que se mira»: para entrenar, ahora; para
    predecir, también ahora. Define qué fichas del paciente ya terminaron.
    """
    fichas = list(fichas)
    if not fichas:
        return []
    tz = ZoneInfo(organization.timezone or "America/La_Paz")
    pagos = _earliest_payments(organization, [f.id for f in fichas])
    historias = _histories(organization, {f.patient_id for f in fichas}, as_of)
    margen = dt.timedelta(hours=PAID_EARLY_HOURS)

    filas = []
    for f in fichas:
        anticipacion = (f.starts_at - f.created_at).total_seconds() / 86400
        anticipacion = min(max(anticipacion, 0.0), float(LEAD_DAYS_CAP))

        pagado = pagos.get(f.id)
        pago_adelantado = 1.0 if pagado is not None and pagado <= f.starts_at - margen else 0.0

        faltas = visitas = 0
        historia = historias.get(f.patient_id)
        if historia is not None:
            fines, acumulado = historia
            # Fichas que terminaron antes de que empezara ésta. La propia
            # termina después de empezar, así que nunca entra.
            n = bisect.bisect_right(fines, f.starts_at)
            faltas = acumulado[n]
            visitas = n - faltas

        local = f.starts_at.astimezone(tz)
        dia = [1.0 if local.weekday() == i else 0.0 for i in range(len(DAYS))]
        filas.append(Row(
            appointment_id=f.id,
            values=[
                anticipacion, pago_adelantado,
                float(min(faltas, PRIOR_NO_SHOWS_CAP)), float(min(visitas, PRIOR_VISITS_CAP)),
                *dia,
                1.0 if local.hour >= AFTERNOON_FROM else 0.0,
            ],
        ))
    return filas


# --------------------------------------------------------------------------
#  Cómo se le explica a quien lo lee
# --------------------------------------------------------------------------

def _plural(n, uno, varios):
    return uno if n == 1 else varios


def describe(name: str, value: float) -> str | None:
    """La razón en español para una variable con ese valor, o ``None`` si no aporta decirla.

    Una variable de día con valor 0 («no es lunes») no se dice: el modelo la usa,
    pero «no es lunes» no le explica nada a quien lee.
    """
    if name == "lead_days":
        dias = round(value)
        return f"Reservó con {dias} {_plural(dias, 'día', 'días')} de anticipación"
    if name == "paid_early":
        return "Pagó por adelantado" if value >= 0.5 else "No pagó por adelantado"
    if name == "prior_no_shows":
        n = int(round(value))
        return "Sin faltas previas" if n == 0 else f"{n} {_plural(n, 'falta previa', 'faltas previas')}"
    if name == "prior_visits":
        n = int(round(value))
        return "Sin visitas previas registradas" if n == 0 else (
            f"{n} {_plural(n, 'visita previa', 'visitas previas')}")
    if name.startswith("dow_"):
        return f"Turno de {DAYS[int(name[4:])]}" if value >= 0.5 else None
    if name == "afternoon":
        return "Turno de tarde" if value >= 0.5 else "Turno de mañana"
    return None
