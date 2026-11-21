"""US-50 — De la frase de quien administra a una consulta de contabilidad.

    "utilidad por sede del mes pasado"
        ↓
    {"metrica": "utilidad", "desde": "2026-10-01", "hasta": "2026-10-31",
     "agrupar": "sede", "sede": null, "profesional": null, "comparar": false}

Las reglas son las de la característica 5 (``reporting/voice.py``) y las de
US-46 (``payments/mine_voice.py``):

1. **Lista cerrada.** La métrica, la agrupación y el período salen de
   vocabulario fijo. El modelo, si responde, solo llena la métrica, el período
   y si compara.
2. **Nunca una cifra.** Ni el analizador ni el modelo calculan nada: ``interpretar``
   devuelve la consulta y ``finance.py`` la ejecuta. La frase de respuesta
   también la arma Python con lo que devolvió ``finance.py``.
3. **Sede, profesional y agrupación los decide Python**, antes de llegar al
   proveedor y con o sin él. El modelo recibe la frase sin esas partes: no puede
   inventar un filtro ni dejarlo sin efecto, y los nombres de los profesionales
   no salen del servidor.
4. **Sin proveedor se degrada, no se improvisa.** Lo que no se entiende se dice
   en ``unresolved`` y no se ejecuta nada.
5. **La frase no queda en la bitácora**: puede nombrar a un profesional.
"""

from __future__ import annotations

import datetime as dt
import re
from decimal import Decimal

from appointments import kpis
from payments.mine_voice import (
    NUM,
    _compactar,
    _fechas,
    _limpio,
    _numero,
    sin_profesional,
)

from . import finance, voice

METRICAS = (
    "utilidad", "ingresos", "devoluciones", "honorarios", "comision", "gastos",
    "ticket_promedio",
)
NOMBRE_DE_METRICA = {
    "utilidad": "La utilidad",
    "ingresos": "Los ingresos",
    "devoluciones": "Las devoluciones",
    "honorarios": "Los honorarios",
    "comision": "La comisión de la pasarela",
    "gastos": "Los gastos",
    "ticket_promedio": "El ticket promedio",
}
CAMPO_DE_METRICA = {"ticket_promedio": "ticket_promedio"}

_PALABRAS_DE_METRICA = (
    ("utilidad", r"utilidad(?:es)?|ganancias?|ganamos|ganado|beneficios?|margen"),
    ("ingresos", r"ingresos?|factur\w*|cobr\w*|vend\w*|recaud\w*|entradas?"),
    ("devoluciones", r"devoluci\w*|devolv\w*|reembols\w*"),
    ("honorarios", r"honorarios?"),
    ("comision", r"comision(?:es)?|stripe|pasarela"),
    ("gastos", r"gastos?|gastamos|egresos?|insumos?|alquiler|sueldos?|costos?"),
    ("ticket_promedio", r"ticket|promedio"),
)
_RESUMEN = r"\b(?:resumen|numeros|cuentas|como (?:nos fue|vamos|andamos))\b"

_AGRUPACIONES = (
    ("sede", r"(?:sucursal(?:es)?|sedes?)"),
    ("especialidad", r"especialidad(?:es)?"),
    ("dia", r"(?:dias?|diari[oa]s?)"),
    ("semana", r"(?:semanas?|semanal(?:es)?)"),
    ("trimestre", r"(?:trimestres?|3\s+meses|tres\s+meses)"),
    ("mes", r"(?:mes(?:es)?|mensual(?:es)?)"),
    ("medico", r"(?:doctor(?:a|es|as)?|profesional(?:es)?|medic[oa]s?)"),
)
_VERBO_DE_AGRUPAR = r"(?:agrup\w*|separ\w*|divid\w*|clasific\w*|desglos\w*)"
_COMPARAR = r"\b(?:compar\w+|versus|vs|contra\s+(?:el|la)\s+(?:periodo|mes|semana)\s+anterior)\b"

SYSTEM_PROMPT = """\
Eres un traductor de frases a una consulta de contabilidad. NO respondes
preguntas ni calculas cifras: solo devuelves un JSON con estas claves:

  "metrica": una de utilidad, ingresos, devoluciones, honorarios, comision,
             gastos, ticket_promedio, o null si no se puede saber
  "desde":   fecha AAAA-MM-DD o null
  "hasta":   fecha AAAA-MM-DD o null
  "comparar": true si pide compararlo con el período anterior, si no false

«Ganancias» y «cuánto ganamos» son utilidad. «Facturamos» y «cobramos» son
ingresos. Si la frase no dice período, usa null en desde y hasta. Nunca
inventes fechas que la frase no diga. Devuelve solo el JSON.
"""


