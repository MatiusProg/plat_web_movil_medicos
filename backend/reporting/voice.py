"""Característica general 5 — De una frase dictada a una definición de reporte.

El reconocimiento de voz ocurre **en el dispositivo** —la Web Speech API en el
navegador, el reconocedor de Android en el teléfono—, así que acá no llega
audio: llega el texto ya transcrito. Lo que hace este módulo es traducir ese
texto a la misma definición que arma el constructor a mano:

    "pacientes mujeres dadas de alta en septiembre, con nombre y teléfono"
        ↓
    {"dataset": "patients",
     "columns": ["first_name", "last_name", "phone"],
     "filters": [{"field": "sex", "operator": "eq", "value": "F"},
                 {"field": "created_at", "operator": "gte", "value": "2026-09-01"},
                 {"field": "created_at", "operator": "lte", "value": "2026-09-30"}],
     "order_by": []}

**Lo que se devuelve es una propuesta, no un reporte.** Quien dictó la ve en el
formulario y confirma; recién ahí se ejecuta por el endpoint de siempre. Esto
no es una cortesía de interfaz: la consigna de la materia pide una interfaz
previa para filtrar antes de generar, y una voz que ejecutara sola la haría
desaparecer.

Tres reglas, las mismas que sostienen al asistente de US-31:

1. **El modelo elige de una lista cerrada.** El prompt se arma con el catálogo
   de ``datasets.py`` **ya filtrado por los permisos de quien habla**, igual
   que el asistente sólo puede responder sobre los fragmentos recuperados. Lo
   que la persona no puede ver por pantalla no entra en el prompt, así que no
   puede salir en la propuesta.
2. **Lo que el modelo devuelve se valida contra el catálogo**, nunca se confía.
   Una columna inventada no se ignora en silencio —eso daría un reporte que
   parece correcto y no lo es—: se descarta y se nombra en ``unresolved`` para
   que la pantalla lo diga.
3. **Si el proveedor no está, se degrada y no se improvisa.** Sin clave, sin
   cuota o ante cualquier error se cae a ``_guess``, que adivina sólo el
   conjunto por palabras clave y deja las columnas por omisión. **Nunca inventa
   un criterio de selección**: un filtro inventado devuelve un subconjunto que
   nadie pidió y que se lee como si fuera el dato.
"""

from __future__ import annotations

import json
import unicodedata

from django.conf import settings
from django.utils import timezone

from . import datasets, exporters, query

# Formatos que se pueden pedir hablando. `json` es la vista previa en pantalla.
FORMATS = ("json", *exporters.FORMATS)

SYSTEM_PROMPT = """\
Traduces lo que una persona pide de viva voz a la definición de un reporte, en
JSON. Trabajás para un sistema de centros médicos y quien habla es personal del
centro: administración, recepción o dirección.

Respondés **sólo** con un objeto JSON de esta forma, sin texto alrededor:

{"dataset": "<código>",
 "columns": ["<código>", ...],
 "filters": [{"field": "<código>", "operator": "<op>", "value": <valor>}],
 "order_by": ["<código>", "-<código>"],
 "format": "json|csv|xlsx|html|pdf",
 "unresolved": ["<lo que se pidió y no existe en el catálogo>"]}

Reglas, sin excepción:
- Usás **únicamente** los códigos del catálogo que viene abajo. No inventás
  conjuntos, columnas, filtros ni operadores, aunque la persona los nombre.
- Lo que la persona pide y no existe en el catálogo va en `unresolved`, con sus
  palabras. No lo reemplaces por algo parecido.
- Si no estás seguro de a qué conjunto se refiere, devolvés `dataset` vacío.
- Las fechas van en formato AAAA-MM-DD, ya resueltas contra la fecha de hoy que
  se indica abajo. Un mes suelto ("septiembre") son dos filtros: desde el día
  primero y hasta el último día de ese mes.
- En los filtros de tipo `choice` usás el **valor** de la opción, no su
  etiqueta.
- Si la persona no pide columnas, dejás `columns` vacío: el sistema usa las
  predeterminadas.
- `format` sólo cuando lo pide ("en Excel", "en PDF"); si no, "json".
- No agregás filtros que la persona no pidió.
"""


