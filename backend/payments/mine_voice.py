"""US-46 — De la frase del paciente a una consulta de comprobantes.

El reconocimiento de voz ocurre **en el dispositivo**: acá llega texto, sea
dictado o escrito. Lo que hace este módulo es traducirlo a una consulta
cerrada:

    "mis últimas 2 facturas de cardiología en octubre"
        ↓
    {"tipo": "pagos", "cantidad": 2, "desde": "2026-10-01",
     "hasta": "2026-10-31", "especialidad": "<uuid>", "agrupar": null}

Y también «mis facturas de los últimos 3 meses agrupadas por sucursal»: un
período corrido (desde la misma fecha de hace 3 meses hasta hoy) y una
agrupación para mostrar la lista por `mes`, `sucursal` o `especialidad`.

Las tres reglas de la característica 5 (`reporting/voice.py`) valen igual:

1. **Lista cerrada.** El tipo es `pagos` o `fichas`; no hay una tercera cosa que
   pedir. El modelo, si responde, sólo puede llenar estas cinco claves.
2. **Todo se valida contra el catálogo.** La especialidad tiene que existir en
   el centro del paciente, las fechas tienen que ser fechas y la cantidad tiene
   tope. Lo que no pasa no se ignora en silencio —devolvería más de lo pedido—:
   se nombra en `unresolved` y no se ejecuta nada.
3. **Sin proveedor se degrada, no se improvisa.** El analizador local lee por
   reglas fijas lo que el paciente dijo explícitamente; lo que no puede leer
   va a `unresolved`. No adivina.

**Quién puede pedir qué no se decide acá.** La consulta no tiene paciente: el
alcance —el titular y sus dependientes— lo pone `payments/mine.py` desde la
sesión, así que una frase que nombre a otra persona no cambia de quién son los
datos. Pedirlo se avisa (`detectar_no_soportado`) para que no parezca que
funcionó.

**Agrupar no lo decide el modelo.** «Por mes», «por sucursal» y «por
especialidad» son vocabulario cerrado: lo detecta Python en la frase, igual
con o sin proveedor. Así un modelo no puede inventar una agrupación que nadie
pidió, ni dejar sin efecto una que sí.

**El modelo traduce, no responde.** No recibe datos de ningún paciente: sólo la
frase, la fecha de hoy y los nombres de las especialidades del centro. El
resumen para leer lo arma Python.
"""

from __future__ import annotations

import calendar
import datetime as dt
import re

from catalog.models import normalize_text

TIPOS = ("pagos", "fichas")
CANTIDAD_MAXIMA = 50

# Los nombres de las claves son los de la consigna de US-46; el sobre de la
# respuesta (`understood`, `unresolved`...) conserva los de la voz del personal.
CLAVES = ("tipo", "cantidad", "desde", "hasta", "especialidad", "agrupar")

# Cómo se puede mostrar la lista. Una a la vez.
AGRUPACIONES = ("mes", "sucursal", "especialidad")
# «Los últimos N meses»: más allá de tres años no es una consulta de comprobantes.
MESES_MAXIMOS = 36

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
    "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10,
    "noviembre": 11, "diciembre": 12,
}
NOMBRES_DE_MES = (
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)

_UNIDADES = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "dieciseis": 16,
    "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
    "veintiun": 21, "veintiuno": 21, "veintiuna": 21, "veintidos": 22,
    "veintitres": 23, "veinticuatro": 24, "veinticinco": 25, "veintiseis": 26,
    "veintisiete": 27, "veintiocho": 28, "veintinueve": 29, "treinta": 30,
    "cuarenta": 40, "cincuenta": 50, "cien": 100, "ciento": 100,
}
_PALABRAS_DE_NUMERO = dict(_UNIDADES)
for _decena, _valor in (("treinta", 30), ("cuarenta", 40)):
    for _unidad in ("un", "uno", "dos", "tres", "cuatro", "cinco", "seis",
                    "siete", "ocho", "nueve"):
        _PALABRAS_DE_NUMERO[f"{_decena} y {_unidad}"] = _valor + _UNIDADES[_unidad]

