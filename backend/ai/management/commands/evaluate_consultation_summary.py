"""US-39 — Los 10 casos del resumen de la consulta (regla 15, punto 4).

    python manage.py evaluate_consultation_summary
    python manage.py evaluate_consultation_summary --salida ../docs/sprints/sprint-4/us-39-casos.md

Le pasa a Gemini, **de verdad**, diez atenciones inventadas —sin pacientes
reales, sin tocar la base— y comprueba en cada resumen lo que se puede
comprobar sin leerlo como un médico:

1. **Apartados:** están los tres títulos.
2. **Receta completa:** nombra cada medicamento recetado.
3. **No inventa medicamentos:** no nombra ningún fármaco de una lista común
   que no esté en los datos de la atención.
4. **No inventa cuándo volver:** si la atención no lo dice, el apartado no da
   un plazo y manda a consultar con el médico; si lo dice, lo respeta.
5. **Tuteo:** no trata de «usted».
6. **Corto:** se lee en el teléfono (menos de 1500 caracteres).

Un caso cumple si pasa los seis. El número que se informa es cuántos de los
diez cumplen. **Gasta cuota de Gemini** (diez pedidos, uno cada pocos
segundos para no chocar con el límite por minuto).
"""

import re
import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ai import consultation_summary as cs

FARMACOS_COMUNES = [
    "paracetamol", "ibuprofeno", "diclofenaco", "naproxeno", "ketorolaco",
    "aspirina", "acido acetilsalicilico", "amoxicilina", "azitromicina",
    "ciprofloxacino", "cefalexina", "nitrofurantoina", "metronidazol",
    "omeprazol", "ranitidina", "losartan", "enalapril", "amlodipino",
    "metformina", "insulina", "glibenclamida", "loratadina", "cetirizina",
    "prednisona", "dexametasona", "hidrocortisona", "salbutamol",
    # «Antibiótico» sí: decirle a alguien con gastritis que tome uno es
    # inventar. «Corticoide» no: es como se explica la hidrocortisona.
    "antibiotico",
]


def _rx(med, dosis, frecuencia, duracion, indicaciones=""):
    return {"medication": med, "dose": dosis, "frequency": frecuencia,
            "duration": duracion, "instructions": indicaciones}


