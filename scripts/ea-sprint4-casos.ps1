# =========================================================================
# Datos de los casos de uso del Sprint 4 para los generadores de EA:
#   ea-comunicacion-sprint4.ps1   (2.1.3 diagrama de comunicacion)
#   ea-diseno-clases-sprint4.ps1  (diseno de clase)
#   ea-secuencia-sprint4.ps1      (secuencia)
# Se carga desde ea-sprint4-comun.ps1.
#
# UN guion por caso de uso, del que salen los tres diagramas:
#   participantes = @( @{ k; n; rol (actor|boundary|control|entity|externo);
#                         col (0 actor, 1 pantalla, 2 control, 3 entidad,
#                         4 externo); f (fila); nota; atr; ops } )
#   rel    = relaciones entre ENTIDADES (d, a, cd, ca, r), de las ForeignKey
#   grupos = [ordered]@{ <n> = 'nombre del flujo' }
#   guion  = @( @{ t='msg'; g; o; d; m; src; ret } |
#               @{ t='alt' } @{ t='op'; g='guarda' } @{ t='fin' } |
#               @{ t='loop'; g='guarda' } ... @{ t='fin' } )
#   m es el rotulo (nombre real del metodo con sus parametros); src es el
#   anclaje al codigo (archivo:linea, SQL), que va a las notas del mensaje.
#   El numero <grupo>.<orden> lo pone Mensajes-Del-Guion por orden de
#   aparicion. ops: TODOS los metodos de la clase en el codigo.
#
# Leidos del codigo el 21/11/26 (rama fix/us51-respaldo-y-v1.6.1, con main
# hasta el PR #127; CU52 releido en main a51d32a, PR #128 y #129). Casos de uso: US-35..US-42 -> CU36..CU43 (paquete 3.10),
# US-46 -> CU47, US-47 -> CU48 (reparto.md), US-48..US-53 -> CU49..CU54
# (ampliacion-17-11.md).
# =========================================================================

$CASOS_SPRINT4 = [ordered]@{}

# =========================================================================
# Datos de CU36 (US-35), CU37 (US-36), CU38 (US-37) y CU39 (US-38).
# Leídos del código el 21/11/26 (rama fix/us51-respaldo-y-v1.6.1).
# Formato: SPEC-datos-sprint4.md. Cada clase lleva TODOS sus métodos.
# =========================================================================

# ---- compartidos entre los cuatro casos de uso -----------------------------
$A_ATR_FICHA = @('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'practitioner_id : uuid',
  'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar',
  'checked_in_at : timestamptz', 'attendance_confirmed_at : timestamptz', 'reminder_sent_at : timestamptz',
  'reinforced_reminder_sent_at : timestamptz', 'expires_at : timestamptz', 'cancelled_at : timestamptz',
  'created_at : timestamptz', 'updated_at : timestamptz')
$A_ATR_VERSION = @('id : uuid', 'organization_id : uuid', 'kind : varchar(16)', 'version : integer', 'status : varchar(10)',
  'trained_at : timestamptz', 'n_train : integer', 'n_test : integer', 'base_rate : double precision',
  'params : jsonb', 'metrics : jsonb', 'beats_baseline : boolean', 'created_at : timestamptz', 'updated_at : timestamptz')
$A_ATR_PREDICCION = @('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'model_version_id : uuid',
  'probability : double precision', 'level : varchar(6)', 'factors : jsonb', 'computed_at : timestamptz')
$A_OPS_PREDICCION = @('predict_proba(params, values)', 'level_for(probability, cutoffs)', 'explain(params, values)',
  'active_version(organization)', 'score_for(organization, now)', 'has_feature(organization)',
  'eligible_organizations(slugs)', 'run_due(now)')
$A_OPS_ENTRENAMIENTO = @('data_status(organization, now)', '_insufficient(message, labeled, absent)', 'train_for(organization, now)',
  '_save_version(organization, params, metricas, supera, n_train, n_test, base_rate, now)', 'promote(version)',
  'label_of(ficha)', '_chunks(items, size)', '_earliest_payments(organization, appointment_ids)',
  '_histories(organization, patient_ids, as_of)', 'build_rows(organization, fichas, as_of)', '_plural(n, uno, varios)',
  'describe(name, value)')
$A_OPS_PANTALLA_RIESGO = @('RiesgoInasistencia()', 'rangoPorDefecto()', 'aErrorPantalla(e)', 'filtro(poner)',
  'verModeloRiesgo(contexto, senal)', 'listarRiesgo(filtros, contexto, senal)', 'listarVersionesRiesgo(contexto, senal)',
  'esErrorDePlan(error)', 'listarSucursales(contexto, senal)', 'TarjetaModelo(estado, cargando)', 'ComparacionBrier(metricas)',
  'Factores(factores)', 'InsigniaNivel(nivel)', 'IconoNivel(nivel)', 'AvisoPlan(mensaje)', 'TablaRiesgo(filas)', 'ListaRiesgo(filas)')

# -------------------------------------------------------------------------
# CU36 (US-35) Predicción de Riesgo de Inasistencia
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU36'] = @{
  cu = 'CU36'; nombre = 'Predicción de Riesgo de Inasistencia'; us = 'US-35'; plataforma = 'web'
  nota = 'Un modelo de regresión logística por organización (noshow/training.py, comando train_noshow) se guarda como coeficientes JSON en model_versions; el proceso score_noshow --loop (scripts/start.sh) califica cada ficha futura en noshow_predictions y la Administración lo consulta en RiesgoInasistencia.tsx (plan Premium, permiso appointments.noshow.read). El entrenamiento no se lanza desde la web.'
  participantes = @(
    @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=1 },
    @{ k='sistema'; n='Sistema'; rol='actor'; col=0; f=3 },
    @{ k='pantalla'; n='PantallaRiesgoInasistencia'; rol='boundary'; col=1; f=1.5
       nota='Web: frontend/src/paginas/RiesgoInasistencia.tsx (ruta /riesgo-inasistencia) y frontend/src/api/riesgo.ts. No hay pantalla móvil; Agendas.tsx no muestra el riesgo.'
       atr=@('GET /api/noshow/model/ : 200 | 403', 'GET /api/noshow/appointments/ : 200 | 400 | 403', 'desde : string', 'hasta : string',
             'sucursal : string', 'nivel : NivelRiesgo', 'pagina : number', 'modelo : EstadoModelo', 'respuesta : Pagina<FichaEnRiesgo>')
       ops=$A_OPS_PANTALLA_RIESGO },
    @{ k='ctrlmod'; n='ControladorModeloRiesgo'; rol='control'; col=2; f=0
       nota='NoShowModelView en noshow/views.py (GET /api/noshow/model/), con CanReadNoShow de noshow/permissions.py.'
       ops=@('get(request)', '_metrics(metricas)', '_round(valor, cifras)', 'has_permission(request, view)') },
    @{ k='ctrlfichas'; n='ControladorRiesgoFichas'; rol='control'; col=2; f=1
       nota='NoShowAppointmentsView en noshow/views.py (GET /api/noshow/appointments/?from=&to=&branch=&level=&page=). Pide el plan con require_feature(noshow_prediction).'
       ops=@('get(request)', '_fila(prediccion)', '_error(code, detail)', '_fecha(valor)', '_organization(request)', '_sin_organizacion()') },
    @{ k='gpred'; n='GestorPrediccion'; rol='control'; col=2; f=2
       nota='noshow/scoring.py; lo lanza el comando score_noshow --loop (noshow/management/commands/score_noshow.py), cada 60 minutos.'
       ops=$A_OPS_PREDICCION },
    @{ k='gentr'; n='GestorEntrenamiento'; rol='control'; col=2; f=3
       nota='noshow/training.py y las variables de noshow/features.py; lo lanza el comando train_noshow (noshow/management/commands/train_noshow.py).'
       ops=$A_OPS_ENTRENAMIENTO },
    @{ k='version'; n='VersionModelo'; rol='entity'; col=3; f=0
       nota='ModelVersion, tabla model_versions. Una sola vigente (status=active) por organización y tipo.'
       atr=$A_ATR_VERSION; ops=@() },
    @{ k='pred'; n='PrediccionInasistencia'; rol='entity'; col=3; f=1.5
       nota='NoShowPrediction, tabla noshow_predictions. Una fila por ficha; level low|medium|high.'
       atr=$A_ATR_PREDICCION; ops=@() },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=3
       nota='Appointment, tabla appointments.'
       atr=$A_ATR_FICHA; ops=@('is_active()') }
  )
  rel = @(
    @{ d='version'; a='pred'; cd='1'; ca='0..*'; r='calcula' },
    @{ d='ficha'; a='pred'; cd='1'; ca='0..1'; r='se califica con' }
  )
  grupos = [ordered]@{ 1 = 'Entrenar el modelo y predecir cada ficha'; 2 = 'Sin datos suficientes para entrenar'; 3 = 'Consultar el riesgo de las fichas'; 4 = 'Sin modelo vigente'; 5 = 'Plan sin la función o filtro inválido' }
  guion = @(
    @{ t='msg'; g=1; o='sistema'; d='gentr'; m='train_for(organization)'; src='train_noshow.py:65; training.py:93' },
    @{ t='msg'; g=1; o='gentr'; d='ficha'; m='filter(organization, debian_atenderse_q(now))'; src='training.py:102' },
    @{ t='alt' },
    @{ t='op'; g='al menos 200 fichas con desenlace y 20 ausencias' },
    @{ t='msg'; g=1; o='gentr'; d='version'; m='create(version, status, params, metrics)'; src='training.py:211; INSERT INTO model_versions (status active | candidate | rejected)' },
    @{ t='msg'; g=1; o='gentr'; d='sistema'; m='TrainResult(version, message)'; ret=$true; src='training.py:190' },
    @{ t='op'; g='faltan fichas o ausencias' },
    @{ t='msg'; g=2; o='gentr'; d='sistema'; m='TrainResult(None, sin_datos, message)'; ret=$true; src='training.py:109' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='sistema'; d='gpred'; m='run_due(now)'; src='score_noshow.py:138; scoring.py:407' },
    @{ t='loop'; g='por cada organización con el plan' },
    @{ t='msg'; g=1; o='gpred'; d='version'; m='filter(status=active).first()'; src='scoring.py:324 (active_version)' },
    @{ t='msg'; g=1; o='gpred'; d='ficha'; m='filter(status__in, starts_at <= now+60d)'; src='scoring.py:340' },
    @{ t='msg'; g=1; o='gpred'; d='pred'; m='bulk_create(nuevas, ignore_conflicts=True)'; src='scoring.py:382; INSERT INTO noshow_predictions' },
    @{ t='msg'; g=1; o='gpred'; d='pred'; m='bulk_update(cambiadas, campos)'; src='scoring.py:383; UPDATE noshow_predictions' },
    @{ t='fin' },
    @{ t='msg'; g=3; o='admin'; d='pantalla'; m='abrirRiesgoInasistencia()'; src='RiesgoInasistencia.tsx:189' },
    @{ t='msg'; g=3; o='pantalla'; d='ctrlmod'; m='get(request)'; src='RiesgoInasistencia.tsx:221; riesgo.ts:106; GET /api/noshow/model/; views.py:174' },
    @{ t='msg'; g=3; o='ctrlmod'; d='gpred'; m='active_version(organization)'; src='views.py:180; scoring.py:322' },
    @{ t='alt' },
    @{ t='op'; g='hay un modelo vigente' },
    @{ t='msg'; g=3; o='ctrlmod'; d='pantalla'; m='200(model, metrics, cutoffs)'; ret=$true; src='views.py:182' },
    @{ t='msg'; g=3; o='admin'; d='pantalla'; m='filtrar(desde, hasta, sucursal, nivel)'; src='RiesgoInasistencia.tsx:300-312' },
    @{ t='msg'; g=3; o='pantalla'; d='ctrlfichas'; m='get(request)'; src='RiesgoInasistencia.tsx:248; riesgo.ts:94; GET /api/noshow/appointments/; views.py:88' },
    @{ t='msg'; g=3; o='ctrlfichas'; d='pred'; m='filter(model_version__status=active, rango)'; src='views.py:127; select_related(appointment__patient, ...)' },
    @{ t='msg'; g=3; o='ctrlfichas'; d='pantalla'; m='200(level, probability, factors)'; ret=$true; src='views.py:150 (_fila, views.py:153)' },
    @{ t='op'; g='no hay modelo vigente' },
    @{ t='msg'; g=4; o='ctrlmod'; d='version'; m='filter(status=rejected).first()'; src='views.py:200' },
    @{ t='msg'; g=4; o='ctrlmod'; d='gentr'; m='data_status(organization)'; src='views.py:219; training.py:75' },
    @{ t='msg'; g=4; o='ctrlmod'; d='pantalla'; m='200(model=null, reason, message)'; ret=$true; src='views.py:207 | 221 | 228 (no_supera_base | sin_datos | sin_modelo)' },
    @{ t='op'; g='plan sin la función o filtro inválido' },
    @{ t='msg'; g=5; o='ctrlfichas'; d='pantalla'; m='403(plan_limit)'; ret=$true; src='views.py:92; tenancy/plans.py:109 (require_feature)' },
    @{ t='msg'; g=5; o='ctrlfichas'; d='pantalla'; m='400(invalid_date | invalid_level | ...)'; ret=$true; src='views.py:104-124 (_error, views.py:46)' },
    @{ t='fin' }
  )
}

# -------------------------------------------------------------------------
# CU37 (US-36) Envío de Recordatorios por Riesgo de Inasistencia
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU37'] = @{
  cu = 'CU37'; nombre = 'Envío de Recordatorios por Riesgo de Inasistencia'; us = 'US-36'; plataforma = 'proceso'
  nota = 'En la misma vuelta de send_appointment_reminders --loop (cada 15 min, scripts/start.sh) que manda el recordatorio de US-28, appointments/reminders.py manda un segundo aviso, 3 h antes, a las fichas confirmadas con predicción de riesgo alto de un modelo vigente; lee la predicción de US-35, no la calcula, y marca reinforced_reminder_sent_at en la misma transacción.'
  participantes = @(
    @{ k='sistema'; n='Sistema'; rol='actor'; col=0; f=1 },
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=3.5 },
    @{ k='comando'; n='ComandoRecordatorios'; rol='boundary'; col=1; f=1.5
       nota='Command en appointments/management/commands/send_appointment_reminders.py; lo lanza scripts/start.sh con --loop. Se apaga con APPOINTMENT_REMINDERS=off.'
       atr=@('--loop : bool', '--every : int = 15')
       ops=@('add_arguments(parser)', 'handle(*args, **options)', '_vuelta()') },
    @{ k='grec'; n='GestorRecordatorios'; rol='control'; col=2; f=0
       nota='appointments/reminders.py. La ventana del refuerzo es APPOINTMENT_REINFORCED_REMINDER_HOURS (3 por omisión, config/settings.py:302).'
       ops=@('due(now)', 'due_reinforced(now)', '_enviar(organization, consulta, evento, campo, now)', 'run_for(organization, now)',
             'run_reinforced_for(organization, now)', '_organizaciones_activas()', '_por_organizacion(funcion, mensaje, now)',
             'run_cycle(now)', 'run_due(now)') },
    @{ k='gpred'; n='GestorPrediccion'; rol='control'; col=2; f=1
       nota='noshow/scoring.py: sólo has_feature (plan con noshow_prediction); la predicción no se recalcula acá.'
       ops=$A_OPS_PREDICCION },
    @{ k='gavisos'; n='GestorAvisos'; rol='control'; col=2; f=2.5
       nota='notifications/services.py (notify y textos) y notifications/push.py (send_to_user, FCM HTTP v1). El texto no dice por qué se refuerza.'
       ops=@('notify(event, appointment_id, organization_id)', '_load(appointment_id)', '_recipient(appointment)', '_minutos()',
             '_cuando(appointment)', '_push_text(event, appointment)', '_datos(appointment)', '_email(event, appointment)',
             '_devolucion(appointment)', 'send_to_user(user, message)', '_read_credentials(raw)', '_authorized_session()',
             '_payload(token, message)', '_is_dead(response)') },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=0.5
       nota='Appointment, tabla appointments. Marca propia reinforced_reminder_sent_at.'
       atr=$A_ATR_FICHA; ops=@('is_active()') },
    @{ k='pred'; n='PrediccionInasistencia'; rol='entity'; col=3; f=2
       nota='NoShowPrediction, tabla noshow_predictions (la escribe CU36).'
       atr=$A_ATR_PREDICCION; ops=@() },
    @{ k='fcm'; n='Firebase Cloud Messaging'; rol='externo'; col=4; f=1.5 },
    @{ k='correo'; n='Servicio de correo (Brevo)'; rol='externo'; col=4; f=3 }
  )
  rel = @(
    @{ d='ficha'; a='pred'; cd='1'; ca='0..1'; r='se califica con' }
  )
  grupos = [ordered]@{ 1 = 'Reforzar el recordatorio de las fichas de riesgo alto'; 2 = 'El plan no incluye la predicción' }
  guion = @(
    @{ t='msg'; g=1; o='sistema'; d='comando'; m='handle(--loop, --every=15)'; src='start.sh:47; send_appointment_reminders.py:45' },
    @{ t='msg'; g=1; o='comando'; d='grec'; m='run_cycle()'; src='send_appointment_reminders.py:73 (_vuelta); reminders.py:156' },
    @{ t='loop'; g='por cada organización activa' },
    @{ t='msg'; g=1; o='grec'; d='gpred'; m='has_feature(organization)'; src='reminders.py:132 (run_reinforced_for); scoring.py:391' },
    @{ t='alt' },
    @{ t='op'; g='el plan incluye la predicción' },
    @{ t='msg'; g=1; o='gpred'; d='grec'; m='True'; ret=$true; src='scoring.py:394' },
    @{ t='msg'; g=1; o='grec'; d='ficha'; m='filter(confirmed, starts_at <= now+3h)'; src='reminders.py:77 (due_reinforced); reinforced_reminder_sent_at IS NULL' },
    @{ t='msg'; g=1; o='grec'; d='pred'; m='filter(level=high, version vigente)'; src='reminders.py:83; JOIN noshow_predictions en la misma consulta' },
    @{ t='msg'; g=1; o='grec'; d='ficha'; m='select_for_update(skip_locked=True, of=self)'; src='reminders.py:103; si es None la tomó otro proceso' },
    @{ t='msg'; g=1; o='grec'; d='gavisos'; m='notify(REINFORCED_REMINDER, ficha.id, org.id)'; src='reminders.py:109; services.py:51' },
    @{ t='msg'; g=1; o='gavisos'; d='ficha'; m='get(pk=appointment_id)'; src='services.py:92 (_load)' },
    @{ t='msg'; g=1; o='gavisos'; d='fcm'; m='session.post(url, json=_payload(token, msg))'; src='services.py:67; push.py:119 (send_to_user), push.py:141' },
    @{ t='msg'; g=1; o='fcm'; d='paciente'; m='push(Tu ficha empieza pronto)'; src='services.py:130; mobile/lib/core/notifications/push.dart:258' },
    @{ t='msg'; g=1; o='gavisos'; d='correo'; m='send_mail(asunto, cuerpo, from, [destino])'; src='services.py:84; django-anymail con BREVO_API_KEY' },
    @{ t='msg'; g=1; o='correo'; d='paciente'; m='correo(Tu ficha de hoy a las HH:MM)'; src='services.py:172-183 (_email)' },
    @{ t='msg'; g=1; o='grec'; d='ficha'; m='save(reinforced_reminder_sent_at)'; src='reminders.py:110-111; misma transacción que el envío' },
    @{ t='op'; g='el plan no la incluye' },
    @{ t='msg'; g=2; o='gpred'; d='grec'; m='False'; ret=$true; src='scoring.py:394; reminders.py:132 devuelve 0' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='grec'; d='comando'; m='(avisadas, reforzadas)'; ret=$true; src='reminders.py:167' }
  )
}