# ==========================================================================
#  El analizador local
# ==========================================================================
def _sin_agrupacion(t: str, profesionales):
    """Saca de la frase cómo agrupar. Devuelve ``(agrupar, texto, bloqueos)``."""
    palabras = {p for _, nombre, apellido in profesionales
                for p in _limpio(f"{nombre} {apellido}").split() if len(p) >= 2}
    no_es_nombre = (
        rf"(?!\s+(?:{'|'.join(re.escape(p) for p in sorted(palabras))})\b)"
        if palabras else ""
    )
    encontradas: list[str] = []
    for nombre, patron in _AGRUPACIONES:
        cola = no_es_nombre if nombre == "medico" else ""
        patrones = (
            rf"\b{_VERBO_DE_AGRUPAR}\s+(?:por|segun|en|a)\s+(?:cada\s+)?{patron}\b{cola}",
            rf"\bpor\s+(?:cada\s+)?{patron}\b{cola}",
            rf"\bde\s+cada\s+{patron}\b{cola}",
            *((r"\bmes\s+a\s+mes\b",) if nombre == "mes" else ()),
            *((r"\bdia\s+a\s+dia\b",) if nombre == "dia" else ()),
        )
        for completo in patrones:
            if re.search(completo, t):
                t = _compactar(re.sub(completo, " ", t))
                if nombre not in encontradas:
                    encontradas.append(nombre)

    bloqueos: list[str] = []
    if len(encontradas) > 1:
        bloqueos.append(
            "Agrupa por una sola cosa a la vez: sede, médico, especialidad, "
            "día, semana, mes o trimestre."
        )
        return None, t, bloqueos
    if not encontradas and re.search(rf"\b{_VERBO_DE_AGRUPAR}\b", t):
        bloqueos.append(
            "No supe por qué agrupar. Puedes agrupar por sede, médico, "
            "especialidad, día, semana, mes o trimestre."
        )
        t = _compactar(re.sub(rf"\b{_VERBO_DE_AGRUPAR}\b", " ", t))
    return (encontradas[0] if encontradas else None), t, bloqueos


def _sin_sede(t: str, sedes):
    """La sede nombrada en la frase. ``(sede|None, texto, bloqueos)``.

    ``sedes`` son ``(id, nombre)`` del centro. Gana el nombre más largo: «Sede
    Norte Alta» antes que «Sede Norte».
    """
    candidatas = sorted(
        ((id_, nombre, _limpio(nombre)) for id_, nombre in sedes),
        key=lambda fila: -len(fila[2]),
    )
    for id_, nombre, limpio in candidatas:
        if not limpio:
            continue
        patron = rf"(?:\b(?:de|en|la|del|sede|sucursal)\s+)*\b{re.escape(limpio)}\b"
        if re.search(patron, t):
            return (id_, nombre), _compactar(re.sub(patron, " ", t, count=1)), []
    return None, t, []


def _periodo_corto(t: str, hoy: dt.date):
    """«hoy», «ayer», «esta semana», «últimos 15 días», «últimas 4 semanas»."""
    fijos = (
        (r"\bhoy\b", lambda: (hoy, hoy)),
        (r"\bayer\b", lambda: (hoy - dt.timedelta(days=1),) * 2),
        (r"\besta semana\b", lambda: (finance._inicio_de_semana(hoy), hoy)),
        (r"\bsemana (?:pasada|anterior)\b", lambda: (
            finance._inicio_de_semana(hoy) - dt.timedelta(days=7),
            finance._inicio_de_semana(hoy) - dt.timedelta(days=1),
        )),
    )
    for patron, rango in fijos:
        encontrado = re.search(patron, t)
        if encontrado:
            return rango(), _compactar(t[:encontrado.start()] + " " + t[encontrado.end():])
    corrido = re.search(
        rf"\b(?:en\s+)?(?:los\s+|las\s+)?ultim[oa]s\s+({NUM})\s+(dias?|semanas?)\b", t,
    )
    if corrido:
        cuantos = _numero(corrido.group(1))
        unidad = 7 if corrido.group(2).startswith("semana") else 1
        resto = _compactar(t[:corrido.start()] + " " + t[corrido.end():])
        return (hoy - dt.timedelta(days=cuantos * unidad - 1), hoy), resto
    return None, t


def _metrica(t: str, bloqueos, comparar=False):
    encontradas = [
        nombre for nombre, patron in _PALABRAS_DE_METRICA
        if re.search(rf"\b(?:{patron})\b", t)
    ]
    if len(encontradas) > 1:
        bloqueos.append("Pide una cifra por vez: ingresos, utilidad, gastos…")
        return None
    if encontradas:
        return encontradas[0]
    if comparar or re.search(_RESUMEN, t):
        return "utilidad"
    bloqueos.append(
        "No supe qué cifra quieres. Prueba con «cuánto ganamos este mes» o "
        "«gastos de la sede Central»."
    )
    return None


