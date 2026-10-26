# =========================================================================
# Datos de los diagramas de NAVEGACION del Sprint 3 (ea-navegacion-sprint3.ps1).
#
# Dos niveles, con la web y el movil juntos (decision de Karen, 26/10/2026):
#   'Sistema'  todas las pantallas con codigo, una columna por subsistema.
#              Solo pantallas y rutas.
#   'P5'..'P8' los subsistemas del Sprint 3, con formularios y controladores.
#
# Fuente: frontend/src/App.tsx y BarraPlataforma.tsx (web);
# mobile/lib/core/router/app_router.dart, patient_gate.dart, org_gate.dart y
# los drawers (movil); backend/*/urls.py para los controladores.
#
# ---- formato ----
#   titulo, nota, disposicion ('columnas' para el del sistema)
#   actores  nombres de actores del 1.3 del Sprint 3 (Usuario es el abstracto:
#            de el cuelgan las pantallas publicas)
#   menus    @{ k; n; ruta; guarda; actores } o, para un menu al que se llega
#            desde otro, @{ k; n; ruta; desde = <k del otro menu>; guardaDesde }
#   controladores  k -> @{ n = archivo del backend; ops = funciones exactas }
#   bandas   @{ titulo; pantallas = @( pantalla ) }
#   pantalla @{ n = archivo o clase; ruta; guarda; atr; ctrl (uno o lista);
#               forms = @( @{ n; atr; ctrl; tipo; ruta } ) }
#            y de donde cuelga: menu = <k>, o desde = <pantalla, formulario o
#            menu, uno o lista>, o actor = <actor> (publicas, sin sesion).
#   Una pantalla que sale en dos diagramas es el MISMO elemento: si lleva
#   atributos, que sean los mismos en los dos.
# =========================================================================

$WEB_ROLES = @('Paciente', 'Médico', 'Recepcionista', 'Administrador de Organización', 'Superadministrador de Plataforma')

