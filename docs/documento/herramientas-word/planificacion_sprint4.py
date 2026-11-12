"""Sprint 4 — punto 1 (Sprint Planning) del capítulo, más US-46/US-47 en el backlog.

Uso:  python planificacion_sprint4.py ENTRADA.docx SALIDA.docx

Qué hace, todo ubicado por texto (ver ../como-editar-el-word.md, regla 6):

- Capítulo 3: agrega US-46 y US-47 a las dos tablas del Product Backlog,
  CU47 y CU48 a la lista de casos de uso, y corrige la fila del Sprint 4 y el
  total de la planificación de sprints (3.11).
- Sprint 4, punto 1: objetivo (con la nota de que las pruebas son vitales),
  tabla de casos de uso, 1.2 Historias de Usuario con las diez tarjetas,
  contexto (pendiente del diagrama), Sprint Backlog (cabecera, tareas T-45 a
  T-57 y estado) y Equipo Scrum sin Michael, como en el Sprint 3.

El formato se copia del Sprint 3: cada pieza nueva se clona de su equivalente
ya formateada. No toca imágenes: las tarjetas del Sprint 3 traen el prototipo
en la última fila y `story_table` la reemplaza por texto.
"""
import sys, re, html
from comun import (abrir, guardar, elements, txt, rows, cells, strip_ids, set_row,
                   table, story_table, buscar, aplicar, esc, PARA_RE, tiene_imagen)

ENT, SAL = sys.argv[1], sys.argv[2]
x = abrir(ENT)
E = elements(x)


def el(n):
    t, a, b = E[n]
    return x[a:b]


def tipo(n, esperado):
    if E[n][0] != esperado:
        raise SystemExit(f'PARADO: el elemento {n} es {E[n][0]}, se esperaba {esperado}: {txt(el(n))[:80]!r}')


def con_texto(par, texto):
    """Clona un párrafo con su pPr y el rPr de su primer run, con otro texto."""
    ppr = re.search(r'<w:pPr>.*?</w:pPr>', par, re.S)
    rpr = re.search(r'<w:r(?: [^>]*)?>\s*(<w:rPr>.*?</w:rPr>)', par, re.S)
    head = re.match(r'<w:p(?: [^>]*)?>', par).group(0)
    return strip_ids(f'{head}{ppr.group(0) if ppr else ""}<w:r>{rpr.group(1) if rpr else ""}'
                     f'<w:t xml:space="preserve">{esc(texto)}</w:t></w:r></w:p>')


def reemplazar_textos(xml, pares):
    for viejo, nuevo in pares:
        v = f'>{esc(viejo)}</w:t>'
        if xml.count(v) != 1:
            raise SystemExit(f'PARADO: {viejo[:60]!r} aparece {xml.count(v)} veces')
        xml = xml.replace(v, f'>{esc(nuevo)}</w:t>')
    return xml


# ---------------------------------------------------------------------------
# Anclas
# ---------------------------------------------------------------------------
s3 = buscar(x, E, 'Sprint 3', 'Titulo11')
s4 = buscar(x, E, 'Sprint 4', 'Titulo11', desde=s3 + 1)
fin = buscar(x, E, 'ANEXOS', desde=s4)

s3_obj = buscar(x, E, '1.1 Objetivos del Sprint', desde=s3, hasta=s4)
s3_hist = buscar(x, E, '1.2 Historias de Usuario', desde=s3, hasta=s4)
s3_bk = buscar(x, E, '1.4 Sprint Backlog', desde=s3, hasta=s4)
tipo(s3_obj + 2, 'tbl'); tipo(s3_hist + 1, 'p'); tipo(s3_bk + 1, 'tbl'); tipo(s3_bk + 3, 'tbl')
TPL_CU = el(s3_obj + 2)
TPL_H12 = strip_ids(el(s3_hist))
TPL_H4 = el(s3_hist + 1)
# la tarjeta de US-28 es la única del Sprint 3 sin imagen: sirve de molde entera
i28 = buscar(x, E, 'US-28 — Notificaciones push y correo', desde=s3_hist, hasta=s4)
tipo(i28 + 1, 'tbl')
TPL_STORY = el(i28 + 1)
if tiene_imagen(TPL_STORY):
    raise SystemExit('PARADO: la tarjeta molde tiene una imagen')
TPL_EMPTY = strip_ids(el(i28 + 2))
TPL_BK_HDR = el(s3_bk + 1)
TPL_BK = el(s3_bk + 3)
TPL_ESTADO = el(s3_bk + 4)
if not txt(TPL_ESTADO).startswith('Estado al'):
    raise SystemExit('PARADO: no encontré el párrafo «Estado al…» del Sprint 3')

