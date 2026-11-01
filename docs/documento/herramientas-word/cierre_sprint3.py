"""Cierre del Sprint 3 en el Word: US-23 (PR #87) y US-30 (PR #89) integradas,
Daily de la semana 3, revisión y retrospectiva.

Uso: python cierre_sprint3.py ENTRADA.docx SALIDA.docx
Cada cambio se ubica por texto dentro del Sprint 3 y se detiene si no lo encuentra.
"""
import sys, html, re
sys.path.insert(0, r'D:\UNI\Si2\PROYECTO_MEDICOS\docs\documento\herramientas-word')
from comun import *

ent, sal = sys.argv[1], sys.argv[2]
x = abrir(ent)
E = elements(x)
A = buscar(x, E, 'Sprint 3', 'Titulo11')
B = buscar(x, E, 'Sprint 4', 'Titulo11')
S = lambda n: x[E[n][1]:E[n][2]]
T = lambda n: html.unescape(txt(S(n))).strip()

def donde(prefijo, tipo='p', desde=A, hasta=B):
    for n in range(desde, hasta):
        if E[n][0] == tipo and (T(n) if tipo == 'p' else html.unescape(txt(S(n)))).startswith(prefijo):
            return n
    sys.exit(f'PARADO: no encontré {prefijo!r} en el Sprint 3.')

def parrafo(n, texto):
    s = S(n)
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', s, re.S)
    return f'<w:p>{ppr.group(0) if ppr else BODY_PPR}{runs(texto)}</w:p>'

def fila_set(tbl, clave, col, valor):
    for tr in rows(tbl):
        cs = cells(tr)
        if html.unescape(txt(cs[0])).strip() == clave:
            vals = [None] * len(cs); vals[col] = valor
            return tbl.replace(tr, set_row(tr, vals), 1)
    sys.exit(f'PARADO: no encontré la fila {clave!r}.')

def tst(nombres):
    """Nombres de prueba con espacio de ancho cero tras cada _, como el resto del reporte."""
    return '; '.join(n.replace('_', '_\u200b') for n in nombres)

ops = {}
def put(n, xml):
    assert n not in ops, n
    ops[n] = xml

# ---------------------------------------------------------------- 1.2 tarjetas
n = donde('US-23 — Ficha asistida en mostrador'); nt = n + 1
d = parse_story(S(nt))
d['func'] = [
    'a) La reserva es book_appointment, la misma función de la pantalla del paciente, llamada por recepción a nombre del paciente desde POST /api/appointments/counter/book/. No se escribe otra forma de reservar (regla 12 del reparto) y se respeta el límite de fichas por mes del plan.',
    'b) Medio de pago nuevo «Efectivo en ventanilla» (Payment.Provider.CASH). El importe lo decide el servidor y la ficha se confirma por confirm_payment, el mismo camino que el webhook de Stripe: salen el comprobante y el correo de siempre.',
    'c) El cobro presencial no exige que el plan de la organización tenga pago en línea.',
    'd) Dos permisos propios, sembrados para Recepción y Administración: appointments.appointment.book_at_counter para reservar (migración 0006) y payments.payment.register_cash para cobrar. El paciente no tiene ninguno de los dos.',
    'e) Una ficha ya pagada no se cobra dos veces y una reserva vencida no se cobra; si dos cobros llegan a la vez, el segundo queda devuelto.',
    'f) Pantalla web /mostrador en cuatro pasos: buscar al paciente o darlo de alta sin salir de la pantalla (ABM de US-10), elegir profesional, fecha y turno de la disponibilidad consolidada, reservar y cobrar en efectivo, y registrar la llegada por documento sin pasar por el QR (check-in de US-22).',
    'g) El cobro está en main desde el 15/10 (PR #80, 11 pruebas) y el mostrador desde el 27/10 (PR #87). La reserva en mostrador no tiene pruebas automatizadas propias: el PR sólo ajusta el conteo de permisos de test_isolation.py.',
]
put(nt, story_table(S(nt), d))

