"""US-41 — Resumen sintético del historial antes de una nueva consulta.

El médico abre la atención y, antes de escribir, lee en cinco renglones lo que
el paciente trae: qué se le diagnosticó, qué toma, qué estudios tiene
pedidos. Es el historial de US-25 resumido, **no un texto nuevo**: no agrega
nada que no esté en las atenciones firmadas.

Tres decisiones, las mismas que sostienen al asistente (US-31):

1. **Cada afirmación cita la atención de la que sale.** Las atenciones van al
   modelo numeradas —``[A1]``, ``[A2]``…— y el modelo tiene que terminar cada
   oración con su cita. Al volver, **la oración sin cita, o con una cita que
   no existe, se descarta**. No se le cree al modelo: se lo verifica. Un
   resumen clínico que no se puede rastrear hasta la atención que lo dice es
   peor que no tener resumen.
2. **Lo que no se puede omitir no se le deja al modelo.** Las alergias, las
   condiciones y la medicación declaradas (US-08) se devuelven siempre,
   leídas de la base, en ``alerts``. Si el modelo no menciona la alergia a la
   penicilina, la pantalla la muestra igual.
3. **Sin proveedor se degrada, no se improvisa.** Sin clave, sin cuota o ante
   un error, el resumen se arma con los diagnósticos **copiados tal cual** de
   cada atención, con su cita, y se rotula ``generated_by: "plantilla"``. Es
   menos legible, pero cada palabra la escribió un médico.

**Para quién es.** Sólo para el médico con vínculo de atención
(``history_scope`` = ``professional``). El paciente **no** lo recibe: un
texto generado no le llega sin que un médico lo apruebe (regla 14 del
Sprint 4), y este no pasa por esa aprobación porque su lector es el propio
médico, que tiene las atenciones originales a un clic.

**Qué sale hacia el proveedor.** Sólo las secciones clínicas, sin el nombre
ni el documento del paciente: el modelo no necesita saber quién es para
resumir lo que tiene. Aun así son datos de salud y el nivel gratuito de Gemini
puede usarlos para entrenar; con los datos de demostración no hay problema,
con pacientes reales habría que pasar a un plan que no lo haga.
"""

from __future__ import annotations

import re

from django.conf import settings

from patients.models import PatientHistoryEntry

from .models import Encounter

# Cuántas atenciones entran al resumen. Las más recientes: lo que el médico
# necesita antes de una consulta es lo último, y diez atenciones ya son más
# historia de la que se lee en un minuto.
MAX_ENCOUNTERS = 10
# Tope por sección, para que una evolución de tres páginas no se coma el
# prompt entero ni la cuota.
MAX_FIELD_CHARS = 600

SYSTEM_PROMPT = """\
Eres un asistente para médicos. Recibes las atenciones firmadas de un paciente,
numeradas [A1], [A2]…, de la más reciente a la más antigua. Escribes un resumen
del historial para el médico que lo va a atender ahora.

Reglas, sin excepción:
- Usa SÓLO lo que está en las atenciones. No agregues diagnósticos,
  interpretaciones, recomendaciones ni conocimiento propio.
- Cada oración termina con la cita de la atención de la que sale, entre
  corchetes: [A1], o [A1][A3] si sale de varias. Una oración sin cita no se
  mostrará.
- Entre 3 y 6 oraciones. Primero los diagnósticos y problemas que se repiten,
  después la medicación indicada y los estudios pedidos, al final lo último
  que se hizo.
- Lenguaje médico, conciso, en español. Sin saludos ni cierre.
"""

_CITA = re.compile(r"\[A(\d+)\]")
# Una cita escrita después del punto ("…arterial. [A1]") se pasa adelante del
# punto, así el corte de oraciones la deja con la oración que cita.
_CITA_TRAS_PUNTO = re.compile(r"([.!?])((?:\s*\[A\d+\])+)")
# Una oración termina en punto o signo seguido de espacio, o en un salto de
# línea. El espacio importa: "2.5 mg" no corta.
_CORTE = re.compile(r"(?<=[.!?])\s+|\n+")


def _recortar(texto: str) -> str:
    texto = " ".join((texto or "").split())
    if len(texto) <= MAX_FIELD_CHARS:
        return texto
    return texto[: MAX_FIELD_CHARS - 1].rstrip() + "…"


def _texto_de(encuentro, seccion: str) -> str:
    """La sección como quedó, con sus enmiendas a continuación."""
    partes = [getattr(encuentro, seccion)]
    partes += [f"(enmienda: {a.text})" for a in encuentro.amendments.all()
               if a.section == seccion]
    return _recortar(" ".join(p for p in partes if p))


def _fuentes(encuentros) -> list[dict]:
    """Las atenciones numeradas, como las ve el modelo y como las cita la pantalla."""
    fuentes = []
    for n, e in enumerate(encuentros, start=1):
        fuentes.append({
            "ref": f"A{n}",
            "encounter_id": str(e.id),
            "date": e.appointment.starts_at.date().isoformat(),
            "branch": e.branch.name,
            "practitioner": e.practitioner.full_name,
            "diagnosis": _texto_de(e, "diagnosis"),
        })
    return fuentes


