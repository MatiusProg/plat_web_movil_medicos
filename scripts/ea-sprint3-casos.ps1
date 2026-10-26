# =========================================================================
# Datos de los casos de uso del Sprint 3, para los generadores de EA.
#
# Lo consumen, con dot-sourcing:
#   ea-comunicacion-sprint3.ps1    (2.1.3 diagrama de comunicacion)
#   ea-diseno-clases-sprint3.ps1   (diagrama de diseno de clase)
#
# Mismo formato que ea-sprint2-casos.ps1. Lo nuevo del Sprint 3:
#   - El diagrama de analisis de clase pasa a ser de DISENO de clase y va
#     despues del de secuencia. Cada mensaje que llega a una clase queda como
#     operacion de esa clase (el generador lo agrega si falta): asi lo que se
#     ve en la comunicacion y en la secuencia se rastrea en la clase.
#   - rel: relaciones entre ENTIDADES, con su multiplicidad en cada extremo
#     (d = desde, a = hacia, cd / ca = multiplicidad, r = nombre). Salen de
#     las ForeignKey de los modelos.
#   - ret = $true: es una respuesta; no se agrega como operacion.
#
# La secuencia la arma Karen: tiene que usar estos mismos participantes y
# estos mismos mensajes, con la misma numeracion.
# =========================================================================