# Primero las más largas: «treinta y cinco» antes que «treinta».
_NUM = "|".join(
    re.escape(p) for p in sorted(_PALABRAS_DE_NUMERO, key=len, reverse=True)
)
NUM = rf"(?:\d{{1,3}}|{_NUM})"
TIPO_PAGOS = r"(?:pagos?|facturas?|cobros?)"
TIPO_FICHAS = r"(?:fichas?|citas?|turnos?)"
TIPO_CUALQUIERA = rf"(?:{TIPO_PAGOS}|{TIPO_FICHAS})"
TIPO_SINGULAR = r"(?:pago|factura|cobro|ficha|cita|turno)"
MES = "|".join(sorted(MESES, key=len, reverse=True))
ANIO = r"(?:19|20)\d{2}"

# Lo que hoy no se puede pedir, y por qué. Cada patrón es una frase que el
# paciente podría decir; el mensaje le explica qué sí se puede.
_NO_SOPORTADO = (
    (r"\b(?:hoy|ayer|anteayer|manana|semanas?|dias?|trimestres?|"
     r"semestres?|quincenas?)\b",
     "Por ahora se pide por mes o por año, no por días ni semanas."),
    (r"\b(?:devuelt[oa]s?|reembols\w*|pendientes?|fallid[oa]s?|cancelad[oa]s?|"
     r"vencid[oa]s?|impag\w*|deudas?|rechazad[oa]s?|anulad[oa]s?|"
     r"reprogramad[oa]s?|por pagar)\b",
     "Solo se muestran los pagos y las fichas que tienen comprobante."),
    (r"\b(?:doctor|doctora|dr|dra|medic[oa]s?|sucursal(?:es)?)\b",
     "Por ahora no se filtra por profesional ni por sucursal."),
    (r"\b(?:monto|montos|importe|importes|bs|bolivianos|dolares|"
     r"mayor(?:es)? a|menor(?:es)? a)\b",
     "Por ahora no se filtra por monto."),
    (r"\b(?:hij[oa]s?|espos[oa]s?|madre|padre|mama|papa|hermanos?|hermanas?|"
     r"abuel[oa]s?|nietos?|nietas?|dependientes?|familiares?|todos los "
     r"pacientes|toda la organizacion|otro paciente|otra persona)\b",
     "No se filtra por persona: se muestran los tuyos y los de tus "
     "dependientes."),
)

# Palabras de relleno que pueden seguir a «de», «en», «con»... sin ser una
# especialidad: no bloquean.
_RELLENO = frozenset({
    "favor", "favorcito", "gracias", "ahora", "mi", "mis", "tu", "tus", "la",
    "el", "los", "las", "un", "una", "unos", "unas", "ver", "mostrar", "dame",
    "muestrame", "quiero", "necesito", "tarde", "noche", "mes", "ano", "anos",
    "total", "todo", "todos", "todas", "lista", "listado", "comprobante",
    "comprobantes", "ultimo", "ultima", "ultimos", "ultimas", "que", "se",
    "pagaron", "pague", "pagado", "pagados", "pagadas", "he", "tengo", "hice",
    "atendi", "atendieron", "reserve", "reservadas", "confirmadas",
    "atendidas", "mias", "mios", "pasado", "pasada", "anterior", "este",
    "esta", "actual", "hace", "unos", "unas",
})


# ==========================================================================
#  Normalización
# ==========================================================================
def _limpio(texto: str) -> str:
    """Minúsculas, sin tildes ni puntuación, con un espacio entre palabras."""
    plano = re.sub(r"[^a-z0-9\s]", " ", normalize_text(texto))
    return re.sub(r"\s+", " ", plano).strip()


def _numero(token: str) -> int:
    return int(token) if token.isdigit() else _PALABRAS_DE_NUMERO[token]


