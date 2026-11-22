"""Escribe el 2.2.1, el 2.3.1 y el 2.3.2 del Sprint 4 con el formato del Sprint 3.

Uso: python pruebas_sprint4.py PLANTILLA.docx ENTRADA.docx SALIDA.docx

PLANTILLA es el documento del grupo («Proyecto SI2 Grupo15.docx»), que tiene la
implementación y las pruebas del Sprint 3 hechas. De ahí se clonan los párrafos
y las tablas (componentes, convención, criterios, cobertura, ficha del caso de
uso, escenarios, estados, resumen y reporte por caso de uso), así el Sprint 4
sale con los mismos estilos. Se inserta debajo de los títulos «2.2.1», «2.3.1» y
«2.3.2» del Sprint 4 y no toca nada más. Si alguno ya tiene contenido, no hace
nada.

Las pruebas que se citan existen en backend/tests y mobile/test con ese nombre;
las capturas, en docs/capturas/sprint-4/.
"""
import copy
import sys

import docx
from docx.oxml.ns import qn

PLANTILLA, ENT, SAL = sys.argv[1], sys.argv[2], sys.argv[3]


# Los mismos ayudantes de mapeo_sprint4.py (ese script corre al importarse, por eso se copian).
def texto(el):
    return ''.join(t.text or '' for t in el.iter(qn('w:t'))).strip()


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


def _es_negrita(r):
    rpr = r.find(qn('w:rPr'))
    return rpr is not None and rpr.find(qn('w:b')) is not None


def con_runs(parrafo, partes):
    """Copia del párrafo con su pPr y una run por parte (negrita donde se pide)."""
    p = limpiar(copy.deepcopy(parrafo))
    runs = [r for r in p.iter(qn('w:r')) if r.find(qn('w:t')) is not None]
    normal = next((r for r in runs if not _es_negrita(r)), runs[0])
    negrita = next((r for r in runs if _es_negrita(r)), normal)
    normal, negrita = copy.deepcopy(normal), copy.deepcopy(negrita)
    for hijo in list(p):
        if hijo.tag != qn('w:pPr'):
            p.remove(hijo)
    for txt, bold in partes:
        r = copy.deepcopy(negrita if bold else normal)
        for hijo in list(r):
            if hijo.tag != qn('w:rPr'):
                r.remove(hijo)
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
    runs = [r for r in p.iter(qn('w:r')) if r.find(qn('w:t')) is not None]
    for r in runs[1:]:
        r.getparent().remove(r)
    r = runs[0]
    for hijo in list(r):
        if hijo.tag != qn('w:rPr'):
            r.remove(hijo)
    t = r.makeelement(qn('w:t'), {})
    t.text = valor
    t.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
    r.append(t)

KAREN = 'Karen Paola Ortega Mancilla'
MATEO = 'Luis Mateo Hurtado Castro'
MIGUEL = 'Luis Miguel Aguayo Quiroz'
ALEX = 'Alexander Osinaga Blanco'
DANIEL = 'José Daniel Iporo Chulque'

# ---------------------------------------------------------------------------
# 2.2.1 Componentes y artefactos generados
# ---------------------------------------------------------------------------
IMPL_INTRO = [
    ('Durante el Sprint 4 se incorporaron a la rama principal tres apps nuevas en el backend —', False),
    ('noshow', False), (' (riesgo de inasistencia y reentrenamiento), ', False),
    ('ai', False), (' (textos generados y su validación) y ', False),
    ('messaging', False),
    (' (chat con el médico)—, y se ampliaron encounters, appointments, payments y reporting, con sus pantallas '
     'en la web y en el móvil. La tabla identifica los archivos presentes en el repositorio al 22/11/26 y su '
     'relación con cada historia.', False),
]

IMPL = [
    ('US-35 — Riesgo de inasistencia por ficha',
     'noshow/ (models.py con ModelVersion y NoShowPrediction, features.py, training.py, scoring.py, views.py, '
     'permissions.py, migraciones 0001 a 0003, comandos train_noshow y score_noshow); '
     'tenancy/management/commands/seed_dataset.py y _causas_inasistencia.py; tenancy/plans.py; '
     'frontend/src/paginas/RiesgoInasistencia.tsx y api/riesgo.ts; scripts/start.sh',
     'GET /api/noshow/appointments/ y /api/noshow/model/ con el permiso noshow.prediction.read, sólo en el plan '
     'que incluye la predicción. Regresión logística por organización; la puntuación corre en segundo plano.'),
    ('US-36 — Recordatorios reforzados',
     'appointments/reminders.py, models.py, migración 0007 (reinforced_reminder_sent_at), '
     'management/commands/send_appointment_reminders.py; notifications/services.py; config/settings.py; '
     'scripts/start.sh',
     'Sin endpoint nuevo: el mismo proceso de US-28 manda el segundo aviso por push y correo a las fichas de '
     'riesgo alto, con su propia marca para no repetirlo.'),
    ('US-37 — Proyección de demanda',
     'reporting/demand.py, demand_views.py, urls.py; frontend/src/paginas/ProyeccionDemanda.tsx y api/demanda.ts',
     'GET /api/reporting/demand/ con reporting.kpi.read: promedio de las ocho semanas previas por especialidad '
     'y franja, con el error medido sobre semanas pasadas.'),
    ('US-38 — Reentrenamiento del modelo',
     'noshow/retraining.py, retrain_views.py, management/commands/retrain_noshow.py; '
     'frontend/src/paginas/RiesgoInasistencia.tsx (historial y motivo de rechazo); scripts/start.sh',
     'GET /api/noshow/versions/. retrain_noshow --all --loop corre una vez al día y sólo promueve la versión '
     'nueva si su Brier es mejor sobre las mismas fichas.'),
    ('US-39 — Resumen claro de la consulta',
     'ai/consultation_summary.py, services.py, views.py, serializers.py, comando '
     'evaluate_consultation_summary; encounters/views.py; frontend/src/paginas/Atencion.tsx y '
     'TextosPorValidar.tsx; mobile/lib/features/clinical_record/',
     'Al firmar se genera un borrador; POST /api/ai/encounters/{id}/summary/ lo reintenta. El paciente lo lee '
     'aprobado en GET /api/ai/texts/mine/.'),
    ('US-40 — Preparación para estudios',
     'ai/study_preparation.py, views.py, urls.py; encounters/views.py; frontend/src/paginas/Atencion.tsx y '
     'RecetaAtencion.tsx; mobile/lib/features/clinical_record/',
     'Un borrador por orden al firmar; POST /api/ai/orders/{id}/preparation/ lo reintenta. Sale del catálogo '
     'de la organización y el modelo sólo lo redacta.'),
    ('US-41 — Resumen del historial para el médico',
     'encounters/summary.py, history_views.py, urls.py; frontend/src/paginas/ResumenHistorial.tsx, '
     'Atencion.tsx y api/atencion.ts',
     'GET /api/encounters/history/{patient_id}/summary/: cada oración cita su atención y la que no cita se '
     'descarta. Sólo para el médico con vínculo de atención.'),
    ('US-42 — Validar o editar texto de IA',
     'ai/ (models.py con AIGeneratedText, services.py, serializers.py, views.py, migraciones 0001 a 0003); '
     'audit/actions.py; backups/manifest.py; frontend/src/paginas/TextosPorValidar.tsx y api/textos_ia.ts',
     'GET /api/ai/texts/, PATCH /api/ai/texts/{id}/, POST approve/ y discard/ con ai.text.validate. El trigger '
     'trg_ai_generated_texts_inmutable protege lo validado.'),
    ('US-46 — Transacciones por voz del paciente',
     'payments/mine.py, mine_voice.py, views_mine.py, permissions.py, urls.py; reporting/voice.py y '
     'exporters.py (QR en PDF); frontend/src/paginas/MisComprobantes.tsx y componentes/EntradaDeVoz.tsx; '
     'mobile/lib/features/receipts/',
     'POST /api/payments/mine/receipts/interpret/ propone la consulta; GET /api/payments/mine/receipts/ la '
     'ejecuta, sólo sobre el paciente y sus dependientes, en JSON o PDF.'),
    ('US-47 — Chat con el médico tratante',
     'messaging/ (models.py con EncounterThread y EncounterMessage, services.py, views.py, migraciones 0001 a '
     '0003); core/notifications/push.dart; frontend/src/paginas/ChatAtencion.tsx y api/chat.ts; '
     'mobile/lib/features/chat/',
     'GET /api/messaging/inbox/ y /encounters/{id}/chat/; POST messages/ y close/. Ventana de 15 días, barrera '
     'de urgencias y triggers que hacen inmutables los mensajes.'),
    ('US-48 — Calificación de la atención con estrellas',
     'encounters/ratings.py, rating_views.py, models.py, migraciones 0007 y 0008; reporting/kpi_views.py '
     '(satisfacción); frontend/src/paginas/CalificarAtencion.tsx y TarjetaSatisfaccion.tsx; '
     'mobile/lib/features/clinical_record/rating_card.dart',
     'POST y PATCH /api/encounters/{id}/rating/; GET /api/reporting/satisfaction/ para la administración. '
     'Corrección sólo durante 7 días, también en la base.'),
    ('US-49 — Recordatorio para tomar los medicamentos',
     'encounters/frequency.py, intakes.py, intake_views.py, migraciones 0009 y 0010; '
     'mobile/lib/features/medications/ (recordatorios.dart, recordarme.dart) y core/notifications/push.dart',
     'GET /api/encounters/medications/{patient_id}/ y POST /api/encounters/prescription/{item}/intakes/. Los '
     'avisos son notificaciones locales del celular, programadas desde la receta firmada.'),
    ('US-50 — Finanzas por voz y área de contabilidad',
     'reporting/finance.py, finance_views.py, finance_voice.py, models.py, migración 0004; catalog/ '
     '(fee_percent, migración 0008); tenancy/migrations/0008; frontend/src/paginas/Contabilidad.tsx y '
     'api/finanzas.ts',
     'GET /api/reporting/finance/summary/, series/ y export/; POST interpret/; gastos y configuración en '
     'expenses/ y settings/. Sólo Pro y Premium.'),
    ('US-51 — Plus en la compra de la ficha',
     'appointments/calendar.py, preconsultation_views.py, migración 0010, serializers.py; '
     'frontend/src/componentes/ExperienciaPlus.tsx y api/preconsulta.ts; '
     'mobile/lib/features/appointments/preconsulta_plus.dart',
     'GET /api/appointments/appointments/{id}/calendar.ics; GET y PUT preconsultation/. La ficha trae la '
     'dirección y el mapa de la sede, y el correo lleva el calendario.'),
    ('US-52 — Lista de espera con aviso de cupo liberado',
     'appointments/waitlist.py, waitlist_views.py, holds.py, changes.py, migraciones 0008 y 0009, comando '
     'process_waitlist; scheduling/availability.py; frontend/src/componentes/TarjetaListaEspera.tsx; '
     'mobile/lib/features/waitlist/',
     'GET y POST /api/appointments/waitlist/, DELETE waitlist/{id}/ y GET waitlist/summary/. Al cancelar, el '
     'turno se guarda para el primero que encaja y se le avisa.'),
    ('US-53 — Signos vitales con gráficas de evolución',
     'encounters/models.py (EncounterVitalSigns), serializers.py, services.py, migraciones 0011 a 0013; '
     'frontend/src/paginas/SignosVitales.tsx y signos_vitales.ts; mobile/lib/features/clinical_record/',
     'Se guardan con el borrador de la atención (PATCH /api/encounters/{id}/) y se leen en el historial. Lo '
     'firmado se corrige sólo con una enmienda.'),
]