$CASOS_SPRINT3 = [ordered]@{

  # -----------------------------------------------------------------------
  'CU24' = @{
    cu = 'CU24'; nombre = 'Agendamiento y Cobro Asistido'; us = 'US-23'
    nota = 'Al 26/10 está el cobro en efectivo en ventanilla (PR #80); la pantalla del mostrador todavía no existe y se usa el endpoint.'
    participantes = @(
      @{ k='recep'; n='Recepcionista'; rol='actor'; col=0; f=1 },
      @{ k='api'; n='InterfazCobroVentanilla'; rol='boundary'; col=1; f=1
         nota='Endpoint POST /api/payments/appointments/{id}/cash/ (payments/urls.py). Sin pantalla web al 26/10.'
         atr=@('POST /api/payments/appointments/{id}/cash/ : 201 | 400 | 404 | 409')
         ops=@('cobrarEnEfectivo(ficha)') },
      @{ k='vista'; n='ControladorCobroVentanilla'; rol='control'; col=2; f=0
         nota='CashPaymentView en payments/views.py. Busca la ficha dentro de la organización del usuario.'
         ops=@('post(request, pk)') },
      @{ k='gestor'; n='GestorPagos'; rol='control'; col=2; f=2
         nota='payments/services.py.'
         ops=@('register_cash_payment(appointment, user, request)', '_assert_payable(appointment)', 'quote(appointment)', 'confirm_payment(payment, request)', '_asentar(request, payment, evento)') },
      @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=3.4
         nota='audit/services.py.'
         ops=@('record(request, action, entity, entity_id, detail)') },
      @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=0
         nota='Tabla appointments.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'status : varchar', 'expires_at : timestamptz')
         ops=@('filter(pk, organization)', 'save(status)') },
      @{ k='pago'; n='Pago'; rol='entity'; col=3; f=2
         nota='Tabla payments. provider = cash para el cobro en ventanilla.'
         atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'created_by_id : uuid', 'amount : numeric(10,2)', 'currency : varchar(3)', 'provider : varchar(12)', 'status : varchar', 'paid_at : timestamptz')
         ops=@('create(appointment, amount, provider)', 'save(status, paid_at)') },
      @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=3.6
         nota='Tabla audit_log.'
         atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
         ops=@('insert(asiento)') }
    )
    rel = @(
      @{ d='ficha'; a='pago'; cd='1'; ca='0..*'; r='se paga con' }
    )
    grupos = [ordered]@{ 1 = 'Cobrar en ventanilla'; 2 = 'La ficha no se puede cobrar' }
    mensajes = @(
      @{ g=1; d='recep'; a='api'; m='cobrarEnEfectivo(ficha)' },
      @{ g=1; d='api'; a='vista'; m='post(request, pk)' },
      @{ g=1; d='vista'; a='ficha'; m='filter(pk, organization)' },
      @{ g=1; d='vista'; a='gestor'; m='register_cash_payment(appointment, user, request)' },
      @{ g=1; d='gestor'; a='gestor'; m='_assert_payable(appointment)' },
      @{ g=1; d='gestor'; a='gestor'; m='quote(appointment)' },
      @{ g=1; d='gestor'; a='pago'; m='create(appointment, amount, provider)' },
      @{ g=1; d='gestor'; a='bitgestor'; m='record(request, action, entity, entity_id, detail)' },
      @{ g=1; d='bitgestor'; a='bitacora'; m='insert(asiento)' },
      @{ g=1; d='gestor'; a='gestor'; m='confirm_payment(payment, request)' },
      @{ g=1; d='gestor'; a='pago'; m='save(status, paid_at)' },
      @{ g=1; d='gestor'; a='ficha'; m='save(status)' },
      @{ g=1; d='vista'; a='api'; m='201(payment_id, amount, appointment)'; ret=$true },
      @{ g=2; d='gestor'; a='vista'; m='ValidationError(code)'; ret=$true },
      @{ g=2; d='vista'; a='api'; m='400(code, detail)'; ret=$true }
    )
  }

  # -----------------------------------------------------------------------
  'CU27' = @{
    cu = 'CU27'; nombre = 'Emisión de Recetas y Órdenes Médicas'; us = 'US-26'
    nota = 'La receta y las órdenes sólo se editan mientras la atención está en borrador; firmada, se corrige con una enmienda (PR #83).'
    participantes = @(
      @{ k='medico'; n='Médico'; rol='actor'; col=0; f=1.5 },
      @{ k='pantalla'; n='PantallaRecetaAtencion'; rol='boundary'; col=1; f=1.5
         nota='Web: frontend/src/paginas/RecetaAtencion.tsx (PanelReceta, RecetaDeLaAtencion) y frontend/src/api/atencion.ts.'
         atr=@('POST /api/encounters/{id}/prescription/ : 201 | 409', 'DELETE /api/encounters/{id}/prescription/{renglon}/ : 204 | 409', 'POST /api/encounters/{id}/orders/ : 201 | 409', 'DELETE /api/encounters/{id}/orders/{orden}/ : 204 | 409', 'POST /api/encounters/{id}/sign/ : 200 | 409', 'GET /api/encounters/{id}/prescription.pdf : 200')
         ops=@('enviarMedicamento(datos)', 'enviarOrden(datos)', 'quitar(renglon)', 'firmar()', 'descargarReceta(id)', 'agregarMedicamento(id, datos, contexto)', 'agregarOrden(id, datos, contexto)', 'quitarMedicamento(id, renglon, contexto)', 'quitarOrden(id, orden, contexto)', 'firmarEncuentro(id, contexto)') },
      @{ k='vista'; n='ControladorAtencion'; rol='control'; col=2; f=0.5
         nota='encounters/views.py: EncounterChildrenView, EncounterChildDetailView, EncounterSignView y PrescriptionPdfView.'
         ops=@('_own_encounter(request, pk)', '_audit(request, action, encuentro)') },
      @{ k='gestor'; n='GestorAtencion'; rol='control'; col=2; f=2.5
         nota='encounters/services.py.'
         ops=@('_require_draft(encounter)', 'is_own(user, encounter)') },
      @{ k='pdf'; n='GeneradorReceta'; rol='control'; col=1; f=4
         nota='encounters/prescription_pdf.py (reportlab). La receta no lleva el diagnóstico.'
         ops=@('filename(encounter)', '_edad(nacimiento, dia)') },
      @{ k='encuentro'; n='Encuentro'; rol='entity'; col=3; f=0
         nota='Tabla encounters.'
         atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'status : varchar', 'diagnosis : text', 'indications : text', 'signed_at : timestamptz', 'signed_by_id : uuid')
         ops=@() },
      @{ k='renglon'; n='RenglonReceta'; rol='entity'; col=3; f=2
         nota='Tabla encounter_prescription_items.'
         atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'medication : varchar(200)', 'dose : varchar(80)', 'frequency : varchar(80)', 'duration : varchar(80)', 'instructions : varchar', 'created_at : timestamptz')
         ops=@() },
      @{ k='orden'; n='OrdenMedica'; rol='entity'; col=3; f=3.4
         nota='Tabla encounter_orders. kind: laboratorio o imagen.'
         atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'kind : varchar(12)', 'description : varchar(300)', 'notes : varchar(300)', 'created_at : timestamptz')
         ops=@() }
    )
    rel = @(
      @{ d='encuentro'; a='renglon'; cd='1'; ca='0..*'; r='prescribe' },
      @{ d='encuentro'; a='orden'; cd='1'; ca='0..*'; r='solicita' }
    )
    grupos = [ordered]@{ 1 = 'Armar la receta y las órdenes (borrador)'; 2 = 'Firmar la atención'; 3 = 'Descargar la receta en PDF'; 4 = 'La atención ya está firmada' }
    mensajes = @(
      @{ g=1; d='medico'; a='pantalla'; m='enviarMedicamento(datos)' },
      @{ g=1; d='pantalla'; a='vista'; m='post(request, pk, kind)' },
      @{ g=1; d='vista'; a='vista'; m='_own_encounter(request, pk)' },
      @{ g=1; d='vista'; a='gestor'; m='add_child(encounter, kind, data)' },
      @{ g=1; d='gestor'; a='gestor'; m='_require_draft(encounter)' },
      @{ g=1; d='gestor'; a='renglon'; m='create(medication, dose, frequency, duration)' },
      @{ g=1; d='medico'; a='pantalla'; m='enviarOrden(datos)' },
      @{ g=1; d='gestor'; a='orden'; m='create(kind, description, notes)' },
      @{ g=1; d='medico'; a='pantalla'; m='quitar(renglon)' },
      @{ g=1; d='pantalla'; a='vista'; m='delete(request, pk, child_pk)' },
      @{ g=1; d='vista'; a='gestor'; m='delete_child(encounter, child)' },
      @{ g=1; d='gestor'; a='renglon'; m='delete()' },
      @{ g=1; d='vista'; a='pantalla'; m='200(encuentro)'; ret=$true },
      @{ g=2; d='medico'; a='pantalla'; m='firmar()' },
      @{ g=2; d='pantalla'; a='vista'; m='sign(request, pk)' },
      @{ g=2; d='vista'; a='gestor'; m='sign(encounter, user)' },
      @{ g=2; d='gestor'; a='encuentro'; m='save(status, signed_at, signed_by)' },
      @{ g=2; d='vista'; a='vista'; m='_audit(request, action, encuentro)' },
      @{ g=3; d='medico'; a='pantalla'; m='descargarReceta(id)' },
      @{ g=3; d='pantalla'; a='vista'; m='get(request, pk)' },
      @{ g=3; d='vista'; a='pdf'; m='render(encounter)' },
      @{ g=3; d='pdf'; a='encuentro'; m='select_related(patient, practitioner, branch)' },
      @{ g=3; d='pdf'; a='renglon'; m='prescription_items()' },
      @{ g=3; d='pdf'; a='orden'; m='orders()' },
      @{ g=3; d='vista'; a='pantalla'; m='200(application/pdf)'; ret=$true },
      @{ g=4; d='gestor'; a='vista'; m='Conflict(encounter_signed)'; ret=$true },
      @{ g=4; d='vista'; a='pantalla'; m='409(detail)'; ret=$true }
    )
  }

  # -----------------------------------------------------------------------
  'CU28' = @{
    cu = 'CU28'; nombre = 'Consulta de Recetas e Indicaciones'; us = 'US-27'
    nota = 'El paciente ve las recetas, las órdenes y las enmiendas dentro de su historia clínica, en la web y en el móvil (PR #83).'
    participantes = @(
      @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=1.5 },
      @{ k='pantalla'; n='PantallaHistoriaClinica'; rol='boundary'; col=1; f=1.5
         nota='Web: frontend/src/paginas/Historial.tsx y RecetaDeLaAtencion (RecetaAtencion.tsx). Móvil: mobile/lib/features/clinical_record/ (clinical_record_screen.dart, clinical_record_api.dart).'
         atr=@('GET /api/encounters/history/{patient_id}/ : 200 | 403 | 404', 'GET /api/encounters/{id}/prescription.pdf : 200 | 404')
         ops=@('abrirMiHistoria()', 'cambiarPersona(opcion)', 'descargarReceta(id)', 'verHistorial(pacienteId, contexto)', 'verHistoriaClinica(pacienteId)') },
      @{ k='vista'; n='ControladorHistorial'; rol='control'; col=2; f=0.5
         nota='PatientHistoryView y CanReadHistory en encounters/history_views.py.'
         ops=@('has_permission(request, view)') },
      @{ k='gestor'; n='GestorAtencion'; rol='control'; col=2; f=2
         nota='encounters/services.py. history_scope decide qué ve cada uno: el paciente, lo suyo y lo de sus dependientes.'
         ops=@() },
      @{ k='recetavista'; n='ControladorReceta'; rol='control'; col=2; f=3.2
         nota='PrescriptionPdfView en encounters/views.py.'
         ops=@() },
      @{ k='pdf'; n='GeneradorReceta'; rol='control'; col=2; f=4.4
         nota='encounters/prescription_pdf.py.'
         ops=@('filename(encounter)') },
      @{ k='entpaciente'; n='Paciente'; rol='entity'; col=3; f=0
         nota='Tabla patients.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'birth_date : date')
         ops=@() },
      @{ k='encuentro'; n='Encuentro'; rol='entity'; col=3; f=1.4
         nota='Tabla encounters.'
         atr=@('id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'status : varchar', 'indications : text', 'treatment : text', 'signed_at : timestamptz')
         ops=@() },
      @{ k='renglon'; n='RenglonReceta'; rol='entity'; col=4; f=0.5
         nota='Tabla encounter_prescription_items.'
         atr=@('id : uuid', 'encounter_id : uuid', 'medication : varchar(200)', 'dose : varchar(80)', 'frequency : varchar(80)', 'duration : varchar(80)')
         ops=@() },
      @{ k='orden'; n='OrdenMedica'; rol='entity'; col=4; f=2
         nota='Tabla encounter_orders.'
         atr=@('id : uuid', 'encounter_id : uuid', 'kind : varchar(12)', 'description : varchar(300)', 'notes : varchar(300)')
         ops=@() },
      @{ k='enmienda'; n='Enmienda'; rol='entity'; col=4; f=3.4
         nota='Tabla encounter_amendments.'
         atr=@('id : uuid', 'encounter_id : uuid', 'section : varchar', 'text : text', 'author_id : uuid', 'created_at : timestamptz')
         ops=@() }
    )
    rel = @(
      @{ d='entpaciente'; a='entpaciente'; cd='0..1'; ca='0..*'; r='tiene a cargo' },
      @{ d='entpaciente'; a='encuentro'; cd='1'; ca='0..*'; r='es atendido en' },
      @{ d='encuentro'; a='renglon'; cd='1'; ca='0..*'; r='prescribe' },
      @{ d='encuentro'; a='orden'; cd='1'; ca='0..*'; r='solicita' },
      @{ d='encuentro'; a='enmienda'; cd='1'; ca='0..*'; r='se corrige con' }
    )
    grupos = [ordered]@{ 1 = 'Ver la historia con sus recetas'; 2 = 'Descargar una receta'; 3 = 'Sin permiso sobre ese paciente' }
    mensajes = @(
      @{ g=1; d='paciente'; a='pantalla'; m='abrirMiHistoria()' },
      @{ g=1; d='pantalla'; a='vista'; m='get(request, patient_id)' },
      @{ g=1; d='vista'; a='vista'; m='has_permission(request, view)' },
      @{ g=1; d='vista'; a='gestor'; m='history_scope(user, patient)' },
      @{ g=1; d='gestor'; a='entpaciente'; m='filter(user, guardian)' },
      @{ g=1; d='vista'; a='encuentro'; m='filter(patient)' },
      @{ g=1; d='vista'; a='renglon'; m='prefetch(prescription_items)' },
      @{ g=1; d='vista'; a='orden'; m='prefetch(orders)' },
      @{ g=1; d='vista'; a='enmienda'; m='prefetch(amendments)' },
      @{ g=1; d='vista'; a='pantalla'; m='200(atenciones)'; ret=$true },
      @{ g=1; d='paciente'; a='pantalla'; m='cambiarPersona(opcion)' },
      @{ g=2; d='paciente'; a='pantalla'; m='descargarReceta(id)' },
      @{ g=2; d='pantalla'; a='recetavista'; m='get(request, pk)' },
      @{ g=2; d='recetavista'; a='pdf'; m='render(encounter)' },
      @{ g=2; d='recetavista'; a='pantalla'; m='200(application/pdf)'; ret=$true },
      @{ g=3; d='vista'; a='pantalla'; m='403(detail)'; ret=$true }
    )
  }

  # -----------------------------------------------------------------------
  'CU29' = @{
    cu = 'CU29'; nombre = 'Gestión de Notificaciones'; us = 'US-28'
    nota = 'Push por Firebase Cloud Messaging y correo por Brevo. El recordatorio lo dispara el comando send_appointment_reminders; las fichas reservadas, pagadas o canceladas llaman al mismo notify() (PR #81).'
    participantes = @(
      @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=0.5 },
      @{ k='sistema'; n='Sistema'; rol='actor'; col=0; f=3 },
      @{ k='app'; n='ServicioPushMovil'; rol='boundary'; col=1; f=0.5
         nota='mobile/lib/core/notifications/push.dart (clase Push).'
         atr=@('POST /api/notifications/devices/ : 201 | 400', 'DELETE /api/notifications/devices/ : 204')
         ops=@('iniciarSesion()', 'cerrarSesion()', 'iniciar()', 'registrar(api)', 'olvidar(api)', 'tocarAviso(appointmentId)') },
      @{ k='comando'; n='ComandoRecordatorios'; rol='boundary'; col=1; f=3
         nota='appointments/management/commands/send_appointment_reminders.py. Corre cada cierto tiempo en Railway.'
         atr=@('--loop : bool', '--interval : int')
         ops=@('add_arguments(parser)', '_vuelta()') },
      @{ k='vista'; n='ControladorDispositivos'; rol='control'; col=2; f=0
         nota='DeviceTokenView en notifications/views.py.'
         ops=@() },
      @{ k='recordatorios'; n='GestorRecordatorios'; rol='control'; col=2; f=3
         nota='appointments/reminders.py. Una transacción por ficha: si una falla, las ya avisadas no se repiten.'
         ops=@('due(now)') },
      @{ k='notif'; n='GestorNotificaciones'; rol='control'; col=3; f=1.8
         nota='notifications/services.py.'
         ops=@('_recipient(appointment)', '_push_text(event, appointment)', '_email(event, appointment)') },
      @{ k='push'; n='ClientePush'; rol='control'; col=3; f=3.4
         nota='notifications/push.py. Borra el token cuando FCM dice que ya no existe.'
         ops=@('_payload(token, message)', '_is_dead(response)') },
      @{ k='tokens'; n='TokenDispositivo'; rol='entity'; col=4; f=0
         nota='Tabla device_tokens.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'token : text', 'platform : varchar', 'created_at : timestamptz', 'last_seen_at : timestamptz')
         ops=@() },
      @{ k='ficha'; n='Ficha'; rol='entity'; col=4; f=1.6
         nota='Tabla appointments. reminder_sent_at evita repetir el recordatorio.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'starts_at : timestamptz', 'status : varchar', 'reminder_sent_at : timestamptz')
         ops=@() },
      @{ k='usuario'; n='Usuario'; rol='entity'; col=4; f=3
         nota='Tabla users.'
         atr=@('id : uuid', 'organization_id : uuid', 'email : varchar(254)', 'first_name : varchar(80)')
         ops=@() },
      @{ k='fcm'; n='Firebase Cloud Messaging'; rol='externo'; col=4; f=4.4 },
      @{ k='correo'; n='Servicio de correo (Brevo)'; rol='externo'; col=3; f=4.8 }
    )
    rel = @(
      @{ d='usuario'; a='tokens'; cd='1'; ca='0..*'; r='registra' },
      @{ d='usuario'; a='ficha'; cd='1'; ca='0..*'; r='recibe aviso de' }
    )
    grupos = [ordered]@{ 1 = 'Registrar el dispositivo al iniciar sesión'; 2 = 'Recordatorio de la ficha'; 3 = 'Olvidar el dispositivo al cerrar sesión' }
    mensajes = @(
      @{ g=1; d='paciente'; a='app'; m='iniciarSesion()' },
      @{ g=1; d='app'; a='app'; m='iniciar()' },
      @{ g=1; d='app'; a='fcm'; m='getToken()' },
      @{ g=1; d='app'; a='vista'; m='post(request)' },
      @{ g=1; d='vista'; a='tokens'; m='update_or_create(token, user, platform)' },
      @{ g=2; d='sistema'; a='comando'; m='handle()' },
      @{ g=2; d='comando'; a='recordatorios'; m='run_due(now)' },
      @{ g=2; d='recordatorios'; a='recordatorios'; m='run_for(organization, now)' },
      @{ g=2; d='recordatorios'; a='ficha'; m='select_for_update(skip_locked)' },
      @{ g=2; d='recordatorios'; a='notif'; m='notify(event, appointment_id, organization_id)' },
      @{ g=2; d='notif'; a='ficha'; m='_load(appointment_id)' },
      @{ g=2; d='notif'; a='push'; m='send_to_user(user, message)' },
      @{ g=2; d='push'; a='tokens'; m='filter(user)' },
      @{ g=2; d='push'; a='fcm'; m='send(payload)' },
      @{ g=2; d='push'; a='tokens'; m='delete()' },
      @{ g=2; d='notif'; a='correo'; m='send_mail(asunto, cuerpo)' },
      @{ g=2; d='recordatorios'; a='ficha'; m='save(reminder_sent_at)' },
      @{ g=2; d='fcm'; a='app'; m='_mostrarConLaAppAbierta(mensaje)' },
      @{ g=2; d='paciente'; a='app'; m='tocarAviso(appointmentId)' },
      @{ g=3; d='paciente'; a='app'; m='cerrarSesion()' },
      @{ g=3; d='app'; a='vista'; m='delete(request)' },
      @{ g=3; d='vista'; a='tokens'; m='filter(token, user).delete()' }
    )
  }

  # -----------------------------------------------------------------------
  'CU30' = @{
    cu = 'CU30'; nombre = 'Consulta de Indicadores y KPIs'; us = 'US-29'
    nota = 'Ocupación, inasistencia, ingresos y demanda por sucursal y especialidad, calculados en la base con la organización del token (PR #82).'
    participantes = @(
      @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=1.5 },
      @{ k='pantalla'; n='PantallaKpis'; rol='boundary'; col=1; f=1.5
         nota='Web: frontend/src/paginas/Kpis.tsx y frontend/src/api/kpis.ts.'
         atr=@('GET /api/reporting/kpis/?from=&to=&branch= : 200 | 400 | 403')
         ops=@('abrirKpis()', 'filtrarPorSucursal(branch)', 'rangoPorDefecto()', 'verKpis(filtros, contexto)', 'Anillo(tasa, etiqueta, tono)', 'Barras(filas, vacio)') },
      @{ k='vista'; n='ControladorKpis'; rol='control'; col=2; f=0.5
         nota='KpiView en reporting/kpi_views.py. Pide el permiso reporting.kpi.read.'
         ops=@('_fecha(valor)', '_error(code, detail)') },
      @{ k='calc'; n='CalculadoraKpis'; rol='control'; col=2; f=2.5
         nota='appointments/kpis.py.'
         ops=@('debian_atenderse_q(ahora)', 'inasistencia_q(ahora)', '_tasa(parte, total)') },
      @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=0
         nota='Tabla appointments.'
         atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'status : varchar', 'checked_in_at : timestamptz')
         ops=@() },
      @{ k='pago'; n='Pago'; rol='entity'; col=3; f=1.8
         nota='Tabla payments.'
         atr=@('id : uuid', 'appointment_id : uuid', 'amount : numeric(10,2)', 'currency : varchar(3)', 'status : varchar', 'paid_at : timestamptz')
         ops=@() },
      @{ k='agenda'; n='Agenda'; rol='entity'; col=4; f=0
         nota='Tabla schedules.'
         atr=@('id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'capacity : smallint', 'valid_from : date', 'valid_until : date', 'is_active : boolean')
         ops=@() },
      @{ k='bloqueo'; n='BloqueoAgenda'; rol='entity'; col=4; f=2
         nota='Tabla schedule_blocks.'
         atr=@('id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'is_active : boolean')
         ops=@() },
      @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=3.4
         nota='Tabla branches.'
         atr=@('id : uuid', 'organization_id : uuid', 'name : varchar', 'timezone : varchar', 'is_active : boolean')
         ops=@() }
    )
    rel = @(
      @{ d='sucursal'; a='ficha'; cd='1'; ca='0..*'; r='recibe' },
      @{ d='sucursal'; a='agenda'; cd='1'; ca='0..*'; r='tiene' },
      @{ d='sucursal'; a='bloqueo'; cd='0..1'; ca='0..*'; r='se bloquea con' },
      @{ d='agenda'; a='ficha'; cd='0..1'; ca='0..*'; r='genera' },
      @{ d='ficha'; a='pago'; cd='1'; ca='0..*'; r='se paga con' }
    )
    grupos = [ordered]@{ 1 = 'Ver el panel de los últimos 30 días'; 2 = 'Filtrar por sucursal'; 3 = 'Rango o sucursal inválidos' }
    mensajes = @(
      @{ g=1; d='admin'; a='pantalla'; m='abrirKpis()' },
      @{ g=1; d='pantalla'; a='pantalla'; m='rangoPorDefecto()' },
      @{ g=1; d='pantalla'; a='vista'; m='get(request)' },
      @{ g=1; d='vista'; a='vista'; m='_fecha(valor)' },
      @{ g=1; d='vista'; a='calc'; m='calcular(organizacion, desde, hasta, branch_id, ahora)' },
      @{ g=1; d='calc'; a='calc'; m='rango_utc(organizacion, desde, hasta)' },
      @{ g=1; d='calc'; a='ficha'; m='aggregate(estado, sucursal, especialidad)' },
      @{ g=1; d='calc'; a='calc'; m='_espacios_ofrecidos(organizacion, desde, hasta, branch_id)' },
      @{ g=1; d='calc'; a='agenda'; m='filter(is_active, valid_from, valid_until)' },
      @{ g=1; d='calc'; a='bloqueo'; m='filter(starts_at, ends_at)' },
      @{ g=1; d='calc'; a='pago'; m='aggregate(Sum(amount))' },
      @{ g=1; d='vista'; a='pantalla'; m='200(ocupacion, inasistencia, ingresos, demanda)'; ret=$true },
      @{ g=2; d='admin'; a='pantalla'; m='filtrarPorSucursal(branch)' },
      @{ g=2; d='pantalla'; a='vista'; m='get(request)' },
      @{ g=2; d='calc'; a='sucursal'; m='filter(pk, organization)' },
      @{ g=3; d='vista'; a='pantalla'; m='400(code, detail)'; ret=$true }
    )
  }

  # -----------------------------------------------------------------------
  'CU34' = @{
    cu = 'CU34'; nombre = 'Agendamiento mediante Chatbot'; us = 'US-33'
    nota = 'El asistente ofrece horarios reales; tocar uno sólo abre la confirmación y la ficha se crea con la misma reserva de CU18. Si el pedido es una urgencia, deriva a emergencias (CU35) y no ofrece horarios. Web y móvil (PR #84).'
    participantes = @(
      @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2 },
      @{ k='pantalla'; n='PantallaAsistente'; rol='boundary'; col=1; f=2
         nota='Web: frontend/src/api/asistente.ts y la página del asistente. Móvil: mobile/lib/features/assistant/ (assistant_screen.dart, assistant_api.dart) y confirmar_reserva_sheet.dart.'
         atr=@('POST /api/assistant/suggest/ : 200 | 403', 'POST /api/assistant/slots/ : 200 | 400 | 403', 'POST /api/assistant/book/ : 201 | 403 | 409')
         ops=@('escribir(mensaje)', 'elegir(oferta)', 'confirmar()', 'consultarAsistente(mensaje, contexto)', 'pedirTurnos(especialidad, preferencia, contexto)', 'reservarDesdeAsistente(oferta, paciente, contexto)', '_buscarTurnos(pedido)') },
      @{ k='asistente'; n='ControladorAsistente'; rol='control'; col=2; f=0
         nota='SuggestView en assistant/views.py.'
         ops=@('_specialty_for_booking(organization, fragments)', '_emergency_response(generated_by)') },
      @{ k='reserva'; n='ControladorReservaAsistente'; rol='control'; col=2; f=2
         nota='SlotsView y BookView en assistant/booking_views.py.'
         ops=@('_redactar(especialidad, ofertas, alternativa)') },
      @{ k='triage'; n='Triage'; rol='control'; col=2; f=4.2
         nota='assistant/triage.py: reglas que detectan una urgencia antes de cualquier otra cosa.'
         ops=@() },
      @{ k='pref'; n='InterpretePreferencias'; rol='control'; col=3; f=0
         nota='assistant/preferences.py: día, franja y sucursal a partir del texto.'
         ops=@() },
      @{ k='oferta'; n='OfertaTurnos'; rol='control'; col=3; f=1.5
         nota='assistant/offers.py, sobre consolidated_availability de scheduling/availability.py (la misma de CU16).'
         ops=@() },
      @{ k='booking'; n='GestorReserva'; rol='control'; col=3; f=3.2
         nota='appointments/booking.py: la misma reserva de CU18. Lanza SlotAlreadyTaken si otro tomó el horario.'
         ops=@() },
      @{ k='especialidad'; n='Especialidad'; rol='entity'; col=4; f=0
         nota='Tabla specialties.'
         atr=@('id : uuid', 'organization_id : uuid', 'name : varchar', 'is_active : boolean')
         ops=@() },
      @{ k='profesional'; n='Profesional'; rol='entity'; col=4; f=1.2
         nota='Tabla practitioners (con practitioner_specialties).'
         atr=@('id : uuid', 'organization_id : uuid', 'first_name : varchar', 'last_name : varchar', 'license_number : varchar', 'is_active : boolean')
         ops=@() },
      @{ k='agenda'; n='Agenda'; rol='entity'; col=4; f=2.6
         nota='Tabla schedules.'
         atr=@('id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'is_active : boolean')
         ops=@() },
      @{ k='ficha'; n='Ficha'; rol='entity'; col=4; f=4
         nota='Tabla appointments.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'status : varchar', 'expires_at : timestamptz')
         ops=@() },
      @{ k='entpaciente'; n='Paciente'; rol='entity'; col=3; f=4.8
         nota='Tabla patients. Se reserva para el titular o para alguien a su cargo.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid')
         ops=@() }
    )
    rel = @(
      @{ d='profesional'; a='especialidad'; cd='1..*'; ca='1..*'; r='ejerce' },
      @{ d='profesional'; a='agenda'; cd='1'; ca='0..*'; r='atiende según' },
      @{ d='agenda'; a='ficha'; cd='0..1'; ca='0..*'; r='genera' },
      @{ d='entpaciente'; a='ficha'; cd='1'; ca='0..*'; r='reserva' },
      @{ d='entpaciente'; a='entpaciente'; cd='0..1'; ca='0..*'; r='tiene a cargo' }
    )
    grupos = [ordered]@{ 1 = 'Pedir un turno en lenguaje natural'; 2 = 'Ofrecer horarios reales'; 3 = 'Confirmar y reservar'; 4 = 'Urgencia u horario ya tomado' }
    mensajes = @(
      @{ g=1; d='paciente'; a='pantalla'; m='escribir(mensaje)' },
      @{ g=1; d='pantalla'; a='asistente'; m='post(request)' },
      @{ g=1; d='asistente'; a='pref'; m='has_booking_intent(text)' },
      @{ g=1; d='asistente'; a='asistente'; m='_booking_hint(request, question, especialidad)' },
      @{ g=1; d='asistente'; a='especialidad'; m='filter(organization, name)' },
      @{ g=1; d='asistente'; a='pantalla'; m='200(answer, booking)'; ret=$true },
      @{ g=2; d='pantalla'; a='pantalla'; m='_buscarTurnos(pedido)' },
      @{ g=2; d='pantalla'; a='reserva'; m='slots(request)' },
      @{ g=2; d='reserva'; a='triage'; m='check(preference)' },
      @{ g=2; d='reserva'; a='pref'; m='parse(text, today)' },
      @{ g=2; d='reserva'; a='oferta'; m='offer_slots(organization, specialty, preference, branch_id)' },
      @{ g=2; d='oferta'; a='profesional'; m='filter(is_active, specialties)' },
      @{ g=2; d='oferta'; a='agenda'; m='consolidated_availability(practitioner, desde, hasta)' },
      @{ g=2; d='reserva'; a='pref'; m='relaxations(preference, today)' },
      @{ g=2; d='reserva'; a='reserva'; m='_redactar(especialidad, ofertas, alternativa)' },
      @{ g=2; d='reserva'; a='pantalla'; m='200(offers, answer)'; ret=$true },
      @{ g=3; d='paciente'; a='pantalla'; m='elegir(oferta)' },
      @{ g=3; d='paciente'; a='pantalla'; m='confirmar()' },
      @{ g=3; d='pantalla'; a='reserva'; m='book(request)' },
      @{ g=3; d='reserva'; a='entpaciente'; m='filter(titular o a cargo)' },
      @{ g=3; d='reserva'; a='booking'; m='book_appointment(patient, practitioner, starts_at)' },
      @{ g=3; d='booking'; a='ficha'; m='create(status, expires_at)' },
      @{ g=3; d='reserva'; a='pantalla'; m='201(ficha)'; ret=$true },
      @{ g=4; d='reserva'; a='pantalla'; m='_emergency_response(regla)'; ret=$true },
      @{ g=4; d='booking'; a='reserva'; m='SlotAlreadyTaken()'; ret=$true },
      @{ g=4; d='reserva'; a='pantalla'; m='409(detail)'; ret=$true }
    )
  }
}