# ==========================================================================
#  Lo que no se puede pedir
# ==========================================================================
def detectar_no_soportado(texto: str, nombres=()) -> list[str]:
    """Los motivos por los que la frase pide algo que hoy no existe.

    Se corre **antes** de ejecutar nada, y también sobre lo que diga el modelo:
    un modelo distraído no puede saltarse esta lista. `nombres` son los
    nombres de pila del titular y sus dependientes ya normalizados; nombrar a
    una persona de la familia no filtra por ella y hay que decirlo.
    """
    t = _limpio(texto)
    motivos: list[str] = []
    for patron, mensaje in _NO_SOPORTADO:
        if re.search(patron, t) and mensaje not in motivos:
            motivos.append(mensaje)
    familia = [n for n in nombres if n and re.search(rf"\b{re.escape(n)}\b", t)]
    persona = _NO_SOPORTADO[-1][1]
    if familia and persona not in motivos:
        motivos.append(persona)
    return motivos


# ==========================================================================
#  Cómo agrupar
# ==========================================================================
_CLAVES_DE_AGRUPACION = (
    ("mes", r"mes(?:es)?"),
    ("sucursal", r"(?:sucursal(?:es)?|sedes?)"),
    ("especialidad", r"especialidad(?:es)?"),
)
_VERBO_DE_AGRUPAR = r"(?:agrup\w*|separ\w*|divid\w*|clasific\w*|desglos\w*)"


def sin_agrupacion(texto: str):
    """Saca de la frase cómo agrupar. Devuelve `(agrupar, texto, bloqueos)`.

    «Agrupadas por sucursal», «por mes», «de cada especialidad», «mes a mes».
    Es lo primero que se corre sobre la frase, con o sin proveedor, y lo que
    devuelve es el texto **sin** esa parte: así «sucursal» no se toma por un
    filtro por sucursal, que sigue sin existir, ni «por especialidad» por una
    especialidad que no está en el catálogo.
    """
    t = _limpio(texto)
    encontradas: list[str] = []
    for nombre, patron in _CLAVES_DE_AGRUPACION:
        patrones = (
            rf"\b{_VERBO_DE_AGRUPAR}\s+(?:por|segun|en|a)\s+(?:cada\s+)?{patron}\b",
            rf"\bpor\s+(?:cada\s+)?{patron}\b",
            rf"\bde\s+cada\s+{patron}\b",
            *((r"\bmes\s+a\s+mes\b",) if nombre == "mes" else ()),
        )
        for patron_completo in patrones:
            if re.search(patron_completo, t):
                t = _compactar(re.sub(patron_completo, " ", t))
                if nombre not in encontradas:
                    encontradas.append(nombre)

    bloqueos: list[str] = []
    if len(encontradas) > 1:
        bloqueos.append(
            "Agrupa por una sola cosa a la vez: mes, sucursal o especialidad."
        )
        return None, t, bloqueos
    if not encontradas and re.search(rf"\b{_VERBO_DE_AGRUPAR}\b", t):
        bloqueos.append(
            "No supe por qué agrupar. Puedes agrupar por mes, sucursal o "
            "especialidad."
        )
        t = _compactar(re.sub(rf"\b{_VERBO_DE_AGRUPAR}\b", " ", t))
    return (encontradas[0] if encontradas else None), t, bloqueos


# ==========================================================================
#  El analizador local
# ==========================================================================
def analizar(texto, especialidades, hoy, nombres=()):
    """Lee la frase por reglas fijas. Devuelve `(consulta, unresolved, avisos)`.

    `consulta` es `None` si algo impide ejecutar —tipo ausente, un criterio que
    no existe—; `unresolved` dice qué. `avisos` son notas que no impiden nada
    (por ejemplo, que se recortó la cantidad). `especialidades` es una lista de
    `(id, nombre)` del centro del paciente y `hoy` una fecha.
    """
    t = _limpio(texto)
    if not t:
        return None, ["No escuché nada."], []

    agrupar, t, bloqueos = sin_agrupacion(t)
    bloqueos = [*bloqueos, *detectar_no_soportado(t, nombres)]
    avisos: list[str] = []

    tipo = _tipo(t, bloqueos)
    cantidad, t = _cantidad(t, bloqueos, avisos)
    desde, hasta, t = _fechas(t, hoy, bloqueos)
    # «No encontré la especialidad X» solo si no hay otro motivo antes: «de
    # hace 3 meses» ya se explicó, y «hace» no es una especialidad.
    de_especialidad: list[str] = []
    especialidad, t = _especialidad(t, especialidades, de_especialidad)
    if not bloqueos:
        bloqueos.extend(de_especialidad)

    if bloqueos:
        return None, bloqueos, avisos
    return _armar(tipo, cantidad, desde, hasta, especialidad, agrupar), [], avisos