# -------------------------------------------------------------------------
# CU38 (US-37) Proyección de Demanda de Fichas
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU38'] = @{
  cu = 'CU38'; nombre = 'Proyección de Demanda de Fichas'; us = 'US-37'; plataforma = 'web'
  nota = 'reporting/demand.py proyecta las fichas por especialidad y franja (mañana, tarde, noche) de las próximas 1 a 8 semanas con el promedio semanal de las 8 semanas previas, las compara con la capacidad de las agendas menos los bloqueos y mide el error con un backtest walk-forward (MAE y WAPE). Se ve en ProyeccionDemanda.tsx (ruta /proyeccion-demanda), con el permiso reporting.kpi.read.'
  participantes = @(
    @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaProyeccionDemanda'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/ProyeccionDemanda.tsx (ruta /proyeccion-demanda) y frontend/src/api/demanda.ts. No está en Kpis.tsx ni en el móvil.'
       atr=@('GET /api/reporting/demand/?weeks=&branch= : 200 | 400 | 403', 'weeks : number', 'branch : string', 'branches : Sucursal[]',
             'data : ProyeccionDemanda', 'error : string', 'loading : boolean')
       ops=@('ProyeccionDemanda()', 'FilterDropdown(label, value, options, onChange)', 'verProyeccionDemanda(weeks, branch, contexto, senal)',
             'listarSucursales(contexto, senal)') },
    @{ k='ctrl'; n='ControladorProyeccionDemanda'; rol='control'; col=2; f=0.5
       nota='DemandProjectionView en reporting/demand_views.py (GET /api/reporting/demand/), con CanReadKpis (reporting.kpi.read) de reporting/permissions.py.'
       ops=@('get(request)', 'has_permission(request, view)') },
    @{ k='gdem'; n='GestorProyeccionDemanda'; rol='control'; col=2; f=2
       nota='reporting/demand.py. HISTORY_WEEKS = 8, MAX_WEEKS = 8. Calcula en Python sobre una sola consulta de fichas.'
       ops=@('band(hour)', 'project(organization, weeks, branch_id, now)') },
    @{ k='gdisp'; n='GestorDisponibilidad'; rol='control'; col=2; f=3.5
       nota='scheduling/availability.py: los mismos espacios de la disponibilidad de CU16.'
       ops=@('_daterange(date_from, date_to)', 'slot_starts(start, end, step_minutes)', '_booked_slots(practitioner_id, date_from, date_to)',
             'generate_slots(schedule, date_from, date_to, tz)', '_blocked(start_aware, end_aware, blocks)',
             'consolidated_availability(practitioner_id, date_from, date_to, branch_id, now)', 'next_available_slot(practitioner_id, now, horizon_days)') },
    @{ k='esp'; n='Especialidad'; rol='entity'; col=3; f=0
       nota='Specialty, tabla specialties.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'description : text', 'is_active : boolean',
             'created_at : timestamptz', 'updated_at : timestamptz'); ops=@() },
    @{ k='espprof'; n='EspecialidadProfesional'; rol='entity'; col=3; f=1
       nota='PractitionerSpecialty, tabla practitioner_specialties. El primer vínculo es la especialidad principal.'
       atr=@('id : bigint', 'organization_id : uuid', 'practitioner_id : uuid', 'specialty_id : uuid', 'created_at : timestamptz'); ops=@() },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=2
       nota='Appointment, tabla appointments. Cuentan confirmed, attended y no_show.'
       atr=$A_ATR_FICHA; ops=@('is_active()') },
    @{ k='agenda'; n='Agenda'; rol='entity'; col=3; f=3
       nota='Schedule, tabla schedules.'
       atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint',
             'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'capacity : smallint', 'valid_from : date',
             'valid_until : date', 'is_active : boolean', 'created_at : timestamptz', 'updated_at : timestamptz'); ops=@() },
    @{ k='bloqueo'; n='BloqueoAgenda'; rol='entity'; col=3; f=4
       nota='ScheduleBlock, tabla schedule_blocks.'
       atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz',
             'ends_at : timestamptz', 'reason : varchar(12)', 'note : varchar(200)', 'is_active : boolean',
             'created_at : timestamptz', 'updated_at : timestamptz'); ops=@() }
  )
  rel = @(
    @{ d='esp'; a='espprof'; cd='1'; ca='0..*'; r='se vincula con' },
    @{ d='agenda'; a='ficha'; cd='1'; ca='0..*'; r='ofrece' }
  )
  grupos = [ordered]@{ 1 = 'Proyectar la demanda de fichas'; 2 = 'Parámetros inválidos o sin organización' }
  guion = @(
    @{ t='msg'; g=1; o='admin'; d='pantalla'; m='abrirProyeccionDemanda()'; src='ProyeccionDemanda.tsx:86' },
    @{ t='msg'; g=1; o='admin'; d='pantalla'; m='elegirFiltros(weeks, branch)'; src='ProyeccionDemanda.tsx:135, 141' },
    @{ t='msg'; g=1; o='pantalla'; d='ctrl'; m='get(request)'; src='ProyeccionDemanda.tsx:110; demanda.ts:38; GET /api/reporting/demand/; demand_views.py:17' },
    @{ t='alt' },
    @{ t='op'; g='weeks entre 1 y 8 y sucursal de la organización' },
    @{ t='msg'; g=1; o='ctrl'; d='gdem'; m='project(org, weeks, branch_id)'; src='demand_views.py:39; demand.py:32' },
    @{ t='msg'; g=1; o='gdem'; d='esp'; m='filter(organization, is_active=True)'; src='demand.py:45' },
    @{ t='msg'; g=1; o='gdem'; d='espprof'; m='filter(organization).values_list(...)'; src='demand.py:47' },
    @{ t='msg'; g=1; o='gdem'; d='ficha'; m='filter(starts_at__gte, __lt, status__in)'; src='demand.py:57; una sola consulta' },
    @{ t='msg'; g=1; o='gdem'; d='agenda'; m='filter(is_active, valid_from__lt=end)'; src='demand.py:84' },
    @{ t='msg'; g=1; o='gdem'; d='bloqueo'; m='filter(is_active, starts_at__lt, ends_at__gt)'; src='demand.py:90' },
    @{ t='loop'; g='por cada agenda vigente' },
    @{ t='msg'; g=1; o='gdem'; d='gdisp'; m='generate_slots(schedule, start, end, tz)'; src='demand.py:100; availability.py:79' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='gdem'; d='ctrl'; m='dict(rows, validation, note)'; ret=$true; src='demand.py:151; backtest walk-forward en demand.py:116' },
    @{ t='msg'; g=1; o='ctrl'; d='pantalla'; m='200(rows, validation, has_historical_data)'; ret=$true; src='demand_views.py:39' },
    @{ t='op'; g='parámetros inválidos o sin organización' },
    @{ t='msg'; g=2; o='ctrl'; d='pantalla'; m='400(invalid_weeks | invalid_branch)'; ret=$true; src='demand_views.py:27, 34, 37' },
    @{ t='msg'; g=2; o='ctrl'; d='pantalla'; m='403(sin_organizacion)'; ret=$true; src='demand_views.py:20' },
    @{ t='fin' }
  )
}

# -------------------------------------------------------------------------
# CU39 (US-38) Reentrenamiento del Modelo de No-Show
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU39'] = @{
  cu = 'CU39'; nombre = 'Reentrenamiento del Modelo de No-Show'; us = 'US-38'; plataforma = 'proceso'
  nota = 'El comando retrain_noshow (--all, --loop --every 1440) recorre las organizaciones con el plan, entrena un candidato con train_for de US-35 cuando hay al menos 20 desenlaces nuevos, lo compara con el vigente por Brier sobre los mismos desenlaces posteriores al vigente y sólo lo promueve si mejora; la Administración ve el historial de versiones en RiesgoInasistencia.tsx (GET /api/noshow/versions/). No está en scripts/start.sh.'
  participantes = @(
    @{ k='sistema'; n='Sistema'; rol='actor'; col=0; f=1 },
    @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=3.5 },
    @{ k='comando'; n='ComandoReentrenamiento'; rol='boundary'; col=1; f=1
       nota='Command en noshow/management/commands/retrain_noshow.py (--organization SLUG | --all, --loop, --every 1440, --min-new 20).'
       atr=@('--organization : SLUG[]', '--all : bool', '--loop : bool', '--every : int = 1440', '--min-new : int = 20')
       ops=@('add_arguments(parser)', 'handle(*args, **options)', 'run()') },
    @{ k='pantalla'; n='PantallaRiesgoInasistencia'; rol='boundary'; col=1; f=3.5
       nota='Web: frontend/src/paginas/RiesgoInasistencia.tsx (sección Historial de versiones No-Show) y frontend/src/api/riesgo.ts. No está en Kpis.tsx.'
       atr=@('GET /api/noshow/versions/ : 200 | 403', 'versiones : VersionRiesgo[]')
       ops=$A_OPS_PANTALLA_RIESGO },
    @{ k='greent'; n='GestorReentrenamiento'; rol='control'; col=2; f=0
       nota='noshow/retraining.py. MIN_NEW_OUTCOMES = 20, MIN_EVALUATION = 20.'
       ops=@('_brier(params, rows)', 'retrain_for(organization, now, min_new)', '_reject(candidate, comparison)', 'run_due(now, slugs, min_new)') },
    @{ k='gentr'; n='GestorEntrenamiento'; rol='control'; col=2; f=1
       nota='noshow/training.py y noshow/features.py (los de CU36).'
       ops=$A_OPS_ENTRENAMIENTO },
    @{ k='gpred'; n='GestorPrediccion'; rol='control'; col=2; f=2
       nota='noshow/scoring.py (los de CU36).'
       ops=$A_OPS_PREDICCION },
    @{ k='ctrlver'; n='ControladorVersionesModelo'; rol='control'; col=2; f=3.5
       nota='NoShowVersionsView en noshow/retrain_views.py (GET /api/noshow/versions/), con CanReadNoShow y require_feature(noshow_prediction).'
       ops=@('get(request)', 'has_permission(request, view)') },
    @{ k='version'; n='VersionModelo'; rol='entity'; col=3; f=1
       nota='ModelVersion, tabla model_versions. La comparación queda en metrics.retraining_comparison.'
       atr=$A_ATR_VERSION; ops=@() },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=2.5
       nota='Appointment, tabla appointments.'
       atr=$A_ATR_FICHA; ops=@('is_active()') }
  )
  rel = @(
    @{ d='ficha'; a='version'; cd='0..*'; ca='0..*'; r='entrena y evalúa' }
  )
  grupos = [ordered]@{ 1 = 'Reentrenar y promover si mejora al vigente'; 2 = 'Sin desenlaces nuevos suficientes'; 3 = 'El candidato no mejora al vigente'; 4 = 'Ver el historial de versiones' }
  guion = @(
    @{ t='msg'; g=1; o='sistema'; d='comando'; m='handle(--all, --loop, --every=1440)'; src='retrain_noshow.py:173' },
    @{ t='msg'; g=1; o='comando'; d='greent'; m='run_due(slugs, min_new)'; src='retrain_noshow.py:187; retraining.py:107' },
    @{ t='msg'; g=1; o='greent'; d='gpred'; m='eligible_organizations(slugs)'; src='retraining.py:110; scoring.py:397' },
    @{ t='loop'; g='por cada organización habilitada' },
    @{ t='msg'; g=1; o='greent'; d='gpred'; m='active_version(organization)'; src='retraining.py:50; tras select_for_update de la organización (retraining.py:48)' },
    @{ t='msg'; g=1; o='greent'; d='version'; m='filter(kind).order_by(-version).first()'; src='retraining.py:51' },
    @{ t='msg'; g=1; o='greent'; d='gentr'; m='data_status(organization, now)'; src='retraining.py:54; training.py:75' },
    @{ t='alt' },
    @{ t='op'; g='al menos 20 desenlaces nuevos y el candidato mejora' },
    @{ t='msg'; g=1; o='greent'; d='gentr'; m='train_for(organization, now)'; src='retraining.py:60; training.py:93' },
    @{ t='msg'; g=1; o='gentr'; d='version'; m='create(version, status=candidate, ...)'; src='training.py:211; INSERT INTO model_versions' },
    @{ t='msg'; g=1; o='greent'; d='ficha'; m='filter(debian_atenderse_q(now)).order_by(...)'; src='retraining.py:68; held_out = posteriores al vigente' },
    @{ t='msg'; g=1; o='greent'; d='gpred'; m='predict_proba(params, row.values)'; src='retraining.py:36 (_brier), 85-86' },
    @{ t='msg'; g=1; o='greent'; d='version'; m='save(update_fields=[metrics])'; src='retraining.py:90-91' },
    @{ t='msg'; g=1; o='greent'; d='gentr'; m='promote(candidate)'; src='retraining.py:96; training.py:219' },
    @{ t='msg'; g=1; o='gentr'; d='version'; m='select_for_update().get(pk=version.pk)'; src='training.py:228' },
    @{ t='msg'; g=1; o='gentr'; d='version'; m='update(status=retired); save(status=active)'; src='training.py:231-236' },
    @{ t='msg'; g=1; o='greent'; d='comando'; m='RetrainResult(promoted, message)'; ret=$true; src='retraining.py:98' },
    @{ t='op'; g='menos de 20 desenlaces nuevos' },
    @{ t='msg'; g=2; o='greent'; d='comando'; m='RetrainResult(skipped, message)'; ret=$true; src='retraining.py:57-58' },
    @{ t='op'; g='el candidato no mejora el Brier del vigente' },
    @{ t='msg'; g=3; o='greent'; d='version'; m='save(update_fields=[metrics, status])'; src='retraining.py:93, 101-104 (_reject: status=rejected)' },
    @{ t='msg'; g=3; o='greent'; d='comando'; m='RetrainResult(rejected, message)'; ret=$true; src='retraining.py:94' },
    @{ t='fin' },
    @{ t='fin' },
    @{ t='msg'; g=4; o='admin'; d='pantalla'; m='abrirRiesgoInasistencia()'; src='RiesgoInasistencia.tsx:189' },
    @{ t='msg'; g=4; o='pantalla'; d='ctrlver'; m='get(request)'; src='RiesgoInasistencia.tsx:231; riesgo.ts:133; GET /api/noshow/versions/; retrain_views.py:133' },
    @{ t='msg'; g=4; o='ctrlver'; d='version'; m='filter(kind).order_by(-version)[:30]'; src='retrain_views.py:138' },
    @{ t='msg'; g=4; o='ctrlver'; d='pantalla'; m='200(results: version, status, comparison)'; ret=$true; src='retrain_views.py:141' }
  )
}


# =========================================================================
# Datos de CU40 (US-39), CU41 (US-40), CU42 (US-41) y CU43 (US-42).
# Leidos del codigo al 21/11/26 (rama fix/us51-respaldo-y-v1.6.1).
# Formato: SPEC-datos-sprint4.md.
# =========================================================================

$OPS_TEXTOS_IA = @('create_draft(kind, text, encounter, medical_order, patient, generated_by)', 'inbox_for(user)',
  '_clean(text)', '_lock_draft(texto)', 'edit(texto, final_text)', 'approve(texto, user, final_text)',
  'discard(texto, user)', 'diff(original, final)', 'own_patient_ids(user)', 'approved_for(user)')
$ATR_TEXTO_IA = @('id : uuid', 'organization_id : uuid', 'kind : varchar(24)', 'patient_id : uuid', 'practitioner_id : uuid',
  'encounter_id : uuid', 'medical_order_id : uuid', 'generated_text : text', 'final_text : text',
  'generated_by : varchar(60)', 'status : varchar(10)', 'reviewed_by_id : uuid', 'reviewed_at : timestamptz',
  'created_at : timestamptz', 'updated_at : timestamptz')
$OPS_BITACORA_S4 = @('client_ip(request)', 'user_agent(request)', 'record(request, action, entity, entity_id, detail, organization, user)',
  '_http_request(request)', 'flush(request)', '_write(entry)', '_usuario_de(request)', '_organization_id(organization, autor)')
$OPS_FIRMA = @('post(request, pk)', '_own_encounter(request, pk)', '_audit(request, action, encuentro, extra)',
  'sign(encounter, user)', 'practitioner_of(user)', 'is_own(user, encounter)')
$OPS_PANTALLA_ATENCION = @('Atencion()', 'guardar()', 'firmar()', 'enviarEnmienda(e)', 'firmarEncuentro(id, contexto)',
  'reintentarResumen(encuentroId, contexto)', 'AvisoResumenPaciente(encuentroId, resultado, onCambio)',
  'PedirResumenPaciente(encuentroId, onResultado)')

# -------------------------------------------------------------------------
# CU40 (US-39) Generacion de Resumen de Consulta mediante IA
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU40'] = @{
  cu = 'CU40'; nombre = 'Generación de Resumen de Consulta mediante IA'; us = 'US-39'; plataforma = 'web'
  nota = 'Al firmar la atención (EncounterSignView), ai/consultation_summary.generate pide a Gemini un resumen en palabras del paciente y lo guarda como borrador en ai_generated_texts con create_draft; firmar nunca falla por el resumen. El paciente lo lee en el móvil sólo cuando su médico lo aprobó (approved_for, regla 14).'
  participantes = @(
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=1 },
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=3 },
    @{ k='pantalla'; n='PantallaAtencion'; rol='boundary'; col=1; f=1
       nota='Web: frontend/src/paginas/Atencion.tsx (firmar) con AvisoResumenPaciente y PedirResumenPaciente de paginas/TextosPorValidar.tsx; api/atencion.ts (firmarEncuentro) y api/textos_ia.ts (reintentarResumen).'
       atr=@('POST /api/encounters/{id}/sign/ : 200 | 400 | 409', 'POST /api/ai/encounters/{id}/summary/ : 200 | 404 | 409', 'resumenPaciente : ResultadoResumen', 'confirmarFirma : boolean')
       ops=$OPS_PANTALLA_ATENCION },
    @{ k='pantallahist'; n='PantallaHistoriaClinica'; rol='boundary'; col=1; f=3
       nota='Móvil: mobile/lib/features/clinical_record/clinical_record_screen.dart (_Resumen) y clinical_record_api.dart (verTextosAprobados, ResumenConsulta).'
       atr=@('GET /api/ai/texts/mine/?patient= : 200', 'historia : HistoriaClinica')
       ops=@('_cargar()', '_cambiarPersona(opcion)', '_descargarReceta(atencion)', 'verHistoriaClinica(client, patientId)',
             'verTextosAprobados(client, patientId)', 'conResumen(resumen, preparaciones)', 'ResumenConsulta.fromJson(json)') },
    @{ k='firma'; n='ControladorFirmaAtencion'; rol='control'; col=2; f=0
       nota='EncounterSignView en encounters/views.py; la firma es sign() de encounters/services.py. El reintento es ConsultationSummaryView en ai/views.py.'
       ops=$OPS_FIRMA },
    @{ k='gresumen'; n='GestorResumenConsulta'; rol='control'; col=2; f=1
       nota='Funciones de ai/consultation_summary.py. Llama a Gemini con su propio _call_model (google-genai), no con assistant/generation.py.'
       ops=@('_cut(text)', 'data_of(encounter)', 'context(encounter)', 'context_from(datos)', '_normalize(text)',
             'warnings(encounter, text)', 'warnings_for(medications, text)', 'provider_available()', 'generate(encounter)', '_call_model(contexto)') },
    @{ k='gtextos'; n='GestorTextosIA'; rol='control'; col=2; f=2
       nota='Funciones de ai/services.py: la única puerta de entrada (create_draft) y de lectura del paciente (approved_for).'
       ops=$OPS_TEXTOS_IA },
    @{ k='ctrlmios'; n='ControladorTextosPaciente'; rol='control'; col=2; f=3
       nota='PatientTextsView en ai/views.py (GET /api/ai/texts/mine/) con PatientTextSerializer de ai/serializers.py: sólo final_text.'
       ops=@('get_queryset()', 'get_encounter_date(obj)', 'get_order_description(obj)') },
    @{ k='texto'; n='TextoGeneradoIA'; rol='entity'; col=3; f=2
       nota='Tabla ai_generated_texts (AiGeneratedText en ai/models.py). Un trigger la vuelve inmutable al dejar draft.'
       atr=$ATR_TEXTO_IA
       ops=@('was_edited()') },
    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=1 }
  )
  rel = @()
  grupos = [ordered]@{ 1 = 'Firmar y generar el borrador'; 2 = 'La IA no está o no respondió'; 3 = 'El paciente lee el resumen aprobado' }
  guion = @(
    @{ t='msg'; g=1; o='medico'; d='pantalla'; m='firmar()'; src='Atencion.tsx:100' },
    @{ t='msg'; g=1; o='pantalla'; d='firma'; m='post(request, pk)'; src='firmarEncuentro: POST /api/encounters/{id}/sign/; api/atencion.ts:201; encounters/views.py:170' },
    @{ t='msg'; g=1; o='firma'; d='firma'; m='sign(encounter, user)'; src='encounters/services.py:154-178; UPDATE encounters SET status=signed, signed_at, signed_by' },
    @{ t='msg'; g=1; o='firma'; d='gresumen'; m='generate(encounter)'; src='encounters/views.py:177-178; consultation_summary.py:193' },
    @{ t='msg'; g=1; o='gresumen'; d='texto'; m='filter(kind, encounter).exclude(discarded)'; src='consultation_summary.py:203-206' },
    @{ t='alt' },
    @{ t='op'; g='no hay resumen vivo y hay proveedor' },
    @{ t='msg'; g=1; o='gresumen'; d='gresumen'; m='context(encounter)'; src='consultation_summary.py:94, :113; motivo, diagnóstico, receta y órdenes, sin nombre' },
    @{ t='msg'; g=1; o='gresumen'; d='ia'; m='generate_content(model, contents, config)'; src='_call_model, consultation_summary.py:232-248; temperature 0.2, 600 tokens, 20 s' },
    @{ t='msg'; g=1; o='ia'; d='gresumen'; m='response.text'; ret=$true; src='consultation_summary.py:248' },
    @{ t='msg'; g=1; o='gresumen'; d='gtextos'; m='create_draft(kind, encounter, text, ...)'; src='consultation_summary.py:224; ai/services.py:49' },
    @{ t='msg'; g=1; o='gtextos'; d='texto'; m='create(organization_id, kind, patient_id, ...)'; src='ai/services.py:71; INSERT INTO ai_generated_texts (status=draft)' },
    @{ t='msg'; g=1; o='gresumen'; d='firma'; m='{status: generated, text_id}'; ret=$true; src='consultation_summary.py:229' },
    @{ t='op'; g='sin proveedor, o el modelo falló o vino vacío' },
    @{ t='msg'; g=2; o='gresumen'; d='firma'; m='{status: unavailable | failed}'; ret=$true; src='consultation_summary.py:210, :220' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='firma'; d='pantalla'; m='200(encuentro, patient_summary)'; ret=$true; src='encounters/views.py:192' },
    @{ t='msg'; g=1; o='pantalla'; d='pantalla'; m='AvisoResumenPaciente(encuentroId, resultado)'; src='Atencion.tsx:105, :151; TextosPorValidar.tsx:128' },
    @{ t='msg'; g=3; o='paciente'; d='pantallahist'; m='verHistoriaClinica(persona)'; src='clinical_record_screen.dart:129' },
    @{ t='msg'; g=3; o='pantallahist'; d='ctrlmios'; m='get_queryset()'; src='verTextosAprobados: GET /api/ai/texts/mine/?patient=; clinical_record_api.dart:429-435; ai/views.py:189' },
    @{ t='msg'; g=3; o='ctrlmios'; d='gtextos'; m='approved_for(user)'; src='ai/views.py:190; ai/services.py:216' },
    @{ t='msg'; g=3; o='gtextos'; d='texto'; m='filter(organization, patient_id__in, approved)'; src='ai/services.py:222-226; WHERE status = approved' },
    @{ t='msg'; g=3; o='ctrlmios'; d='pantallahist'; m='200(results)'; ret=$true; src='ai/views.py:207; PatientTextSerializer, ai/serializers.py:88' },
    @{ t='msg'; g=3; o='pantallahist'; d='pantallahist'; m='conResumen(resumen, preparaciones)'; src='clinical_record_api.dart:250, :419; _Resumen, clinical_record_screen.dart:501' }
  )
}