n = donde('US-30 — Reportes operativos'); nt = n + 1
d = parse_story(S(nt))
d['func'] = [
    'a) Dos conjuntos de datos nuevos en reporting/datasets.py: Fichas (una fila por ficha) y Pagos (una fila por intento de cobro). No se tocó el constructor ni las pantallas: el catálogo se arma solo desde GET /api/reporting/datasets/.',
    'b) Los números coinciden con el panel de US-29: la columna Asistencia se calcula con debian_atenderse_q e inasistencia_q de appointments/kpis.py, en vez de reescribir la regla. Los ausentes, la demanda por sucursal y los ingresos dan lo mismo que /kpis.',
    'c) Los dos conjuntos exigen reporting.kpi.read, el permiso del panel, que sólo tiene la Administración. Recepción y los profesionales no los ven en el catálogo y reciben 403.',
    'd) El reporte entrega filas, no totales, y cada moneda se suma por separado. Los totales se sacan con la tabla dinámica o el autofiltro del Excel.',
    'e) Dos arreglos en el motor: query.py incluye la clave primaria para que DISTINCT no junte fichas iguales en un reporte de pocas columnas, y exporters.py manda el importe al Excel como número (#,##0.00) y ya no falla con fechas con zona horaria.',
    'f) Se exportan a csv, xlsx, html y pdf, y se piden por voz, con lo que ya hace la característica 5 en la web y en el móvil.',
    'g) 13 pruebas en tests/test_us30.py. Integrada el 26/10 (PR #89).',
]
put(nt, story_table(S(nt), d))

n = donde('US-28 — Notificaciones push y correo'); nt = n + 1
d = parse_story(S(nt))
assert not any(f.startswith('h)') for f in d['func'])
d['func'] = d['func'] + ['h) Desde Android 13 el aviso necesita el permiso POST_NOTIFICATIONS; se declaró en el AndroidManifest el 26/10 (PR #89).']
put(nt, story_table(S(nt), d))

# ---------------------------------------------------------------- 1.4 backlog
nb = donde('IDTarea', 'tbl')
tb = fila_set(S(nb), 'T-37', 5, 'Completado')
tb = fila_set(tb, 'T-42', 5, 'Completado')
put(nb, tb)
ne = donde('Estado al 26/10/26.')
put(ne, parrafo(ne, '**Estado al 01/11/26.** Las siete historias están en la rama principal: US-33 (backend y web '
    'el 13/10, PR #77 y #78; móvil el 26/10, PR #84), US-28 (15/10, PR #81), US-29 (18/10, PR #82), US-26 y US-27 '
    '(25/10, PR #83), US-30 (26/10, PR #89) y US-23 (el cobro el 15/10, PR #80, y el mostrador el 27/10, PR #87). '
    'Las dependencias del reparto se cumplieron: el pago presencial llegó el 15/10 (el plazo era el 17/10) y la '
    'definición de los indicadores el 18/10 (el plazo era el 20/10). US-26 llegó el 25/10, tres días después de la '
    'fecha del reparto, y US-23 y US-30 se subieron el 26/10, el último día de desarrollo.'))

# ---------------------------------------------------------------- 2.2.1 componentes
ni = donde('Durante el Sprint 3 se incorporaron a la rama principal')
t = T(ni)
for viejo, nuevo in [('el cobro en efectivo en ventanilla', 'el mostrador con el cobro en efectivo, los reportes de fichas y de pagos'),
                     ('al 26/10/26', 'al 01/11/26')]:
    assert viejo in t, viejo
    t = t.replace(viejo, nuevo)
put(ni, parrafo(ni, t))
nc = donde('HistoriaComponentes', 'tbl')
tc = S(nc)
tc = fila_set(tc, 'US-23 — Ficha asistida en mostrador (cobro)', 0, 'US-23 — Ficha asistida en mostrador')
tc = fila_set(tc, 'US-23 — Ficha asistida en mostrador', 1,
    'payments/models.py (Provider.CASH), providers.py (CashProvider), services.py (register_cash_payment), views.py, '
    'urls.py, permissions.py, migraciones 0004 y 0005; appointments/counter.py, urls.py, migración 0006; '
    'frontend/src/paginas/Mostrador.tsx, api/mostrador.ts y componentes/BarraPlataforma.tsx; '
    'docs/sprints/sprint-3/pago-presencial-mostrador.md')
tc = fila_set(tc, 'US-23 — Ficha asistida en mostrador', 2,
    'POST /api/appointments/counter/book/ con el permiso appointments.appointment.book_at_counter y '
    'POST /api/payments/appointments/{id}/cash/ con payments.payment.register_cash. La pantalla /mostrador '
    'reserva, cobra y registra la llegada.')
