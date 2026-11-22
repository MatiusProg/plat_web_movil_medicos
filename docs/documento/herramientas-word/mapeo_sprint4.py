"""Escribe el 2.1.2.2 «Diseño lógico (Mapeo)» del Sprint 4 con el formato del Sprint 3.

Uso: python mapeo_sprint4.py PLANTILLA.docx ENTRADA.docx SALIDA.docx

PLANTILLA es el documento del grupo («Proyecto SI2 Grupo15.docx»), que tiene el
2.1.2.2 del Sprint 3 ya hecho: de ahí se clonan el párrafo de introducción, el
título de cada tabla («tabla — qué guarda (US)»), la tabla Columna | Tipo |
Restricción con su encabezado azul y el párrafo en blanco que las separa. Así
el Sprint 4 sale con los mismos estilos sin reescribirlos a mano.

El contenido sale de las migraciones del sprint y coincide con el script del
2.1.2.3. Se inserta debajo del título «2.1.2.2 Diseño lógico (Mapeo)» del
Sprint 4 y no toca nada más. Si ese apartado ya tiene contenido, no hace nada.
"""
import copy
import sys

import docx
from docx.oxml.ns import qn

PLANTILLA, ENT, SAL = sys.argv[1], sys.argv[2], sys.argv[3]

INTRO = [
    ('El mapeo al modelo relacional de las doce tablas que creó el sprint. Como en el Sprint 3, las '
     'claves foráneas hacia registros de la organización son ', False),
    ('compuestas', True),
    (' «(x_id, organization_id)»: un mensaje no puede colgar de una conversación de otra organización '
     'ni una predicción de una ficha ajena, aunque la aplicación se equivoque (RNF-08). Las reglas que no '
     'pueden depender de la aplicación (lo firmado no se toca, lo validado no se edita) las cumplen '
     'triggers en la propia base.', False),
]

ORG = ('organization_id', 'uuid', 'FK organizations, NOT NULL')
ID = ('id', 'uuid', 'PK')
FECHAS = ('created_at / updated_at', 'timestamptz', 'NOT NULL')