i_obj = buscar(x, E, '1.1 Objetivos del Sprint', desde=s4, hasta=fin)
i_hist = buscar(x, E, 'Historias de Usuario', desde=s4, hasta=fin)
i_ctx = buscar(x, E, '1.3 Contexto del Sistema', desde=s4, hasta=fin)
i_bk = buscar(x, E, '1.4 Sprint Backlog', desde=s4, hasta=fin)
i_eq = buscar(x, E, '1.5 Equipo Scrum', desde=s4, hasta=fin)
tipo(i_obj + 1, 'p'); tipo(i_obj + 2, 'tbl'); tipo(i_ctx + 1, 'p')
tipo(i_bk + 1, 'tbl'); tipo(i_bk + 3, 'tbl'); tipo(i_eq + 1, 'tbl')
if not (i_obj < i_hist < i_ctx < i_bk < i_eq):
    raise SystemExit('PARADO: el punto 1 del Sprint 4 no tiene el orden esperado')
for n in range(i_hist, i_ctx):
    if tiene_imagen(el(n)):
        raise SystemExit(f'PARADO: el elemento {n} del 1.2 del Sprint 4 tiene una imagen; no se borra')

ops = {}

# ---------------------------------------------------------------------------
# 1.1 Objetivos
# ---------------------------------------------------------------------------
OBJETIVO = ('Cerrar las épicas de IA que faltan —predicción de inasistencia y de demanda, y textos clínicos '
            'validados por el médico—, sumar los reportes por voz del paciente y el chat con su médico, y dejar '
            'todas las IA del sistema terminadas y comprobadas en producción.')
PRUEBAS = ('Es el último sprint y lo que se presenta es el sistema completo. Por eso las pruebas de este '
           'sprint son vitales y más exhaustivas que en los anteriores: cada historia entra a la rama '
           'principal con pruebas automatizadas de sus bordes —el acceso de otro paciente, de otro rol y de '
           'otra organización, la degradación sin el proveedor de IA y las entradas inválidas—, con sus casos '
           'en el plan de pruebas (2.3.1) y con capturas de cada caso que se ve en pantalla, en la web y en el '
           'móvil, tomadas contra producción. Un caso sin captura no cuenta como probado en el reporte de '
           'pruebas (2.3.2).')
obj_par = el(i_obj + 1)
ops[i_obj + 1] = con_texto(obj_par, OBJETIVO) + con_texto(obj_par, PRUEBAS)

CUS = [
    ('CU36 / Predicción de Riesgo de Inasistencia', 'WEB',
     'El sistema clasifica cada ficha futura en riesgo bajo, medio o alto de inasistencia con un modelo '
     'entrenado por organización, y el administrador lo ve y lo filtra en la agenda.'),
    ('CU37 / Envío de Recordatorios por Riesgo de Inasistencia', 'WEB/MÓVIL',
     'A las fichas con riesgo alto se les envía un segundo recordatorio, por push y por correo, más cerca '
     'de la hora, en el mismo proceso de los recordatorios de US-28.'),
    ('CU38 / Proyección de Demanda de Fichas', 'WEB',
     'El administrador consulta cuántas fichas se esperan por especialidad y franja horaria en las próximas '
     'semanas, junto a la ocupación real y con el margen de error medido.'),
    ('CU39 / Reentrenamiento del Modelo de No-Show', 'WEB',
     'El modelo de inasistencia se vuelve a entrenar solo con los desenlaces nuevos y sólo reemplaza al '
     'vigente si es mejor. El administrador ve qué versión está vigente.'),
    ('CU40 / Generación de Resumen de Consulta mediante IA', 'WEB/MÓVIL',
     'Al firmar la atención se genera un resumen en lenguaje llano para el paciente, que lo lee en el '
     'móvil después de que el médico lo aprueba.'),
    ('CU41 / Generación de Indicaciones de Preparación', 'WEB/MÓVIL',
     'Para cada orden de laboratorio o de imagen, el paciente recibe las instrucciones de preparación, '
     'redactadas sobre el corpus de la organización y aprobadas por el médico.'),
    ('CU42 / Generación de Resumen de Historia Clínica', 'WEB',
     'Antes de una nueva consulta, el médico lee una síntesis del historial del paciente en la que cada '
     'afirmación cita la atención de la que sale.'),
    ('CU43 / Validación de Contenido Generado por IA', 'WEB',
     'El médico lee, edita, aprueba o descarta cada texto generado por IA antes de que llegue al paciente. '
     'Ningún borrador sale por un endpoint del paciente.'),
    ('CU47 / Consulta de Transacciones por Voz', 'WEB/MÓVIL',
     'El paciente pide hablando o escribiendo sus pagos, fichas o comprobantes recientes y ve la lista con '
     'el QR del comprobante de cada uno. Sólo lo propio y lo de sus dependientes.'),
    ('CU48 / Chat con el Médico Tratante', 'WEB/MÓVIL',
     'El paciente atendido le escribe al médico que firmó su atención para consultas sobre la medicación o '
     'las indicaciones, y el médico responde desde la web. No es un canal de urgencias.'),
]
ops[i_obj + 2] = table(TPL_CU, [(0, None)],
                       [[str(k + 1), cu, pl, d] for k, (cu, pl, d) in enumerate(CUS)], 1)