tc = fila_set(tc, 'US-30 — Reportes operativos', 1,
    'reporting/datasets.py (conjuntos appointments y payments), query.py, exporters.py; tests/test_us30.py; '
    'docs/sprints/sprint-3/us-30-reportes-operativos.md')
tc = fila_set(tc, 'US-30 — Reportes operativos', 2,
    'Los conjuntos Fichas y Pagos aparecen en GET /api/reporting/datasets/ sólo con reporting.kpi.read; el '
    'constructor de la característica 5 los consulta y exporta.')
put(nc, tc)

# ---------------------------------------------------------------- 2.3.1 plan
np_ = donde('El plan define entradas, acciones y salidas esperadas')
t = T(np_)
viejo = 'Cubre las historias del Sprint 3 que ya tienen código; US-30 redacta su plan antes de implementarse.'
assert viejo in t
put(np_, parrafo(np_, t.replace(viejo, 'Cubre las siete historias del Sprint 3.')))

ncov = donde('Caso de usoHistoriaEscenarios', 'tbl')
pre, rs, post = split_tbl(S(ncov))
nueva = set_row(rs[5], ['CU31 · Generación de Reportes', 'US-30', '7'])
put(ncov, strip_ids(pre + ''.join(rs[:6]) + nueva + ''.join(rs[6:]) + post))

# CP-23-08: la reserva en mostrador ya existe
n24 = donde('IDAcción / escenarioResultado esperadoCP-23-01', 'tbl')
put(n24, fila_set(S(n24), 'CP-23-08', 2,
    'La ficha se crea con book_appointment, a nombre del paciente; sin el permiso book_at_counter se responde 403.'))

# bloque CU31 clonado del de CU30, se inserta antes de CU34
h30 = donde('CU30 — Consulta de Indicadores y KPIs')
h34 = donde('CU34 — Agendamiento mediante Chatbot', desde=h30)
assert E[h30 + 1][0] == 'tbl' and E[h30 + 4][0] == 'tbl'
campos = S(h30 + 1)
for clave, val in [('Caso de uso', 'CU31 — Generación de Reportes'), ('Historia de usuario', 'US-30 · Web'),
                   ('Descripción', 'El administrador pide al constructor de reportes los conjuntos Fichas y Pagos, '
                                   'los filtra y los exporta, con los mismos números que el panel de indicadores.'),
                   ('Precondiciones', 'Organización con fichas en varios estados y pagos en línea y en efectivo, '
                                      'una cuenta de Administración, una de Recepción, una de Paciente y una segunda '
                                      'organización para probar el aislamiento.'),
                   ('Responsable', 'Alexander Osinaga Blanco')]:
    campos = fila_set(campos, clave, 1, val)
esc_30 = [
    ['CP-30-01', 'Ver el catálogo de reportes como Administración, Recepción y Paciente.', 'Fichas y Pagos aparecen sólo para la Administración; los demás reciben 403 si los piden.'],
    ['CP-30-02', 'Pedir las fichas ausentes de un período.', 'Son las mismas que cuenta el panel (no_show.missed), incluida la confirmada vencida sin check-in.'],
    ['CP-30-03', 'Contar las fichas por sucursal en un rango de fechas.', 'Coincide con la demanda por sucursal del panel; lo que cae fuera del rango no sale.'],
    ['CP-30-04', 'Pedir un reporte de fichas con pocas columnas.', 'Sale una fila por ficha, aunque dos fichas tengan los mismos valores.'],
    ['CP-30-05', 'Sumar los ingresos por sucursal en el conjunto Pagos.', 'Coincide con los ingresos del panel, por moneda; el efectivo sale como «Efectivo en ventanilla».'],
    ['CP-30-06', 'Exportar Fichas y Pagos a PDF y a Excel.', 'Los archivos se generan y el importe llega al Excel como número que se puede sumar.'],
    ['CP-30-07', 'Pedir el reporte desde dos organizaciones.', 'Cada administración ve sólo los datos de su organización.'],
]
bloque = (parrafo(h30, 'CU31 — Generación de Reportes') + campos + S(h30 + 2) + S(h30 + 3)
          + table(S(h30 + 4), [(0, None)], esc_30, 1) + S(h30 + 5))
put(h34, strip_ids(bloque) + S(h34))

