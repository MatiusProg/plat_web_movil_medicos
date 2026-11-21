"""US-50 — La contabilidad: ingresos, devoluciones, comisión, honorarios,
gastos y utilidad.

Todo el cálculo está acá y es de Python. La voz (``finance_voice.py``) solo
traduce una frase a ``{período, agrupar, filtros}``: nunca decide una cifra.

**Qué cuenta cada columna** (por moneda, nunca mezcladas):

- ``ingresos``: pagos cobrados (``succeeded`` o después devueltos) por la fecha
  de **cobro** (``paid_at``).
- ``devoluciones``: pagos devueltos, por la fecha de **devolución**
  (``refunded_at``). Un pago cobrado en octubre y devuelto en noviembre suma en
  octubre y resta en noviembre: cada mes dice lo que de verdad pasó en él.
- ``comision``: el porcentaje de la pasarela sobre lo cobrado y **no devuelto**
  (el efectivo en ventanilla no tiene comisión).
- ``honorarios``: el porcentaje del profesional sobre lo cobrado y no devuelto.
- ``gastos``: lo cargado a mano (``Expense``) por su fecha.
- ``utilidad`` = ingresos − devoluciones − comisión − honorarios − gastos.

Cada comisión y honorario se redondea al centavo **por pago**, así que la suma
de los grupos es siempre igual al total.

**Agrupar es solo presentación.** El total no cambia con el criterio: cada
evento cae en exactamente un grupo. Un gasto que no se puede atribuir al
criterio (un gasto general ante «por médico») va a un grupo propio.
"""

import datetime as dt
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from appointments import kpis
from catalog.models import PractitionerSpecialty
from payments.models import Payment

from .models import Expense, FinanceSettings

CENTAVO = Decimal("0.01")
CERO = Decimal("0.00")
AGRUPACIONES = ("sede", "medico", "especialidad", "dia", "semana", "mes", "trimestre")
SIN_AGRUPAR = "total"
SIN_ESPECIALIDAD = "Sin especialidad"
GASTOS_GENERALES = "Gastos generales"
MESES_DE_LA_SERIE = 6

CAMPOS = ("ingresos", "devoluciones", "comision", "honorarios", "gastos")


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def porcentaje_de(monto: Decimal, porcentaje: Decimal) -> Decimal:
    return redondear(monto * porcentaje / Decimal("100"))


def ajustes_de(organizacion) -> FinanceSettings:
    ajustes, _ = FinanceSettings.objects.get_or_create(organization=organizacion)
    return ajustes


class _Acumulador:
    """Las sumas de un grupo, para una moneda."""

    __slots__ = ("nombre", "orden", *CAMPOS, "pagos")

    def __init__(self, nombre="", orden=""):
        self.nombre = nombre
        self.orden = orden
        for campo in CAMPOS:
            setattr(self, campo, CERO)
        self.pagos = 0

    @property
    def utilidad(self):
        return (self.ingresos - self.devoluciones - self.comision
                - self.honorarios - self.gastos)

    @property
    def ticket_promedio(self):
        if not self.pagos:
            return None
        return redondear(self.ingresos / self.pagos)

    def a_dict(self):
        return {
            "ingresos": str(self.ingresos),
            "devoluciones": str(self.devoluciones),
            "neto": str(self.ingresos - self.devoluciones),
            "comision": str(self.comision),
            "honorarios": str(self.honorarios),
            "gastos": str(self.gastos),
            "utilidad": str(self.utilidad),
            "pagos": self.pagos,
            "ticket_promedio": (
                str(self.ticket_promedio) if self.ticket_promedio is not None else None
            ),
        }


def _inicio_de_semana(fecha: dt.date) -> dt.date:
    return fecha - dt.timedelta(days=fecha.weekday())


def clave_de_periodo(fecha: dt.date, agrupar: str):
    """``(clave, etiqueta)`` del bucket de tiempo de ``fecha``."""
    if agrupar == "dia":
        return fecha.isoformat(), fecha.strftime("%d/%m/%Y")
    if agrupar == "semana":
        lunes = _inicio_de_semana(fecha)
        domingo = lunes + dt.timedelta(days=6)
        return lunes.isoformat(), f"{lunes:%d/%m} al {domingo:%d/%m/%Y}"
    if agrupar == "mes":
        return f"{fecha:%Y-%m}", f"{fecha:%m/%Y}"
    trimestre = (fecha.month - 1) // 3 + 1
    return f"{fecha.year}-T{trimestre}", f"T{trimestre} {fecha.year}"