def _tipo(t, bloqueos):
    pagos = re.search(rf"\b{TIPO_PAGOS}\b", t) is not None
    fichas = re.search(rf"\b{TIPO_FICHAS}\b", t) is not None
    if pagos and fichas:
        bloqueos.append("Pide una cosa por vez: pagos o fichas.")
    elif not pagos and not fichas:
        bloqueos.append(
            "No supe si quieres tus pagos o tus fichas. Prueba con «mis "
            "últimas 2 facturas» o «mis fichas de cardiología»."
        )
    return "pagos" if pagos else "fichas" if fichas else None


def _cantidad(t, bloqueos, avisos):
    """«últimas 2», «las 3 últimas», «2 facturas», «última ficha»."""
    candidatos = (
        (rf"\bultim[oa]s?\s+({NUM})\s+{TIPO_CUALQUIERA}\b", 1),
        (rf"\b({NUM})\s+ultim[oa]s\s+{TIPO_CUALQUIERA}\b", 1),
        (rf"\b({NUM})\s+{TIPO_CUALQUIERA}\b", 1),
    )
    for patron, grupo in candidatos:
        encontrado = re.search(patron, t)
        if encontrado:
            valor = _numero(encontrado.group(grupo))
            sobrante = t[:encontrado.start(grupo)] + " " + t[encontrado.end(grupo):]
            return _validar_cantidad(valor, bloqueos, avisos), _compactar(sobrante)

    # «última ficha», «último pago»: en singular, una.
    if re.search(rf"\bultim[oa]\s+{TIPO_SINGULAR}\b", t):
        return 1, t
    return None, t


def _validar_cantidad(valor, bloqueos, avisos):
    if valor <= 0:
        bloqueos.append("La cantidad tiene que ser al menos 1.")
        return None
    if valor > CANTIDAD_MAXIMA:
        avisos.append(f"Se muestran como máximo {CANTIDAD_MAXIMA}.")
        return CANTIDAD_MAXIMA
    return valor


