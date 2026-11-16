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

import datetime as dt

import pytest

from payments import mine_voice
from payments.mine_voice import analizar, detectar_no_soportado, sanear_consulta
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


# ==========================================================================
#  El analizador local (sin proveedor): lo que el paciente dijo, nada más
# ==========================================================================
HOY = dt.date(2026, 11, 16)
ESPECIALIDADES = [
    ("id-cardio", "Cardiología"),
    ("id-pedia", "Pediatría"),
    ("id-general", "Medicina General"),
]


def leer(frase, hoy=HOY, nombres=()):
    return analizar(frase, ESPECIALIDADES, hoy, nombres)


def consulta_de(frase, **kw):
    consulta, unresolved, _ = leer(frase, **kw)
    assert consulta is not None, f"{frase!r} no se entendió: {unresolved}"
    return consulta


def motivos_de(frase, **kw):
    consulta, unresolved, _ = leer(frase, **kw)
    assert consulta is None, f"{frase!r} no debía entenderse: {consulta}"
    return unresolved


def test_ultimas_dos_facturas_son_pagos_con_cantidad_dos():
    consulta = consulta_de("mis últimas 2 facturas")
    assert consulta["tipo"] == "pagos"
    assert consulta["cantidad"] == 2
    assert consulta["desde"] is None and consulta["hasta"] is None
    assert consulta["especialidad"] is None


@pytest.mark.parametrize("frase", [
    "mis últimas dos facturas", "las dos últimas facturas", "dos facturas",
    "mis ULTIMAS 2 Facturas", "dame mis últimas 2 facturas por favor",
])
def test_dos_en_palabras_y_en_digitos_dan_lo_mismo(frase):
    assert consulta_de(frase)["cantidad"] == 2


@pytest.mark.parametrize("frase", [
    "mi última factura", "el último pago", "mi última ficha",
])
def test_una_ultima_en_singular_es_una(frase):
    assert consulta_de(frase)["cantidad"] == 1


def test_ultimas_sin_numero_no_pone_cantidad():
    consulta = consulta_de("mis últimas facturas")
    assert consulta["tipo"] == "pagos" and consulta["cantidad"] is None


@pytest.mark.parametrize("frase, esperado", [
    ("las últimas cinco fichas", 5), ("quince facturas", 15),
    ("mis últimas treinta y cinco facturas", 35),
    ("mis últimas veintidós fichas", 22), ("mis 10 últimas fichas", 10),
])
def test_las_cantidades_en_palabras_se_entienden(frase, esperado):
    assert consulta_de(frase)["cantidad"] == esperado


def test_cero_no_se_entiende_y_mas_del_tope_se_recorta_con_aviso():
    assert any("al menos 1" in m for m in motivos_de("mis últimas 0 facturas"))
    consulta, _, avisos = leer("mis últimas cien facturas")
    assert consulta["cantidad"] == mine_voice.CANTIDAD_MAXIMA
    assert any("máximo" in a for a in avisos)


def test_los_pagos_de_octubre_son_el_mes_completo_del_ano_actual():
    consulta = consulta_de("los pagos de octubre")
    assert consulta["tipo"] == "pagos"
    assert (consulta["desde"], consulta["hasta"]) == ("2026-10-01", "2026-10-31")


def test_un_mes_que_todavia_no_llego_es_del_ano_anterior():
    # Hoy es 16/11/2026: el diciembre más reciente es el de 2025.
    consulta = consulta_de("mis pagos de diciembre")
    assert (consulta["desde"], consulta["hasta"]) == ("2025-12-01", "2025-12-31")
    # Y el mes en curso es del año en curso.
    assert consulta_de("mis pagos de noviembre")["desde"] == "2026-11-01"


def test_el_mes_con_ano_explicito_manda_sobre_el_ano_por_omision():
    consulta = consulta_de("mis fichas de febrero de 2025")
    assert (consulta["desde"], consulta["hasta"]) == ("2025-02-01", "2025-02-28")
    assert consulta_de("pagos de febrero 2024")["hasta"] == "2024-02-29"