# ---------------------------------------------------------------------------
# 2.3.1 Plan de pruebas
# ---------------------------------------------------------------------------
PLAN_INTRO = [('El plan define entradas, acciones y salidas esperadas para validar el comportamiento funcional '
               'con técnicas de caja negra. Cubre las dieciséis historias del Sprint 4, con un caso de uso cada '
               'una (CU36 a CU43 y CU47 a CU54).', False)]

CONVENCION = [('Convención de identificadores.', True),
              (' Se continúa la convención de los sprints anteriores: CP-<historia>-<número>. El número '
               'intermedio corresponde a la historia de usuario, no al caso de uso.', False)]

CRITERIOS = [
    ('Entorno', 'Backend Django REST Framework, clientes React y Flutter, y PostgreSQL con usuario de aplicación '
                'sin privilegios y aislamiento RLS. Las pruebas automatizadas corren sin claves de Gemini, de '
                'Firebase ni de Brevo: el proveedor de IA se simula o se prueba su ausencia, y no salen push ni '
                'correos reales. Los casos límite manuales se ejecutaron contra la API y la web locales, y el '
                'recorrido final en el celular, contra producción.'),
    ('Datos', 'Organizaciones, cuentas, pacientes y profesionales ficticios. El modelo de inasistencia se '
              'entrena con datos sintéticos de seis meses que siembra seed_dataset, con causas conocidas. No se '
              'usan datos clínicos reales.'),
    ('Técnicas', 'Partición de equivalencia, valores límite, tablas de decisión, transiciones de estado, pruebas '
                 'de autorización (otro paciente, otro médico, otro rol y otra organización) y, en lo clínico y '
                 'de seguridad, verificación por mutación.'),
    ('Resultado satisfactorio', 'La salida real coincide con la esperada y no se alteran datos fuera de la '
                                'operación autorizada.'),
    ('Resultado fallido', 'Se observa una diferencia verificable; debe registrarse el error, su evidencia y su '
                          'corrección.'),
    ('No ejecutado / pendiente', 'No hay evidencia suficiente para declarar satisfactorio o fallido el '
                                 'escenario.'),
]