# ---------------------------------------------------------------- 2.3.2 reporte
nres = donde('CUHistoriaResponsableSituación del reporte', 'tbl')
tr_ = S(nres)
for clave, val in [('CU24', 'Integrada (PR #80 y #87). El cobro tiene 11 pruebas automatizadas; la reserva en mostrador no tiene prueba automatizada propia.'),
                   ('CU31', 'Integrada (PR #89). 13 pruebas en test_us30.py; evidencia de interfaz por completar.')]:
    tr_ = fila_set(tr_, clave, 3, val)
put(nres, tr_)

r24 = donde('IDEscenarioPrueba identificadaEstadoCP-23-01', 'tbl')
put(r24, fila_set(S(r24), 'CP-23-08', 3, 'Pendiente: sin prueba automatizada.'))

p30 = donde('Prueba de caso de uso CU30: Consulta de Indicadores y KPIs')
p34 = donde('Prueba de caso de uso CU34', desde=p30)
assert E[p30 + 3][0] == 'tbl'
OK = 'Cubierto por prueba automatizada.'
rep_30 = [
    ['CP-30-01', esc_30[0][1], tst(['test_la_administracion_ve_fichas_y_pagos_en_el_catalogo', 'test_recepcion_con_reportes_no_ve_fichas_ni_pagos', 'test_un_paciente_no_se_lleva_las_fichas_del_centro']), OK],
    ['CP-30-02', esc_30[1][1], tst(['test_las_ausentes_del_reporte_son_las_del_panel']), OK],
    ['CP-30-03', esc_30[2][1], tst(['test_las_fichas_del_reporte_cuadran_con_la_demanda_del_panel', 'test_el_rango_de_fechas_deja_afuera_lo_que_no_cae_en_el']), OK],
    ['CP-30-04', esc_30[3][1], tst(['test_con_pocas_columnas_sale_una_fila_por_ficha', 'test_el_reporte_de_fichas_se_puede_filtrar_por_sucursal_y_ordenar']), OK],
    ['CP-30-05', esc_30[4][1], tst(['test_los_ingresos_del_reporte_son_los_del_panel', 'test_el_pago_en_ventanilla_sale_con_su_nombre']), OK],
    ['CP-30-06', esc_30[5][1], tst(['test_fichas_y_pagos_se_exportan_a_pdf_y_a_excel', 'test_el_importe_llega_al_excel_como_numero_que_se_puede_sumar']), OK],
    ['CP-30-07', esc_30[6][1], tst(['test_el_reporte_solo_trae_los_datos_de_la_organizacion']), OK],
]
bloque = (parrafo(p30, 'Prueba de caso de uso CU31: Generación de Reportes')
          + parrafo(p30 + 1, 'Caso de uso / historia: CU31 · US-30 · Web')
          + parrafo(p30 + 2, 'Responsable: Alexander Osinaga Blanco')
          + table(S(p30 + 3), [(0, None)], rep_30, 1) + S(p30 + 4))
put(p34, strip_ids(bloque) + S(p34))