@pytest.mark.parametrize("frase, desde, hasta", [
    ("mis pagos de este mes", "2026-11-01", "2026-11-30"),
    ("mis pagos del mes pasado", "2026-10-01", "2026-10-31"),
    ("mis pagos de este año", "2026-01-01", "2026-12-31"),
    ("mis pagos del año pasado", "2025-01-01", "2025-12-31"),
    ("mis pagos de 2025", "2025-01-01", "2025-12-31"),
])
def test_este_mes_el_mes_pasado_y_los_anos(frase, desde, hasta):
    consulta = consulta_de(frase)
    assert (consulta["desde"], consulta["hasta"]) == (desde, hasta)


def test_el_mes_pasado_de_enero_es_diciembre_del_ano_anterior():
    consulta = consulta_de("mis pagos del mes pasado", hoy=dt.date(2026, 1, 10))
    assert (consulta["desde"], consulta["hasta"]) == ("2025-12-01", "2025-12-31")


@pytest.mark.parametrize("frase", [
    "mis pagos de agosto a octubre",
    "mis pagos desde agosto hasta octubre",
    "mis pagos entre agosto y octubre",
])
def test_un_rango_de_meses_se_entiende_de_tres_maneras(frase):
    consulta = consulta_de(frase)
    assert (consulta["desde"], consulta["hasta"]) == ("2026-08-01", "2026-10-31")


@pytest.mark.parametrize("frase", [
    "mis pagos de enero y marzo",
    "mis pagos de enero, marzo y mayo",
])
def test_dos_meses_sueltos_no_son_un_rango_y_se_dice(frase):
    assert any("más de un mes" in m for m in motivos_de(frase))


def test_un_rango_al_reves_no_se_entiende():
    assert motivos_de("mis pagos de octubre a agosto")


def test_la_especialidad_se_reconoce_sin_tildes_ni_mayusculas():
    consulta = consulta_de("mis fichas de CARDIOLOGIA")
    assert consulta["tipo"] == "fichas"
    assert consulta["especialidad"] == "id-cardio"
    assert consulta["especialidad_nombre"] == "Cardiología"


def test_gana_la_especialidad_de_nombre_mas_largo():
    consulta = consulta_de("mis fichas de medicina general")
    assert consulta["especialidad"] == "id-general"


def test_todo_junto_en_una_frase():
    consulta = consulta_de("mis últimas 2 facturas de cardiología en octubre")
    assert consulta == {
        "tipo": "pagos", "cantidad": 2, "desde": "2026-10-01",
        "hasta": "2026-10-31", "especialidad": "id-cardio",
        "especialidad_nombre": "Cardiología",
    }


def test_una_especialidad_que_el_centro_no_tiene_no_se_ignora():
    motivos = motivos_de("mis fichas de neurología")
    assert any("neurologia" in m for m in motivos)


def test_el_relleno_no_se_toma_por_una_especialidad():
    assert consulta_de("mis últimas facturas por favor")["tipo"] == "pagos"
    assert consulta_de("mis pagos de este mes, gracias")["tipo"] == "pagos"


def test_sin_tipo_o_con_los_dos_tipos_no_se_entiende():
    assert any("pagos o tus fichas" in m for m in motivos_de("mis últimas 2 cosas"))
    assert any("una cosa por vez" in m for m in motivos_de("mis pagos y mis fichas"))
    # «Comprobante» solo es ambiguo: no se adivina.
    assert motivos_de("mis comprobantes")


def test_ultimos_tres_dias_no_se_toma_como_cantidad():
    motivos = motivos_de("mis pagos de los últimos 3 días")
    assert any("días ni semanas" in m for m in motivos)


@pytest.mark.parametrize("frase, parte", [
    ("mis pagos devueltos", "tienen comprobante"),
    ("mis fichas canceladas", "tienen comprobante"),
    ("mis pagos pendientes", "tienen comprobante"),
    ("mis pagos de hoy", "días ni semanas"),
    ("mis pagos de la semana pasada", "días ni semanas"),
    ("mis fichas con el doctor Pérez", "profesional"),
    ("mis pagos mayores a 100 bs", "monto"),
    ("los pagos de mi hijo", "No se filtra por persona"),
    ("los pagos de todos los pacientes", "No se filtra por persona"),
])
def test_lo_que_hoy_no_se_puede_pedir_se_dice_y_no_se_ejecuta(frase, parte):
    assert any(parte in m for m in motivos_de(frase))