# Cada caso de uso: código, nombre, historia, plataforma, descripción, precondiciones, responsable,
# situación (para el resumen) y escenarios (acción, resultado esperado, evidencia).
# La evidencia es una lista: nombres test_* (backend/tests), «móvil:archivo» (mobile/test),
# «captura:US-xx-nn» (docs/capturas/sprint-4) o «api:descripción» (verificado contra la API, 22/11/26).
CUS = [
    dict(cu='CU36', nombre='Predicción de Riesgo de Inasistencia', us='US-35', plat='Web', resp=MIGUEL,
         desc='El sistema clasifica cada ficha futura en riesgo bajo, medio o alto con un modelo entrenado por '
              'organización, y la administración lo ve y lo filtra.',
         pre='Organización con el plan que incluye la predicción, fichas con desenlace sembradas por '
             'seed_dataset, administrador con noshow.prediction.read y una segunda organización.',
         sit='Integrada (PR #108). 40 funciones de prueba en test_us35.py; capturas US-35-01 a 03.',
         esc=[
             ('Entrenar con los datos sembrados.', 'Se crea una versión que le gana a la línea base «siempre '
              'asiste» y recupera el signo de cada causa.',
              ['test_con_lo_que_siembra_seed_dataset_el_modelo_aprende_y_puntua',
               'test_el_modelo_redescubre_el_signo_de_las_causas']),
             ('Entrenar sin datos suficientes, o con un modelo que no supera la base.', 'No se crea versión o '
              'queda rechazada; nunca es la vigente, tampoco en la base.',
              ['test_sin_datos_suficientes_no_se_crea_ninguna_version',
               'test_un_modelo_nunca_es_vigente_si_no_le_gana_a_la_base',
               'test_un_modelo_que_no_supera_la_base_no_puede_ser_vigente']),
             ('Calcular las variables de una ficha.', 'No usan la propia ficha ni las posteriores (sin fuga de '
              'datos), y la etiqueta es la inasistencia de US-29.',
              ['test_las_variables_no_cuentan_la_propia_ficha_ni_las_posteriores',
               'test_la_etiqueta_es_la_inasistencia_de_us29']),
             ('Puntuar las fichas.', 'Sólo las futuras y activas, una vez cada una, con nivel y razones; sin '
              'modelo vigente no se inventa ninguna predicción.',
              ['test_solo_se_puntuan_las_fichas_futuras_y_activas',
               'test_puntuar_dos_veces_no_duplica_ni_repite_filas',
               'test_sin_modelo_vigente_no_se_inventa_ninguna_prediccion']),
             ('Ver y filtrar el riesgo en la web.', 'La administración ve sus fichas con el nivel y las filtra '
              'por nivel y sucursal.',
              ['test_la_administracion_ve_el_riesgo_de_sus_fichas', 'test_se_filtra_por_nivel_y_por_sucursal',
               'captura:US-35-02', 'captura:US-35-03']),
             ('Entrar como recepción, como paciente o sin sesión.', 'Se rechaza (403 o 401); el paciente no ve '
              'su propio riesgo.',
              ['test_recepcion_no_ve_el_riesgo', 'test_el_paciente_no_ve_su_propio_riesgo',
               'test_sin_sesion_no_se_ve_nada']),
             ('Pedir el riesgo desde otra organización o con el plan Básico.', 'No ve nada ajeno; el Básico '
              'recibe plan_limit.',
              ['test_una_organizacion_no_ve_las_predicciones_de_otra', 'test_el_plan_basico_recibe_plan_limit',
               'test_cada_organizacion_entrena_solo_con_sus_fichas']),
             ('Mandar parámetros inválidos.', 'Responde 400 con su código; una sucursal ajena no se acepta.',
              ['test_los_parametros_malos_responden_400_con_su_codigo',
               'test_una_sucursal_de_otra_organizacion_no_se_acepta']),
         ]),
    dict(cu='CU37', nombre='Envío de Recordatorios por Riesgo de Inasistencia', us='US-36', plat='Móvil (push) '
         'y correo', resp=ALEX,
         desc='A las fichas con riesgo alto se les envía un segundo recordatorio, más cerca de la hora, por push '
              'y por correo.',
         pre='Fichas confirmadas con predicción de US-35, el proceso de recordatorios de US-28 y dos '
             'organizaciones.',
         sit='Integrada (PR #109). 18 funciones de prueba en test_us36.py; sin capturas (decisión del equipo).',
         esc=[
             ('Correr el proceso con una ficha de riesgo alto.', 'Sale el refuerzo, más cerca de la hora que el '
              'primer recordatorio.',
              ['test_la_ficha_con_riesgo_alto_recibe_el_recordatorio_reforzado',
               'test_el_refuerzo_sale_mas_cerca_de_la_hora_que_el_primero']),
             ('Correr el proceso dos veces.', 'El refuerzo no se repite.',
              ['test_correr_dos_veces_no_repite_el_refuerzo']),
             ('Fichas de riesgo medio o bajo, o sin predicción.', 'No reciben refuerzo.',
              ['test_solo_el_riesgo_alto_recibe_el_refuerzo', 'test_sin_prediccion_no_hay_refuerzo',
               'test_sin_modelo_vigente_no_hay_refuerzo']),
             ('Organización sin el plan, o con los recordatorios apagados.', 'No sale el refuerzo.',
              ['test_sin_el_plan_que_incluye_la_prediccion_no_hay_refuerzo',
               'test_con_los_recordatorios_apagados_tampoco_sale_el_refuerzo']),
             ('Leer el texto del aviso.', 'No le dice al paciente cómo lo califica el centro; el correo pide '
              'confirmar sólo si no confirmó.',
              ['test_el_aviso_no_le_dice_al_paciente_como_lo_califica_el_centro',
               'test_el_correo_del_refuerzo_pide_confirmar_solo_si_no_confirmo']),
             ('Falla el envío de una organización o del refuerzo.', 'Las demás reciben el suyo y el primer '
              'recordatorio sale igual.',
              ['test_si_una_organizacion_falla_las_demas_reciben_su_refuerzo',
               'test_si_falla_el_refuerzo_el_primer_recordatorio_sale_igual']),
             ('Dos organizaciones con fichas de riesgo alto.', 'Cada una refuerza sólo sus fichas, a sus '
              'teléfonos.', ['test_cada_organizacion_refuerza_solo_sus_fichas_a_sus_telefonos']),
         ]),
    dict(cu='CU38', nombre='Proyección de Demanda de Fichas', us='US-37', plat='Web', resp=DANIEL,
         desc='La administración ve cuántas fichas se esperan por especialidad y franja en las próximas semanas, '
              'junto a la ocupación y al error medido sobre semanas pasadas.',
         pre='Organización con fichas de al menos ocho semanas, administrador con reporting.kpi.read y una '
             'segunda organización.',
         sit='Integrada (PR #113). Una prueba automatizada del corte de semanas; el resto verificado contra la '
             'API el 22/11/26 y con las capturas US-37-01 y 02.',
         esc=[
             ('Pedir la proyección como administrador.', 'Devuelve el método, las ocho semanas de historia, las '
              'filas por especialidad y franja, y la validación.',
              ['api:GET /api/reporting/demand/ → 200', 'captura:US-37-01', 'captura:US-37-02']),
             ('Comprobar que la validación no usa la semana que proyecta.', 'Cada semana evaluada usa sólo las '
              'ocho anteriores.', ['test_backtest_no_usa_semana_objetivo']),
             ('Pedir 0, 9 o «abc» semanas, y luego 1 y 8.', 'Los tres primeros responden 400 invalid_weeks; '
              '1 y 8 se aceptan.', ['api:weeks=0, 9 y abc → 400; 1 y 8 → 200']),
             ('Filtrar por una sucursal malformada o de otra organización.', 'Responde 400 invalid_branch.',
              ['api:branch malformada y branch de scsalud → 400']),
             ('Entrar como recepción, como paciente o sin sesión.', 'Recepción y paciente reciben 403; sin '
              'sesión, 401.', ['api:recepción y paciente → 403; sin sesión → 401']),
         ]),
    dict(cu='CU39', nombre='Reentrenamiento del Modelo de No-Show', us='US-38', plat='Web', resp=DANIEL,
         desc='El modelo se vuelve a entrenar con los desenlaces nuevos y sólo reemplaza al vigente si mejora el '
              'Brier sobre las mismas fichas posteriores a su entrenamiento.',
         pre='Organización con un modelo vigente (US-35), desenlaces nuevos y el proceso diario retrain_noshow.',
         sit='Integrada (PR #113, #134 y #135). 5 pruebas automatizadas; corrido en producción el 22/11/26 '
             '(captura US-38-01).',
         esc=[
             ('Reentrenar sin desenlaces nuevos suficientes.', 'No se entrena (skipped).',
              ['test_retrain_sin_desenlaces_nuevos_no_entrena']),
             ('Comparar el candidato con el vigente.', 'Los dos se miden con el Brier sobre las mismas fichas.',
              ['test_comparacion_brier_mismas_fichas']),
             ('El candidato es peor que el vigente.', 'Queda rechazado y el vigente no cambia.',
              ['test_candidato_peor_se_rechaza_sin_promocion']),
             ('Reentrenar en producción con --all.', 'urbari conserva su versión 1 y la 2 queda rechazada con '
              'el motivo en la pantalla; la tarea diaria queda lanzada por scripts/start.sh.',
              ['captura:US-38-01', 'prod:retrain_noshow --all del 22/11/26']),
             ('Ver el historial sin sesión, como recepción o desde otra organización.', 'Sin sesión 401; '
              'recepción y paciente 403; no se ven versiones de otra organización.',
              ['test_historial_requiere_autenticacion', 'test_historial_no_filtra_otra_organizacion',
               'api:recepción y paciente → 403']),
         ]),
    dict(cu='CU40', nombre='Generación de Resumen de Consulta mediante IA', us='US-39', plat='Web / móvil',
         resp=KAREN,
         desc='Al firmar la atención se genera un resumen en lenguaje llano que el paciente lee después de que '
              'el médico lo aprueba.',
         pre='Atención firmada con su receta, médico tratante, proveedor de IA simulado o ausente y una segunda '
             'organización.',
         sit='Integrada (PR #105). 18 funciones de prueba en test_us39.py y clinical_record_test.dart en el '
             'móvil; capturas US-39-01 y 02.',
         esc=[
             ('Firmar una atención.', 'Se genera un borrador para el médico; al modelo le llega sólo esa '
              'atención, sin el nombre ni el documento.',
              ['test_al_firmar_se_genera_un_borrador_para_el_medico',
               'test_al_modelo_le_llega_solo_esta_atencion_sin_quien_es']),
             ('Firmar sin proveedor o con el modelo caído.', 'No se genera y se dice; la atención queda firmada '
              'igual.', ['test_sin_proveedor_no_se_genera_y_se_dice',
                         'test_si_el_modelo_falla_la_atencion_queda_firmada']),
             ('Reintentar la generación.', 'Genera si antes no se pudo; nunca deja dos resúmenes vivos.',
              ['test_reintentar_genera_cuando_no_se_pudo_al_firmar', 'test_no_se_generan_dos_resumenes_vivos',
               'test_descartado_se_puede_volver_a_generar']),
             ('Otro médico u otra organización reintentan.', 'Se rechaza.',
              ['test_otro_medico_no_lo_reintenta', 'test_otra_organizacion_no_lo_reintenta']),
             ('El evaluador revisa el texto.', 'Detecta lo inventado y exige remitir al médico.',
              ['test_el_evaluador_detecta_lo_inventado', 'test_el_evaluador_exige_remitir_al_medico_sin_plazo']),
             ('El paciente abre su atención.', 'Lo lee sólo aprobado, en la web y en el móvil.',
              ['test_el_paciente_lo_lee_solo_aprobado', 'test_el_filtro_por_paciente_no_abre_a_otro',
               'móvil:clinical_record_test.dart', 'captura:US-39-02']),
         ]),
    dict(cu='CU41', nombre='Generación de Indicaciones de Preparación', us='US-40', plat='Web / móvil',
         resp=MATEO,
         desc='Para cada orden de laboratorio o imagen se genera la preparación desde el catálogo de la '
              'organización, y el paciente la ve aprobada junto a la orden.',
         pre='Atención con órdenes, catálogo de servicios con preparación cargada, proveedor simulado o ausente '
             'y una segunda organización.',
         sit='Integrada (PR #116). 20 funciones de prueba en test_us40.py; capturas US-40-01 a 03, dos en '
             'producción.',
         esc=[
             ('Firmar una atención con dos órdenes.', 'Se genera un borrador por orden; al modelo le llegan el '
              'estudio y la fuente, sin el paciente.',
              ['test_al_firmar_se_genera_un_borrador_por_orden', 'test_dos_ordenes_dos_preparaciones',
               'test_al_modelo_le_llega_el_estudio_y_la_fuente_sin_quien_es']),
             ('El catálogo no tiene preparación para el estudio.', 'No se inventa una; tampoco cuenta un '
              'servicio inactivo, vacío o de otra organización.',
              ['test_sin_fuente_no_se_inventa', 'test_no_cuenta_un_servicio_inactivo_vacio_o_de_otro_estudio',
               'test_el_catalogo_de_otra_organizacion_no_cuenta']),
             ('Sin proveedor o con el modelo caído.', 'Queda el texto del catálogo y la firma no se cae.',
              ['test_sin_proveedor_queda_el_texto_del_catalogo',
               'test_si_el_modelo_falla_queda_el_catalogo_y_la_firma',
               'test_una_falla_inesperada_no_tumba_la_firma']),
             ('El modelo cambia un número de la fuente.', 'La bandeja lo advierte al médico.',
              ['test_la_bandeja_avisa_los_numeros_que_no_estan_en_la_fuente',
               'test_las_advertencias_comparan_numeros_con_la_fuente']),
             ('Otro médico u otra organización la reintentan.', 'Se rechaza.',
              ['test_otro_medico_del_centro_no_la_reintenta', 'test_otra_organizacion_no_la_reintenta']),
             ('El paciente abre la orden.', 'La lee sólo aprobada y junto a su orden.',
              ['test_el_paciente_la_lee_solo_aprobada_y_junto_a_su_orden', 'captura:US-40-01',
               'captura:US-40-02']),
         ]),
    dict(cu='CU42', nombre='Generación de Resumen de Historia Clínica', us='US-41', plat='Web', resp=MATEO,
         desc='Antes de una consulta, el médico lee una síntesis del historial en la que cada oración cita la '
              'atención de la que sale.',
         pre='Paciente con atenciones firmadas y alergias declaradas, médico con ficha con el paciente y otro '
             'sin ella, y una segunda organización.',
         sit='Integrada (PR #99). 16 funciones de prueba en test_us41.py, verificadas por mutación; capturas '
             'US-41-01 y 02.',
         esc=[
             ('El modelo devuelve oraciones sin cita o con una cita inventada.', 'Se descartan; sólo queda lo '
              'citado.', ['test_la_oracion_sin_cita_o_con_cita_inventada_se_descarta',
                          'test_la_cita_cero_no_existe', 'test_con_gemini_devuelve_solo_lo_citado']),
             ('El modelo no cita nada, falla o no hay proveedor.', 'Cae a la plantilla con los diagnósticos tal '
              'cual.', ['test_si_el_modelo_no_cita_nada_cae_a_la_plantilla',
                        'test_si_el_proveedor_falla_cae_a_la_plantilla',
                        'test_sin_proveedor_copia_los_diagnosticos_tal_cual']),
             ('El paciente tiene alergias graves.', 'Salen de la base, las graves primero, aunque el modelo no '
              'las mencione.', ['test_las_alergias_salen_de_la_base_y_las_graves_primero']),
             ('Paciente sin atenciones firmadas, o con una enmienda.', 'Sin atenciones no hay resumen; la '
              'enmienda llega al resumen.', ['test_sin_atenciones_firmadas_no_hay_resumen',
                                             'test_la_enmienda_llega_al_resumen']),
             ('Lo pide el paciente, un médico sin ficha u otra organización.', 'No lo reciben.',
              ['test_el_paciente_no_recibe_el_resumen_aunque_lea_su_historial',
               'test_un_medico_sin_ficha_con_el_paciente_no_lo_recibe', 'test_otra_organizacion_no_lo_recibe']),
             ('Un médico es dado de baja.', 'Pierde el acceso en el acto.',
              ['test_un_medico_dado_de_baja_lo_pierde_en_el_acto']),
         ]),
    dict(cu='CU43', nombre='Validación de Contenido Generado por IA', us='US-42', plat='Web', resp=KAREN,
         desc='Ningún texto generado llega al paciente sin que un médico lo apruebe: lo lee, lo corrige, lo '
              'aprueba o lo descarta desde una bandeja.',
         pre='Textos en borrador de US-39, US-40 y US-41, médico autor, otro médico del centro, paciente con '
             'dependiente y una segunda organización.',
         sit='Integrada (PR #102 y #104). 53 funciones de prueba en test_us42.py y test_us42_bordes.py; '
             'capturas US-42-01 a 03.',
         esc=[
             ('El médico abre su bandeja.', 'Ve sus pendientes y filtra por estado; otro médico no los ve.',
              ['test_el_medico_ve_sus_pendientes', 'test_la_bandeja_filtra_por_estado',
               'test_otro_medico_del_centro_no_lo_ve_ni_lo_aprueba', 'captura:US-42-02']),
             ('Corregir y aprobar.', 'Se guardan el texto del modelo, el corregido y la diferencia.',
              ['test_corregir_guarda_los_dos_textos_y_la_diferencia', 'test_aprobar_con_correccion',
               'captura:US-42-01']),
             ('Aprobar vacío, sólo con espacios o por encima del tope.', 'Se rechaza con 400; el tope exacto se '
              'acepta.', ['test_no_se_aprueba_con_un_texto_vacio_o_de_espacios',
                          'test_no_se_aprueba_con_un_texto_mas_largo_que_el_tope',
                          'test_el_texto_del_tope_exacto_se_acepta']),
             ('Volver a decidir algo aprobado o descartado.', 'Se rechaza, también en la base.',
              ['test_lo_decidido_no_se_vuelve_a_decidir', 'test_lo_aprobado_no_se_descarta_ni_se_corrige',
               'test_la_base_no_deja_tocar_lo_aprobado', 'test_la_base_no_deja_borrar']),
             ('El paciente pide sus textos.', 'Ve sólo lo aprobado, nunca el borrador ni lo descartado; el '
              'titular ve los de su dependiente.',
              ['test_el_paciente_no_ve_el_borrador', 'test_el_paciente_no_ve_lo_descartado',
               'test_el_paciente_ve_solo_el_texto_aprobado', 'test_el_titular_ve_los_de_su_dependiente']),
             ('Otro paciente u otra organización.', 'No ve ni aprueba nada; la RLS esconde los textos.',
              ['test_un_paciente_no_ve_los_textos_de_otro', 'test_otra_organizacion_no_ve_ni_aprueba',
               'test_la_rls_esconde_los_textos_de_otra_organizacion']),
             ('Identificadores malformados o inexistentes.', 'Responde 404 o lista vacía, nunca 500.',
              ['test_el_paciente_con_una_atencion_malformada_no_rompe', 'test_un_texto_que_no_existe_da_404']),
             ('Restaurar una copia de respaldo.', 'Lleva los textos y no deshace una aprobación.',
              ['test_la_copia_lleva_los_textos_y_restaurar_no_los_cambia',
               'test_un_borrador_de_la_copia_no_deshace_la_aprobacion']),
         ]),
    dict(cu='CU47', nombre='Consulta de Transacciones por Voz', us='US-46', plat='Web / móvil', resp=ALEX,
         desc='El paciente pide, hablando o escribiendo, «mis últimas 2 facturas» o «mis fichas de cardiología» '
              'y ve la lista con el QR del comprobante de cada una.',
         pre='Paciente con pagos y fichas, titular con dependiente, otro titular, especialidades del centro y '
             'proveedor de IA simulado o ausente.',
         sit='Integrada (PR #110). 146 funciones de prueba en test_us46.py y 2 archivos del móvil; capturas '
             'US-46-01 a 03.',
         esc=[
             ('Decir «mis últimas 2 facturas».', 'Se proponen pagos con cantidad dos y la lista trae el QR '
              'firmado de cada comprobante.',
              ['test_ultimas_dos_facturas_son_pagos_con_cantidad_dos',
               'test_lista_los_pagos_con_comprobante_y_su_qr_firmado', 'captura:US-46-01']),
             ('Pedir por mes, rango de meses o especialidad.', 'Se entiende el período y la especialidad del '
              'centro, sin tildes ni mayúsculas.',
              ['test_los_pagos_de_octubre_son_el_mes_completo_del_ano_actual',
               'test_un_rango_de_meses_se_entiende_de_tres_maneras',
               'test_la_especialidad_se_reconoce_sin_tildes_ni_mayusculas', 'captura:US-46-02']),
             ('Decir algo que no se entiende o no se puede pedir.', 'Se dice y no se ejecuta.',
              ['test_lo_que_hoy_no_se_puede_pedir_se_dice_y_no_se_ejecuta',
               'test_texto_vacio_dice_que_no_se_escucho_nada', 'test_un_rango_al_reves_no_se_entiende']),
             ('Pedir lo de otro paciente, por frase o por la URL.', 'Nunca aparece nada ajeno, tampoco en el '
              'PDF.', ['test_un_paciente_nunca_ve_lo_de_otro_aunque_la_frase_lo_pida',
                       'test_los_parametros_de_persona_en_la_url_no_tienen_efecto',
                       'test_el_dependiente_de_otro_titular_no_aparece_ni_en_pdf']),
             ('El modelo devuelve algo inventado o fuera de la lista.', 'No se ejecuta; si el proveedor falla '
              'se usa el analizador local.',
              ['test_el_modelo_con_algo_inventado_o_invalido_no_ejecuta',
               'test_el_modelo_no_puede_cambiar_de_quien_son_los_datos',
               'test_si_el_proveedor_falla_se_degrada_al_analizador_local']),
             ('El titular pide lo suyo y lo de su dependiente.', 'Aparecen los dos, con el nombre de cada uno.',
              ['test_incluye_al_titular_y_a_sus_dependientes_con_el_nombre_de_cada_uno']),
             ('Bajar el PDF.', 'Sale de la misma consulta, con los QR dibujados, y deja asiento sin la frase.',
              ['test_el_pdf_y_el_json_salen_de_la_misma_consulta',
               'test_el_pdf_con_qr_es_un_pdf_valido_y_dibuja_los_codigos',
               'test_interpretar_deja_asiento_sin_la_frase_dictada', 'captura:US-46-03']),
             ('Entrar sin sesión o como personal sin perfil de paciente.', '401 y 403.',
              ['test_sin_sesion_es_401', 'test_el_personal_sin_perfil_de_paciente_recibe_403']),
         ]),
    dict(cu='CU48', nombre='Chat con el Médico Tratante', us='US-47', plat='Web / móvil', resp=MATEO,
         desc='El paciente atendido le escribe al médico que lo atendió sobre la medicación o las indicaciones '
              'de esa atención, y el médico le responde desde la web.',
         pre='Atención firmada, su paciente y el médico firmante, otro paciente, otro médico, titular con '
             'dependiente y una segunda organización.',
         sit='Integrada (PR #106, #107, #111 y #119). 32 funciones de prueba en test_us47.py, verificadas por '
             'mutación, y chat_test.dart; 35 capturas, cinco en producción.',
         esc=[
             ('El paciente pregunta y el médico responde.', 'La conversación muestra la receta y el aviso; la '
              'respuesta avisa por push sin el texto.',
              ['test_paciente_pregunta_y_el_medico_responde', 'test_la_conversacion_muestra_la_receta_y_el_aviso',
               'test_la_respuesta_del_medico_avisa_al_paciente_sin_el_texto', 'captura:US-47-07',
               'captura:US-47-22']),
             ('Abrir el chat de una atención en borrador.', 'No tiene chat.',
              ['test_una_atencion_en_borrador_no_tiene_chat']),
             ('Otro paciente, otro médico u otra organización.', 'No entran; la RLS esconde las conversaciones.',
              ['test_otro_paciente_no_entra', 'test_otro_medico_del_centro_no_entra',
               'test_otra_organizacion_no_entra', 'test_la_rls_esconde_las_conversaciones_de_otra_organizacion',
               'captura:US-47-09']),
             ('Escribir pasados los 15 días o con la conversación cerrada.', 'Nadie escribe; cerrar dos veces '
              'da 409 y el paciente no puede cerrar.',
              ['test_vencida_la_ventana_nadie_escribe', 'test_el_medico_la_cierra_y_nadie_escribe',
               'test_cerrar_dos_veces_da_409', 'test_el_paciente_no_puede_cerrar', 'captura:US-47-25']),
             ('El paciente describe una urgencia.', 'Se guarda marcada y el paciente ve primero la derivación a '
              'emergencias.', ['test_una_urgencia_se_guarda_marcada_y_trae_la_derivacion',
                               'test_el_mensaje_del_medico_nunca_se_marca', 'captura:US-47-08']),
             ('Mandar un mensaje vacío o de más de 2.000 caracteres.', 'Se rechaza, también en el servicio.',
              ['test_no_se_manda_un_mensaje_vacio', 'test_el_tope_de_largo', 'test_el_servicio_tambien_pone_el_tope',
               'captura:US-47-18', 'captura:US-47-19']),
             ('Editar o borrar un mensaje, o reabrir una conversación.', 'La base lo impide.',
              ['test_la_base_no_deja_editar_ni_borrar_un_mensaje',
               'test_la_base_no_deja_borrar_ni_reabrir_una_conversacion']),
             ('Falla el push.', 'El mensaje queda guardado.', ['test_si_el_push_falla_el_mensaje_queda']),
             ('Un mensaje con una palabra muy larga o con un <script>.', 'Se muestra como texto y la burbuja '
              'no se rompe (corregido en el PR #137).', ['captura:US-47-35']),
         ]),
    dict(cu='CU49', nombre='Calificación de la Atención', us='US-48', plat='Web / móvil', resp=KAREN,
         desc='El paciente atendido califica su atención de 1 a 5 estrellas con un comentario opcional, y la '
              'administración ve los promedios.',
         pre='Atención firmada, su paciente, titular con dependiente, médico, administrador y una segunda '
             'organización.',
         sit='Integrada (PR #115 y #119). 31 funciones de prueba en test_us48.py y rating_test.dart; capturas '
             'US-48-01 a 05.',
         esc=[
             ('Calificar con o sin comentario.', 'Se guarda y aparece en el historial propio.',
              ['test_el_paciente_califica_su_atencion', 'test_el_comentario_es_opcional',
               'test_el_historial_propio_trae_la_calificacion', 'captura:US-48-05']),
             ('Calificar una atención ajena, un borrador o como médico.', 'Se rechaza.',
              ['test_no_se_califica_una_atencion_ajena', 'test_no_se_califica_un_borrador',
               'test_el_medico_no_califica_aunque_lea_el_historial']),
             ('Mandar 0, 6, «abc» estrellas o un comentario de 501 caracteres.', 'Responde 400; la base tampoco '
              'acepta estrellas fuera de rango.', ['test_estrellas_fuera_de_rango_o_no_numericas',
                                                   'test_un_comentario_de_501_caracteres',
                                                   'test_la_base_no_deja_estrellas_fuera_de_rango']),
             ('Calificar dos veces.', 'Se rechaza.', ['test_no_se_califica_dos_veces']),
             ('Corregir dentro y fuera de los 7 días.', 'Dentro se acepta; fuera se rechaza, también en la base.',
              ['test_se_corrige_dentro_de_los_7_dias', 'test_pasados_los_7_dias_no_se_corrige',
               'test_pasados_los_7_dias_la_base_tampoco_deja']),
             ('El médico ve su promedio.', 'Ve el suyo, nunca el nombre del paciente ni las estrellas de otro.',
              ['test_el_medico_ve_su_promedio', 'test_el_medico_no_ve_el_nombre_del_paciente_en_ningun_endpoint',
               'test_otro_medico_no_ve_las_estrellas_ajenas', 'captura:US-48-03']),
             ('La administración abre el tablero.', 'Ve promedios y distribución, filtra por sede y los '
              'comentarios no traen al paciente.',
              ['test_el_admin_ve_promedios_y_distribucion', 'test_el_admin_filtra_por_sede',
               'test_los_comentarios_del_admin_no_traen_al_paciente']),
             ('Calificar en el celular.', 'El botón Enviar aparece y la calificación se envía (defecto '
              'corregido en el PR #119).', ['móvil:rating_test.dart', 'captura:US-48-01', 'captura:US-48-02']),
         ]),
    dict(cu='CU50', nombre='Recordatorio de Toma de Medicamentos', us='US-49', plat='Móvil (el médico, web)',
         resp=KAREN,
         desc='A partir de la receta firmada, la aplicación avisa al paciente cuándo tomar cada medicamento, y el '
              'médico ve qué parte del tratamiento se cumplió.',
         pre='Receta firmada con frecuencias y duración, paciente con el celular, titular con dependiente y una '
             'segunda organización.',
         sit='Integrada (PR #118 y #119). 24 funciones de prueba en test_us49.py y medications_test.dart; '
             'capturas US-49-01 a 05.',
         esc=[
             ('Leer la frecuencia de cada ítem.', 'Se entienden las frecuencias; sin horario fijo o sin duración '
              'no se inventa uno.', ['test_frecuencias_que_se_entienden',
                                     'test_frecuencias_sin_horario_fijo_no_inventan_uno',
                                     'test_sin_duracion_no_hay_horario']),
             ('Activar «Recordarme» en el celular.', 'Se programan los avisos y se ve la próxima toma.',
              ['móvil:medications_test.dart', 'captura:US-49-02', 'captura:US-49-03']),
             ('Marcar una toma.', 'Queda marcada, también desde la notificación.',
              ['test_el_paciente_marca_una_toma', 'test_mis_medicamentos_trae_las_tomas_marcadas',
               'captura:US-49-05']),
             ('Marcar dos veces, fuera del horario o con un estado inexistente.', 'Se rechaza; la base no deja '
              'dos veces la misma toma.', ['test_marcar_dos_veces_la_misma_toma', 'test_una_toma_fuera_del_horario',
                                           'test_un_estado_que_no_existe',
                                           'test_la_base_no_deja_dos_veces_la_misma_toma']),
             ('Marcar una toma ajena, de un borrador o como médico.', 'Se rechaza.',
              ['test_no_se_marca_una_toma_de_una_receta_ajena', 'test_no_se_marca_una_toma_de_un_borrador',
               'test_el_medico_no_marca_tomas']),
             ('Cambiar o borrar una toma marcada.', 'La base lo impide.',
              ['test_la_base_no_deja_cambiar_ni_borrar_una_toma']),
             ('El médico abre el historial.', 'Ve el cumplimiento del tratamiento.',
              ['test_el_medico_ve_el_cumplimiento_en_el_historial']),
             ('Otra organización.', 'No marca ni ve las tomas.',
              ['test_otra_organizacion_no_marca', 'test_otra_organizacion_no_ve_las_tomas']),
         ]),
    dict(cu='CU51', nombre='Consulta Financiera por Voz y Contabilidad', us='US-50', plat='Web', resp=ALEX,
         desc='La administración consulta ingresos, gastos y utilidad en una pantalla de contabilidad y '
              'hablando («¿cuánto ganamos este mes?»).',
         pre='Organización Pro o Premium con pagos en línea y en efectivo, gastos, honorarios de profesionales, '
             'administrador con los permisos de finanzas y una organización Básico.',
         sit='Integrada (PR #121). 52 funciones de prueba en test_us50.py; capturas US-50-01 y 02.',
         esc=[
             ('Ver el resumen del período.', 'La utilidad coincide con la suma a mano: el efectivo no paga '
              'comisión y lo devuelto tampoco.',
              ['test_la_utilidad_se_suma_a_mano', 'test_el_efectivo_no_paga_comision_y_lo_devuelto_tampoco',
               'captura:US-50-02']),
             ('Un período sin datos o con varias monedas.', 'Da cero sin error y cada moneda va por separado.',
              ['test_un_periodo_sin_datos_da_cero_y_no_error', 'test_cada_moneda_va_por_separado']),
             ('Agrupar por sede, médico o especialidad.', 'La suma de los grupos es el total.',
              ['test_la_suma_de_los_grupos_es_el_total', 'test_por_medico_y_por_especialidad']),
             ('Preguntar «¿cuánto ganamos este mes?».', 'Responde la utilidad del mes con una frase.',
              ['test_cuanto_ganamos_este_mes_es_la_utilidad_del_mes', 'captura:US-50-01']),
             ('Una frase que no se entiende o una respuesta rara del modelo.', 'Se dice y no se ejecuta.',
              ['test_lo_que_no_se_entiende_se_dice_y_no_se_ejecuta',
               'test_una_respuesta_rara_del_modelo_no_ejecuta_nada']),
             ('Cargar, editar y borrar un gasto; mandar uno inválido.', 'Queda asiento; el inválido o de una '
              'sucursal ajena se rechaza.', ['test_cargar_editar_y_borrar_un_gasto_deja_asiento',
                                             'test_un_gasto_con_datos_malos_se_rechaza',
                                             'test_un_gasto_no_se_cuelga_de_la_sucursal_de_otra_organizacion']),
             ('Una comisión o un honorario fuera de 0 a 100.', 'Se rechaza.',
              ['test_la_comision_fuera_de_rango_se_rechaza', 'test_el_honorario_tiene_que_estar_entre_0_y_100']),
             ('Entrar sin el permiso, con el plan Básico o desde otra organización.', '403, plan_limit y nada '
              'ajeno.', ['test_quien_no_tiene_el_permiso_recibe_403', 'test_el_plan_basico_no_incluye_la_contabilidad',
                         'test_otra_organizacion_no_se_ve']),
         ]),
    dict(cu='CU52', nombre='Complemento de la Compra de Ficha', us='US-51', plat='Web / móvil', resp=DANIEL,
         desc='Después de pagar, el paciente recibe además del comprobante el evento de calendario, cómo llegar a '
              'la sede y una preconsulta que el médico lee en la atención.',
         pre='Ficha pagada y vigente, sede con y sin coordenadas, titular con dependiente y otro paciente.',
         sit='Integrada (PR #127, #128 y #129). 15 funciones de prueba en test_us51.py y test_us51_plus.py y '
             'preconsulta_plus_test.dart; capturas US-51-01 a 04.',
         esc=[
             ('Bajar el calendario de la ficha.', 'Es un .ics válido en hora de La Paz, sin líneas de más de 75 '
              'octetos.', ['test_el_titular_baja_un_ics_valido_en_hora_de_la_paz',
                           'test_ninguna_linea_pasa_de_75_octetos']),
             ('Bajar el calendario de una ficha ajena o sin pagar.', 'No se baja.',
              ['test_el_ics_de_una_ficha_ajena_no_se_baja', 'test_sin_ficha_pagada_y_vigente_no_hay_ics']),
             ('Ver cómo llegar.', 'La ficha trae la dirección y el mapa; sin coordenadas no hay mapa.',
              ['test_la_ficha_trae_la_direccion_y_el_mapa', 'test_una_sede_sin_coordenadas_no_tiene_mapa',
               'captura:US-51-02']),
             ('Recibir el correo de la compra.', 'Trae el calendario adjunto y cómo llegar.',
              ['test_el_correo_trae_el_calendario_adjunto_y_como_llegar']),
             ('Completar la preconsulta.', 'Se guarda con su límite; el médico la ve en la atención.',
              ['test_guardar_y_leer_preconsulta', 'test_campos_tienen_limite',
               'test_el_medico_ve_la_preconsulta_en_la_atencion', 'captura:US-51-04']),
             ('Leer o editar la preconsulta ajena, sin pagar o después de la atención.', 'Se rechaza.',
              ['test_no_puede_leer_ni_editar_la_preconsulta_ajena', 'test_reserva_sin_pagar_no_tiene_preconsulta',
               'test_no_se_edita_despues_de_atencion']),
             ('Ver el plus en el celular.', 'Muestra la cuenta regresiva, el calendario y el mapa.',
              ['móvil:preconsulta_plus_test.dart', 'captura:US-51-01']),
         ]),
    dict(cu='CU53', nombre='Gestión de Lista de Espera', us='US-52', plat='Web / móvil', resp=MIGUEL,
         desc='Sin turno libre, el paciente se anota en lista de espera; si alguien cancela, el turno se le '
              'guarda al primero que encaja y se le avisa.',
         pre='Organización Pro sin turnos libres, varios pacientes anotados, titular con dependiente, el proceso '
             'process_waitlist y una organización Básico.',
         sit='Integrada (PR #114). 56 funciones de prueba en test_us52.py y waitlist_test.dart; capturas '
             'US-52-01 a 04.',
         esc=[
             ('Anotarse sin turnos libres.', 'Se crea la entrada y dice la posición, por orden de llegada.',
              ['test_anotarse_crea_la_entrada_y_dice_su_posicion', 'test_la_posicion_sigue_el_orden_de_llegada',
               'captura:US-52-02']),
             ('Anotarse dos veces, con turno libre o con un rango inválido.', 'Se rechaza.',
              ['test_no_se_puede_anotar_dos_veces_al_mismo_profesional',
               'test_si_hay_turno_libre_no_tiene_sentido_anotarse',
               'test_un_rango_en_el_pasado_o_invertido_no_se_acepta']),
             ('Alguien cancela.', 'El turno se guarda para el primero y se le avisa; si dos compiten, sólo uno se '
              'lo queda.', ['test_cancelar_le_guarda_el_turno_al_primero_y_le_avisa',
                            'test_dos_pacientes_compiten_por_el_mismo_cupo_y_solo_uno_se_lo_queda']),
             ('El turno guardado vence.', 'Pasa al siguiente; si nadie espera, vuelve a estar libre.',
              ['test_el_turno_guardado_vence_y_pasa_al_siguiente',
               'test_si_nadie_mas_espera_el_turno_vuelve_a_estar_libre']),
             ('Pagar el turno ofrecido, o pagarlo tarde.', 'Cierra la entrada; el pago tardío se devuelve.',
              ['test_pagar_el_turno_ofrecido_cierra_la_entrada',
               'test_un_pago_tardio_sobre_la_reserva_vencida_se_devuelve']),
             ('Especialidad, sucursal o fechas que no encajan.', 'No se le ofrece el turno.',
              ['test_una_especialidad_distinta_no_recibe_el_turno', 'test_la_sucursal_pedida_se_respeta',
               'test_fuera_del_rango_de_fechas_no_se_ofrece']),
             ('Anotarse por un ajeno, sin ser paciente o con el plan Básico.', 'Se rechaza.',
              ['test_anotarse_por_un_dependiente_y_no_por_un_ajeno', 'test_quien_no_es_paciente_no_se_anota',
               'test_el_basico_no_tiene_lista_de_espera']),
             ('Falla el push o el proceso al ofrecer.', 'La cancelación queda y la oferta se reintenta.',
              ['test_si_el_push_falla_la_cancelacion_y_la_oferta_siguen',
               'test_un_error_al_ofrecer_no_deshace_la_cancelacion',
               'test_una_oferta_que_fallo_se_reintenta_en_la_vuelta_siguiente']),
             ('La administración ve el resumen.', 'Anotados, tomados y tasa de recuperación, sólo de su '
              'organización.', ['test_el_resumen_cuenta_anotados_tomaron_y_la_tasa_de_recuperacion',
                                'test_el_resumen_es_solo_de_administracion_y_de_su_organizacion']),
         ]),
    dict(cu='CU54', nombre='Registro de Signos Vitales', us='US-53', plat='Web / móvil', resp=MATEO,
         desc='En la atención se registran los signos vitales como números, y el médico y el paciente ven su '
              'evolución de una consulta a otra.',
         pre='Atención en borrador y otra firmada, médico tratante, otro médico, el paciente y una segunda '
             'organización.',
         sit='Integrada (PR #120 y #122). 34 funciones de prueba en test_us53.py; 13 capturas, tres en '
             'producción.',
         esc=[
             ('Cargar los signos con el borrador.', 'Se guardan y traen el IMC; se puede cargar sólo la presión '
              'y sin talla no hay IMC.', ['test_se_guardan_con_el_borrador_y_traen_el_imc',
                                          'test_se_puede_cargar_solo_la_presion', 'test_sin_talla_no_hay_imc',
                                          'captura:US-53-01']),
             ('Cargar un valor imposible o una diastólica mayor que la sistólica.', 'Se rechaza diciendo el '
              'límite y no se guarda nada del borrador.',
              ['test_lo_imposible_se_rechaza', 'test_el_mensaje_dice_el_limite',
               'test_la_diastolica_no_puede_ser_mayor_ni_igual', 'test_si_se_rechazan_no_se_guarda_nada_del_borrador',
               'captura:US-53-03']),
             ('Cargar los valores límite.', 'Se aceptan.', ['test_los_limites_posibles_se_aceptan']),
             ('Cargar un valor anormal.', 'Se guarda y se marca; justo debajo del borde no hay alerta.',
              ['test_lo_anormal_se_guarda_y_se_marca', 'test_el_borde_de_cada_alerta',
               'test_justo_debajo_del_borde_no_hay_alerta', 'captura:US-53-02']),
             ('Cambiar o borrar los signos de una atención firmada.', 'La API y la base lo impiden; se corrigen '
              'con una enmienda.', ['test_firmada_la_api_no_deja_cambiarlos', 'test_la_base_no_deja_cambiarlos_firmada',
                                    'test_firmada_se_corrigen_con_una_enmienda', 'captura:US-53-05']),
             ('Otro médico u otra organización.', 'No los carga ni los ve.',
              ['test_otro_medico_no_los_carga_en_una_atencion_ajena', 'test_otra_organizacion_no_los_ve',
               'test_el_medico_de_otra_organizacion_no_los_carga']),
             ('El paciente abre su historia.', 'Ve sus signos y las gráficas de evolución, en la web y en el '
              'celular.', ['test_el_paciente_los_ve_en_su_historia', 'captura:US-53-11', 'captura:US-53-13']),
         ]),
]

