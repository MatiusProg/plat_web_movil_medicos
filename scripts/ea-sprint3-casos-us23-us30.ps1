# =========================================================================
# Datos de CU24 (US-23) y CU31 (US-30) despues del pull del 01/11/26.
#
# Se cargan con dot-sourcing DESPUES de ea-sprint3-casos.ps1 (los de Mateo):
#   - CU24 se reemplaza entero. Al 26/10 sólo existía el cobro en efectivo
#     (PR #80); con el PR #87 la recepción busca o registra al paciente,
#     reserva a su nombre (POST /api/appointments/counter/book/), cobra en
#     efectivo y registra la llegada por documento, todo en Mostrador.tsx.
#   - CU31 entra nuevo: con el PR #89 el constructor de reportes tiene los
#     conjuntos de fichas y de pagos (reporting/datasets.py).
# El formato es el de ea-sprint3-casos.ps1. Cada clase lleva TODOS sus
# metodos del codigo (pedido de Karen del 01/11), no solo los mensajes.
# =========================================================================

# ---- metodos compartidos (mismo modulo en los dos casos de uso) ------------
$OPS_PLANES = @('current_plan(organization)', '_sin_plan()', 'require_feature(organization, feature, que)',
  'check_limit(organization, field, usados, que, singular)', '_inicio_de_mes()', 'staff_count(organization)',
  '_staff_queryset(organization)', 'is_staff_member(organization, user)', 'appointments_this_month(organization)',
  'ai_queries_this_month(organization)')
$OPS_BITACORA = @('client_ip(request)', 'user_agent(request)', 'record(request, action, entity, entity_id, detail, organization, user)',
  '_http_request(request)', 'flush(request)', '_write(entry)', '_usuario_de(request)', '_organization_id(organization, autor)')
$ATR_FICHA = @('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'practitioner_id : uuid',
  'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar',
  'checked_in_at : timestamptz', 'expires_at : timestamptz', 'cancelled_at : timestamptz', 'created_at : timestamptz')
$ATR_PAGO = @('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'created_by_id : uuid', 'amount : numeric(10,2)',
  'currency : varchar(3)', 'provider : varchar(12)', 'status : varchar', 'paid_at : timestamptz', 'refunded_at : timestamptz',
  'refund_reason : varchar')
$ATR_BITACORA = @('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar',
  'entity_id : varchar', 'detail : jsonb', 'occurred_at : timestamptz')