def analizar(texto: str, hoy: dt.date, sedes=(), profesionales=()):
    """Lee la frase por reglas fijas. Devuelve ``(consulta, unresolved)``.

    ``consulta`` es ``None`` si algo impide ejecutar; ``unresolved`` dice qué.
    """
    t = _limpio(texto)
    if not t:
        return None, ["No escuché nada."]

    agrupar, t, bloqueos = _sin_agrupacion(t, profesionales)
    comparar = bool(re.search(_COMPARAR, t))
    t = _compactar(re.sub(_COMPARAR, " ", t))
    profesional, t, de_profesional = sin_profesional(t, profesionales)
    sede, t, _ = _sin_sede(t, sedes)
    bloqueos = [*bloqueos, *de_profesional]

    metrica = _metrica(t, bloqueos, comparar)
    corto, t = _periodo_corto(t, hoy)
    if corto:
        desde, hasta = corto
    else:
        desde, hasta, t = _fechas(t, hoy, bloqueos)
    # «Compará este mes con el anterior»: el «anterior» sobra, no es otro período.
    if comparar:
        t = _compactar(re.sub(r"\b(?:con|el|la|mes|periodo|semana|anterior)\b", " ", t))
    if bloqueos:
        return None, bloqueos
    return _armar(metrica, desde, hasta, agrupar, sede, profesional, comparar, hoy), []


def _armar(metrica, desde, hasta, agrupar, sede, profesional, comparar, hoy):
    if desde is None or hasta is None:
        # Sin período, el mes en curso hasta hoy.
        desde, hasta = hoy.replace(day=1), hoy
    return {
        "metrica": metrica,
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "agrupar": agrupar,
        "sede": sede[0] if sede else None,
        "sede_nombre": sede[1] if sede else None,
        "profesional": profesional[0] if profesional else None,
        "profesional_nombre": profesional[1] if profesional else None,
        "comparar": bool(comparar),
    }


# ==========================================================================
#  Lo que devuelve el modelo
# ==========================================================================
def _fecha(valor):
    try:
        return dt.date.fromisoformat(str(valor))
    except (TypeError, ValueError):
        return None


def sanear(crudo, hoy, agrupar, sede, profesional, comparar_local):
    """El JSON del modelo, validado contra la lista cerrada. ``(consulta, unresolved)``."""
    if not isinstance(crudo, dict):
        return None, ["No pude interpretar la frase."]
    metrica = crudo.get("metrica")
    if metrica not in METRICAS:
        return None, [
            "No supe qué cifra quieres. Prueba con «cuánto ganamos este mes»."
        ]
    desde, hasta = _fecha(crudo.get("desde")), _fecha(crudo.get("hasta"))
    if (desde is None) != (hasta is None):
        return None, ["No entendí el período."]
    if desde and (desde > hasta or desde.year < 2000 or hasta.year > hoy.year + 1):
        return None, ["No entendí el período."]
    comparar = comparar_local or crudo.get("comparar") is True
    return _armar(metrica, desde, hasta, agrupar, sede, profesional, comparar, hoy), []


def _pedido(texto: str, hoy: dt.date) -> str:
    return f"Hoy es {hoy.isoformat()}.\nFrase: {texto}"


# ==========================================================================
#  El resumen en una frase y la ejecución
# ==========================================================================
def _plata(moneda: str, valor: str) -> str:
    entero, _, decimales = str(Decimal(valor)).partition(".")
    signo = "-" if entero.startswith("-") else ""
    entero = entero.lstrip("-")
    miles = f"{int(entero):,}".replace(",", ".")
    return f"{signo}{moneda} {miles},{(decimales or '00').ljust(2, '0')}"


def _fecha_corta(texto: str) -> str:
    return dt.date.fromisoformat(texto).strftime("%d/%m/%Y")