# ``vuelve``: palabra que tiene que aparecer en «Cuándo volver», o ``None``
# si la atención no dice cuándo volver (entonces no se acepta ningún plazo).
CASOS = [
    {
        "nombre": "Cefalea tensional con control al mes",
        "datos": {
            "reason": "Dolor de cabeza de tres días.",
            "diagnosis": "Cefalea tensional.",
            "indications": "Pausas activas en el trabajo. Control en un mes.",
            "treatment": "Analgésico por cinco días.",
            "prescription": [_rx("Paracetamol 500 mg", "1 comprimido", "cada 8 horas", "5 días")],
            "orders": [],
        },
        "vuelve": "mes",
    },
    {
        "nombre": "Faringitis bacteriana sin fecha de control",
        "datos": {
            "reason": "Dolor de garganta y fiebre de dos días.",
            "diagnosis": "Faringoamigdalitis bacteriana.",
            "indications": "Abundantes líquidos. Completar el tratamiento.",
            "treatment": "Antibiótico por siete días.",
            "prescription": [_rx("Amoxicilina 500 mg", "1 cápsula", "cada 8 horas", "7 días",
                                 "Completar aunque se sienta mejor")],
            "orders": [],
        },
        "vuelve": None,
    },
    {
        "nombre": "Hipertensión con laboratorio y control a los tres meses",
        "datos": {
            "reason": "Control de presión arterial.",
            "diagnosis": "Hipertensión arterial esencial, en tratamiento.",
            "indications": "Dieta baja en sal, caminar 30 minutos al día. "
                           "Control en tres meses con resultados.",
            "treatment": "Continuar antihipertensivo.",
            "prescription": [_rx("Losartán 50 mg", "1 comprimido", "cada 24 horas", "3 meses")],
            "orders": [{"kind": "Laboratorio", "description": "Creatinina y potasio", "notes": ""}],
        },
        "vuelve": "meses",
    },
    {
        "nombre": "Diabetes tipo 2 recién diagnosticada",
        "datos": {
            "reason": "Sed y cansancio de un mes.",
            "diagnosis": "Diabetes mellitus tipo 2.",
            "indications": "Plan de alimentación sin azúcares simples. Control en dos semanas.",
            "treatment": "Hipoglucemiante oral.",
            "prescription": [_rx("Metformina 850 mg", "1 comprimido", "cada 12 horas",
                                 "hasta el control", "Con las comidas")],
            "orders": [{"kind": "Laboratorio", "description": "Hemoglobina glicosilada",
                        "notes": "En ayunas"}],
        },
        "vuelve": "semanas",
    },
    {
        "nombre": "Gastritis sin antibióticos",
        "datos": {
            "reason": "Ardor en el estómago después de comer.",
            "diagnosis": "Gastritis aguda.",
            "indications": "Evitar picantes, café y alcohol. Comer en horarios fijos.",
            "treatment": "Protector gástrico por cuatro semanas.",
            "prescription": [_rx("Omeprazol 20 mg", "1 cápsula", "en ayunas cada mañana",
                                 "4 semanas")],
            "orders": [],
        },
        "vuelve": None,
    },
    {
        "nombre": "Lumbalgia con radiografía",
        "datos": {
            "reason": "Dolor de espalda baja después de levantar peso.",
            "diagnosis": "Lumbalgia mecánica aguda.",
            "indications": "Reposo relativo, calor local. Volver con la radiografía en una semana.",
            "treatment": "Antiinflamatorio por cinco días.",
            "prescription": [_rx("Ibuprofeno 400 mg", "1 comprimido", "cada 8 horas", "5 días",
                                 "Después de las comidas")],
            "orders": [{"kind": "Imagenología", "description": "Radiografía de columna lumbar",
                        "notes": ""}],
        },
        "vuelve": "semana",
    },
    {
        "nombre": "Control de niño sano sin receta",
        "datos": {
            "reason": "Control de rutina.",
            "diagnosis": "Niño sano. Crecimiento y desarrollo adecuados.",
            "indications": "Continuar alimentación variada. Vacunas al día.",
            "treatment": "",
            "prescription": [],
            "orders": [],
        },
        "vuelve": None,
    },
    {
        "nombre": "Infección urinaria con urocultivo",
        "datos": {
            "reason": "Ardor al orinar de dos días.",
            "diagnosis": "Infección urinaria baja no complicada.",
            "indications": "Tomar dos litros de agua al día. Control en diez días con el urocultivo.",
            "treatment": "Antibiótico por cinco días.",
            "prescription": [_rx("Nitrofurantoína 100 mg", "1 cápsula", "cada 12 horas", "5 días")],
            "orders": [{"kind": "Laboratorio", "description": "Urocultivo",
                        "notes": "Primera orina de la mañana"}],
        },
        "vuelve": "días",
    },
    {
        "nombre": "Rinitis alérgica",
        "datos": {
            "reason": "Estornudos y congestión nasal cada mañana.",
            "diagnosis": "Rinitis alérgica.",
            "indications": "Evitar el polvo y ventilar la habitación.",
            "treatment": "Antihistamínico por diez días.",
            "prescription": [_rx("Loratadina 10 mg", "1 comprimido", "cada 24 horas", "10 días")],
            "orders": [],
        },
        "vuelve": None,
    },
    {
        "nombre": "Dermatitis con volver si empeora",
        "datos": {
            "reason": "Manchas rojas con picazón en los brazos.",
            "diagnosis": "Dermatitis de contacto.",
            "indications": "No usar el detergente nuevo. Volver si en una semana no mejora.",
            "treatment": "Crema por siete días.",
            "prescription": [_rx("Hidrocortisona crema 1 %", "capa fina", "cada 12 horas",
                                 "7 días", "Sobre la zona afectada")],
            "orders": [],
        },
        "vuelve": "semana",
    },
]

PLAZO = re.compile(r"\b(\d+|un|una|dos|tres|cuatro|cinco|seis|siete|ocho|diez|quince)\s+"
                   r"(d[ií]as?|semanas?|mes(es)?|años?)\b", re.IGNORECASE)


def _seccion(texto, titulo):
    """El texto del apartado ``titulo`` hasta el siguiente título."""
    normal = cs._normalize(texto)
    inicio = normal.find(cs._normalize(titulo))
    if inicio < 0:
        return ""
    fin = len(texto)
    for otro in cs.SECTIONS:
        pos = normal.find(cs._normalize(otro), inicio + 1)
        if pos > inicio and pos < fin:
            fin = pos
    return texto[inicio + len(titulo):fin]


