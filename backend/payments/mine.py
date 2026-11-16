"""US-46 — Los comprobantes del paciente: qué se consulta y de quién.

Una consulta (`Consulta`) dice *qué* pide el paciente —pagos o fichas, cuántos,
de cuándo, de qué especialidad—. **No dice de quién**: el alcance sale siempre
de la sesión (`alcance`) y es el titular y sus dependientes, nunca otro. Por
eso la frase dictada, el modelo y los parámetros de la URL no pueden cambiar
de quién son los datos: no hay por dónde entrar.

**Solo lo que tiene comprobante.** El comprobante es el QR de la ficha (US-19,
`appointments/receipts.py`) y existe solo para fichas `confirmed` o
`attended`. Se lista entonces:

- `pagos`: los pagos `succeeded` de esas fichas. «Factura» es un pago: no hay
  un modelo de factura. Un pago devuelto, pendiente o fallido no sale: no hay
  comprobante que mostrar.
- `fichas`: esas fichas.

El QR de un pago es el de su ficha. Si la ficha se reprogramó, el pago se
movió a la ficha nueva (`transfer_payment`, US-20) y sale con el código nuevo.

**La fecha.** Un pago se ubica por cuándo se pagó (`paid_at`) y una ficha por
cuándo es (`starts_at`), en hora local del proyecto: «los pagos de octubre» no
se corre un día por la zona horaria.
"""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

from django.db.models import F, Prefetch, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from appointments import receipts
from appointments.models import Appointment
from catalog.models import Specialty
from reporting.exporters import QRCelda

from .mine_voice import CANTIDAD_MAXIMA, TIPOS
from .models import Payment

# Qué fichas tienen comprobante (US-19).
CON_COMPROBANTE = (Appointment.Status.CONFIRMED, Appointment.Status.ATTENDED)
# Sin cantidad, esto.
CANTIDAD_POR_OMISION = 20
FORMATOS = ("json", "pdf")

ENCABEZADOS_PDF = [
    "Fecha", "Paciente", "Profesional", "Especialidad", "Sucursal", "Detalle",
    "Comprobante",
]
ESTADOS = {
    Appointment.Status.CONFIRMED: "Confirmada",
    Appointment.Status.ATTENDED: "Atendida",
}


@dataclass(frozen=True)
class Consulta:
    tipo: str
    cantidad: int | None = None
    desde: dt.date | None = None
    hasta: dt.date | None = None
    especialidad: uuid.UUID | None = None

    @property
    def limite(self) -> int:
        return self.cantidad or CANTIDAD_POR_OMISION

    @property
    def filtros(self) -> int:
        """Cuántos criterios trae, sin contar el tipo."""
        return sum(
            valor is not None
            for valor in (self.cantidad, self.desde, self.hasta, self.especialidad)
        )


# ==========================================================================
#  Los parámetros
# ==========================================================================
def parse_consulta(params, organization):
    """`(Consulta, {})` o `(None, errores)`. Revalida todo: el cliente no manda.

    Solo se leen `tipo`, `cantidad`, `desde`, `hasta` y `especialidad`. Un
    `paciente`, un `patient_id` o una `organizacion` en la URL se ignoran: no
    están en la lista y no hay dónde enchufarlos.
    """
    errores: dict[str, list[str]] = {}
    hoy = timezone.localdate()

    tipo = params.get("tipo")
    if tipo not in TIPOS:
        errores["tipo"] = ["Tiene que ser «pagos» o «fichas»."]

    cantidad = None
    crudo = params.get("cantidad")
    if crudo not in (None, ""):
        try:
            cantidad = int(crudo)
        except (TypeError, ValueError):
            cantidad = 0
        if not 1 <= cantidad <= CANTIDAD_MAXIMA:
            errores["cantidad"] = [f"Tiene que ser un número de 1 a {CANTIDAD_MAXIMA}."]
            cantidad = None

    fechas = {}
    for campo in ("desde", "hasta"):
        valor = params.get(campo)
        if valor in (None, ""):
            continue
        try:
            fecha = dt.date.fromisoformat(valor)
        except (TypeError, ValueError):
            errores[campo] = ["Tiene que ser una fecha AAAA-MM-DD."]
            continue
        if not 2000 <= fecha.year <= hoy.year + 1:
            errores[campo] = ["Es una fecha fuera de rango."]
            continue
        fechas[campo] = fecha
    if len(fechas) == 2 and fechas["desde"] > fechas["hasta"]:
        errores["desde"] = ["No puede ser posterior a «hasta»."]

    especialidad = None
    crudo = params.get("especialidad")
    if crudo not in (None, ""):
        try:
            especialidad = uuid.UUID(str(crudo))
        except ValueError:
            errores["especialidad"] = ["No es una especialidad válida."]
        else:
            # Una especialidad de otro centro no existe para este paciente.
            if not Specialty.objects.filter(
                id=especialidad, organization=organization, is_active=True,
            ).exists():
                errores["especialidad"] = ["No es una especialidad de este centro."]
                especialidad = None

    if errores:
        return None, errores
    return Consulta(tipo, cantidad, fechas.get("desde"), fechas.get("hasta"),
                    especialidad), {}