# -------------------------------------------------------------------------
$CASOS_SPRINT3['CU24'] = @{
  cu = 'CU24'; nombre = 'Agendamiento y Cobro Asistido'; us = 'US-23'
  nota = 'La recepción atiende en el mostrador (Mostrador.tsx, PR #87): busca o registra al paciente, le reserva un turno real a su nombre, lo cobra en efectivo y registra su llegada por documento. La reserva es la misma book_appointment de CU18 y el cobro el mismo confirm_payment del pago en línea.'
  participantes = @(
    @{ k='recep'; n='Recepcionista'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaMostrador'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Mostrador.tsx (ruta /mostrador) y frontend/src/api/mostrador.ts; usa buscarPacientes y crearPaciente (api/pacientes.ts), listarProfesionalesTodos (api/catalogo.ts), disponibilidadConsolidada (api/disponibilidad.ts) y realizarCheckIn (api/fichas.ts). Sólo se ve con appointments.appointment.book_at_counter.'
       atr=@('busqueda : string', 'paciente : string', 'profesional : string', 'dia : string', 'espacio : Espacio', 'ficha : Ficha', 'documento : string', 'ocupado : boolean')
       ops=@('Mostrador()', 'fechaLocal(dias)', 'errorTexto(e)', 'ejecutar(accion)', 'reservarEnMostrador(datos, contexto)', 'cobrarEnMostrador(id, contexto)',
             'buscarPacientes(filtros, contexto, senal)', 'crearPaciente(datos, contexto)', 'listarProfesionalesTodos(contexto, senal)',
             'disponibilidadConsolidada(parametros, contexto, senal)', 'realizarCheckIn(datos, contexto)') },
    @{ k='busq'; n='ControladorBusquedaPacientes'; rol='control'; col=2; f=0
       nota='PatientSearchViewSet en patients/search.py (GET /api/patients/search/).'
       ops=@('organization()', 'get_serializer_class()', 'get_queryset()', 'retrieve(request, pk)', 'normalizar(texto)') },
    @{ k='alta'; n='ControladorAltaPaciente'; rol='control'; col=2; f=1
       nota='PatientAdminViewSet y PatientAdminSerializer en patients/admin_ops.py (POST /api/patients/admin/).'
       ops=@('get_queryset()', 'get_permissions()', 'perform_create(serializer)', 'perform_update(serializer)', 'destroy(request, pk)', 'merge(request)',
             'validate_document_number(value)', 'validate(attrs)') },
    @{ k='disp'; n='ControladorDisponibilidad'; rol='control'; col=2; f=2
       nota='AvailabilityView en scheduling/availability.py (GET /api/scheduling/availability/).'
       ops=@('get(request)', '_parse_date(value)') },
    @{ k='gdisp'; n='GestorDisponibilidad'; rol='control'; col=2; f=3
       nota='Las funciones de scheduling/availability.py: la misma disponibilidad de CU16.'
       ops=@('_daterange(date_from, date_to)', 'slot_starts(start, end, step_minutes)', '_booked_slots(practitioner_id, date_from, date_to)',
             'generate_slots(schedule, date_from, date_to, tz)', '_blocked(start_aware, end_aware, blocks)',
             'consolidated_availability(practitioner_id, date_from, date_to, branch_id, now)', 'next_available_slot(practitioner_id, now, horizon_days)') },
    @{ k='ctrlres'; n='ControladorReservaMostrador'; rol='control'; col=2; f=4
       nota='CounterBookingView y CanBookAtCounter en appointments/counter.py (POST /api/appointments/counter/book/). Pide appointments.appointment.book_at_counter.'
       ops=@('post(request)', 'has_permission(request, view)') },
    @{ k='planes'; n='GestorPlanes'; rol='control'; col=2; f=5
       nota='tenancy/plans.py: el tope de fichas por mes del plan.'
       ops=$OPS_PLANES },
    @{ k='reserva'; n='GestorReserva'; rol='control'; col=2; f=6
       nota='appointments/booking.py: la misma reserva de CU18. Lanza SlotAlreadyTaken si otro tomó el turno.'
       ops=@('_validate_slot_is_real(schedule, starts_at)', 'book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)',
             'get_permissions()', 'get_queryset()', 'create(request)') },
    @{ k='vista'; n='ControladorCobroVentanilla'; rol='control'; col=2; f=7
       nota='CashPaymentView en payments/views.py (POST /api/payments/appointments/{id}/cash/). Pide payments.payment.register_cash.'
       ops=@('post(request, pk)') },
    @{ k='gestor'; n='GestorPagos'; rol='control'; col=2; f=8
       nota='payments/services.py.'
       ops=@('_assert_payable(appointment)', 'start_checkout(appointment, user, request, return_to)', 'confirm_payment(payment, provider_payment_id, request)',
             'register_cash_payment(appointment, user, request)', 'refund_payment(payment, reason, request)', 'refund_for_cancellation(appointment, request)',
             'transfer_payment(origen, destino, request)', '_asentar(request, payment, evento)') },
    @{ k='tarifa'; n='GestorTarifas'; rol='control'; col=2; f=9
       nota='payments/pricing.py: el importe lo decide el servidor, nunca la recepción.'
       ops=@('_mas_barato(servicios)', 'quote(appointment)') },
    @{ k='checkin'; n='ControladorCheckIn'; rol='control'; col=2; f=10
       nota='CheckInView y CheckInSerializer en appointments/checkin.py (POST /api/appointments/checkin/), la misma de CU22.'
       ops=@('post(request)', '_find_by_document(organization, document_number)', '_find_by_qr(organization, qr_code)', 'validate(attrs)') },
    @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=11
       nota='audit/services.py.'
       ops=$OPS_BITACORA },
    @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=0
       nota='Tabla patients.'
       atr=@('id : uuid', 'organization_id : uuid', 'document_type : varchar', 'document_number : varchar', 'first_name : varchar', 'last_name : varchar', 'phone : varchar', 'is_active : boolean')
       ops=@('__str__()', 'full_name()') },
    @{ k='agenda'; n='Agenda'; rol='entity'; col=3; f=2
       nota='Tabla schedules.'
       atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'is_active : boolean')
       ops=@('__str__()') },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=4
       nota='Tabla appointments. Nace pending_payment y vence a los APPOINTMENT_HOLD_MINUTES.'
       atr=$ATR_FICHA
       ops=@('__str__()', 'is_active()') },
    @{ k='pago'; n='Pago'; rol='entity'; col=3; f=7
       nota='Tabla payments. provider = cash para el cobro en ventanilla.'
       atr=$ATR_PAGO
       ops=@('__str__()') },
    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=9
       nota='Tabla audit_log.'
       atr=$ATR_BITACORA
       ops=@('__str__()') }
  )
  rel = @(
    @{ d='paciente'; a='ficha'; cd='1'; ca='0..*'; r='reserva' },
    @{ d='agenda'; a='ficha'; cd='1'; ca='0..*'; r='ofrece' },
    @{ d='ficha'; a='pago'; cd='1'; ca='0..*'; r='se paga con' }
  )
  grupos = [ordered]@{ 1 = 'Reservar a nombre del paciente'; 2 = 'Registrar un paciente nuevo'; 3 = 'Cobrar en efectivo'; 4 = 'Registrar la llegada'; 5 = 'El turno o la ficha no sirven' }
  mensajes = @(
    @{ g=1; d='recep'; a='pantalla'; m='buscarPaciente(texto)' },
    @{ g=1; d='pantalla'; a='busq'; m='list(request)' },
    @{ g=1; d='busq'; a='busq'; m='get_queryset()' },
    @{ g=1; d='busq'; a='paciente'; m='filter(organization, q, status)' },
    @{ g=1; d='busq'; a='pantalla'; m='200(results)'; ret=$true },
    @{ g=1; d='recep'; a='pantalla'; m='elegirTurno(profesional, dia)' },
    @{ g=1; d='pantalla'; a='disp'; m='get(request)' },
    @{ g=1; d='disp'; a='gdisp'; m='consolidated_availability(practitioner_id, date_from, date_to, branch_id, now)' },
    @{ g=1; d='gdisp'; a='agenda'; m='filter(practitioner, is_active)' },
    @{ g=1; d='gdisp'; a='gdisp'; m='_booked_slots(practitioner_id, date_from, date_to)' },
    @{ g=1; d='gdisp'; a='ficha'; m='filter(practitioner, status, starts_at)' },
    @{ g=1; d='disp'; a='pantalla'; m='200(days, slots)'; ret=$true },
    @{ g=1; d='recep'; a='pantalla'; m='reservar()' },
    @{ g=1; d='pantalla'; a='ctrlres'; m='post(request)' },
    @{ g=1; d='ctrlres'; a='planes'; m='appointments_this_month(organization)' },
    @{ g=1; d='ctrlres'; a='planes'; m='check_limit(organization, field, usados, que, singular)' },
    @{ g=1; d='ctrlres'; a='reserva'; m='book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)' },
    @{ g=1; d='reserva'; a='paciente'; m='filter(pk, organization, is_active)' },
    @{ g=1; d='reserva'; a='agenda'; m='select_for_update(pk, organization, branch, practitioner)' },
    @{ g=1; d='reserva'; a='reserva'; m='_validate_slot_is_real(schedule, starts_at)' },
    @{ g=1; d='reserva'; a='ficha'; m='create(patient, practitioner, branch, schedule, starts_at, status, expires_at)' },
    @{ g=1; d='ctrlres'; a='pantalla'; m='201(ficha pending_payment)'; ret=$true },
    @{ g=2; d='recep'; a='pantalla'; m='registrarPaciente(datos)' },
    @{ g=2; d='pantalla'; a='alta'; m='create(request)' },
    @{ g=2; d='alta'; a='alta'; m='validate(attrs)' },
    @{ g=2; d='alta'; a='alta'; m='perform_create(serializer)' },
    @{ g=2; d='alta'; a='paciente'; m='create(datos, organization)' },
    @{ g=2; d='alta'; a='pantalla'; m='201(paciente)'; ret=$true },
    @{ g=3; d='recep'; a='pantalla'; m='confirmarCobro()' },
    @{ g=3; d='pantalla'; a='vista'; m='post(request, pk)' },
    @{ g=3; d='vista'; a='ficha'; m='filter(pk, organization)' },
    @{ g=3; d='vista'; a='gestor'; m='register_cash_payment(appointment, user, request)' },
    @{ g=3; d='gestor'; a='gestor'; m='_assert_payable(appointment)' },
    @{ g=3; d='gestor'; a='tarifa'; m='quote(appointment)' },
    @{ g=3; d='gestor'; a='pago'; m='create(appointment, amount, currency, provider)' },
    @{ g=3; d='gestor'; a='gestor'; m='_asentar(request, payment, evento)' },
    @{ g=3; d='gestor'; a='bitgestor'; m='record(request, action, entity, entity_id, detail, organization, user)' },
    @{ g=3; d='gestor'; a='gestor'; m='confirm_payment(payment, provider_payment_id, request)' },
    @{ g=3; d='gestor'; a='pago'; m='save(status, paid_at)' },
    @{ g=3; d='gestor'; a='ficha'; m='save(status, expires_at)' },
    @{ g=3; d='vista'; a='pantalla'; m='201(payment_id, amount, appointment)'; ret=$true },
    @{ g=3; d='bitgestor'; a='bitacora'; m='insert(asiento)' },
    @{ g=4; d='recep'; a='pantalla'; m='registrarLlegada(documento)' },
    @{ g=4; d='pantalla'; a='checkin'; m='post(request)' },
    @{ g=4; d='checkin'; a='checkin'; m='_find_by_document(organization, document_number)' },
    @{ g=4; d='checkin'; a='ficha'; m='select_for_update(organization, document_number)' },
    @{ g=4; d='checkin'; a='ficha'; m='save(status, checked_in_at)' },
    @{ g=4; d='checkin'; a='pantalla'; m='200(id, status, checked_in_at)'; ret=$true },
    @{ g=5; d='reserva'; a='ctrlres'; m='SlotAlreadyTaken(detail)'; ret=$true },
    @{ g=5; d='ctrlres'; a='pantalla'; m='409(turno_ocupado, detail)'; ret=$true },
    @{ g=5; d='gestor'; a='vista'; m='ValidationError(code)'; ret=$true },
    @{ g=5; d='vista'; a='pantalla'; m='400(code, detail)'; ret=$true }
  )
}