# ---------------------------------------------------------------- 3. Daily semana 3
DAILY = {  # persona: [(ayer, hoy, obstáculo) por día, del 27 al 31/10]
    'ALEXANDER OSINAGA BLANCO': [
        ('Presenté como Product Owner el avance a la ingeniera y subí US-30 con los conjuntos Fichas y Pagos (PR #89).', 'Revisar como Product Owner la pantalla de mostrador de Daniel (PR #87).', 'Ninguno'),
        ('Revisé como Product Owner el mostrador de Daniel (PR #87).', 'Probar en el despliegue los reportes de Fichas y Pagos exportados a Excel y PDF.', 'Ninguno'),
        ('Probé en el despliegue los reportes de Fichas y Pagos en Excel y PDF.', 'Comparar los ingresos del reporte de pagos con el panel, incluido el cobro en ventanilla.', 'El reporte entrega filas y no totales; los totales se sacan con la tabla dinámica del Excel.'),
        ('Comparé los ingresos del reporte de pagos con el panel, incluido el efectivo en ventanilla.', 'Preparar como Product Owner la retroalimentación de cada historia para la revisión.', 'Ninguno'),
        ('Preparé la retroalimentación de cada historia para la revisión.', 'Ensayar con el equipo la demostración del Sprint 3.', 'Ninguno'),
    ],
    'LUIS MATEO HURTADO CASTRO': [
        ('Armé el capítulo del Sprint 3 en el documento y presenté el avance a la ingeniera.', 'Revisar y mergear US-23 (PR #87) y los diagramas de Karen (PR #88).', 'Ninguno'),
        ('Mergeé US-23 (PR #87) y los diagramas de secuencia, navegación, estado y tiempo (PR #88).', 'Actualizar el documento con lo integrado y los diagramas del Sprint 3.', 'Ninguno'),
        ('Actualicé el documento con lo integrado y los diagramas del Sprint 3.', 'Probar en el celular la reserva conversacional de US-33 contra el despliegue.', 'Ninguno'),
        ('Probé en el celular la reserva conversacional contra el despliegue y cancelé las fichas de prueba.', 'Completar en Enterprise Architect el modelo de dominio del Sprint 3: recetas, órdenes y tokens.', 'Ninguno'),
        ('Completé el modelo de dominio con recetas, órdenes y tokens de dispositivo.', 'Subir el .eapx y cerrar el Sprint 3 en el documento: Daily, revisión y retrospectiva.', 'El .eapx es binario: si dos lo editan a la vez se pierde un trabajo, así que se sube antes de que Karen siga.'),
    ],
    'JOSÉ DANIEL IPORO CHULQUE': [
        ('Integré main en mi rama y subí US-23 a revisión (PR #87).', 'Corregir lo que salga de la revisión del mostrador.', 'Ninguno'),
        ('US-23 quedó integrada en main (PR #87).', 'Probar el mostrador de punta a punta: reservar, cobrar en efectivo y registrar la llegada.', 'Ninguno'),
        ('Probé el mostrador de punta a punta: reservar, cobrar y registrar la llegada sin QR.', 'Probar el alta de un paciente nuevo sin salir del mostrador.', 'Ninguno'),
        ('Probé el alta de un paciente nuevo desde el mostrador.', 'Pasarle a Karen el flujo del mostrador para el diagrama de CU24.', 'La reserva en mostrador no tiene pruebas automatizadas propias; queda anotado.'),
        ('Le pasé a Karen el flujo del mostrador para rehacer CU24.', 'Preparar la demostración del mostrador para la revisión.', 'Ninguno'),
    ],
    'KAREN PAOLA ORTEGA MANCILLA': [
        ('Presenté el avance a la ingeniera y subí secuencia, navegación, estado y tiempo del Sprint 3 (PR #88).', 'Revisar el código de US-23 para rehacer los diagramas de CU24.', 'Ninguno'),
        ('Revisé el código del mostrador: counter.py y Mostrador.tsx.', 'Rehacer la secuencia de CU24 con la reserva y el cobro del mostrador.', 'Ninguno'),
        ('Rehice la secuencia de CU24 con la reserva y el cobro del mostrador.', 'Dibujar CU31 a partir de los conjuntos Fichas y Pagos de US-30.', 'Ninguno'),
        ('Dibujé los diagramas de CU31, reportes operativos.', 'Completar los métodos de frontera y control en el diseño de clase.', 'Ninguno'),
        ('Completé los métodos de frontera y control en el diseño de clase.', 'Subir los diagramas: CU24 rehecho y CU31 nuevo.', 'Hay que esperar el .eapx de Mateo con el modelo de dominio para no pisar su trabajo.'),
    ],
    'LUIS MIGUEL AGUAYO QUIROZ': [
        ('Presenté el panel de KPIs a la ingeniera y cuadré con Alexander los totales de US-30 (PR #89).', 'Definir de qué variables depende la inasistencia en seed_dataset para el Sprint 4.', 'Ninguno'),
        ('Definí las variables de la inasistencia: anticipación, pago por adelantado, faltas previas, día y hora.', 'Comprobar en el despliegue que los reportes de US-30 den los mismos números que /kpis.', 'Ninguno'),
        ('Comprobé que los reportes de US-30 y /kpis den los mismos números.', 'Revisar que el efectivo del mostrador sume en los ingresos del panel.', 'Ninguno'),
        ('Revisé que el efectivo del mostrador sume en los ingresos del panel.', 'Preparar la demostración del panel de KPIs para la revisión.', 'Ninguno'),
        ('Preparé la demostración del panel de KPIs.', 'Ensayar con el equipo la demostración del Sprint 3.', 'Ninguno'),
    ],
}
nd = donde('Daily ScrumSemana 327 octubre', 'tbl')
td = S(nd)
rs = rows(td)
for i, tr in enumerate(rs):
    cs = cells(tr)
    nombre = html.unescape(txt(cs[0])).strip()
    if nombre in DAILY:
        dias = DAILY.pop(nombre)
        for k in range(3):
            fila = rs[i + k]
            vals = [None, None] + [dia[k] for dia in dias] + [None] * (len(cells(fila)) - 7)
            td = td.replace(fila, set_row(fila, vals), 1)
