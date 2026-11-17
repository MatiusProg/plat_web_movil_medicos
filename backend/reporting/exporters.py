"""Característica general 5 — «todo reporte debe poder exportarse a otros
formatos: Excel, HTML, eMail, PDF».

Cuatro formatos y un canal. El canal —el correo— no es un quinto formato: es
cualquiera de los cuatro, adjunto. Eso está en ``delivery.py``; acá sólo se
producen bytes.

**Todo exportador recibe lo mismo y devuelve lo mismo**: encabezados, filas,
título, y devuelve ``(bytes, tipo_mime, extensión)``. Esa uniformidad es lo que
permite que la vista elija el formato con una línea y que agregar uno nuevo
—ODS, JSON— no la toque.

**Las dependencias pesadas se importan dentro de la función, no arriba.**
``openpyxl`` y ``reportlab`` sólo hacen falta si alguien pide ese formato; con
el import arriba, un despliegue al que le falte una de las dos no arranca en
lugar de fallar en el único endpoint que la necesita. Ya pasó con otra cosa en
este proyecto: un error de importación en un módulo que nadie usaba tumbaba el
proceso entero.
"""

import csv
import datetime as dt
import io
import re
from decimal import Decimal
from html import escape

from django.utils import timezone

# Qué produce cada formato. La vista valida contra estas claves.
FORMATS = ("csv", "xlsx", "html", "pdf")

MIME = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": ("application/vnd.openxmlformats-officedocument"
             ".spreadsheetml.sheet"),
    "html": "text/html; charset=utf-8",
    "pdf": "application/pdf",
}


class QRCelda:
    """Una celda que en el PDF es un código QR y en los demás formatos, su texto.

    US-46: la lista de comprobantes del paciente lleva el código firmado de
    cada ficha. En CSV, Excel y HTML ese código es una cadena como cualquier
    otra (``str(celda)``), así que esos exportadores no necesitan saber que
    existe; sólo ``_pdf`` la reconoce y la dibuja. La firma de ``export`` no
    cambia: una fila sigue siendo una lista de valores.
    """

    __slots__ = ("valor",)

    def __init__(self, valor):
        self.valor = str(valor)

    def __str__(self):
        return self.valor

    def __repr__(self):
        return f"QRCelda({self.valor!r})"


class FilaDeGrupo(list):
    """Una fila que abre un grupo: un título, no un dato.

    US-46: la lista de comprobantes puede agruparse por mes, sucursal o
    especialidad. En el PDF es una fila combinada y sombreada con el nombre del
    grupo, su cantidad y su total; en CSV, Excel y HTML, una fila común con ese
    texto en la primera celda. Se construye con el mismo ancho que las demás
    filas (`[texto, "", "", ...]`) y **no cuenta como fila de datos** en el
    pie («N fila(s)»).
    """

    __slots__ = ()

    @property
    def texto(self) -> str:
        return str(self[0]) if self else ""


def _filas_de_datos(rows) -> int:
    return sum(1 for fila in rows if not isinstance(fila, FilaDeGrupo))


def export(fmt: str, headers, rows, title: str, subtitle: str = "",
           truncated: bool = False):
    """Devuelve ``(contenido_en_bytes, tipo_mime, nombre_de_archivo)``."""
    if fmt not in FORMATS:
        raise ValueError(f"Formato no soportado: {fmt}")

    contenido = _EXPORTERS[fmt](headers, rows, title, subtitle, truncated)
    return contenido, MIME[fmt], f"{slugify(title)}.{fmt}"


def slugify(texto: str) -> str:
    """Un nombre de archivo que sobreviva a Windows, a un adjunto de correo y
    a una cabecera ``Content-Disposition``.

    Sin esto, un reporte llamado «Pacientes: altas 09/2026» produce un nombre
    con dos puntos y barras, que Windows rechaza al guardar y que parte la
    cabecera HTTP en dos.
    """
    limpio = re.sub(r"[^\w\s-]", "", texto, flags=re.UNICODE).strip()
    limpio = re.sub(r"[\s_]+", "-", limpio).lower()
    return limpio[:80] or "reporte"