def _contexto(encuentros) -> str:
    bloques = []
    for n, e in enumerate(encuentros, start=1):
        renglones = [f"[A{n}] {e.appointment.starts_at.date().isoformat()}"]
        for seccion, etiqueta in Encounter.SECTIONS.items():
            texto = _texto_de(e, seccion)
            if texto:
                renglones.append(f"  {etiqueta}: {texto}")
        receta = [
            f"{i.medication} {i.dose}, {i.frequency}, {i.duration}"
            for i in e.prescription_items.all()
        ]
        if receta:
            renglones.append("  Receta: " + "; ".join(receta))
        ordenes = [f"{o.get_kind_display()}: {o.description}" for o in e.orders.all()]
        if ordenes:
            renglones.append("  Órdenes: " + "; ".join(ordenes))
        bloques.append("\n".join(renglones))
    return "\n\n".join(bloques)


def _alertas(paciente) -> dict:
    vigentes = list(
        PatientHistoryEntry.objects
        .filter(organization=paciente.organization, patient=paciente, is_active=True)
        .order_by("kind", "-recorded_at")
    )
    # Las graves primero: es lo que no puede quedar abajo de la pantalla.
    peso = {"anaphylactic": 0, "severe": 1, "moderate": 2, "mild": 3, "": 4}

    def item(a):
        return {"description": a.description, "severity": a.severity or None,
                "severity_label": a.get_severity_display() if a.severity else None}

    alergias = sorted((a for a in vigentes if a.kind == "allergy"),
                      key=lambda a: peso.get(a.severity, 4))
    return {
        "allergies": [item(a) for a in alergias],
        "conditions": [item(a) for a in vigentes if a.kind == "condition"],
        "medications": [item(a) for a in vigentes if a.kind == "medication"],
    }


def _mover_citas(texto: str) -> str:
    """"…arterial. [A1] Toma…" → "…arterial [A1]. Toma…"."""
    return _CITA_TRAS_PUNTO.sub(lambda m: m.group(2) + m.group(1), texto)


def verificar(texto: str, total: int) -> tuple[list[dict], int]:
    """Parte el texto del modelo en oraciones y se queda con las citadas.

    Devuelve ``(oraciones, descartadas)``. Cada oración es
    ``{"text": …, "refs": ["A1", …]}``, con el texto **sin** las citas (la
    pantalla las dibuja como enlaces). Una oración se descarta si no cita
    nada o si alguna de sus citas no existe: una cita inventada es la señal de
    que el modelo está completando de memoria.
    """
    oraciones, descartadas = [], 0
    texto = _mover_citas(texto or "")
    for cruda in _CORTE.split(texto):
        cruda = cruda.strip()
        if not cruda or not re.search(r"\w", _CITA.sub("", cruda)):
            continue
        numeros = [int(n) for n in _CITA.findall(cruda)]
        if not numeros or any(n < 1 or n > total for n in numeros):
            descartadas += 1
            continue
        limpia = " ".join(_CITA.sub("", cruda).split())
        limpia = re.sub(r"\s+([.,;:!?])", r"\1", limpia)
        refs = list(dict.fromkeys(f"A{n}" for n in numeros))
        oraciones.append({"text": limpia, "refs": refs})
    return oraciones, descartadas


def _plantilla(fuentes: list[dict]) -> list[dict]:
    """El resumen sin modelo: cada diagnóstico, copiado tal cual, con su cita."""
    return [
        {"text": f"{f['date']} · {f['branch']} · {f['practitioner']}: {f['diagnosis']}",
         "refs": [f["ref"]]}
        for f in fuentes if f["diagnosis"]
    ]


def summarize(paciente) -> dict:
    """Arma el resumen del historial. Nunca lanza por culpa del proveedor."""
    encuentros = list(
        Encounter.objects
        .filter(organization=paciente.organization, patient=paciente,
                status=Encounter.Status.SIGNED)
        .select_related("appointment", "branch", "practitioner")
        .prefetch_related("amendments", "prescription_items", "orders")
        .order_by("-appointment__starts_at")[:MAX_ENCOUNTERS]
    )
    fuentes = _fuentes(encuentros)
    resultado = {
        "alerts": _alertas(paciente),
        "sources": fuentes,
        "sentences": [],
        "discarded": 0,
        "generated_by": "sin_datos",
    }
    if not encuentros:
        return resultado

    oraciones, descartadas = [], 0
    if settings.ASSISTANT_CHAT_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
        try:
            oraciones, descartadas = verificar(_call_model(_contexto(encuentros)),
                                               len(encuentros))
        except Exception:
            # El médico no tiene por qué leer un error de cuota: se degrada y
            # el `generated_by` lo deja a la vista.
            oraciones, descartadas = [], 0

    if oraciones:
        resultado.update(sentences=oraciones, discarded=descartadas,
                         generated_by="gemini")
    else:
        resultado.update(sentences=_plantilla(fuentes), discarded=descartadas,
                         generated_by="plantilla")
    return resultado


def _call_model(contexto: str) -> str:
    """La llamada al proveedor, sola, para que las pruebas la simulen."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    response = client.models.generate_content(
        model=settings.ASSISTANT_CHAT_MODEL,
        contents=f"Atenciones del paciente:\n\n{contexto}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=500,
        ),
    )
    return (response.text or "").strip()