def _fechas(t, hoy, bloqueos):
    """El mes, el año o un rango. Devuelve `(desde, hasta, texto_restante)`."""
    relativas = []

    # «Los últimos 3 meses», «el último mes»: corrido, desde la misma fecha de
    # hace N meses hasta hoy. No son meses calendario completos: el 16/11,
    # «los últimos 3 meses» empiezan el 16/08.
    corrido = re.search(
        rf"\b(?:en\s+)?(?:los\s+)?ultim[oa]s\s+({NUM})\s+mes(?:es)?\b", t,
    ) or re.search(r"\b(?:en\s+)?(?:el\s+)?ultimo\s+mes\b", t)
    if corrido:
        cuantos = _numero(corrido.group(1)) if corrido.groups() else 1
        t = _compactar(t[:corrido.start()] + " " + t[corrido.end():])
        if not 1 <= cuantos <= MESES_MAXIMOS:
            bloqueos.append(
                f"Pide entre 1 y {MESES_MAXIMOS} meses, por ejemplo «los "
                "últimos 3 meses»."
            )
        else:
            relativas.append((_restar_meses(hoy, cuantos), hoy))

    for patron, rango in (
        (r"\beste mes\b", lambda: _mes(hoy.year, hoy.month)),
        (r"\bmes (?:pasado|anterior)\b", lambda: _mes_anterior(hoy)),
        (r"\beste ano\b", lambda: _anio(hoy.year)),
        (r"\bano (?:pasado|anterior)\b", lambda: _anio(hoy.year - 1)),
    ):
        encontrado = re.search(patron, t)
        if encontrado:
            relativas.append(rango())
            t = _compactar(t[:encontrado.start()] + " " + t[encontrado.end():])

    meses = list(re.finditer(
        rf"\b({MES})(?:\s+(?:de|del))?(?:\s+({ANIO}))?\b", t,
    ))
    if meses:
        rango = _rango_de_meses(t, meses, hoy, bloqueos)
        t = _compactar(re.sub(
            rf"\b(?:de|del|en|desde|hasta|entre|a|y)?\s*\b({MES})"
            rf"(?:\s+(?:de|del))?(?:\s+{ANIO})?\b", " ", t,
        ))
        t = _compactar(re.sub(r"\b(?:desde|hasta|entre)\b", " ", t))
        if rango:
            relativas.append(rango)
    else:
        solo_anio = re.search(rf"\b({ANIO})\b", t)
        if solo_anio:
            anio = int(solo_anio.group(1))
            if not 2000 <= anio <= hoy.year + 1:
                bloqueos.append(f"No tengo comprobantes del año {anio}.")
            else:
                relativas.append(_anio(anio))
            t = _compactar(t[:solo_anio.start()] + " " + t[solo_anio.end():])

    # Un «mes» que sobró no se entendió («hace 3 meses», «3 meses atrás»): se
    # dice en vez de devolver todo como si no hubiera dicho nada.
    if re.search(r"\bmes(?:es)?\b", t):
        bloqueos.append(
            "No entendí el período. Prueba con «los últimos 3 meses» o un mes "
            "como «octubre»."
        )
    if len(relativas) > 1:
        bloqueos.append("Pediste dos fechas distintas. Dime solo un mes o un año.")
        return None, None, t
    if not relativas:
        return None, None, t
    desde, hasta = relativas[0]
    if desde > hasta:
        bloqueos.append("La fecha de inicio es posterior a la de fin.")
        return None, None, t
    return desde, hasta, t


def _rango_de_meses(t, meses, hoy, bloqueos):
    """Un mes, o «de X a Y». Dos meses sueltos son ambiguos y se avisan."""
    def resolver(coincidencia):
        mes = MESES[coincidencia.group(1)]
        if coincidencia.group(2):
            anio = int(coincidencia.group(2))
            if not 2000 <= anio <= hoy.year + 1:
                bloqueos.append(f"No tengo comprobantes del año {anio}.")
                return None
            return anio, mes
        # Sin año: el actual, o el anterior si ese mes todavía no llegó.
        return (hoy.year if mes <= hoy.month else hoy.year - 1), mes

    if len(meses) == 1:
        resuelto = resolver(meses[0])
        return _mes(*resuelto) if resuelto else None

    if len(meses) == 2:
        conector = t[meses[0].end():meses[1].start()].strip()
        antes = (t[:meses[0].start()].strip().split() or [""])[-1]
        # «de enero a marzo», «desde enero hasta marzo», «entre enero y
        # marzo». «De enero y marzo» son dos meses sueltos, no un rango.
        if (antes, conector) in (
            ("de", "a"), ("de", "hasta"), ("desde", "a"), ("desde", "hasta"),
            ("entre", "y"),
        ):
            primero, segundo = resolver(meses[0]), resolver(meses[1])
            if primero and segundo:
                return _mes(*primero)[0], _mes(*segundo)[1]
            return None
    bloqueos.append(
        "Pediste más de un mes. Dime uno solo, o un rango como «de enero a "
        "marzo»."
    )
    return None


def _mes(anio, mes):
    return (dt.date(anio, mes, 1),
            dt.date(anio, mes, calendar.monthrange(anio, mes)[1]))


def _restar_meses(fecha, meses):
    """`fecha` menos `meses` meses, sin pasarse del fin del mes (31/05 → 28/02)."""
    total = fecha.year * 12 + (fecha.month - 1) - meses
    anio, mes0 = divmod(total, 12)
    mes = mes0 + 1
    return dt.date(anio, mes, min(fecha.day, calendar.monthrange(anio, mes)[1]))