def _fecha_local(instante, tz) -> dt.date:
    return instante.astimezone(tz).date()


def _especialidades(organizacion) -> dict:
    """``{practitioner_id: nombre}``: la primera especialidad por nombre."""
    nombres = {}
    filas = (
        PractitionerSpecialty.objects
        .filter(organization=organizacion)
        .values_list("practitioner_id", "specialty__name")
        .order_by("specialty__name")
    )
    for practitioner_id, nombre in filas:
        nombres.setdefault(practitioner_id, nombre)
    return nombres


def calcular(organizacion, desde: dt.date, hasta: dt.date, *, branch_id=None,
             practitioner_id=None, agrupar=None) -> dict:
    """La contabilidad de ``[desde, hasta]``, por moneda y agrupada."""
    if agrupar and agrupar not in AGRUPACIONES:
        raise ValueError(f"Agrupación desconocida: {agrupar}")

    tz = ZoneInfo(organizacion.timezone or "America/La_Paz")
    inicio, fin = kpis.rango_utc(organizacion, desde, hasta)
    ajustes = ajustes_de(organizacion)
    porcentaje_pasarela = Decimal(ajustes.stripe_percent)
    especialidades = _especialidades(organizacion) if agrupar == "especialidad" else {}

    totales: dict[str, _Acumulador] = defaultdict(_Acumulador)
    grupos: dict[str, dict[str, _Acumulador]] = defaultdict(dict)

    def grupo(moneda, clave, nombre, orden=None):
        por_clave = grupos[moneda]
        if clave not in por_clave:
            por_clave[clave] = _Acumulador(nombre, orden if orden is not None else nombre)
        return por_clave[clave]

    def clave_de_pago(pago, fecha):
        cita = pago.appointment
        if agrupar == "sede":
            return str(cita.branch_id), cita.branch.name, cita.branch.name
        if agrupar == "medico":
            medico = cita.practitioner
            return str(medico.id), medico.full_name, medico.full_name
        if agrupar == "especialidad":
            nombre = especialidades.get(cita.practitioner_id, SIN_ESPECIALIDAD)
            return nombre, nombre, nombre
        if agrupar:
            clave, etiqueta = clave_de_periodo(fecha, agrupar)
            return clave, etiqueta, clave
        return SIN_AGRUPAR, "Total", ""

    def sumar(moneda, campo, monto, clave):
        setattr(totales[moneda], campo, getattr(totales[moneda], campo) + monto)
        destino = grupo(moneda, *clave) if agrupar else None
        if destino is not None:
            setattr(destino, campo, getattr(destino, campo) + monto)
        return destino

    base = (
        Payment.objects.filter(organization=organizacion)
        .select_related("appointment__branch", "appointment__practitioner")
    )
    if branch_id:
        base = base.filter(appointment__branch_id=branch_id)
    if practitioner_id:
        base = base.filter(appointment__practitioner_id=practitioner_id)

    # ---- Ingresos: lo cobrado en el rango, se haya devuelto después o no ----
    cobrados = base.filter(
        status__in=[Payment.Status.SUCCEEDED, Payment.Status.REFUNDED],
        paid_at__gte=inicio, paid_at__lt=fin,
    )
    for pago in cobrados:
        fecha = _fecha_local(pago.paid_at, tz)
        clave = clave_de_pago(pago, fecha)
        sumar(pago.currency, "ingresos", pago.amount, clave)
        totales[pago.currency].pagos += 1
        if agrupar:
            grupo(pago.currency, *clave).pagos += 1
        if pago.status != Payment.Status.SUCCEEDED:
            continue
        # Comisión y honorario solo de lo que quedó cobrado.
        if pago.provider != Payment.Provider.CASH and porcentaje_pasarela:
            sumar(pago.currency, "comision",
                  porcentaje_de(pago.amount, porcentaje_pasarela), clave)
        porcentaje_medico = Decimal(pago.appointment.practitioner.fee_percent)
        if porcentaje_medico:
            sumar(pago.currency, "honorarios",
                  porcentaje_de(pago.amount, porcentaje_medico), clave)

    # ---- Devoluciones: por la fecha en que se devolvieron ----------------------
    devueltos = base.filter(
        status=Payment.Status.REFUNDED,
        refunded_at__gte=inicio, refunded_at__lt=fin,
    )
    for pago in devueltos:
        fecha = _fecha_local(pago.refunded_at, tz)
        sumar(pago.currency, "devoluciones", pago.amount, clave_de_pago(pago, fecha))

    # ---- Gastos ----------------------------------------------------------------
    gastos = Expense.objects.filter(
        organization=organizacion, spent_on__gte=desde, spent_on__lte=hasta,
    ).select_related("branch")
    if branch_id:
        gastos = gastos.filter(branch_id=branch_id)
    # Un gasto no es de un médico: con ese filtro no entra a la cuenta.
    if practitioner_id:
        gastos = gastos.none()
    for gasto in gastos:
        if agrupar == "sede":
            clave = (
                (str(gasto.branch_id), gasto.branch.name, gasto.branch.name)
                if gasto.branch_id else ("general", GASTOS_GENERALES, "~")
            )
        elif agrupar in ("medico", "especialidad"):
            clave = ("general", GASTOS_GENERALES, "~")
        elif agrupar:
            clave_t, etiqueta = clave_de_periodo(gasto.spent_on, agrupar)
            clave = (clave_t, etiqueta, clave_t)
        else:
            clave = (SIN_AGRUPAR, "Total", "")
        sumar(gasto.currency, "gastos", gasto.amount, clave)

    monedas = []
    for moneda in sorted(totales):
        filas = sorted(
            grupos[moneda].items(), key=lambda par: (par[1].orden, par[0]),
        ) if agrupar else []
        monedas.append({
            "currency": moneda,
            "totals": totales[moneda].a_dict(),
            "groups": [
                {"key": clave, "label": acumulado.nombre, **acumulado.a_dict()}
                for clave, acumulado in filas
            ],
        })
    return {
        "range": {"from": desde.isoformat(), "to": hasta.isoformat(),
                  "timezone": organizacion.timezone or "America/La_Paz"},
        "branch": str(branch_id) if branch_id else None,
        "practitioner": str(practitioner_id) if practitioner_id else None,
        "group_by": agrupar,
        "commission_percent": str(redondear(porcentaje_pasarela)),
        "currencies": monedas,
    }