# ==========================================================================
#  El alcance
# ==========================================================================
def alcance(user, prefijo: str = "") -> Q:
    """Las fichas del titular y las de sus dependientes. Sale de la sesión.

    Mismo criterio que `appointments/booking.py` y `owns_appointment`. Quien
    llama ya garantizó el perfil de paciente (`IsPatientProfile`).
    """
    titular = user.patient_profile
    return (
        Q(**{f"{prefijo}patient_id": titular.id})
        | Q(**{f"{prefijo}patient__guardian_id": titular.id})
    )


def _inicio_del_dia(fecha: dt.date) -> dt.datetime:
    return timezone.make_aware(dt.datetime.combine(fecha, dt.time.min))


# ==========================================================================
#  La consulta
# ==========================================================================
def consultar(user, consulta: Consulta):
    """El queryset de lo que pidió, más reciente primero y sin cortar."""
    organizacion = user.organization

    if consulta.tipo == "pagos":
        prefijo = "appointment__"
        consulta_base = (
            Payment.objects
            .filter(organization=organizacion,
                    status=Payment.Status.SUCCEEDED,
                    appointment__organization=organizacion,
                    appointment__status__in=CON_COMPROBANTE)
            .filter(alcance(user, prefijo))
            # `paid_at` siempre se fija al confirmar (payments/services.py);
            # el respaldo es por si alguna fila vieja no lo tuviera.
            .annotate(fecha=Coalesce("paid_at", "created_at"))
            .select_related(
                "appointment__patient", "appointment__practitioner",
                "appointment__branch", "appointment__organization",
            )
            .prefetch_related(Prefetch("appointment__practitioner__specialties"))
        )
    else:
        prefijo = ""
        consulta_base = (
            Appointment.objects
            .filter(organization=organizacion, status__in=CON_COMPROBANTE)
            .filter(alcance(user))
            .annotate(fecha=F("starts_at"))
            .select_related("patient", "practitioner", "branch", "organization")
            .prefetch_related("practitioner__specialties")
        )

    if consulta.desde:
        consulta_base = consulta_base.filter(fecha__gte=_inicio_del_dia(consulta.desde))
    if consulta.hasta:
        # `lt` el día siguiente a las 00:00: incluye todo el último día.
        consulta_base = consulta_base.filter(
            fecha__lt=_inicio_del_dia(consulta.hasta + dt.timedelta(days=1)),
        )
    if consulta.especialidad:
        consulta_base = consulta_base.filter(
            **{f"{prefijo}practitioner__specialties": consulta.especialidad},
        )
    return consulta_base.order_by("-fecha", "-id")


def listar(user, consulta: Consulta):
    """`(objetos, truncado)`: hasta `limite`, y si había más."""
    pedidos = list(consultar(user, consulta)[: consulta.limite + 1])
    return pedidos[: consulta.limite], len(pedidos) > consulta.limite


# ==========================================================================
#  Lo que se devuelve
# ==========================================================================
def serializar(objeto, tipo: str, titular) -> dict:
    """Un ítem de la lista, con el código del QR de su ficha."""
    cita = objeto.appointment if tipo == "pagos" else objeto
    paciente = cita.patient
    item = {
        "id": str(objeto.id),
        "appointment_id": str(cita.id),
        "code": receipts.issue_code(cita),
        "date": objeto.fecha.isoformat(),
        "starts_at": cita.starts_at.isoformat(),
        "patient_name": paciente.full_name,
        "is_dependent": paciente.id != titular.id,
        "practitioner_name": cita.practitioner.full_name,
        "specialties": [s.name for s in cita.practitioner.specialties.all()],
        "branch_name": cita.branch.name,
        "status": cita.status,
        "amount": None, "currency": None, "provider": None, "paid_at": None,
    }
    if tipo == "pagos":
        item.update(
            amount=str(objeto.amount), currency=objeto.currency,
            provider=objeto.provider,
            paid_at=objeto.paid_at.isoformat() if objeto.paid_at else None,
        )
    return item


def titulo_del_pdf(consulta: Consulta) -> str:
    return ("Mis comprobantes de pagos" if consulta.tipo == "pagos"
            else "Mis comprobantes de fichas")


def filas_del_pdf(items: list[dict]) -> list[list]:
    """Una fila por ítem; el código va como `QRCelda` y se dibuja en el PDF."""
    filas = []
    for item in items:
        fecha = timezone.localtime(dt.datetime.fromisoformat(item["date"]))
        detalle = (f"{item['amount']} {item['currency']}" if item["amount"]
                   else ESTADOS.get(item["status"], item["status"]))
        filas.append([
            f"{fecha:%d/%m/%Y %H:%M}",
            item["patient_name"] + (" (dependiente)" if item["is_dependent"] else ""),
            item["practitioner_name"],
            ", ".join(item["specialties"]),
            item["branch_name"],
            detalle,
            QRCelda(item["code"]),
        ])
    return filas