NOTA_ESC = [('Escenarios planificados y resultados esperados. La columna de estado se completa únicamente en el '
             'reporte de ejecución.', False)]

# ---------------------------------------------------------------------------
# 2.3.2 Reporte de prueba
# ---------------------------------------------------------------------------
ESTADOS = [
    ('Cubierto por prueba automatizada', 'Existe una función de prueba en backend/tests que verifica el '
     'escenario, y la suite completa terminó en verde en la última ejecución (22/11/26).'),
    ('Cubierto por prueba del móvil', 'Lo verifica una prueba de mobile/test, y la suite del móvil terminó en '
     'verde.'),
    ('Verificado en la API o en pantalla', 'El escenario se ejecutó a mano contra la API o la interfaz el '
     '22/11/26, o su captura está en docs/capturas/sprint-4 y en la tarjeta de la historia.'),
    ('Verificado en producción', 'Se ejecutó en el despliegue de Railway con los datos de la organización.'),
]

EVIDENCIA = [
    ('Evidencia global acreditada:', True),
    (' el 22/11/26, después de integrar las dieciséis historias, la suite completa del backend terminó con '
     '1686 pruebas aprobadas y ninguna fallida. La suite del móvil terminó con {MOVIL}. Las pruebas de lo '
     'clínico y de seguridad se verificaron por mutación: se rompe a propósito la regla y la prueba tiene que '
     'fallar.', False),
]

