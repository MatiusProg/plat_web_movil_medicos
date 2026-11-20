"""US-49 — De «cada 8 horas por 5 días» a un horario de tomas.

La receta (US-26) guarda la frecuencia y la duración **como texto libre**,
porque así las escribe el médico. Para programar avisos hace falta un número:
cada cuántas horas y cuántas tomas en total. Este módulo hace esa traducción,
y **cuando no está seguro, no inventa**: devuelve el motivo y la app dice «Esta
indicación no tiene horario fijo» en vez de ofrecer un recordatorio
equivocado.

Lo que entiende:

- «cada 8 horas», «c/8 h», «cada 8hs», «cada ocho horas»
- «3 veces al día», «tres veces por día», «2 veces x día»
- «una vez al día», «1 vez al día», «diario», «cada día», «cada 24 horas»
- «cada 2 días», «cada 48 horas»

Lo que **no** convierte en horario, aunque traiga un número:

- lo condicional: «según dolor», «si hay fiebre», «a demanda», «PRN», «SOS»,
  «cada 8 horas si hay dolor»;
- una duración vacía, «continuo», «indefinido» o «hasta nuevo aviso».

Las mismas reglas valen para el paciente y para el médico: el porcentaje de
cumplimiento que ve el médico se calcula sobre el total que sale de acá.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

# Topes: más allá de esto no es un tratamiento que se recuerde con avisos.
MAX_DIAS = 90
MAX_TOMAS = 200

# Motivos por los que no hay horario. La app los muestra con una frase.
SIN_HORARIO_FIJO = "no_fixed_schedule"
SIN_DURACION = "no_duration"
DEMASIADAS_TOMAS = "too_many_doses"

MOTIVOS = {
    SIN_HORARIO_FIJO: "Esta indicación no tiene horario fijo.",
    SIN_DURACION: "La receta no dice por cuántos días: no se puede programar.",
    DEMASIADAS_TOMAS: "El tratamiento es demasiado largo para recordarlo con avisos.",
}

_NUMEROS = {
    "un": 1, "una": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5,
    "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11,
    "doce": 12, "trece": 13, "catorce": 14, "quince": 15, "veinte": 20,
    "veintiuno": 21, "treinta": 30, "cuarenta y ocho": 48, "veinticuatro": 24,
}
_NUM = r"(\d+|" + "|".join(sorted(_NUMEROS, key=len, reverse=True)) + r")"

_CONDICIONAL = re.compile(
    r"\b(segun|si\s+(hay|tiene|presenta|persiste)|en\s+caso|a\s+demanda|"
    r"prn|sos|cuando\s+(sea\s+necesario|lo\s+necesite|haya)|condicional|"
    r"necesidad|necesario)\b"
)
_SIN_FIN = re.compile(r"\b(continu[oa]|indefinid[oa]|permanente|cronic[oa]|"
                      r"hasta\s+nuevo\s+aviso|de\s+por\s+vida)\b")

_CADA_HORAS = re.compile(rf"(?:cada|c/)\s*{_NUM}\s*(?:h|hs|hrs|horas?)\b")
_CADA_HORA = re.compile(r"\bcada\s+hora\b")
_VECES_DIA = re.compile(rf"\b{_NUM}\s*(?:veces|vez)\s*(?:al|por|x|a\s+l)\s*dia\b")
_UNA_VEZ = re.compile(r"\b(diari[oa]|cada\s+dia|todos\s+los\s+dias|"
                      r"una\s+vez\s+al\s+dia)\b")
_CADA_DIAS = re.compile(rf"\bcada\s+{_NUM}\s*dias?\b")

_DURACION = re.compile(rf"\b{_NUM}\s*(dias?|semanas?|mes(?:es)?)\b")
_UNA_SEMANA = re.compile(r"\buna\s+semana\b")


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes.lower()).strip()


def _numero(valor: str) -> int:
    return int(valor) if valor.isdigit() else _NUMEROS[valor]


def intervalo_en_horas(frecuencia: str) -> int | None:
    """Cada cuántas horas, o ``None`` si no hay un horario fijo."""
    texto = _normalizar(frecuencia)
    if not texto or _CONDICIONAL.search(texto):
        return None

    if m := _CADA_HORAS.search(texto):
        horas = _numero(m.group(1))
        return horas if 1 <= horas <= 72 else None
    if _CADA_HORA.search(texto):
        return 1
    if m := _VECES_DIA.search(texto):
        veces = _numero(m.group(1))
        # Sólo repartos exactos del día: «5 veces al día» no da horas enteras.
        return 24 // veces if veces and 24 % veces == 0 else None
    if m := _CADA_DIAS.search(texto):
        dias = _numero(m.group(1))
        return 24 * dias if 1 <= dias <= 3 else None
    if _UNA_VEZ.search(texto):
        return 24
    return None


def dias_de_tratamiento(duracion: str) -> int | None:
    """Cuántos días dura, o ``None`` si no lo dice o no tiene fin."""
    texto = _normalizar(duracion)
    if not texto or _SIN_FIN.search(texto):
        return None
    if m := _DURACION.search(texto):
        cantidad = _numero(m.group(1))
        unidad = m.group(2)
        dias = cantidad * (7 if unidad.startswith("semana")
                           else 30 if unidad.startswith("mes") else 1)
        return dias if 1 <= dias <= MAX_DIAS else None
    if _UNA_SEMANA.search(texto):
        return 7
    return None


@dataclass(frozen=True)
class Horario:
    interval_hours: int
    days: int
    total_doses: int

    def as_dict(self):
        return asdict(self)


def interpretar(frecuencia: str, duracion: str) -> tuple[Horario | None, str | None]:
    """``(horario, None)`` si se puede programar, o ``(None, motivo)``.

    «cada 8 horas» por «5 días» son 15 tomas: ``5 * 24 / 8``. Si el intervalo no
    entra justo en los días, se redondea hacia abajo: no se agrega una toma
    después de que el tratamiento terminó.
    """
    intervalo = intervalo_en_horas(frecuencia)
    if intervalo is None:
        return None, SIN_HORARIO_FIJO
    dias = dias_de_tratamiento(duracion)
    if dias is None:
        return None, SIN_DURACION
    total = max(1, dias * 24 // intervalo)
    if total > MAX_TOMAS:
        return None, DEMASIADAS_TOMAS
    return Horario(interval_hours=intervalo, days=dias, total_doses=total), None


def para_la_api(frecuencia: str, duracion: str) -> dict:
    """Lo que viaja en cada medicamento de la receta (`schedule`)."""
    horario, motivo = interpretar(frecuencia, duracion)
    if horario is None:
        return {"schedule": None, "schedule_reason": MOTIVOS[motivo]}
    return {"schedule": horario.as_dict(), "schedule_reason": None}