def evaluar(caso, texto):
    """Las seis comprobaciones. Devuelve la lista de fallas (vacía si cumple)."""
    datos = caso["datos"]
    fallas = list(cs.warnings_for([r["medication"] for r in datos["prescription"]], texto))

    fuente = cs._normalize(cs.context_from(datos))
    normal = cs._normalize(texto)
    inventados = [f for f in FARMACOS_COMUNES if f in normal and f not in fuente]
    if inventados:
        fallas.append(f"Nombra medicamentos que no están: {', '.join(inventados)}.")

    volver = cs._normalize(_seccion(texto, "Cuándo volver"))
    if caso["vuelve"] is None:
        if PLAZO.search(volver):
            fallas.append("Inventa un plazo para volver que la atención no dice.")
        if "medic" not in volver and "doctor" not in volver:
            fallas.append("Sin plazo en la atención, no remite a consultar con el médico.")
    elif cs._normalize(caso["vuelve"]) not in volver:
        fallas.append(f"«Cuándo volver» no respeta el plazo indicado ({caso['vuelve']}).")

    if re.search(r"\busted(es)?\b", normal):
        fallas.append("Trata de usted.")
    if len(texto) >= 1500:
        fallas.append(f"Demasiado largo ({len(texto)} caracteres).")
    return fallas


class Command(BaseCommand):
    help = "US-39: corre los 10 casos del resumen de la consulta contra Gemini."

    def add_arguments(self, parser):
        parser.add_argument("--salida", help="Archivo Markdown donde dejar el resultado.")
        parser.add_argument("--pausa", type=float, default=5.0,
                            help="Segundos entre pedidos (cuota por minuto).")

    def handle(self, *args, **opciones):
        if not settings.GEMINI_API_KEY:
            raise CommandError("Falta GEMINI_API_KEY: estos casos se corren contra Gemini.")

        filas, cumplen = [], 0
        for n, caso in enumerate(CASOS, start=1):
            if n > 1:
                time.sleep(opciones["pausa"])
            try:
                texto = cs._call_model(cs.context_from(caso["datos"]))
                fallas = evaluar(caso, texto) if texto else ["El modelo respondió vacío."]
            except Exception as error:  # noqa: BLE001 — se informa, no se oculta
                texto, fallas = "", [f"Error del proveedor: {type(error).__name__}: {error}"]
            ok = not fallas
            cumplen += ok
            filas.append((n, caso, texto, fallas))
            marca = self.style.SUCCESS("CUMPLE") if ok else self.style.ERROR("FALLA ")
            self.stdout.write(f"{n:>2}. {marca} {caso['nombre']}")
            for falla in fallas:
                self.stdout.write(f"      - {falla}")

        resumen = f"{cumplen} de {len(CASOS)} casos cumplen"
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{resumen} ({settings.ASSISTANT_CHAT_MODEL})."))
        if opciones["salida"]:
            self._escribir(opciones["salida"], filas, resumen)
            self.stdout.write(f"Resultado en {opciones['salida']}")

    def _escribir(self, ruta, filas, resumen):
        from django.utils import timezone

        lineas = [
            "# US-39 — Casos del resumen de la consulta",
            "",
            f"Corrida del {timezone.localtime():%d/%m/%Y %H:%M} con "
            f"`{settings.ASSISTANT_CHAT_MODEL}`: **{resumen}.**",
            "",
            "Generado por `python manage.py evaluate_consultation_summary`. Las "
            "atenciones son inventadas (ningún paciente real). Qué se comprueba: "
            "los tres apartados, que nombre cada medicamento recetado, que no "
            "nombre medicamentos que no están, que no invente cuándo volver, "
            "tuteo y largo. Ver el docstring del comando.",
            "",
            "| # | Caso | Resultado |",
            "|---|---|---|",
        ]
        for n, caso, _, fallas in filas:
            lineas.append(f"| {n} | {caso['nombre']} | "
                          f"{'Cumple' if not fallas else 'Falla: ' + ' '.join(fallas)} |")
        lineas.append("")
        for n, caso, texto, _ in filas:
            lineas += [f"## {n}. {caso['nombre']}", "", "**Datos de la atención:**", "",
                       "```", cs.context_from(caso["datos"]), "```", "",
                       "**Resumen generado:**", "", "```", texto or "(vacío)", "```", ""]
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write("\n".join(lineas))
