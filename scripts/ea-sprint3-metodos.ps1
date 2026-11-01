# =========================================================================
# TODOS los metodos de cada clase de los diagramas de diseno de clase del
# Sprint 3 (pedido de Karen, 01/11/26): no solo los mensajes que recibe, sino
# todo lo que la clase tiene en el codigo. Lo consume
# ea-diseno-clases-completo-sprint3.ps1, que los agrega a las clases que ya
# estan en el eapx sin rehacer los diagramas (las secuencias apuntan a esas
# clases). Clave: caso de uso -> k del participante en ea-sprint3-casos.ps1.
# Primero van las ops y los mensajes que ya estaban, con el mismo texto;
# despues el resto en el orden del codigo. Encima de cada lista, de donde sale.
# CU24 y CU31 no estan aca: sus clases ya traen todos los metodos en
# ea-sprint3-casos-us23-us30.ps1.
# =========================================================================

$METODOS_SPRINT3 = @{}

# Metodos completos de las clases de diseno de CU27 y CU28 (Sprint 3).
# Primero las ops y los mensajes que ya estan en scripts/ea-sprint3-casos.ps1,
# despues el resto en el orden del codigo.

$METODOS_SPRINT3 += @{
  'CU27' = [ordered]@{
    # frontend/src/paginas/RecetaAtencion.tsx:22-177 (fechaHora:22, tieneReceta:26, BotonDescargar:29, bajar:33, Listas:48, PanelReceta:82, ejecutar:90, campo:109, RecetaDeLaAtencion:168)
    # frontend/src/api/atencion.ts:133-202 (solo exportadas: verAgenda:133, abrirAtencion:136, verEncuentro:139, guardarBorrador:142, agregarEnmienda:148, verAntecedentes:154, verHistorial:167)
    'pantalla' = @(
      'enviarMedicamento(datos)', 'enviarOrden(datos)', 'quitar(renglon)', 'firmar()', 'descargarReceta(id)',
      'agregarMedicamento(id, datos, contexto)', 'agregarOrden(id, datos, contexto)', 'quitarMedicamento(id, renglon, contexto)',
      'quitarOrden(id, orden, contexto)', 'firmarEncuentro(id, contexto)',
      'fechaHora(iso)', 'tieneReceta(e)', 'BotonDescargar(encuentro)', 'bajar()', 'Listas(encuentro, quitar)',
      'PanelReceta(encuentro, onCambio)', 'ejecutar(accion, despues)', 'campo(clave, etiqueta, ayuda, obligatorio, max)',
      'RecetaDeLaAtencion(encuentro)',
      'verAgenda(fecha, contexto, senal)', 'abrirAtencion(fichaId, contexto)', 'verEncuentro(id, contexto, senal)',
      'guardarBorrador(id, datos, contexto)', 'agregarEnmienda(id, section, text, contexto)',
      'verAntecedentes(pacienteId, contexto, senal)', 'verHistorial(pacienteId, contexto, senal)'
    )
    # backend/encounters/views.py:62-241 (_own_encounter:62, _audit:77, EncounterChildrenView.post:208, EncounterChildDetailView._child:223, patch:230, delete:238, EncounterSignView.post:169, PrescriptionPdfView.get:264)
    'vista' = @(
      '_own_encounter(request, pk)', '_audit(request, action, encuentro)',
      'post(request, pk, kind)', 'delete(request, pk, child_pk)', 'sign(request, pk)', 'get(request, pk)',
      '_child(encuentro, child_pk)', 'patch(request, pk, child_pk)'
    )
    # backend/encounters/services.py:56-253
    'gestor' = @(
      '_require_draft(encounter)', 'is_own(user, encounter)',
      'add_child(encounter, kind, data)', 'delete_child(encounter, child)', 'sign(encounter, user)',
      'practitioner_of(user)', 'local_today(appointment)', 'appointment_local_date(appointment)',
      'open_encounter(user, appointment)', 'update_draft(encounter, data)', 'amend(encounter, user, section, text)',
      'update_child(encounter, child, data)', 'history_scope(user, patient)'
    )
    # backend/encounters/prescription_pdf.py:34-195 (_local:34, _edad:39, filename:47, render:52)
    'pdf' = @(
      'filename(encounter)', '_edad(nacimiento, dia)',
      'render(encounter)',
      '_local(encounter, momento)'
    )
    # backend/encounters/models.py:128-133 (Encounter.__str__:128, is_signed:132)
    'encuentro' = @(
      'save(status, signed_at, signed_by)', 'select_related(patient, practitioner, branch)',
      '__str__()', 'is_signed()'
    )
    # backend/encounters/models.py:209 (PrescriptionItem.__str__)
    'renglon' = @(
      'create(medication, dose, frequency, duration)', 'delete()', 'prescription_items()',
      '__str__()'
    )
    # backend/encounters/models.py:246 (MedicalOrder.__str__)
    'orden' = @(
      'create(kind, description, notes)', 'orders()',
      '__str__()'
    )
  }
  'CU28' = [ordered]@{
    # frontend/src/paginas/Historial.tsx:9-64 (fecha:9, fechaHora:10, resumenHistorial:13, Historial:21, cargar:29, LineaDeTiempo:64)
    # frontend/src/paginas/RecetaAtencion.tsx:168 (RecetaDeLaAtencion)
    # mobile/lib/features/clinical_record/clinical_record_screen.dart:65-140 (createState:65, client:86, _descargarReceta:90, _cargar:124, _cambiarPersona:140, build:152 y en los widgets privados)
    # mobile/lib/features/clinical_record/clinical_record_api.dart:38-161 (Enmienda.fromJson:38, Medicamento.fromJson:62, Orden.fromJson:83, tieneReceta:118, Atencion.fromJson:120, HistoriaClinica.fromJson:161)
    'pantalla' = @(
      'abrirMiHistoria()', 'cambiarPersona(opcion)', 'descargarReceta(id)', 'verHistorial(pacienteId, contexto)', 'verHistoriaClinica(pacienteId)',
      'fecha(iso)', 'fechaHora(iso)', 'resumenHistorial(datos, vacio)', 'Historial()', 'cargar(signal)', 'LineaDeTiempo(datos)',
      'RecetaDeLaAtencion(encuentro)',
      'createState()', 'client()', '_descargarReceta(atencion)', '_cargar()', '_cambiarPersona(opcion)', 'build(context)',
      'Enmienda.fromJson(json)', 'Medicamento.fromJson(json)', 'Orden.fromJson(json)', 'tieneReceta()',
      'Atencion.fromJson(json)', 'HistoriaClinica.fromJson(json)'
    )
    # backend/encounters/history_views.py:40 (PatientHistoryView.get); backend/encounters/permissions.py:16 (has_permission, heredado por CanReadHistory)
    'vista' = @(
      'has_permission(request, view)',
      'get(request, patient_id)'
    )
    # backend/encounters/services.py:56-253
    'gestor' = @(
      'history_scope(user, patient)',
      'practitioner_of(user)', 'is_own(user, encounter)', 'local_today(appointment)', 'appointment_local_date(appointment)',
      'open_encounter(user, appointment)', 'update_draft(encounter, data)', 'sign(encounter, user)',
      'amend(encounter, user, section, text)', '_require_draft(encounter)', 'add_child(encounter, kind, data)',
      'update_child(encounter, child, data)', 'delete_child(encounter, child)'
    )
    # backend/encounters/views.py:264 (PrescriptionPdfView.get)
    'recetavista' = @(
      'get(request, pk)'
    )
    # backend/encounters/prescription_pdf.py:34-52
    'pdf' = @(
      'filename(encounter)',
      'render(encounter)',
      '_local(encounter, momento)', '_edad(nacimiento, dia)'
    )
    # backend/patients/models.py:128-132 (Patient.__str__:128, full_name:132)
    'entpaciente' = @(
      'filter(user, guardian)',
      '__str__()', 'full_name()'
    )
    # backend/encounters/models.py:128-133
    'encuentro' = @(
      'filter(patient)',
      '__str__()', 'is_signed()'
    )
    # backend/encounters/models.py:209
    'renglon' = @(
      'prefetch(prescription_items)',
      '__str__()'
    )
    # backend/encounters/models.py:246
    'orden' = @(
      'prefetch(orders)',
      '__str__()'
    )
    # backend/encounters/models.py:165 (EncounterAmendment.__str__)
    'enmienda' = @(
      'prefetch(amendments)',
      '__str__()'
    )
  }
}

