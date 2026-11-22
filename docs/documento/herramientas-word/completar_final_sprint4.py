"""Completa la copia alineada al índice de la ingeniera con lo que pidió en la clase del 17/11/26
(transcripción del 21/11/26) y con el estado real del Sprint 4 al 22/11/26.

Uso:  python completar_final_sprint4.py ENTRADA.docx SALIDA.docx

1. 5.1: columna «Casos de Uso» después de «Historia de Usuario» (la ingeniera pidió las HU *y* los
   CU en los que participó cada miembro).
2. QR: suma la API y la aplicación móvil (release) a GitHub y la web. Las imágenes QR se generan
   aparte (`qr_final.py`) y se pegan a mano: este script no agrega imágenes (regla 5).
3. Bibliografía: sección «Herramientas de inteligencia artificial utilizadas» (pidió citar los
   agentes y modelos de IA).
4. Sprint 4: estados del Sprint Backlog al 22/11, la Sprint Review y la Retrospective propias (tenían
   copiado el contenido del Sprint 0), y las filas del Sprint 4 en 5.2 y 5.3.

Todo se ubica por texto (regla 6) y se detiene si un ancla no aparece.
"""
import sys, re, html
from comun import (abrir, guardar, elements, txt, rows, cells, set_row, esc, strip_ids,
                   buscar, aplicar, get_grid, set_widths, scale, PARA_RE)

ENT, SAL = sys.argv[1], sys.argv[2]
x = abrir(ENT)


def T(i):
    return html.unescape(txt(x[E[i][1]:E[i][2]])).strip()


def clonar_parrafo(par, texto):
    """El mismo párrafo (pPr y formato del primer run) con otro texto."""
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', par, re.S)
    ppr = ppr.group(0) if ppr else ''
    rpr = re.search(r'<w:r(?:\s[^>]*)?>\s*(<w:rPr>.*?</w:rPr>)', par, re.S)
    rpr = rpr.group(1) if rpr else ''
    return f'<w:p>{ppr}<w:r>{rpr}<w:t xml:space="preserve">{esc(texto)}</w:t></w:r></w:p>'


def tabla_desde(i):
    j = i + 1
    while E[j][0] != 'tbl':
        j += 1
    return j


# --- US → CU (paquete 3.10; CU = US + 1 salvo el arranque: login, registro y recuperación) ----
CU = {1: 'CU2', 2: 'CU1, CU4', 3: 'CU3'}
for n in range(4, 54):
    CU.setdefault(n, f'CU{n + 1}')


def cus_de(historias):
    nums = [int(m) for m in re.findall(r'US-(\d+)', historias)]
    return ', '.join(CU[n] for n in nums) if nums else '—'


ops = {}
E = elements(x)

# ---------- 1. 5.1: columna de casos de uso ----------------------------------------------------
i51 = tabla_desde(buscar(x, E, '5.1 Calificación miembros de equipo SCRUM'))
tbl = x[E[i51][1]:E[i51][2]]
assert [html.unescape(txt(c)) for c in cells(rows(tbl)[0])][4] == 'Historia de Usuario', 'PARADO: 5.1'
nuevo = tbl
for k, tr in enumerate(rows(tbl)):
    cs = cells(tr)
    hu = cs[4]
    texto = 'Casos de Uso' if k == 0 else cus_de(html.unescape(txt(hu)))
    copia = set_row(f'<w:tr>{hu}</w:tr>', [texto])[len('<w:tr>'):-len('</w:tr>')]
    nuevo = nuevo.replace(tr, tr.replace(hu, hu + copia, 1), 1)
# Sprint # | Miembro | Rol | Nota | Historia de Usuario | Casos de Uso | Tiempo (suma 8828, el ancho
# de la tabla original): «Sprint 1» y «Developer» no se parten.
nuevo = set_widths(nuevo, [1000, 2050, 1250, 650, 1828, 1250, 800])
ops[i51] = strip_ids(nuevo)
p51 = buscar(x, E, 'Pendiente: las notas se completan con las de cada revisión.')
ops[p51] = clonar_parrafo(x[E[p51][1]:E[p51][2]],
    'Pendiente: las notas se completan con las de cada revisión. Los casos de uso salen del paquete '
    '3.10: cada historia corresponde a su caso de uso.')

# ---------- 2. QR: API y aplicación móvil ------------------------------------------------------
iweb = buscar(x, E, 'https://platwebmovilmedicos-production-ae19.up.railway.app')
rot = x[E[iweb - 1][1]:E[iweb - 1][2]]      # «WEB»
url = x[E[iweb][1]:E[iweb][2]]
vacio = '<w:p/>'
qr = ''.join([
    vacio, clonar_parrafo(rot, 'API (BACKEND)'),
    clonar_parrafo(url, 'https://web-production-872fa.up.railway.app/api/health/'),
    vacio, clonar_parrafo(rot, 'APLICACIÓN MÓVIL (APK)'),
    clonar_parrafo(url, 'https://github.com/MatiusProg/plat_web_movil_medicos/releases/latest'),
])
ops[iweb] = url + qr