ALCANCE = [
    ('Casos límite manuales del 22/11/26:', True),
    (' además de la suite, se probaron a mano unos cien casos límite contra la API y la web locales, con las '
     'cuentas de cada rol, y un recorrido de lectura en el celular contra producción: acceso de otro paciente, '
     'otro médico, recepción, superadministrador y otra organización; rangos, duplicados, fechas inválidas y '
     'textos enormes o con código. Encontraron cinco defectos, corregidos en el PR #137: cualquier paciente '
     'podía hacer el check-in de otro con su documento y ver sus datos (US-22), el check-in por documento '
     'tomaba la primera ficha de la historia en vez de la de hoy, el título del check-in no se veía en el tema '
     'claro, una palabra larga rompía la burbuja del chat (US-47) y la web no renovaba la sesión vencida al '
     'volver. Las dos correcciones del check-in tienen cuatro pruebas nuevas, verificadas por mutación.', False),
]


def evidencia(items):
    """(texto de la columna «Prueba identificada», estado) a partir de la lista de evidencias."""
    pruebas, capturas, api, prod, movil = [], [], [], [], []
    for e in items:
        if e.startswith('test_'):
            pruebas.append(e.replace('_', '_​'))
        elif e.startswith('captura:'):
            capturas.append(e.split(':', 1)[1])
        elif e.startswith('móvil:'):
            movil.append('mobile/test/' + e.split(':', 1)[1])
        elif e.startswith('api:'):
            api.append(e.split(':', 1)[1])
        elif e.startswith('prod:'):
            prod.append(e.split(':', 1)[1])
    partes = pruebas + movil
    if api:
        partes.append('API local: ' + '; '.join(api))
    if prod:
        partes.append('Producción: ' + '; '.join(prod))
    if capturas:
        partes.append('Captura ' + ', '.join(capturas))
    if pruebas:
        estado = 'Cubierto por prueba automatizada.'
    elif movil:
        estado = 'Cubierto por prueba del móvil.'
    elif prod:
        estado = 'Verificado en producción.'
    elif api or capturas:
        estado = 'Verificado en la API o en pantalla.'
    else:
        estado = 'Pendiente.'
    return '; '.join(partes) or '—', estado