def _pie(truncated: bool, filas: int) -> str:
    """La nota al pie. Un reporte cortado tiene que decirlo en el archivo, no
    sólo en la respuesta de la API: el archivo es lo que se reenvía."""
    generado = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    nota = f"{filas} fila(s) · generado el {generado}"
    if truncated:
        nota += (" · ATENCIÓN: el resultado se truncó. Agregá criterios de "
                 "selección para verlo completo.")
    return nota


# --------------------------------------------------------------------------
#  CSV
# --------------------------------------------------------------------------
def _csv(headers, rows, title, subtitle, truncated):
    """CSV con BOM, punto y coma, a propósito.

    Las dos decisiones son para Excel en español, que es donde esto se abre:

    - **BOM UTF-8.** Sin él, Excel lee el archivo como ANSI y «Pérez» sale
      «PÃ©rez». Es el mismo tropiezo que los `.ps1` de los generadores de
      diagramas.
    - **Punto y coma.** Excel con configuración regional en español usa la coma
      como separador decimal y espera `;` entre campos. Con coma, todo el
      reporte cae en la primera columna.
    """
    buffer = io.StringIO()
    escritor = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    escritor.writerow(headers)
    for fila in rows:
        escritor.writerow(fila)
    escritor.writerow([])
    escritor.writerow([_pie(truncated, _filas_de_datos(rows))])
    return buffer.getvalue().encode("utf-8-sig")


# --------------------------------------------------------------------------
#  Excel
# --------------------------------------------------------------------------
def _xlsx(headers, rows, title, subtitle, truncated):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    libro = Workbook()
    hoja = libro.active
    # El nombre de una hoja no admite : \ / ? * [ ] y se corta en 31
    # caracteres. openpyxl no avisa: guarda un archivo que Excel se niega a
    # abrir.
    hoja.title = re.sub(r"[:\\/?*\[\]]", "-", title)[:31] or "Reporte"

    fila_actual = 1
    hoja.cell(row=1, column=1, value=title).font = Font(bold=True, size=14)
    fila_actual += 1
    if subtitle:
        hoja.cell(row=fila_actual, column=1, value=subtitle).font = Font(
            italic=True, size=10, color="555555",
        )
        fila_actual += 1
    fila_actual += 1

    fila_encabezado = fila_actual
    relleno = PatternFill("solid", start_color="1F4E79")
    for columna, encabezado in enumerate(headers, start=1):
        celda = hoja.cell(row=fila_encabezado, column=columna, value=encabezado)
        celda.font = Font(bold=True, color="FFFFFF")
        celda.fill = relleno
        celda.alignment = Alignment(vertical="center")

    for desplazamiento, fila in enumerate(rows, start=1):
        for columna, valor in enumerate(fila, start=1):
            celda = hoja.cell(row=fila_encabezado + desplazamiento,
                              column=columna, value=_excel_value(valor))
            if isinstance(valor, Decimal):
                celda.number_format = "#,##0.00"

    # Ancho por contenido. Sin esto todas las columnas salen en 8,43 y las
    # fechas se ven como `#######`, que es el reclamo número uno de cualquier
    # exportación a Excel.
    for columna, encabezado in enumerate(headers, start=1):
        largo = max(
            [len(str(encabezado))]
            + [len(str(fila[columna - 1])) for fila in rows[:200]]
        )
        hoja.column_dimensions[get_column_letter(columna)].width = min(
            max(largo + 2, 10), 50,
        )

    # Congela el encabezado y habilita el autofiltro: quien recibe el Excel va
    # a querer seguir filtrando, y es gratis dárselo.
    hoja.freeze_panes = hoja.cell(row=fila_encabezado + 1, column=1)
    if rows:
        ultima = get_column_letter(len(headers))
        hoja.auto_filter.ref = (
            f"A{fila_encabezado}:{ultima}{fila_encabezado + len(rows)}"
        )

    pie = hoja.cell(row=fila_encabezado + len(rows) + 2, column=1,
                    value=_pie(truncated, _filas_de_datos(rows)))
    pie.font = Font(italic=True, size=9, color="808080")

    salida = io.BytesIO()
    libro.save(salida)
    return salida.getvalue()