TABLAS = [
    ('ai_generated_texts', 'los textos que escribe la IA y valida el médico (US-39 a US-42)', [
        ID, ORG,
        ('patient_id / practitioner_id', 'uuid', 'FK compuestas a patients y practitioners, NOT NULL'),
        ('encounter_id', 'uuid', 'FK compuesta a encounters; obligatoria en el resumen de la consulta y en la preparación'),
        ('medical_order_id', 'uuid', 'FK compuesta a encounter_orders; obligatoria en la preparación para un estudio'),
        ('kind', 'varchar(24)', 'consultation_summary, preparation o history_summary (ck_ai_text_kind)'),
        ('generated_text / final_text', 'text', 'Lo que escribió el modelo y lo que quedó tras la revisión, NOT NULL'),
        ('generated_by', 'varchar(60)', 'El modelo que lo escribió'),
        ('status', 'varchar(10)', 'draft, approved o discarded (ck_ai_text_status); aprobado exige final_text no vacío'),
        ('reviewed_by_id', 'uuid', 'FK compuesta a users: el médico que lo validó'),
        ('reviewed_at', 'timestamptz', 'Con reviewed_by_id, obligatorio fuera de draft (ck_ai_text_reviewed)'),
        FECHAS,
        ('trigger', 'trg_ai_generated_texts_inmutable',
         'No se borra (se descarta), el texto del modelo no cambia y lo validado o descartado ya no se modifica'),
    ]),
    ('waitlist_entries', 'la lista de espera (US-52)', [
        ID, ORG,
        ('patient_id', 'uuid', 'FK compuesta a patients, NOT NULL'),
        ('requested_by_id', 'uuid', 'FK compuesta a users: quien lo anotó, NOT NULL'),
        ('practitioner_id / specialty_id', 'uuid', 'FK compuestas; al menos una de las dos (ck_waitlist_target)'),
        ('branch_id', 'uuid', 'FK compuesta a branches; NULL es cualquier sucursal'),
        ('date_from / date_to', 'date', 'Las fechas que le sirven; date_to ≥ date_from (ck_waitlist_date_order)'),
        ('status', 'varchar(10)', 'waiting, offered, booked, expired o cancelled (ck_waitlist_status)'),
        ('offered_appointment_id', 'uuid', 'FK compuesta a appointments: el turno liberado que se le ofreció'),
        ('offered_at', 'timestamptz', 'Cuándo se le ofreció; la reserva vence si no la paga'),
        FECHAS,
    ]),
    ('appointment_preconsultations', 'la preconsulta del plus (US-51)', [
        ('id', 'bigint', 'PK, identidad'), ORG,
        ('appointment_id', 'uuid', 'FK compuesta a appointments, UNIQUE: una por ficha'),
        ('reason', 'text', 'Motivo de la consulta, NOT NULL'),
        ('questions', 'text', 'Preguntas para el médico, NOT NULL'),
        ('updated_at', 'timestamptz', 'NOT NULL'),
    ]),
    ('encounter_ratings', 'la calificación de la atención (US-48)', [
        ID, ORG,
        ('encounter_id', 'uuid', 'FK compuesta a encounters, UNIQUE: una por atención'),
        ('patient_id / practitioner_id / branch_id', 'uuid', 'FK compuestas, NOT NULL'),
        ('rated_by_id', 'uuid', 'FK compuesta a users: quien calificó, NOT NULL'),
        ('stars', 'smallint', 'De 1 a 5 (ck_rating_stars)'),
        ('comment', 'varchar(500)', 'Opcional; vacío por defecto'),
        FECHAS,
        ('trigger', 'trg_encounter_ratings_guarda',
         'Sólo se califica una atención firmada; no se borra, no cambia de atención ni de autor y se corrige sólo durante 7 días'),
    ]),
    ('encounter_medication_intakes', 'las tomas de los medicamentos (US-49)', [
        ID, ORG,
        ('patient_id', 'uuid', 'FK compuesta a patients, NOT NULL'),
        ('prescription_item_id', 'uuid', 'FK compuesta a encounter_prescription_items, NOT NULL'),
        ('dose_number', 'smallint', 'Número de toma, desde 1 (ck_intake_dose_number)'),
        ('(prescription_item_id, dose_number)', 'único', 'Una toma no se marca dos veces (uq_intake_item_dose)'),
        ('status', 'varchar(8)', 'taken o skipped (ck_intake_status)'),
        ('scheduled_at', 'timestamptz', 'La hora prevista de la toma'),
        ('recorded_at', 'timestamptz', 'NOT NULL'),
        ('recorded_by_id', 'uuid', 'FK compuesta a users, NOT NULL'),
        ('trigger', 'trg_encounter_medication_intakes_guarda',
         'Sólo se marcan tomas de una receta firmada; una toma marcada no se cambia ni se borra'),
    ]),
    ('encounter_vital_signs', 'los signos vitales de la atención (US-53)', [
        ID, ORG,
        ('encounter_id', 'uuid', 'FK compuesta a encounters, UNIQUE: uno por atención'),
        ('systolic / diastolic', 'smallint', 'mmHg, de 50 a 300 y de 20 a 200; la sistólica mayor que la diastólica'),
        ('heart_rate', 'smallint', 'Latidos por minuto, de 20 a 250'),
        ('temperature', 'numeric(3,1)', '°C, de 30 a 45'),
        ('spo2', 'smallint', 'Saturación en %, de 50 a 100'),
        ('weight_kg / height_cm', 'numeric(4,1)', 'De 0,5 a 400 kg y de 30 a 250 cm'),
        ('glucose', 'smallint', 'mg/dL, de 10 a 1000'),
        ('(cada medida)', 'NULL', 'Se carga sólo lo que se midió; los rangos son los ck_vitals_*_posible'),
        FECHAS,
        ('trigger', 'trg_vital_signs_solo_en_borrador', 'Rechaza INSERT, UPDATE y DELETE si la atención está firmada'),
    ]),
    ('encounter_threads', 'la conversación del paciente con su médico (US-47)', [
        ID, ORG,
        ('encounter_id', 'uuid', 'FK compuesta a encounters, UNIQUE: una por atención'),
        ('patient_id / practitioner_id', 'uuid', 'FK compuestas, NOT NULL'),
        ('patient_read_at / practitioner_read_at', 'timestamptz', 'Hasta dónde leyó cada lado'),
        ('last_message_at', 'timestamptz', 'El último mensaje; ordena la bandeja del médico'),
        ('closed_at', 'timestamptz', 'Cuándo se cerró'),
        ('closed_by_id', 'uuid', 'FK compuesta a users; va junto con closed_at (ck_thread_closed)'),
        ('created_at', 'timestamptz', 'NOT NULL'),
        ('trigger', 'trg_encounter_threads_guarda',
         'No se borra, no cambia de atención ni de participantes y una conversación cerrada no se reabre'),
    ]),
    ('encounter_messages', 'los mensajes del chat (US-47)', [
        ID, ORG,
        ('thread_id', 'uuid', 'FK compuesta a encounter_threads, NOT NULL'),
        ('author_id', 'uuid', 'FK compuesta a users, NOT NULL'),
        ('side', 'varchar(12)', 'patient o practitioner (ck_message_side)'),
        ('body', 'text', 'No vacío (ck_message_body)'),
        ('flagged_emergency', 'boolean', 'Posible urgencia; sólo en mensajes del paciente (ck_message_flag_patient)'),
        ('created_at', 'timestamptz', 'NOT NULL'),
        ('trigger', 'trg_encounter_messages_inmutable', 'Un mensaje no se modifica ni se borra'),
    ]),
    ('model_versions', 'las versiones del modelo de inasistencia (US-35 y US-38)', [
        ID, ORG,
        ('kind', 'varchar(16)', 'noshow (ck_model_version_kind)'),
        ('version', 'integer', 'Correlativo por organización y tipo (uq_model_version_numero)'),
        ('status', 'varchar(10)',
         'active, candidate, rejected o retired; una sola active por organización y tipo (uq_model_version_vigente)'),
        ('beats_baseline', 'boolean', 'Si le gana a «siempre asiste»; active y candidate lo exigen (ck_model_version_supera_base)'),
        ('trained_at', 'timestamptz', 'NOT NULL'),
        ('n_train / n_test', 'integer', 'Fichas para aprender y para comprobar, con un corte en el tiempo'),
        ('base_rate', 'double precision', 'Tasa de ausencias del entrenamiento; de ella salen los umbrales'),
        ('params', 'jsonb', 'Variables, coeficientes, intercepto, media y escala'),
        ('metrics', 'jsonb', 'AUC, Brier, recall, precisión, umbrales y la comparación del reentrenamiento'),
        FECHAS,
    ]),
    ('noshow_predictions', 'el riesgo de inasistencia de cada ficha futura (US-35)', [
        ID, ORG,
        ('appointment_id', 'uuid', 'FK compuesta a appointments, UNIQUE: una por ficha, se actualiza en cada vuelta'),
        ('model_version_id', 'uuid', 'FK compuesta a model_versions: la versión que la calculó'),
        ('probability', 'double precision', 'Entre 0 y 1 (ck_noshow_pred_probability)'),
        ('level', 'varchar(6)', 'low, medium o high (ck_noshow_pred_level)'),
        ('factors', 'jsonb', 'Lo que más aumenta o reduce el riesgo, para explicarlo en pantalla'),
        ('computed_at', 'timestamptz', 'NOT NULL'),
    ]),
    ('finance_settings', 'la configuración de las finanzas (US-50)', [
        ID,
        ('organization_id', 'uuid', 'FK organizations, UNIQUE: una por organización'),
        ('stripe_percent', 'numeric(5,2)', 'Comisión de la pasarela en los pagos en línea; el efectivo no la paga'),
        ('updated_at', 'timestamptz', 'NOT NULL'),
    ]),
    ('expenses', 'los gastos de la organización (US-50)', [
        ID, ORG,
        ('branch_id', 'uuid', 'FK compuesta a branches; NULL es un gasto general'),
        ('category', 'varchar(12)', 'insumos, alquiler, sueldos, servicios u otros'),
        ('amount', 'numeric(10,2)', 'Mayor que 0 (ck_expense_amount)'),
        ('currency', 'varchar(3)', 'Moneda, NOT NULL'),
        ('spent_on', 'date', 'Fecha del gasto, NOT NULL'),
        ('note', 'varchar(200)', 'Detalle; vacío por defecto'),
        ('created_by_id', 'uuid', 'FK users, ON DELETE SET NULL: quien lo cargó'),
        FECHAS,
    ]),
]