def _mes_anterior(hoy):
    anio, mes = (hoy.year, hoy.month - 1) if hoy.month > 1 else (hoy.year - 1, 12)
    return _mes(anio, mes)


def _anio(anio):
    return dt.date(anio, 1, 1), dt.date(anio, 12, 31)


def _especialidad(t, especialidades, bloqueos):
    """La especialidad del catálogo que nombra la frase, o un bloqueo."""
    mejor = None
    for id_, nombre in especialidades:
        normalizado = _limpio(nombre)
        if normalizado and re.search(rf"\b{re.escape(normalizado)}\b", t):
            if mejor is None or len(normalizado) > len(mejor[2]):
                mejor = (id_, nombre, normalizado)
    if mejor:
        id_, nombre, normalizado = mejor
        t = _compactar(re.sub(rf"\b{re.escape(normalizado)}\b", " ", t, count=1))
        return (str(id_), nombre), t

    # Nada coincide, pero la frase pide «de algo»: se avisa, no se ignora.
    sobrante = re.search(
        r"\b(?:de|del|en|con|para|sobre|por)\s+(?:(?:el|la|los|las|mi|mis|un|"
        r"una)\s+)*([a-z]{4,}(?:\s+[a-z]{3,}){0,2})", _sin_tipos(t),
    )
    if sobrante:
        palabras = sobrante.group(1).split()
        if palabras[0] not in _RELLENO and not (set(palabras) <= _RELLENO):
            bloqueos.append(
                f"No encontré «{sobrante.group(1)}» entre las especialidades de "
                "este centro."
            )
    return None, t


def _sin_tipos(t):
    return re.sub(rf"\b{TIPO_CUALQUIERA}\b", " ", t)


def _compactar(t):
    return re.sub(r"\s+", " ", t).strip()


def _armar(tipo, cantidad, desde, hasta, especialidad, agrupar=None):
    return {
        "tipo": tipo,
        "cantidad": cantidad,
        "desde": desde.isoformat() if desde else None,
        "hasta": hasta.isoformat() if hasta else None,
        "especialidad": especialidad[0] if especialidad else None,
        "especialidad_nombre": especialidad[1] if especialidad else None,
        "agrupar": agrupar,
    }


# ==========================================================================
#  Lo que devuelve el modelo
# ==========================================================================
SYSTEM_PROMPT_PACIENTE = """\
Traduces lo que un paciente pide de viva voz a una consulta de sus comprobantes,
en JSON. No respondes preguntas ni calculas nada: solo traduces.

Devuelves exactamente estas claves y ninguna otra:

{"tipo": "pagos" | "fichas" | null,
 "cantidad": entero | null,
 "desde": "AAAA-MM-DD" | null,
 "hasta": "AAAA-MM-DD" | null,
 "especialidad": "<nombre exacto de la lista>" | null,
 "no_entendido": ["lo que pidió y no puedes expresar con estas claves"]}

Reglas:
- «facturas», «pagos» y «cobros» son "pagos". «Fichas», «citas» y «turnos» son
  "fichas". Si pide las dos cosas o ninguna, "tipo" es null.
- "cantidad" solo si pidió un número de resultados («mis últimas 2 facturas»).
- Un mes suelto («octubre») son dos fechas: el primer y el último día de ese
  mes. Sin año, usa el año de la fecha de hoy, o el anterior si ese mes todavía
  no llegó. Un año suelto es del 1 de enero al 31 de diciembre.
- «Los últimos N meses» son corridos: "desde" es la fecha de hoy menos N meses
  y "hasta" es la fecha de hoy. «El último mes» es N = 1.
- El texto llega en minúsculas y sin tildes, y sin la parte que pide agrupar
  (eso no lo decides tú).
- "especialidad" es uno de los nombres de la lista, copiado igual. Si pide una
  que no está en la lista, déjala en null y anótala en "no_entendido".
- No hay forma de pedir por persona, profesional, sucursal, monto, estado,
  días ni semanas: anótalo en "no_entendido".
- Nunca inventes datos. Lo dudoso va en "no_entendido".
"""