def periodo_anterior(desde: dt.date, hasta: dt.date):
    """El rango de la misma duración que termina justo antes de ``desde``."""
    dias = (hasta - desde).days + 1
    fin = desde - dt.timedelta(days=1)
    return fin - dt.timedelta(days=dias - 1), fin


def variacion(actual: str, anterior: str):
    """Variación porcentual, o ``None`` si no hay base (anterior en cero)."""
    previo = Decimal(anterior)
    if previo == 0:
        return None
    return str(redondear((Decimal(actual) - previo) / abs(previo) * 100))


def con_comparacion(organizacion, desde, hasta, **filtros) -> dict:
    """``calcular`` más ``compare``: cada tarjeta contra el período anterior."""
    actual = calcular(organizacion, desde, hasta, **filtros)
    antes_desde, antes_hasta = periodo_anterior(desde, hasta)
    anterior = calcular(organizacion, antes_desde, antes_hasta, **filtros)
    previas = {m["currency"]: m["totals"] for m in anterior["currencies"]}
    vacio = _Acumulador().a_dict()
    for moneda in actual["currencies"]:
        base = previas.get(moneda["currency"], vacio)
        moneda["compare"] = {
            "previous_totals": base,
            "change_percent": {
                campo: variacion(moneda["totals"][campo], base[campo])
                for campo in (*CAMPOS, "utilidad")
            },
        }
    actual["previous_range"] = anterior["range"]
    return actual


def serie_de_meses(organizacion, hoy: dt.date, *, branch_id=None,
                   practitioner_id=None) -> dict:
    """Los últimos 6 meses (el actual incluido), mes a mes, con ceros en los vacíos."""
    anio, mes = hoy.year, hoy.month - (MESES_DE_LA_SERIE - 1)
    while mes < 1:
        mes += 12
        anio -= 1
    desde = dt.date(anio, mes, 1)
    datos = calcular(organizacion, desde, hoy, branch_id=branch_id,
                     practitioner_id=practitioner_id, agrupar="mes")

    meses = []
    a, m = desde.year, desde.month
    for _ in range(MESES_DE_LA_SERIE):
        meses.append(f"{a}-{m:02d}")
        m += 1
        if m > 12:
            m, a = 1, a + 1

    por_moneda = []
    for moneda in datos["currencies"]:
        existentes = {g["key"]: g for g in moneda["groups"]}
        vacio = _Acumulador().a_dict()
        por_moneda.append({
            "currency": moneda["currency"],
            "months": [
                {"month": clave, **{k: v for k, v in
                                    (existentes.get(clave) or vacio).items()
                                    if k in ("ingresos", "devoluciones", "gastos",
                                             "utilidad")}}
                for clave in meses
            ],
        })
    return {"months": meses, "currencies": por_moneda}