CIERRE = [
    ('appointments', False),
    (' — se agrega reinforced_reminder_sent_at, timestamptz NULL: el segundo recordatorio de una ficha con '
     'riesgo alto ya salió (US-36). ', False),
    ('practitioners', False),
    (' — se agrega fee_percent, numeric(5,2) NOT NULL DEFAULT 0: el porcentaje de lo cobrado que se le paga '
     'al profesional, de 0 a 100 (US-50).', False),
]


def texto(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t'))).strip()


def seccion(body, sprint):
    """Los elementos entre «2.1.2.2» y «2.1.2.3» del sprint pedido (sin los títulos)."""
    actual, dentro, out, titulo = None, False, [], None
    for el in body.iterchildren():
        t = texto(el)
        if el.tag == qn('w:p') and t.startswith('Sprint ') and len(t) < 10:
            actual = t
        if el.tag == qn('w:p') and t.startswith('2.1.2.2'):
            dentro = actual == sprint
            if dentro:
                titulo = el
            continue
        if el.tag == qn('w:p') and t.startswith('2.1.2.3'):
            dentro = False
        if dentro:
            out.append(el)
    return titulo, out


def limpiar(el):
    """Sin w14:paraId/textId: Word los regenera y así no quedan repetidos."""
    for e in el.iter():
        for a in list(e.attrib):
            if a.endswith('}paraId') or a.endswith('}textId'):
                del e.attrib[a]
        if e.tag == qn('w:lastRenderedPageBreak'):
            e.getparent().remove(e)
    for pe in list(el.iter(qn('w:proofErr'))):
        pe.getparent().remove(pe)
    return el


def con_runs(parrafo, partes):
    """Copia del párrafo con su pPr y una run por parte (negrita donde se pide)."""
    p = limpiar(copy.deepcopy(parrafo))
    runs = p.findall(qn('w:r'))
    normal = next(r for r in runs if r.find(qn('w:rPr')) is None or r.find(qn('w:rPr')).find(qn('w:b')) is None)
    negrita = next((r for r in runs if r.find(qn('w:rPr')) is not None and r.find(qn('w:rPr')).find(qn('w:b')) is not None), normal)
    for r in runs:
        p.remove(r)
    for txt, bold in partes:
        r = copy.deepcopy(negrita if bold else normal)
        for t in r.findall(qn('w:t')):
            r.remove(t)
        t = r.makeelement(qn('w:t'), {})
        t.text = txt
        t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
        r.append(t)
        p.append(r)
    return p


def poner_texto(tc, valor):
    p = tc.find(qn('w:p'))
    for extra in tc.findall(qn('w:p'))[1:]:
        tc.remove(extra)
    runs = p.findall(qn('w:r'))
    for r in runs[1:]:
        p.remove(r)
    r = runs[0]
    for t in r.findall(qn('w:t')):
        r.remove(t)
    t = r.makeelement(qn('w:t'), {})
    t.text = valor
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t)