def pedido_al_modelo(texto, especialidades, hoy) -> str:
    """La frase, la fecha de hoy y los nombres de las especialidades del centro.

    Nada más: ningún dato de pacientes, de pagos ni de fichas sale hacia el
    proveedor.
    """
    nombres = "\n".join(f"- {nombre}" for _, nombre in especialidades) or "(ninguna)"
    return (
        f"Fecha de hoy: {hoy.isoformat()}\n\n"
        f"Especialidades del centro:\n{nombres}\n\n"
        f"Pedido de la persona: {texto.strip()}"
    )


def sanear_consulta(crudo, especialidades, hoy, nombres=(), agrupar=None):
    """Valida lo que devolvió el modelo. `(consulta, unresolved, avisos)`.

    Solo se leen las cinco claves que el modelo llena; cualquier otra —un
    `paciente`, un `organization`, un `agrupar`— se descarta sin mirarla. Cómo
    agrupar lo trae `agrupar`, que sacó Python de la frase (`sin_agrupacion`).
    Lo que el modelo anotó en `no_entendido` y todo lo que no pase la
    validación bloquea.
    """
    bloqueos = [
        str(item).strip()[:200]
        for item in (crudo.get("no_entendido") or [])
        if isinstance(item, str) and item.strip()
    ] if isinstance(crudo, dict) else ["No pude leer la respuesta."]
    avisos: list[str] = []
    if not isinstance(crudo, dict):
        return None, bloqueos, avisos

    tipo = crudo.get("tipo")
    if tipo not in TIPOS:
        bloqueos.append("No supe si quieres tus pagos o tus fichas.")
        tipo = None

    cantidad = crudo.get("cantidad")
    if cantidad is not None:
        if isinstance(cantidad, bool) or not (
            isinstance(cantidad, int) or (isinstance(cantidad, str) and cantidad.isdigit())
        ):
            bloqueos.append("No entendí la cantidad.")
            cantidad = None
        else:
            cantidad = _validar_cantidad(int(cantidad), bloqueos, avisos)

    desde = _fecha(crudo.get("desde"), hoy, bloqueos)
    hasta = _fecha(crudo.get("hasta"), hoy, bloqueos)
    if desde and hasta and desde > hasta:
        bloqueos.append("La fecha de inicio es posterior a la de fin.")

    especialidad = None
    pedida = crudo.get("especialidad")
    if pedida:
        pedida = normalize_text(str(pedida))
        for id_, nombre in especialidades:
            if normalize_text(nombre) == pedida:
                especialidad = (str(id_), nombre)
                break
        else:
            bloqueos.append(
                f"No encontré «{str(crudo['especialidad'])[:60]}» entre las "
                "especialidades de este centro."
            )

    if bloqueos:
        return None, bloqueos, avisos
    return _armar(tipo, cantidad, desde, hasta, especialidad, agrupar), [], avisos


def _fecha(valor, hoy, bloqueos):
    if valor in (None, ""):
        return None
    try:
        fecha = dt.date.fromisoformat(str(valor))
    except ValueError:
        bloqueos.append(f"No entendí la fecha «{str(valor)[:20]}».")
        return None
    if not 2000 <= fecha.year <= hoy.year + 1:
        bloqueos.append(f"No tengo comprobantes del año {fecha.year}.")
        return None
    return fecha


# ==========================================================================
#  El resumen para leer
# ==========================================================================
def resumen(consulta) -> str:
    """La consulta en palabras. La arma Python, nunca el modelo."""
    partes = ["Pagos con comprobante" if consulta["tipo"] == "pagos"
              else "Fichas con comprobante"]
    if consulta["cantidad"]:
        partes.append(f"últimos {consulta['cantidad']}"
                      if consulta["cantidad"] > 1 else "el último")
    if consulta["especialidad_nombre"]:
        partes.append(consulta["especialidad_nombre"])
    periodo = _periodo(consulta["desde"], consulta["hasta"])
    if periodo:
        partes.append(periodo)
    if consulta.get("agrupar"):
        partes.append(f"agrupados por {consulta['agrupar']}")
    return " · ".join(partes)