def interpret(text: str, user, *, dataset_code: str = "") -> dict:
    """Traduce `text` a una definición de reporte para `user`.

    Devuelve siempre un diccionario con las mismas claves, aunque no haya
    entendido nada:

        understood      hay un conjunto y la definición pasó la validación
        definition      lista para mandar a `POST /api/reporting/run/`
        spoken_summary  la propuesta en palabras, para leerla o mostrarla
        unresolved      lo que se pidió y no se pudo resolver
        generated_by    "gemini" o "plantilla", como en el asistente

    No lanza: una falla del proveedor baja la calidad de la propuesta, no tumba
    el endpoint.
    """
    catalogo = datasets.available_for(user)
    texto = (text or "").strip()

    if not catalogo:
        return _nada(
            "No tenés permiso para consultar ningún conjunto de datos.",
            generated_by="plantilla",
        )
    if not texto:
        return _nada("No escuché nada.", generated_by="plantilla")

    crudo, generated_by = _propuesta_del_modelo(texto, catalogo, dataset_code)
    if crudo is None:
        crudo, generated_by = _guess(texto, catalogo, dataset_code), "plantilla"

    definicion, sin_resolver = _sanear(crudo, catalogo, dataset_code)

    if not definicion.get("dataset"):
        return _nada(
            "No reconocí sobre qué querés el reporte.",
            unresolved=sin_resolver,
            generated_by=generated_by,
        )

    # Se valida sin ejecutar: `build` arma el QuerySet pero no lo recorre, así
    # que cuesta lo mismo que revisar la definición a mano y además comprueba
    # el permiso del conjunto contra quien habla.
    try:
        query.build(definicion, user)
    except query.DefinitionError as error:
        sin_resolver.append(error.detail)
        return _nada(
            "Entendí el pedido, pero no pude armarlo.",
            unresolved=sin_resolver,
            generated_by=generated_by,
        )
    except PermissionError as error:
        return _nada(
            "No tenés permiso para consultar esos datos "
            f"(hace falta «{error.args[0]}»).",
            generated_by=generated_by,
        )

    return {
        "understood": True,
        "definition": definicion,
        "spoken_summary": _resumen(definicion, catalogo),
        "unresolved": sin_resolver,
        "generated_by": generated_by,
    }


# --------------------------------------------------------------------------
#  El proveedor
# --------------------------------------------------------------------------

def _propuesta_del_modelo(texto, catalogo, dataset_code) -> tuple[dict | None, str]:
    """Lo que devolvió Gemini, o `None` si no se pudo preguntar."""
    if settings.ASSISTANT_CHAT_PROVIDER != "gemini" or not settings.GEMINI_API_KEY:
        return None, "plantilla"
    try:
        crudo = _call_model(_pedido(texto, catalogo, dataset_code))
    except Exception:
        # Se traga igual que en `assistant/generation.py`: quien dicta un
        # reporte no tiene por qué leer un error de cuota. Queda el
        # `generated_by` para que se note desde afuera.
        return None, "plantilla"
    return (crudo, "gemini") if isinstance(crudo, dict) else (None, "plantilla")