# -------------------------------------------------------------------------
# CU41 (US-40) Generacion de Indicaciones de Preparacion
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU41'] = @{
  cu = 'CU41'; nombre = 'Generación de Indicaciones de Preparación'; us = 'US-40'; plataforma = 'web'
  nota = 'Al firmar la atención, ai/study_preparation.generate_for_encounter recorre las órdenes: busca la preparación en el catálogo (services.preparation) por nombre o en el corpus de US-32 (retrieve), la redacta con Gemini y la deja en borrador; sin proveedor queda el texto del catálogo y sin fuente no se genera. El paciente la ve en el móvil junto a la orden, aprobada.'
  participantes = @(
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaAtencion'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Atencion.tsx (firmar) y api/atencion.ts (firmarEncuentro). La respuesta trae study_preparations pero la web no la muestra; el paciente la lee en el móvil: _Preparacion en mobile/lib/features/clinical_record/clinical_record_screen.dart, verTextosAprobados en clinical_record_api.dart.'
       atr=@('POST /api/encounters/{id}/sign/ : 200 | 400 | 409', 'POST /api/ai/orders/{id}/preparation/ : 200 | 404 | 409')
       ops=$OPS_PANTALLA_ATENCION },
    @{ k='firma'; n='ControladorFirmaAtencion'; rol='control'; col=2; f=0
       nota='EncounterSignView en encounters/views.py. El reintento por orden es StudyPreparationView en ai/views.py (POST /api/ai/orders/{id}/preparation/).'
       ops=$OPS_FIRMA },
    @{ k='gprep'; n='GestorPreparacionEstudio'; rol='control'; col=2; f=1
       nota='Funciones de ai/study_preparation.py. Llama a Gemini con su propio _call_model (google-genai).'
       ops=@('_normalize(text)', '_palabras(text)', '_parecido(nombre, pedido)', 'find_by_name(order)', 'find_in_corpus(order)',
             'source_for(order)', '_cut(text)', 'context(order, service)', 'catalog_text(order, service)', 'warnings_for(text, source)',
             'warnings(texto)', 'provider_available()', 'generate(order)', 'generate_for_encounter(encounter)', '_call_model(contexto)') },
    @{ k='grecup'; n='GestorRecuperacion'; rol='control'; col=2; f=2
       nota='assistant/retrieval.py (corpus de US-31/US-32, tabla assistant_catalog_fragments, filtro por organización antes del orden por similitud) y embed_query de assistant/embeddings.py.'
       ops=@('retrieve(organization, question, limit)', 'rank_specialties(fragments)', '_source_names(organization, fragments)',
             'is_administrative(fragment)', 'embed_query(question)') },
    @{ k='gtextos'; n='GestorTextosIA'; rol='control'; col=2; f=3
       nota='Funciones de ai/services.py.'
       ops=$OPS_TEXTOS_IA },
    @{ k='orden'; n='OrdenMedica'; rol='entity'; col=3; f=0
       nota='Tabla encounter_orders (MedicalOrder en encounters/models.py).'
       atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'kind : varchar(12)', 'description : varchar(300)',
             'notes : varchar(300)', 'created_at : timestamptz')
       ops=@() },
    @{ k='servicio'; n='Servicio'; rol='entity'; col=3; f=1.5
       nota='Tabla services (Service en catalog/models.py): preparation es la fuente.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'kind : varchar(20)', 'specialty_id : uuid',
             'description : text', 'preparation : text', 'price : numeric', 'currency : varchar(3)', 'is_active : boolean',
             'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@() },
    @{ k='texto'; n='TextoGeneradoIA'; rol='entity'; col=3; f=3
       nota='Tabla ai_generated_texts (kind = preparation; una sola viva por orden).'
       atr=$ATR_TEXTO_IA
       ops=@('was_edited()') },
    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=2 }
  )
  rel = @(
    @{ d='orden'; a='texto'; cd='1'; ca='0..*'; r='tiene preparación' }
  )
  grupos = [ordered]@{ 1 = 'Generar la preparación con IA'; 2 = 'Sin IA: queda el texto del catálogo'; 3 = 'El catálogo no tiene preparación' }
  guion = @(
    @{ t='msg'; g=1; o='medico'; d='pantalla'; m='firmar()'; src='Atencion.tsx:100' },
    @{ t='msg'; g=1; o='pantalla'; d='firma'; m='post(request, pk)'; src='firmarEncuentro: POST /api/encounters/{id}/sign/; api/atencion.ts:201; encounters/views.py:170' },
    @{ t='msg'; g=1; o='firma'; d='gprep'; m='generate_for_encounter(encounter)'; src='encounters/views.py:184-185; study_preparation.py:292' },
    @{ t='msg'; g=1; o='gprep'; d='orden'; m='orders.all()'; src='study_preparation.py:295' },
    @{ t='loop'; g='por cada orden de la atención' },
    @{ t='msg'; g=1; o='gprep'; d='texto'; m='filter(kind, medical_order).exclude(discarded)'; src='generate, study_preparation.py:260-263' },
    @{ t='msg'; g=1; o='gprep'; d='servicio'; m='filter(organization_id, is_active)'; src='find_by_name, study_preparation.py:121-138; .exclude(preparation=""); _parecido >= 0.75' },
    @{ t='alt' },
    @{ t='op'; g='el nombre no corresponde: se busca en el corpus' },
    @{ t='msg'; g=1; o='gprep'; d='grecup'; m='retrieve(organization, pregunta, limit=5)'; src='find_in_corpus, study_preparation.py:160; retrieval.py:117' },
    @{ t='msg'; g=1; o='grecup'; d='ia'; m='embed_query(question)'; src='retrieval.py:134; embeddings.py:181' },
    @{ t='msg'; g=1; o='grecup'; d='grecup'; m='filter(organization).order_by(distance)[:5]'; src='retrieval.py:137-141; SELECT ... FROM assistant_catalog_fragments WHERE organization_id ORDER BY embedding <=> v' },
    @{ t='msg'; g=1; o='grecup'; d='gprep'; m='fragmentos'; ret=$true; src='retrieval.py:164' },
    @{ t='msg'; g=1; o='gprep'; d='servicio'; m='filter(pk=source_id, is_active).first()'; src='study_preparation.py:170-176' },
    @{ t='op'; g='ni el nombre ni el corpus dan una fuente' },
    @{ t='msg'; g=3; o='gprep'; d='firma'; m='{order, status: no_source}'; ret=$true; src='study_preparation.py:268-269' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='hay proveedor y el modelo respondió' },
    @{ t='msg'; g=1; o='gprep'; d='gprep'; m='context(order, service)'; src='study_preparation.py:193, :274' },
    @{ t='msg'; g=1; o='gprep'; d='ia'; m='generate_content(model, contents, config)'; src='_call_model, study_preparation.py:304-320; temperature 0.2, 400 tokens' },
    @{ t='msg'; g=1; o='ia'; d='gprep'; m='response.text'; ret=$true; src='study_preparation.py:320' },
    @{ t='op'; g='sin proveedor o sin respuesta' },
    @{ t='msg'; g=2; o='gprep'; d='gprep'; m='catalog_text(order, service)'; src='study_preparation.py:204, :281; generated_by = catalogo' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='gprep'; d='gtextos'; m='create_draft(kind, medical_order, text, ...)'; src='study_preparation.py:285-286; ai/services.py:49' },
    @{ t='msg'; g=1; o='gtextos'; d='texto'; m='create(organization_id, kind, medical_order)'; src='ai/services.py:71; INSERT INTO ai_generated_texts (status=draft)' },
    @{ t='msg'; g=1; o='gprep'; d='firma'; m='{order, status: generated | from_catalog}'; ret=$true; src='study_preparation.py:289' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='firma'; d='pantalla'; m='200(encuentro, study_preparations)'; ret=$true; src='encounters/views.py:186-193' }
  )
}

# -------------------------------------------------------------------------
# CU42 (US-41) Generacion de Resumen de Historia Clinica
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU42'] = @{
  cu = 'CU42'; nombre = 'Generación de Resumen de Historia Clínica'; us = 'US-41'; plataforma = 'web'
  nota = 'En la atención, el médico con vínculo pide el resumen del historial (GET /api/encounters/history/{paciente}/summary/); encounters/summary.summarize manda a Gemini las últimas 10 atenciones firmadas numeradas, descarta toda oración sin cita válida y devuelve aparte las alergias leídas de la base. Sin IA, copia los diagnósticos. No se guarda en ai_generated_texts.'
  participantes = @(
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=1.5 },
    @{ k='pantalla'; n='PantallaResumenHistorial'; rol='boundary'; col=1; f=1.5
       nota='Web: PanelResumenHistorial en frontend/src/paginas/ResumenHistorial.tsx, dentro de paginas/Atencion.tsx; api/atencion.ts (verResumenHistorial).'
       atr=@('GET /api/encounters/history/{paciente}/summary/ : 200 | 404', 'datos : ResumenHistorial', 'cargando : boolean')
       ops=@('PanelResumenHistorial(pacienteId)', 'pedir()', 'fuente(ref)', 'verResumenHistorial(pacienteId, contexto, senal)') },
    @{ k='ctrl'; n='ControladorResumenHistorial'; rol='control'; col=2; f=0
       nota='PatientHistorySummaryView en encounters/history_views.py. Pide encounters.history.read.'
       ops=@('get(request, patient_id)') },
    @{ k='galcance'; n='GestorAtenciones'; rol='control'; col=2; f=1
       nota='encounters/services.py: history_scope decide OWN, PROFESSIONAL o nada.'
       ops=@('practitioner_of(user)', 'is_own(user, encounter)', 'history_scope(user, patient)', 'open_encounter(user, appointment)',
             'update_draft(encounter, data)', 'sign(encounter, user)', 'amend(encounter, user, section, text)') },
    @{ k='gresumen'; n='GestorResumenHistorial'; rol='control'; col=2; f=2
       nota='Funciones de encounters/summary.py. Llama a Gemini con su propio _call_model (google-genai).'
       ops=@('_recortar(texto)', '_texto_de(encuentro, seccion)', '_fuentes(encuentros)', '_contexto(encuentros)', '_alertas(paciente)',
             '_mover_citas(texto)', 'verificar(texto, total)', '_plantilla(fuentes)', 'summarize(paciente)', '_call_model(contexto)') },
    @{ k='bitacora'; n='GestorBitacora'; rol='control'; col=2; f=3
       nota='audit/services.py: deja RECORD_READ con origen resumen y quién lo redactó, sin el texto.'
       ops=$OPS_BITACORA_S4 },
    @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=0
       nota='Tabla patients.'
       atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'relationship : varchar', 'document_type : varchar',
             'document_number : varchar(20)', 'first_name : varchar(80)', 'last_name : varchar(80)', 'birth_date : date', 'sex : varchar(1)',
             'phone : varchar(30)', 'is_active : boolean', 'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@() },
    @{ k='encuentro'; n='Encuentro'; rol='entity'; col=3; f=1.5
       nota='Tabla encounters (sólo las firmadas entran al resumen).'
       atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid',
             'status : varchar', 'reason : text', 'evolution : text', 'diagnosis : text', 'indications : text', 'treatment : text',
             'signed_at : timestamptz', 'signed_by_id : uuid', 'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@() },
    @{ k='antecedente'; n='Antecedente'; rol='entity'; col=3; f=3
       nota='Tabla patient_history_entries (US-08): alergias, condiciones y medicación declaradas.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'kind : varchar(20)', 'description : varchar(200)', 'severity : varchar',
             'source : varchar', 'declared_by_id : uuid', 'recorded_at : date', 'is_active : boolean', 'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@() },
    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=1.5 }
  )
  rel = @(
    @{ d='paciente'; a='encuentro'; cd='1'; ca='0..*'; r='es atendido en' },
    @{ d='paciente'; a='antecedente'; cd='1'; ca='0..*'; r='declara' }
  )
  grupos = [ordered]@{ 1 = 'Resumir el historial con citas'; 2 = 'Sin IA: diagnósticos copiados'; 3 = 'Sin vínculo de atención' }
  guion = @(
    @{ t='msg'; g=1; o='medico'; d='pantalla'; m='generarResumen()'; src='ResumenHistorial.tsx:27, :43' },
    @{ t='msg'; g=1; o='pantalla'; d='ctrl'; m='get(request, patient_id)'; src='verResumenHistorial: GET /api/encounters/history/{id}/summary/; api/atencion.ts:252; history_views.py:103' },
    @{ t='msg'; g=1; o='ctrl'; d='paciente'; m='filter(organization, pk).first()'; src='history_views.py:106-108' },
    @{ t='msg'; g=1; o='ctrl'; d='galcance'; m='history_scope(user, patient)'; src='history_views.py:109; encounters/services.py:243' },
    @{ t='alt' },
    @{ t='op'; g='alcance professional: tuvo una ficha con el paciente' },
    @{ t='msg'; g=1; o='ctrl'; d='gresumen'; m='summarize(paciente)'; src='history_views.py:112; summary.py:195' },
    @{ t='msg'; g=1; o='gresumen'; d='encuentro'; m='filter(organization, patient, signed)[:10]'; src='summary.py:197-204; ORDER BY appointment.starts_at DESC' },
    @{ t='msg'; g=1; o='gresumen'; d='gresumen'; m='_fuentes(encuentros)'; src='summary.py:97, :205; [A1], [A2]...' },
    @{ t='msg'; g=1; o='gresumen'; d='antecedente'; m='filter(organization, patient, is_active)'; src='_alertas, summary.py:133-138' },
    @{ t='alt' },
    @{ t='op'; g='hay proveedor y quedan oraciones citadas' },
    @{ t='msg'; g=1; o='gresumen'; d='ia'; m='generate_content(model, contents, config)'; src='_call_model(_contexto(encuentros)), summary.py:219, :235-250; temperature 0.1' },
    @{ t='msg'; g=1; o='ia'; d='gresumen'; m='response.text'; ret=$true; src='summary.py:250' },
    @{ t='msg'; g=1; o='gresumen'; d='gresumen'; m='verificar(texto, total)'; src='summary.py:160-183; descarta la oración sin cita o con cita inexistente' },
    @{ t='op'; g='sin proveedor, error o ninguna oración citada' },
    @{ t='msg'; g=2; o='gresumen'; d='gresumen'; m='_plantilla(fuentes)'; src='summary.py:186, :230; generated_by = plantilla' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='gresumen'; d='ctrl'; m='{alerts, sources, sentences, generated_by}'; ret=$true; src='summary.py:226-232' },
    @{ t='msg'; g=1; o='ctrl'; d='bitacora'; m='record(request, RECORD_READ, patients, ...)'; src='history_views.py:113-118' },
    @{ t='msg'; g=1; o='ctrl'; d='pantalla'; m='200(patient, alerts, sources, sentences)'; ret=$true; src='history_views.py:119' },
    @{ t='op'; g='otro médico sin ficha, o el propio paciente' },
    @{ t='msg'; g=3; o='ctrl'; d='pantalla'; m='404'; ret=$true; src='history_views.py:109-110' },
    @{ t='fin' }
  )
}