def _excel_value(valor):
    """Lo que openpyxl sabe escribir.

    Un ``UUID`` o un ``time`` de Python le hacen lanzar ``ValueError: Cannot
    convert``. Se pasan como texto; los tipos que Excel sí entiende —número,
    fecha, instante— se dejan como están para que la celda quede tipada y se
    pueda ordenar. Un ``Decimal`` (el importe de un pago) pasa a ``float``: como
    texto la columna no se podría sumar, y con dos decimales no pierde nada.
    """
    if isinstance(valor, Decimal):
        return float(valor)
    if isinstance(valor, dt.datetime) and valor.tzinfo is not None:
        # Excel no guarda zonas horarias: openpyxl lanza ``TypeError`` con un
        # instante «aware». Se escribe la hora de pared de la zona del
        # proyecto, que es la que muestran las demás pantallas.
        return timezone.localtime(valor).replace(tzinfo=None)
    if isinstance(valor, (int, float, dt.date, dt.datetime)) and not isinstance(
        valor, bool
    ):
        return valor
    return str(valor)


# --------------------------------------------------------------------------
#  HTML
# --------------------------------------------------------------------------
def _html(headers, rows, title, subtitle, truncated):
    """Un HTML de una sola pieza, con los estilos adentro.

    Sin hoja externa a propósito: el archivo se abre desde el disco o se pega
    en un correo, y en los dos casos un ``<link>`` a un CSS del servidor no
    resuelve. Todo escapado con ``html.escape``: los datos vienen de campos que
    cargó un usuario, y un apellido con ``<`` rompería la tabla.
    """
    encabezados = "".join(f"<th>{escape(str(h))}</th>" for h in headers)
    cuerpo = "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in fila) + "</tr>"
        for fila in rows
    )
    aviso = ""
    if truncated:
        aviso = (
            '<p class="aviso">El resultado se truncó. Agregá criterios de '
            "selección para verlo completo.</p>"
        )

    return f"""<!doctype html>
<html lang="es">
<meta charset="utf-8">
<title>{escape(title)}</title>
<style>
  body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
         margin: 2rem; color: #1a1a1a; background: #fff; }}
  h1 {{ font-size: 1.4rem; margin: 0 0 .25rem; }}
  .subtitulo {{ color: #555; margin: 0 0 1.5rem; font-size: .9rem; }}
  .aviso {{ background: #fff4e5; border-left: 4px solid #d97706;
            padding: .75rem 1rem; font-size: .9rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .875rem; }}
  th {{ background: #1f4e79; color: #fff; text-align: left;
        padding: .5rem .75rem; position: sticky; top: 0; }}
  td {{ padding: .45rem .75rem; border-bottom: 1px solid #e5e7eb; }}
  tr:nth-child(even) td {{ background: #f9fafb; }}
  footer {{ margin-top: 1.5rem; color: #6b7280; font-size: .8rem; }}
  @media print {{ body {{ margin: 0; }} th {{ position: static; }} }}
</style>
<h1>{escape(title)}</h1>
<p class="subtitulo">{escape(subtitle)}</p>
{aviso}
<table><thead><tr>{encabezados}</tr></thead><tbody>{cuerpo}</tbody></table>
<footer>{escape(_pie(truncated, _filas_de_datos(rows)))}</footer>
</html>""".encode("utf-8")