def _call_model(prompt: str) -> dict | None:
    """La llamada al proveedor, sola, para que las pruebas la simulen."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.ASSISTANT_CHAT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            # Cero y no 0,2 como el asistente: acá no se redacta nada, se
            # traduce. La misma frase tiene que dar la misma definición.
            temperature=0,
            max_output_tokens=800,
            response_mime_type="application/json",
        ),
    )
    try:
        return json.loads((response.text or "").strip())
    except (json.JSONDecodeError, TypeError):
        return None


def _pedido(texto: str, catalogo, dataset_code: str) -> str:
    """El catálogo que puede ver quien habla, más su frase."""
    hoy = timezone.localdate()
    partes = [f"Fecha de hoy: {hoy.isoformat()} ({hoy:%d de %B de %Y}).", ""]

    if dataset_code:
        # La pantalla ya tenía un conjunto abierto: se lo decimos, pero no se
        # le impone, porque alguien puede dictar algo de otro conjunto.
        partes.append(f"La persona está mirando el conjunto «{dataset_code}».")
        partes.append("")

    partes.append("Catálogo disponible para esta persona:")
    for dataset in catalogo:
        partes.append("")
        partes.append(f"## {dataset.code} — {dataset.label}")
        partes.append(f"   {dataset.description}")
        partes.append("   Columnas:")
        for columna in dataset.columns:
            partes.append(f"   - {columna.code}: {columna.label}"
                          f" ({columna.kind}){_opciones(columna)}")
        partes.append("   Filtros:")
        for filtro in dataset.filters:
            operadores = ", ".join(sorted(datasets.OPERATORS[filtro.kind]))
            partes.append(f"   - {filtro.code}: {filtro.label}"
                          f" ({filtro.kind}; operadores: {operadores})"
                          f"{_opciones(filtro)}")

    partes += ["", f"Pedido de la persona: {texto}"]
    return "\n".join(partes)


def _opciones(campo) -> str:
    if not campo.choices:
        return ""
    pares = ", ".join(f"{valor}={etiqueta}"
                      for valor, etiqueta in campo.choices.items())
    return f" [{pares}]"


# --------------------------------------------------------------------------
#  Validación contra el catálogo
# --------------------------------------------------------------------------

def _sanear(crudo: dict, catalogo, dataset_code: str) -> tuple[dict, list[str]]:
    """Deja sólo lo que existe en el catálogo y nombra lo que descartó."""
    sin_resolver = [
        str(item)[:200] for item in (crudo.get("unresolved") or [])
        if str(item).strip()
    ]

    por_codigo = {dataset.code: dataset for dataset in catalogo}
    codigo = str(crudo.get("dataset") or "").strip()
    dataset = por_codigo.get(codigo) or por_codigo.get(dataset_code)
    if dataset is None:
        if codigo:
            sin_resolver.append(
                f"No existe —o no podés consultar— el conjunto «{codigo}»."
            )
        return {"dataset": "", "columns": [], "filters": [], "order_by": []}, sin_resolver

    columnas = []
    for codigo_columna in crudo.get("columns") or []:
        if dataset.column(str(codigo_columna).strip()):
            columnas.append(str(codigo_columna).strip())
        else:
            sin_resolver.append(
                f"No hay una columna «{codigo_columna}» en {dataset.label}."
            )

    filtros = []
    for filtro in crudo.get("filters") or []:
        if not isinstance(filtro, dict):
            continue
        campo = str(filtro.get("field") or "").strip()
        operador = str(filtro.get("operator") or "eq").strip()
        declarado = dataset.filter(campo)
        if declarado is None:
            sin_resolver.append(
                f"No se puede filtrar por «{campo}» en {dataset.label}."
            )
            continue
        if operador not in datasets.OPERATORS[declarado.kind]:
            sin_resolver.append(
                f"«{operador}» no es una comparación válida para "
                f"{declarado.label}."
            )
            continue
        if filtro.get("value") in (None, ""):
            sin_resolver.append(f"No entendí con qué comparar {declarado.label}.")
            continue
        filtros.append({"field": campo, "operator": operador,
                        "value": filtro["value"]})

    orden = []
    for criterio in crudo.get("order_by") or []:
        texto = str(criterio).strip()
        if dataset.column(texto.lstrip("-")):
            orden.append(texto)
        elif texto:
            sin_resolver.append(f"No se puede ordenar por «{texto}».")

    definicion = {
        "dataset": dataset.code,
        "columns": columnas,
        "filters": filtros,
        "order_by": orden or list(dataset.default_order),
    }
    formato = str(crudo.get("format") or "json").strip()
    definicion["format"] = formato if formato in FORMATS else "json"
    return definicion, sin_resolver


# --------------------------------------------------------------------------
#  Sin proveedor
# --------------------------------------------------------------------------

def _guess(texto: str, catalogo, dataset_code: str) -> dict:
    """Adivina **sólo el conjunto**, por el nombre que se haya dicho.

    Sin filtros a propósito: ver la regla 3 del encabezado. Lo que sale de acá
    es el conjunto con sus columnas por omisión, que es lo mismo que ver quien
    abre el constructor y elige un conjunto a mano.
    """
    normalizado = _sin_tildes(texto)
    for dataset in catalogo:
        etiqueta = _sin_tildes(dataset.label)
        # La etiqueta va en plural ("Pacientes") y se dicta en singular tan
        # seguido como en plural, así que se compara también sin la ese final.
        if etiqueta in normalizado or etiqueta.rstrip("s") in normalizado:
            return {"dataset": dataset.code}
    return {"dataset": dataset_code}


def _sin_tildes(texto: str) -> str:
    descompuesto = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


# --------------------------------------------------------------------------
#  La propuesta en palabras
# --------------------------------------------------------------------------

def _resumen(definicion: dict, catalogo) -> str:
    """Lo entendido, dicho en una frase. **La arma Python, no el modelo.**

    Que la escriba el modelo sería dejar que un resumen amable describa una
    definición que dice otra cosa. Acá se lee de la definición ya saneada, así
    que lo que se muestra es exactamente lo que se va a ejecutar.
    """
    dataset = next(
        (d for d in catalogo if d.code == definicion["dataset"]), None,
    )
    if dataset is None:
        return ""

    codigos = definicion.get("columns") or list(dataset.default_columns)
    columnas = [dataset.column(c).label for c in codigos if dataset.column(c)]
    partes = [f"{dataset.label}: {', '.join(columnas)}"]

    for filtro in definicion.get("filters") or []:
        declarado = dataset.filter(filtro["field"])
        if declarado is None:
            continue
        valor = filtro["value"]
        if declarado.choices:
            valor = declarado.choices.get(str(valor), valor)
        partes.append(f"{declarado.label} {_COMPARACIONES.get(filtro['operator'], filtro['operator'])} {valor}")

    formato = definicion.get("format", "json")
    if formato != "json":
        partes.append(f"en {formato.upper()}")
    return " · ".join(partes)


_COMPARACIONES = {
    "eq": "es", "contains": "contiene", "starts": "empieza con",
    "lt": "antes de", "lte": "hasta", "gt": "después de", "gte": "desde",
    "in": "entre",
}


def _nada(motivo: str, *, unresolved=None, generated_by="plantilla") -> dict:
    """La respuesta cuando no hay propuesta que ofrecer."""
    return {
        "understood": False,
        "definition": None,
        "spoken_summary": motivo,
        "unresolved": unresolved or [],
        "generated_by": generated_by,
    }