$NAVEGACION_SPRINT3 = [ordered]@{

  # =======================================================================
  'Sistema' = @{
    titulo = 'Sistema'
    disposicion = 'columnas'
    nota = 'Navegación del sistema completo, web y móvil juntas, al 26/10/2026: todas las pantallas que tienen código, una columna por subsistema (P1 a P8; P9 y P10 todavía no tienen pantallas). Sólo pantallas y rutas: los formularios y los controladores de cada pantalla están en los diagramas de subsistema. No es UML: es la extensión UWE (diagrama de clases con estereotipos de navegación). Web: rutas de frontend/src/App.tsx; toda ruta protegida pasa por RutaProtegida (sesión) y cuelga de BarraPlataforma.tsx, cuyas entradas aparecen según el permiso que dice cada guarda (BarraPlataforma.tsx:343-351). Móvil: rutas de mobile/lib/core/router/app_router.dart; la sesión la pide el redirect (:116-132), SoloPacientes (patient_gate.dart:16) y ConPermiso (org_gate.dart:64). Las guardas de la interfaz son cosméticas: la puerta real es el permiso del backend. Sólo web: recuperar contraseña, servicios, pacientes, bloqueos, check-in, atención médica y KPIs. Sólo móvil: dependientes, antecedentes y comprobantes guardados.'
    actores = @('Usuario') + $WEB_ROLES
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=$WEB_ROLES },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=$WEB_ROLES },
      @{ k='org';  n='OrganizationDrawer'; ruta='/org'; desde='movil'; guardaDesde='[alguna sección de la organización]' },
      @{ k='plat'; n='PlatformDrawer'; ruta='/platform/dashboard'; desde='movil'; guardaDesde='[isPlatformAdmin]' }
    )
    controladores = @{}
    bandas = @(
      @{ titulo='P2 Usuarios y Seguridad'; pantallas=@(
          @{ n='InicioSesion.tsx'; ruta='/ingresar'; actor='Usuario' },
          @{ n='RecuperarAcceso.tsx'; ruta='/recuperar'; desde='InicioSesion.tsx' },
          @{ n='RestablecerContrasena.tsx'; ruta='/restablecer'; desde='RecuperarAcceso.tsx'; guarda='[enlace del correo]' },
          @{ n='RegistroPaciente.tsx'; ruta='/registro'; desde='InicioSesion.tsx' },
          @{ n='SignInScreen'; ruta='/sign-in'; actor='Usuario' },
          @{ n='RegisterScreen'; ruta='/register'; desde='SignInScreen' },
          @{ n='Roles.tsx'; ruta='/roles'; menu='web'; guarda='[users.role.read]' },
          @{ n='Usuarios.tsx'; ruta='/usuarios'; menu='web'; guarda='[users.user.read]' },
          @{ n='Bitacora.tsx'; ruta='/bitacora'; menu='web'; guarda='[audit.log.read]' },
          @{ n='Perfil.tsx'; ruta='/perfil'; menu='web' },
          @{ n='RolesScreen'; ruta='/org/roles'; menu='org'; guarda='[users.role.read]' },
          @{ n='UsersScreen'; ruta='/org/usuarios'; menu='org'; guarda='[users.user.read]' },
          @{ n='AuditScreen'; ruta='/org/bitacora'; menu='org'; guarda='[audit.log.read]' },
          @{ n='ProfileScreen'; ruta='/profile'; menu='movil' }
      ) },
      @{ titulo='P1 Gestión Multi-Tenant (y el Panel)'; pantallas=@(
          @{ n='Panel.tsx'; ruta='/panel'; menu='web' },
          @{ n='Organizaciones.tsx'; ruta='/organizaciones'; menu='web'; guarda='[is_platform_admin]' },
          @{ n='AltaOrganizacion.tsx'; ruta='/organizaciones/nueva'; desde='Organizaciones.tsx' },
          @{ n='Planes.tsx'; ruta='/planes'; menu='web'; guarda='[is_platform_admin]' },
          @{ n='Suscripciones.tsx'; ruta='/suscripciones'; menu='web'; guarda='[is_platform_admin]' },
          @{ n='HistorialSuscripcion.tsx'; ruta='/suscripciones/:organizationId/historial'; desde='Suscripciones.tsx' },
          @{ n='PlatformDashboardScreen'; ruta='/platform/dashboard'; menu='plat' },
          @{ n='OrganizationsScreen'; ruta='/platform/organizations'; menu='plat' },
          @{ n='RegisterOrganizationScreen'; ruta='/platform/organizations/new'; desde='OrganizationsScreen' },
          @{ n='PlansScreen'; ruta='/platform/plans'; menu='plat' },
          @{ n='PlanFormScreen'; ruta='/platform/plans/new'; desde='PlansScreen' },
          @{ n='EditarPlanPorId'; ruta='/platform/plans/:id/edit'; desde='PlansScreen' },
          @{ n='SubscriptionsScreen'; ruta='/platform/subscriptions'; menu='plat' },
          @{ n='ChangePlanScreen'; ruta='/platform/subscriptions/change'; desde='SubscriptionsScreen' },
          @{ n='SubscriptionHistoryScreen'; ruta='/platform/organizations/:id/subscriptions'; desde='SubscriptionsScreen' }
      ) },
      @{ titulo='P3 Gestión de Pacientes'; pantallas=@(
          @{ n='Pacientes.tsx'; ruta='/pacientes'; menu='web'; guarda='[patients.patient.read]' },
          @{ n='DependentsScreen'; ruta='/dependents'; menu='movil'; guarda='[SoloPacientes]' },
          @{ n='DependentFormScreen'; ruta='/dependents/new'; desde='DependentsScreen' },
          @{ n='HistoryScreen'; ruta='/history'; menu='movil'; guarda='[SoloPacientes]' }
      ) },
      @{ titulo='P4 Catálogo Médico y Agendas'; pantallas=@(
          @{ n='Sucursales.tsx'; ruta='/sucursales'; menu='web'; guarda='[catalog.branch.read]' },
          @{ n='Especialidades.tsx'; ruta='/especialidades'; menu='web'; guarda='[catalog.specialty.read]' },
          @{ n='Profesionales.tsx'; ruta='/profesionales'; menu='web'; guarda='[catalog.professional.read]' },
          @{ n='Servicios.tsx'; ruta='/servicios'; menu='web'; guarda='[catalog.service.read]' },
          @{ n='Agendas.tsx'; ruta='/agendas'; menu='web'; guarda='[scheduling.schedule.read]' },
          @{ n='BloqueosAgenda.tsx'; ruta='/agendas/bloqueos'; desde='Agendas.tsx'; guarda='[scheduling.block.read]' },
          @{ n='BuscarProfesionales.tsx'; ruta='/buscar-profesionales'; menu='web'; guarda='[catalog.professional.read]' },
          @{ n='Disponibilidad.tsx'; ruta='/disponibilidad'; menu='web'; guarda='[scheduling.slot.read]' },
          @{ n='SchedulesScreen'; ruta='/org/agendas'; menu='org'; guarda='[scheduling.schedule.read]' },
          @{ n='ScheduleFormScreen'; ruta='/org/agendas/form'; desde='SchedulesScreen'; guarda='[scheduling.schedule.create]' },
          @{ n='BranchesScreen'; ruta='/org/sucursales'; menu='org'; guarda='[catalog.branch.read]' },
          @{ n='SpecialtiesAdminScreen'; ruta='/org/especialidades'; menu='org'; guarda='[catalog.specialty.read]' },
          @{ n='ProfessionalsAdminScreen'; ruta='/org/profesionales'; menu='org'; guarda='[catalog.professional.read]' },
          @{ n='OrgAvailabilityScreen'; ruta='/org/disponibilidad'; menu='org'; guarda='[scheduling.slot.read]' },
          @{ n='SpecialtiesScreen'; ruta='/specialties'; menu='movil' },
          @{ n='SearchScreen'; ruta='/search?specialty='; desde='SpecialtiesScreen' },
          @{ n='AvailabilityScreen'; ruta='/professionals/:id/availability'; desde=@('SearchScreen', 'OrgAvailabilityScreen') }
      ) },
      @{ titulo='P5 Agendamiento y Compra de Fichas'; pantallas=@(
          @{ n='MisFichas.tsx'; ruta='/mis-fichas'; menu='web'; guarda='[appointments.appointment.read]' },
          @{ n='CheckIn.tsx'; ruta='/check-in'; menu='web'; guarda='[appointments.appointment.read]' },
          @{ n='MyAppointmentsScreen'; ruta='/appointments'; menu='movil'; guarda='[SoloPacientes]' },
          @{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; desde=@('MyAppointmentsScreen', 'AvailabilityScreen') },
          @{ n='RescheduleScreen'; ruta='/appointments/:id/reschedule'; desde='AppointmentDetailScreen' },
          @{ n='ReceiptScreen'; ruta='/appointments/:id/receipt'; desde='AppointmentDetailScreen' },
          @{ n='SavedReceiptsScreen'; ruta='/receipts'; desde='MyAppointmentsScreen' }
      ) },
      @{ titulo='P6 Historia Clínica Digital'; pantallas=@(
          @{ n='AgendaAtencion.tsx'; ruta='/atencion'; menu='web'; guarda='[encounters.encounter.read]' },
          @{ n='Atencion.tsx'; ruta='/atencion/:id'; desde='AgendaAtencion.tsx' },
          @{ n='Historial.tsx'; ruta='/historial/:pacienteId'; desde='AgendaAtencion.tsx'; guarda='[encounters.history.read]' },
          @{ n='MiHistoria.tsx'; ruta='/mi-historia'; menu='web'; guarda='[rol patient + encounters.history.read]' },
          @{ n='ClinicalRecordScreen'; ruta='/clinical-record'; menu='movil'; guarda='[SoloPacientes]' }
      ) },
      @{ titulo='P7 Notificaciones y Reportes'; pantallas=@(
          @{ n='Reportes.tsx'; ruta='/reportes'; menu='web'; guarda='[reporting.report.run]' },
          @{ n='Kpis.tsx'; ruta='/kpis'; menu='web'; guarda='[reporting.kpi.read]' },
          @{ n='ReportsScreen'; ruta='/org/reportes'; menu='org'; guarda='[reporting.report.run]' }
      ) },
      @{ titulo='P8 IA 1 · Chatbot de Orientación (RAG)'; pantallas=@(
          @{ n='Asistente.tsx'; ruta='/asistente'; menu='web'; guarda='[assistant.suggest.use + plan ai_chatbot]' },
          @{ n='AssistantScreen'; ruta='/assistant'; menu='movil'; guarda='[SoloPacientes + plan ai_chatbot]' }
      ) },
      @{ titulo='Copias de seguridad (CG-6)'; pantallas=@(
          @{ n='Respaldos.tsx'; ruta='/respaldos'; menu='web'; guarda='[backups.backup.create]' },
          @{ n='BackupsScreen'; ruta='/org/respaldos'; menu='org'; guarda='[backups.backup.create]' }
      ) }
    )
  }

  # =======================================================================
  'P5' = @{
    titulo = 'P5 Agendamiento y Compra de Fichas'
    nota = 'Subsistema P5 (CU18 a CU24), web y móvil juntas. Reservar: la web abre ModalReservarFicha.tsx desde Disponibilidad.tsx; el móvil, ConfirmarReservaSheet desde AvailabilityScreen (se llega por Buscar profesionales, P4). Mis fichas: la web hace todo en la lista (MisFichas.tsx: pagar con return_to = web, comprobante, reprogramar, cancelar y confirmar asistencia); el móvil reparte en MyAppointmentsScreen, AppointmentDetailScreen, RescheduleScreen y ReceiptScreen, y guarda los comprobantes para verlos sin red (SavedReceiptsScreen, sin backend). Pagar: las dos abren el Checkout de Stripe (página externa); su submit es el webhook firmado, y return_page devuelve a /mis-fichas (302) o a la app por el deep link centromedico://app/appointments/{id}. Las dos plataformas llegan a los MISMOS archivos del backend. El cobro en ventanilla de CU24 (POST /api/payments/appointments/{id}/cash/, CashPaymentView) no tiene pantalla al 26/10: está como operación del controlador. El check-in es sólo web.'
    actores = @('Paciente', 'Recepcionista')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Paciente', 'Recepcionista') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      avail    = @{ n='scheduling/availability.py'; ops=@('AvailabilityView.get(request)') }
      booking  = @{ n='appointments/booking.py'; ops=@('AppointmentViewSet.list(request)', 'AppointmentViewSet.retrieve(request, pk)', 'AppointmentViewSet.create(request)', 'book_appointment(patient, practitioner, starts_at)') }
      payments = @{ n='payments/views.py'; ops=@('CheckoutView.post(request, pk)', 'stripe_webhook(request)', 'return_page(request)', 'CashPaymentView.post(request, pk)') }
      changes  = @{ n='appointments/changes.py'; ops=@('CancelAppointmentView.post(request, pk)', 'RescheduleAppointmentView.post(request, pk)') }
      attend   = @{ n='appointments/attendance.py'; ops=@('ConfirmAttendanceView.post(request, pk)', 'attendance_link_view(request, token)') }
      receipts = @{ n='appointments/receipts.py'; ops=@('ReceiptView.get(request, pk)') }
      checkin  = @{ n='appointments/checkin.py'; ops=@('CheckInView.post(request)') }
    }
    bandas = @(
      @{ titulo='Reservar'; pantallas=@(
          @{ n='Disponibilidad.tsx'; ruta='/disponibilidad'; menu='web'; guarda='[scheduling.slot.read]'; atr=@('professional', 'from', 'to', 'branch'); ctrl='avail'
             forms=@( @{ n='ModalReservarFicha.tsx'; atr=@('patient', 'practitioner', 'branch', 'schedule', 'starts_at'); ctrl='booking' } ) },
          @{ n='AvailabilityScreen'; ruta='/professionals/:id/availability'; menu='movil'; guarda='[Buscar profesionales -> /specialties -> /search]'; atr=@('from', 'to'); ctrl='avail'
             forms=@( @{ n='ConfirmarReservaSheet'; atr=@('patient'); ctrl='booking' } ) }
      ) },
      @{ titulo='Mis fichas y pago'; pantallas=@(
          @{ n='MisFichas.tsx'; ruta='/mis-fichas'; menu='web'; guarda='[appointments.appointment.read]'; atr=@('practitioner_name', 'starts_at', 'status', 'payment_status'); ctrl=@('booking', 'attend', 'changes')
             forms=@( @{ n='ModalComprobante.tsx'; atr=@('code', 'organization_name'); ctrl='receipts' },
                      @{ n='ModalReprogramarFicha.tsx'; atr=@('branch', 'schedule', 'starts_at'); ctrl='changes' } ) },
          @{ n='MyAppointmentsScreen'; ruta='/appointments'; menu='movil'; guarda='[SoloPacientes]'; atr=@('practitioner_name', 'starts_at', 'status'); ctrl='booking' },
          @{ n='SavedReceiptsScreen'; ruta='/receipts'; desde='MyAppointmentsScreen'; atr=@('ReceiptStore (flutter_secure_storage)') },
          @{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; desde=@('MyAppointmentsScreen', 'AvailabilityScreen'); atr=@('status', 'fee', 'expires_at', 'payment_status'); ctrl=@('booking', 'attend')
             forms=@( @{ n='DialogoPagarFicha'; atr=@('return_to = app'); ctrl='payments' },
                      @{ n='DialogoCancelarFicha'; atr=@('motivo'); ctrl='changes' } ) },
          @{ n='RescheduleScreen'; ruta='/appointments/:id/reschedule'; desde='AppointmentDetailScreen'; atr=@('branch', 'schedule', 'starts_at'); ctrl=@('avail', 'changes') },
          @{ n='ReceiptScreen'; ruta='/appointments/:id/receipt'; desde='AppointmentDetailScreen'; atr=@('code', 'organization_name'); ctrl='receipts' },
          @{ n='Checkout de Stripe'; ruta='checkout_url'; desde=@('MisFichas.tsx', 'DialogoPagarFicha'); guarda='[pending_payment]'; atr=@('line_items', 'success_url', 'cancel_url'); ctrl='payments'
             forms=@( @{ n='return_page'; tipo='navigationClass'; ruta='/api/payments/return/?resultado=&ficha=&origen='; atr=@('302 /mis-fichas', 'centromedico://app/appointments/{id}') } ) }
      ) },
      @{ titulo='Ventanilla'; pantallas=@(
          @{ n='CheckIn.tsx'; ruta='/check-in'; menu='web'; guarda='[appointments.appointment.read]'; atr=@('document_number', 'qr_code'); ctrl='checkin' }
      ) }
    )
  }

  # =======================================================================
  'P6' = @{
    titulo = 'P6 Historia Clínica Digital'
    nota = 'Subsistema P6 (CU25 a CU28), web y móvil juntas. La atención del médico (agenda del día, borrador, firma, enmienda, receta y órdenes) es sólo web: AgendaAtencion.tsx y Atencion.tsx con PanelReceta (RecetaAtencion.tsx); el historial del paciente que ve el médico es Historial.tsx. El paciente ve su historia y la de las personas a su cargo en MiHistoria.tsx (web) y en ClinicalRecordScreen (móvil): las dos eligen la persona con el mismo selector (patient-options) y leen el MISMO PatientHistoryView, y descargan la receta del mismo PrescriptionPdfView. Atencion.tsx no tiene entrada de menú: se abre desde la agenda o desde el Panel.'
    actores = @('Médico', 'Paciente')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Médico', 'Paciente') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      enc    = @{ n='encounters/views.py'; ops=@('AgendaView.get(request)', 'EncounterOpenView.post(request)', 'EncounterDetailView.get(request, pk)', 'EncounterDetailView.patch(request, pk)', 'EncounterSignView.post(request, pk)', 'EncounterAmendView.post(request, pk)', 'EncounterChildrenView.post(request, pk)', 'EncounterChildDetailView.delete(request, pk, child_pk)', 'PrescriptionPdfView.get(request, pk)') }
      ante   = @{ n='patients/history.py'; ops=@('PatientHistoryViewSet.highlights(request)') }
      hist   = @{ n='encounters/history_views.py'; ops=@('PatientHistoryView.get(request, patient_id)') }
      deps   = @{ n='patients/dependents.py'; ops=@('DependentViewSet.options_for_selector(request)') }
    }
    bandas = @(
      @{ titulo='Atención del médico (sólo web)'; pantallas=@(
          @{ n='AgendaAtencion.tsx'; ruta='/atencion'; menu='web'; guarda='[encounters.encounter.read]'; atr=@('date', 'starts_at', 'patient', 'status_display', 'encounter'); ctrl='enc' },
          @{ n='Atencion.tsx'; ruta='/atencion/:id'; desde='AgendaAtencion.tsx'; guarda='[encounters.encounter.create]'; atr=@('reason', 'evolution', 'diagnosis', 'indications', 'treatment'); ctrl=@('enc', 'ante')
             forms=@( @{ n='PanelReceta'; atr=@('medication', 'dose', 'frequency', 'duration', 'instructions', 'kind', 'description', 'notes'); ctrl='enc' },
                      @{ n='AgregarEnmienda'; atr=@('section', 'text'); ctrl='enc' } ) },
          @{ n='Historial.tsx'; ruta='/historial/:pacienteId'; desde='AgendaAtencion.tsx'; guarda='[encounters.history.read]'; atr=@('branch'); ctrl=@('hist', 'enc') }
      ) },
      @{ titulo='Historia del paciente (web y móvil)'; pantallas=@(
          @{ n='MiHistoria.tsx'; ruta='/mi-historia'; menu='web'; guarda='[rol patient + encounters.history.read]'; atr=@('patient'); ctrl=@('deps', 'hist', 'enc') },
          @{ n='ClinicalRecordScreen'; ruta='/clinical-record'; menu='movil'; guarda='[SoloPacientes]'; atr=@('branch'); ctrl=@('hist', 'enc')
             forms=@( @{ n='PatientSelector'; atr=@('patient'); ctrl='deps' } ) }
      ) }
    )
  }

  # =======================================================================
  'P7' = @{
    titulo = 'P7 Notificaciones y Reportes'
    nota = 'Subsistema P7 (CU29 a CU31), web y móvil juntas. Reportes: Reportes.tsx (web) y ReportsScreen (móvil) usan el MISMO reporting/views.py; sólo el móvil envía el reporte por correo (_FormularioDeEnvio); la web tiene enviarPorCorreo en reportes.ts:126 pero ninguna pantalla lo usa. Indicadores: Kpis.tsx, sólo web. Notificaciones: no tienen pantalla propia. La app registra el teléfono al iniciar sesión (POST /api/notifications/devices/) y lo olvida al cerrarla (DELETE), sin que el usuario haga nada (push.dart, session.dart:207 y :386); por eso DeviceTokenView cuelga de SignInScreen. Tocar un aviso abre la ficha en AppointmentDetailScreen (P5).'
    actores = @('Usuario', 'Administrador de Organización', 'Médico', 'Recepcionista', 'Paciente')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Administrador de Organización', 'Médico', 'Recepcionista') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Administrador de Organización', 'Médico', 'Recepcionista', 'Paciente') },
      @{ k='org';  n='OrganizationDrawer'; ruta='/org'; desde='movil'; guardaDesde='[alguna sección de la organización]' }
    )
    controladores = @{
      rep   = @{ n='reporting/views.py'; ops=@('DatasetListView.get(request)', 'RunReportView.post(request)', 'InterpretVoiceView.post(request)') }
      kpi   = @{ n='reporting/kpi_views.py'; ops=@('KpiView.get(request)') }
      notif = @{ n='notifications/views.py'; ops=@('DeviceTokenView.post(request)', 'DeviceTokenView.delete(request)') }
    }
    bandas = @(
      @{ titulo='Reportes'; pantallas=@(
          @{ n='Reportes.tsx'; ruta='/reportes'; menu='web'; guarda='[reporting.report.run]'; atr=@('dataset', 'columns', 'filters', 'format'); ctrl='rep'
             forms=@( @{ n='SeccionVoz'; atr=@('texto dictado'); ctrl='rep' } ) },
          @{ n='ReportsScreen'; ruta='/org/reportes'; menu='org'; guarda='[reporting.report.run]'; atr=@('dataset', 'columns'); ctrl='rep'
             forms=@( @{ n='_FormularioDeCriterio'; atr=@('Campo', 'Comparación', 'Valor'); ctrl='rep' },
                      @{ n='_ElegirFormato'; atr=@('format'); ctrl='rep' },
                      @{ n='_FormularioDeEnvio'; atr=@('Destinatarios'); ctrl='rep' } ) }
      ) },
      @{ titulo='Indicadores (sólo web)'; pantallas=@(
          @{ n='Kpis.tsx'; ruta='/kpis'; menu='web'; guarda='[reporting.kpi.read]'; atr=@('from', 'to', 'branch'); ctrl='kpi' }
      ) },
      @{ titulo='Avisos push (sólo móvil)'; pantallas=@(
          @{ n='SignInScreen'; ruta='/sign-in'; actor='Usuario'; ctrl='notif' },
          @{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; menu='movil'; guarda='[toca un aviso push]' }
      ) }
    )
  }

  # =======================================================================
  'P8' = @{
    titulo = 'P8 IA 1 · Chatbot de Orientación (RAG)'
    nota = 'Subsistema P8 (CU32 a CU35), web y móvil juntas. Asistente.tsx (web) y AssistantScreen (móvil) consultan el MISMO assistant/views.py (orientación, consultas y urgencias) y reservan por el MISMO assistant/booking_views.py (US-33: el asistente ofrece horarios reales y la ficha se crea sólo al confirmar). Para elegir la persona, la web abre ModalReservarFicha.tsx y el móvil ConfirmarReservaSheet, las mismas hojas de la reserva de P5. Tras reservar, la web lleva a Mis fichas y el móvil a la ficha (P5). La urgencia corta la conversación con AlertaEmergencia (web) o _AlertaEmergencia (móvil) y no ofrece horarios. Servicios.tsx dispara la reindexación del catálogo que alimenta al asistente. La entrada sólo aparece si el plan incluye ai_chatbot (GET /platform/my-plan/ en la web, incluyeAsistente en el móvil).'
    actores = @('Paciente', 'Recepcionista', 'Administrador de Organización')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Paciente', 'Recepcionista', 'Administrador de Organización') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      suggest = @{ n='assistant/views.py'; ops=@('SuggestView.post(request)') }
      book    = @{ n='assistant/booking_views.py'; ops=@('SlotsView.post(request)', 'BookView.post(request)') }
      reindex = @{ n='assistant/reindex_views.py'; ops=@('ReindexView.post(request)') }
    }
    bandas = @(
      @{ titulo='Asistente (web y móvil)'; pantallas=@(
          @{ n='Asistente.tsx'; ruta='/asistente'; menu='web'; guarda='[assistant.suggest.use + plan ai_chatbot]'; atr=@('question'); ctrl='suggest'
             forms=@( @{ n='BurbujaTurnos'; atr=@('preference'); ctrl='book' },
                      @{ n='ModalReservarFicha.tsx'; atr=@('patient', 'practitioner', 'branch', 'schedule', 'starts_at'); ctrl='book' } ) },
          @{ n='MisFichas.tsx'; ruta='/mis-fichas'; desde='Asistente.tsx'; guarda='[BurbujaReservada]' },
          @{ n='AssistantScreen'; ruta='/assistant'; menu='movil'; guarda='[SoloPacientes + plan ai_chatbot]'; atr=@('question', 'preference'); ctrl=@('suggest', 'book')
             forms=@( @{ n='ConfirmarReservaSheet'; atr=@('patient'); ctrl='book' } ) },
          @{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; desde='AssistantScreen'; guarda='[ficha reservada]' }
      ) },
      @{ titulo='Catálogo del asistente'; pantallas=@(
          @{ n='Servicios.tsx'; ruta='/servicios'; menu='web'; guarda='[catalog.service.read + assistant.catalog.reindex]'; ctrl='reindex' }
      ) }
    )
  }
}