def test_nombrar_a_alguien_de_la_familia_se_avisa_y_no_filtra():
    motivos = motivos_de("los pagos de Lucía", nombres=("lucia", "carlos"))
    assert any("No se filtra por persona" in m for m in motivos)
    # Sin ese nombre en la familia, «Lucía» sería algo que no es una
    # especialidad: tampoco se ejecuta.
    assert motivos_de("los pagos de Lucía")


def test_texto_vacio_dice_que_no_se_escucho_nada():
    assert motivos_de("   ") == ["No escuché nada."]
    assert motivos_de("") == ["No escuché nada."]


def test_un_ano_imposible_no_se_entiende():
    assert any("año 1999" in m for m in motivos_de("mis pagos de 1999"))


def test_detectar_no_soportado_no_dice_nada_de_una_frase_valida():
    assert detectar_no_soportado("mis últimas 2 facturas de cardiología") == []


# ==========================================================================
#  Lo que devuelve el modelo se valida igual
# ==========================================================================
def sanear(crudo):
    return sanear_consulta(crudo, ESPECIALIDADES, HOY)


def test_el_modelo_con_una_respuesta_valida_pasa():
    consulta, unresolved, _ = sanear({
        "tipo": "pagos", "cantidad": 2, "desde": "2026-10-01",
        "hasta": "2026-10-31", "especialidad": "cardiologia",
    })
    assert unresolved == []
    assert consulta["especialidad"] == "id-cardio"
    assert consulta["cantidad"] == 2


def test_el_modelo_con_un_tipo_fuera_de_la_lista_no_ejecuta():
    consulta, unresolved, _ = sanear({"tipo": "recetas"})
    assert consulta is None and unresolved


@pytest.mark.parametrize("crudo", [
    {"tipo": "pagos", "especialidad": "Neurología"},
    {"tipo": "pagos", "desde": "ayer"},
    {"tipo": "pagos", "desde": "2026-10-31", "hasta": "2026-10-01"},
    {"tipo": "pagos", "desde": "1990-01-01"},
    {"tipo": "pagos", "cantidad": 0},
    {"tipo": "pagos", "cantidad": "muchas"},
    {"tipo": "pagos", "cantidad": True},
    {"tipo": "pagos", "no_entendido": ["pagos del doctor Pérez"]},
])
def test_el_modelo_con_algo_inventado_o_invalido_no_ejecuta(crudo):
    consulta, unresolved, _ = sanear(crudo)
    assert consulta is None and unresolved


def test_el_modelo_no_puede_agregar_claves_de_alcance():
    consulta, _, _ = sanear({
        "tipo": "pagos", "paciente": "otro", "patient_id": "x",
        "organization": "otra", "usuario": "admin",
    })
    assert consulta is not None
    assert set(consulta) == {*mine_voice.CLAVES, "especialidad_nombre"}


def test_el_modelo_con_una_cantidad_en_digitos_como_texto_se_acepta_y_se_recorta():
    consulta, _, avisos = sanear({"tipo": "fichas", "cantidad": "80"})
    assert consulta["cantidad"] == mine_voice.CANTIDAD_MAXIMA and avisos


def test_una_respuesta_que_no_es_un_objeto_no_se_entiende():
    consulta, unresolved, _ = sanear(["pagos"])
    assert consulta is None and unresolved


# ==========================================================================
#  El resumen para leer lo arma Python
# ==========================================================================
@pytest.mark.parametrize("frase, esperado", [
    ("mis últimas 2 facturas", "Pagos con comprobante · últimos 2"),
    ("mi última ficha", "Fichas con comprobante · el último"),
    ("los pagos de octubre", "Pagos con comprobante · octubre de 2026"),
    ("mis fichas de cardiología de este año",
     "Fichas con comprobante · Cardiología · año 2026"),
    ("mis pagos de agosto a octubre",
     "Pagos con comprobante · de agosto de 2026 a octubre de 2026"),
])
def test_el_resumen_dice_lo_que_se_va_a_mostrar_con_el_ano_resuelto(
    frase, esperado,
):
    assert mine_voice.resumen(consulta_de(frase)) == esperado