# Métodos completos de las clases de diseño de CU29 y CU30 (Sprint 3).
# Primero las ops y mensajes que ya estaban en scripts/ea-sprint3-casos.ps1,
# después el resto en el orden del código.

$METODOS_SPRINT3 += @{
  'CU29' = [ordered]@{
    # mobile/lib/core/notifications/push.dart:74 (clase Push; setter :112, iniciar :125, _iniciar :127, registrar :180, _enviar :207, olvidar :228, _mostrarConLaAppAbierta :252, tocarAviso :274, _abrir :276)
    'app' = @('iniciarSesion()', 'cerrarSesion()', 'iniciar()', 'registrar(api)', 'olvidar(api)', 'tocarAviso(appointmentId)', '_mostrarConLaAppAbierta(mensaje)', 'alAbrirFicha(callback)', '_iniciar()', '_enviar(token)', '_abrir(appointmentId)')
    # backend/appointments/management/commands/send_appointment_reminders.py:28 (add_arguments :31, handle :41, _vuelta :68)
    'comando' = @('add_arguments(parser)', '_vuelta()', 'handle()')
    # backend/notifications/views.py:21 (DeviceTokenView: post :24, delete :45)
    'vista' = @('post(request)', 'delete(request)')
    # backend/appointments/reminders.py:42 (due :42, run_for :55, run_due :81)
    'recordatorios' = @('due(now)', 'run_due(now)', 'run_for(organization, now)')
    # backend/notifications/services.py:40 (notify :40, _load :81, _recipient :92, _cuando :98, _push_text :105, _datos :121, _email :130, _devolucion :160)
    'notif' = @('_recipient(appointment)', '_push_text(event, appointment)', '_email(event, appointment)', 'notify(event, appointment_id, organization_id)', '_load(appointment_id)', '_cuando(appointment)', '_datos(appointment)', '_devolucion(appointment)')
    # backend/notifications/push.py:56 (_read_credentials :56, _authorized_session :64, _payload :84, _is_dead :102, send_to_user :119)
    'push' = @('_payload(token, message)', '_is_dead(response)', 'send_to_user(user, message)', '_read_credentials(raw)', '_authorized_session()')
    # backend/notifications/models.py:59 (DeviceToken.__str__) + mensajes ORM de views.py y push.py
    'tokens' = @('update_or_create(token, user, platform)', 'filter(user)', 'delete()', 'filter(token, user).delete()', '__str__()')
    # backend/appointments/models.py:221 (Appointment: __str__ :221, is_active :229) + mensajes de reminders.py y services.py
    'ficha' = @('select_for_update(skip_locked)', '_load(appointment_id)', 'save(reminder_sent_at)', '__str__()', 'is_active()')
    # backend/accounts/models.py:22 (UserManager: _create :27, create_user :35, create_platform_admin :40, create_superuser :47; User: __str__ :134, full_name :138, is_locked :142, permission_codes :146, has_permission :159)
    'usuario' = @('_create(email, password)', 'create_user(email, password, organization)', 'create_platform_admin(email, password)', 'create_superuser(email, password)', '__str__()', 'full_name()', 'is_locked()', 'permission_codes()', 'has_permission(code)')
  }
  'CU30' = [ordered]@{
    # frontend/src/paginas/Kpis.tsx:20 (aIso :20, rangoPorDefecto :22, porcentaje :29, dinero :32, Anillo :36, Barras :54, Kpis :71) + frontend/src/api/kpis.ts:49 (verKpis)
    'pantalla' = @('abrirKpis()', 'filtrarPorSucursal(branch)', 'rangoPorDefecto()', 'verKpis(filtros, contexto)', 'Anillo(tasa, etiqueta, tono)', 'Barras(filas, vacio)', 'aIso(fecha)', 'porcentaje(tasa)', 'dinero(total, moneda)', 'Kpis()')
    # backend/reporting/kpi_views.py:31 (_error :31, _fecha :35, KpiView.get :45)
    'vista' = @('_fecha(valor)', '_error(code, detail)', 'get(request)')
    # backend/appointments/kpis.py:40 (debian_atenderse_q :40, inasistencia_q :48, rango_utc :56, _tasa :64, _espacios_ofrecidos :68, calcular :106)
    'calc' = @('debian_atenderse_q(ahora)', 'inasistencia_q(ahora)', '_tasa(parte, total)', 'calcular(organizacion, desde, hasta, branch_id, ahora)', 'rango_utc(organizacion, desde, hasta)', '_espacios_ofrecidos(organizacion, desde, hasta, branch_id)')
    # backend/appointments/models.py:221 (Appointment: __str__ :221, is_active :229) + mensaje de kpis.py
    'ficha' = @('aggregate(estado, sucursal, especialidad)', '__str__()', 'is_active()')
    # backend/payments/models.py:91 (Payment.__str__) + mensaje de kpis.py
    'pago' = @('aggregate(Sum(amount))', '__str__()')
    # backend/scheduling/models.py:75 (Schedule.__str__) + mensaje de kpis.py
    'agenda' = @('filter(is_active, valid_from, valid_until)', '__str__()')
    # backend/scheduling/models.py:140 (ScheduleBlock.__str__) + mensaje de kpis.py
    'bloqueo' = @('filter(starts_at, ends_at)', '__str__()')
    # backend/catalog/models.py:77 (Branch.__str__) + mensaje de kpi_views.py
    'sucursal' = @('filter(pk, organization)', '__str__()')
  }
}