# ---------------------------------------------------------------------------
# Plantilla y documento
# ---------------------------------------------------------------------------
def entre(body, sprint, desde, hasta):
    """El título que empieza con «desde» en el sprint pedido y los elementos hasta el que empieza con «hasta»."""
    actual, dentro, out, titulo = None, False, [], None
    for el in body.iterchildren():
        t = texto(el)
        if el.tag == qn('w:p') and t.startswith('Sprint ') and len(t) < 10:
            actual = t
            dentro = False
        if el.tag == qn('w:p') and t.startswith(desde) and actual == sprint and titulo is None:
            titulo, dentro = el, True
            continue
        if dentro and el.tag == qn('w:p') and t.startswith(hasta):
            break
        if dentro:
            out.append(el)
    return titulo, out


def tabla(molde, filas, fila_molde=1):
    tbl = limpiar(copy.deepcopy(molde))
    trs = tbl.findall(qn('w:tr'))
    modelo = trs[fila_molde]
    for tr in trs[1:]:
        tbl.remove(tr)
    for fila in filas:
        tr = copy.deepcopy(modelo)
        for tc, valor in zip(tr.findall(qn('w:tc')), fila):
            poner_texto(tc, valor)
        tbl.append(tr)
    return tbl


def tabla_un_parrafo(molde, partes):
    tbl = limpiar(copy.deepcopy(molde))
    tc = tbl.find(qn('w:tr')).find(qn('w:tc'))
    p = tc.find(qn('w:p'))
    p.addprevious(con_runs(p, partes))
    tc.remove(p)
    return tbl


