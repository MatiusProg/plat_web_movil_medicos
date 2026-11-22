# =========================================================================
# Datos de los diagramas de ESTADO y TIEMPO del Sprint 4.
#
# Lo consumen, despues de ea-sprint4-comun.ps1:
#   ea-estado-sprint4.ps1   clave 'estado'
#   ea-tiempo-sprint4.ps1   clave 'tiempo'
#
# El formato es el de ea-sprint3-dinamica.ps1 (claves estado y tiempo):
#   estado = @{ estados = @( @{ k; n; col; f } | @{ k; tipo='inicial'|'final'; col; f } )
#               transiciones = @( @{ de; a; r='evento [guarda] / accion {archivo:linea}' } ) }
#            ortogonal=$true en la unica flecha de vuelta del sumidero de errores.
#   tiempo = @{ escenario; nota; lineas = @( @{ n; estados; marcas = @( @{ t; e; ev; r } ) } ) }
#            t de 0 a 84; r sin llaves.
# Leidos del codigo el 22/11/26 (main 2349f66). Los nombres de los casos de
# uso salen de ea-sprint4-casos.ps1.
# =========================================================================

$DINAMICA_SPRINT4 = @{}

# =========================================================================
# Datos de ESTADO y TIEMPO del Sprint 4: CU36 (US-35), CU37 (US-36),
# CU38 (US-37) y CU39 (US-38). Formato: SPEC-estado-tiempo-sprint4.md.
# Leídos del código en main 2349f66 el 22/11/26 (backend/noshow,
# appointments/reminders.py, reporting/demand*.py, frontend/src/paginas).
# =========================================================================

