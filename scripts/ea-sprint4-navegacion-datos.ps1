# =========================================================================
# Datos de los diagramas de NAVEGACION del Sprint 4 (ea-navegacion-sprint4.ps1).
# Mismo formato que ea-sprint3-navegacion-datos.ps1 (ver su cabecera).
#   'Sistema'  todas las pantallas con codigo al 22/11/2026, una columna por
#              subsistema (P1 a P10). Solo pantallas y rutas.
#   'P5','P6','P7'  lo nuevo del Sprint 4 en esos subsistemas.
#   'P9','P10'      los subsistemas de IA que estrenan pantallas.
# Fuente: frontend/src/App.tsx y el menu de la web; mobile/lib/core/router/
# app_router.dart, gates y drawers; backend/*/urls.py (main 2349f66).
# =========================================================================

# =========================================================================
# Datos de los diagramas de NAVEGACION del Sprint 4 (mismo generador que el
# del Sprint 3: ea-navegacion-sprint3.ps1, leyendo $NAVEGACION_SPRINT4).
#
# Dos niveles, con la web y el movil juntos (decision de Karen, 26/10/2026):
#   'Sistema'  todas las pantallas con codigo al 22/11/2026, una columna por
#              subsistema (P1 a P10). Solo pantallas y rutas.
#   'P5' 'P6' 'P7' 'P9' 'P10'  solo lo NUEVO del Sprint 4 (US-35..US-42,
#              US-46..US-53), con formularios y controladores.
#
# Fuente: frontend/src/App.tsx y BarraPlataforma.tsx (web);
# mobile/lib/core/router/app_router.dart, patient_gate.dart, org_gate.dart y
# los drawers (movil); backend/*/urls.py y sus vistas para los controladores.
#
# ---- formato ---- (el mismo del Sprint 3)
#   titulo, nota, disposicion ('columnas' para el del sistema)
#   actores  nombres de actores del 1.3 (Usuario es el abstracto: de el
#            cuelgan las pantallas publicas)
#   menus    @{ k; n; ruta; guarda; actores } o, para un menu al que se llega
#            desde otro, @{ k; n; ruta; desde = <k del otro menu>; guardaDesde }
#   controladores  k -> @{ n = archivo del backend; ops = funciones exactas }
#   bandas   @{ titulo; pantallas = @( pantalla ) }
#   pantalla @{ n = archivo o clase; ruta; guarda; atr; ctrl (uno o lista);
#               forms = @( @{ n; atr; ctrl (UNO); tipo; ruta } ) }
#            y de donde cuelga: menu = <k>, o desde = <pantalla, formulario o
#            menu, uno o lista>, o actor = <actor> (publicas, sin sesion).
#   Una pantalla que sale en dos diagramas es el MISMO elemento: si lleva
#   atributos, que sean los mismos en los dos. Por eso los atributos de las
#   pantallas repetidas y los controladores compartidos estan en variables.
# =========================================================================

$WEB_ROLES = @('Paciente', 'Médico', 'Recepcionista', 'Administrador de Organización', 'Superadministrador de Plataforma')

# ---- atributos de las pantallas que salen en mas de un diagrama ----------
# (los mismos que en el Sprint 3 cuando la pantalla ya existia; Atencion.tsx
# suma los signos vitales de US-53)
$S4_ATR = @{
  'MisFichas.tsx'           = @('practitioner_name', 'starts_at', 'status', 'payment_status')
  'MyAppointmentsScreen'    = @('practitioner_name', 'starts_at', 'status')
  'AppointmentDetailScreen' = @('status', 'fee', 'expires_at', 'payment_status')
  'Disponibilidad.tsx'      = @('professional', 'from', 'to', 'branch')
  'AvailabilityScreen'      = @('from', 'to')
  'Kpis.tsx'                = @('from', 'to', 'branch')
  'AgendaAtencion.tsx'      = @('date', 'starts_at', 'patient', 'status_display', 'encounter')
  'Atencion.tsx'            = @('reason', 'evolution', 'diagnosis', 'indications', 'treatment', 'vital_signs')
  'Historial.tsx'           = @('branch')
  'MiHistoria.tsx'          = @('patient')
  'ClinicalRecordScreen'    = @('branch')
  'ReceiptScreen'           = @('code', 'organization_name')
  'SavedReceiptsScreen'     = @('ReceiptStore (flutter_secure_storage)')
}