# --------------------------------------------------------------------------
#  PDF
# --------------------------------------------------------------------------
def _pdf(headers, rows, title, subtitle, truncated):
    """PDF con ``reportlab``.

    **Apaisado y no vertical.** Un reporte con seis columnas no entra en A4
    vertical y reportlab no avisa: recorta la tabla por la derecha y el PDF
    sale con columnas faltantes.

    **El ancho de columna se reparte por contenido**, no en partes iguales: con
    partes iguales, «Activo» ocupa lo mismo que «Dirección» y la dirección se
    parte en cuatro renglones.
    """
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
    )

    salida = io.BytesIO()
    documento = SimpleDocTemplate(
        salida, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=14 * mm,
        title=title, author="Plataforma médica",
    )

    estilos = getSampleStyleSheet()
    celda = ParagraphStyle(
        "celda", parent=estilos["BodyText"], fontSize=7.5, leading=9.5,
        alignment=TA_LEFT, spaceAfter=0, spaceBefore=0,
    )
    celda_encabezado = ParagraphStyle(
        "celda_encabezado", parent=celda, textColor=colors.white,
        fontName="Helvetica-Bold",
    )

    # Cada celda es un Paragraph para que el texto largo se envuelva. Con
    # cadenas sueltas, reportlab no parte la línea y la columna se ensancha
    # hasta empujar a las demás fuera de la página.
    tabla_datos = [[Paragraph(escape(str(h)), celda_encabezado) for h in headers]]
    celda_grupo = ParagraphStyle(
        "celda_grupo", parent=celda, fontName="Helvetica-Bold", fontSize=8.5,
        leading=11,
    )
    tabla_datos += [
        [_parrafo(fila.texto, celda_grupo)] + [""] * (len(headers) - 1)
        if isinstance(fila, FilaDeGrupo)
        else [_celda_del_pdf(v, celda) for v in fila]
        for fila in rows
    ]
    # Dónde están los encabezados de grupo (la fila 0 es el encabezado de la tabla).
    filas_de_grupo = [
        indice for indice, fila in enumerate(rows, start=1)
        if isinstance(fila, FilaDeGrupo)
    ]
    solo_datos = [fila for fila in rows if not isinstance(fila, FilaDeGrupo)]

    disponible = documento.width
    anchos = _anchos_con_qr(headers, solo_datos, disponible, QR_LADO_MM * mm)
    columnas_qr = _columnas_qr(solo_datos)

    tabla = Table(tabla_datos, colWidths=anchos, repeatRows=1)
    tabla.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E79")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#F9FAFB")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        # Un encabezado de grupo ocupa todo el ancho y se distingue de los datos.
        *[estilo for fila in filas_de_grupo for estilo in (
            ("SPAN", (0, fila), (-1, fila)),
            ("BACKGROUND", (0, fila), (-1, fila), colors.HexColor("#DBEAFE")),
            ("TOPPADDING", (0, fila), (-1, fila), 5),
            ("BOTTOMPADDING", (0, fila), (-1, fila), 5),
        )],
        # El QR va centrado en su celda; el resto del contenido, arriba.
        *[estilo for c in columnas_qr for estilo in (
            ("VALIGN", (c, 1), (c, -1), "MIDDLE"),
            ("ALIGN", (c, 1), (c, -1), "CENTER"),
        )],
    ]))

    historia = [
        Paragraph(escape(title), estilos["Title"]),
    ]
    if subtitle:
        historia.append(Paragraph(
            escape(subtitle),
            ParagraphStyle("sub", parent=estilos["Normal"], fontSize=9,
                           textColor=colors.HexColor("#555555")),
        ))
    if truncated:
        historia.append(Spacer(1, 4 * mm))
        historia.append(Paragraph(
            "El resultado se truncó. Agregá criterios de selección para verlo "
            "completo.",
            ParagraphStyle("aviso", parent=estilos["Normal"], fontSize=9,
                           textColor=colors.HexColor("#B45309")),
        ))
    historia.append(Spacer(1, 6 * mm))
    historia.append(tabla)

    documento.build(
        historia,
        onFirstPage=_pie_de_pagina(_pie(truncated, _filas_de_datos(rows))),
        onLaterPages=_pie_de_pagina(_pie(truncated, _filas_de_datos(rows))),
    )
    return salida.getvalue()