def _periodo(desde, hasta):
    if not desde and not hasta:
        return ""
    d = dt.date.fromisoformat(desde) if desde else None
    h = dt.date.fromisoformat(hasta) if hasta else None
    if d and h:
        if d == dt.date(d.year, 1, 1) and h == dt.date(d.year, 12, 31):
            return f"año {d.year}"
        if d.day == 1 and h == _mes(h.year, h.month)[1]:
            if (d.year, d.month) == (h.year, h.month):
                return f"{NOMBRES_DE_MES[d.month]} de {d.year}"
            return (f"de {NOMBRES_DE_MES[d.month]} de {d.year} a "
                    f"{NOMBRES_DE_MES[h.month]} de {h.year}")
    desde_texto = f"desde el {d:%d/%m/%Y}" if d else ""
    hasta_texto = f"hasta el {h:%d/%m/%Y}" if h else ""
    return " ".join(p for p in (desde_texto, hasta_texto) if p)


# ==========================================================================
#  Todo junto
# ==========================================================================
def _nada(motivos, generated_by="plantilla"):
    return {
        "understood": False, "consulta": None, "spoken_summary": "",
        "unresolved": list(motivos), "generated_by": generated_by,
    }


def interpretar_consulta(texto, user, *, hoy=None) -> dict:
    """La frase del paciente `user` convertida en una consulta, o por qué no.

    Devuelve siempre las mismas claves, aunque no haya entendido nada, y no
    lanza. `consulta` se manda tal cual como parámetros del
    `GET /api/payments/mine/receipts/`, que vuelve a validar todo.
    """
    from django.utils import timezone

    from reporting import voice

    texto = (texto or "").strip()
    if not texto:
        return _nada(["No escuché nada."])

    hoy = hoy or timezone.localdate()
    especialidades, nombres = _contexto_del_centro(user)

    # Cómo agrupar lo decide Python, con o sin proveedor, y el modelo recibe
    # la frase sin esa parte: no puede inventar una agrupación ni dejarla sin
    # efecto.
    agrupar, sin_agrupar, bloqueos = sin_agrupacion(texto)
    motivos = [*bloqueos, *detectar_no_soportado(sin_agrupar, nombres)]
    if motivos:
        return _nada(motivos)

    crudo, generado_por = voice.ask_model(
        SYSTEM_PROMPT_PACIENTE,
        pedido_al_modelo(sin_agrupar, especialidades, hoy),
    )
    if crudo is not None:
        consulta, unresolved, avisos = sanear_consulta(
            crudo, especialidades, hoy, nombres, agrupar,
        )
    else:
        generado_por = "plantilla"
        consulta, unresolved, avisos = analizar(
            texto, especialidades, hoy, nombres,
        )

    if consulta is None:
        return _nada(unresolved, generado_por)
    return {
        "understood": True,
        "consulta": consulta,
        "spoken_summary": resumen(consulta),
        "unresolved": avisos,
        "generated_by": generado_por,
    }


def _contexto_del_centro(user):
    """Las especialidades del centro y los nombres de pila de la familia."""
    from catalog.models import Specialty
    from patients.models import Patient

    especialidades = list(
        Specialty.objects
        .filter(organization_id=user.organization_id, is_active=True)
        .values_list("id", "name")
    )
    titular = getattr(user, "patient_profile", None)
    nombres: set[str] = set()
    if titular is not None:
        familia = Patient.objects.filter(
            organization_id=user.organization_id,
        ).filter(guardian_id=titular.id)
        for paciente in [titular, *familia]:
            for parte in (paciente.first_name or "").split():
                limpio = _limpio(parte)
                if len(limpio) >= 3:
                    nombres.add(limpio)
    return especialidades, sorted(nombres)