# -------------------------------------------------------------------------
# CU43 (US-42) Validacion de Contenido Generado por IA
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU43'] = @{
  cu = 'CU43'; nombre = 'Validación de Contenido Generado por IA'; us = 'US-42'; plataforma = 'web'
  nota = 'El médico de la atención revisa en «Textos por validar» los borradores de ai_generated_texts (resumen de consulta y preparación), ve la diferencia con el texto del modelo, y los corrige, aprueba o descarta (ai/views.py y ai/services.py). La decisión es una sola: _lock_draft bloquea la fila y un trigger la vuelve inmutable.'
  participantes = @(
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=3 },
    @{ k='pantalla'; n='PantallaTextosPorValidar'; rol='boundary'; col=1; f=3
       nota='Web: frontend/src/paginas/TextosPorValidar.tsx (ruta /textos-ia) y frontend/src/api/textos_ia.ts. Sólo con ai.text.review.'
       atr=@('GET /api/ai/texts/?status= : 200', 'PATCH /api/ai/texts/{id}/ : 200 | 400 | 404 | 409', 'POST /api/ai/texts/{id}/approve/ : 200 | 404 | 409',
             'POST /api/ai/texts/{id}/discard/ : 200 | 404 | 409', 'estado : EstadoTexto', 'textos : TextoIa[]', 'valor : string')
       ops=@('TextosPorValidar()', 'recargar(signal)', 'cambiarPestana(e)', 'decidido(t, mensaje)', 'Pendiente(texto, onDecidido)', 'hacer(accion)',
             'Decidido(texto)', 'Diferencia(tramos)', 'Origen(texto)', 'verBandeja(estado, pagina, contexto, senal)',
             'corregirTexto(id, final_text, contexto)', 'aprobarTexto(id, final_text, contexto)', 'descartarTexto(id, contexto)') },
    @{ k='bandeja'; n='ControladorBandejaTextos'; rol='control'; col=2; f=0
       nota='InboxView en ai/views.py (GET /api/ai/texts/).'
       ops=@('get_queryset()') },
    @{ k='serial'; n='SerializadorRevision'; rol='control'; col=2; f=1
       nota='ReviewSerializer en ai/serializers.py: texto del modelo, corregido, diferencia y advertencias.'
       ops=@('get_encounter_date(obj)', 'get_order_description(obj)', 'get_reviewed_by_name(obj)', 'get_diff(obj)', 'get_warnings(obj)') },
    @{ k='detalle'; n='ControladorDetalleTexto'; rol='control'; col=2; f=2
       nota='TextDetailView en ai/views.py (GET y PATCH /api/ai/texts/{id}/) y _texto_propio: 404 si no es del médico.'
       ops=@('get(request, pk)', 'patch(request, pk)', '_texto_propio(request, pk)', '_asiento(request, action, texto, extra)') },
    @{ k='aprobar'; n='ControladorAprobarTexto'; rol='control'; col=2; f=3
       nota='ApproveView en ai/views.py (POST /api/ai/texts/{id}/approve/) con ApproveSerializer.'
       ops=@('post(request, pk)') },
    @{ k='descartar'; n='ControladorDescartarTexto'; rol='control'; col=2; f=4
       nota='DiscardView en ai/views.py (POST /api/ai/texts/{id}/discard/).'
       ops=@('post(request, pk)') },
    @{ k='gtextos'; n='GestorTextosIA'; rol='control'; col=2; f=5
       nota='Funciones de ai/services.py; Conflict (409) si el texto ya no es borrador.'
       ops=$OPS_TEXTOS_IA },
    @{ k='bitacora'; n='GestorBitacora'; rol='control'; col=2; f=6
       nota='audit/services.py: AI_TEXT_EDIT, AI_TEXT_APPROVE (con corregido) y AI_TEXT_DISCARD.'
       ops=$OPS_BITACORA_S4 },
    @{ k='texto'; n='TextoGeneradoIA'; rol='entity'; col=3; f=3
       nota='Tabla ai_generated_texts (AiGeneratedText en ai/models.py): draft -> approved | discarded, una sola vez (trigger trg_ai_generated_texts_inmutable).'
       atr=$ATR_TEXTO_IA
       ops=@('was_edited()') }
  )
  rel = @()
  grupos = [ordered]@{ 1 = 'Listar los pendientes'; 2 = 'Corregir y aprobar'; 3 = 'Descartar'; 4 = 'Texto ajeno o ya decidido' }
  guion = @(
    @{ t='msg'; g=1; o='medico'; d='pantalla'; m='abrirTextosPorValidar()'; src='TextosPorValidar.tsx:212, :224' },
    @{ t='msg'; g=1; o='pantalla'; d='bandeja'; m='get_queryset()'; src='verBandeja(draft, pagina): GET /api/ai/texts/?status=draft; api/textos_ia.ts:46; ai/views.py:71' },
    @{ t='msg'; g=1; o='bandeja'; d='gtextos'; m='inbox_for(user)'; src='ai/views.py:73; ai/services.py:87' },
    @{ t='msg'; g=1; o='gtextos'; d='texto'; m='filter(organization, practitioner, draft)'; src='ai/services.py:92-99; ai/views.py:77-80, ORDER BY created_at' },
    @{ t='msg'; g=1; o='bandeja'; d='serial'; m='get_diff(obj)'; src='ai/serializers.py:57' },
    @{ t='msg'; g=1; o='serial'; d='gtextos'; m='diff(generated_text, final_text)'; src='ai/services.py:171' },
    @{ t='msg'; g=1; o='bandeja'; d='pantalla'; m='200(results, count)'; ret=$true; src='ListAPIView paginada' },
    @{ t='msg'; g=2; o='medico'; d='pantalla'; m='guardarSinAprobar(valor)'; src='TextosPorValidar.tsx:59, :105' },
    @{ t='msg'; g=2; o='pantalla'; d='detalle'; m='patch(request, pk)'; src='corregirTexto: PATCH /api/ai/texts/{id}/; api/textos_ia.ts:49; ai/views.py:89; _texto_propio (inbox_for(user).filter(pk)), :53-57' },
    @{ t='msg'; g=2; o='detalle'; d='gtextos'; m='edit(texto, final_text)'; src='ai/views.py:93; ai/services.py:124' },
    @{ t='msg'; g=2; o='gtextos'; d='texto'; m='select_for_update().get(pk)'; src='_lock_draft, ai/services.py:118' },
    @{ t='msg'; g=2; o='gtextos'; d='texto'; m='save(update_fields=[final_text])'; src='ai/services.py:128-129' },
    @{ t='msg'; g=2; o='detalle'; d='pantalla'; m='200(texto, diff)'; ret=$true; src='ai/views.py:95' },
    @{ t='msg'; g=2; o='medico'; d='pantalla'; m='aprobar()'; src='TextosPorValidar.tsx:60-62, :100' },
    @{ t='msg'; g=2; o='pantalla'; d='aprobar'; m='post(request, pk)'; src='aprobarTexto: POST /api/ai/texts/{id}/approve/; api/textos_ia.ts:52; ai/views.py:101' },
    @{ t='alt' },
    @{ t='op'; g='es del médico y sigue en borrador' },
    @{ t='msg'; g=2; o='aprobar'; d='gtextos'; m='approve(texto, user, final_text)'; src='ai/views.py:105; ai/services.py:133' },
    @{ t='msg'; g=2; o='gtextos'; d='texto'; m='save(approved, reviewed_by, reviewed_at)'; src='ai/services.py:140-148; UPDATE ai_generated_texts' },
    @{ t='msg'; g=2; o='aprobar'; d='bitacora'; m='record(request, AI_TEXT_APPROVE, corregido)'; src='ai/views.py:107, :60' },
    @{ t='msg'; g=2; o='aprobar'; d='pantalla'; m='200(texto)'; ret=$true; src='ai/views.py:108' },
    @{ t='op'; g='es de otro médico o de otra organización' },
    @{ t='msg'; g=4; o='aprobar'; d='pantalla'; m='404'; ret=$true; src='_texto_propio, ai/views.py:55-56' },
    @{ t='op'; g='ya estaba aprobado o descartado' },
    @{ t='msg'; g=4; o='gtextos'; d='aprobar'; m='Conflict()'; ret=$true; src='_lock_draft, ai/services.py:119-120' },
    @{ t='msg'; g=4; o='aprobar'; d='pantalla'; m='409(detail)'; ret=$true; src='ai/services.py:39-42' },
    @{ t='fin' },
    @{ t='msg'; g=3; o='medico'; d='pantalla'; m='descartar()'; src='TextosPorValidar.tsx:64, :112' },
    @{ t='msg'; g=3; o='pantalla'; d='descartar'; m='post(request, pk)'; src='descartarTexto: POST /api/ai/texts/{id}/discard/; api/textos_ia.ts:57; ai/views.py:114' },
    @{ t='msg'; g=3; o='descartar'; d='gtextos'; m='discard(texto, user)'; src='ai/views.py:115; ai/services.py:152' },
    @{ t='msg'; g=3; o='gtextos'; d='texto'; m='save(discarded, reviewed_by, reviewed_at)'; src='ai/services.py:154-158' },
    @{ t='msg'; g=3; o='descartar'; d='bitacora'; m='record(request, AI_TEXT_DISCARD)'; src='ai/views.py:116' },
    @{ t='msg'; g=3; o='descartar'; d='pantalla'; m='200(texto)'; ret=$true; src='ai/views.py:117' }
  )
}


# =========================================================================
# Datos de CU47 (US-46), CU48 (US-47) y CU51 (US-50) del Sprint 4.
# Leídos del código el 21/11/26 (rama fix/us51-respaldo-y-v1.6.1).
# =========================================================================

# -------------------------------------------------------------------------
# CU47 (US-46) Consulta de Transacciones por Voz
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU47'] = @{
  cu = 'CU47'; nombre = 'Consulta de Transacciones por Voz'; us = 'US-46'; plataforma = 'móvil'
  nota = 'El paciente dicta o escribe una frase («mis últimas 2 facturas de octubre»); payments/mine_voice.py la traduce a una consulta cerrada (Gemini por reporting/voice.ask_model, o reglas fijas sin proveedor) y payments/mine.py lista sus pagos o fichas, de él y sus dependientes (alcance desde la sesión), cada uno con el código QR firmado de appointments/receipts.py.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaMisComprobantes'; rol='boundary'; col=1; f=2
       nota='Móvil: mobile/lib/features/receipts/my_receipts_screen.dart (MyReceiptsScreen) y my_receipts_api.dart. Web: frontend/src/paginas/MisComprobantes.tsx y api/misComprobantes.ts.'
       atr=@('POST /api/payments/mine/receipts/interpret/ : 200', 'GET /api/payments/mine/receipts/ : 200 | 400', '_propuesta : PropuestaDeComprobantes', '_lista : ListaDeComprobantes', '_puedeDictar : bool')
       ops=@('_prepararDictado()', '_hablar()', '_buscar(texto)', '_bajarPdf()', '_abrir(ruta)', 'interpretarComprobantes(client, texto)', 'listarComprobantes(client, consulta)', 'descargarComprobantesPdf(client, consulta)') },
    @{ k='vista'; n='ControladorMisComprobantes'; rol='control'; col=2; f=0
       nota='MyReceiptsInterpretView y MyReceiptsView en payments/views_mine.py (IsPatientProfile).'
       ops=@('post(request)', 'get(request)', '_como_dict(consulta)', '_pdf(request, consulta, items, grupos, truncado, resumen)') },
    @{ k='interprete'; n='GestorConsultaPorVoz'; rol='control'; col=2; f=1
       nota='Funciones de payments/mine_voice.py: de la frase a una consulta de la lista cerrada (pagos | fichas).'
       ops=@('interpretar_consulta(texto, user, hoy)', '_contexto_del_centro(user)', 'sin_agrupacion(texto, profesionales)', 'sin_profesional(texto, profesionales)', 'detectar_no_soportado(texto, nombres)', 'analizar(texto, especialidades, hoy, nombres, profesionales)', 'pedido_al_modelo(texto, especialidades, hoy)', 'sanear_consulta(crudo, especialidades, hoy, nombres, agrupar, profesional)', 'resumen(consulta)', '_nada(motivos, generated_by)') },
    @{ k='voz'; n='GestorVozReportes'; rol='control'; col=2; f=2
       nota='reporting/voice.py: el gate del proveedor y la llamada a Gemini (temperature=0), compartidos con la característica 5.'
       ops=@('interpret(text, user, dataset_code)', 'proveedor_disponible()', 'ask_model(system_prompt, prompt)', '_call_model(prompt)', '_call_model_with(system_prompt, prompt)') },
    @{ k='consulta'; n='GestorComprobantes'; rol='control'; col=2; f=3
       nota='Funciones de payments/mine.py: valida la consulta, aplica el alcance (titular y dependientes) y serializa con el QR.'
       ops=@('parse_consulta(params, organization)', 'alcance(user, prefijo)', 'consultar(user, consulta)', 'listar(user, consulta)', 'serializar(objeto, tipo, titular)', 'agrupar_items(items, por)', 'titulo_del_pdf(consulta)', 'filas_del_pdf(items, grupos)') },
    @{ k='recibo'; n='GestorComprobanteQR'; rol='control'; col=2; f=4
       nota='appointments/receipts.py: código MC1. firmado con django.core.signing (ReceiptView para el comprobante suelto).'
       ops=@('issue_code(appointment)', 'read_code(code, organization)', 'receipt_payload(appointment)', 'get(request, pk)') },
    @{ k='pago'; n='Pago'; rol='entity'; col=3; f=1
       nota='Tabla payments (payments/models.py, Payment).'
       atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'created_by_id : uuid', 'amount : decimal(10,2)', 'currency : varchar(3)', 'provider : varchar(12)', 'status : varchar', 'provider_payment_id : varchar(255)', 'paid_at : timestamptz', 'refunded_at : timestamptz', 'created_at : timestamptz')
       ops=@() },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=3
       nota='Tabla appointments (appointments/models.py, Appointment); con comprobante: confirmed o attended.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar', 'created_at : timestamptz')
       ops=@() },
    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=2 }
  )
  rel = @(
    @{ d='ficha'; a='pago'; cd='1'; ca='0..*'; r='se paga con' }
  )
  grupos = [ordered]@{ 1 = 'De la frase a la lista con QR'; 2 = 'Sin proveedor de IA: reglas fijas'; 3 = 'No entendió la frase' }
  guion = @(
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='dictarConsulta(frase)'; src='my_receipts_screen.dart:126 (_hablar) y :153 (_buscar)' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='post(request)'; src='interpretarComprobantes: POST /api/payments/mine/receipts/interpret/; my_receipts_api.dart:262; views_mine.py:44' },
    @{ t='msg'; g=1; o='vista'; d='interprete'; m='interpretar_consulta(texto, user)'; src='views_mine.py:48; mine_voice.py:774' },
    @{ t='msg'; g=1; o='interprete'; d='interprete'; m='_contexto_del_centro(user)'; src='mine_voice.py:790, :829 (especialidades y profesionales activos del centro)' },
    @{ t='msg'; g=1; o='interprete'; d='voz'; m='ask_model(SYSTEM_PROMPT_PACIENTE, pedido)'; src='mine_voice.py:803; voice.py:176' },
    @{ t='alt' },
    @{ t='op'; g='hay proveedor y responde' },
    @{ t='msg'; g=1; o='voz'; d='ia'; m='generate_content(model, contents, config)'; src='voice.py:188, :209 (_call_model_with)' },
    @{ t='msg'; g=1; o='ia'; d='voz'; m='json(tipo, cantidad, desde, hasta, ...)'; ret=$true; src='voice.py:209-220' },
    @{ t='msg'; g=1; o='voz'; d='interprete'; m='(crudo, "gemini")'; ret=$true; src='voice.py:191' },
    @{ t='msg'; g=1; o='interprete'; d='interprete'; m='sanear_consulta(crudo, especialidades, hoy)'; src='mine_voice.py:809, :650' },
    @{ t='op'; g='sin proveedor o la llamada falla' },
    @{ t='msg'; g=2; o='voz'; d='interprete'; m='(None, "plantilla")'; ret=$true; src='voice.py:185-190' },
    @{ t='msg'; g=2; o='interprete'; d='interprete'; m='analizar(texto, especialidades, hoy)'; src='mine_voice.py:814, :342' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='entendió la consulta' },
    @{ t='msg'; g=1; o='interprete'; d='vista'; m='{understood, consulta, spoken_summary}'; ret=$true; src='mine_voice.py:820' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='200(propuesta)'; ret=$true; src='views_mine.py:52 (bitácora sin la frase), :66' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='get(request)'; src='listarComprobantes: GET /api/payments/mine/receipts/?tipo=&cantidad=&desde=&hasta=; my_receipts_screen.dart:170; views_mine.py:84' },
    @{ t='msg'; g=1; o='vista'; d='consulta'; m='parse_consulta(query_params, organization)'; src='views_mine.py:85; mine.py:102' },
    @{ t='msg'; g=1; o='vista'; d='consulta'; m='listar(user, consulta)'; src='views_mine.py:99; mine.py:261 -> consultar, :210' },
    @{ t='alt' },
    @{ t='op'; g='tipo = pagos' },
    @{ t='msg'; g=1; o='consulta'; d='pago'; m='filter(organization, status, alcance(user))'; src='mine.py:214-231; SELECT ... FROM payments JOIN appointments WHERE status=succeeded AND (patient_id=:t OR patient.guardian_id=:t) ORDER BY fecha DESC LIMIT n+1' },
    @{ t='op'; g='tipo = fichas' },
    @{ t='msg'; g=1; o='consulta'; d='ficha'; m='filter(status__in, alcance(user))'; src='mine.py:233-240; SELECT * FROM appointments WHERE status IN (confirmed, attended) AND (patient_id=:t OR ...) ORDER BY starts_at DESC' },
    @{ t='fin' },
    @{ t='loop'; g='por cada pago o ficha, hasta el límite' },
    @{ t='msg'; g=1; o='vista'; d='consulta'; m='serializar(objeto, tipo, titular)'; src='views_mine.py:100; mine.py:270' },
    @{ t='msg'; g=1; o='consulta'; d='recibo'; m='issue_code(cita)'; src='mine.py:277; receipts.py:53 (MC1. + signing.dumps)' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='vista'; d='consulta'; m='agrupar_items(items, agrupar)'; src='views_mine.py:101; mine.py:317' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='200(items, groups, summary)'; ret=$true; src='views_mine.py:107' },
    @{ t='msg'; g=1; o='pantalla'; d='paciente'; m='lista con el QR de cada comprobante'; ret=$true; src='my_receipts_screen.dart:607 (QrImageView del code)' },
    @{ t='op'; g='no entendió (unresolved)' },
    @{ t='msg'; g=3; o='interprete'; d='vista'; m='_nada(unresolved, generado_por)'; ret=$true; src='mine_voice.py:819, :767' },
    @{ t='msg'; g=3; o='vista'; d='pantalla'; m='200(understood=false, unresolved)'; ret=$true; src='views_mine.py:66' },
    @{ t='msg'; g=3; o='pantalla'; d='paciente'; m='muestra lo que no entendió'; ret=$true; src='my_receipts_screen.dart:263, :381 (_LoQueEntendio); no pide la lista' },
    @{ t='fin' }
  )
}