# ---- controladores que salen en mas de un diagrama (mismas ops) ----------
$S4_CTRL = @{
  enc  = @{ n='encounters/views.py'; ops=@('EncounterDetailView.get(request, pk)', 'EncounterDetailView.patch(request, pk)', 'EncounterSignView.post(request, pk)') }
  hist = @{ n='encounters/history_views.py'; ops=@('PatientHistoryView.get(request, patient_id)', 'PatientHistorySummaryView.get(request, patient_id)') }
}

$NAVEGACION_SPRINT4 = [ordered]@{

  # =======================================================================
  'Sistema' = @{
    titulo = 'Sistema'
    disposicion = 'columnas'
    nota = 'Navegación del sistema completo, web y móvil juntas, al 22/11/2026: todas las pantallas que tienen código, una columna por subsistema (P1 a P10). Sólo pantallas y rutas: los formularios y los controladores de cada pantalla están en los diagramas de subsistema. No es UML: es la extensión UWE (diagrama de clases con estereotipos de navegación). Web: rutas de frontend/src/App.tsx; toda ruta protegida pasa por RutaProtegida (sesión) y cuelga de BarraPlataforma.tsx, cuyas entradas aparecen según el permiso que dice cada guarda y, si la entrada lo pide, según la función del plan (requierePlan; BarraPlataforma.tsx:403-411). Móvil: rutas de mobile/lib/core/router/app_router.dart; la sesión la pide el redirect (:123), SoloPacientes (patient_gate.dart) y ConPermiso (org_gate.dart). Las guardas de la interfaz son cosméticas: la puerta real es el permiso (y el plan) del backend. Nuevo en el Sprint 4: consultas de pacientes y chat (US-47), mis medicamentos (US-49, sólo móvil), mis comprobantes por voz (US-46), contabilidad (US-50, sólo web), riesgo de inasistencia y proyección de demanda (US-35/37/38, sólo web) y textos por validar (US-42, sólo web). La experiencia Plus (US-51), la lista de espera (US-52), la calificación (US-48), los signos vitales (US-53) y los resúmenes (US-39/40/41) no tienen ruta propia: viven dentro de pantallas que ya estaban (ver P5, P6 y P10). Sólo web: recuperar contraseña, servicios, pacientes, bloqueos, check-in, mostrador, atención médica, KPIs, contabilidad, P9 y P10. Sólo móvil: dependientes, antecedentes, comprobantes guardados y mis medicamentos.'
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
          @{ n='Mostrador.tsx'; ruta='/mostrador'; menu='web'; guarda='[appointments.appointment.book_at_counter]' },
          @{ n='MyAppointmentsScreen'; ruta='/appointments'; menu='movil'; guarda='[SoloPacientes]' },
          @{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; desde=@('MyAppointmentsScreen', 'AvailabilityScreen') },
          @{ n='RescheduleScreen'; ruta='/appointments/:id/reschedule'; desde='AppointmentDetailScreen' },
          @{ n='ReceiptScreen'; ruta='/appointments/:id/receipt'; desde=@('AppointmentDetailScreen', 'SavedReceiptsScreen', 'MyReceiptsScreen') },
          @{ n='SavedReceiptsScreen'; ruta='/receipts'; desde=@('MyAppointmentsScreen', 'MyReceiptsScreen') }
      ) },
      @{ titulo='P6 Historia Clínica Digital'; pantallas=@(
          @{ n='AgendaAtencion.tsx'; ruta='/atencion'; menu='web'; guarda='[encounters.encounter.read]' },
          @{ n='Atencion.tsx'; ruta='/atencion/:id'; desde='AgendaAtencion.tsx' },
          @{ n='Historial.tsx'; ruta='/historial/:pacienteId'; desde='AgendaAtencion.tsx'; guarda='[encounters.history.read]' },
          @{ n='ChatAtencion.tsx'; ruta='/consultas'; menu='web'; guarda='[encounters.encounter.read]' },
          @{ n='ConsultaChat'; ruta='/consultas/:encuentroId'; desde=@('ChatAtencion.tsx', 'MiHistoria.tsx'); guarda='[encounters.chat]' },
          @{ n='MiHistoria.tsx'; ruta='/mi-historia'; menu='web'; guarda='[rol patient + encounters.history.read]' },
          @{ n='ClinicalRecordScreen'; ruta='/clinical-record'; menu='movil'; guarda='[SoloPacientes]' },
          @{ n='ChatScreen'; ruta='/chat/:encounterId'; desde='ClinicalRecordScreen'; guarda='[SoloPacientes]' },
          @{ n='MedicationsScreen'; ruta='/medications'; menu='movil'; guarda='[SoloPacientes]' }
      ) },
      @{ titulo='P7 Notificaciones y Reportes'; pantallas=@(
          @{ n='Reportes.tsx'; ruta='/reportes'; menu='web'; guarda='[reporting.report.run]' },
          @{ n='Kpis.tsx'; ruta='/kpis'; menu='web'; guarda='[reporting.kpi.read]' },
          @{ n='Contabilidad.tsx'; ruta='/contabilidad'; menu='web'; guarda='[finance.accounting.read]' },
          @{ n='MisComprobantes.tsx'; ruta='/mis-comprobantes'; menu='web'; guarda='[rol patient + encounters.history.read]' },
          @{ n='ReportsScreen'; ruta='/org/reportes'; menu='org'; guarda='[reporting.report.run]' },
          @{ n='MyReceiptsScreen'; ruta='/my-receipts'; menu='movil'; guarda='[SoloPacientes]' }
      ) },
      @{ titulo='P8 IA 1 · Chatbot de Orientación (RAG)'; pantallas=@(
          @{ n='Asistente.tsx'; ruta='/asistente'; menu='web'; guarda='[assistant.suggest.use + plan ai_chatbot]' },
          @{ n='AssistantScreen'; ruta='/assistant'; menu='movil'; guarda='[SoloPacientes + plan ai_chatbot]' }
      ) },
      @{ titulo='P9 IA 2 · Predicción de Inasistencia'; pantallas=@(
          @{ n='RiesgoInasistencia.tsx'; ruta='/riesgo-inasistencia'; menu='web'; guarda='[appointments.noshow.read + plan noshow_prediction]' },
          @{ n='ProyeccionDemanda.tsx'; ruta='/proyeccion-demanda'; menu='web'; guarda='[reporting.kpi.read]' }
      ) },
      @{ titulo='P10 IA 3 · Generación de Resúmenes'; pantallas=@(
          @{ n='TextosPorValidar.tsx'; ruta='/textos-ia'; menu='web'; guarda='[ai.text.review]' }
      ) },
      @{ titulo='Copias de seguridad (CG-6)'; pantallas=@(
          @{ n='Respaldos.tsx'; ruta='/respaldos'; menu='web'; guarda='[backups.backup.create]' },
          @{ n='BackupsScreen'; ruta='/org/respaldos'; menu='org'; guarda='[backups.backup.create]' }
      ) }
    )
  }

  # =======================================================================
  'P5' = @{
    titulo = 'P5 Agendamiento y Compra de Fichas · Sprint 4'
    nota = 'Lo nuevo de P5 en el Sprint 4, web y móvil juntas. US-51 Experiencia Plus: no tiene ruta; la web abre ExperienciaPlus.tsx desde MisFichas.tsx (botón «Mi experiencia Plus», sólo en una ficha con comprobante) y el móvil abre PreconsultaPlusSheet desde AppointmentDetailScreen (sólo si la ficha está confirmada o atendida). Las dos guardan la preconsulta (motivo y preguntas) en el MISMO PreconsultationView y muestran el mapa de la sucursal con branch_maps_url, que arma maps_url(branch) de appointments/calendar.py. «Agregar a mi calendario» no es igual: la web baja el .ics de CalendarView (hora de La Paz y aviso 24 h antes); el móvil abre calendar.google.com/calendar/render, sin backend. US-52 lista de espera: cuando no hay espacios, la web ofrece TarjetaListaEspera.tsx en Disponibilidad.tsx y el móvil AnotarseCard en AvailabilityScreen; las dos se anotan por el MISMO WaitlistView. Mis fichas (MisFichas.tsx y MyAppointmentsScreen) muestra las entradas y permite salir (WaitlistEntryView.delete). Kpis.tsx muestra el resumen de la lista (WaitlistSummaryView). La lista es de los planes Pro y Premium (función waitlist): sin ella el backend responde plan_limit al anotarse y la lista llega vacía.'
    actores = @('Paciente', 'Recepcionista', 'Administrador de Organización')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Paciente', 'Recepcionista', 'Administrador de Organización') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      avail    = @{ n='scheduling/availability.py'; ops=@('AvailabilityView.get(request)') }
      booking  = @{ n='appointments/booking.py'; ops=@('AppointmentViewSet.list(request)', 'AppointmentViewSet.retrieve(request, pk)', 'AppointmentViewSet.create(request)', 'book_appointment(patient, practitioner, starts_at)') }
      precons  = @{ n='appointments/preconsultation_views.py'; ops=@('PreconsultationView.get(request, pk)', 'PreconsultationView.put(request, pk)') }
      calendar = @{ n='appointments/calendar.py'; ops=@('CalendarView.get(request, pk)', 'build_ics(appointment)', 'maps_url(branch)') }
      waitlist = @{ n='appointments/waitlist_views.py'; ops=@('WaitlistView.get(request)', 'WaitlistView.post(request)', 'WaitlistEntryView.delete(request, pk)', 'WaitlistSummaryView.get(request)') }
    }
    bandas = @(
      @{ titulo='Experiencia Plus (US-51)'; pantallas=@(
          @{ n='MisFichas.tsx'; ruta='/mis-fichas'; menu='web'; guarda='[appointments.appointment.read]'; atr=$S4_ATR['MisFichas.tsx']; ctrl=@('booking', 'waitlist')
             forms=@( @{ n='ExperienciaPlus.tsx'; atr=@('reason', 'questions', 'branch_maps_url'); ctrl='precons' },
                      @{ n='calendar.ics'; tipo='navigationClass'; ruta='/api/appointments/appointments/{id}/calendar.ics'; atr=@('hora de La Paz', 'aviso 24 h antes'); ctrl='calendar' } ) },
          @{ n='MyAppointmentsScreen'; ruta='/appointments'; menu='movil'; guarda='[SoloPacientes]'; atr=$S4_ATR['MyAppointmentsScreen']; ctrl=@('booking', 'waitlist') },
          @{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; desde='MyAppointmentsScreen'; atr=$S4_ATR['AppointmentDetailScreen']; ctrl='booking'
             forms=@( @{ n='PreconsultaPlusSheet'; atr=@('reason', 'questions', 'branch_maps_url', 'calendar.google.com'); ctrl='precons' } ) }
      ) },
      @{ titulo='Lista de espera (US-52)'; pantallas=@(
          @{ n='Disponibilidad.tsx'; ruta='/disponibilidad'; menu='web'; guarda='[scheduling.slot.read]'; atr=$S4_ATR['Disponibilidad.tsx']; ctrl='avail'
             forms=@( @{ n='TarjetaListaEspera.tsx'; atr=@('patient', 'practitioner', 'specialty', 'branch', 'date_from', 'date_to'); ctrl='waitlist' } ) },
          @{ n='AvailabilityScreen'; ruta='/professionals/:id/availability'; menu='movil'; guarda='[Buscar profesionales -> /specialties -> /search]'; atr=$S4_ATR['AvailabilityScreen']; ctrl='avail'
             forms=@( @{ n='AnotarseCard'; atr=@('patient', 'practitioner', 'date_from', 'date_to'); ctrl='waitlist' } ) },
          @{ n='Kpis.tsx'; ruta='/kpis'; menu='web'; guarda='[reporting.kpi.read]'; atr=$S4_ATR['Kpis.tsx']; ctrl='waitlist' }
      ) }
    )
  }

  # =======================================================================
  'P6' = @{
    titulo = 'P6 Historia Clínica Digital · Sprint 4'
    nota = 'Lo nuevo de P6 en el Sprint 4, web y móvil juntas. US-47 chat paciente–médico, sobre una atención firmada: el médico ve la bandeja en ChatAtencion.tsx (/consultas) y conversa en ConsultaChat o desde la misma atención (PanelChat en Atencion.tsx); el paciente llega desde MiHistoria.tsx (web) o desde ClinicalRecordScreen con «Escribir al médico» (móvil, ChatScreen; también abre al tocar el aviso push). Los tres usan el MISMO messaging/views.py (permiso encounters.chat); sin tiempo real, la web vuelve a pedir la conversación cada 10 s. US-48 calificación: el paciente califica la atención en CalificarAtencion.tsx (web) y TarjetaCalificacion (móvil), por el MISMO EncounterRatingView; el médico ve su promedio en AgendaAtencion.tsx (MiPromedio, MyRatingsView) y la organización la satisfacción en Kpis.tsx (TarjetaSatisfaccion.tsx, SatisfactionView). US-49 mis medicamentos: sólo móvil (MedicationsScreen), con recordatorios locales (InterruptorRecordatorio, flutter_local_notifications) y las tomas en MedicationIntakesView. US-53 signos vitales: el médico los carga en Atencion.tsx (SignosVitales.tsx, se guardan con EncounterDetailView.patch) y la evolución se grafica en Historial.tsx y MiHistoria.tsx (EvolucionSignos.tsx) y en ClinicalRecordScreen (MisSignosVitales); los datos vienen del MISMO PatientHistoryView.'
    actores = @('Médico', 'Paciente', 'Administrador de Organización')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Médico', 'Paciente', 'Administrador de Organización') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      enc    = $S4_CTRL.enc
      hist   = $S4_CTRL.hist
      chat   = @{ n='messaging/views.py'; ops=@('InboxView.get(request)', 'ChatView.get(request, encounter_id)', 'SendMessageView.post(request, encounter_id)', 'CloseChatView.post(request, encounter_id)') }
      rating = @{ n='encounters/rating_views.py'; ops=@('EncounterRatingView.get(request, pk)', 'EncounterRatingView.post(request, pk)', 'EncounterRatingView.patch(request, pk)', 'MyRatingsView.get(request)') }
      satisf = @{ n='reporting/kpi_views.py'; ops=@('KpiView.get(request)', 'SatisfactionView.get(request)') }
      intake = @{ n='encounters/intake_views.py'; ops=@('MyMedicationsView.get(request, patient_id)', 'MedicationIntakesView.get(request, item_pk)', 'MedicationIntakesView.post(request, item_pk)') }
    }
    bandas = @(
      @{ titulo='Atención del médico (web)'; pantallas=@(
          @{ n='AgendaAtencion.tsx'; ruta='/atencion'; menu='web'; guarda='[encounters.encounter.read]'; atr=$S4_ATR['AgendaAtencion.tsx']; ctrl='rating' },
          @{ n='Atencion.tsx'; ruta='/atencion/:id'; desde='AgendaAtencion.tsx'; guarda='[encounters.encounter.create]'; atr=$S4_ATR['Atencion.tsx']; ctrl='enc'
             forms=@( @{ n='SignosVitales.tsx'; atr=@('systolic', 'diastolic', 'heart_rate', 'temperature', 'spo2', 'glucose', 'weight_kg', 'height_cm'); ctrl='enc' },
                      @{ n='PanelChat'; atr=@('body'); ctrl='chat' } ) },
          @{ n='Historial.tsx'; ruta='/historial/:pacienteId'; desde='AgendaAtencion.tsx'; guarda='[encounters.history.read]'; atr=$S4_ATR['Historial.tsx']; ctrl='hist'
             forms=@( @{ n='EvolucionSignos.tsx'; atr=@('presion', 'heart_rate', 'temperature', 'spo2', 'glucose', 'weight_kg', 'bmi') } ) },
          @{ n='ChatAtencion.tsx'; ruta='/consultas'; menu='web'; guarda='[encounters.encounter.read]'; atr=@('unread_total'); ctrl='chat' },
          @{ n='ConsultaChat'; ruta='/consultas/:encuentroId'; desde=@('ChatAtencion.tsx', 'MiHistoria.tsx'); guarda='[encounters.chat]'; atr=@('body'); ctrl='chat' }
      ) },
      @{ titulo='Historia del paciente (web y móvil)'; pantallas=@(
          @{ n='MiHistoria.tsx'; ruta='/mi-historia'; menu='web'; guarda='[rol patient + encounters.history.read]'; atr=$S4_ATR['MiHistoria.tsx']; ctrl='hist'
             forms=@( @{ n='CalificarAtencion.tsx'; atr=@('stars', 'comment'); ctrl='rating' } ) },
          @{ n='ClinicalRecordScreen'; ruta='/clinical-record'; menu='movil'; guarda='[SoloPacientes]'; atr=$S4_ATR['ClinicalRecordScreen']; ctrl='hist'
             forms=@( @{ n='TarjetaCalificacion'; atr=@('stars', 'comment'); ctrl='rating' },
                      @{ n='MisSignosVitales'; atr=@('presion', 'heart_rate', 'temperature', 'spo2', 'glucose', 'weight_kg', 'bmi') } ) },
          @{ n='ChatScreen'; ruta='/chat/:encounterId'; desde='ClinicalRecordScreen'; guarda='[SoloPacientes]'; atr=@('body'); ctrl='chat' },
          @{ n='MedicationsScreen'; ruta='/medications'; menu='movil'; guarda='[SoloPacientes]'; atr=@('patient'); ctrl='intake'
             forms=@( @{ n='InterruptorRecordatorio'; atr=@('dose_number', 'status', 'scheduled_at'); ctrl='intake' } ) }
      ) },
      @{ titulo='Satisfacción (US-48)'; pantallas=@(
          @{ n='Kpis.tsx'; ruta='/kpis'; menu='web'; guarda='[reporting.kpi.read]'; atr=$S4_ATR['Kpis.tsx']
             forms=@( @{ n='TarjetaSatisfaccion.tsx'; atr=@('desde', 'hasta', 'sucursal'); ctrl='satisf' } ) }
      ) }
    )
  }

  # =======================================================================
  'P7' = @{
    titulo = 'P7 Notificaciones y Reportes · Sprint 4'
    nota = 'Lo nuevo de P7 en el Sprint 4, web y móvil juntas. US-46 mis comprobantes por voz: el paciente los pide hablando o escribiendo en MisComprobantes.tsx (web, con EntradaDeVoz.tsx) y en MyReceiptsScreen (móvil, _Pedido); las dos interpretan la frase con el MISMO MyReceiptsInterpretView y traen la lista (o el archivo, ?formato=) de MyReceiptsView. En el móvil cada comprobante abre ReceiptScreen y queda guardado para verlo sin red (SavedReceiptsScreen). La entrada web aparece con el rol patient + encounters.history.read (BarraPlataforma.tsx); el backend pide appointments.appointment.read y un perfil de paciente. US-50 contabilidad: sólo web (Contabilidad.tsx): resumen, serie de seis meses y exportación de reporting/finance_views.py; la pregunta por voz va por InterpretView; los gastos (PestanaGastos) y la comisión de Stripe (PestanaComision) se cargan sólo con finance.expense.manage. Es de los planes Pro y Premium.'
    actores = @('Paciente', 'Administrador de Organización')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Paciente', 'Administrador de Organización') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      mine     = @{ n='payments/views_mine.py'; ops=@('MyReceiptsInterpretView.post(request)', 'MyReceiptsView.get(request)') }
      receipts = @{ n='appointments/receipts.py'; ops=@('ReceiptView.get(request, pk)') }
      fin      = @{ n='reporting/finance_views.py'; ops=@('SummaryView.get(request)', 'SeriesView.get(request)', 'ExportView.get(request)', 'InterpretView.post(request)', 'ExpenseListView.get(request)', 'ExpenseListView.post(request)', 'ExpenseDetailView.patch(request, pk)', 'ExpenseDetailView.delete(request, pk)', 'SettingsView.get(request)', 'SettingsView.put(request)') }
    }
    bandas = @(
      @{ titulo='Mis comprobantes por voz (US-46)'; pantallas=@(
          @{ n='MisComprobantes.tsx'; ruta='/mis-comprobantes'; menu='web'; guarda='[rol patient + encounters.history.read]'; atr=@('text', 'formato'); ctrl='mine'
             forms=@( @{ n='EntradaDeVoz.tsx'; atr=@('texto dictado'); ctrl='mine' } ) },
          @{ n='MyReceiptsScreen'; ruta='/my-receipts'; menu='movil'; guarda='[SoloPacientes]'; atr=@('text', 'formato'); ctrl='mine'
             forms=@( @{ n='_Pedido'; atr=@('texto dictado o escrito'); ctrl='mine' } ) },
          @{ n='ReceiptScreen'; ruta='/appointments/:id/receipt'; desde=@('MyReceiptsScreen', 'SavedReceiptsScreen'); atr=$S4_ATR['ReceiptScreen']; ctrl='receipts' },
          @{ n='SavedReceiptsScreen'; ruta='/receipts'; desde='MyReceiptsScreen'; guarda='[Ver guardados]'; atr=$S4_ATR['SavedReceiptsScreen'] }
      ) },
      @{ titulo='Contabilidad (US-50, sólo web)'; pantallas=@(
          @{ n='Contabilidad.tsx'; ruta='/contabilidad'; menu='web'; guarda='[finance.accounting.read]'; atr=@('from', 'to', 'branch', 'practitioner', 'group', 'compare', 'file', 'text'); ctrl='fin'
             forms=@( @{ n='PestanaGastos'; atr=@('branch', 'category', 'amount', 'currency', 'spent_on', 'note'); ctrl='fin' },
                      @{ n='PestanaComision'; atr=@('stripe_percent'); ctrl='fin' } ) }
      ) }
    )
  }

  # =======================================================================
  'P9' = @{
    titulo = 'P9 IA 2 · Predicción de Inasistencia'
    nota = 'Subsistema P9 (US-35, US-37 y US-38), sólo web: el móvil no tiene estas pantallas. US-35: RiesgoInasistencia.tsx lista las fichas futuras con su nivel de riesgo y sus factores (NoShowAppointmentsView; sin from/to el backend toma de hoy a hoy + 14 días) y el estado del modelo con sus métricas (NoShowModelView, TarjetaModelo). US-38: la misma pantalla muestra las versiones del modelo (NoShowVersionsView); el reentrenamiento no tiene pantalla. Tres cerraduras del lado del servidor: el permiso appointments.noshow.read, el plan (noshow_prediction, sólo Premium; la entrada del menú se oculta con requierePlan) y la organización. US-37: ProyeccionDemanda.tsx proyecta la demanda por semanas y sucursal (DemandProjectionView, permiso reporting.kpi.read).'
    actores = @('Administrador de Organización')
    menus = @(
      @{ k='web'; n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Administrador de Organización') }
    )
    controladores = @{
      noshow   = @{ n='noshow/views.py'; ops=@('NoShowAppointmentsView.get(request)', 'NoShowModelView.get(request)') }
      versions = @{ n='noshow/retrain_views.py'; ops=@('NoShowVersionsView.get(request)') }
      demand   = @{ n='reporting/demand_views.py'; ops=@('DemandProjectionView.get(request)') }
    }
    bandas = @(
      @{ titulo='Riesgo de inasistencia (US-35, US-38)'; pantallas=@(
          @{ n='RiesgoInasistencia.tsx'; ruta='/riesgo-inasistencia'; menu='web'; guarda='[appointments.noshow.read + plan noshow_prediction]'; atr=@('from', 'to', 'branch', 'level', 'page'); ctrl=@('noshow', 'versions')
             forms=@( @{ n='TarjetaModelo'; atr=@('metrics', 'brier'); ctrl='noshow' } ) }
      ) },
      @{ titulo='Proyección de demanda (US-37)'; pantallas=@(
          @{ n='ProyeccionDemanda.tsx'; ruta='/proyeccion-demanda'; menu='web'; guarda='[reporting.kpi.read]'; atr=@('weeks', 'branch'); ctrl='demand' }
      ) }
    )
  }

  # =======================================================================
  'P10' = @{
    titulo = 'P10 IA 3 · Generación de Resúmenes'
    nota = 'Subsistema P10 (US-39 a US-42), web y móvil juntas. Ningún texto de la IA llega al paciente sin que el médico lo apruebe. Al firmar en Atencion.tsx (EncounterSignView) se generan el resumen de la consulta para el paciente (US-39) y la preparación de cada orden de estudio (US-40); el médico ve el resultado en AvisoResumenPaciente y, en una atención ya firmada, puede pedirlo con PedirResumenPaciente (ConsultationSummaryView). Los borradores se revisan, editan, aprueban o descartan en TextosPorValidar.tsx (US-42, permiso ai.text.review). US-41: el resumen del historial para el médico, con cada oración citando sus atenciones, es PanelResumenHistorial en Atencion.tsx (PatientHistorySummaryView, encounters.history.read). El paciente lee sólo lo aprobado (PatientTextsView, /api/ai/texts/mine/): la web muestra el resumen de cada consulta en MiHistoria.tsx (ResumenDeLaConsulta); el móvil, en ClinicalRecordScreen, el resumen (_Resumen) y también la preparación de cada orden (_Preparacion). StudyPreparationView (POST /api/ai/orders/{id}/preparation/) existe pero ninguna pantalla lo llama al 22/11/2026.'
    actores = @('Médico', 'Paciente')
    menus = @(
      @{ k='web';  n='BarraPlataforma.tsx'; ruta='/* (ArmazonPlataforma)'; guarda='[sesión]'; actores=@('Médico', 'Paciente') },
      @{ k='movil'; n='_HomeScreen'; ruta='/home'; guarda='[sesión]'; actores=@('Paciente') }
    )
    controladores = @{
      enc  = $S4_CTRL.enc
      hist = $S4_CTRL.hist
      ai   = @{ n='ai/views.py'; ops=@('InboxView.get(request)', 'TextDetailView.get(request, pk)', 'TextDetailView.patch(request, pk)', 'ApproveView.post(request, pk)', 'DiscardView.post(request, pk)', 'ConsultationSummaryView.post(request, encounter_id)', 'StudyPreparationView.post(request, order_id)', 'PatientTextsView.get(request)') }
    }
    bandas = @(
      @{ titulo='Médico (sólo web)'; pantallas=@(
          @{ n='TextosPorValidar.tsx'; ruta='/textos-ia'; menu='web'; guarda='[ai.text.review]'; atr=@('status', 'kind', 'text'); ctrl='ai'
             forms=@( @{ n='Pendiente'; atr=@('text'); ctrl='ai' } ) },
          @{ n='AgendaAtencion.tsx'; ruta='/atencion'; menu='web'; guarda='[encounters.encounter.read]'; atr=$S4_ATR['AgendaAtencion.tsx'] },
          @{ n='Atencion.tsx'; ruta='/atencion/:id'; desde='AgendaAtencion.tsx'; guarda='[encounters.encounter.create]'; atr=$S4_ATR['Atencion.tsx']; ctrl='enc'
             forms=@( @{ n='AvisoResumenPaciente'; atr=@('text', 'status'); ctrl='ai' },
                      @{ n='PedirResumenPaciente'; atr=@('encounter'); ctrl='ai' },
                      @{ n='PanelResumenHistorial'; atr=@('patient'); ctrl='hist' } ) }
      ) },
      @{ titulo='Paciente (web y móvil)'; pantallas=@(
          @{ n='MiHistoria.tsx'; ruta='/mi-historia'; menu='web'; guarda='[rol patient + encounters.history.read]'; atr=$S4_ATR['MiHistoria.tsx']; ctrl='ai'
             forms=@( @{ n='ResumenDeLaConsulta'; atr=@('text', 'practitioner_name', 'approved_at') } ) },
          @{ n='ClinicalRecordScreen'; ruta='/clinical-record'; menu='movil'; guarda='[SoloPacientes]'; atr=$S4_ATR['ClinicalRecordScreen']; ctrl='ai'
             forms=@( @{ n='_Resumen'; atr=@('texto', 'aprobadoPor', 'aprobadoEl') },
                      @{ n='_Preparacion'; atr=@('texto') } ) }
      ) }
    )
  }
}