def frase_de_respuesta(consulta: dict, resultado: dict) -> str:
    """Una frase con lo que calculó ``finance.py``. Nunca cifras del modelo."""
    metrica = consulta["metrica"]
    rango = resultado["range"]
    periodo = (
        f"el {_fecha_corta(rango['from'])}" if rango["from"] == rango["to"]
        else f"del {_fecha_corta(rango['from'])} al {_fecha_corta(rango['to'])}"
    )
    monedas = resultado["currencies"]
    if not monedas:
        return f"No hay movimientos {periodo}."

    campo = CAMPO_DE_METRICA.get(metrica, metrica)
    partes = []
    for moneda in monedas:
        valor = moneda["totals"][campo]
        if valor is None:
            partes.append(f"{moneda['currency']}: sin pagos")
            continue
        texto = _plata(moneda["currency"], valor)
        if consulta["comparar"]:
            cambio = moneda["compare"]["change_percent"].get(campo)
            if cambio is None:
                texto += " (sin período anterior con qué comparar)"
            else:
                numero = Decimal(cambio)
                sentido = "más" if numero >= 0 else "menos"
                texto += f" ({str(abs(numero)).replace('.', ',')} % {sentido} que el período anterior)"
        partes.append(texto)
    frase = f"{NOMBRE_DE_METRICA[metrica]} {periodo}: {' y '.join(partes)}"
    if consulta.get("sede_nombre"):
        frase += f", en {consulta['sede_nombre']}"
    if consulta.get("profesional_nombre"):
        frase += f", de {consulta['profesional_nombre']}"
    frase += "."

    if consulta["agrupar"] and len(monedas) == 1:
        grupos = monedas[0]["groups"]
        if grupos:
            top = sorted(
                (g for g in grupos if g.get(campo) is not None),
                key=lambda g: Decimal(g[campo]), reverse=True,
            )[:3]
            detalle = ", ".join(
                f"{g['label']} {_plata(monedas[0]['currency'], g[campo])}" for g in top
            )
            frase += f" Por grupo: {detalle}."
    return frase


def _nada(motivos, generado_por="plantilla"):
    return {
        "understood": False,
        "query": None,
        "result": None,
        "spoken_summary": "",
        "unresolved": motivos,
        "generated_by": generado_por,
    }


def contexto_del_centro(organizacion):
    from catalog.models import Branch, Practitioner

    sedes = list(
        Branch.objects.filter(organization=organizacion, is_active=True)
        .values_list("id", "name")
    )
    profesionales = list(
        Practitioner.objects.filter(organization=organizacion, is_active=True)
        .values_list("id", "first_name", "last_name")
    )
    return sedes, profesionales


def ejecutar(organizacion, consulta: dict) -> dict:
    """La consulta ya validada, calculada por ``finance.py``."""
    desde = dt.date.fromisoformat(consulta["desde"])
    hasta = dt.date.fromisoformat(consulta["hasta"])
    filtros = {
        "branch_id": consulta.get("sede"),
        "practitioner_id": consulta.get("profesional"),
        "agrupar": consulta.get("agrupar"),
    }
    if consulta["comparar"]:
        return finance.con_comparacion(organizacion, desde, hasta, **filtros)
    return finance.calcular(organizacion, desde, hasta, **filtros)


def interpretar(texto: str, user, *, hoy: dt.date | None = None) -> dict:
    """La frase de ``user`` convertida en consulta, calculada y resumida.

    Devuelve siempre las mismas claves y no lanza.
    """
    from django.utils import timezone

    texto = (texto or "").strip()
    if not texto:
        return _nada(["No escuché nada."])
    organizacion = user.organization
    hoy = hoy or timezone.localdate()

    sedes, profesionales = contexto_del_centro(organizacion)
    t = _limpio(texto)
    agrupar, t, bloqueos = _sin_agrupacion(t, profesionales)
    comparar = bool(re.search(_COMPARAR, t))
    t = _compactar(re.sub(_COMPARAR, " ", t))
    profesional, t, de_profesional = sin_profesional(t, profesionales)
    sede, limpio, _ = _sin_sede(t, sedes)
    motivos = [*bloqueos, *de_profesional]
    if motivos:
        return _nada(motivos)

    # El proveedor recibe la frase sin sede, profesional ni agrupación.
    crudo, generado_por = voice.ask_model(SYSTEM_PROMPT, _pedido(limpio, hoy))
    if crudo is not None:
        consulta, unresolved = sanear(crudo, hoy, agrupar, sede, profesional, comparar)
    else:
        generado_por = "plantilla"
        consulta, unresolved = analizar(texto, hoy, sedes, profesionales)

    if consulta is None:
        return _nada(unresolved, generado_por)
    if (dt.date.fromisoformat(consulta["hasta"])
            - dt.date.fromisoformat(consulta["desde"])).days >= kpis.MAX_DIAS:
        return _nada([f"El período no puede superar {kpis.MAX_DIAS} días."], generado_por)

    resultado = ejecutar(organizacion, consulta)
    return {
        "understood": True,
        "query": consulta,
        "result": resultado,
        "spoken_summary": frase_de_respuesta(consulta, resultado),
        "unresolved": [],
        "generated_by": generado_por,
    }