# -------------------------------------------------------------------------
# CU48 (US-47) Chat con el Médico Tratante
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU48'] = @{
  cu = 'CU48'; nombre = 'Chat con el Médico Tratante'; us = 'US-47'; plataforma = 'móvil'
  nota = 'Una conversación por atención firmada (backend/messaging/, PR #100 y #111): el paciente escribe desde el móvil, assistant/triage.check marca lo que suena a urgencia y le muestra la derivación; el médico responde desde la web y notifications/push avisa al paciente por FCM después del COMMIT. Pasados 15 días de la firma (ENCOUNTER_CHAT_DAYS) o si el médico la cerró, queda en sólo lectura.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=1 },
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=3 },
    @{ k='pantalla'; n='PantallaChat'; rol='boundary'; col=1; f=2
       nota='Móvil (paciente): mobile/lib/features/chat/chat_screen.dart (ChatScreen) y chat_api.dart. Web (médico y paciente): frontend/src/paginas/ChatAtencion.tsx (PanelChat, ConsultasPacientes) y api/chat.ts.'
       atr=@('GET /api/messaging/encounters/{id}/chat/ : 200 | 404', 'POST /api/messaging/encounters/{id}/chat/messages/ : 201 | 400 | 409', '_urgencia : String?', 'canWrite : bool', 'closedReason : closed | expired')
       ops=@('_cargar()', '_enviar()', '_alFinal()', 'verConversacion(client, encounterId)', 'escribirMensaje(client, encounterId, body)', 'enviar(e)', 'cerrar()', 'cerrarConversacion(encuentroId, contexto)', 'verBandejaChat(contexto)') },
    @{ k='vista'; n='ControladorChat'; rol='control'; col=2; f=0
       nota='ChatView, SendMessageView, CloseChatView e InboxView en messaging/views.py (permiso CanChat).'
       ops=@('get(request, encounter_id)', 'post(request, encounter_id)', 'get(request)', '_atencion(request, encounter_id)', '_conversacion(encounter, lado, thread)', '_mensaje(m, lado_de_quien_lee)', '_uuid(valor)') },
    @{ k='gestor'; n='GestorChat'; rol='control'; col=2; f=1.3
       nota='Funciones de messaging/services.py; side_of usa history_scope de encounters/services.py.'
       ops=@('window_days()', 'side_of(user, encounter)', 'encounter_for(user, encounter_id)', 'closes_at(encounter)', 'can_write(encounter, thread, now)', 'thread_of(encounter)', '_thread_for_update(encounter)', '_clean(body)', 'send(user, encounter, side, body)', 'mark_read(thread, side)', 'close(user, encounter)', 'inbox_for(user)', 'notify_patient(encounter_id, organization_id)') },
    @{ k='triage'; n='GestorTriage'; rol='control'; col=2; f=2.6
       nota='assistant/triage.py: barrera de urgencias por reglas, sin proveedor (TriageResult).'
       ops=@('check(question)') },
    @{ k='avisos'; n='GestorAvisosPush'; rol='control'; col=2; f=4
       nota='notifications/push.py: envío por FCM HTTP v1; nunca propaga errores.'
       ops=@('_read_credentials(raw)', '_authorized_session()', '_payload(token, message)', '_is_dead(response)', 'send_to_user(user, message)') },
    @{ k='hilo'; n='ConversacionAtencion'; rol='entity'; col=3; f=1
       nota='Tabla encounter_threads (messaging/models.py, EncounterThread): una por atención.'
       atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'patient_read_at : timestamptz', 'practitioner_read_at : timestamptz', 'last_message_at : timestamptz', 'closed_at : timestamptz', 'closed_by_id : uuid', 'created_at : timestamptz')
       ops=@('__str__()') },
    @{ k='mensaje'; n='MensajeAtencion'; rol='entity'; col=3; f=3
       nota='Tabla encounter_messages (messaging/models.py, EncounterMessage).'
       atr=@('id : uuid', 'organization_id : uuid', 'thread_id : uuid', 'author_id : uuid', 'side : varchar(12)', 'body : text', 'flagged_emergency : boolean', 'created_at : timestamptz')
       ops=@('__str__()') },
    @{ k='fcm'; n='Firebase Cloud Messaging'; rol='externo'; col=4; f=4 }
  )
  rel = @(
    @{ d='hilo'; a='mensaje'; cd='1'; ca='0..*'; r='contiene' }
  )
  grupos = [ordered]@{ 1 = 'El paciente escribe a su médico'; 2 = 'Suena a urgencia: derivar a emergencias'; 3 = 'El médico responde y se avisa al paciente'; 4 = 'Ventana vencida o cerrada: sólo lectura' }
  guion = @(
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='abrirChat(encounterId)'; src='app_router.dart:381; chat_screen.dart:94 (_cargar)' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='get(request, encounter_id)'; src='verConversacion: GET /api/messaging/encounters/{id}/chat/; chat_api.dart:106; views.py:130' },
    @{ t='msg'; g=1; o='vista'; d='gestor'; m='encounter_for(user, encounter_id)'; src='views.py:65; services.py:86 (Encounter firmada del centro)' },
    @{ t='msg'; g=1; o='gestor'; d='gestor'; m='side_of(user, encounter)'; src='services.py:68; history_scope(user, patient) == OWN en :78' },
    @{ t='msg'; g=1; o='vista'; d='gestor'; m='thread_of(encounter)'; src='views.py:132; services.py:114' },
    @{ t='msg'; g=1; o='gestor'; d='hilo'; m='filter(encounter).first()'; src='services.py:115; SELECT * FROM encounter_threads WHERE encounter_id = :e' },
    @{ t='msg'; g=1; o='vista'; d='gestor'; m='can_write(encounter, thread)'; src='views.py:94; services.py:107 (now < signed_at + 15 días y sin closed_at)' },
    @{ t='alt' },
    @{ t='op'; g='dentro de la ventana y sin cerrar' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='200(conversacion, can_write=true)'; ret=$true; src='views.py:134-135 (mark_read)' },
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='enviar(texto)'; src='chat_screen.dart:118 (_enviar)' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='post(request, encounter_id)'; src='escribirMensaje: POST /api/messaging/encounters/{id}/chat/messages/; chat_api.dart:112; views.py:146' },
    @{ t='msg'; g=1; o='vista'; d='gestor'; m='send(user, encounter, side, body)'; src='views.py:150; services.py:145' },
    @{ t='msg'; g=1; o='gestor'; d='triage'; m='check(body)'; src='services.py:151; triage.py:231' },
    @{ t='msg'; g=1; o='gestor'; d='hilo'; m='select_for_update().get(pk)'; src='services.py:118-131 (_thread_for_update: get_or_create y bloqueo)' },
    @{ t='msg'; g=1; o='gestor'; d='mensaje'; m='create(thread, side, body, flagged_emergency)'; src='services.py:156; INSERT INTO encounter_messages ...' },
    @{ t='msg'; g=1; o='gestor'; d='hilo'; m='save(update_fields)'; src='services.py:170 (last_message_at, *_read_at)' },
    @{ t='alt' },
    @{ t='op'; g='la barrera detecta urgencia' },
    @{ t='msg'; g=2; o='vista'; d='pantalla'; m='201(message, emergency)'; ret=$true; src='views.py:157-160 (bitácora sin el texto)' },
    @{ t='msg'; g=2; o='pantalla'; d='paciente'; m='aviso: ir a emergencias'; ret=$true; src='chat_screen.dart:159 (_Urgencia)' },
    @{ t='op'; g='mensaje común' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='201(message, emergency=null)'; ret=$true; src='views.py:160' },
    @{ t='fin' },
    @{ t='msg'; g=3; o='medico'; d='pantalla'; m='responder(texto)'; src='ChatAtencion.tsx:83 (PanelChat.enviar); api/chat.ts:59' },
    @{ t='msg'; g=3; o='pantalla'; d='vista'; m='post(request, encounter_id)'; src='POST /api/messaging/encounters/{id}/chat/messages/; views.py:146' },
    @{ t='msg'; g=3; o='vista'; d='gestor'; m='send(user, encounter, PRACTITIONER, body)'; src='views.py:150; services.py:145 (sin barrera para el médico)' },
    @{ t='msg'; g=3; o='gestor'; d='gestor'; m='notify_patient(encounter_id, organization_id)'; src='services.py:174 (transaction.on_commit), :236' },
    @{ t='msg'; g=3; o='gestor'; d='avisos'; m='send_to_user(user, Message)'; src='services.py:256; push.py:119 (recipient_user: paciente o titular)' },
    @{ t='msg'; g=3; o='avisos'; d='fcm'; m='post(SEND_URL, _payload(token, message))'; src='push.py:141 (por cada DeviceToken)' },
    @{ t='op'; g='venció la ventana o el médico la cerró' },
    @{ t='msg'; g=4; o='vista'; d='pantalla'; m='200(can_write=false, closed_reason)'; ret=$true; src='views.py:96-101 (closed | expired); un POST tardío da 409 chat_closed, services.py:155' },
    @{ t='msg'; g=4; o='pantalla'; d='paciente'; m='conversación en sólo lectura'; ret=$true; src='chat_screen.dart:186 (_Cerrada)' },
    @{ t='fin' }
  )
}

# -------------------------------------------------------------------------
# CU51 (US-50) Finanzas por Voz y Contabilidad
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU51'] = @{
  cu = 'CU51'; nombre = 'Finanzas por Voz y Contabilidad'; us = 'US-50'; plataforma = 'web'
  nota = 'La contabilidad del período (Contabilidad.tsx, característica accounting del plan): reporting/finance.py suma ingresos, devoluciones, comisión de la pasarela, honorarios y gastos por moneda; una pregunta dictada pasa por reporting/finance_voice.py (Gemini por voice.ask_model o reglas fijas sin proveedor), se calcula con el mismo finance.calcular y se responde en una frase.'
  participantes = @(
    @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaContabilidad'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Contabilidad.tsx (Contabilidad, EntradaDeVoz) y api/finanzas.ts. Sin pantalla móvil.'
       atr=@('GET /api/reporting/finance/summary/ : 200 | 400 | 403', 'POST /api/reporting/finance/interpret/ : 200', 'desde : string', 'hasta : string', 'agrupar : Agrupacion', 'voz : RespuestaDeVoz')
       ops=@('Contabilidad()', 'preguntar(texto)', 'verEnLaTabla()', 'bajar(formato)', 'periodo(dias)', 'verResumen(f, contexto, senal)', 'verSerie(f, contexto, senal)', 'preguntarPorVoz(texto, contexto)', 'descargarContabilidad(f, formato, contexto)', 'crearGasto(gasto, contexto)', 'guardarComision(porcentaje, contexto)') },
    @{ k='vista'; n='ControladorContabilidad'; rol='control'; col=2; f=0
       nota='SummaryView, SeriesView, InterpretView, ExportView, ExpenseListView, ExpenseDetailView y SettingsView en reporting/finance_views.py (CanReadAccounting).'
       ops=@('get(request)', 'post(request)', 'patch(request, pk)', 'delete(request, pk)', 'put(request)', '_organizacion(request)', '_consulta(request, organizacion)', '_quiere_comparar(request)', 'filas_del_archivo(datos)') },
    @{ k='vozfin'; n='GestorFinanzasPorVoz'; rol='control'; col=2; f=1
       nota='Funciones de reporting/finance_voice.py.'
       ops=@('interpretar(texto, user, hoy)', 'contexto_del_centro(organizacion)', '_sin_agrupacion(t, profesionales)', '_sin_sede(t, sedes)', '_periodo_corto(t, hoy)', '_metrica(t, bloqueos, comparar)', 'analizar(texto, hoy, sedes, profesionales)', 'sanear(crudo, hoy, agrupar, sede, profesional, comparar_local)', '_pedido(texto, hoy)', 'frase_de_respuesta(consulta, resultado)', 'ejecutar(organizacion, consulta)', '_nada(motivos, generado_por)') },
    @{ k='voz'; n='GestorVozReportes'; rol='control'; col=2; f=2
       nota='reporting/voice.py: el gate del proveedor y la llamada a Gemini.'
       ops=@('interpret(text, user, dataset_code)', 'proveedor_disponible()', 'ask_model(system_prompt, prompt)', '_call_model(prompt)', '_call_model_with(system_prompt, prompt)') },
    @{ k='calculo'; n='GestorContabilidad'; rol='control'; col=2; f=3
       nota='Funciones de reporting/finance.py.'
       ops=@('redondear(valor)', 'porcentaje_de(monto, porcentaje)', 'ajustes_de(organizacion)', 'clave_de_periodo(fecha, agrupar)', '_especialidades(organizacion)', 'calcular(organizacion, desde, hasta, branch_id, practitioner_id, agrupar)', 'periodo_anterior(desde, hasta)', 'variacion(actual, anterior)', 'con_comparacion(organizacion, desde, hasta, filtros)', 'serie_de_meses(organizacion, hoy, branch_id, practitioner_id)') },
    @{ k='ajustes'; n='AjustesFinancieros'; rol='entity'; col=3; f=1
       nota='Tabla finance_settings (reporting/models.py, FinanceSettings): una fila por organización.'
       atr=@('id : uuid', 'organization_id : uuid', 'stripe_percent : decimal', 'updated_at : timestamptz')
       ops=@() },
    @{ k='pago'; n='Pago'; rol='entity'; col=3; f=2.5
       nota='Tabla payments (payments/models.py, Payment).'
       atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'amount : decimal(10,2)', 'currency : varchar(3)', 'provider : varchar(12)', 'status : varchar', 'paid_at : timestamptz', 'refunded_at : timestamptz', 'created_at : timestamptz')
       ops=@() },
    @{ k='gasto'; n='Gasto'; rol='entity'; col=3; f=4
       nota='Tabla expenses (reporting/models.py, Expense).'
       atr=@('id : uuid', 'organization_id : uuid', 'branch_id : uuid', 'category : varchar(12)', 'amount : decimal(10,2)', 'currency : varchar(3)', 'spent_on : date', 'note : varchar(200)', 'created_by_id : uuid', 'created_at : timestamptz')
       ops=@() },
    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=2 }
  )
  rel = @()
  grupos = [ordered]@{ 1 = 'Ver la contabilidad del período'; 2 = 'Preguntar por voz'; 3 = 'Sin proveedor de IA: reglas fijas'; 4 = 'No entendió la pregunta' }
  guion = @(
    @{ t='msg'; g=1; o='admin'; d='pantalla'; m='elegirPeriodo(desde, hasta)'; src='Contabilidad.tsx:244 (periodo) y filtros de :184' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='get(request)'; src='verResumen: GET /api/reporting/finance/summary/?from=&to=&group=&compare=; Contabilidad.tsx:205; api/finanzas.ts:96; finance_views.py:92' },
    @{ t='msg'; g=1; o='vista'; d='calculo'; m='calcular(organizacion, desde, hasta, agrupar)'; src='finance_views.py:102 (o con_comparacion); finance.py:138' },
    @{ t='msg'; g=1; o='calculo'; d='ajustes'; m='get_or_create(organization)'; src='finance.py:146 -> ajustes_de, :59' },
    @{ t='msg'; g=1; o='calculo'; d='pago'; m='filter(status__in, paid_at__gte, paid_at__lt)'; src='finance.py:180-192; SELECT ... FROM payments WHERE status IN (succeeded, refunded) AND paid_at en el rango' },
    @{ t='loop'; g='por cada pago cobrado' },
    @{ t='msg'; g=1; o='calculo'; d='calculo'; m='sumar(moneda, campo, monto, clave)'; src='finance.py:195-210 (ingresos, comisión, honorarios con fee_percent)' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='calculo'; d='pago'; m='filter(status=REFUNDED, refunded_at__gte)'; src='finance.py:213-219 (devoluciones por fecha de devolución)' },
    @{ t='msg'; g=1; o='calculo'; d='gasto'; m='filter(spent_on__gte, spent_on__lte)'; src='finance.py:222-244; SELECT * FROM expenses WHERE spent_on BETWEEN :desde AND :hasta' },
    @{ t='msg'; g=1; o='calculo'; d='vista'; m='{range, currencies(totals, groups)}'; ret=$true; src='finance.py:258-268' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='200(resumen)'; ret=$true; src='finance_views.py:103-108 (bitácora FINANCE_QUERY)' },
    @{ t='msg'; g=2; o='admin'; d='pantalla'; m='preguntar(texto)'; src='Contabilidad.tsx:275 (EntradaDeVoz), :214' },
    @{ t='msg'; g=2; o='pantalla'; d='vista'; m='post(request)'; src='preguntarPorVoz: POST /api/reporting/finance/interpret/; api/finanzas.ts:135; finance_views.py:143' },
    @{ t='msg'; g=2; o='vista'; d='vozfin'; m='interpretar(texto, user)'; src='finance_views.py:149; finance_voice.py:388' },
    @{ t='msg'; g=2; o='vozfin'; d='voz'; m='ask_model(SYSTEM_PROMPT, _pedido(limpio, hoy))'; src='finance_voice.py:413; voice.py:176' },
    @{ t='alt' },
    @{ t='op'; g='hay proveedor y responde' },
    @{ t='msg'; g=2; o='voz'; d='ia'; m='generate_content(model, contents, config)'; src='voice.py:188, :209' },
    @{ t='msg'; g=2; o='ia'; d='voz'; m='json(metrica, desde, hasta, comparar)'; ret=$true; src='voice.py:209-220' },
    @{ t='msg'; g=2; o='voz'; d='vozfin'; m='(crudo, "gemini")'; ret=$true; src='voice.py:191' },
    @{ t='msg'; g=2; o='vozfin'; d='vozfin'; m='sanear(crudo, hoy, agrupar, sede, profesional)'; src='finance_voice.py:415, :262' },
    @{ t='op'; g='sin proveedor o la llamada falla' },
    @{ t='msg'; g=3; o='voz'; d='vozfin'; m='(None, "plantilla")'; ret=$true; src='voice.py:185-190' },
    @{ t='msg'; g=3; o='vozfin'; d='vozfin'; m='analizar(texto, hoy, sedes, profesionales)'; src='finance_voice.py:418, :205' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='entendió la pregunta' },
    @{ t='msg'; g=2; o='vozfin'; d='calculo'; m='calcular(organizacion, desde, hasta, filtros)'; src='finance_voice.py:426 -> ejecutar, :386' },
    @{ t='msg'; g=2; o='vozfin'; d='vozfin'; m='frase_de_respuesta(consulta, resultado)'; src='finance_voice.py:431, :299' },
    @{ t='msg'; g=2; o='vozfin'; d='vista'; m='{understood, query, result, spoken_summary}'; ret=$true; src='finance_voice.py:427-434' },
    @{ t='msg'; g=2; o='vista'; d='pantalla'; m='200(respuesta)'; ret=$true; src='finance_views.py:152-158 (bitácora sin la frase)' },
    @{ t='msg'; g=2; o='pantalla'; d='admin'; m='respuesta en una frase'; ret=$true; src='Contabilidad.tsx:280 (voz.spoken_summary)' },
    @{ t='op'; g='no entendió o el período supera el tope' },
    @{ t='msg'; g=4; o='vozfin'; d='vista'; m='_nada(unresolved, generado_por)'; ret=$true; src='finance_voice.py:420-424, :349' },
    @{ t='msg'; g=4; o='vista'; d='pantalla'; m='200(understood=false, unresolved)'; ret=$true; src='finance_views.py:158; Contabilidad.tsx:282' },
    @{ t='fin' }
  )
}


# =========================================================================
# Datos D del Sprint 4: CU49 (US-48), CU50 (US-49) y CU54 (US-53).
# Leídos del código el 21/11/26 (rama fix/us51-respaldo-y-v1.6.1).
# Formato: SPEC-datos-sprint4.md.
# =========================================================================

# ---- compartido -----------------------------------------------------------
$ATR_ENCUENTRO = @('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid',
  'branch_id : uuid', 'status : varchar', 'reason : text', 'evolution : text', 'diagnosis : text', 'indications : text',
  'treatment : text', 'signed_at : timestamptz', 'signed_by_id : uuid', 'created_at : timestamptz', 'updated_at : timestamptz')
$OPS_SERVICIOS_ATENCION = @('practitioner_of(user)', 'is_own(user, encounter)', 'local_today(appointment)',
  'appointment_local_date(appointment)', 'open_encounter(user, appointment)', 'update_draft(encounter, data)',
  '_save_vital_signs(encounter, valores)', 'sign(encounter, user)', 'amend(encounter, user, section, text)',
  '_require_draft(encounter)', 'add_child(encounter, kind, data)', 'update_child(encounter, child, data)',
  'delete_child(encounter, child)', 'history_scope(user, patient)')