# ---------------------------------------------------------------------------
# 1.2 Historias de Usuario
# ---------------------------------------------------------------------------
PRIO = {'🔴': 'Prioridad: ALTA', '🟡': 'Prioridad: MEDIA', '🟢': 'Prioridad: BAJA'}
NO_MOVIL = 'Móvil: — (el administrador trabaja en la web)'

HISTORIAS = [
    ('US-35 — Riesgo de inasistencia por ficha', dict(
        short='Riesgo de inasistencia de cada ficha',
        cu='CU36 — Predicción de Riesgo de Inasistencia',
        desc=['El sistema clasifica cada ficha futura en riesgo bajo, medio o alto de inasistencia, con un '
              'modelo entrenado por organización, y el administrador lo ve y lo filtra en la agenda.'],
        prio='🔴', horas='16 hr',
        func=['a) Primero los datos: seed_dataset deja de sortear el desenlace de cada ficha al azar (78/12/10) '
              'y la inasistencia pasa a depender de la anticipación de la reserva, el pago por adelantado, las '
              'faltas previas, el día y la hora. Sobre datos sorteados el modelo no tiene nada que aprender.',
              'b) La etiqueta es la inasistencia que definió US-29: no_show sobre las fichas que debían '
              'atenderse. Una cancelada a tiempo no cuenta.',
              'c) Modelo simple y explicable (regresión logística o árbol, con scikit-learn), entrenado por '
              'organización dentro de su tenant_context y guardado en model_versions con sus métricas.',
              'd) Se compara contra la línea base «siempre asiste». Si el modelo no le gana, se informa.',
              'e) Cada ficha futura tiene su predicción en noshow_predictions (bajo, medio o alto, con la '
              'probabilidad); la agenda web la muestra en una columna y la filtra.'],
        resp=['Web: Luis Miguel Aguayo (backend y agenda)', NO_MOVIL],
        proto=['Prototipo (capturas web)'])),
    ('US-36 — Recordatorios reforzados', dict(
        short='Segundo recordatorio para las fichas de riesgo alto',
        cu='CU37 — Envío de Recordatorios por Riesgo de Inasistencia',
        desc=['A las fichas clasificadas con riesgo alto se les envía un segundo recordatorio, por push y por '
              'correo, más cerca de la hora.'],
        prio='🟡', horas='10 hr',
        func=['a) Va en el mismo proceso de US-28 (send_appointment_reminders --loop), una organización a la vez '
              'dentro de tenant_context. No se agrega un proceso nuevo.',
              'b) Nunca dos veces: tiene su propia marca, puesta en la misma transacción que el envío, con la '
              'técnica de reminder_sent_at.',
              'c) Lee la predicción de US-35, no la calcula. Si la ficha no tiene predicción, no hay refuerzo.',
              'd) El aviso sale después del COMMIT y sin propagar errores: un FCM o un Brevo caído no frena la '
              'vuelta.'],
        resp=['Web: Alexander Osinaga (backend)', 'Móvil: Alexander Osinaga (recibe el push que ya existe)'],
        proto=['Prototipo (capturas móvil)'])),
    ('US-37 — Proyección de demanda', dict(
        short='Demanda esperada por especialidad y franja',
        cu='CU38 — Proyección de Demanda de Fichas',
        desc=['El administrador ve cuántas fichas se esperan por especialidad y franja horaria en las próximas '
              'semanas, junto a la ocupación real.'],
        prio='🟢', horas='10 hr',
        func=['a) Promedio por día de la semana y franja, con la tendencia de las últimas semanas: se explica en '
              'una frase y se puede comparar con lo que pasó.',
              'b) Se calcula en la base, como los KPI de US-29, dentro de la organización.',
              'c) Se muestra en el panel de indicadores junto a la ocupación real, con el margen de error medido '
              'sobre semanas pasadas.'],
        resp=['Web: José Daniel Iporo (backend y panel)', NO_MOVIL],
        proto=['Prototipo (capturas web)'])),
    ('US-38 — Reentrenamiento del modelo', dict(
        short='Reentrenamiento periódico del modelo de inasistencia',
        cu='CU39 — Reentrenamiento del Modelo de No-Show',
        desc=['El modelo de inasistencia se vuelve a entrenar solo con los desenlaces nuevos y sólo reemplaza al '
              'vigente si es mejor.'],
        prio='🟢', horas='10 hr',
        func=['a) Comando retrain_noshow con el mismo patrón --loop de las copias y los recordatorios, '
              'organización por organización.',
              'b) Un modelo nuevo no reemplaza al vigente si es peor: los dos se miden con la misma métrica sobre '
              'los mismos datos de prueba, y las dos versiones quedan en model_versions.',
              'c) El administrador ve qué versión está vigente, cuándo se entrenó y con qué resultado.'],
        resp=['Web: José Daniel Iporo (backend y estado del modelo)', NO_MOVIL],
        proto=['Prototipo (capturas web)'])),
    ('US-39 — Resumen claro de la consulta', dict(
        short='Resumen de la consulta en lenguaje llano',
        cu='CU40 — Generación de Resumen de Consulta mediante IA',
        desc=['Al firmar la atención se genera un resumen en lenguaje llano —qué se encontró, qué hay que hacer, '
              'cuándo volver— que el paciente lee en el móvil después de que el médico lo aprueba.'],
        prio='🟡', horas='10 hr',
        func=['a) Se genera desde la atención firmada y su receta, no desde texto libre: el prompt lleva sólo esos '
              'campos y nunca datos de otro paciente.',
              'b) Sin proveedor no se genera, y se dice. No hay plantilla de reemplazo para un resumen médico: uno '
              'armado por reglas se leería como si lo hubiera revisado alguien.',
              'c) Nace en borrador y pasa por US-42. El paciente sólo ve el texto aprobado.',
              'd) El móvil lo muestra en la atención de su historial.'],
        resp=['Web: Karen Ortega (backend)', 'Móvil: Karen Ortega'],
        proto=['Prototipo (capturas móvil)'])),
    ('US-40 — Preparación para estudios', dict(
        short='Instrucciones de preparación para cada estudio',
        cu='CU41 — Generación de Indicaciones de Preparación',
        desc=['Para cada orden de laboratorio o de imagen, el paciente recibe las instrucciones de preparación '
              '(ayuno, medicación que suspender, qué llevar), aprobadas por el médico.'],
        prio='🟢', horas='6 hr',
        func=['a) Sale primero del corpus administrativo de US-32, que ya tiene las preparaciones cargadas por '
              'la organización. El modelo sólo redacta sobre lo recuperado.',
              'b) Si no hay fragmento, no inventa una preparación: lo dice y remite al centro.',
              'c) Pasa por US-42, y el paciente la ve en el móvil junto a la orden.'],
        resp=['Web: Luis Mateo Hurtado (backend)', 'Móvil: Luis Mateo Hurtado'],
        proto=['Prototipo (capturas móvil)'])),
    ('US-41 — Resumen del historial para el médico', dict(
        short='Síntesis del historial antes de la consulta',
        cu='CU42 — Generación de Resumen de Historia Clínica',
        desc=['Antes de una nueva consulta, el médico lee en la pantalla de la atención una síntesis del '
              'historial del paciente, en la que cada afirmación cita la atención de la que sale.'],
        prio='🟢', horas='10 hr',
        func=['a) Cada oración cita la atención de la que sale ([A1], [A2]…). La oración sin cita, o con una '
              'cita que no existe, se descarta: no se le cree al modelo, se lo verifica.',
              'b) Las alergias, condiciones y medicación declaradas (US-08) se muestran siempre, leídas de la '
              'base, aunque el modelo no las mencione.',
              'c) Sin proveedor se degrada: copia los diagnósticos tal cual de cada atención, con su cita, y se '
              'rotula como plantilla.',
              'd) Sólo para el médico con vínculo de atención en esa organización. Al modelo no le llegan el '
              'nombre ni el documento del paciente.',
              'e) Entregada el 11/11/26 (PR #99), con 16 pruebas verificadas por mutación.'],
        resp=['Web: Luis Mateo Hurtado (backend y panel en la atención)',
              'Móvil: — (el médico trabaja en la web)'],
        proto=['Prototipo (capturas web)'])),
    ('US-42 — Validar o editar texto de IA', dict(
        short='Bandeja del médico para los textos generados',
        cu='CU43 — Validación de Contenido Generado por IA',
        desc=['Ningún texto generado por IA llega al paciente sin que un médico lo apruebe: el médico lo lee, '
              'lo edita, lo aprueba o lo descarta desde una bandeja.'],
        prio='🔴', horas='6 hr',
        func=['a) Una sola tabla para todo texto generado (ai_generated_texts): tipo, atención u orden de '
              'origen, texto generado, texto final, estado (borrador, aprobado, descartado), quién lo aprobó y '
              'cuándo. US-39, US-40 y US-41 escriben ahí.',
              'b) Se guardan el texto original del modelo y el editado: si el médico corrige, queda la diferencia.',
              'c) El paciente sólo lee textos aprobados. Un borrador no sale por ningún endpoint del paciente, y '
              'una prueba lo demuestra.',
              'd) Bandeja web del médico con sus textos pendientes.'],
        resp=['Web: Karen Ortega (backend y bandeja)', 'Móvil: — (el médico trabaja en la web)'],
        proto=['Prototipo (capturas web)'])),
    ('US-46 — Transacciones por voz del paciente', dict(
        short='Mis pagos, fichas y comprobantes, pedidos por voz',
        cu='CU47 — Consulta de Transacciones por Voz',
        desc=['El paciente pide, hablando o escribiendo, «mis últimas 2 facturas» o «mis fichas de cardiología» '
              'y ve la lista con el QR del comprobante de cada una.'],
        prio='🟡', horas='10 hr',
        func=['a) Reutiliza la voz de la característica 5 (reconocimiento en el dispositivo) y las reglas de '
              'reporting/voice.py: lista cerrada, validación contra el catálogo y degradación sin proveedor.',
              'b) El modelo traduce, no responde: devuelve tipo, cantidad, rango de fechas y especialidad. Los '
              'datos y los QR salen de la base, y lo que no entendió lo dice.',
              'c) Sólo lo propio: la consulta está atada al paciente que habla y a sus dependientes. Una prueba '
              'intenta pedir los pagos de otro.',
              'd) El QR es el del comprobante firmado de US-19, y la lista se descarga en PDF con el exportador '
              'que ya existe.'],
        resp=['Web: Alexander Osinaga (backend y web)', 'Móvil: Alexander Osinaga'],
        proto=['Prototipo (capturas web y móvil)'])),
    ('US-47 — Chat con el médico tratante', dict(
        short='Consultas al médico después de la atención',
        cu='CU48 — Chat con el Médico Tratante',
        desc=['El paciente atendido le escribe al médico que lo atendió para consultas sobre la medicación o las '
              'indicaciones de esa atención, y el médico le responde desde la web. Lo pidió la ingeniera el '
              '12/11/26.'],
        prio='🟡', horas='10 hr',
        func=['a) La conversación nace de una atención firmada: una por atención, entre su paciente y el médico '
              'que la firmó, con la receta y las órdenes de esa atención a la vista.',
              'b) Se puede escribir durante 15 días desde la firma (a confirmar en la revisión). Después queda de '
              'sólo lectura y ofrece reservar una ficha. El médico puede cerrarla antes.',
              'c) No es un canal de urgencias: cada mensaje del paciente pasa por las reglas de la barrera de '
              'US-34. Si disparan, el paciente ve primero la derivación a emergencias y el médico ve el mensaje '
              'marcado.',
              'd) El mismo alcance que la historia clínica: el paciente o el titular del dependiente y el médico '
              'firmante, en esa organización. RLS y pruebas que intentan entrar desde otro paciente, otro médico '
              'y otra organización, verificadas por mutación.',
              'e) Sin tiempo real: la pantalla consulta cada 10 segundos, y el mensaje nuevo avisa por push (el '
              'FCM de US-28) al paciente y con un contador en la bandeja del médico.',
              'f) Sólo texto, hasta 2.000 caracteres. Un mensaje no se edita ni se borra.'],
        resp=['Web: Luis Mateo Hurtado (backend y bandeja del médico)', 'Móvil: Luis Mateo Hurtado'],
        proto=['Prototipo (capturas web y móvil)'])),
]