$METODOS_SPRINT3 += @{
  'CU34' = [ordered]@{
    # frontend/src/api/asistente.ts:105; frontend/src/paginas/Asistente.tsx:94; mobile/lib/features/assistant/assistant_screen.dart:44; mobile/lib/features/assistant/assistant_api.dart:45; mobile/lib/features/appointments/confirmar_reserva_sheet.dart:32
    'pantalla' = @('escribir(mensaje)', 'elegir(oferta)', 'confirmar()', 'consultarAsistente(mensaje, contexto)', 'pedirTurnos(especialidad, preferencia, contexto)', 'reservarDesdeAsistente(oferta, paciente, contexto)', '_buscarTurnos(pedido)',
      'Asistente()', 'enviar(reintento)', 'buscarTurnos(pedido, controlHeredado, textoPaciente)', 'reintentarTurnos(pedido)', 'cerrarModal()', 'confirmarReserva(patientId)', 'alEnviar(evento)', 'alPresionar(evento)', 'derivacion(mensaje)', 'motivoDelFallo(fallo)', 'Bienvenida(alElegir)', 'BurbujaPaciente(texto)', 'Burbuja(children)', 'BurbujaAsistente(respuesta, alVerHorarios, ocupado)', 'fechaYHora(iso)', 'BurbujaTurnos(respuesta, ocupado, alElegir, alPedirOtro)', 'pedirOtro(evento)', 'BurbujaReservada(ficha)', 'AlertaEmergencia(mensaje)', 'BurbujaError(motivo, alReintentar)', 'Pensando()', 'IconoEnviar()', 'IconoConversacion()',
      'createState()', 'esAviso()', 'esError()', 'esPaciente()', 'client()', 'dispose()', '_enviar(reintento)', '_elegir(oferta, pedido)', '_reintentar(turno)', '_motivo(error)', '_bajar()', 'build(context)', '_buscarOtro()',
      'fromJson(json)', 'puedeReservar()', 'inicio()', '_first(json, keys)', '_texto(value)', '_firstString(json, keys)', '_respuestaDeEjemplo(mensaje)', '_turnosDeEjemplo(specialtyId)')
    # backend/assistant/views.py:51
    'asistente' = @('_specialty_for_booking(organization, fragments)', '_emergency_response(generated_by)', 'post(request)', '_booking_hint(request, question, especialidad)', '_administrativa(request, question, fragments, booking)', '_audit(request, emergency_layer, specialty_suggested, kind)')
    # backend/assistant/booking_views.py:52
    'reserva' = @('_redactar(especialidad, ofertas, alternativa)', 'slots(request)', 'book(request)', '_sin_organizacion()', 'post(request)')
    # backend/assistant/triage.py:231
    'triage' = @('check(preference)')
    # backend/assistant/preferences.py:58
    'pref' = @('has_booking_intent(text)', 'parse(text, today)', 'relaxations(preference, today)', 'is_empty()', 'accepts(start)', 'as_dict()', '_next_weekday(today, weekday)', '_week_of(day)')
    # backend/assistant/offers.py:35; backend/scheduling/availability.py:102
    'oferta' = @('offer_slots(organization, specialty, preference, branch_id)', 'consolidated_availability(practitioner_id, date_from, date_to, branch_id, now)')
    # backend/appointments/booking.py:53
    'booking' = @('book_appointment(patient, practitioner, starts_at)', '_validate_slot_is_real(schedule, starts_at)', 'get_permissions()', 'get_queryset()', 'create(request)')
    # backend/catalog/models.py:124
    'especialidad' = @('filter(organization, name)', '__str__()')
    # backend/catalog/models.py:157
    'profesional' = @('filter(is_active, specialties)', '__str__()', 'full_name()', 'save()')
    # backend/scheduling/models.py:17
    'agenda' = @('consolidated_availability(practitioner, desde, hasta)', '__str__()')
    # backend/appointments/models.py:20
    'ficha' = @('create(status, expires_at)', '__str__()', 'is_active()')
    # backend/patients/models.py:18
    'entpaciente' = @('filter(titular o a cargo)', '__str__()', 'full_name()')
  }
}