# -------------------------------------------------------------------------
# CU49 (US-48) Calificación de la Atención
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU49'] = @{
  cu = 'CU49'; nombre = 'Calificación de la Atención'; us = 'US-48'; plataforma = 'móvil'
  nota = 'El paciente (o el titular de su dependiente, history_scope == OWN) califica con 1 a 5 estrellas y un comentario opcional cada atención firmada, desde la tarjeta «¿Cómo te atendieron?» de Mi historia clínica (móvil) o CalificarAtencion.tsx (web); una sola por atención (OneToOne), se corrige 7 días con PATCH. El administrador ve los promedios por médico, especialidad y sede en la tarjeta Satisfacción del panel de KPIs (GET /api/reporting/satisfaction/). El médico ve sólo su promedio (MyRatingsView, GET /api/encounters/ratings/mine/).'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=1 },
    @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=4 },
    @{ k='pantalla'; n='PantallaCalificacion'; rol='boundary'; col=1; f=1
       nota='Móvil: TarjetaCalificacion en mobile/lib/features/clinical_record/rating_card.dart, montada debajo de cada atención firmada en clinical_record_screen.dart:397; calificarAtencion en clinical_record_api.dart:474. La calificación inicial viene en cada atención de GET /api/encounters/history/{paciente}/ (history_views.py:68-79). Web: frontend/src/paginas/CalificarAtencion.tsx y api/calificaciones.ts.'
       atr=@('POST /api/encounters/{id}/rating/ : 201 | 400 | 404 | 409', 'PATCH /api/encounters/{id}/rating/ : 200 | 404 | 409',
             'encounterId : String', '_guardada : Calificacion?', '_estrellas : int', '_comentario : TextEditingController', '_editando : bool', '_enviando : bool', '_error : String?')
       ops=@('_enviar()', 'build(context)', 'dispose()', 'estrellasEnTexto(n)', 'calificarAtencion(client, encounterId, primera, estrellas, comentario)',
             'verHistoriaClinica(client, patientId)', 'CalificarAtencion(encuentroId, inicial)', 'enviar(e)', 'calificar(encuentroId, primera, datos, contexto)') },
    @{ k='pantallaadm'; n='PantallaSatisfaccion'; rol='boundary'; col=1; f=4
       nota='Web: TarjetaSatisfaccion en frontend/src/paginas/TarjetaSatisfaccion.tsx, dentro del panel de KPIs (Kpis), y verSatisfaccion en api/calificaciones.ts:66. MiPromedio es la del médico.'
       atr=@('GET /api/reporting/satisfaction/?from=&to=&branch= : 200 | 400 | 403', 'desde : string', 'hasta : string', 'sucursal : string', 'vista : Vista')
       ops=@('TarjetaSatisfaccion(desde, hasta, sucursal)', 'Distribucion(datos)', 'Tabla(filas, columna)', 'MiPromedio()',
             'verSatisfaccion(filtros, contexto, senal)', 'verMisEstrellas(contexto, senal)', 'promedio(valor)') },
    @{ k='vista'; n='ControladorCalificacion'; rol='control'; col=2; f=0
       nota='EncounterRatingView (con RatingWriteSerializer y RatingReadSerializer) en backend/encounters/rating_views.py. Pide encounters.history.read (CanReadHistory) y el alcance propio: a un médico le da 404.'
       ops=@('get(request, pk)', 'post(request, pk)', 'patch(request, pk)', '_atencion_propia(request, pk)', 'leer(rating)', 'is_valid(raise_exception)') },
    @{ k='alcance'; n='GestorAtencion'; rol='control'; col=2; f=1
       nota='backend/encounters/services.py: history_scope decide OWN (paciente o titular), PROFESSIONAL o None.'
       ops=$OPS_SERVICIOS_ATENCION },
    @{ k='gestor'; n='GestorCalificaciones'; rol='control'; col=2; f=2.5
       nota='backend/encounters/ratings.py (con RatingConflict, 409). Las reglas que no dependen de la vista (firmada, 1 a 5, 7 días, no se borra) las vuelve a exigir la migración 0008.'
       ops=@('editable(rating, ahora)', 'as_dict(rating, ahora)', 'rate(user, encounter, stars, comment)', 'correct(encounter, stars, comment)',
             '_promedio(valor)', '_distribucion(qs)', '_resumen(qs)', '_agrupado(qs, campo_id, campo_nombre)',
             'for_practitioner(practitioner)', 'for_organization(organizacion, inicio, fin, branch_id)') },
    @{ k='ctrlsat'; n='ControladorSatisfaccion'; rol='control'; col=2; f=4
       nota='SatisfactionView en backend/reporting/kpi_views.py:87. Mismo permiso (CanReadKpis) y filtros que el panel de KPIs.'
       ops=@('get(request)', 'filtros(request, organizacion)', '_fecha(valor)', '_error(code, detail)') },
    @{ k='encuentro'; n='Encuentro'; rol='entity'; col=3; f=0.5
       nota='Tabla encounters (Encounter en encounters/models.py).'
       atr=$ATR_ENCUENTRO
       ops=@('is_signed()') },
    @{ k='rating'; n='CalificacionAtencion'; rol='entity'; col=3; f=2.5
       nota='Tabla encounter_ratings (EncounterRating en encounters/models.py:272). CHECK ck_rating_stars (1 a 5); encounter_id único (OneToOne).'
       atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid',
             'rated_by_id : uuid', 'stars : smallint', 'comment : varchar(500)', 'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@('editable_until()') }
  )
  rel = @(
    @{ d='encuentro'; a='rating'; cd='1'; ca='0..1'; r='se califica con' }
  )
  grupos = [ordered]@{ 1 = 'Calificar la atención'; 2 = 'Cambiar la calificación dentro de los 7 días'; 3 = 'La calificación se rechaza'; 4 = 'El administrador ve los promedios' }
  guion = @(
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='calificar(estrellas, comentario)'; src='rating_card.dart:170, :219 (Enviar calificación); _enviar :59' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='post(request, pk)'; src='calificarAtencion: POST /api/encounters/{id}/rating/, clinical_record_api.dart:474-485; rating_views.py:77' },
    @{ t='msg'; g=1; o='vista'; d='encuentro'; m='filter(organization, pk, status=SIGNED)'; src='_atencion_propia, rating_views.py:52-61; SELECT * FROM encounters WHERE organization_id = :org AND id = :pk AND status = signed' },
    @{ t='msg'; g=1; o='vista'; d='alcance'; m='history_scope(request.user, encuentro.patient)'; src='rating_views.py:62-65; services.py:243' },
    @{ t='alt' },
    @{ t='op'; g='alcance propio y atención sin calificar' },
    @{ t='msg'; g=1; o='vista'; d='vista'; m='is_valid(raise_exception=True)'; src='RatingWriteSerializer: stars 1..5, comment <= 500, rating_views.py:30-35, :79-80' },
    @{ t='msg'; g=1; o='vista'; d='gestor'; m='rate(request.user, encuentro, stars, comment)'; src='rating_views.py:81; ratings.py:59' },
    @{ t='msg'; g=1; o='gestor'; d='rating'; m='create(encounter, rated_by, stars, comment)'; src='ratings.py:65-74; INSERT INTO encounter_ratings (organization_id, encounter_id, patient_id, practitioner_id, branch_id, rated_by_id, stars, comment)' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='201(rating)'; ret=$true; src='leer(rating), rating_views.py:47, :82; la tarjeta muestra «Calificaste con ★★★★☆», rating_card.dart:91-115' },
    @{ t='op'; g='otra pestaña ya la calificó (OneToOne)' },
    @{ t='msg'; g=3; o='gestor'; d='vista'; m='RatingConflict(already_rated)'; ret=$true; src='IntegrityError en el OneToOne, ratings.py:75-78' },
    @{ t='msg'; g=3; o='vista'; d='pantalla'; m='409(code, detail)'; ret=$true; src='RatingConflict status 409, ratings.py:33-38; rating_card.dart:78-79 muestra e.message' },
    @{ t='op'; g='no es suya o no está firmada' },
    @{ t='msg'; g=3; o='vista'; d='pantalla'; m='404'; ret=$true; src='Http404 en _atencion_propia, rating_views.py:62-65' },
    @{ t='fin' },
    @{ t='msg'; g=2; o='paciente'; d='pantalla'; m='cambiarCalificacion(estrellas, comentario)'; src='botón Cambiar (hasta el ...), rating_card.dart:121-133; Guardar cambio :219-224' },
    @{ t='msg'; g=2; o='pantalla'; d='vista'; m='patch(request, pk)'; src='calificarAtencion(primera: false): PATCH /api/encounters/{id}/rating/, clinical_record_api.dart:483-484; rating_views.py:84' },
    @{ t='msg'; g=2; o='vista'; d='gestor'; m='correct(encuentro, stars, comment)'; src='rating_views.py:88; ratings.py:81' },
    @{ t='msg'; g=2; o='gestor'; d='rating'; m='select_for_update().filter(encounter)'; src='ratings.py:84-85; SELECT ... FROM encounter_ratings WHERE encounter_id = :id FOR UPDATE' },
    @{ t='alt' },
    @{ t='op'; g='editable(rating): created_at + 7 días >= ahora' },
    @{ t='msg'; g=2; o='gestor'; d='rating'; m='save(update_fields=[stars, comment])'; src='ratings.py:94-96; UPDATE encounter_ratings SET stars, comment, updated_at' },
    @{ t='msg'; g=2; o='vista'; d='pantalla'; m='200(rating)'; ret=$true; src='rating_views.py:89' },
    @{ t='op'; g='pasaron los 7 días' },
    @{ t='msg'; g=3; o='gestor'; d='vista'; m='RatingConflict(rating_locked)'; ret=$true; src='ratings.py:88-93; editable :41' },
    @{ t='msg'; g=3; o='vista'; d='pantalla'; m='409(rating_locked)'; ret=$true; src='la tarjeta dice «Ya no se puede cambiar.», rating_card.dart:134-139' },
    @{ t='fin' },
    @{ t='msg'; g=4; o='admin'; d='pantallaadm'; m='filtrarPeriodo(desde, hasta, sucursal)'; src='filtros del panel de KPIs; TarjetaSatisfaccion.tsx:78-91' },
    @{ t='msg'; g=4; o='pantallaadm'; d='ctrlsat'; m='get(request)'; src='verSatisfaccion: GET /api/reporting/satisfaction/?from=&to=&branch=, api/calificaciones.ts:66-70; kpi_views.py:98' },
    @{ t='msg'; g=4; o='ctrlsat'; d='ctrlsat'; m='filtros(request, organizacion)'; src='kpi_views.py:42, :105-109; kpis.rango_utc' },
    @{ t='msg'; g=4; o='ctrlsat'; d='gestor'; m='for_organization(organizacion, inicio, fin, branch_id)'; src='kpi_views.py:112; ratings.py:143' },
    @{ t='msg'; g=4; o='gestor'; d='rating'; m='filter(organization, starts_at en rango)'; src='ratings.py:145-151; WHERE organization_id = :org AND appointment.starts_at >= :inicio AND < :fin [AND branch_id]' },
    @{ t='msg'; g=4; o='gestor'; d='rating'; m='values(practitioner).annotate(Avg, Count)'; src='ratings.py:153-179 (por médico y especialidad), _agrupado por sede :122, _resumen :113' },
    @{ t='msg'; g=4; o='ctrlsat'; d='pantallaadm'; m='200(average, distribution, by_practitioner)'; ret=$true; src='kpi_views.py:109-113; comentarios sin nombre del paciente, ratings.py:181-189' }
  )
}

# -------------------------------------------------------------------------
# CU50 (US-49) Recordatorio de Toma de Medicamentos
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU50'] = @{
  cu = 'CU50'; nombre = 'Recordatorio de Toma de Medicamentos'; us = 'US-49'; plataforma = 'móvil'
  nota = 'En Mis medicamentos (móvil) el paciente activa «Recordarme» en cada medicamento de una receta firmada: el backend interpreta la frecuencia y la duración (frequency.interpretar: «cada 8 horas» por «5 días» = 15 tomas) y el teléfono programa una notificación local por toma (flutter_local_notifications), sin depender del servidor. Cada toma marcada («Tomada» desde el aviso o la app) queda pendiente en el teléfono y se manda con POST; (prescription_item, dose_number) es único, así que un reintento da 409 y no se duplica. Si la frecuencia no tiene horario fijo, no se ofrece el recordatorio y se dice por qué.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2.5 },
    @{ k='pantalla'; n='PantallaMisMedicamentos'; rol='boundary'; col=1; f=2.5
       nota='Móvil: MedicationsScreen en mobile/lib/features/medications/medications_screen.dart, InterruptorRecordatorio («Recordarme») en recordarme.dart, y verMisMedicamentos y marcarToma en medications_api.dart. No hay pantalla web: el médico ve el cumplimiento en la atención y el historial.'
       atr=@('GET /api/encounters/medications/{paciente}/ : 200 | 404', 'POST /api/encounters/prescription/{item}/intakes/ : 201 | 400 | 404 | 409',
             '_deQuien : PatientOption?', '_tratamientos : List<Tratamiento>?', '_marcando : Set<String>', '_error : String?')
       ops=@('_cargar()', '_cambiarPersona(opcion)', '_marcar(t, numero, tomada)', '_interruptor(t)', 'build(context)',
             '_activar(context, horario)', 'cuandoEnTexto(momento, ahora)', 'verMisMedicamentos(client, patientId)',
             'marcarToma(client, itemId, numero, tomada, programadaPara)') },
    @{ k='recordatorios'; n='GestorRecordatorios'; rol='control'; col=2; f=0
       nota='Recordatorios (ChangeNotifier) en mobile/lib/features/medications/recordatorios.dart. Guarda los activos y las tomas pendientes en AlmacenSeguro (flutter_secure_storage); RecordatorioActivo.momentoDe(n) da la hora de cada toma. Al cerrar sesión cancela todo.'
       atr=@('_activos : Map<String, RecordatorioActivo>', '_pendientes : List<TomaPendiente>', 'clienteParaEnviar : ApiClient?')
       ops=@('iniciar()', 'cargar()', '_cargar()', '_guardar()', '_titulo(r)', '_cuerpo(r, n)', 'activar(recordatorio)', 'desactivar(itemId)',
             '_cancelarAvisos(r)', 'cancelarTodo()', 'marcar(itemId, numero, tomada)', 'posponer(itemId, numero)', 'sincronizar(api)',
             'responder(payload, accion)', '_programarSeguro(id, cuando, titulo, cuerpo, payload)', '_cancelarSeguro(id)', 'pedirPermiso()',
             'esDeMedicamento(payload)', 'idDeAviso(itemId, n, pospuesto)') },
    @{ k='programador'; n='ProgramadorAvisosLocales'; rol='control'; col=2; f=1
       nota='ProgramadorLocal en recordatorios.dart:216: envuelve flutter_local_notifications (zonedSchedule, canal de Android, botones Tomada y Posponer 15 min).'
       ops=@('iniciar()', '_iniciar()', 'respuestaDeArranque()', 'pedirPermiso()', 'programar(id, cuando, titulo, cuerpo, payload)', 'cancelar(id)') },
    @{ k='vistamed'; n='ControladorMisMedicamentos'; rol='control'; col=2; f=2
       nota='MyMedicationsView en backend/encounters/intake_views.py:88: lo recetado en atenciones firmadas de los últimos 120 días, con horario, cumplimiento y tomas. Pide encounters.history.read y history_scope == OWN.'
       ops=@('get(request, patient_id)', '_uuid(valor)') },
    @{ k='vista'; n='ControladorTomas'; rol='control'; col=2; f=3
       nota='MedicationIntakesView (con IntakeWriteSerializer e IntakeReadSerializer) en backend/encounters/intake_views.py:68.'
       ops=@('get(request, item_pk)', 'post(request, item_pk)', '_medicamento_propio(request, item_pk)', 'is_valid(raise_exception)') },
    @{ k='gestor'; n='GestorTomas'; rol='control'; col=2; f=4
       nota='backend/encounters/intakes.py (con IntakeConflict 409 e IntakeInvalid 400).'
       ops=@('cumplimiento(item, horario)', 'registrar(user, item, dose_number, estado, scheduled_at)', 'as_dict(toma)') },
    @{ k='frecuencia'; n='InterpreteFrecuencia'; rol='control'; col=2; f=5
       nota='backend/encounters/frequency.py: lee «cada 8 h», «3 veces al día», «diario»... y la duración; devuelve Horario(interval_hours, days, total_doses) o el motivo (no_fixed_schedule, no_duration, too_many_doses).'
       ops=@('_normalizar(texto)', '_numero(valor)', 'intervalo_en_horas(frecuencia)', 'dias_de_tratamiento(duracion)',
             'interpretar(frecuencia, duracion)', 'para_la_api(frecuencia, duracion)', 'as_dict()') },
    @{ k='item'; n='MedicamentoRecetado'; rol='entity'; col=3; f=1.5
       nota='Tabla encounter_prescription_items (PrescriptionItem en encounters/models.py:185).'
       atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'medication : varchar(200)', 'dose : varchar(80)',
             'frequency : varchar(80)', 'duration : varchar(80)', 'instructions : varchar(300)', 'created_at : timestamptz')
       ops=@() },
    @{ k='toma'; n='TomaMedicamento'; rol='entity'; col=3; f=3.5
       nota='Tabla encounter_medication_intakes (MedicationIntake en encounters/models.py:353). UNIQUE uq_intake_item_dose (prescription_item_id, dose_number); no se cambia ni se borra (migración 0010).'
       atr=@('id : uuid', 'organization_id : uuid', 'prescription_item_id : uuid', 'patient_id : uuid', 'dose_number : smallint',
             'status : varchar(8)', 'scheduled_at : timestamptz', 'recorded_by_id : uuid', 'recorded_at : timestamptz')
       ops=@() }
  )
  rel = @(
    @{ d='item'; a='toma'; cd='1'; ca='0..*'; r='registra' }
  )
  grupos = [ordered]@{ 1 = 'Activar el recordatorio'; 2 = 'Marcar la toma como tomada'; 3 = 'La toma ya estaba marcada'; 4 = 'La frecuencia no se puede interpretar' }
  guion = @(
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='abrirMisMedicamentos()'; src='medications_screen.dart:59 (_cargar)' },
    @{ t='msg'; g=1; o='pantalla'; d='vistamed'; m='get(request, patient_id)'; src='verMisMedicamentos: GET /api/encounters/medications/{id}/, medications_api.dart:114; intake_views.py:91-96 (history_scope OWN)' },
    @{ t='msg'; g=1; o='vistamed'; d='item'; m='filter(encounter__patient, SIGNED, signed_at)'; src='intake_views.py:98-106; SELECT * FROM encounter_prescription_items JOIN encounters WHERE patient_id = :p AND status = signed AND signed_at >= ahora - 120 días' },
    @{ t='loop'; g='por cada medicamento recetado' },
    @{ t='msg'; g=1; o='vistamed'; d='frecuencia'; m='para_la_api(item.frequency, item.duration)'; src='intake_views.py:110; frequency.py:155' },
    @{ t='msg'; g=1; o='frecuencia'; d='frecuencia'; m='interpretar(frecuencia, duracion)'; src='frequency.py:136-152: intervalo_en_horas :87, dias_de_tratamiento :110, total = dias * 24 // intervalo' },
    @{ t='msg'; g=1; o='vistamed'; d='gestor'; m='cumplimiento(item, horario)'; src='intake_views.py:122; intakes.py:38 («12 de 15 tomas»)' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='vistamed'; d='pantalla'; m='200(medications con schedule)'; ret=$true; src='intake_views.py:111-126' },
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='activarRecordatorio(horaPrimeraToma)'; src='interruptor Recordarme y showTimePicker, recordarme.dart:53-62, :111-114' },
    @{ t='msg'; g=1; o='pantalla'; d='recordatorios'; m='activar(recordatorio)'; src='recordarme.dart:64-71; recordatorios.dart:440' },
    @{ t='loop'; g='por cada toma futura (1..totalTomas)' },
    @{ t='msg'; g=1; o='recordatorios'; d='programador'; m='programar(id, cuando, titulo, cuerpo, payload)'; src='_programarSeguro, recordatorios.dart:445-454, :570; zonedSchedule :268-302; payload med|item|n' },
    @{ t='fin' },
    @{ t='msg'; g=1; o='recordatorios'; d='recordatorios'; m='_guardar()'; src='recordatorios.dart:421 (AlmacenSeguro, flutter_secure_storage)' },
    @{ t='msg'; g=2; o='paciente'; d='pantalla'; m='marcarTomada(numero)'; src='botón Tomada en la app, medications_screen.dart:85; o en el aviso, responder :550 (accionTomada)' },
    @{ t='msg'; g=2; o='pantalla'; d='recordatorios'; m='marcar(itemId, numero, tomada)'; src='medications_screen.dart:87; recordatorios.dart:492 (no la agrega dos veces a _pendientes)' },
    @{ t='msg'; g=2; o='recordatorios'; d='programador'; m='cancelar(idDeAviso(itemId, numero))'; src='_cancelarSeguro, recordatorios.dart:504-505, :306' },
    @{ t='msg'; g=2; o='recordatorios'; d='recordatorios'; m='sincronizar(api)'; src='recordatorios.dart:507-508, :527' },
    @{ t='msg'; g=2; o='recordatorios'; d='vista'; m='post(request, item_pk)'; src='marcarToma: POST /api/encounters/prescription/{id}/intakes/, medications_api.dart:131-148; intake_views.py:76' },
    @{ t='msg'; g=2; o='vista'; d='item'; m='filter(organization, pk, SIGNED).first()'; src='_medicamento_propio, intake_views.py:56-65 (y history_scope OWN)' },
    @{ t='msg'; g=2; o='vista'; d='gestor'; m='registrar(user, item, dose_number, estado, scheduled_at)'; src='intake_views.py:78-84; intakes.py:52' },
    @{ t='msg'; g=2; o='gestor'; d='frecuencia'; m='interpretar(item.frequency, item.duration)'; src='intakes.py:54-64 (sin horario: IntakeInvalid no_schedule 400; toma fuera de 1..total: invalid_dose)' },
    @{ t='alt' },
    @{ t='op'; g='toma nueva' },
    @{ t='msg'; g=2; o='gestor'; d='toma'; m='create(prescription_item, dose_number, status)'; src='intakes.py:65-75; INSERT INTO encounter_medication_intakes (organization_id, prescription_item_id, patient_id, dose_number, status, scheduled_at, recorded_by_id)' },
    @{ t='msg'; g=2; o='vista'; d='recordatorios'; m='201(toma)'; ret=$true; src='intake_views.py:85; sale de _pendientes, recordatorios.dart:541-544' },
    @{ t='op'; g='la toma ya estaba marcada (reintento)' },
    @{ t='msg'; g=3; o='gestor'; d='vista'; m='IntakeConflict(already_recorded)'; ret=$true; src='IntegrityError en uq_intake_item_dose, intakes.py:76-77' },
    @{ t='msg'; g=3; o='vista'; d='recordatorios'; m='409(already_recorded)'; ret=$true; src='marcarToma lo cuenta como enviado, medications_api.dart:149-150' },
    @{ t='fin' },
    @{ t='msg'; g=4; o='vistamed'; d='frecuencia'; m='para_la_api(frecuencia, duracion)'; src='intake_views.py:110; ej. «según dolor», «uso continuo», sin duración o más de 200 tomas' },
    @{ t='msg'; g=4; o='frecuencia'; d='vistamed'; m='schedule=None, schedule_reason'; ret=$true; src='frequency.py:143-151, :157-159 (MOTIVOS[motivo])' },
    @{ t='msg'; g=4; o='vistamed'; d='pantalla'; m='200(schedule=null, schedule_reason)'; ret=$true; src='intake_views.py:121; medications_api.dart:106 (motivoSinHorario)' },
    @{ t='msg'; g=4; o='pantalla'; d='paciente'; m='motivoSinHorario, sin «Recordarme»'; ret=$true; src='recordarme.dart:86-94; medications_screen.dart:108-112, :192-195' }
  )
}