def blanco():
    return limpiar(copy.deepcopy(P_BLANCO))


def par(molde, partes):
    return con_runs(molde, partes if isinstance(partes, list) else [(partes, False)])


plantilla = docx.Document(PLANTILLA)
pb = plantilla.element.body
_, s3_impl = entre(pb, 'Sprint 3', '2.2.1', '2.3 Pruebas')
_, s3_plan = entre(pb, 'Sprint 3', '2.3.1', '2.3.2')
_, s3_rep = entre(pb, 'Sprint 3', '2.3.2', '3. Daily')

P_IMPL = s3_impl[0]
T_IMPL = next(e for e in s3_impl if e.tag == qn('w:tbl'))
P_BLANCO = next(e for e in s3_impl if e.tag == qn('w:p') and texto(e) == '')

tbls = [e for e in s3_plan if e.tag == qn('w:tbl')]
T_CONV, T_CRIT, T_COB, T_FICHA, T_ESC = tbls[0], tbls[1], tbls[2], tbls[3], tbls[4]
P_PLAN = s3_plan[0]
P_ROTULO = next(e for e in s3_plan if texto(e) == 'Cobertura por caso de uso')
P_CU = next(e for e in s3_plan if texto(e).startswith('CU24 — '))
P_NOTA = next(e for e in s3_plan if texto(e).startswith('Escenarios planificados'))

tbls = [e for e in s3_rep if e.tag == qn('w:tbl')]
T_EST, T_RES, T_REP = tbls[0], tbls[1], tbls[2]
P_EVID = next(e for e in s3_rep if texto(e).startswith('Evidencia global'))
P_ROT_RES = next(e for e in s3_rep if texto(e) == 'Resumen de casos de uso')
P_PRUEBA = next(e for e in s3_rep if texto(e).startswith('Prueba de caso de uso CU24'))
P_CUH = next(e for e in s3_rep if texto(e).startswith('Caso de uso / historia'))
P_RESP = next(e for e in s3_rep if texto(e).startswith('Responsable:'))