# -------------------------------------------------------------------------
# CU36 (US-35) Predicción de Riesgo de Inasistencia
# Estado: la consulta de la Administración (tarjeta del modelo y lista de
# fichas). Tiempo: el proceso score_noshow --loop que escribe la predicción.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU36'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Administrador';            col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';               col=1; f=2 },
      @{ k='pedm';   n='Pedir estado del modelo';             col=2; f=0.5 },
      @{ k='capf';   n='Capturar filtros';                    col=2; f=3 },
      @{ k='valm';   n='Buscar versión active';               col=3; f=0 },
      @{ k='valsin'; n='Explicar la falta de modelo';         col=3; f=1.5 },
      @{ k='valf';   n='Validar filtros';                     col=3; f=3 },
      @{ k='listar'; n='Leer predicciones del modelo vigente'; col=3; f=4.5 },
      @{ k='error';  n='Informar error';                      col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';              col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';    a='aut' },
      @{ de='aut';    a='menu';   r='[token y appointments.noshow.read] {CanReadNoShow, permissions.py:14; views.py:86}' },
      @{ de='aut';    a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';   a='pedm';   r='[abrir la pantalla] / verModeloRiesgo() {RiesgoInasistencia.tsx:222}' },
      @{ de='menu';   a='capf';   r='[filtrar] {RiesgoInasistencia.tsx:245-248}' },
      @{ de='pedm';   a='valm';   r='GET /api/noshow/model/ {riesgo.ts:107; views.py:174}' },
      @{ de='valm';   a='ok';     r='[plan y status=active] / 200(model, metrics, cutoffs) {views.py:180-198}' },
      @{ de='valm';   a='valsin'; r='[sin versión active] {views.py:181}' },
      @{ de='valm';   a='error';  r='[sin organización o plan sin noshow_prediction] {403 views.py:176, :178; plans.py:114}' },
      @{ de='valsin'; a='ok';     r='[rejected | < 200 fichas o 20 ausencias | nada] / 200(model=null, reason) {views.py:206, :220, :228}' },
      @{ de='capf';   a='valf';   r='listarRiesgo(desde, hasta, sucursal, nivel) {RiesgoInasistencia.tsx:248; views.py:88}' },
      @{ de='valf';   a='listar'; r='[fechas, rango < 366 días, nivel y sucursal propia] {views.py:104-124}' },
      @{ de='valf';   a='error';  r='[plan sin la función o filtro inválido] {403 views.py:92; 400 :105, :107, :109, :114, :121}' },
      @{ de='listar'; a='ok';     r='[model_version active, ficha activa y futura] / página de 25 {views.py:127-150}' },
      @{ de='error';  a='menu';   r='/ mensaje de error'; ortogonal=$true },
      @{ de='ok';     a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el entrenamiento deja una versión active, la vuelta siguiente de score_noshow califica las fichas de los próximos 60 días y la Administración las consulta'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. train_noshow (training.py:93) crea la versión con status active si supera la línea base y no hay otra vigente, candidate si ya la hay y rejected si no supera (training.py:205-210); sólo active califica (scoring.py:91-98). 60 min = --every por omisión de score_noshow (score_noshow.py:36, :49, :65), el proceso que lanza scripts/start.sh:54; se apaga con NOSHOW_SCORING=off (config/settings.py:307). 60 días = HORIZON_DAYS (scoring.py:41, :113): se califican las fichas pending_payment y confirmed que empiezan dentro de ese horizonte. Transacción de la organización: Fijando inquilino es tenant_context(org) (scoring.py:104), que abre transaction.atomic (tenancy/context.py:57); Validando es active_version(); Escribiendo es bulk_create y bulk_update de noshow_predictions (scoring.py:151-156); Confirmada es el COMMIT al salir del bloque. La consulta web pide un JWT vigente: 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:387). Muestra sólo predicciones de la versión active y de fichas futuras (noshow/views.py:133-135).'
    lineas = @(
      @{ n='Comando score_noshow'
         estados=@('Durmiendo', 'Dando la vuelta')
         marcas=@( @{ t=0;  e='Durmiendo';       ev='time.sleep()' },
                   @{ t=12; e='Dando la vuelta'; ev='_vuelta()'; r='60 min' },
                   @{ t=40; e='Durmiendo';       ev='puntuadas' },
                   @{ t=84; e='Dando la vuelta'; ev='_vuelta()'; r='60 min' } ) },
      @{ n='Versión del modelo'
         estados=@('Sin versión', 'active')
         marcas=@( @{ t=0; e='Sin versión' },
                   @{ t=6; e='active'; ev='train_for()' } ) },
      @{ n='Transacción de la organización'
         estados=@('Inactiva', 'Fijando inquilino', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=16; e='Fijando inquilino'; ev='tenant_context()' },
                   @{ t=20; e='Validando';         ev='active_version()' },
                   @{ t=26; e='Escribiendo';       ev='bulk_create()' },
                   @{ t=34; e='Confirmada';        ev='COMMIT' },
                   @{ t=38; e='Inactiva' } ) },
      @{ n='Ficha'
         estados=@('Sin calificar', 'Calificada')
         marcas=@( @{ t=0;  e='Sin calificar'; ev='confirmed' },
                   @{ t=34; e='Calificada';    ev='level, factors'; r='<= 60 días' } ) },
      @{ n='Consulta de la Administración'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Leyendo', 'Respondida')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=52; e='Autenticando'; ev='GET /appointments/'; r='30 min' },
                   @{ t=56; e='Validando';    ev='require_feature()' },
                   @{ t=60; e='Leyendo';      ev='SELECT' },
                   @{ t=66; e='Respondida';   ev='200' },
                   @{ t=70; e='Inactiva' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU37 (US-36) Envío de Recordatorios por Riesgo de Inasistencia
# Flujo del comando send_appointment_reminders --loop: la vuelta del
# refuerzo, después del recordatorio de 24 h de US-28 (CU29 del Sprint 3).
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU37'] = @{
  estado = @{
    estados = @(
      @{ k='ini';     tipo='inicial'; col=0; f=0 },
      @{ k='vuelta';  n='Iniciar comando';                    col=0; f=2 },
      @{ k='finoff';  tipo='final';   col=0; f=4.5 },
      @{ k='orgs';    n='Recorrer organizaciones activas';    col=1; f=1 },
      @{ k='esperar'; n='Esperar la vuelta siguiente';        col=1; f=4 },
      @{ k='recn';    n='Mandar recordatorios de 24 h';       col=2; f=0 },
      @{ k='plan';    n='Verificar plan con predicción';      col=2; f=2 },
      @{ k='listar';  n='Listar fichas de riesgo alto';       col=2; f=3.5 },
      @{ k='sig';     n='Tomar siguiente ficha';              col=3; f=2 },
      @{ k='bloq';    n='Bloquear ficha';                     col=3; f=3.5 },
      @{ k='avisar';  n='Avisar por push y correo';           col=3; f=5 },
      @{ k='marcar';  n='Marcar reinforced_reminder_sent_at'; col=4; f=4.5 },
      @{ k='error';   n='Informar error';                     col=4; f=6 },
      @{ k='ok';      n='Transacción completada';             col=4; f=1.5 },
      @{ k='fin';     tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';     a='vuelta' },
      @{ de='vuelta';  a='finoff';  r='[APPOINTMENT_REMINDERS en off, 0 o false] {send_appointment_reminders.py:46-48}' },
      @{ de='vuelta';  a='recn';    r='handle() [encendido] / _vuelta(), run_cycle() {send_appointment_reminders.py:60, :73}' },
      @{ de='recn';    a='orgs';    r='/ run_for() de US-28 en cada organización; después, el refuerzo {reminders.py:163-166}' },
      @{ de='orgs';    a='plan';    r='[queda una organización activa] / run_reinforced_for(org) {reminders.py:148-150, :123}' },
      @{ de='plan';    a='orgs';    r='[plan sin noshow_prediction] / return 0 {reminders.py:132-133; scoring.py:160}' },
      @{ de='plan';    a='listar';  r='[has_feature] / due_reinforced(now) en tenant_context(org) {reminders.py:134, :92-93}' },
      @{ de='listar';  a='sig';     r='/ pks: confirmed, sin marca, en 3 h, level=high, versión active {reminders.py:77-84}' },
      @{ de='sig';     a='orgs';    r='[no quedan pks] / return avisadas {reminders.py:113}' },
      @{ de='sig';     a='bloq';    r='[queda un pk] / tenant_context(org): una transacción por ficha {reminders.py:96, :99}' },
      @{ de='bloq';    a='avisar';  r='[skip_locked devuelve la ficha] / notify(REINFORCED_REMINDER) {reminders.py:102-109}' },
      @{ de='bloq';    a='sig';     r='[None: la tomó otro proceso o ya no corresponde] / continue {reminders.py:106-108}' },
      @{ de='avisar';  a='marcar';  r='[enviado, sin destinatario o fallido: notify no propaga] {services.py:66-67, :75, :85}' },
      @{ de='marcar';  a='sig';     r='/ reinforced_reminder_sent_at = now(), save(), COMMIT {reminders.py:110-111}' },
      @{ de='marcar';  a='error';   r='[excepción en la base dentro de _enviar] {reminders.py:150-151}' },
      @{ de='error';   a='orgs';    r='/ logger.exception: siguiente organización, la ficha queda sin marcar {reminders.py:152}'; ortogonal=$true },
      @{ de='orgs';    a='ok';      r='[no quedan organizaciones] / return (normales, reforzados) {reminders.py:167}' },
      @{ de='ok';      a='esperar'; r='[--loop] / time.sleep(every * 60) {send_appointment_reminders.py:54, :70}' },
      @{ de='esperar'; a='recn';    r='/ close_old_connections(), _vuelta() {send_appointment_reminders.py:69, :60}' },
      @{ de='ok';      a='fin';     r='[sin --loop] {send_appointment_reminders.py:50-52}' }
    )
  }

  tiempo = @{
    escenario = 'la ficha confirmada de riesgo alto recibe el recordatorio de 24 horas y, ya dentro de las 3 horas, una vuelta le manda el refuerzo una sola vez'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos; entre el aviso de 24 h y el de 3 h pasan muchas vueltas que no se dibujan. 24 h = APPOINTMENT_REMINDER_HOURS (config/settings.py:297, appointments/reminders.py:59). 3 h = APPOINTMENT_REINFORCED_REMINDER_HOURS (config/settings.py:302-304): due_reinforced() toma las fichas confirmed sin reinforced_reminder_sent_at que empiezan dentro de las próximas 3 h, reservadas antes de esa ventana, con predicción level=high de una versión active (reminders.py:76-84). La predicción la escribe score_noshow cada 60 min (score_noshow.py:36); acá sólo se lee. 15 min = --every por omisión (send_appointment_reminders.py:41, :54), el proceso de scripts/start.sh:47: el refuerzo sale a lo sumo unos 15 min después de entrar en la ventana. 10 s = TIMEOUT_SECONDS de cada POST a FCM (notifications/push.py:36, :142). Transacción de la ficha: Fijando inquilino es tenant_context(org) (reminders.py:99; tenancy/context.py:57), Validando es el SELECT ... FOR UPDATE SKIP LOCKED con las condiciones de due_reinforced() (reminders.py:102-105), Escribiendo es notify() más el UPDATE de reinforced_reminder_sent_at (:109-111) y Confirmada es el COMMIT. El envío nunca deshace la transacción (notifications/services.py:75-76, :85-86). En la vuelta siguiente (t = 84) la ficha ya tiene la marca: el refuerzo no se repite.'
    lineas = @(
      @{ n='Comando de recordatorios'
         estados=@('Durmiendo', 'Dando la vuelta')
         marcas=@( @{ t=0;  e='Durmiendo';       ev='time.sleep()' },
                   @{ t=8;  e='Dando la vuelta'; ev='run_cycle()'; r='15 min' },
                   @{ t=20; e='Durmiendo' },
                   @{ t=48; e='Dando la vuelta'; ev='run_cycle()'; r='15 min' },
                   @{ t=70; e='Durmiendo';       ev='reforzadas' },
                   @{ t=84; e='Dando la vuelta'; ev='run_cycle()'; r='15 min' } ) },
      @{ n='Predicción de la ficha'
         estados=@('Sin calificar', 'high')
         marcas=@( @{ t=0; e='Sin calificar' },
                   @{ t=4; e='high'; ev='score_for()'; r='60 min' } ) },
      @{ n='Ficha'
         estados=@('Fuera de la ventana', 'Recordada', 'En la ventana de 3 h', 'Reforzada')
         marcas=@( @{ t=0;  e='Fuera de la ventana';  ev='confirmed' },
                   @{ t=12; e='Recordada';            ev='reminder_sent_at'; r='24 h' },
                   @{ t=44; e='En la ventana de 3 h'; ev='faltan 3 h'; r='3 h' },
                   @{ t=64; e='Reforzada';            ev='reinforced_sent_at'; r='< 15 min' } ) },
      @{ n='Transacción de la ficha'
         estados=@('Inactiva', 'Fijando inquilino', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=50; e='Fijando inquilino'; ev='tenant_context()' },
                   @{ t=53; e='Validando';         ev='SKIP LOCKED' },
                   @{ t=56; e='Escribiendo';       ev='notify()' },
                   @{ t=64; e='Confirmada';        ev='COMMIT' },
                   @{ t=67; e='Inactiva' } ) },
      @{ n='Aviso push reforzado'
         estados=@('Sin aviso', 'En FCM', 'Mostrado')
         marcas=@( @{ t=0;  e='Sin aviso' },
                   @{ t=58; e='En FCM';   ev='send_to_user()'; r='10 s' },
                   @{ t=61; e='Mostrado'; ev='onMessage' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU38 (US-37) Proyección de Demanda de Fichas
# Transacción de lectura de la web. Lo que manda el reloj es el calendario:
# semanas cerradas del histórico, semana en curso excluida, semanas futuras.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU38'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Administrador';                 col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar semanas y sucursal';           col=1; f=2 },
      @{ k='pedir';  n='Pedir proyección';                         col=2; f=0.5 },
      @{ k='leer';   n='Contar fichas por especialidad y franja';  col=2; f=2.5 },
      @{ k='cap';    n='Calcular capacidad de las agendas';        col=2; f=4 },
      @{ k='back';   n='Medir el error con backtest';              col=2; f=5.5 },
      @{ k='valid';  n='Validar organización y parámetros';        col=3; f=0.5 },
      @{ k='armar';  n='Comparar demanda con capacidad';           col=3; f=4 },
      @{ k='error';  n='Informar error';                           col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';                   col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y reporting.kpi.read] {CanReadKpis, permissions.py:57; demand_views.py:15}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='pedir';  r='elegirFiltros(weeks, branch) {ProyeccionDemanda.tsx:135, :141}' },
      @{ de='pedir'; a='valid';  r='verProyeccionDemanda() / GET /api/reporting/demand/ {ProyeccionDemanda.tsx:110; demand.ts:38}' },
      @{ de='valid'; a='error';  r='[sin organización, weeks fuera de 1..8 o sucursal ajena] {403 demand_views.py:19; 400 :26, :33, :36}' },
      @{ de='valid'; a='leer';   r='[1 <= weeks <= 8 y sucursal propia] / project(org, weeks, branch) {demand_views.py:39; demand.py:32}' },
      @{ de='leer';  a='cap';    r='/ especialidad principal; confirmed, attended y no_show de 16 semanas {demand.py:45-81}' },
      @{ de='cap';   a='back';   r='/ generate_slots() por agenda vigente, sin bloqueos ni espacios pasados {demand.py:84-111}' },
      @{ de='back';  a='armar';  r='/ walk-forward: cada semana con las 8 anteriores; MAE y WAPE {demand.py:116-128, :159-160}' },
      @{ de='armar'; a='ok';     r='[con o sin histórico] / 200(rows, validation, has_historical_data) {demand.py:130-169}' },
      @{ de='error'; a='menu';   r='/ mensaje de error'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'la Administración pide la proyección a mitad de semana: la semana en curso queda fuera y la proyección empieza el lunes siguiente'
    nota = 'Regla relativa (0 a 100): instantes del escenario sobre el calendario, no milisegundos medidos. La proyección empieza el lunes siguiente (demand.py:36-39) y dura weeks semanas, de 1 a 8 = MAX_WEEKS (demand.py:21; demand_views.py:26). La semana en curso, incompleta, se excluye del histórico (demand.py:41-42). Histórico: las 8 semanas cerradas anteriores = HISTORY_WEEKS (demand.py:20, :43); antes, otras 8 de calentamiento del backtest walk-forward (demand.py:44, :113-128). La capacidad sólo cuenta espacios que empiezan después de now (demand.py:103) y descuenta los bloqueos que se superponen (:105-109). La transacción es una sola lectura, sin escritura: 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:387) para el GET.'
    lineas = @(
      @{ n='Transacción de la proyección'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Calculando', 'Respondida')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=50; e='Autenticando'; ev='GET /demand/'; r='30 min' },
                   @{ t=52; e='Validando';    ev='weeks 1..8' },
                   @{ t=54; e='Calculando';   ev='project()' },
                   @{ t=58; e='Respondida';   ev='200' },
                   @{ t=60; e='Inactiva' } ) },
      @{ n='Semanas del calendario'
         estados=@('Calentamiento', 'Histórico', 'Semana en curso', 'Proyectadas')
         marcas=@( @{ t=0;  e='Calentamiento';   ev='backtest_start'; r='8 sem' },
                   @{ t=24; e='Histórico';       ev='hist_start'; r='8 sem' },
                   @{ t=48; e='Semana en curso'; ev='hist_end' },
                   @{ t=56; e='Proyectadas';     ev='lunes siguiente'; r='1 a 8 sem' } ) },
      @{ n='Espacio de agenda'
         estados=@('No cuenta', 'Cuenta')
         marcas=@( @{ t=0;  e='No cuenta' },
                   @{ t=54; e='Cuenta';    ev='slot_start > now' },
                   @{ t=70; e='No cuenta'; ev='ScheduleBlock' },
                   @{ t=76; e='Cuenta';    ev='fin del bloqueo' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU39 (US-38) Reentrenamiento del Modelo de No-Show
# Flujo del comando retrain_noshow --all --loop: candidate, y active sólo
# si gana; si no, rejected. La vigente anterior pasa a retired.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU39'] = @{
  estado = @{
    estados = @(
      @{ k='ini';      tipo='inicial'; col=0; f=0 },
      @{ k='vuelta';   n='Iniciar comando';                        col=0; f=2 },
      @{ k='finerr';   tipo='final';   col=0; f=4.5 },
      @{ k='orgs';     n='Recorrer organizaciones con el plan';    col=1; f=1 },
      @{ k='esperar';  n='Esperar la vuelta siguiente';            col=1; f=4 },
      @{ k='bloq';     n='Bloquear organización';                  col=2; f=0 },
      @{ k='contar';   n='Contar desenlaces nuevos';               col=2; f=1.5 },
      @{ k='entrenar'; n='Entrenar candidato';                     col=2; f=3 },
      @{ k='evaluar';  n='Armar desenlaces posteriores al vigente'; col=3; f=1 },
      @{ k='comparar'; n='Comparar Brier con el vigente';          col=3; f=2.5 },
      @{ k='promover'; n='Promover candidato a active';            col=3; f=4 },
      @{ k='rechazar'; n='Rechazar candidato';                     col=3; f=5.5 },
      @{ k='error';    n='Informar error';                         col=4; f=6 },
      @{ k='ok';       n='Transacción completada';                 col=4; f=1.5 },
      @{ k='fin';      tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';      a='vuelta' },
      @{ de='vuelta';   a='finerr';   r='[sin --organization ni --all, --every < 1 o slug desconocido] / CommandError {retrain_noshow.py:28-37}' },
      @{ de='vuelta';   a='orgs';     r='handle() / run(), run_due(slugs, min_new) {retrain_noshow.py:39-44; retraining.py:107}' },
      @{ de='orgs';     a='bloq';     r='[queda una organización activa con noshow_prediction] / retrain_for() {retraining.py:110-113}' },
      @{ de='bloq';     a='contar';   r='/ atomic, select_for_update(Organization), active_version() {retraining.py:45-53}' },
      @{ de='contar';   a='orgs';     r='[hay versión y nuevos < 20] / RetrainResult(skipped) {retraining.py:54-58}' },
      @{ de='contar';   a='entrenar'; r='[sin versión o nuevos >= 20] / train_for() {retraining.py:60; training.py:93}' },
      @{ de='entrenar'; a='orgs';     r='[sin datos | rejected | sin vigente: queda active] / RetrainResult {retraining.py:61-65}' },
      @{ de='entrenar'; a='evaluar';  r='[status=candidate y hay active] / 20 % final, posterior a trained_at {retraining.py:68-75}' },
      @{ de='evaluar';  a='rechazar'; r='[< 20 desenlaces o una sola clase] / sin_evaluacion_independiente {retraining.py:80-83}' },
      @{ de='evaluar';  a='comparar'; r='/ _brier(vigente), _brier(candidato), retraining_comparison {retraining.py:85-91}' },
      @{ de='comparar'; a='rechazar'; r='[Brier candidato >= vigente - 1e-6] / no_mejora_vigente {retraining.py:92-94}' },
      @{ de='comparar'; a='promover'; r='[mejora] / promote(candidate) {retraining.py:96; training.py:219}' },
      @{ de='promover'; a='orgs';     r='[beats_baseline] / vigente a retired, candidato a active, COMMIT {training.py:228-236}' },
      @{ de='promover'; a='error';    r='[ValueError sin beats_baseline o falla de la base] {training.py:229-230}' },
      @{ de='rechazar'; a='orgs';     r='/ _reject(): status=rejected, save() {retraining.py:101-104}' },
      @{ de='error';    a='orgs';     r='/ logger.exception, RetrainResult(error): siguiente organización {retraining.py:114-117}'; ortogonal=$true },
      @{ de='orgs';     a='ok';       r='[no quedan organizaciones] / imprime acción y mensaje {retrain_noshow.py:40-41}' },
      @{ de='ok';       a='esperar';  r='[--loop] / time.sleep(every * 60) {retrain_noshow.py:51}' },
      @{ de='esperar';  a='orgs';     r='/ close_old_connections(), run() {retrain_noshow.py:48-50}' },
      @{ de='ok';       a='fin';      r='[sin --loop] {retrain_noshow.py:43-45}' }
    )
  }

  tiempo = @{
    escenario = 'con 20 desenlaces nuevos, la vuelta diaria de retrain_noshow entrena un candidato que mejora el Brier, lo promueve, y score_noshow recalifica después'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 1440 min = --every por omisión de retrain_noshow (retrain_noshow.py:23, :51): una vuelta al día; no lo lanza scripts/start.sh (cron externo o --loop, retrain_noshow.py:3-4). 20 = MIN_NEW_OUTCOMES y MIN_EVALUATION (retraining.py:22-23): desenlaces con etiqueta nuevos desde la última versión (retraining.py:54-57) y desenlaces del 20 % final posteriores a trained_at del vigente (:71-72, :80). Todo retrain_for es una transacción (transaction.atomic, retraining.py:45) con la organización bloqueada (select_for_update, :48): Fijando inquilino es ese bloqueo más tenant_context (:49), Validando es data_status(), Escribiendo es el INSERT del candidate (training.py:211), la comparación (:90-91) y promote(), que retira la vigente y activa la nueva (training.py:231-236; índice único parcial de una sola active, noshow/models.py:90-92); Confirmada es el COMMIT. Desde el COMMIT la vista de fichas y el refuerzo de US-36 sólo leen predicciones de la versión active (noshow/views.py:133; appointments/reminders.py:84): las de la versión retirada dejan de verse hasta que score_noshow recalifica, a lo sumo 60 min después (score_noshow.py:36).'
    lineas = @(
      @{ n='Comando retrain_noshow'
         estados=@('Durmiendo', 'Dando la vuelta')
         marcas=@( @{ t=0;  e='Durmiendo';       ev='time.sleep()' },
                   @{ t=14; e='Dando la vuelta'; ev='run()'; r='1440 min' },
                   @{ t=56; e='Durmiendo';       ev='resultados' } ) },
      @{ n='Transacción de la organización'
         estados=@('Inactiva', 'Fijando inquilino', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=18; e='Fijando inquilino'; ev='FOR UPDATE org' },
                   @{ t=24; e='Validando';         ev='data_status()'; r='>= 20 nuevos' },
                   @{ t=30; e='Escribiendo';       ev='INSERT candidate' },
                   @{ t=50; e='Confirmada';        ev='COMMIT' },
                   @{ t=54; e='Inactiva' } ) },
      @{ n='Versión nueva'
         estados=@('Sin crear', 'candidate', 'active')
         marcas=@( @{ t=0;  e='Sin crear' },
                   @{ t=30; e='candidate'; ev='train_for()' },
                   @{ t=46; e='active';    ev='promote()'; r='Brier menor' } ) },
      @{ n='Versión vigente anterior'
         estados=@('active', 'retired')
         marcas=@( @{ t=0;  e='active' },
                   @{ t=46; e='retired'; ev='promote()' } ) },
      @{ n='Predicciones de las fichas'
         estados=@('De la anterior', 'Sin mostrar', 'De la nueva')
         marcas=@( @{ t=0;  e='De la anterior' },
                   @{ t=50; e='Sin mostrar'; ev='COMMIT' },
                   @{ t=74; e='De la nueva'; ev='score_for()'; r='<= 60 min' } ) }
    )
  }
}


# =========================================================================
# Datos de ESTADO y TIEMPO del Sprint 4: CU40, CU41, CU42 y CU43 (IA).
# Leídos del código el 22/11/26 (working tree en main, 2349f66).
# Mismo formato que las claves 'estado' y 'tiempo' de ea-sprint3-dinamica.ps1.
# =========================================================================

# -------------------------------------------------------------------------
# CU40 (US-39) Generación de Resumen de Consulta mediante IA
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU40'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Médico';                   col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';               col=1; f=2 },
      @{ k='capf';   n='Confirmar firma';                     col=2; f=0.5 },
      @{ k='reint';  n='Pedir reintento del resumen';         col=2; f=3.2 },
      @{ k='valg';   n='Validar firma';                       col=3; f=0 },
      @{ k='vivo';   n='Verificar resumen vivo y proveedor';  col=3; f=1.6 },
      @{ k='valr';   n='Validar atención propia y firmada';   col=3; f=3.2 },
      @{ k='llm';    n='Esperar respuesta del modelo';        col=3; f=4.8 },
      @{ k='ok';     n='Transacción completada';              col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 },
      @{ k='aviso';  n='Informar resumen no generado';        col=4; f=4.3 },
      @{ k='error';  n='Informar error';                      col=4; f=6 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.encounter.create | ai.text.review] {views.py:168}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='capf';   r='[firmar] {POST /encounters/<id>/sign/}' },
      @{ de='menu';  a='reint';  r='[reintentar] {POST /ai/encounters/<id>/summary/}' },
      @{ de='capf';  a='valg';   r='firmar() {Atencion.tsx:100, :105}' },
      @{ de='valg';  a='vivo';   r='[propia, draft, motivo y diagnóstico] / sign(), status=signed {services.py:166}' },
      @{ de='valg';  a='error';  r='[ajena 404, ya signed 409 o faltan campos 400] {views.py:62, services.py:156, :164}' },
      @{ de='reint'; a='valr';   r='reintentarResumen() {TextosPorValidar.tsx:140}' },
      @{ de='valr';  a='vivo';   r='[propia y signed] {ai/views.py:140-142}' },
      @{ de='valr';  a='error';  r='[ajena 404 o atención no firmada 409] {ai/views.py:141, :143}' },
      @{ de='vivo';  a='ok';     r='[ya hay uno draft o approved] / exists {consultation_summary.py:203-208}' },
      @{ de='vivo';  a='llm';    r='[sin vivo y con Gemini] / _call_model(context()) {consultation_summary.py:213}' },
      @{ de='vivo';  a='aviso';  r='[sin proveedor] / unavailable {consultation_summary.py:209-210}' },
      @{ de='llm';   a='ok';     r='[texto] / create_draft(): nace draft; IntegrityError = exists {:224-229}' },
      @{ de='llm';   a='aviso';  r='[excepción, 20 s o vacío] / failed, se puede reintentar {:214-220}' },
      @{ de='aviso'; a='fin';    r='/ la firma queda igual {views.py:192}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el médico firma y la misma petición espera a Gemini para dejar el resumen en draft; el médico lo aprueba más tarde'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. La firma y el resumen van en UNA transacción: TenantMiddleware abre transaction.atomic() por petición (tenancy/middleware.py:39-41; ATOMIC_REQUESTS=False, config/settings.py:176), así el UPDATE de sign() (encounters/services.py:166-169) y el select_for_update de la ficha (:173) siguen abiertos mientras se espera al modelo (encounters/views.py:177-178). 20 s = TIMEOUT_MS (ai/consultation_summary.py:46, HttpOptions en :238); 600 tokens (:44). 60 s = --timeout de gunicorn (scripts/start.sh:69): si corta el worker, vuelve atrás todo, firma incluida. El texto nace draft (ai/models.py:73-75, ai/services.py:71) y no tiene plazo para validarse; uq_ai_text_summary_vivo (ai/models.py:131-135) deja uno vivo por atención. El paciente lo ve recién approved (approved_for, ai/services.py:216-226).'
    lineas = @(
      @{ n='Transacción de la firma'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Esperando IA', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=4;  e='Autenticando'; ev='POST /sign/' },
                   @{ t=8;  e='Validando';    ev='sign()' },
                   @{ t=12; e='Escribiendo';  ev='UPDATE signed' },
                   @{ t=16; e='Esperando IA'; ev='_call_model()'; r='20 s máx' },
                   @{ t=40; e='Escribiendo';  ev='INSERT draft' },
                   @{ t=44; e='Confirmada';   ev='COMMIT' },
                   @{ t=48; e='Inactiva';     ev='200 + resumen' } ) },
      @{ n='Llamada a Gemini'
         estados=@('Inactiva', 'Esperando', 'Respondió')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=16; e='Esperando'; ev='generate_content' },
                   @{ t=38; e='Respondió'; ev='response.text'; r='20 s' },
                   @{ t=42; e='Inactiva' } ) },
      @{ n='Worker de gunicorn'
         estados=@('Libre', 'Atendiendo')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=4;  e='Atendiendo'; ev='petición'; r='60 s máx' },
                   @{ t=48; e='Libre';      ev='respuesta' } ) },
      @{ n='Atención'
         estados=@('draft', 'signed')
         marcas=@( @{ t=0;  e='draft' },
                   @{ t=12; e='signed'; ev='signed_at = now()'; r='sin COMMIT' } ) },
      @{ n='Resumen (texto IA)'
         estados=@('no existe', 'draft', 'approved')
         marcas=@( @{ t=0;  e='no existe' },
                   @{ t=40; e='draft';    ev='create_draft()' },
                   @{ t=76; e='approved'; ev='approve()'; r='sin plazo' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU41 (US-40) Generación de Indicaciones de Preparación
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU41'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Médico';                   col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';               col=1; f=2 },
      @{ k='capf';   n='Confirmar firma';                     col=2; f=0.5 },
      @{ k='reint';  n='Pedir preparación de una orden';      col=2; f=3.6 },
      @{ k='valg';   n='Validar firma';                       col=3; f=0 },
      @{ k='sig';    n='Tomar siguiente orden';               col=3; f=1.2 },
      @{ k='fte';    n='Buscar fuente: nombre o corpus';      col=3; f=2.4 },
      @{ k='red';    n='Redactar: Gemini o catálogo';         col=3; f=3.6 },
      @{ k='valr';   n='Validar orden propia y firmada';      col=3; f=4.8 },
      @{ k='ok';     n='Transacción completada';              col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 },
      @{ k='error';  n='Informar error';                      col=4; f=5.5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.encounter.create | ai.text.review] {views.py:168}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='capf';   r='[firmar] {POST /encounters/<id>/sign/}' },
      @{ de='menu';  a='reint';  r='[reintentar] {POST /ai/orders/<id>/preparation/}' },
      @{ de='capf';  a='valg';   r='firmar() {Atencion.tsx:100}' },
      @{ de='valg';  a='sig';    r='[propia, draft y completa] / sign() y resumen CU40 {views.py:172-185}' },
      @{ de='valg';  a='error';  r='[ajena 404, ya signed 409 o faltan campos 400] {services.py:156, :164}' },
      @{ de='sig';   a='fte';    r='[orden sin preparación viva] {study_preparation.py:260-267}' },
      @{ de='sig';   a='ok';     r='[no quedan órdenes] / 200 con study_preparations {views.py:186-193}' },
      @{ de='fte';   a='red';    r='[servicio activo con preparation] {find_by_name :121, find_in_corpus :141}' },
      @{ de='fte';   a='sig';    r='[viva: exists | sin fuente: no_source] / siguiente {:264-269}' },
      @{ de='red';   a='sig';    r='[Gemini o, si falla, catálogo] / create_draft() nace draft {:271-289}' },
      @{ de='reint'; a='valr';   r='POST /ai/orders/<id>/preparation/ {ai/views.py:162}' },
      @{ de='valr';  a='fte';    r='[propia y signed] / generate(orden) {ai/views.py:172-176}' },
      @{ de='valr';  a='error';  r='[ajena 404 o atención no firmada 409] {ai/views.py:172-175}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'firmar una atención con dos órdenes: cada una puede esperar a Gemini dentro de la misma petición que la firma'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. generate_for_encounter recorre las órdenes en serie (ai/study_preparation.py:292-301) después del resumen de CU40 (encounters/views.py:177-185), todo en la transacción que abre TenantMiddleware (tenancy/middleware.py:39-41). 20 s = TIMEOUT_MS por llamada (study_preparation.py:46, HttpOptions :310), 400 tokens (:45); la búsqueda en el corpus llama a embed_query (assistant/retrieval.py:134) sin timeout propio. Sin proveedor o sin respuesta queda el texto del catálogo (generated_by = catalogo, :280-281). 60 s = --timeout de gunicorn (scripts/start.sh:69): resumen + órdenes deben caber ahí o la firma vuelve atrás. Cada preparación nace draft; uq_ai_text_preparation_viva (ai/models.py:136-140) deja una viva por orden.'
    lineas = @(
      @{ n='Transacción de la firma'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Esperando IA', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=3;  e='Autenticando'; ev='POST /sign/' },
                   @{ t=6;  e='Validando';    ev='sign()' },
                   @{ t=9;  e='Escribiendo';  ev='UPDATE signed' },
                   @{ t=12; e='Esperando IA'; ev='resumen y órdenes'; r='20 s c/u' },
                   @{ t=62; e='Escribiendo';  ev='INSERT draft' },
                   @{ t=66; e='Confirmada';   ev='COMMIT' },
                   @{ t=70; e='Inactiva';     ev='200 + preparaciones' } ) },
      @{ n='Preparación orden 1'
         estados=@('no existe', 'buscando fuente', 'redactando', 'draft')
         marcas=@( @{ t=0;  e='no existe' },
                   @{ t=28; e='buscando fuente'; ev='find_by_name()' },
                   @{ t=31; e='redactando';      ev='_call_model()'; r='20 s' },
                   @{ t=44; e='draft';           ev='create_draft()' } ) },
      @{ n='Preparación orden 2'
         estados=@('no existe', 'buscando fuente', 'redactando', 'draft')
         marcas=@( @{ t=0;  e='no existe' },
                   @{ t=46; e='buscando fuente'; ev='embed_query()'; r='sin timeout' },
                   @{ t=50; e='redactando';      ev='_call_model()'; r='20 s' },
                   @{ t=62; e='draft';           ev='catálogo o IA' } ) },
      @{ n='Worker de gunicorn'
         estados=@('Libre', 'Atendiendo')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=3;  e='Atendiendo'; ev='petición'; r='60 s máx' },
                   @{ t=70; e='Libre';      ev='respuesta' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU42 (US-41) Generación de Resumen de Historia Clínica
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU42'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Médico';                       col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';                   col=1; f=2 },
      @{ k='ped';    n='Pedir resumen del historial';             col=2; f=1.5 },
      @{ k='valv';   n='Validar vínculo de atención';             col=3; f=0 },
      @{ k='car';    n='Cargar 10 atenciones firmadas y alergias'; col=3; f=1.4 },
      @{ k='llm';    n='Esperar respuesta del modelo';            col=3; f=2.8 },
      @{ k='ver';    n='Verificar citas [A1..An]';                col=3; f=4.2 },
      @{ k='plant';  n='Copiar diagnósticos (plantilla)';         col=3; f=5.6 },
      @{ k='ok';     n='Transacción completada';                  col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 },
      @{ k='error';  n='Informar error';                          col=4; f=5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.history.read] {CanReadHistory, history_views.py:101}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='ped';    r='[generar resumen] {ResumenHistorial.tsx:43}' },
      @{ de='ped';   a='valv';   r='pedir() / GET /history/<paciente>/summary/ {ResumenHistorial.tsx:27}' },
      @{ de='valv';  a='car';    r='[history_scope = professional] {history_views.py:109; services.py:243}' },
      @{ de='valv';  a='error';  r='[sin ficha con el paciente, own o ajeno] / 404 {history_views.py:109-110}' },
      @{ de='car';   a='ok';     r='[sin atenciones signed] / generated_by = sin_datos {summary.py:211-214}' },
      @{ de='car';   a='llm';    r='[proveedor gemini y clave] / _call_model(_contexto()) {summary.py:217-219}' },
      @{ de='car';   a='plant';  r='[sin proveedor] {summary.py:217, :229}' },
      @{ de='llm';   a='ver';    r='[response.text] / verificar(texto, total) {summary.py:219, :160}' },
      @{ de='llm';   a='plant';  r='[cuota, red o error] {summary.py:221-224}' },
      @{ de='ver';   a='ok';     r='[quedan oraciones citadas] / generated_by = gemini, RECORD_READ {summary.py:226}' },
      @{ de='ver';   a='plant';  r='[ninguna oración con cita válida] {summary.py:176-178}' },
      @{ de='plant'; a='ok';     r='/ generated_by = plantilla, RECORD_READ {summary.py:186, :230; views:113}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el médico pide el resumen antes de la consulta y espera a Gemini con el panel en «Generando…»'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. El resumen se pide con un botón, no al abrir la página (frontend/src/paginas/ResumenHistorial.tsx:18-19, «Generando…» en :44). Entran las 10 atenciones firmadas más recientes (MAX_ENCOUNTERS, encounters/summary.py:51, orden por appointment.starts_at en :203). La llamada a Gemini (temperature 0.1, 500 tokens, summary.py:235-250) NO tiene timeout propio, a diferencia de CU40 y CU41: sólo la corta el --timeout 60 de gunicorn (scripts/start.sh:69). Toda excepción degrada a la plantilla (summary.py:221-231). No se guarda en ai_generated_texts: lo único que se escribe es el asiento RECORD_READ (encounters/history_views.py:113-118), dentro de la transacción de TenantMiddleware (tenancy/middleware.py:39-41).'
    lineas = @(
      @{ n='Transacción del resumen'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Esperando IA', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Autenticando'; ev='GET /summary/' },
                   @{ t=11; e='Validando';    ev='history_scope()' },
                   @{ t=18; e='Esperando IA'; ev='_call_model()'; r='sin timeout' },
                   @{ t=56; e='Validando';    ev='verificar()' },
                   @{ t=62; e='Escribiendo';  ev='RECORD_READ' },
                   @{ t=66; e='Confirmada';   ev='COMMIT' },
                   @{ t=70; e='Inactiva';     ev='200' } ) },
      @{ n='Llamada a Gemini'
         estados=@('Inactiva', 'Esperando', 'Respondió')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=18; e='Esperando'; ev='generate_content' },
                   @{ t=54; e='Respondió'; ev='response.text' },
                   @{ t=58; e='Inactiva' } ) },
      @{ n='Worker de gunicorn'
         estados=@('Libre', 'Atendiendo')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=6;  e='Atendiendo'; ev='petición'; r='60 s máx' },
                   @{ t=70; e='Libre';      ev='respuesta' } ) },
      @{ n='Panel del resumen'
         estados=@('Vacío', 'Generando', 'Mostrando')
         marcas=@( @{ t=0;  e='Vacío' },
                   @{ t=4;  e='Generando'; ev='Generar resumen' },
                   @{ t=72; e='Mostrando'; ev='setDatos()' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU43 (US-42) Validación de Contenido Generado por IA
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU43'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Médico';                 col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';             col=1; f=2 },
      @{ k='listar'; n='Listar pendientes (draft)';         col=2; f=0 },
      @{ k='corr';   n='Capturar corrección';               col=2; f=1.6 },
      @{ k='apr';    n='Confirmar aprobación';              col=2; f=3.2 },
      @{ k='desc';   n='Confirmar descarte';                col=2; f=4.8 },
      @{ k='valc';   n='Validar corrección';                col=3; f=1.6 },
      @{ k='vala';   n='Validar aprobación';                col=3; f=3.2 },
      @{ k='vald';   n='Validar descarte';                  col=3; f=4.8 },
      @{ k='ok';     n='Transacción completada';            col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 },
      @{ k='error';  n='Informar error';                    col=4; f=5.5 }
    )
    transiciones = @(
      @{ de='ini';    a='aut' },
      @{ de='aut';    a='menu';   r='[token y ai.text.review] {CanReviewTexts, ai/views.py:45}' },
      @{ de='aut';    a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';   a='listar'; r='[abrir bandeja] {GET /ai/texts/?status=draft}' },
      @{ de='menu';   a='corr';   r='[guardar sin aprobar] {PATCH /ai/texts/<id>/}' },
      @{ de='menu';   a='apr';    r='[aprobar] {POST /ai/texts/<id>/approve/}' },
      @{ de='menu';   a='desc';   r='[descartar] {POST /ai/texts/<id>/discard/}' },
      @{ de='listar'; a='ok';     r='[sus textos draft] / inbox_for(), ORDER BY created_at {ai/views.py:71-80}' },
      @{ de='corr';   a='valc';   r='hacer(guardar) {TextosPorValidar.tsx:59}' },
      @{ de='valc';   a='ok';     r='[propio, draft, 1..4000 car.] / edit(), sigue draft {services.py:124-129}' },
      @{ de='valc';   a='error';  r='[ajeno 404, no draft 409, vacío o > 4000 400] {views.py:56, services.py:105}' },
      @{ de='apr';    a='vala';   r='hacer(aprobar) {TextosPorValidar.tsx:61}' },
      @{ de='vala';   a='ok';     r='[propio y draft] / status = approved, reviewed_at {services.py:140-148}' },
      @{ de='vala';   a='error';  r='[ajeno 404 o approved | discarded 409] {views.py:56, services.py:119-120}' },
      @{ de='desc';   a='vald';   r='hacer(descartar) {TextosPorValidar.tsx:64}' },
      @{ de='vald';   a='ok';     r='[propio y draft] / status = discarded, AI_TEXT_DISCARD {services.py:155-158}' },
      @{ de='vald';   a='error';  r='[ajeno 404 o ya decidido 409] {views.py:56, services.py:119-120}' },
      @{ de='error';  a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';     a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el médico aprueba un borrador en una pestaña y, a la vez, lo descarta en otra: la segunda espera el bloqueo y recibe 409'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. _lock_draft toma la fila con select_for_update (ai/services.py:112-121): la segunda transacción espera a que la primera haga COMMIT, relee status y, como ya no es draft, lanza Conflict (409, ai/services.py:39-42). Desde approved o discarded la fila es inmutable: trg_ai_generated_texts_inmutable rechaza todo UPDATE o DELETE (ai/migrations/0002_rls_e_inmutabilidad.py:81-95), y ck_ai_text_reviewed exige reviewed_by y reviewed_at (ai/models.py:120-124). El borrador no vence: espera en la bandeja, del más viejo al más nuevo (ai/views.py:78-80). Cada petición es una transacción de TenantMiddleware (tenancy/middleware.py:39-41); el acceso del médico dura 30 min (ACCESS_TOKEN_LIFETIME, config/settings.py:387).'
    lineas = @(
      @{ n='Transacción pestaña A (aprobar)'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=8;  e='Autenticando'; ev='POST /approve/' },
                   @{ t=14; e='Validando';    ev='_lock_draft()'; r='FOR UPDATE' },
                   @{ t=22; e='Escribiendo';  ev='UPDATE approved' },
                   @{ t=34; e='Confirmada';   ev='COMMIT' },
                   @{ t=40; e='Inactiva';     ev='200' } ) },
      @{ n='Transacción pestaña B (descartar)'
         estados=@('Inactiva', 'Autenticando', 'Esperando bloqueo', 'Validando', 'Rechazada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=16; e='Autenticando';      ev='POST /discard/' },
                   @{ t=20; e='Esperando bloqueo'; ev='select_for_update'; r='FOR UPDATE' },
                   @{ t=34; e='Validando';         ev='status <> draft' },
                   @{ t=40; e='Rechazada';         ev='Conflict()'; r='409' },
                   @{ t=46; e='Inactiva';          ev='409 al médico' } ) },
      @{ n='Fila de ai_generated_texts'
         estados=@('Libre', 'Bloqueada por A', 'Bloqueada por B')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=14; e='Bloqueada por A'; ev='lock de A' },
                   @{ t=34; e='Bloqueada por B'; ev='COMMIT de A' },
                   @{ t=40; e='Libre';     ev='ROLLBACK B' } ) },
      @{ n='Texto IA'
         estados=@('draft', 'approved')
         marcas=@( @{ t=0;  e='draft' },
                   @{ t=34; e='approved'; ev='reviewed_at = now()'; r='inmutable' } ) }
    )
  }
}


# =========================================================================
# Sprint 4 - Datos de ESTADO y TIEMPO (grupo C): CU47, CU48, CU49, CU51.
# Mismo formato que ea-sprint3-dinamica.ps1 (claves 'estado' y 'tiempo').
# Anclajes verificados contra el working tree de main (22/11/26).
# =========================================================================

# CU47 (US-46) Consulta de Transacciones por Voz - móvil, paciente
$DINAMICA_SPRINT4['CU47'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';             col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';           col=1; f=2 },
      @{ k='dic';    n='Dictar o escribir la frase';      col=2; f=0 },
      @{ k='pedl';   n='Pedir la lista';                  col=2; f=2.5 },
      @{ k='pedp';   n='Pedir el PDF con los QR';         col=2; f=4.5 },
      @{ k='trad';   n='Traducir con Gemini';             col=3; f=0 },
      @{ k='reglas'; n='Leer con reglas fijas';           col=3; f=1.3 },
      @{ k='valc';   n='Validar consulta y alcance';      col=3; f=3.5 },
      @{ k='error';  n='Informar error';                  col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';          col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';    a='aut' },
      @{ de='aut';    a='menu';   r='[token y perfil de paciente activo] {IsPatientProfile, permissions.py:28}' },
      @{ de='aut';    a='fin403'; r='[sin token o sin perfil] {401 | 403 sin_perfil_de_paciente, permissions.py:31}' },
      @{ de='menu';   a='dic';    r='[dictar | escribir] / listen(es_BO) en el celular {voice_input.dart:86}' },
      @{ de='menu';   a='pedp';   r='[bajar PDF] {GET /payments/mine/receipts/?formato=pdf, views_mine.py:104}' },
      @{ de='dic';    a='trad';   r='POST interpret [texto <= 300 y proveedor_disponible()] / ask_model() {voice.py:176}' },
      @{ de='dic';    a='reglas'; r='[sin proveedor] / (None, plantilla) {voice.py:185-186}' },
      @{ de='dic';    a='error';  r='[vacía, otra persona o no soportado] / _nada(motivos) {mine_voice.py:787, :799}' },
      @{ de='trad';   a='reglas'; r='[error o respuesta no JSON] / (None, plantilla) {voice.py:189-191}' },
      @{ de='trad';   a='pedl';   r='[sanear_consulta() resuelve] / 200(propuesta) {mine_voice.py:809, :820}' },
      @{ de='reglas'; a='pedl';   r='[analizar() resuelve] / 200(propuesta) {mine_voice.py:814, :820}' },
      @{ de='reglas'; a='error';  r='[consulta None] / _nada(unresolved), understood=false {mine_voice.py:819}' },
      @{ de='pedl';   a='valc';   r='GET /payments/mine/receipts/ / parse_consulta() {views_mine.py:85; mine.py:102}' },
      @{ de='pedp';   a='valc';   r='parse_consulta(), formato pdf {views_mine.py:85, :89}' },
      @{ de='valc';   a='ok';     r='[válida] / listar() pagos succeeded | fichas, issue_code() {mine.py:210, :277}' },
      @{ de='valc';   a='error';  r='[cantidad fuera de 1..50 o filtro inválido] {400 consulta_invalida, views_mine.py:92}' },
      @{ de='error';  a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';     a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el paciente dicta «mis facturas de los últimos 3 meses»: el período se fija contra hoy y el celular espera cada respuesta'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. El dictado ocurre en el celular (speech_to_text en modo dictation, mobile/lib/features/reporting/voice_input.dart:86-92) y sólo llega texto. «Los últimos N meses» es un período corrido desde la misma fecha de hace N meses hasta hoy (payments/mine_voice.py:422-437), con hoy = timezone.localdate() (mine_voice.py:789) y como mucho MESES_MAXIMOS = 36 (:69). La llamada a Gemini no tiene plazo propio (reporting/voice.py:203-220, sin timeout): si falla, ask_model degrada a la plantilla (voice.py:189-191). El celular corta cada petición a los 20 s (Config.timeout, mobile/lib/core/config.dart:40; client.dart:184). La lista trae como mucho 20 sin cantidad o 50 agrupada (payments/mine.py:60, :87; CANTIDAD_MAXIMA mine_voice.py:59) y cada comprobante con su código firmado (appointments/receipts.py:53).'
    lineas = @(
      @{ n='Dictado en el celular'
         estados=@('Inactivo', 'Escuchando', 'Texto final')
         marcas=@( @{ t=0;  e='Inactivo' },
                   @{ t=4;  e='Escuchando';  ev='listen(es_BO)' },
                   @{ t=14; e='Texto final'; ev='finalResult' },
                   @{ t=20; e='Inactivo';    ev='_buscar(texto)' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Leyendo', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=18; e='Autenticando'; ev='POST interpret' },
                   @{ t=22; e='Validando';    ev='interpretar()' },
                   @{ t=38; e='Escribiendo';  ev='bitácora' },
                   @{ t=41; e='Confirmada';   ev='COMMIT' },
                   @{ t=44; e='Inactiva';     ev='200 propuesta' },
                   @{ t=52; e='Autenticando'; ev='GET receipts' },
                   @{ t=56; e='Validando';    ev='parse_consulta()' },
                   @{ t=60; e='Leyendo';      ev='listar(), QR' },
                   @{ t=72; e='Confirmada';   ev='200 items' },
                   @{ t=76; e='Inactiva' } ) },
      @{ n='Gemini'
         estados=@('En espera', 'Traduciendo', 'Respondió')
         marcas=@( @{ t=0;  e='En espera' },
                   @{ t=24; e='Traduciendo'; ev='ask_model()'; r='sin timeout' },
                   @{ t=34; e='Respondió';   ev='JSON' },
                   @{ t=40; e='En espera' } ) },
      @{ n='Período de la consulta'
         estados=@('Sin fijar', 'Hoy - 3 meses')
         marcas=@( @{ t=0;  e='Sin fijar' },
                   @{ t=36; e='Hoy - 3 meses'; ev='sanear_consulta()'; r='localdate' } ) },
      @{ n='Petición del celular'
         estados=@('Sin petición', 'Esperando', 'Respondida')
         marcas=@( @{ t=0;  e='Sin petición' },
                   @{ t=18; e='Esperando';  ev='send()' },
                   @{ t=44; e='Respondida'; ev='200'; r='<= 20 s' },
                   @{ t=52; e='Esperando';  ev='send()' },
                   @{ t=74; e='Respondida'; ev='200'; r='<= 20 s' } ) }
    )
  }
}

# CU48 (US-47) Chat con el Médico Tratante - paciente en el móvil, médico en la web
$DINAMICA_SPRINT4['CU48'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente o Médico';    col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';           col=1; f=2 },
      @{ k='abr';    n='Abrir la conversación';           col=2; f=0 },
      @{ k='esc';    n='Escribir mensaje';                col=2; f=1.6 },
      @{ k='cer';    n='Cerrar la conversación';          col=2; f=3.2 },
      @{ k='valv';   n='Verificar atención y ventana';    col=3; f=0 },
      @{ k='valm';   n='Validar mensaje y ventana';       col=3; f=1.6 },
      @{ k='valc';   n='Verificar que siga abierta';      col=3; f=3.2 },
      @{ k='push';   n='Avisar al paciente por FCM';      col=3; f=4.8 },
      @{ k='urg';    n='Mostrar derivación a emergencias'; col=4; f=0 },
      @{ k='error';  n='Informar error';                  col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';          col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.chat] {CanChat, views.py:53}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='abr';    r='[abrir] {GET /messaging/encounters/<id>/chat/, views.py:130}' },
      @{ de='menu';  a='esc';    r='[enviar] {POST .../chat/messages/, views.py:146}' },
      @{ de='menu';  a='cer';    r='[cerrar] {POST .../chat/close/, views.py:165}' },
      @{ de='abr';   a='valv';   r='encounter_for(), side_of(), thread_of() {services.py:86, :68, :114}' },
      @{ de='valv';  a='ok';     r='[signed y lado] / can_write, closed_reason null|closed|expired {views.py:94-99}' },
      @{ de='valv';  a='error';  r='[ajena, no signed o sin lado] {404 views.py:67}' },
      @{ de='esc';   a='valm';   r='send(user, encounter, side, body) {services.py:145}' },
      @{ de='valm';  a='urg';    r='[PATIENT y triage.check().is_emergency] / flagged_emergency=true {services.py:151}' },
      @{ de='valm';  a='ok';     r='[PATIENT, sin urgencia, can_write] / INSERT, last_message_at {services.py:156, :170}' },
      @{ de='valm';  a='push';   r='[PRACTITIONER y can_write] / INSERT, on_commit(notify_patient) {services.py:174}' },
      @{ de='valm';  a='error';  r='[vacío, > 2000, closed_at o now >= signed_at + 15 d] {400 :138, 409 chat_closed :155}' },
      @{ de='urg';   a='ok';     r='/ 201(message, emergency) {views.py:157-159}' },
      @{ de='push';  a='ok';     r='/ send_to_user() paciente o titular, nunca propaga {services.py:256; push.py:119}' },
      @{ de='cer';   a='valc';   r='[lado PRACTITIONER] / close(user, encounter) {views.py:167; services.py:185}' },
      @{ de='valc';  a='ok';     r='[closed_at null] / closed_at = now(), closed_by {services.py:191-193}' },
      @{ de='valc';  a='error';  r='[paciente o ya cerrada] {404 views.py:168, 409 ChatClosed services.py:190}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el médico responde al tercer día y el paciente manda un mensaje tardío cuando la ventana de 15 días ya venció'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no días medidos. La ventana es de 15 días desde la firma: ENCOUNTER_CHAT_DAYS con 15 por omisión (messaging/services.py:61, getattr; no está en config/settings.py), closes_at = signed_at + 15 días (services.py:103-104) y can_write = now < closes_at y sin closed_at (services.py:107-111). Un POST después de closes_at responde 409 chat_closed bajo select_for_update (services.py:153-155) y la conversación queda en sólo lectura con closed_reason = expired (messaging/views.py:96-99). La respuesta del médico avisa al paciente recién después del COMMIT (transaction.on_commit, services.py:174) y cada envío a FCM espera como mucho 10 s (TIMEOUT_SECONDS, notifications/push.py:36, :142); un FCM caído no deshace el mensaje (services.py:236). No hay push hacia el médico: la web sondea cada 10 s (frontend/src/paginas/ChatAtencion.tsx:26) y la bandeja cada 30 s (:209); el celular sondea cada 10 s (mobile/lib/features/chat/chat_screen.dart:49, :82).'
    lineas = @(
      @{ n='Ventana de la conversación'
         estados=@('abierta', 'closed', 'expired')
         marcas=@( @{ t=0;  e='abierta'; ev='signed_at' },
                   @{ t=64; e='expired'; ev='closes_at'; r='15 días' } ) },
      @{ n='Transacción del chat'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=12; e='Autenticando'; ev='POST del médico' },
                   @{ t=16; e='Validando';    ev='can_write()' },
                   @{ t=20; e='Escribiendo';  ev='INSERT' },
                   @{ t=24; e='Confirmada';   ev='COMMIT' },
                   @{ t=28; e='Inactiva';     ev='201' },
                   @{ t=68; e='Autenticando'; ev='POST tardío' },
                   @{ t=72; e='Validando';    ev='can_write()' },
                   @{ t=76; e='Inactiva';     ev='409 chat_closed' } ) },
      @{ n='Aviso push al paciente'
         estados=@('Sin aviso', 'Enviando', 'Entregado')
         marcas=@( @{ t=0;  e='Sin aviso' },
                   @{ t=25; e='Enviando';  ev='on_commit' },
                   @{ t=32; e='Entregado'; ev='FCM 200'; r='<= 10 s' } ) },
      @{ n='Pantalla del paciente'
         estados=@('Esperando', 'Leyendo', 'Sólo lectura')
         marcas=@( @{ t=0;  e='Esperando' },
                   @{ t=36; e='Leyendo';      ev='GET (sondeo)'; r='10 s' },
                   @{ t=40; e='Esperando';    ev='mark_read()' },
                   @{ t=80; e='Sólo lectura'; ev='expired'; r='10 s' } ) }
    )
  }
}

# CU49 (US-48) Calificación de la Atención - paciente (móvil y web) y administrador (web)
$DINAMICA_SPRINT4['CU49'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente o Administrador'; col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';           col=1; f=2 },
      @{ k='cal';    n='Capturar estrellas y comentario'; col=2; f=0 },
      @{ k='cor';    n='Cambiar la calificación';         col=2; f=1.6 },
      @{ k='sat';    n='Pedir satisfacción del período';  col=2; f=3.2 },
      @{ k='valc';   n='Validar atención y datos';        col=3; f=0 },
      @{ k='valv';   n='Verificar los 7 días';            col=3; f=1.6 },
      @{ k='valr';   n='Validar rango y sede';            col=3; f=3.2 },
      @{ k='error';  n='Informar error';                  col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';          col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.history.read | reporting.kpi.read] {rating_views.py:70; kpi_views.py:96}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='cal';    r='[calificar] {POST /encounters/<id>/rating/, rating_views.py:77}' },
      @{ de='menu';  a='cor';    r='[cambiar y editable] {PATCH /encounters/<id>/rating/, rating_views.py:84}' },
      @{ de='menu';  a='sat';    r='[ver satisfacción] {GET /reporting/satisfaction/, kpi_views.py:98}' },
      @{ de='cal';   a='valc';   r='_enviar() {rating_card.dart:59}' },
      @{ de='valc';  a='ok';     r='[signed, OWN, 1..5 y <= 500] / rate(): INSERT encounter_ratings {ratings.py:59, :65}' },
      @{ de='valc';  a='error';  r='[ajena o no signed, datos inválidos o ya calificada] {404 :65, 400 :80, 409 ratings.py:77}' },
      @{ de='cor';   a='valv';   r='correct(encuentro, stars, comment) {rating_views.py:88; ratings.py:81}' },
      @{ de='valv';  a='ok';     r='[now <= created_at + 7 días] / UPDATE stars, comment {ratings.py:41, :96}' },
      @{ de='valv';  a='error';  r='[pasaron 7 días o sin calificar] {409 rating_locked ratings.py:89, trigger 0008:99}' },
      @{ de='sat';   a='valr';   r='filtros(request, organizacion) {kpi_views.py:42, :104}' },
      @{ de='valr';  a='ok';     r='[rango <= 366 días] / for_organization(): Avg, Count sin paciente {ratings.py:143}' },
      @{ de='valr';  a='error';  r='[fecha inválida, invertida o > 366 días] {400 kpi_views.py:56-61}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el paciente califica, corrige al quinto día y al octavo el segundo cambio rebota'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no días medidos. Una calificación por atención (OneToOne; el segundo POST da 409 already_rated, encounters/ratings.py:75-78). Se corrige durante EDITABLE_DAYS = 7 (encounters/models.py:276) contados desde created_at, no desde la firma: editable_until = created_at + 7 días (models.py:331-333), editable() = now <= editable_until (ratings.py:41-42), y correct() lo revisa bajo select_for_update (ratings.py:84-93). Corregir no mueve created_at: el plazo no se reinicia. La base lo repite con el trigger encounter_ratings_guarda: now() > created_at + interval ''7 days'' rechaza el UPDATE y el DELETE siempre (encounters/migrations/0008_us48_rls_e_inmutabilidad.py:71-108). La tarjeta del móvil muestra «Cambiar (hasta el ...)» sólo si editable (mobile/lib/features/clinical_record/rating_card.dart:121-139).'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=4;  e='Autenticando'; ev='POST rating' },
                   @{ t=8;  e='Validando';    ev='is_valid()' },
                   @{ t=12; e='Escribiendo';  ev='INSERT' },
                   @{ t=16; e='Confirmada';   ev='COMMIT' },
                   @{ t=20; e='Inactiva';     ev='201' },
                   @{ t=40; e='Autenticando'; ev='PATCH' },
                   @{ t=44; e='Validando';    ev='editable()' },
                   @{ t=48; e='Escribiendo';  ev='UPDATE' },
                   @{ t=52; e='Confirmada';   ev='COMMIT' },
                   @{ t=56; e='Inactiva';     ev='200' },
                   @{ t=72; e='Autenticando'; ev='PATCH' },
                   @{ t=76; e='Validando';    ev='editable()' },
                   @{ t=80; e='Inactiva';     ev='409 rating_locked' } ) },
      @{ n='Calificación'
         estados=@('Sin calificar', 'Editable', 'Fija')
         marcas=@( @{ t=0;  e='Sin calificar' },
                   @{ t=16; e='Editable'; ev='created_at' },
                   @{ t=64; e='Fija';     ev='editable_until'; r='7 días' } ) },
      @{ n='Trigger de la base'
         estados=@('Admite UPDATE', 'Rechaza UPDATE')
         marcas=@( @{ t=0;  e='Admite UPDATE' },
                   @{ t=64; e='Rechaza UPDATE'; ev='now() > +7 días'; r='7 days' } ) },
      @{ n='Tarjeta del móvil'
         estados=@('Formulario', 'Con Cambiar', 'Sin Cambiar')
         marcas=@( @{ t=0;  e='Formulario' },
                   @{ t=20; e='Con Cambiar'; ev='201' },
                   @{ t=82; e='Sin Cambiar'; ev='Ya no se puede' } ) }
    )
  }
}

# CU51 (US-50) Finanzas por Voz y Contabilidad - administrador en la web
$DINAMICA_SPRINT4['CU51'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Administrador';        col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';           col=1; f=2 },
      @{ k='per';    n='Elegir período y filtros';        col=2; f=0 },
      @{ k='preg';   n='Dictar o escribir la pregunta';   col=2; f=1.6 },
      @{ k='gas';    n='Cargar gasto';                    col=2; f=4.5 },
      @{ k='valp';   n='Validar rango y filtros';         col=3; f=0 },
      @{ k='trad';   n='Traducir con Gemini';             col=3; f=1.6 },
      @{ k='reglas'; n='Leer con reglas fijas';           col=3; f=3 },
      @{ k='valg';   n='Validar gasto';                   col=3; f=4.5 },
      @{ k='error';  n='Informar error';                  col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';          col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';    a='aut' },
      @{ de='aut';    a='menu';   r='[token, finance.accounting.read y plan con accounting] {permissions.py:63; finance_views.py:49}' },
      @{ de='aut';    a='fin403'; r='[sin permiso o plan sin accounting] {403 | 403 plan_limit, plans.py:115}' },
      @{ de='menu';   a='per';    r='[ver resumen] {GET /reporting/finance/summary/, finance_views.py:92}' },
      @{ de='menu';   a='preg';   r='[preguntar] {POST /reporting/finance/interpret/, finance_views.py:143}' },
      @{ de='menu';   a='gas';    r='[cargar y finance.expense.manage] {POST .../expenses/, finance_views.py:258}' },
      @{ de='per';    a='valp';   r='_consulta(request, organizacion) {finance_views.py:57}' },
      @{ de='valp';   a='ok';     r='[válidos] / calcular() | con_comparacion(), FINANCE_QUERY {finance_views.py:101-104}' },
      @{ de='valp';   a='error';  r='[fecha, rango > 366 d, profesional o group inválido] {400 kpi_views.py:60; :69, :78}' },
      @{ de='preg';   a='trad';   r='[texto <= 300 y proveedor_disponible()] / ask_model() {finance_voice.py:413}' },
      @{ de='preg';   a='reglas'; r='[sin proveedor] / (None, plantilla) {voice.py:185-186}' },
      @{ de='preg';   a='error';  r='[vacía o profesional ambiguo] / _nada(motivos) {finance_voice.py:397, :410}' },
      @{ de='trad';   a='reglas'; r='[error o respuesta no JSON] / (None, plantilla) {voice.py:189-191}' },
      @{ de='trad';   a='ok';     r='[sanear() resuelve, <= 366 d] / ejecutar(), frase_de_respuesta() {finance_voice.py:415, :426}' },
      @{ de='reglas'; a='ok';     r='[analizar() resuelve, <= 366 d] / ejecutar(), frase_de_respuesta() {finance_voice.py:418, :431}' },
      @{ de='reglas'; a='error';  r='[consulta None o > 366 días] / _nada(unresolved) {finance_voice.py:420-424}' },
      @{ de='gas';    a='valg';   r='ExpenseSerializer(data) {finance_views.py:283}' },
      @{ de='valg';   a='ok';     r='[monto > 0, moneda, sede y fecha válidas] / INSERT expenses {finance_views.py:285}' },
      @{ de='valg';   a='error';  r='[monto <= 0 o fecha < hoy - 5 años o > hoy + 366 d] {400 finance_views.py:230, :249}' },
      @{ de='error';  a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';     a='fin' }
    )
  }

  tiempo = @{
    escenario = 'un pago cobrado el mes pasado se devuelve este mes y el administrador pregunta por voz cuánto ingresó comparado con el anterior'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no días medidos. El ingreso cuenta por paid_at (reporting/finance.py:190-194) y la devolución por refunded_at (finance.py:213-217): el mismo pago suma en el período anterior y resta en el actual. paid_at lo fija la confirmación (payments/services.py:103) y refunded_at la devolución (services.py:174). Los rangos son días locales del centro pasados a UTC (kpis.rango_utc, finance.py:144-145, appointments/kpis.py:56), el período sin fechas son 30 días (DIAS_POR_DEFECTO, reporting/kpi_views.py:28) y nunca más de 366 (kpis.py:35; finance_voice.py:422-424). con_comparacion calcula dos veces, el actual y el anterior (finance.py:285-289). La traducción a Gemini no tiene plazo propio (reporting/voice.py:203-220) y degrada a reglas fijas si falla (voice.py:189-191).'
    lineas = @(
      @{ n='Pago'
         estados=@('pending', 'succeeded', 'refunded')
         marcas=@( @{ t=0;  e='pending' },
                   @{ t=8;  e='succeeded'; ev='paid_at = now()' },
                   @{ t=34; e='refunded';  ev='refunded_at' } ) },
      @{ n='Mes que lo cuenta'
         estados=@('Anterior: ingreso', 'Actual: devolución')
         marcas=@( @{ t=0;  e='Anterior: ingreso' },
                   @{ t=24; e='Actual: devolución'; ev='día 1 local'; r='rango_utc' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Leyendo', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=46; e='Autenticando'; ev='POST interpret' },
                   @{ t=50; e='Validando';    ev='interpretar()' },
                   @{ t=62; e='Leyendo';      ev='calcular() x2' },
                   @{ t=70; e='Escribiendo';  ev='FINANCE_QUERY' },
                   @{ t=74; e='Confirmada';   ev='COMMIT' },
                   @{ t=78; e='Inactiva';     ev='200 frase' } ) },
      @{ n='Gemini'
         estados=@('En espera', 'Traduciendo', 'Respondió')
         marcas=@( @{ t=0;  e='En espera' },
                   @{ t=52; e='Traduciendo'; ev='ask_model()'; r='sin timeout' },
                   @{ t=58; e='Respondió';   ev='JSON' },
                   @{ t=62; e='En espera' } ) }
    )
  }
}


# =========================================================================
# Sprint 4 - datos de ESTADO y TIEMPO de CU50, CU52, CU53 y CU54.
# Leidos del codigo el 22/11/26 (working tree en main, 2349f66).
# =========================================================================

# -------------------------------------------------------------------------
# CU50 (US-49) Recordatorio de Toma de Medicamentos
# Flujo: ver lo recetado con su horario, activar los avisos locales y
# marcar una toma (taken o skipped) que se manda con POST.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU50'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';                 col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';               col=1; f=2 },
      @{ k='pedir';  n='Pedir mis medicamentos';              col=2; f=0 },
      @{ k='act';    n='Elegir hora de la primera toma';      col=2; f=1.6 },
      @{ k='marc';   n='Marcar toma';                         col=2; f=3.2 },
      @{ k='sinc';   n='Sincronizar tomas pendientes';        col=2; f=4.8 },
      @{ k='valh';   n='Interpretar frecuencia y duración';   col=3; f=0 },
      @{ k='prog';   n='Programar avisos locales';            col=3; f=1.6 },
      @{ k='valt';   n='Validar toma';                        col=3; f=4 },
      @{ k='error';  n='Informar error';                      col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';              col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y history_scope OWN] {CanReadHistory, intake_views.py:89, :95}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='pedir';  r='[Mis medicamentos] {GET /encounters/medications/<paciente>/}' },
      @{ de='menu';  a='act';    r='[Recordarme y schedule] {recordarme.dart:53, :113}' },
      @{ de='menu';  a='marc';   r='[Tomada en la app o en el aviso] {medications_screen.dart:85; recordatorios.dart:550}' },
      @{ de='pedir'; a='valh';   r='/ firmadas de 120 días, para_la_api() {intake_views.py:98-110}' },
      @{ de='valh';  a='ok';     r='[horario] / schedule, cumplimiento taken/skipped {frequency.py:136; intakes.py:38}' },
      @{ de='valh';  a='error';  r='[sin horario fijo, sin duración o > 200 tomas] / schedule_reason {frequency.py:143-151}' },
      @{ de='act';   a='prog';   r='showTimePicker(), pedirPermiso() {recordarme.dart:56, :64}' },
      @{ de='prog';  a='ok';     r='[toma futura] / zonedSchedule() por toma, _guardar() {recordatorios.dart:440-457}' },
      @{ de='marc';  a='sinc';   r='/ cancela su aviso y la encola en _pendientes {recordatorios.dart:492-506}' },
      @{ de='sinc';  a='valt';   r='marcarToma(): POST intakes/ {recordatorios.dart:527; intake_views.py:76}' },
      @{ de='sinc';  a='error';  r='[sin conexión] / queda en _pendientes, se reintenta {recordatorios.dart:538-540}' },
      @{ de='valt';  a='ok';     r='[1..total_doses y nueva] / INSERT status taken|skipped, 201 {intakes.py:65-75}' },
      @{ de='valt';  a='ok';     r='[409 already_recorded] / cuenta como enviada {intakes.py:76; medications_api.dart:149}' },
      @{ de='valt';  a='error';  r='[no_schedule | invalid_dose 400, ajeno 404] {intakes.py:55-64; intake_views.py:61}' },
      @{ de='error'; a='menu';   r='/ mensaje o motivo, sin «Recordarme»'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'cada 8 horas por 5 días: suena la toma 2, el paciente la pospone 15 min, la marca Tomada sin conexión y se manda al volver'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. El horario lo da el backend: interpretar() divide días * 24 por el intervalo (frequency.py:136-152; tope 90 días y 200 tomas, :34-35) y el teléfono calcula cada hora con momentoDe(n) = primera toma + intervalo * (n - 1) (recordatorios.dart:68-69). 8 h = intervalo de «cada 8 horas». Los avisos son locales (zonedSchedule, recordatorios.dart:276) en modo inexactAllowWhileIdle (:285): Android puede atrasarlos un poco. 15 min = posponerPor (recordatorios.dart:40, :512-523). Marcar cancela el aviso y deja la toma en _pendientes (:492-506), guardada en el almacén seguro; 20 s = Config.timeout de cada petición (mobile/lib/core/config.dart:40): sin conexión la toma queda pendiente y sincronizar() la reintenta al abrir Mis medicamentos (medications_screen.dart:62). La transacción no tiene plazo propio: registrar() hace el INSERT y (prescription_item, dose_number) es único, así que un reintento da 409 y cuenta como enviada (intakes.py:76-77; medications_api.dart:149).'
    lineas = @(
      @{ n='Transacción de la toma'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=50; e='Autenticando'; ev='POST intakes/' },
                   @{ t=56; e='Inactiva';     ev='sin conexión'; r='20 s' },
                   @{ t=62; e='Autenticando'; ev='sincronizar()' },
                   @{ t=66; e='Validando';    ev='registrar()' },
                   @{ t=70; e='Escribiendo';  ev='INSERT' },
                   @{ t=74; e='Confirmada';   ev='COMMIT' },
                   @{ t=78; e='Inactiva';     ev='201' } ) },
      @{ n='Horario de tomas'
         estados=@('Toma 1', 'Toma 2', 'Toma 3')
         marcas=@( @{ t=0;  e='Toma 1'; ev='primeraToma' },
                   @{ t=20; e='Toma 2'; ev='momentoDe(2)'; r='8 h' },
                   @{ t=84; e='Toma 3'; ev='momentoDe(3)'; r='8 h' } ) },
      @{ n='Aviso local de la toma 2'
         estados=@('Programado', 'Mostrado', 'Pospuesto', 'Cancelado')
         marcas=@( @{ t=0;  e='Programado'; ev='zonedSchedule()' },
                   @{ t=20; e='Mostrado';   ev='suena' },
                   @{ t=26; e='Pospuesto';  ev='Posponer' },
                   @{ t=40; e='Mostrado';   ev='suena de nuevo'; r='15 min' },
                   @{ t=46; e='Cancelado';  ev='Tomada' } ) },
      @{ n='Toma 2 en el teléfono'
         estados=@('Sin marcar', 'Pendiente', 'Enviada')
         marcas=@( @{ t=0;  e='Sin marcar' },
                   @{ t=46; e='Pendiente'; ev='marcar()' },
                   @{ t=78; e='Enviada';   ev='sale de pendientes' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU52 (US-51) Experiencia Plus en la Compra de la Ficha
# Flujo: abrir la experiencia Plus de la ficha pagada, guardar la
# preconsulta, agregar al calendario (móvil: Google Calendar) o bajar el
# .ics (web).
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU52'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';                 col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';               col=1; f=2 },
      @{ k='abrir';  n='Abrir Mi experiencia Plus';           col=2; f=0 },
      @{ k='cap';    n='Capturar preconsulta';                col=2; f=1.6 },
      @{ k='cal';    n='Agregar a mi calendario';             col=2; f=3.2 },
      @{ k='ics';    n='Pedir la ficha .ics (web)';           col=2; f=4.8 },
      @{ k='valf';   n='Verificar ficha propia y pagada';     col=3; f=0 },
      @{ k='valp';   n='Validar preconsulta y plazo';         col=3; f=1.6 },
      @{ k='ext';    n='Abrir Google Calendar';               col=3; f=3.2 },
      @{ k='vali';   n='Verificar ficha confirmada';          col=3; f=4.8 },
      @{ k='error';  n='Informar error';                      col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';              col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y CanReadAppointments] {preconsultation_views.py:24}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='abrir';  r='[ficha confirmed] {appointment_detail_screen.dart:522-528}' },
      @{ de='menu';  a='cap';    r='[_editable: confirmed y antes de starts_at] {preconsulta_plus.dart:92}' },
      @{ de='menu';  a='cal';    r='[_editable] {preconsulta_plus.dart:200-208}' },
      @{ de='menu';  a='ics';    r='[web] {ExperienciaPlus.tsx:59-61}' },
      @{ de='abrir'; a='valf';   r='_load(): GET preconsultation/ {preconsulta_plus.dart:117; preconsultation_views.py:36}' },
      @{ de='valf';  a='ok';     r='[owns_appointment y confirmed o attended] / 200 reason, questions {preconsultation_views.py:41}' },
      @{ de='valf';  a='error';  r='[ajena, pending_payment, cancelled o expired] / 404 {preconsultation_views.py:29-33}' },
      @{ de='cap';   a='valp';   r='_save(): PUT preconsultation/ {preconsulta_plus.dart:130; preconsultation_views.py:47}' },
      @{ de='valp';  a='ok';     r='[confirmed y starts_at > now] / update_or_create() {preconsultation_views.py:57-61}' },
      @{ de='valp';  a='error';  r='[attended 409 closed, starts_at <= now 409 started, 400] {preconsultation_views.py:49-56}' },
      @{ de='cal';   a='ext';    r='enlaceCalendario(): action=TEMPLATE, horas en UTC {preconsulta_plus.dart:38-57}' },
      @{ de='ext';   a='ok';     r='[launchUrl abre la app] {preconsulta_plus.dart:59, :94-96}' },
      @{ de='ext';   a='error';  r='[no abre] / «No se pudo abrir el calendario.» {preconsulta_plus.dart:97-99}' },
      @{ de='ics';   a='vali';   r='descargarArchivo(): GET calendar.ics {cliente.ts:92; calendar.py:114}' },
      @{ de='vali';  a='ok';     r='[propia y confirmed] / build_ics() con VALARM -PT24H {calendar.py:53, :96, :122}' },
      @{ de='vali';  a='error';  r='[ajena o no confirmed] / 404 sin decir cuál {calendar.py:119-121}' },
      @{ de='error'; a='menu';   r='/ mensaje de error'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el paciente paga dentro de los 15 min de la reserva, completa la preconsulta y, llegado starts_at, ya no la puede editar'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:270): la reserva nace pending_payment con expires_at (booking.py:110, :148) y _assert_payable rechaza el pago vencido (payments/services.py:39); confirm_payment la pasa a confirmed y borra expires_at (services.py:118-119) y deja notify(CONFIRMED) para después del COMMIT (:128), que manda el correo con «Cómo llegar» y el .ics (attendance.py:151-164). 24 h = la alarma VALARM TRIGGER:-PT24H del .ics (calendar.py:96); el enlace de Google Calendar del móvil no la trae (preconsulta_plus.dart:38-57). La preconsulta se edita mientras la ficha es confirmed y starts_at > now (preconsultation_views.py:49, :55; en el móvil _editable, preconsulta_plus.dart:92); desde starts_at el PUT da 409 appointment_started. Al firmarse la atención la ficha pasa a attended (encounters/services.py:173-175) y la preconsulta queda sólo de lectura.'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Autenticando'; ev='webhook del pago' },
                   @{ t=9;  e='Validando';    ev='_assert_payable()' },
                   @{ t=12; e='Escribiendo';  ev='confirmed' },
                   @{ t=14; e='Confirmada';   ev='COMMIT' },
                   @{ t=17; e='Inactiva';     ev='notify()' },
                   @{ t=30; e='Autenticando'; ev='PUT preconsulta' },
                   @{ t=33; e='Validando';    ev='starts_at > now' },
                   @{ t=36; e='Escribiendo';  ev='update_or_create()' },
                   @{ t=39; e='Confirmada';   ev='COMMIT' },
                   @{ t=42; e='Inactiva';     ev='200' },
                   @{ t=72; e='Autenticando'; ev='PUT tardío' },
                   @{ t=76; e='Validando';    ev='starts_at <= now' },
                   @{ t=80; e='Inactiva';     ev='409 started' } ) },
      @{ n='Ficha'
         estados=@('pending_payment', 'confirmed', 'attended')
         marcas=@( @{ t=0;  e='pending_payment'; ev='expires_at' },
                   @{ t=14; e='confirmed';       ev='pagada'; r='< 15 min' },
                   @{ t=84; e='attended';        ev='sign()' } ) },
      @{ n='Preconsulta'
         estados=@('Sin anotar', 'Editable', 'Guardada', 'Cerrada')
         marcas=@( @{ t=0;  e='Sin anotar' },
                   @{ t=14; e='Editable'; ev='confirmed' },
                   @{ t=39; e='Guardada'; ev='updated_at' },
                   @{ t=66; e='Cerrada';  ev='starts_at'; r='starts_at' } ) },
      @{ n='Evento .ics del correo'
         estados=@('Sin enviar', 'Adjuntado', 'Alarma')
         marcas=@( @{ t=0;  e='Sin enviar' },
                   @{ t=20; e='Adjuntado'; ev='send()' },
                   @{ t=50; e='Alarma';    ev='VALARM'; r='24 h' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU53 (US-52) Lista de Espera con Aviso de Cupo Liberado
# Flujo: una vuelta de process_waitlist --loop (como CU29 del Sprint 3).
# El disparador es el comando, sin usuario ni JWT. Estados de
# waitlist_entries: waiting, offered, booked, expired, cancelled.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU53'] = @{
  estado = @{
    estados = @(
      @{ k='ini';       tipo='inicial'; col=0; f=0 },
      @{ k='vuelta';    n='Iniciar comando';                       col=0; f=2 },
      @{ k='ok';        n='Transacción completada';                col=0; f=4 },
      @{ k='fin';       tipo='final';   col=0; f=6 },
      @{ k='finoff';    tipo='final';   col=1; f=0 },
      @{ k='orgs';      n='Recorrer organizaciones con lista';     col=1; f=2 },
      @{ k='esperar';   n='Esperar la vuelta siguiente';           col=1; f=4 },
      @{ k='liberar';   n='Liberar reservas vencidas';             col=2; f=0.5 },
      @{ k='refrescar'; n='Poner al día las entradas';             col=2; f=2 },
      @{ k='turnos';    n='Listar turnos libres que alguien espera'; col=2; f=3.5 },
      @{ k='error';     n='Informar error';                        col=2; f=6 },
      @{ k='cand';      n='Tomar siguiente entrada waiting';       col=3; f=1.5 },
      @{ k='guardar';   n='Guardar el turno 15 min';               col=4; f=0.5 },
      @{ k='ofrecer';   n='Marcar entrada offered';                col=4; f=2.25 },
      @{ k='avisar';    n='Avisar cupo liberado';                  col=4; f=4 }
    )
    transiciones = @(
      @{ de='ini';       a='vuelta' },
      @{ de='vuelta';    a='finoff';    r='[WAITLIST_PROCESS off, 0 o false] {process_waitlist.py:47-49}' },
      @{ de='vuelta';    a='orgs';      r='handle() [encendido] / _vuelta(), run_due() {process_waitlist.py:46, :73-74}' },
      @{ de='orgs';      a='liberar';   r='[queda una org con waitlist en el plan] / tenant_context(org) {waitlist.py:496-498, :471}' },
      @{ de='liberar';   a='refrescar'; r='/ pending_payment con expires_at <= now: expired {waitlist.py:472; holds.py:72-104}' },
      @{ de='refrescar'; a='turnos';    r='/ offered: booked|cancelled|expired; waiting vencida: expired {waitlist.py:473, :363-408}' },
      @{ de='refrescar'; a='error';     r='[excepción en la base dentro de run_organization] {waitlist.py:498-499}' },
      @{ de='turnos';    a='cand';      r='[queda un turno libre] / offer_freed_slot(), offer_slot() {waitlist.py:476-477, :329}' },
      @{ de='turnos';    a='orgs';      r='[no quedan turnos] / refresh_entries() {waitlist.py:478-480}' },
      @{ de='cand';      a='guardar';   r='[select_for_update waiting y libre a esa hora] {waitlist.py:296-304}' },
      @{ de='cand';      a='turnos';    r='[sin candidatas, SlotAlreadyTaken o tope del plan] / None {waitlist.py:288-293, :314-316}' },
      @{ de='guardar';   a='ofrecer';   r='/ book_appointment(): pending_payment, expires_at +15 min {booking.py:110, :148}' },
      @{ de='ofrecer';   a='avisar';    r='/ status=offered, offered_at=now, COMMIT {waitlist.py:319-325}' },
      @{ de='avisar';    a='turnos';    r='/ notify(CUPO_LIBERADO): push FCM y correo {waitlist.py:354-356}' },
      @{ de='error';     a='orgs';      r='/ logger.exception: siguiente organización {waitlist.py:500-501}'; ortogonal=$true },
      @{ de='orgs';      a='ok';        r='[no quedan organizaciones] / return total {waitlist.py:504}' },
      @{ de='ok';        a='esperar';   r='[--loop] / time.sleep(every * 60), every = 1 {process_waitlist.py:42, :55, :71}' },
      @{ de='esperar';   a='orgs';      r='/ close_old_connections(), _vuelta() {process_waitlist.py:61, :70}' },
      @{ de='ok';        a='fin';       r='[sin --loop] {process_waitlist.py:51-53}' }
    )
  }

  tiempo = @{
    escenario = 'se cancela una ficha, el turno se le guarda 15 min a la primera de la fila, no paga y la vuelta del proceso se lo ofrece a la segunda'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. La primera oferta no espera al proceso: la cancelación deja offer_freed_slot en transaction.on_commit (changes.py:201), que guarda el turno como una ficha pending_payment (book_appointment, booking.py:148) y marca la entrada offered (waitlist.py:319-325) bajo tenant_context (:337). 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:270). 1 min = --every por omisión de process_waitlist (process_waitlist.py:41-44, :55), lanzado con --loop por scripts/start.sh:60; por eso la oferta vencida se libera a lo sumo un minuto después de expires_at. La vuelta la libera con include_offers=True (waitlist.py:472; holds.py:72), refresh_entries pasa la entrada offered a expired (:383-394) y _turnos_libres_que_alguien_espera vuelve a encontrar el turno y se lo ofrece a la siguiente waiting (:431, :476-477). 3 min = GRACE_MINUTES (holds.py:48): si el proceso estuviera apagado, la búsqueda libera el turno igual pasado ese margen. Push con TIMEOUT_SECONDS = 10 por POST a FCM (notifications/push.py:36); notify nunca deshace la oferta.'
    lineas = @(
      @{ n='Comando process_waitlist'
         estados=@('Durmiendo', 'Dando la vuelta')
         marcas=@( @{ t=0;  e='Durmiendo';       ev='time.sleep()' },
                   @{ t=64; e='Dando la vuelta'; ev='_vuelta()'; r='1 min' },
                   @{ t=82; e='Durmiendo';       ev='total' } ) },
      @{ n='Transacción de la oferta'
         estados=@('Inactiva', 'Fijando inquilino', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Fijando inquilino'; ev='on_commit' },
                   @{ t=9;  e='Validando';         ev='FOR UPDATE' },
                   @{ t=12; e='Escribiendo';       ev='book_appointment()' },
                   @{ t=15; e='Confirmada';        ev='COMMIT' },
                   @{ t=18; e='Inactiva';          ev='notify(cupo)' },
                   @{ t=66; e='Fijando inquilino'; ev='tenant_context()' },
                   @{ t=69; e='Validando';         ev='include_offers' },
                   @{ t=72; e='Escribiendo';       ev='book_appointment()' },
                   @{ t=75; e='Confirmada';        ev='COMMIT' },
                   @{ t=78; e='Inactiva';          ev='notify(cupo)' } ) },
      @{ n='Turno guardado a la primera'
         estados=@('Sin reserva', 'pending_payment', 'Vencida', 'expired')
         marcas=@( @{ t=0;  e='Sin reserva' },
                   @{ t=12; e='pending_payment'; ev='expires_at' },
                   @{ t=60; e='Vencida';         ev='expires_at <= now'; r='15 min' },
                   @{ t=69; e='expired';         ev='release_expired()' } ) },
      @{ n='Entrada de la primera'
         estados=@('waiting', 'offered', 'expired')
         marcas=@( @{ t=0;  e='waiting' },
                   @{ t=15; e='offered'; ev='offered_at' },
                   @{ t=70; e='expired'; ev='refresh_entries()' } ) },
      @{ n='Entrada de la segunda'
         estados=@('waiting', 'offered')
         marcas=@( @{ t=0;  e='waiting' },
                   @{ t=75; e='offered'; ev='offered_at' } ) }
    )
  }
}

# -------------------------------------------------------------------------
# CU54 (US-53) Registro de Signos Vitales
# Flujo: capturar los signos en el borrador, guardarlos con el PATCH,
# firmar (quedan fijos) y ver la evolución.
# -------------------------------------------------------------------------
$DINAMICA_SPRINT4['CU54'] = @{
  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Médico';                   col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';               col=1; f=2 },
      @{ k='cap';    n='Capturar signos vitales';             col=2; f=0 },
      @{ k='gua';    n='Guardar borrador';                    col=2; f=1.6 },
      @{ k='firm';   n='Confirmar firma';                     col=2; f=3.2 },
      @{ k='evo';    n='Pedir evolución';                     col=2; f=4.8 },
      @{ k='valw';   n='Leer y marcar en la web';             col=3; f=0 },
      @{ k='valb';   n='Validar rangos y borrador';           col=3; f=1.6 },
      @{ k='valg';   n='Validar firma';                       col=3; f=3.2 },
      @{ k='valh';   n='Verificar alcance del historial';     col=3; f=4.8 },
      @{ k='error';  n='Informar error';                      col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';              col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token y encounters.encounter.create] {CanCreateEncounters, views.py:149-151}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='cap';    r='[atención draft] {EditorSignos, Atencion.tsx:175}' },
      @{ de='menu';  a='firm';   r='[firmar] {POST /encounters/<id>/sign/}' },
      @{ de='menu';  a='evo';    r='[pestaña Evolución] {Historial.tsx:57, :62}' },
      @{ de='cap';   a='valw';   r='leerSignos(textos) {signos_vitales.ts:16; Atencion.tsx:82}' },
      @{ de='valw';  a='gua';    r='[posibles] / calcular(): IMC, alerts Alta | Baja {signos_vitales.ts:37-47}' },
      @{ de='valw';  a='error';  r='[imposible] / campo marcado, Guardar y Firmar bloqueados {Atencion.tsx:88, :131}' },
      @{ de='gua';   a='valb';   r='PATCH vital_signs, sólo si cambiaron {api/atencion.ts:197; views.py:159}' },
      @{ de='valb';  a='ok';     r='[en VITAL_LIMITS, diastólica < sistólica y draft] / _save_vital_signs() {services.py:129}' },
      @{ de='valb';  a='error';  r='[fuera de rango 400, ajena 404, signed 409] {serializers.py:101, :132; services.py:116}' },
      @{ de='firm';  a='valg';   r='firmar() {Atencion.tsx}' },
      @{ de='valg';  a='ok';     r='[motivo y diagnóstico] / signed_at = now(): signos fijos {services.py:166-169}' },
      @{ de='valg';  a='error';  r='[ya firmado 409 o falta motivo o diagnóstico 400] {services.py:155-164}' },
      @{ de='evo';   a='valh';   r='verHistorial(): GET history/<paciente>/ {api/atencion.ts:226; history_views.py:40}' },
      @{ de='valh';  a='ok';     r='[PROFESSIONAL u OWN] / signed con vital_signs, puntosDe() {history_views.py:48; signos_vitales.ts:95}' },
      @{ de='valh';  a='error';  r='[sin alcance] / 404 {history_views.py:44-46}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'el médico carga los signos al empezar la consulta, la sesión se renueva sola y firma; desde la firma los signos quedan fijos'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. Los signos no tienen plazo propio: se guardan, reemplazan o borran mientras la atención es draft (update_draft y _save_vital_signs, encounters/services.py:114-151) y quedan fijos en el instante de la firma, que pone signed_at = now() (services.py:166-169); desde ahí el PATCH da 409 (:116-119) y la base los rechaza con el trigger trg_vital_signs_solo_en_borrador (encounters/migrations/0012, :53-78); se corrigen con una enmienda de la sección vital_signs. Lo imposible se rechaza siempre con los mismos límites (VITAL_LIMITS, models.py:427; CHECK ck_vitals_*, :476-483). El reloj que manda es la sesión del médico en la web: 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:387); 25 min = MINUTOS_HASTA_RENOVAR (frontend/src/sesion/ContextoSesion.tsx:38), el setTimeout de :81 renueva el par antes de que venza y el refresco viejo va a la lista negra (ROTATE_REFRESH_TOKENS y BLACKLIST_AFTER_ROTATION, settings.py:389-390). Por eso la firma sale con el acceso nuevo.'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Autenticando'; ev='PATCH vital_signs' },
                   @{ t=11; e='Validando';    ev='_rango(), validate()' },
                   @{ t=16; e='Escribiendo';  ev='INSERT' },
                   @{ t=21; e='Confirmada';   ev='COMMIT' },
                   @{ t=25; e='Inactiva';     ev='200 (bmi, alerts)' },
                   @{ t=60; e='Autenticando'; ev='POST /sign/' },
                   @{ t=65; e='Validando';    ev='sign()' },
                   @{ t=70; e='Escribiendo';  ev='UPDATE' },
                   @{ t=75; e='Confirmada';   ev='COMMIT' },
                   @{ t=80; e='Inactiva';     ev='200' } ) },
      @{ n='Renovación de la sesión'
         estados=@('Esperando', 'Renovando')
         marcas=@( @{ t=0;  e='Esperando' },
                   @{ t=44; e='Renovando'; ev='renovar()'; r='25 min' },
                   @{ t=48; e='Esperando'; ev='par nuevo' } ) },
      @{ n='Acceso viejo'
         estados=@('Vigente', 'Vencido')
         marcas=@( @{ t=0;  e='Vigente' },
                   @{ t=53; e='Vencido'; ev='expira'; r='30 min' } ) },
      @{ n='Atención'
         estados=@('draft', 'signed')
         marcas=@( @{ t=0;  e='draft' },
                   @{ t=75; e='signed'; ev='signed_at = now()' } ) },
      @{ n='Signos vitales'
         estados=@('Sin cargar', 'En borrador', 'Fijos')
         marcas=@( @{ t=0;  e='Sin cargar' },
                   @{ t=21; e='En borrador'; ev='INSERT' },
                   @{ t=75; e='Fijos';       ev='trigger 0012' } ) }
    )
  }
}