# -------------------------------------------------------------------------
# CU54 (US-53) Registro de Signos Vitales
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU54'] = @{
  cu = 'CU54'; nombre = 'Registro de Signos Vitales'; us = 'US-53'; plataforma = 'web'
  nota = 'En la atención (web) el médico carga presión, frecuencia cardíaca, temperatura, saturación, glucosa, peso y talla, todos opcionales; viajan con el mismo «Guardar borrador» (PATCH /api/encounters/{id}/, campo vital_signs) y se firman con la atención. La web y la API rechazan lo imposible (los mismos límites que los CHECK de la base, migración 0011); lo anormal sólo se marca (alerts) y el IMC se calcula. Firmada la atención no se tocan: 409 y el trigger vital_signs_solo_en_borrador (migración 0012); se corrigen con una enmienda de la sección vital_signs. La evolución se grafica en la pestaña Evolución del historial (médico) y en Mi historia (paciente, web y móvil).'
  participantes = @(
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaAtencion'; rol='boundary'; col=1; f=2
       nota='Web: Atencion.tsx (registrar), EditorSignos, VerSignos y FilaSignos en SignosVitales.tsx; Historial.tsx con EvolucionSignos.tsx (pestaña Evolución del médico) y MiHistoria.tsx (paciente); guardarBorrador y verHistorial en api/atencion.ts. Móvil (sólo lectura del paciente): MisSignosVitales en mobile/lib/features/clinical_record/signos_evolucion.dart.'
       atr=@('PATCH /api/encounters/{id}/ : 200 | 400 | 404 | 409', 'GET /api/encounters/history/{paciente}/ : 200 | 404',
             'signos : TextosSignos', 'encuentro : Encuentro', 'guardando : boolean', 'elegida : IdSerie')
       ops=@('Atencion()', 'cargar(signal)', 'guardar(e)', 'firmar()', 'enviarEnmienda(e)', 'EditorSignos(textos, onCambio)', 'VerSignos(signos)',
             'FilaSignos(signos)', 'EvolucionSignos(encuentros)', 'GraficoSigno(serie, puntos)',
             'guardarBorrador(id, datos, contexto)', 'firmarEncuentro(id, contexto)', 'verHistorial(pacienteId, contexto, senal)') },
    @{ k='lector'; n='LectorSignos'; rol='control'; col=2; f=0
       nota='frontend/src/paginas/signos_vitales.ts: lee y valida lo escrito con los límites de SIGNOS (api/atencion.ts:74, iguales a VITAL_LIMITS), calcula IMC y marcas como VitalSigns.bmi/alerts, y arma las series de las gráficas.'
       ops=@('aTextos(signos)', 'mismosSignos(a, b)', 'leerSignos(textos)', 'calcular(d)', 'puntosDe(serie, encuentros)', 'ultimaMedicion(encuentros)', 'filaCompacta(s)') },
    @{ k='vista'; n='ControladorAtencion'; rol='control'; col=2; f=1
       nota='EncounterDetailView en backend/encounters/views.py:146 (PATCH pide CanCreateEncounters); _own_encounter :62 da 404 si la atención no es del médico.'
       ops=@('get_permissions()', 'get(request, pk)', 'patch(request, pk)', '_own_encounter(request, pk)', '_audit(request, action, encuentro)') },
    @{ k='serializer'; n='ValidadorSignosVitales'; rol='control'; col=2; f=2
       nota='VitalSignsWriteSerializer y _rango en backend/encounters/serializers.py:101-138, anidado en EncounterDraftSerializer.vital_signs (:200); la lectura es VitalSignsSerializer (:86) vía EncounterSerializer.get_vital_signs (:181).'
       ops=@('_rango(campo, decimales)', 'validate(attrs)', 'is_valid(raise_exception)', 'get_vital_signs(encuentro)') },
    @{ k='servicio'; n='GestorAtencion'; rol='control'; col=2; f=3
       nota='backend/encounters/services.py (Conflict = 409).'
       ops=$OPS_SERVICIOS_ATENCION },
    @{ k='historial'; n='ControladorHistoriaClinica'; rol='control'; col=2; f=4
       nota='PatientHistoryView en backend/encounters/history_views.py:37 (GET /api/encounters/history/{paciente}/), con CanReadHistory.'
       ops=@('get(request, patient_id)') },
    @{ k='encuentro'; n='Encuentro'; rol='entity'; col=3; f=1
       nota='Tabla encounters (Encounter en encounters/models.py:33).'
       atr=$ATR_ENCUENTRO
       ops=@('is_signed()') },
    @{ k='signos'; n='SignosVitales'; rol='entity'; col=3; f=3
       nota='Tabla encounter_vital_signs (VitalSigns en encounters/models.py:439). CHECK ck_vitals_<campo>_posible y ck_vitals_sistolica_mayor; FK compuesta (encounter_id, organization_id), RLS FORCE y trigger vital_signs_solo_en_borrador (migración 0012).'
       atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'systolic : smallint', 'diastolic : smallint', 'heart_rate : smallint',
             'temperature : numeric(3,1)', 'spo2 : smallint', 'weight_kg : numeric(4,1)', 'height_cm : numeric(4,1)', 'glucose : smallint',
             'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@('bmi()', 'alerts()', 'is_empty()') }
  )
  rel = @(
    @{ d='encuentro'; a='signos'; cd='1'; ca='0..1'; r='registra' }
  )
  grupos = [ordered]@{ 1 = 'Registrar los signos en el borrador'; 2 = 'Un valor imposible se rechaza'; 3 = 'La atención firmada no se edita'; 4 = 'Ver la evolución' }
  guion = @(
    @{ t='msg'; g=1; o='medico'; d='pantalla'; m='escribirSignos(textos)'; src='EditorSignos onCambio, SignosVitales.tsx:28-50; Atencion.tsx:175' },
    @{ t='msg'; g=1; o='pantalla'; d='lector'; m='leerSignos(textos)'; src='SignosVitales.tsx:29; Atencion.tsx:82; signos_vitales.ts:16-35 (lo imposible marca el campo y bloquea guardar y firmar, Atencion.tsx:88, :131)' },
    @{ t='msg'; g=1; o='pantalla'; d='lector'; m='calcular(datos)'; src='SignosVitales.tsx:30; signos_vitales.ts:38-48' },
    @{ t='msg'; g=1; o='lector'; d='pantalla'; m='bmi, alerts (Alta / Baja)'; ret=$true; src='PA >= 140/90 o T >= 38 Alta; SpO2 < 92 Baja; signos_vitales.ts:41-47' },
    @{ t='msg'; g=1; o='medico'; d='pantalla'; m='guardarBorrador()'; src='Guardar borrador, Atencion.tsx:85-97 (los signos van sólo si cambiaron)' },
    @{ t='msg'; g=1; o='pantalla'; d='vista'; m='patch(request, pk)'; src='guardarBorrador: PATCH /api/encounters/{id}/ con vital_signs, api/atencion.ts:197-200; views.py:159' },
    @{ t='msg'; g=1; o='vista'; d='encuentro'; m='filter(organization, pk).first()'; src='_own_encounter, views.py:62-75 (is_own; si no, 404)' },
    @{ t='msg'; g=1; o='vista'; d='serializer'; m='is_valid(raise_exception=True)'; src='EncounterDraftSerializer, views.py:161-162; serializers.py:190-200; _rango :101-117' },
    @{ t='msg'; g=1; o='serializer'; d='serializer'; m='validate(attrs)'; src='diastólica < sistólica, serializers.py:132-138' },
    @{ t='alt' },
    @{ t='op'; g='valores posibles y atención en borrador' },
    @{ t='msg'; g=1; o='vista'; d='servicio'; m='update_draft(encuentro, validated_data)'; src='views.py:163; services.py:114-126' },
    @{ t='msg'; g=1; o='servicio'; d='encuentro'; m='save(update_fields=[campos, updated_at])'; src='services.py:120-123' },
    @{ t='msg'; g=1; o='servicio'; d='servicio'; m='_save_vital_signs(encounter, valores)'; src='services.py:124-125, :129-150 (se reemplazan enteros; null o todo vacío los borra)' },
    @{ t='msg'; g=1; o='servicio'; d='signos'; m='create(encounter, **completos) / save()'; src='services.py:143-150; INSERT INTO encounter_vital_signs ... o UPDATE ... SET systolic, diastolic, ...' },
    @{ t='msg'; g=1; o='vista'; d='pantalla'; m='200(encuentro con vital_signs)'; ret=$true; src='views.py:164; EncounterSerializer.get_vital_signs con bmi y alerts, serializers.py:181-187' },
    @{ t='op'; g='valor imposible (60 °C, diastólica >= sistólica)' },
    @{ t='msg'; g=2; o='serializer'; d='vista'; m='ValidationError(min_value / max_value)'; ret=$true; src='«Temperatura (°C): el máximo posible es 45.», serializers.py:105-117, :134-137' },
    @{ t='msg'; g=2; o='vista'; d='pantalla'; m='400(vital_signs: {campo: [mensaje]})'; ret=$true; src='raise_exception, views.py:162; la base también lo rechaza con CHECK, models.py:470-485' },
    @{ t='op'; g='la atención ya está firmada' },
    @{ t='msg'; g=3; o='vista'; d='servicio'; m='update_draft(encuentro, validated_data)'; src='views.py:163; services.py:115' },
    @{ t='msg'; g=3; o='servicio'; d='vista'; m='Conflict(detail)'; ret=$true; src='services.py:116-119 «El encuentro está firmado y no se edita. Agrega una enmienda.»; trigger vital_signs_solo_en_borrador, 0012:53-78' },
    @{ t='msg'; g=3; o='vista'; d='pantalla'; m='409(detail)'; ret=$true; src='services.py:48-51; firmada, la sección es FilaSignos + enmienda vital_signs, Atencion.tsx:168-175' },
    @{ t='fin' },
    @{ t='msg'; g=4; o='medico'; d='pantalla'; m='verEvolucion(pacienteId)'; src='pestaña Evolución del historial, Historial.tsx:57, :62' },
    @{ t='msg'; g=4; o='pantalla'; d='historial'; m='get(request, patient_id)'; src='verHistorial: GET /api/encounters/history/{id}/, api/atencion.ts:226; Historial.tsx:34; history_views.py:40' },
    @{ t='msg'; g=4; o='historial'; d='servicio'; m='history_scope(request.user, paciente)'; src='history_views.py:44-46; services.py:243 (PROFESSIONAL: tiene o tuvo ficha con el paciente)' },
    @{ t='msg'; g=4; o='historial'; d='encuentro'; m='filter(patient, status=SIGNED)'; src='history_views.py:48-58 con select_related(vital_signs); sólo lo firmado' },
    @{ t='msg'; g=4; o='historial'; d='serializer'; m='get_vital_signs(encuentro)'; src='EncounterSerializer(encuentros, many=True), history_views.py:67; serializers.py:181-187 (VitalSignsSerializer con bmi y alerts, models.py:491-511)' },
    @{ t='msg'; g=4; o='historial'; d='pantalla'; m='200(encounters con vital_signs)'; ret=$true; src='history_views.py:80-86' },
    @{ t='loop'; g='por cada serie con datos (PA, FC, T, SpO2, glucosa, peso, IMC)' },
    @{ t='msg'; g=4; o='pantalla'; d='lector'; m='puntosDe(serie, encuentros)'; src='EvolucionSignos.tsx:87; signos_vitales.ts:95-105 (enmendado = punto hueco)' },
    @{ t='fin' },
    @{ t='msg'; g=4; o='pantalla'; d='medico'; m='GraficoSigno(serie, puntos)'; ret=$true; src='EvolucionSignos.tsx:25-84, :98; franja normal sombreada' }
  )
}


# =========================================================================
# Datos de CU52 (US-51) y CU53 (US-52) del Sprint 4, leidos del codigo el
# 21/11/26 (rama fix/us51-respaldo-y-v1.6.1, con cambios sin commitear de
# otra sesion en calendar.py, attendance.py, serializers.py y urls.py).
# =========================================================================

$ATR_FICHA_S4 = @('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'practitioner_id : uuid',
  'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar',
  'checked_in_at : timestamptz', 'attendance_confirmed_at : timestamptz', 'reminder_sent_at : timestamptz',
  'reinforced_reminder_sent_at : timestamptz', 'expires_at : timestamptz', 'cancelled_at : timestamptz',
  'cancellation_reason : varchar', 'refund_eligible : boolean', 'rescheduled_from_id : uuid',
  'created_at : timestamptz', 'updated_at : timestamptz')

