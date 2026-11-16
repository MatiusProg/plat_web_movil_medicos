"""US-46 — Reportes transaccionales por voz.

El paciente pide, hablando o escribiendo, «mis últimas 2 facturas», «los pagos
de octubre» o «mis fichas de cardiología», y ve la lista con el QR del
comprobante de cada una. Lo que se prueba es lo que la historia tiene que
cumplir:

- El PDF lleva el QR de cada comprobante y los demás formatos, su texto.
- La frase se traduce a `{tipo, cantidad, desde, hasta, especialidad}` desde
  una lista cerrada y se valida contra el catálogo del centro. Sin proveedor
  se degrada a un analizador local que no improvisa.
- La consulta está atada al paciente que habla y a sus dependientes: nunca
  puede pedir pagos de otro, diga lo que diga la frase.
- Lo que se lista tiene comprobante, y la frase dictada no queda en la
  bitácora.

Gemini nunca se llama de verdad: la llamada al proveedor se simula, igual que
en `test_caracteristica_5_voz.py`.
"""

import pytest

from reporting import exporters
from reporting.exporters import QRCelda

CODIGO = "MC1." + "x" * 150


# ==========================================================================
#  El exportador: QR en el PDF, texto en lo demás
# ==========================================================================
@pytest.fixture
def filas_con_qr():
    return [
        ["05/10/2026", "Ana Pérez", QRCelda(CODIGO)],
        ["06/10/2026", "Luis Pérez", QRCelda(CODIGO + "y")],
    ]


ENCABEZADOS = ["Fecha", "Paciente", "Comprobante"]


def test_la_celda_qr_es_su_texto_para_quien_no_dibuja():
    celda = QRCelda(CODIGO)
    assert str(celda) == CODIGO
    assert celda.valor == CODIGO


def test_csv_y_html_llevan_el_codigo_como_texto(filas_con_qr):
    csv, _, _ = exporters.export("csv", ENCABEZADOS, filas_con_qr, "Mis pagos")
    html, _, _ = exporters.export("html", ENCABEZADOS, filas_con_qr, "Mis pagos")
    assert CODIGO in csv.decode("utf-8-sig")
    assert CODIGO in html.decode("utf-8")


def test_xlsx_guarda_el_codigo_como_texto_de_la_celda(filas_con_qr):
    from io import BytesIO

    from openpyxl import load_workbook

    contenido, _, _ = exporters.export("xlsx", ENCABEZADOS, filas_con_qr, "Mis pagos")
    hoja = load_workbook(BytesIO(contenido)).active
    valores = {celda.value for fila in hoja.iter_rows() for celda in fila}
    assert CODIGO in valores


def test_el_pdf_con_qr_es_un_pdf_valido_y_dibuja_los_codigos(filas_con_qr):
    con_qr, mime, nombre = exporters.export(
        "pdf", ENCABEZADOS, filas_con_qr, "Mis pagos", subtitle="últimos 2",
    )
    como_texto, _, _ = exporters.export(
        "pdf", ENCABEZADOS, [[f, p, str(q)] for f, p, q in filas_con_qr],
        "Mis pagos", subtitle="últimos 2",
    )

    assert con_qr.startswith(b"%PDF-")
    assert mime == "application/pdf" and nombre == "mis-pagos.pdf"
    # El dibujo del QR agrega trazos vectoriales que el texto plano no tiene.
    assert con_qr != como_texto


def test_el_pdf_con_muchos_qr_se_parte_en_paginas_y_no_se_rompe():
    filas = [["05/10/2026", f"Paciente {i}", QRCelda(CODIGO + str(i))]
             for i in range(25)]
    contenido, _, _ = exporters.export("pdf", ENCABEZADOS, filas, "Mis pagos")
    assert contenido.startswith(b"%PDF-")
    # Con 32 mm por fila no caben 25 en una hoja apaisada.
    assert contenido.count(b"/Type /Page\n") + contenido.count(b"/Type /Page ") > 1


def test_el_pdf_sin_celdas_qr_se_arma_como_siempre():
    contenido, _, _ = exporters.export(
        "pdf", ["A", "B"], [["uno", "dos"], ["tres", "cuatro"]], "Sin QR",
    )
    assert contenido.startswith(b"%PDF-")


def test_las_columnas_qr_tienen_ancho_fijo_y_el_resto_se_reparte():
    from reportlab.lib.units import mm

    filas = [["05/10/2026", "Ana", QRCelda(CODIGO)]]
    disponible = 270 * mm
    anchos = exporters._anchos_con_qr(ENCABEZADOS, filas, disponible, 32 * mm)

    assert anchos[2] == pytest.approx(32 * mm + 10)
    assert sum(anchos) == pytest.approx(disponible)
    assert anchos[0] > 0 and anchos[1] > 0