# -------------------------------------------------------------------------
$cu31 = @{
  cu = 'CU31'; nombre = 'Generación de Reportes'; us = 'US-30'
  nota = 'Reportes operativos de fichas y de pagos (PR #89) en el constructor de reportes de la característica 5: se arman, se ven en pantalla y se exportan a PDF o Excel. Los dos conjuntos piden reporting.kpi.read, el permiso del panel de CU30, y la asistencia se calcula con los mismos filtros del panel.'
  participantes = @(
    @{ k='admin'; n='Administrador de Organización'; rol='actor'; col=0; f=2 },
    @{ k='pantalla'; n='PantallaReportes'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Reportes.tsx (ruta /reportes) y frontend/src/api/reportes.ts. El catálogo se dibuja solo desde GET /api/reporting/datasets/: la pantalla no cambió con US-30.'
       atr=@('catalogo : CatalogoDeReportes', 'conjunto : ConjuntoDeDatos', 'columnas : string[]', 'criterios : CriterioDeFiltro[]', 'orden : string[]', 'vista : VistaPrevia', 'trabajando : boolean')
       ops=@('valorInicial(campo)', 'Reportes()', 'elegirConjunto(elegido)', 'aplicar(propuesta)', 'dictado(texto)', 'previsualizarAhora()', 'exportarAhora(formato)',
             'SeccionVoz(voz, trabajando, interpretacion)', 'Columnas(conjunto, elegidas, onCambiar, orden, onOrden)', 'alternar(codigo)', 'rotarOrden(codigo)',
             'marcaDeOrden(codigo)', 'Criterios(conjunto, criterios, onCambiar)', 'agregar()', 'cambiar(indice, cambios)', 'ValorDeCriterio(campo, valor, onCambiar)',
             'Resultado(vista, maximo)', 'listarConjuntos(contexto, senal)', 'previsualizar(definicion, contexto, senal)', 'interpretarPorVoz(texto, dataset, contexto, senal)',
             'enviarPorCorreo(definicion, destinatarios, titulo, contexto)', 'exportar(definicion, formato, titulo, contexto)') },
    @{ k='catvista'; n='ControladorCatalogoReportes'; rol='control'; col=2; f=0
       nota='DatasetListView en reporting/views.py (GET /api/reporting/datasets/). Pide reporting.report.run.'
       ops=@('get(request)') },
    @{ k='run'; n='ControladorEjecucionReporte'; rol='control'; col=2; f=1
       nota='RunReportView y las funciones _run, _subtitulo, _cuerpo_del_correo y _audit_run de reporting/views.py (POST /api/reporting/run/).'
       ops=@('post(request)', '_run(request, datos, saved_report)', '_subtitulo(report, definicion)', '_cuerpo_del_correo(user, titulo, filas, truncado)',
             '_audit_run(request, report, definicion, formato, filas, saved_report, recipients)') },
    @{ k='catalogo'; n='CatalogoConjuntos'; rol='control'; col=2; f=2
       nota='reporting/datasets.py: la clase Dataset y el registro. US-30 agregó APPOINTMENTS y PAYMENTS, con permission = reporting.kpi.read.'
       ops=@('column(code)', 'filter(code)', 'base_queryset(user)', '_by_code(items, code)', '_labels(choices_class)', '_fichas_con_asistencia(objects, organization)',
             'get(code)', 'available_for(user)') },
    @{ k='query'; n='ConstructorReporte'; rol='control'; col=2; f=3
       nota='reporting/query.py: build y la clase Report. US-30 hizo que rows() lleve la clave primaria en el SELECT, para una fila por ficha o pago.'
       ops=@('headers()', 'rows(limit)', 'build(definition, user)', '_columns(dataset, pedidas)', '_apply_filters(queryset, dataset, criterios)', '_coerce(filtro, valor)',
             '_order(dataset, pedido)', '_format(columna, valor)') },
    @{ k='kpis'; n='CalculadoraKpis'; rol='control'; col=2; f=4
       nota='appointments/kpis.py: los mismos filtros del panel de CU30, para que la asistencia del reporte coincida con él.'
       ops=@('debian_atenderse_q(ahora)', 'inasistencia_q(ahora)', 'rango_utc(organizacion, desde, hasta)', '_tasa(parte, total)',
             '_espacios_ofrecidos(organizacion, desde, hasta, branch_id)', 'calcular(organizacion, desde, hasta, branch_id, ahora)') },
    @{ k='planes'; n='GestorPlanes'; rol='control'; col=2; f=5
       nota='tenancy/plans.py: llevarse el archivo pide report_export en el plan; verlo en pantalla, no.'
       ops=$OPS_PLANES },
    @{ k='export'; n='ExportadorReportes'; rol='control'; col=2; f=6
       nota='reporting/exporters.py. US-30: el importe llega al Excel como número con formato #,##0.00 y los instantes en la hora de La Paz.'
       ops=@('export(fmt, headers, rows, title, subtitle, truncated)', 'slugify(texto)', '_pie(truncated, filas)', '_csv(headers, rows, title, subtitle, truncated)',
             '_xlsx(headers, rows, title, subtitle, truncated)', '_excel_value(valor)', '_html(headers, rows, title, subtitle, truncated)',
             '_pdf(headers, rows, title, subtitle, truncated)', '_anchos_de_columna(headers, rows, disponible)', '_pie_de_pagina(texto)') },
    @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=7
       nota='audit/services.py. Se asienta quién sacó qué y cuántas filas, nunca las filas.'
       ops=$OPS_BITACORA },
    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=1
       nota='Tabla appointments, con sus pacientes, profesionales, especialidades y sucursales por join.'
       atr=$ATR_FICHA
       ops=@('__str__()', 'is_active()') },
    @{ k='pago'; n='Pago'; rol='entity'; col=3; f=4
       nota='Tabla payments, en línea y en ventanilla.'
       atr=$ATR_PAGO
       ops=@('__str__()') },
    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=7
       nota='Tabla audit_log. action = report.run.'
       atr=$ATR_BITACORA
       ops=@('__str__()') }
  )
  rel = @(
    @{ d='ficha'; a='pago'; cd='1'; ca='0..*'; r='se paga con' }
  )
  grupos = [ordered]@{ 1 = 'Elegir el conjunto'; 2 = 'Ver el reporte en pantalla'; 3 = 'Exportar a PDF o Excel'; 4 = 'Sin permiso o sin exportación en el plan' }
  mensajes = @(
    @{ g=1; d='admin'; a='pantalla'; m='abrirReportes()' },
    @{ g=1; d='pantalla'; a='catvista'; m='get(request)' },
    @{ g=1; d='catvista'; a='catalogo'; m='available_for(user)' },
    @{ g=1; d='catvista'; a='pantalla'; m='200(datasets, formats, max_rows)'; ret=$true },
    @{ g=1; d='admin'; a='pantalla'; m='elegirConjunto(elegido)' },
    @{ g=2; d='admin'; a='pantalla'; m='previsualizarAhora()' },
    @{ g=2; d='pantalla'; a='run'; m='post(request)' },
    @{ g=2; d='run'; a='run'; m='_run(request, datos, saved_report)' },
    @{ g=2; d='run'; a='query'; m='build(definition, user)' },
    @{ g=2; d='query'; a='catalogo'; m='get(code)' },
    @{ g=2; d='query'; a='query'; m='_columns(dataset, pedidas)' },
    @{ g=2; d='query'; a='catalogo'; m='base_queryset(user)' },
    @{ g=2; d='catalogo'; a='catalogo'; m='_fichas_con_asistencia(objects, organization)' },
    @{ g=2; d='catalogo'; a='kpis'; m='inasistencia_q(ahora)' },
    @{ g=2; d='catalogo'; a='kpis'; m='debian_atenderse_q(ahora)' },
    @{ g=2; d='query'; a='query'; m='_apply_filters(queryset, dataset, criterios)' },
    @{ g=2; d='query'; a='query'; m='_order(dataset, pedido)' },
    @{ g=2; d='run'; a='query'; m='rows(limit)' },
    @{ g=2; d='query'; a='ficha'; m='values_list(paths, pk)' },
    @{ g=2; d='query'; a='pago'; m='values_list(paths, pk)' },
    @{ g=2; d='run'; a='run'; m='_audit_run(request, report, definicion, formato, filas, saved_report, recipients)' },
    @{ g=2; d='run'; a='bitgestor'; m='record(request, action, entity, entity_id, detail, organization, user)' },
    @{ g=2; d='bitgestor'; a='bitacora'; m='insert(asiento)' },
    @{ g=2; d='run'; a='pantalla'; m='200(columns, rows, truncated)'; ret=$true },
    @{ g=3; d='admin'; a='pantalla'; m='exportarAhora(formato)' },
    @{ g=3; d='pantalla'; a='run'; m='post(request)' },
    @{ g=3; d='run'; a='run'; m='_run(request, datos, saved_report)' },
    @{ g=3; d='run'; a='query'; m='build(definition, user)' },
    @{ g=3; d='run'; a='planes'; m='require_feature(organization, feature, que)' },
    @{ g=3; d='run'; a='query'; m='rows(limit)' },
    @{ g=3; d='run'; a='run'; m='_subtitulo(report, definicion)' },
    @{ g=3; d='run'; a='export'; m='export(fmt, headers, rows, title, subtitle, truncated)' },
    @{ g=3; d='export'; a='export'; m='_xlsx(headers, rows, title, subtitle, truncated)' },
    @{ g=3; d='export'; a='export'; m='_excel_value(valor)' },
    @{ g=3; d='export'; a='export'; m='_pdf(headers, rows, title, subtitle, truncated)' },
    @{ g=3; d='export'; a='export'; m='slugify(texto)' },
    @{ g=3; d='run'; a='run'; m='_audit_run(request, report, definicion, formato, filas, saved_report, recipients)' },
    @{ g=3; d='run'; a='pantalla'; m='200(archivo, Content-Disposition, X-Report-Rows)'; ret=$true },
    @{ g=4; d='query'; a='run'; m='PermissionError(permission)'; ret=$true },
    @{ g=4; d='run'; a='pantalla'; m='403(sin_permiso_sobre_el_conjunto, detail)'; ret=$true },
    @{ g=4; d='planes'; a='run'; m='PlanLimitExceeded(detail)'; ret=$true },
    @{ g=4; d='run'; a='pantalla'; m='403(plan_limit, detail)'; ret=$true }
  )
}
# CU31 va despues de CU30, en el orden de los casos de uso.
$pos = @($CASOS_SPRINT3.Keys).IndexOf('CU30') + 1
if (-not $CASOS_SPRINT3.Contains('CU31')) { $CASOS_SPRINT3.Insert($pos, 'CU31', $cu31) }