# -------------------------------------------------------------------------
# CU52 (US-51) Experiencia Plus en la Compra de la Ficha
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU52'] = @{
  cu = 'CU52'; nombre = 'Experiencia Plus en la Compra de la Ficha'; us = 'US-51'; plataforma = 'móvil'
  nota = 'Al confirmarse el pago (confirm_payment) el correo de confirmación sale con «Cómo llegar» y la ficha .ics adjunta (attendance.py + calendar.py). En el móvil, la ficha confirmada abre «Mi experiencia Plus» (preconsulta_plus.dart, PR #127 a #129): cuenta regresiva, «Agregar a mi calendario» con el enlace de Google Calendar (no baja el .ics), el mapa de la sede, cómo prepararse y la preconsulta opcional, que el médico ve en la atención. El .ics (CalendarView) lo baja la web (ExperienciaPlus.tsx) y va en el correo.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=1.5 },
    @{ k='medico'; n='Médico'; rol='actor'; col=0; f=6 },
    @{ k='pantalla'; n='PantallaFichaPlus'; rol='boundary'; col=1; f=1.5
       nota='Móvil: mobile/lib/features/appointments/appointment_detail_screen.dart (botón «Mi experiencia Plus», :522-528) y preconsulta_plus.dart (PreconsultaPlusSheet, cuentaRegresiva, enlaceCalendario, _abrirFuera); appointments_api.dart (verFicha). Web: frontend/src/paginas/MisFichas.tsx y frontend/src/componentes/ExperienciaPlus.tsx, que baja el .ics con descargarArchivo (api/cliente.ts:92).'
       atr=@('GET /api/appointments/appointments/{id}/ : 200 | 404', 'GET .../{id}/preconsultation/ : 200 | 404',
             'PUT .../{id}/preconsultation/ : 200 | 400 | 404 | 409', 'GET .../{id}/calendar.ics : 200 | 404 (web)',
             '_reason : TextEditingController', '_questions : TextEditingController', '_editable : bool', '_porQueNo : String?',
             'openUrl : Future<bool> Function(Uri)?', 'branchMapsUrl : String?')
       ops=@('_recargar(silencioso)', '_empezarAEsperar()', '_dejarDeEsperar()', '_pagar()', 'verFicha(client, id)', 'iniciarPago(client, id)',
             'cuentaRegresiva(inicio, ahora, medico)', 'enlaceCalendario(ficha)', '_abrirFuera(url)', '_calendario()', '_comoLlegar()',
             '_load()', '_save()', '_porQueNo()', 'calendario()', 'descargarArchivo(ruta, contexto, nombre)') },
    @{ k='ext'; n='Google Calendar / Maps'; rol='externo'; col=4; f=0.5 },
    @{ k='ctrlficha'; n='ControladorFicha'; rol='control'; col=2; f=0
       nota='AppointmentViewSet en appointments/booking.py (GET /api/appointments/appointments/{id}/) con AppointmentSerializer de appointments/serializers.py (branch_address y branch_maps_url, US-51).'
       ops=@('get_permissions()', 'get_queryset()', 'create(request)', 'retrieve(request, pk)',
             'get_fee(obj)', 'get_branch_maps_url(obj)', 'get_payment_status(obj)') },
    @{ k='ctrlpre'; n='ControladorPreconsulta'; rol='control'; col=2; f=1.5
       nota='PreconsultationView y PreconsultationSerializer en appointments/preconsultation_views.py (GET/PUT /api/appointments/appointments/{id}/preconsultation/).'
       ops=@('_appointment(request, pk)', 'get(request, pk)', 'put(request, pk)', 'is_valid(raise_exception)') },
    @{ k='ctrlcal'; n='ControladorCalendario'; rol='control'; col=2; f=3
       nota='appointments/calendar.py: maps_url («Cómo llegar»), build_ics e ics_filename, y CalendarView (GET .../{id}/calendar.ics, sólo ficha propia y confirmada; la usa la web).'
       ops=@('maps_url(branch)', '_texto(valor)', '_plegar(linea)', 'build_ics(appointment)', 'ics_filename(appointment)', 'get(request, pk)') },
    @{ k='gpagos'; n='GestorPagos'; rol='control'; col=2; f=4
       nota='payments/services.py: confirm_payment confirma la ficha y deja el aviso para después del COMMIT.'
       ops=@('_assert_payable(appointment)', 'start_checkout(appointment, user, request, return_to)', 'confirm_payment(payment, provider_payment_id, request)',
             'register_cash_payment(appointment, user, request)', 'refund_payment(payment, reason, request)', 'refund_for_cancellation(appointment, request)',
             'transfer_payment(origen, destino, request)', '_asentar(request, payment, evento)') },
    @{ k='gconf'; n='GestorConfirmacion'; rol='control'; col=2; f=5
       nota='appointments/attendance.py: send_confirmation_email (lo llama notifications.services.notify(CONFIRMED)); agrega «Cómo llegar» y adjunta el .ics.'
       ops=@('confirm_attendance(appointment, now)', 'post(request, pk)', 'attendance_link(appointment)', 'recipient_user(appointment)',
             '_destinatario(appointment)', 'send_confirmation_email(appointment_id, organization_id)', 'attendance_link_view(request, token)',
             '_pagina(titulo, texto, status)') },
    @{ k='atencion'; n='PantallaAtencion'; rol='boundary'; col=1; f=6
       nota='Web del médico: frontend/src/paginas/Atencion.tsx, sección «Lo que el paciente anotó antes de la consulta» (:158-162).'
       atr=@('GET /api/encounters/{id}/ : 200 | 404', 'encuentro.preconsultation : {reason, questions, updated_at} | null')
       ops=@('abrirAtencion(id)') },
    @{ k='ctrlenc'; n='ControladorAtencion'; rol='control'; col=2; f=6
       nota='EncounterDetailView en encounters/views.py (:146) con EncounterSerializer.get_preconsultation (encounters/serializers.py:152, :166-179): lo escribe el paciente, se muestra aparte y nunca entra en lo firmado.'
       ops=@('get(request, pk)', 'get_preconsultation(encuentro)') },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=1
       nota='Tabla appointments (Appointment en appointments/models.py).'
       atr=$ATR_FICHA_S4
       ops=@('is_active()') },
    @{ k='precon'; n='PreconsultaFicha'; rol='entity'; col=3; f=3
       nota='Tabla appointment_preconsultations (AppointmentPreconsultation en appointments/models.py): notas voluntarias, nunca un diagnóstico.'
       atr=@('id : bigint', 'appointment_id : uuid', 'organization_id : uuid', 'reason : text', 'questions : text', 'updated_at : timestamptz')
       ops=@() },
    @{ k='brevo'; n='Servicio de correo (Brevo)'; rol='externo'; col=4; f=5 }
  )
  rel = @(
    @{ d='ficha'; a='precon'; cd='1'; ca='0..1'; r='se prepara con' }
  )
  grupos = [ordered]@{ 1 = 'Ver la experiencia Plus tras pagar'; 2 = 'Guardar la preconsulta'; 3 = 'Agregar al calendario y cómo llegar'; 4 = 'Ficha ajena, sin pagar, cancelada o ya empezada'; 5 = 'El médico ve la preconsulta' }
  guion = @(
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='pagar()'; src='_pagar appointment_detail_screen.dart:206 (pago de CU19)' },
    @{ t='msg'; g=1; o='gpagos'; d='gpagos'; m='confirm_payment(payment, provider_payment_id)'; src='webhook de la pasarela; payments/services.py:79' },
    @{ t='msg'; g=1; o='gpagos'; d='ficha'; m='save(status=confirmed, expires_at=None)'; src='services.py:118; UPDATE appointments SET status=confirmed' },
    @{ t='msg'; g=1; o='gpagos'; d='gconf'; m='send_confirmation_email(appointment_id, org)'; src='on_commit notify(CONFIRMED) services.py:128; attendance.py:120' },
    @{ t='msg'; g=1; o='gconf'; d='ctrlcal'; m='maps_url(branch)'; src='attendance.py:151-153; calendar.py:25' },
    @{ t='msg'; g=1; o='gconf'; d='ctrlcal'; m='build_ics(appointment)'; src='attendance.py:158; calendar.py:53, ics_filename :104' },
    @{ t='msg'; g=1; o='gconf'; d='brevo'; m='send(fail_silently=False)'; src='correo.attach(nombre, ics, text/calendar) + send, attendance.py:163-164' },
    @{ t='msg'; g=1; o='pantalla'; d='ctrlficha'; m='retrieve(request, pk)'; src='_empezarAEsperar :174, _recargar :113-116; verFicha appointments_api.dart:200; GET /api/appointments/appointments/{id}/' },
    @{ t='msg'; g=1; o='ctrlficha'; d='ctrlcal'; m='maps_url(branch)'; src='get_branch_maps_url, serializers.py:37-40; calendar.py:25' },
    @{ t='msg'; g=1; o='ctrlficha'; d='pantalla'; m='200(ficha confirmed, branch_maps_url)'; ret=$true; src='serializers.py:54' },
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='abrirExperienciaPlus()'; src='«Mi experiencia Plus» appointment_detail_screen.dart:522-528; web MisFichas.tsx:516' },
    @{ t='msg'; g=1; o='pantalla'; d='pantalla'; m='cuentaRegresiva(inicio, ahora, medico)'; src='devuelve la frase entera («Faltan 3 días para tu ficha con...»), preconsulta_plus.dart:24-34, llamada :164-167; web ExperienciaPlus.tsx:37' },
    @{ t='msg'; g=1; o='pantalla'; d='ctrlpre'; m='get(request, pk)'; src='_load preconsulta_plus.dart:117-119; GET .../preconsultation/; preconsultation_views.py:36' },
    @{ t='msg'; g=1; o='ctrlpre'; d='ficha'; m='filter(pk, organization).first()'; src='_appointment, preconsultation_views.py:26-33' },
    @{ t='alt' },
    @{ t='op'; g='propia (owns_appointment) y confirmed o attended' },
    @{ t='msg'; g=1; o='ctrlpre'; d='precon'; m='filter(appointment, organization).first()'; src='preconsultation_views.py:38; SELECT FROM appointment_preconsultations' },
    @{ t='msg'; g=1; o='ctrlpre'; d='pantalla'; m='200(reason, questions, updated_at)'; ret=$true; src='preconsultation_views.py:41-45' },
    @{ t='op'; g='ajena, sin pagar, cancelada o vencida' },
    @{ t='msg'; g=4; o='ctrlpre'; d='pantalla'; m='404'; ret=$true; src='Http404 sin decir cuál, preconsultation_views.py:30, :33' },
    @{ t='fin' },
    @{ t='msg'; g=2; o='paciente'; d='pantalla'; m='guardarPreconsulta(motivo, preguntas)'; src='_save preconsulta_plus.dart:130; sólo si _editable :92' },
    @{ t='msg'; g=2; o='pantalla'; d='ctrlpre'; m='put(request, pk)'; src='client.put preconsulta_plus.dart:133; PUT .../preconsultation/; preconsultation_views.py:47' },
    @{ t='alt' },
    @{ t='op'; g='confirmed y antes de starts_at' },
    @{ t='msg'; g=2; o='ctrlpre'; d='precon'; m='update_or_create(appointment, defaults)'; src='transaction.atomic, preconsultation_views.py:58' },
    @{ t='msg'; g=2; o='ctrlpre'; d='pantalla'; m='200(reason, questions, updated_at)'; ret=$true; src='preconsultation_views.py:62-63' },
    @{ t='op'; g='ya atendida o el turno ya empezó' },
    @{ t='msg'; g=4; o='ctrlpre'; d='pantalla'; m='409(appointment_closed | appointment_started)'; ret=$true; src='preconsultation_views.py:50, :56; _porQueNo preconsulta_plus.dart:150-157' },
    @{ t='fin' },
    @{ t='msg'; g=3; o='paciente'; d='pantalla'; m='agregarAMiCalendario()'; src='tarjeta «Agregar a mi calendario» sólo si _editable, preconsulta_plus.dart:200-208; _calendario :94' },
    @{ t='msg'; g=3; o='pantalla'; d='pantalla'; m='enlaceCalendario(ficha)'; src='Uri https://calendar.google.com/calendar/render?action=TEMPLATE, horas en UTC (Z), lugar y «Cómo llegar» en details; preconsulta_plus.dart:38-57' },
    @{ t='msg'; g=3; o='pantalla'; d='ext'; m='_abrirFuera(url)'; src='(widget.openUrl ?? _abrirFuera)(enlaceCalendario(ficha)): launchUrl(externalApplication), preconsulta_plus.dart:59-60, :95-96; si no abre, «No se pudo abrir el calendario.» :97-99. La web baja el .ics: ExperienciaPlus.tsx:59-61 -> CalendarView, calendar.py:109-121' },
    @{ t='msg'; g=3; o='paciente'; d='pantalla'; m='comoLlegar()'; src='tarjeta sólo si hay branchMapsUrl, preconsulta_plus.dart:210-220; _comoLlegar :102-108' },
    @{ t='msg'; g=3; o='pantalla'; d='ext'; m='_abrirFuera(Uri.parse(branchMapsUrl))'; src='abre Google Maps con las coordenadas de la sede, preconsulta_plus.dart:105; si no abre, «No se pudo abrir el mapa.»' },
    @{ t='msg'; g=5; o='medico'; d='atencion'; m='abrirAtencion(id)'; src='Atencion.tsx' },
    @{ t='msg'; g=5; o='atencion'; d='ctrlenc'; m='get(request, pk)'; src='GET /api/encounters/{id}/; EncounterDetailView, encounters/views.py:146, :153' },
    @{ t='msg'; g=5; o='ctrlenc'; d='ctrlenc'; m='get_preconsultation(encuentro)'; src='EncounterSerializer, encounters/serializers.py:152, :166' },
    @{ t='msg'; g=5; o='ctrlenc'; d='precon'; m='filter(appointment_id).first()'; src='serializers.py:174-175; None si no anotó nada :176-177' },
    @{ t='msg'; g=5; o='ctrlenc'; d='atencion'; m='200(encuentro, preconsultation)'; ret=$true; src='«Lo que el paciente anotó antes de la consulta», Atencion.tsx:158-162' }
  )
}

# -------------------------------------------------------------------------
# CU53 (US-52) Lista de Espera con Aviso de Cupo Liberado
# -------------------------------------------------------------------------
$CASOS_SPRINT4['CU53'] = @{
  cu = 'CU53'; nombre = 'Lista de Espera con Aviso de Cupo Liberado'; us = 'US-52'; plataforma = 'móvil'
  nota = 'El paciente se anota si no hay turnos (waitlist.join); al cancelarse una ficha, el gancho on_commit offer_freed_slot le guarda el turno al primero que encaje como una ficha pending_payment de 15 minutos y lo avisa por push y correo; process_waitlist --loop libera las ofertas vencidas y ofrece el turno al siguiente.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=1 },
    @{ k='sistema'; n='Sistema'; rol='actor'; col=0; f=3 },
    @{ k='pantalla'; n='PantallaListaEspera'; rol='boundary'; col=1; f=1.5
       nota='Móvil: mobile/lib/features/waitlist/anotarse_card.dart y waitlist_api.dart (desde availability_screen.dart cuando no hay espacios), my_appointments_screen.dart (sección En lista de espera), appointment_detail_screen.dart (cancelar, cuenta regresiva y pagar) y core/notifications/push.dart (tocar el aviso). Web: frontend/src/componentes/TarjetaListaEspera.tsx, paginas/Disponibilidad.tsx, paginas/MisFichas.tsx y api/listaEspera.ts.'
       atr=@('GET /api/appointments/waitlist/ : 200(enabled, results)', 'POST /api/appointments/waitlist/ : 201 | 400 | 403',
             'DELETE /api/appointments/waitlist/{id}/ : 204 | 404', 'POST .../appointments/{id}/cancel/ : 200 | 400 | 403 | 404',
             '_desde : DateTime', '_hasta : DateTime', '_paraQuien : PatientOption?', '_restante : Duration?')
       ops=@('_elegirFechas()', '_anotarme()', 'anotarseEnListaDeEspera(client, patientId, practitionerId, dateFrom, dateTo)',
             'miListaDeEspera(client)', 'salirDeListaDeEspera(client, id)', 'mensajeDeListaDeEspera(error)',
             '_cargarEspera()', '_salirDeLaLista(entrada)', '_cancelar()', 'cancelarFicha(client, id)', '_pagar()',
             '_ajustarCuentaRegresiva(ficha)', 'tocarAviso(appointmentId)', '_abrir(appointmentId)') },
    @{ k='ctrlespera'; n='ControladorListaEspera'; rol='control'; col=2; f=0
       nota='WaitlistView, WaitlistEntryView y WaitlistSummaryView en appointments/waitlist_views.py (/api/appointments/waitlist/), con WaitlistEntrySerializer y JoinWaitlistSerializer. Pide el plan con waitlist (Pro y Premium).'
       ops=@('get_permissions()', 'get(request)', 'post(request)', 'delete(request, pk)', '_mias(request)', '_error(codigo, detalle, http)',
             '_fecha(valor)', 'get_position(obj)', 'get_offered_expires_at(obj)') },
    @{ k='ctrlcancel'; n='ControladorCancelacion'; rol='control'; col=2; f=1
       nota='CancelAppointmentView y cancel_appointment en appointments/changes.py (POST /api/appointments/appointments/{id}/cancel/); deja offer_freed_slot en transaction.on_commit.'
       ops=@('post(request, pk)', '_notice(appointment, now)', '_assert_cancellable(appointment, now)', 'cancel_appointment(appointment, now)',
             'reschedule_appointment(appointment, ...)', '_puede_operar(user, appointment)', '_get_appointment_or_404(request, pk)') },
    @{ k='gespera'; n='GestorListaEspera'; rol='control'; col=2; f=2
       nota='appointments/waitlist.py; la reserva del turno guardado es book_appointment (booking.py) y el vencimiento release_expired_holds (holds.py). Lo corre en fondo manage.py process_waitlist --loop.'
       ops=@('has_feature(organization)', '_error(mensaje, codigo)', '_hoy(organization)',
             'join(organization, user, patient_id, practitioner_id, specialty_id, branch_id, date_from, date_to, today)',
             '_hay_turno_libre(profesional, especialidad, sucursal, desde, hasta)', 'leave(entry)', 'position(entry)',
             '_candidatos(ficha)', '_quienes_lo_soltaron(ficha)', '_ocupado_a_esa_hora(entry, ficha)', 'offer_slot(ficha, now)',
             'offer_freed_slot(appointment_id, organization_id)', 'refresh_entries(organization, today)', '_ya_reservo(entrada)',
             '_turnos_libres_que_alguien_espera(organization, now)', 'run_organization(organization, now)',
             'eligible_organizations()', 'run_due(now)', 'summary(organization, desde, hasta)') },
    @{ k='gavisos'; n='GestorAvisos'; rol='control'; col=2; f=3
       nota='notifications/services.py (notify con el evento cupo_liberado: push y correo por send_mail) y notifications/push.py (send_to_user contra FCM).'
       ops=@('notify(event, appointment_id, organization_id)', '_load(appointment_id)', '_recipient(appointment)', '_minutos()',
             '_cuando(appointment)', '_push_text(event, appointment)', '_datos(appointment)', '_email(event, appointment)', '_devolucion(appointment)',
             'send_to_user(user, message)', '_payload(token, message)', '_is_dead(response)', '_authorized_session()', '_read_credentials(raw)') },
    @{ k='entrada'; n='EntradaListaEspera'; rol='entity'; col=3; f=1
       nota='Tabla waitlist_entries (WaitlistEntry en appointments/models.py). Estados waiting, offered, booked, expired, cancelled.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'requested_by_id : uuid', 'practitioner_id : uuid',
             'specialty_id : uuid', 'branch_id : uuid', 'date_from : date', 'date_to : date', 'status : varchar(10)',
             'offered_appointment_id : uuid', 'offered_at : timestamptz', 'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@() },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=2
       nota='Tabla appointments (Appointment en appointments/models.py). El turno guardado es una ficha pending_payment con expires_at.'
       atr=$ATR_FICHA_S4
       ops=@('is_active()') },
    @{ k='fcm'; n='Firebase Cloud Messaging'; rol='externo'; col=4; f=1.5 }
  )
  rel = @(
    @{ d='ficha'; a='entrada'; cd='0..1'; ca='0..*'; r='se ofrece como' }
  )
  grupos = [ordered]@{ 1 = 'Anotarse en la lista de espera'; 2 = 'Se cancela una ficha y se ofrece el turno'; 3 = 'Tomar el turno guardado'; 4 = 'El turno vence y pasa al siguiente'; 5 = 'No se puede anotar' }
  guion = @(
    @{ t='msg'; g=1; o='paciente'; d='pantalla'; m='anotarme(desde, hasta, paraQuien)'; src='_elegirFechas :73, _anotarme anotarse_card.dart:99; availability_screen.dart:170' },
    @{ t='msg'; g=1; o='pantalla'; d='ctrlespera'; m='post(request)'; src='anotarseEnListaDeEspera waitlist_api.dart:135; POST /api/appointments/waitlist/; waitlist_views.py:130' },
    @{ t='msg'; g=1; o='ctrlespera'; d='gespera'; m='join(organization, user, patient_id, ...)'; src='require_feature :132; waitlist_views.py:138; waitlist.py:77' },
    @{ t='msg'; g=1; o='gespera'; d='gespera'; m='_hay_turno_libre(prof, esp, desde, hasta)'; src='waitlist.py:139, :158 (consolidated_availability)' },
    @{ t='alt' },
    @{ t='op'; g='sin turnos libres y sin entrada viva igual' },
    @{ t='msg'; g=1; o='gespera'; d='entrada'; m='create(patient, date_from, date_to, ...)'; src='waitlist.py:147; INSERT INTO waitlist_entries (status=waiting)' },
    @{ t='msg'; g=1; o='ctrlespera'; d='pantalla'; m='201(entrada, position)'; ret=$true; src='waitlist_views.py:148; position waitlist.py:209' },
    @{ t='op'; g='hay turnos, ya anotado o plan sin lista de espera' },
    @{ t='msg'; g=5; o='gespera'; d='ctrlespera'; m='ValidationError(hay_turnos | ya_anotado)'; ret=$true; src='waitlist.py:140, :154 (uq_waitlist_live)' },
    @{ t='msg'; g=5; o='ctrlespera'; d='pantalla'; m='400(code) | 403(plan_limit)'; ret=$true; src='waitlist_views.py:132, :147; mensajeDeListaDeEspera anotarse_card.dart:28, :127' },
    @{ t='fin' },
    @{ t='msg'; g=2; o='paciente'; d='pantalla'; m='cancelarFicha()'; src='otro paciente: _cancelar appointment_detail_screen.dart:283, cancelarFicha :318' },
    @{ t='msg'; g=2; o='pantalla'; d='ctrlcancel'; m='post(request, pk)'; src='POST /api/appointments/appointments/{id}/cancel/; changes.py:161' },
    @{ t='msg'; g=2; o='ctrlcancel'; d='ficha'; m='save(status=cancelled, cancelled_at)'; src='cancel_appointment changes.py:51-73; UPDATE appointments' },
    @{ t='msg'; g=2; o='ctrlcancel'; d='pantalla'; m='200(ficha)'; ret=$true; src='changes.py:203; la oferta corre después del COMMIT' },
    @{ t='msg'; g=2; o='ctrlcancel'; d='gespera'; m='offer_freed_slot(appointment_id, org_id)'; src='transaction.on_commit changes.py:201; waitlist.py:329; offer_slot :275 (check_limit del plan)' },
    @{ t='loop'; g='por cada candidata de _candidatos(ficha), por orden de llegada' },
    @{ t='msg'; g=2; o='gespera'; d='entrada'; m='select_for_update().filter(pk, status=waiting)'; src='waitlist.py:296-303 (_ocupado_a_esa_hora la salta)' },
    @{ t='msg'; g=2; o='gespera'; d='ficha'; m='book_appointment(patient_id, starts_at, ...)'; src='booking.py:73; waitlist.py:306; INSERT appointments pending_payment, expires_at = ahora + 15 min' },
    @{ t='msg'; g=2; o='gespera'; d='entrada'; m='save(status=offered, offered_appointment)'; src='waitlist.py:319-325' },
    @{ t='fin' },
    @{ t='msg'; g=2; o='gespera'; d='gavisos'; m='notify(CUPO_LIBERADO, nueva.id, org_id)'; src='waitlist.py:354-356; notifications/services.py:51; correo por send_mail :82' },
    @{ t='msg'; g=2; o='gavisos'; d='fcm'; m='send_to_user(user, Message(titulo, cuerpo))'; src='_push_text services.py:134; push.py:119, session.post :141' },
    @{ t='msg'; g=3; o='paciente'; d='pantalla'; m='tocarAviso(appointmentId)'; src='push.dart:292, _abrir :303 (data.appointment_id)' },
    @{ t='msg'; g=3; o='pantalla'; d='pantalla'; m='_ajustarCuentaRegresiva(ficha)'; src='los 15 min del turno guardado; appointment_detail_screen.dart:139' },
    @{ t='msg'; g=3; o='paciente'; d='pantalla'; m='pagar()'; src='_pagar appointment_detail_screen.dart:206 (pago de CU19)' },
    @{ t='msg'; g=4; o='sistema'; d='gespera'; m='run_due(now)'; src='manage.py process_waitlist --loop, _vuelta process_waitlist.py:73-74; waitlist.py:492' },
    @{ t='loop'; g='por cada organización activa con lista de espera' },
    @{ t='msg'; g=4; o='gespera'; d='ficha'; m='release_expired_holds(now, include_offers)'; src='run_organization waitlist.py:466-471; holds.py:72; UPDATE appointments SET status=expired' },
    @{ t='msg'; g=4; o='gespera'; d='gespera'; m='refresh_entries(organization)'; src='waitlist.py:363' },
    @{ t='alt' },
    @{ t='op'; g='la ficha ofrecida se pagó' },
    @{ t='msg'; g=3; o='gespera'; d='entrada'; m='save(status=booked)'; src='waitlist.py:383-395' },
    @{ t='op'; g='venció sin pagar' },
    @{ t='msg'; g=4; o='gespera'; d='entrada'; m='save(status=expired)'; src='waitlist.py:390-395; rango pasado: update :397-399' },
    @{ t='fin' },
    @{ t='msg'; g=4; o='gespera'; d='gespera'; m='offer_freed_slot(ficha.id, organization.id)'; src='al siguiente de la fila; _turnos_libres_que_alguien_espera :431; waitlist.py:474-476' },
    @{ t='fin' }
  )
}