# ---------- 3. Bibliografía: herramientas de IA ------------------------------------------------
ib = buscar(x, E, 'BIBLIOGRAFIA', 'CAPITULO')
ia = buscar(x, E, 'ANEXOS', 'CAPITULO', desde=ib)
ult = ia - 1
while E[ult][0] != 'p' or not T(ult):
    ult -= 1
ref = x[E[ult][1]:E[ult][2]]
tit = x[E[buscar(x, E, 'Casos de estudio y sitios consultados', desde=ib)][1]:
        E[buscar(x, E, 'Casos de estudio y sitios consultados', desde=ib)][2]]
REFS_IA = [
    'Anthropic. (2026). Claude Code con Claude Opus [Asistente de programación con inteligencia '
    'artificial]. https://claude.com/claude-code. Usado en el desarrollo del backend, la web y el '
    'móvil, en las pruebas, en la generación de los diagramas de Enterprise Architect y en la '
    'documentación.',
    'OpenAI. (2026). ChatGPT [Modelo de lenguaje]. https://chatgpt.com. Usado para redactar y revisar '
    'textos del documento y para generar imágenes de apoyo.',
    'Google. (2026). Gemini API: gemini-3.5-flash-lite y gemini-embedding-001 [Modelos de lenguaje y '
    'de embeddings]. https://ai.google.dev. Integrados en el producto: asistente de orientación y '
    'reserva, resúmenes de la consulta y del historial, e indicaciones de preparación.',
    'Radford, A., Kim, J. W., Xu, T., Brockman, G., McLeavey, C., & Sutskever, I. (2022). Robust speech '
    'recognition via large-scale weak supervision (Whisper). OpenAI. https://github.com/openai/whisper. '
    'Usado, mediante faster-whisper, para transcribir la clase del 17/11/26 sobre el cierre.',
    'Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning '
    'Research, 12, 2825–2830. Usado en el modelo de predicción de inasistencia y la proyección de demanda.',
]
ops[ult] = (ref + clonar_parrafo(tit, 'Herramientas de inteligencia artificial utilizadas')
            + clonar_parrafo(ref, 'Se citan los agentes y modelos de IA que usó el equipo y para qué.')
            + ''.join(clonar_parrafo(ref, r) for r in REFS_IA))

# ---------- 4. Sprint 4 ------------------------------------------------------------------------
s4 = buscar(x, E, 'Sprint 4', 'Titulo11')

# 4a. Sprint Backlog: estados al 22/11/26
ibk = buscar(x, E, '1.4 Sprint Backlog', desde=s4)
ib1 = tabla_desde(ibk)
ib2 = tabla_desde(ib1)
tbl = x[E[ib2][1]:E[ib2][2]]
assert 'T-45' in txt(tbl), 'PARADO: Sprint Backlog del Sprint 4'
nuevo = tbl
for tr in rows(tbl):
    cs = [html.unescape(txt(c)) for c in cells(tr)]
    if re.match(r'T-\d+', cs[0]) and cs[5] != 'Completado' and cs[0] != 'T-55':
        nuevo = nuevo.replace(tr, set_row(tr, [None] * 5 + ['Completado']), 1)
ops[ib2] = strip_ids(nuevo)
ins = buscar(x, E, 'Estado al 17/11/26.', desde=s4, exacto=False)
ops[ins] = clonar_parrafo(x[E[ins][1]:E[ins][2]],
    'Estado al 22/11/26: las dieciséis historias del Sprint 4 están en la rama principal y desplegadas '
    '(US-48 a US-53 en los PR #112 a #129), con la aplicación móvil final publicada como versión 1.6.1. '
    'T-55, la verificación final de las IA en producción, queda para antes de la revisión.')