bloque = [TPL_H12]
for titulo, d in HISTORIAS:
    d = dict(d, prio=PRIO[d['prio']], horas='Cant Horas : ' + d['horas'])
    bloque += [con_texto(TPL_H4, titulo), story_table(TPL_STORY, d), TPL_EMPTY]
ops[i_hist] = ''.join(bloque)
for n in range(i_hist + 1, i_ctx):
    ops[n] = ''

# ---------------------------------------------------------------------------
# 1.3 Contexto del Sistema
# ---------------------------------------------------------------------------
ops[i_ctx + 1] = con_texto(el(i_ctx + 1),
                           'Pendiente: diagrama de casos de uso del Sprint 4 —CU36 a CU43, CU47 y CU48 con sus '
                           'actores—, exportado de Enterprise Architect.')

# ---------------------------------------------------------------------------
# 1.4 Sprint Backlog
# ---------------------------------------------------------------------------
objetivo_s3 = html.unescape(re.findall(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', TPL_BK_HDR)[4])
if objetivo_s3 == 'Objetivo: ' or not objetivo_s3.startswith('Cerrar la Épica 5'):
    raise SystemExit('PARADO: no encontré el objetivo del Sprint 3 en la cabecera del backlog')
ops[i_bk + 1] = strip_ids(reemplazar_textos(TPL_BK_HDR, [
    ('Número de Sprint: 3', 'Número de Sprint: 4'),
    ('Tiempo Programado: 19 días', 'Tiempo Programado: 14 días'),
    (objetivo_s3, OBJETIVO),
    ('Fecha de Inicio: 13/10/26', 'Fecha de Inicio: 10/11/26'),
    ('Fecha de Finalización: 31/10/26', 'Fecha de Finalización: 23/11/26'),
]))

TAREAS = [
    ('T-45', 'Clasificar cada ficha por riesgo de inasistencia', 'Historia', '16 horas', 'Aguayo Quiroz, L.M.', 'Pendiente', 'Must have'),
    ('T-46', 'Recordatorios reforzados por riesgo alto', 'Historia', '10 horas', 'Osinaga Blanco, A.', 'Pendiente', 'Should have'),
    ('T-47', 'Proyección de demanda por especialidad y franja', 'Historia', '10 horas', 'Iporo Chulque, J.D.', 'Pendiente', 'Could have'),
    ('T-48', 'Reentrenamiento periódico del modelo', 'Historia', '10 horas', 'Iporo Chulque, J.D.', 'Pendiente', 'Could have'),
    ('T-49', 'Resumen claro de la consulta', 'Historia', '10 horas', 'Ortega Mancilla, K.P.', 'Pendiente', 'Should have'),
    ('T-50', 'Instrucciones de preparación para estudios', 'Historia', '6 horas', 'Hurtado Castro, L.M.', 'Pendiente', 'Could have'),
    ('T-51', 'Resumen del historial para el médico', 'Historia', '10 horas', 'Hurtado Castro, L.M.', 'Completado', 'Could have'),
    ('T-52', 'Validar o editar texto generado por IA', 'Historia', '6 horas', 'Ortega Mancilla, K.P.', 'En progreso', 'Must have'),
    ('T-53', 'Reportes transaccionales por voz del paciente', 'Historia', '10 horas', 'Osinaga Blanco, A.', 'Pendiente', 'Should have'),
    ('T-54', 'Diagrama de redes', 'Documentación', '4 horas', 'Hurtado Castro, L.M.', 'En progreso', 'Must have'),
    ('T-55', 'Verificación final de las IA en producción', 'Pruebas', '4 horas', 'Aguayo Quiroz, L.M.', 'Pendiente', 'Must have'),
    ('T-56', 'Chat con el médico tratante', 'Historia', '10 horas', 'Hurtado Castro, L.M.', 'Pendiente', 'Should have'),
    ('T-57', 'Capítulo del Sprint 4, diagramas y capturas', 'Técnica', 'Fuera de las 106 h', 'Hurtado Castro, L.M.', 'En progreso', 'Must have'),
]
ops[i_bk + 3] = table(TPL_BK, [(0, None)], [list(t) for t in TAREAS], 1)

ESTADO = ('Estado al 12/11/26. US-41 está en la rama principal desde el 11/11 (PR #99). US-42 está en curso: '
          'su tabla de textos generados es la que destraba US-39, US-40 y US-41 para el paciente, y su plazo es '
          'el 14/11. US-46 y US-47 son historias nuevas: la primera salió de la revisión del Sprint 3 y la '
          'segunda la pidió la ingeniera el 12/11, ya con el sprint en marcha. Las dos suben el compromiso de '
          '78 a 106 horas, junto con el diagrama de redes y la verificación final de las IA.')
for n in range(i_bk + 4, i_eq):
    if tiene_imagen(el(n)) or txt(el(n)).strip():
        raise SystemExit(f'PARADO: el elemento {n} entre el backlog y el equipo no está vacío')
# «Estado al…» en negrita y el resto normal, con los rPr de los dos primeros runs del Sprint 3
_runs = re.findall(r'<w:r(?: [^>]*)?>\s*(<w:rPr>.*?</w:rPr>)', TPL_ESTADO, re.S)
_ppr = re.search(r'<w:pPr>.*?</w:pPr>', TPL_ESTADO, re.S)
_et, _resto = ESTADO.split(' ', 3)[:3], ESTADO.split(' ', 3)[3]
ops[i_bk + 4] = strip_ids(
    f'<w:p>{_ppr.group(0) if _ppr else ""}'
    f'<w:r>{_runs[0]}<w:t xml:space="preserve">{esc(" ".join(_et))}</w:t></w:r>'
    f'<w:r>{re.sub(r"<w:b(?:Cs)?/>", "", _runs[0])}<w:t xml:space="preserve">{esc(" " + _resto)}</w:t></w:r></w:p>') + TPL_EMPTY
for n in range(i_bk + 5, i_eq):
    ops[n] = ''

# ---------------------------------------------------------------------------
# 1.5 Equipo Scrum: sin Michael, como el Sprint 3
# ---------------------------------------------------------------------------
eq = el(i_eq + 1)
mich = [p for p in PARA_RE.findall(eq) if 'Mamani Samurio' in txt(p)]
if len(mich) == 1:
    ops[i_eq + 1] = eq.replace(mich[0], '', 1)
elif mich:
    raise SystemExit('PARADO: Michael aparece más de una vez en el Equipo Scrum')

# ---------------------------------------------------------------------------
# 2. Proceso/patrón: los mismos títulos que el Sprint 3, más 2.1.1.3 Diagrama de Redes
# ---------------------------------------------------------------------------
# El esqueleto que tenía el Sprint 4 venía del Sprint 0 (Modelo C4, títulos pegados
# en un mismo párrafo). Se reemplaza entero por los títulos del Sprint 3, clonando
# el formato de cada nivel, con los CU del Sprint 4 y un párrafo vacío debajo de
# cada título hoja para pegar el diagrama.
s3_p2 = buscar(x, E, '2. Proceso/patrón de desarrollo por Historia de Usuario', 'Titulo2', desde=s3, hasta=s4)
s3_d3 = buscar(x, E, '3. Daily Scrum', 'Titulo2', desde=s3_p2, hasta=s4)
NIVEL = {}
for n in range(s3_p2, s3_d3):
    m = re.search(r'<w:pStyle w:val="([^"]+)"/>', el(n)[:600]) if E[n][0] == 'p' else None
    if m and m.group(1) not in NIVEL:
        NIVEL[m.group(1)] = el(n)
for k in ('Titulo2', 'Titulo3', 'Titulo4', 'titulo5', 'Titulo6'):
    if k not in NIVEL:
        raise SystemExit(f'PARADO: el punto 2 del Sprint 3 no tiene un título {k}')

p2 = buscar(x, E, '2. Proceso/patrón de desarrollo por Historia de Usuario', 'Titulo2', desde=i_eq, hasta=fin)
d3 = buscar(x, E, '3. Daily Scrum', 'Titulo2', desde=p2, hasta=fin)
for n in range(p2, d3):
    s = el(n)
    if tiene_imagen(s) or E[n][0] != 'p':
        raise SystemExit(f'PARADO: el punto 2 del Sprint 4 ya tiene contenido (elemento {n}); no se pisa')
    if txt(s).strip() and 'w:pStyle' not in s[:600]:
        raise SystemExit(f'PARADO: el punto 2 del Sprint 4 tiene texto que no es título (elemento {n})')

TODOS = ['CU36 – Predicción de Riesgo de Inasistencia',
         'CU37 – Envío de Recordatorios por Riesgo de Inasistencia',
         'CU38 – Proyección de Demanda de Fichas',
         'CU39 – Reentrenamiento del Modelo de No-Show',
         'CU40 – Generación de Resumen de Consulta mediante IA',
         'CU41 – Generación de Indicaciones de Preparación',
         'CU42 – Generación de Resumen de Historia Clínica',
         'CU43 – Validación de Contenido Generado por IA',
         'CU47 – Consulta de Transacciones por Voz',
         'CU48 – Chat con el Médico Tratante']
# estados y tiempo: como en el Sprint 3, sólo los CU con proceso o transacción
# (fuera las consultas: CU38, CU42 y CU47)
PROCESOS = [c for c in TODOS if c[:4] not in ('CU38', 'CU42', 'CU47')]

H = lambda nivel, texto: con_texto(NIVEL[nivel], texto)
VACIO = TPL_EMPTY
esq = [H('Titulo2', '2. Proceso/patrón de desarrollo por Historia de Usuario'),
       H('Titulo3', '2.1 Diseño'),
       H('Titulo4', '2.1.1 Diseñar de la arquitectura')]
for t in ('2.1.1.1 Diagrama de capas', '2.1.1.2 Diagrama de despliegue', '2.1.1.3 Diagrama de Redes'):
    esq += [H('titulo5', t), VACIO]
esq += [H('Titulo4', '2.1.2 Diseño de datos')]
for t in ('2.1.2.1 Diseño Conceptual', '2.1.2.2 Diseño lógico (Mapeo)', '2.1.2.3 Diseño Físico (Script)'):
    esq += [H('titulo5', t), VACIO]
esq += [H('Titulo4', '2.1.3 Diseño de la lógica de negocio'),
        H('titulo5', '2.1.3.1 Diagrama de comunicación')]
esq += [p for c in TODOS for p in (H('Titulo6', c), VACIO)]
esq += [H('Titulo4', '2.1.4 Diseño de procesos')]
for t, cus in (('2.1.4.1 Diagrama de diseño de clase', TODOS),
               ('2.1.4.2 Diagrama de secuencia', TODOS),
               ('2.1.4.3 Diagrama de estados (solo procesos y transacciones)', PROCESOS),
               ('2.1.4.4 Diagrama de tiempo (procesos en general)', PROCESOS),
               ('2.1.4.5 Diagrama de navegación', ['Sistema'])):
    esq += [H('titulo5', t)] + [p for c in cus for p in (H('Titulo6', c), VACIO)]
esq += [H('Titulo3', '2.2 Implementación'),
        H('Titulo4', '2.2.1 Componentes y artefactos generados'), VACIO,
        H('Titulo3', '2.3 Pruebas'),
        H('Titulo4', '2.3.1 Plan de pruebas (criterios de aceptación - Caja Negra)'), VACIO,
        H('Titulo4', '2.3.2 Reporte de prueba'), VACIO]
ops[p2] = ''.join(esq)
for n in range(p2 + 1, d3):
    ops[n] = ''

# ---------------------------------------------------------------------------
# Capítulo 3: backlog, casos de uso y planificación
# ---------------------------------------------------------------------------
def tabla_que_termina(ultima_celda0, ncols):
    for n, (t, a, b) in enumerate(E[:s3]):
        if t != 'tbl':
            continue
        rs = rows(x[a:b])
        cs = cells(rs[-1])
        if len(cs) == ncols and html.unescape(txt(cs[0])).strip() == ultima_celda0:
            yield n


def agregar_filas(n, filas):
    tbl = el(n)
    rs = rows(tbl)
    nuevas = ''.join(strip_ids(set_row(rs[-1], f)) for f in filas)
    z = tbl.rfind(rs[-1]) + len(rs[-1])
    return tbl[:z] + nuevas + tbl[z:]


cap3 = {}
for n in tabla_que_termina('US-45', 3):
    cap3[n] = agregar_filas(n, [
        ['US-46', 'paciente', 'Quiero consultar por voz mis pagos, fichas y comprobantes recientes y ver el QR de '
                              'cada uno, para tener a mano lo que pagué sin buscarlo pantalla por pantalla.'],
        ['US-47', 'paciente', 'Quiero escribirle al médico que me atendió para consultarle sobre la medicación o '
                              'las indicaciones de esa atención, para resolver mis dudas sin pedir otra ficha.'],
    ])
for n in tabla_que_termina('US-45', 5):
    cap3[n] = agregar_filas(n, [
        ['US-46', 'Paciente', 'Consultar por voz mis pagos, fichas y comprobantes recientes y ver el QR de cada uno.', '🟡', '10 h'],
        ['US-47', 'Paciente', 'Escribirle al médico tratante para consultas sobre la medicación o las indicaciones de la atención.', '🟡', '10 h'],
    ])
for n in tabla_que_termina('CU46', 5):
    cap3[n] = agregar_filas(n, [
        ['CU47', 'Consulta de Transacciones por Voz', 'X', 'X', 'Paciente'],
        ['CU48', 'Chat con el Médico Tratante', 'X', 'X', 'Paciente / Médico'],
    ])
if len(cap3) != 3:
    raise SystemExit(f'PARADO: esperaba 3 tablas del capítulo 3 (backlog x2 y casos de uso), encontré {len(cap3)}')

i_plan = buscar(x, E, '3.11 Planificación Sprint (Diagrama de Gantt)', exacto=False, hasta=s3)
plan = None
for n in range(i_plan, i_plan + 6):
    if E[n][0] == 'tbl' and 'US-35 a US-42' in txt(el(n)):
        plan = n
        break
if plan is None:
    raise SystemExit('PARADO: no encontré la tabla del 3.11 con la fila del Sprint 4')
pt = el(plan)
# la última celda de cada fila de sprint: «56 h», «102 h»… (la cabecera y el total no)
horas = []
for tr in rows(pt):
    m = re.fullmatch(r'\s*(\d+) h\s*', html.unescape(txt(cells(tr)[-1])))
    if m:
        horas.append(int(m.group(1)))
if len(horas) != 5 or horas[-1] != 78:
    raise SystemExit(f'PARADO: las horas del 3.11 no son las esperadas: {horas}')
total = sum(horas) - 78 + 106
pt = reemplazar_textos(pt, [('US-35 a US-42', 'US-35 a US-42 + US-46, US-47'), ('78 h', '106 h')])
# el total es «=» y «436 h» en dos runs; el 436 no era la suma (daba 452), se pone la suma real
_tot = re.findall(r'>(\d+ h)</w:t>', rows(pt)[-1])
if len(_tot) != 1:
    raise SystemExit(f'PARADO: la fila del total no tiene un solo valor: {_tot}')
pt = reemplazar_textos(pt, [(_tot[0], f'{total} h')])
cap3[plan] = pt

ops.update(cap3)

out = aplicar(x, E, ops)
guardar(ENT, out, SAL)
print(f'Listo: {SAL}')
print(f'  capítulo 3: tablas {sorted(cap3)}; total del 3.11 = {total} h')
print(f'  Sprint 4: {len(HISTORIAS)} historias, {len(TAREAS)} tareas, {len(CUS)} casos de uso')
print(f'  Michael quitado del Equipo Scrum: {"sí" if mich else "no estaba"}')