def tabla(molde, filas):
    tbl = limpiar(copy.deepcopy(molde))
    trs = tbl.findall(qn('w:tr'))
    encabezado, fila_molde = trs[0], trs[1]
    for tr in trs[1:]:
        tbl.remove(tr)
    for fila in filas:
        tr = copy.deepcopy(fila_molde)
        for tc, valor in zip(tr.findall(qn('w:tc')), fila):
            poner_texto(tc, valor)
        tbl.append(tr)
    return tbl


plantilla = docx.Document(PLANTILLA)
_, molde = seccion(plantilla.element.body, 'Sprint 3')
p_intro = molde[0]
p_titulo = next(e for e in molde if e.tag == qn('w:p') and texto(e).startswith('encounter_prescription_items'))
t_molde = next(e for e in molde if e.tag == qn('w:tbl'))
p_blanco = next(e for e in molde if e.tag == qn('w:p') and texto(e) == '')
p_cierre = molde[-1]

doc = docx.Document(ENT)
titulo, actual = seccion(doc.element.body, 'Sprint 4')
assert titulo is not None, 'No se encontró el 2.1.2.2 del Sprint 4'
if any(texto(e) for e in actual) or any(e.tag == qn('w:tbl') for e in actual):
    sys.exit('El 2.1.2.2 del Sprint 4 ya tiene contenido: no se toca.')

nuevos = [con_runs(p_intro, INTRO)]
for nombre, que, filas in TABLAS:
    nuevos.append(con_runs(p_titulo, [(nombre, False), (f' — {que}', False)]))
    nuevos.append(tabla(t_molde, filas))
    nuevos.append(limpiar(copy.deepcopy(p_blanco)))
nuevos.append(con_runs(p_cierre, CIERRE))

ancla = titulo
for el in nuevos:
    ancla.addnext(el)
    ancla = el
doc.save(SAL)
print('tablas:', len(TABLAS), 'filas:', sum(len(f) for _, _, f in TABLAS), '->', SAL)