# 4b. Sprint Review del Sprint 4 (tenía la del Sprint 0)
ir = buscar(x, E, '4. Sprint Review', desde=s4)
irt = tabla_desde(ir)
tbl = x[E[irt][1]:E[irt][2]]
assert 'REVISION DE SPRINT 0' in txt(tbl), 'PARADO: Sprint Review del Sprint 4'
INC = [
    ('US-35', 'Riesgo de inasistencia por ficha', 'Modelo entrenado con datos sintéticos de seis meses; el riesgo se ve en su pantalla. Falta programar el reentrenamiento en producción.'),
    ('US-36', 'Recordatorios reforzados', 'El paciente de riesgo alto recibe un segundo aviso horas antes, una sola vez.'),
    ('US-37', 'Proyección de demanda', 'Proyección por especialidad y franja horaria en su propia pantalla.'),
    ('US-38', 'Reentrenamiento del modelo', 'El modelo nuevo sólo reemplaza al vigente si lo mejora.'),
    ('US-39', 'Resumen claro de la consulta', 'El paciente lo ve sólo después de que el médico lo aprueba.'),
    ('US-40', 'Preparación para estudios', 'Indicaciones revisadas por el médico; el paciente las ve en el móvil.'),
    ('US-41', 'Resumen del historial para el médico', 'Aparece al abrir la atención, antes de escribir.'),
    ('US-42', 'Validar o editar texto de IA', 'Nada escrito por la IA llega al paciente sin la aprobación del médico.'),
    ('US-46', 'Transacciones por voz del paciente', 'Comprobantes pedidos por voz o escritos, con su QR, agrupados por mes, sucursal o médico.'),
    ('US-47', 'Chat con el médico tratante', 'El aviso del chat llega al celular y abre la conversación.'),
    ('US-48', 'Calificación de la atención', 'De una a cinco estrellas con comentario, con estadísticas por médico y sucursal.'),
    ('US-49', 'Recordatorio de medicamentos', 'Avisos de cada toma; desde la notificación se marca tomada o se pospone.'),
    ('US-50', 'Finanzas por voz y contabilidad', 'Ganancia bruta y neta después de gastos y comisiones, también por voz.'),
    ('US-51', 'Plus en la compra de la ficha', 'Calendario, cómo llegar, cómo prepararse, cuenta regresiva y preconsulta que ve el médico.'),
    ('US-52', 'Lista de espera', 'El cupo liberado se ofrece al siguiente de la fila, con un plazo para pagar.'),
    ('US-53', 'Signos vitales con gráficas', 'Lo imposible se rechaza también en la base; gráficas de evolución para médico y paciente.'),
]
rs = rows(tbl)
idx_inc = [k for k, tr in enumerate(rs) if re.match(r'US-\d+', html.unescape(txt(cells(tr)[0])).strip())]
assert idx_inc, 'PARADO: filas del incremento'
nuevo_rs = []
for k, tr in enumerate(rs):
    t = html.unescape(txt(tr))
    if k in idx_inc:
        if k == idx_inc[0]:
            for us, nombre, obs in INC:
                nuevo_rs.append(set_row(tr, [f'{us} | {nombre}', obs]))
        continue
    if 'REVISION DE SPRINT 0' in t:
        tr = set_row(tr, ['REVISION DE SPRINT 4'])
    elif t.startswith('OBJETIVOS DEL SPRINT'):
        tr = set_row(tr, ['OBJETIVOS DEL SPRINT\nCerrar las épicas de IA que faltaban —predicción de inasistencia y de demanda, '
                          'y textos clínicos validados por el médico—, sumar los reportes por voz y el chat con el médico, '
                          'y las seis historias de la ampliación del 17/11: calificación, medicamentos, finanzas, el plus de '
                          'la ficha, la lista de espera y los signos vitales.'])
    nuevo_rs.append(tr)
pre = tbl[:tbl.find(rs[0])]
post = tbl[tbl.rfind(rs[-1]) + len(rs[-1]):]
ops[irt] = strip_ids(pre + ''.join(nuevo_rs) + post)

# 4c. Retrospective del Sprint 4
iro = buscar(x, E, '5. Sprint Retrospective', desde=s4)
irot = tabla_desde(iro)
tbl = x[E[irot][1]:E[irot][2]]
assert 'RETROSPECTIVA DEL SPRINT 0' in txt(tbl), 'PARADO: Retrospectiva del Sprint 4'
BIEN = ['Las dieciséis historias quedaron en producción y se probaron en un celular contra producción.',
        'Las pruebas de bordes y por mutación encontraron defectos antes de la entrega.',
        'Los diagramas del Sprint 4 se generaron desde el código y coinciden con lo implementado.',
        'Cada historia cerró con capturas y con su caso en el plan de pruebas.']
MAL = ['La ampliación del 17/11 sumó 48 horas con una semana de margen.',
       'Una historia se entregó distinta a su texto y hubo que completarla al cierre.',
       'Las tareas programadas de producción, como el reentrenamiento, quedaron sin configurar.',
       'La documentación se concentró en los últimos días.']
DIF = ['Revisar cada historia contra su texto antes de integrarla.',
       'Incluir las tareas de fondo de producción en la definición de terminado.',
       'Repartir la documentación desde el Planning, no al cierre.',
       'Probar en el celular cada historia móvil apenas se integra.']