# Lado del QR en el PDF. El código firmado de una ficha tiene unos 150
# caracteres (un QR de versión 8 o 9): a 32 mm cada módulo mide medio milímetro,
# que lee cualquier teléfono y el lector del check-in, impreso o en pantalla.
QR_LADO_MM = 32


def _columnas_qr(rows):
    """Los índices de las columnas donde alguna fila trae un ``QRCelda``."""
    indices = set()
    for fila in rows:
        for indice, valor in enumerate(fila):
            if isinstance(valor, QRCelda):
                indices.add(indice)
    return sorted(indices)


def _celda_del_pdf(valor, estilo):
    """Un ``Drawing`` con el QR, o el ``Paragraph`` de siempre."""
    if isinstance(valor, QRCelda):
        return _dibujo_qr(valor.valor, QR_LADO_MM)
    return _parrafo(valor, estilo)


def _parrafo(valor, estilo):
    from reportlab.platypus import Paragraph

    return Paragraph(escape(str(valor)), estilo)


def _dibujo_qr(valor, lado_mm):
    """El QR de ``valor`` como dibujo vectorial, de ``lado_mm`` de lado."""
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.lib.units import mm

    # Corrección de errores media: aguanta una impresión sucia sin agrandar
    # el código más de lo que ya es.
    widget = QrCodeWidget(valor, barLevel="M")
    x0, y0, x1, y1 = widget.getBounds()
    lado = lado_mm * mm
    dibujo = Drawing(
        lado, lado, transform=[lado / (x1 - x0), 0, 0, lado / (y1 - y0), 0, 0],
    )
    dibujo.add(widget)
    return dibujo


def _anchos_con_qr(headers, rows, disponible, lado):
    """Como ``_anchos_de_columna``, pero con ancho fijo en las columnas QR.

    El código de una ficha mide 150 caracteres: medido por contenido, esa
    columna se llevaría media página. Las columnas QR reciben el lado del
    dibujo más el relleno y el resto se reparte lo que queda.
    """
    columnas_qr = _columnas_qr(rows)
    if not columnas_qr:
        return _anchos_de_columna(headers, rows, disponible)

    ancho_qr = lado + 10  # 4 pt de relleno a cada lado, más un respiro
    resto = [i for i in range(len(headers)) if i not in columnas_qr]
    repartido = _anchos_de_columna(
        [headers[i] for i in resto],
        [[fila[i] for i in resto] for fila in rows],
        max(disponible - ancho_qr * len(columnas_qr), 0),
    ) if resto else []

    anchos, siguiente = [], iter(repartido)
    for indice in range(len(headers)):
        anchos.append(ancho_qr if indice in columnas_qr else next(siguiente))
    return anchos


def _anchos_de_columna(headers, rows, disponible):
    """Reparte el ancho en proporción al contenido, con un piso y un techo.

    Se miran las primeras 200 filas y no todas: con veinte mil, medir cada
    celda cuesta más que dibujar el PDF, y a partir de un par de cientos el
    ancho típico de una columna ya no cambia.
    """
    muestras = rows[:200]
    pesos = []
    for indice, encabezado in enumerate(headers):
        largos = [len(str(encabezado))] + [
            len(str(fila[indice])) for fila in muestras
        ]
        # El promedio, no el máximo: una sola dirección larguísima no debe
        # quedarse con media página.
        promedio = sum(largos) / len(largos)
        pesos.append(max(min(promedio, 40), 6))

    total = sum(pesos)
    return [disponible * peso / total for peso in pesos]


def _pie_de_pagina(texto):
    """Dibuja el pie y el número de página en cada hoja."""
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    def dibujar(canvas, documento):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(12 * mm, 8 * mm, texto[:170])
        canvas.drawRightString(
            documento.pagesize[0] - 12 * mm, 8 * mm,
            f"Página {canvas.getPageNumber()}",
        )
        canvas.restoreState()

    return dibujar


_EXPORTERS = {
    "csv": _csv,
    "xlsx": _xlsx,
    "html": _html,
    "pdf": _pdf,
}