MOVIL = sys.argv[4] if len(sys.argv) > 4 else 'todas sus pruebas aprobadas'
EJEC = sys.argv[5]      # salidas reales: <archivo>.txt de pytest -v, movil_<archivo>.txt y api_<CP>.txt
CAPT = sys.argv[6]      # docs/capturas/sprint-4
TMP = sys.argv[7]       # dónde dejar los PNG de las ejecuciones

import glob  # noqa: E402
import os  # noqa: E402
import re  # noqa: E402

from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.shared import Cm  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from terminal_png import dibujar  # noqa: E402

def leer(ruta):
    """Las salidas de consola en Windows pueden venir en cp1252."""
    crudo = open(ruta, 'rb').read()
    try:
        return crudo.decode('utf-8')
    except UnicodeDecodeError:
        return crudo.decode('cp1252')


# Índice de las salidas de pytest: archivo -> (cabecera, resumen, líneas).
PYTEST = {}
for ruta in glob.glob(os.path.join(EJEC, 'test_*.txt')):
    arch = os.path.basename(ruta)[:-4]
    lineas = leer(ruta).splitlines()
    cab = [l for l in lineas if l.startswith('platform ')] + [re.search(r'collected \d+ items?', l).group(0) for l in lineas if re.search(r'collected \d+ items?', l)][:1]
    resumen = next(l for l in reversed(lineas) if re.match(r'^=+ .*(passed|failed).* =+$', l))
    PYTEST[arch] = (cab, resumen, lineas)


def lineas_pytest(pruebas):
    """Extracto real de la salida de pytest -v para esas pruebas, agrupado por archivo."""
    por_archivo = {}
    for t in pruebas:
        for arch, (_, _, lineas) in sorted(PYTEST.items()):
            hits = [l for l in lineas if re.search(rf'::{t}(\[| )', l) and ('PASSED' in l or 'FAILED' in l)]
            if hits:
                por_archivo.setdefault(arch, []).extend(hits)
                break
        else:
            raise SystemExit(f'No está en las salidas: {t}')
    out = []
    for arch, hits in por_archivo.items():
        cab, resumen, _ = PYTEST[arch]
        out += [f'$ python -m pytest tests/{arch}.py -v'] + cab + ['…'] + hits + ['…', resumen, '']
    return out[:-1]


def lineas_movil(arch):
    lineas = leer(os.path.join(EJEC, f'movil_{arch}.txt')).splitlines()
    vistos, out = set(), []
    for l in lineas:
        m = re.match(r'^\d\d:\d\d \+\d+: (.*)$', l)
        if m and 'loading ' not in m.group(1) and 'All tests passed' not in l and m.group(1) not in vistos:
            vistos.add(m.group(1))
            out.append(l)
    final = next(l for l in reversed(lineas) if 'All tests passed' in l or 'failed' in l.lower())
    return [f'$ flutter test test/{arch}.dart --reporter expanded'] + out[-14:] + [final]


def lineas_api(cp):
    ruta = os.path.join(EJEC, f'api_{cp}.txt')
    return leer(ruta).rstrip().splitlines() if os.path.exists(ruta) else []


def captura(cod):
    return glob.glob(os.path.join(CAPT, cod + '-*.png'))[0]


def imagen(ruta, ancho_cm):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(ruta, width=Cm(ancho_cm))
    el = p._p
    el.getparent().remove(el)
    return el


def ancho_de(ruta):
    from PIL import Image
    w, h = Image.open(ruta).size
    return 6.0 if h > w else 15.5


doc = docx.Document(ENT)
db = doc.element.body
t_impl, c_impl = entre(db, 'Sprint 4', '2.2.1', '2.3 Pruebas')
t_plan, c_plan = entre(db, 'Sprint 4', '2.3.1', '2.3.2')
t_rep, c_rep = entre(db, 'Sprint 4', '2.3.2', '3. Daily')
for nombre, t, c in (('2.2.1', t_impl, c_impl), ('2.3.1', t_plan, c_plan), ('2.3.2', t_rep, c_rep)):
    assert t is not None, f'No se encontró el {nombre} del Sprint 4'
    if any(texto(e) for e in c) or any(e.tag == qn('w:tbl') for e in c):
        sys.exit(f'El {nombre} del Sprint 4 ya tiene contenido: no se toca.')

# Los subtítulos navegables usan los estilos de título del propio Sprint 4.
_, s4 = entre(db, 'Sprint 4', '2.1 Diseño', '2.2 Implementación')
H5 = next(e for e in s4 if texto(e).startswith('2.1.1.1 Modelo C4'))
H6 = next(e for e in s4 if texto(e).startswith('CU36 – Predicción'))

# 2.2.1
impl = [par(P_IMPL, IMPL_INTRO), tabla(T_IMPL, IMPL)]

# 2.3.1
plan = [par(P_PLAN, PLAN_INTRO), tabla_un_parrafo(T_CONV, CONVENCION), blanco(),
        tabla(T_CRIT, CRITERIOS), blanco(), par(P_ROTULO, 'Cobertura por caso de uso'),
        tabla(T_COB, [(f"{c['cu']} · {c['nombre']}", c['us'], str(len(c['esc']))) for c in CUS]), blanco()]
for c in CUS:
    n = c['us'].split('-')[1]
    plan += [par(H5, f"{c['cu']} — {c['nombre']}"),
             tabla(T_FICHA, [('Caso de uso', f"{c['cu']} — {c['nombre']}"),
                             ('Historia de usuario', f"{c['us']} · {c['plat']}"),
                             ('Descripción', c['desc']), ('Precondiciones', c['pre']),
                             ('Responsable', c['resp'])]),
             blanco(), par(P_NOTA, NOTA_ESC),
             tabla(T_ESC, [(f'CP-{n}-{i:02d}', a, r) for i, (a, r, _) in enumerate(c['esc'], 1)]), blanco()]

# 2.3.2
os.makedirs(TMP, exist_ok=True)
evid = [(t.replace('{MOVIL}', MOVIL), b) for t, b in EVIDENCIA]
rep = [tabla(T_EST, ESTADOS), blanco(), par(P_EVID, evid), par(P_EVID, ALCANCE),
       par(P_ROT_RES, 'Resumen de casos de uso'),
       tabla(T_RES, [(c['cu'], c['us'], c['resp'], c['sit']) for c in CUS]), blanco()]
total, n_img = {}, 0
for c in CUS:
    n = c['us'].split('-')[1]
    rep += [par(H5, f"{c['cu']} — {c['nombre']}"),
            par(P_CUH, [('Caso de uso / historia:', True), (f" {c['cu']} · {c['us']} · {c['plat']}", False)]),
            par(P_RESP, [('Responsable:', True), (f" {c['resp']}", False)])]
    for i, (a, r, ev) in enumerate(c['esc'], 1):
        cp = f'CP-{n}-{i:02d}'
        prueba, estado = evidencia(ev)
        total[estado] = total.get(estado, 0) + 1
        rep += [par(H6, f'{cp} · {a.rstrip(".")}'),
                tabla(T_FICHA, [('Escenario', a), ('Resultado esperado', r),
                                ('Prueba identificada', prueba), ('Estado', estado)]),
                blanco()]
        figuras = []
        for e in ev:
            if e.startswith('captura:'):
                ruta = captura(e.split(':', 1)[1])
                nombre = os.path.basename(ruta)[:-4]
                cod, resto = nombre[:8], nombre[9:].replace('-', ' ')
                figuras.append((ruta, ancho_de(ruta), f'Captura {cod}: {resto}.'))
        tests = [e for e in ev if e.startswith('test_')]
        if tests:
            png = dibujar(f'{cp} · pytest · 22/11/26', lineas_pytest(tests), os.path.join(TMP, f'{cp}.png'))
            figuras.append((png, 15.5, f'Ejecución de las pruebas de {cp} en el backend (extracto real, 22/11/26).'))
        for e in ev:
            if e.startswith('móvil:'):
                arch = e.split(':', 1)[1].replace('.dart', '')
                png = dibujar(f'{cp} · flutter test', lineas_movil(arch), os.path.join(TMP, f'{cp}-movil.png'))
                figuras.append((png, 15.5, f'Ejecución de mobile/test/{arch}.dart (extracto real, 22/11/26).'))
        api = lineas_api(cp)
        if api:
            png = dibujar(f'{cp} · API local · 22/11/26', api, os.path.join(TMP, f'{cp}-api.png'))
            figuras.append((png, 15.5, f'Verificación de {cp} contra la API local (salida real, 22/11/26).'))
        for ruta, ancho, pie in figuras:
            rep += [imagen(ruta, ancho), par(P_NOTA, [(pie, False)])]
            n_img += 1
        rep.append(blanco())

for titulo, nuevos in ((t_impl, impl), (t_plan, plan), (t_rep, rep)):
    ancla = titulo
    for el in nuevos:
        ancla.addnext(el)
        ancla = el

doc.save(SAL)
print('casos de uso:', len(CUS), 'escenarios:', sum(len(c['esc']) for c in CUS), 'imágenes:', n_img,
      'estados:', total, '->', SAL)