rs = rows(tbl)
cont = [k for k, tr in enumerate(rs) if len(cells(tr)) == 3 and 'QUE SALIO BIEN' not in txt(tr)]
assert cont, 'PARADO: filas de la discusión'
nuevo_rs = []
for k, tr in enumerate(rs):
    t = html.unescape(txt(tr))
    if k in cont:
        if k == cont[0]:
            for a, b, c in zip(BIEN, MAL, DIF):
                nuevo_rs.append(set_row(tr, [a, b, c]))
        continue
    if 'RETROSPECTIVA DEL SPRINT 0' in t:
        tr = set_row(tr, ['RETROSPECTIVA DEL SPRINT 4'])
    elif t.startswith('FECHA'):
        tr = set_row(tr, [None, '23/11/26'])
    elif t.startswith('OBJETIVO'):
        tr = set_row(tr, ['OBJETIVO: Revisar cómo se cerró el último sprint, con la ampliación del 17/11, y dejar las '
                          'recomendaciones del proyecto.'])
    elif t.startswith('TEMAS A TRATAR'):
        tr = set_row(tr, ['TEMAS A TRATAR\nCierre de la ampliación del 17/11\nVerificación en producción\nDocumentación final'])
    nuevo_rs.append(tr)
pre = tbl[:tbl.find(rs[0])]
post = tbl[tbl.rfind(rs[-1]) + len(rs[-1]):]
ops[irot] = strip_ids(pre + ''.join(nuevo_rs) + post)

# 4d. 5.2 y 5.3: filas del Sprint 4
OBS4 = {
    'Ortega Mancilla, K.P.': 'Los textos de la IA llegan al paciente sólo aprobados. La calificación y los recordatorios de medicamentos se probaron en el celular contra producción.',
    'Hurtado Castro, L.M.': 'El chat abre la conversación desde la notificación. Los signos vitales se validan también en la base y tienen gráficas de evolución. Diagrama de redes y documentación del cierre.',
    'Aguayo Quiroz, L.M.': 'El riesgo de inasistencia usa un modelo entrenado con datos sintéticos de seis meses. La lista de espera ofrece el cupo al siguiente. Falta programar el reentrenamiento en producción.',
    'Osinaga Blanco, A.': 'Los comprobantes y las finanzas se consultan por voz, con la ganancia neta después de los gastos. El recordatorio reforzado no se repite.',
    'Iporo Chulque, J.D.': 'Proyección de demanda y reentrenamiento con comparación de modelos. El plus de la ficha se completó al cierre con el calendario, cómo llegar y la cuenta regresiva.',
}
i52 = tabla_desde(buscar(x, E, '5.2 Sprint Review'))
tbl = x[E[i52][1]:E[i52][2]]
nuevo = tbl
for tr in rows(tbl):
    cs = [html.unescape(txt(c)) for c in cells(tr)]
    if cs[0] == 'Sprint 4' and cs[2] in OBS4:
        nuevo = nuevo.replace(tr, set_row(tr, [None, None, None, OBS4[cs[2]]]), 1)
ops[i52] = strip_ids(nuevo)
p52 = buscar(x, E, 'Lo que se presentó en la revisión de cada sprint', exacto=False)
ops[p52] = clonar_parrafo(x[E[p52][1]:E[p52][2]],
    'Lo que se presentó en la revisión de cada sprint, quién lo hizo y lo que se observó. Sale de la '
    'Sprint Review de cada sprint del capítulo 4.')
i53 = tabla_desde(buscar(x, E, '5.3 Sprint Retrospective'))
tbl = x[E[i53][1]:E[i53][2]]
nuevo = tbl
for tr in rows(tbl):
    if html.unescape(txt(cells(tr)[0])) == 'Sprint 4':
        nuevo = nuevo.replace(tr, set_row(tr, [None, '\n'.join(BIEN[:3]), '\n'.join(MAL[:3]), '\n'.join(DIF[:3])]), 1)
ops[i53] = strip_ids(nuevo)
p53 = buscar(x, E, 'Pendiente: completar con la retrospectiva del Sprint 4.')
ops[p53] = ''

out = aplicar(x, E, ops)
assert len(re.findall(r'<w:drawing>', out)) == len(re.findall(r'<w:drawing>', x)), 'PARADO: cambió una imagen'
guardar(ENT, out, SAL)
print('Listo:', SAL)
print('  5.1: columna Casos de Uso; QR: API y móvil; bibliografía: 5 referencias de IA')
print('  Sprint 4: backlog al 22/11, Review y Retrospective propias, filas de 5.2 y 5.3')