assert not DAILY, DAILY
put(nd, td)

# ---------------------------------------------------------------- 4. Review
REVIEW = {
    'US-23': 'El mostrador reserva con la misma función que el paciente y cobra en efectivo por el mismo camino que el pago en línea, con el comprobante y el correo. Faltan pruebas automatizadas de la reserva en mostrador y pasar los textos de la pantalla a tuteo.',
    'US-26': 'La receta respeta la regla de la firma también en la base y la alergia queda a la vista mientras se receta. El PDF no lleva el diagnóstico, como corresponde.',
    'US-27': 'El paciente ve recetas, órdenes e indicaciones con el mismo alcance del historial y baja el PDF en la web y en el móvil.',
    'US-28': 'Probada en un teléfono real; el recordatorio no se repite y un FCM caído no deja la ficha sin confirmar. Desde Android 13 se pide el permiso de notificaciones.',
    'US-29': 'Los indicadores se calculan en la base y coinciden con el panel de inicio. Conviene explicar en la pantalla cómo se cuenta la inasistencia.',
    'US-30': 'Fichas y Pagos dan los mismos números que el panel y el importe se suma en el Excel. Los totales dentro del archivo quedan para una historia aparte.',
    'US-33': 'Nada se reserva sin confirmación y la barrera de urgencias sigue corriendo primero. Unificar el formato de la hora del asistente con el resto de la aplicación.',
}
nr = donde('REVISION DE SPRINT 3', 'tbl')
trv = S(nr)
for tr in rows(trv):
    cs = cells(tr)
    k = html.unescape(txt(cs[0])).strip()[:5]
    if len(cs) == 2 and k in REVIEW:
        trv = trv.replace(tr, set_row(tr, [None, REVIEW.pop(k)]), 1)
assert not REVIEW, REVIEW
put(nr, trv)
npend = donde('Pendiente. La retroalimentación de cada función')
put(npend, parrafo(npend, 'Revisión del 01/11/26. Las siete historias del Sprint 3 están integradas en la rama principal; '
                          'los pendientes que salieron de la revisión pasan al Sprint 4.'))

# ---------------------------------------------------------------- 5. Retro
RETRO = [
    ['Las dos dependencias de la ruta crítica llegaron antes del plazo: el pago presencial el 15/10 y la definición de los indicadores el 18/10.',
     'US-23 y US-30 se subieron el 26/10, el último día de desarrollo, y sus diagramas y capturas se hicieron después.',
     'Fijar un corte intermedio para cada historia, no sólo para las dependencias, y revisar el avance a mitad del sprint.'],
    ['Las siete historias quedaron en la rama principal, y US-30 dio los mismos números que el panel porque reutilizó la definición de kpis.py.',
     'El mostrador entró sin pruebas automatizadas propias de la reserva y con textos en voseo, fuera de la guía de diseño.',
     'No mergear una historia sin pruebas de su endpoint nuevo ni sin pasar sus textos por la guía de diseño.'],
    ['Las capturas de US-26, US-27, US-29 y US-33 se tomaron al cerrar cada historia, como se acordó en la retrospectiva del Sprint 2.',
     'El modelo de Enterprise Architect se editó en dos máquinas y el modelo de dominio del Sprint 3 quedó sólo en local hasta el 01/11.',
     'Subir el .eapx en cuanto se edita y avisar al equipo antes de abrirlo.'],
]
nrt = donde('RETROSPECTIVA DEL SPRINT 3', 'tbl')
trt = S(nrt)
trt = fila_set(trt, 'FECHA', 1, '01/11/26')
pend = [tr for tr in rows(trt) if html.unescape(txt(cells(tr)[0])).startswith('Pendiente: se completa')]
assert len(pend) == 3, len(pend)
for tr, vals in zip(pend, RETRO):
    trt = trt.replace(tr, set_row(tr, vals), 1)
put(nrt, trt)

out = aplicar(x, E, ops)
guardar(ent, out, sal)
print('OK', len(ops), 'cambios')
