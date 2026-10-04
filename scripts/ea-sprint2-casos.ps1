# =========================================================================
# Datos de los casos de uso del Sprint 2, para los generadores de EA.
#
# Lo consumen, con dot-sourcing:
#   ea-comunicacion-sprint2.ps1   (2.1.3   diagrama de comunicacion)
#   ea-clases-sprint2.ps1         (2.1.4.1 clases de analisis)
#   ea-secuencia-sprint2.ps1      (2.1.4.2 diagrama de secuencia)
#
# Comunicacion y secuencia dibujan los MISMOS mensajes con la MISMA
# numeracion, y clases dibuja los mismos participantes: por eso los datos
# viven una sola vez, aca, y no copiados en cada generador. Agregar un caso de
# uso es agregar un bloque.
#
# ---- REGLAS (docs/diagramas/GUIA-DE-DIAGRAMAS.md, seccion 1) ----
#   - Los nombres son los exactos del codigo: archivos, funciones, tablas.
#   - Las entidades llevan el nombre de la TABLA (db_table), no el del modelo.
#   - Actor -> frontera: la accion del usuario. Frontera -> controlador: la
#     llamada real. Controlador -> entidad: la consulta.
#
# ---- FORMATO ----
#   participantes: k (clave), n (nombre), rol (actor | boundary | control |
#     entity), col (0..4) y f (fila, admite medias filas), nota.
#     Para la clase de analisis: atr (atributos) y ops (operaciones).
#   mensajes: g (grupo), d (desde), a (hacia), m (texto), ret ($true si es
#     una respuesta: en secuencia se dibuja punteada). Todo texto lleva
#     parentesis: a un mensaje de secuencia sin ellos EA le agrega "()", y
#     '200 Perfil' salia '200 Perfil()'. Por eso '200 (Perfil)'.
#   grupos: titulo de cada grupo. Es la guarda del operando en secuencia y la
#     leyenda del diagrama de comunicacion.
# =========================================================================

$CASOS_SPRINT2 = [ordered]@{

  'CU6' = @{
    cu     = 'CU6'
    nombre = 'Gestión de Perfil de Usuario'
    us     = 'US-05'
    nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. La web y el móvil llaman al mismo endpoint. El usuario sale siempre del token: ninguna ruta lleva un identificador.'
    # Clases CONCEPTUALES, como en Violet Boutique: el modelo de analisis es
    # anterior al diseno, asi que "GestorPerfil" no es un archivo. La nota de
    # cada una dice que modulos del codigo la implementan, y en el diagrama
    # de clases sus operaciones son las funciones reales.
    participantes = @(
      @{ k='usuario';  n='Usuario'; rol='actor'; col=0; f=1.6 },

      @{ k='pantalla'; n='PantallaPerfil'; rol='boundary'; col=1; f=0.6
         nota='Web: frontend/src/paginas/Perfil.tsx y frontend/src/api/perfil.ts. Móvil: mobile/lib/features/profile/. Backend: profile en accounts/views/profile.py.'
         atr=@('GET /api/accounts/users/me/ : 200 | 401', 'PATCH /api/accounts/users/me/ : 200 | 400 | 401')
         ops=@('obtenerPerfil(contexto)', 'actualizarPerfil(datos, contexto)', 'profile(request)') },

      @{ k='form';     n='FormularioContrasena'; rol='boundary'; col=1; f=2.8
         nota='El componente CambioDeContrasena de frontend/src/paginas/Perfil.tsx, y su par en mobile/lib/features/profile/profile_screen.dart. Backend: change_password en accounts/views/profile.py.'
         atr=@('POST /api/accounts/users/me/password/ : 200 | 400 | 401')
         ops=@('cambiarContrasena(datos, contexto)', 'change_password(request)') },

      @{ k='gestor';   n='GestorPerfil'; rol='control'; col=2; f=1.6
         nota='accounts/views/profile.py y accounts/serializers/profile.py. Resuelve el usuario desde el token y rechaza con su nombre todo campo que no sea editable.'
         atr=@()
         ops=@('to_internal_value(data)', 'validate_email(value)', 'get_roles(user)', 'validate(attrs)', '_sincronizar_paciente(user, cambiados)') },

      @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=0
         nota='audit/services.py. Encola el asiento y lo escribe el middleware al terminar la petición. Nunca guarda contraseñas.'
         atr=@()
         ops=@('record(request, action, entity, entity_id, detail)') },

      @{ k='auth';     n='GestorAutenticacion'; rol='control'; col=2; f=3.2
         nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token), accounts/passwords.py (la política compartida con US-03), accounts/services/password_reset.py (la revocación) y accounts/tokens.py (el par nuevo).'
         atr=@()
         ops=@('authenticate(request)', 'validate_password_strength(password, user)', 'revoke_all_sessions(user)', 'tokens_for_user(user)') },

      @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
         nota='Tabla audit_log.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
         ops=@('insert(asiento)') },

      @{ k='entusuario'; n='Usuario'; rol='entity'; col=3; f=1.2
         nota='Tabla users. UNIQUE(organization_id, email): el correo es único dentro de cada organización.'
         atr=@('id : uuid', 'organization_id : uuid', 'email : varchar(254)', 'first_name : varchar(80)', 'last_name : varchar(80)', 'phone : varchar(30)', 'document_number : varchar(20)', 'password : varchar(128)', 'is_active : boolean')
         ops=@('exists(organization_id, email__iexact)', 'save()', 'check_password(raw)', 'set_password(raw)') },

      @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=2.2
         nota='Tabla patients: la ficha demográfica que ve recepción.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'phone : varchar(30)')
         ops=@('update(first_name, last_name, phone)') },

      @{ k='token';    n='TokenRevocado'; rol='entity'; col=3; f=3.2
         nota='Tabla token_blacklist_blacklistedtoken (SimpleJWT). Un refresco que está acá ya no renueva.'
         atr=@('id : bigint', 'token_id : bigint', 'blacklisted_at : timestamptz')
         ops=@('get_or_create(token)') }
    )

    estado = @{
      estados = @(
        @{ k='ini';    tipo='inicial'; col=0; f=0 },
        @{ k='aut';    n='Autenticar Usuario';          col=0; f=2 },
        @{ k='fin401'; tipo='final';   col=0; f=4.5 },
        @{ k='menu';   n='Seleccionar operación';       col=1; f=2 },
        @{ k='ver';    n='Desplegar perfil';            col=2; f=0 },
        @{ k='capd';   n='Capturar datos de contacto';  col=2; f=2 },
        @{ k='capc';   n='Capturar contraseñas';        col=2; f=4 },
        @{ k='vald';   n='Validar datos';               col=3; f=2 },
        @{ k='valc';   n='Validar contraseña';          col=3; f=4 },
        @{ k='error';  n='Informar error';              col=4; f=5.5 },
        @{ k='ok';     n='Transacción completada';      col=4; f=1 },
        @{ k='fin';    tipo='final';   col=4; f=3 }
      )
      transiciones = @(
        @{ de='ini';   a='aut' },
        @{ de='aut';   a='menu';   r='[token válido] {IsAuthenticated, views/profile.py:45}' },
        @{ de='aut';   a='fin401'; r='[sin token] {401}' },
        @{ de='menu';  a='ver';    r='[consultar] {GET /users/me/}' },
        @{ de='menu';  a='capd';   r='[editar datos] {PATCH /users/me/}' },
        @{ de='menu';  a='capc';   r='[cambiar contraseña] {POST /users/me/password/}' },
        @{ de='capd';  a='vald';   r='guardar()' },
        @{ de='capc';  a='valc';   r='cambiar()' },
        @{ de='vald';  a='ok';     r='[sólo campos editables y correo libre] / save()' },
        @{ de='vald';  a='error';  r='[campo no editable o correo ya usado] {400 serializers/profile.py:83, :102}' },
        @{ de='valc';  a='ok';     r='[actual correcta y nueva válida] / revoke_all_sessions() {views/profile.py:119}' },
        @{ de='valc';  a='error';  r='[actual incorrecta o repetida] {400 views/profile.py:103, :110}' },
        @{ de='ver';   a='ok' },
        @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
        @{ de='ok';    a='fin' }
      )
    }
    # ---- 2.1.4.4 Diagrama de tiempo: un escenario, donde manda el reloj ----
    # La regla es RELATIVA (0 a 100): los instantes son del escenario, no
    # milisegundos medidos. Lo unico medible son las restricciones, y salen
    # del codigo. Se escriben SIN llaves: las pone EA.
    tiempo = @{
      escenario = 'cambiar la contraseña'
      nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:294). El refresco del otro dispositivo se revoca en el mismo COMMIT (revoke_all_sessions, views/profile.py:119); su acceso sigue valiendo hasta vencer, porque un JWT no se puede invalidar sin consultar la base. La sesión en curso recibe un par nuevo y sigue adentro.'
      lineas = @(
        @{ n='Transacción'
           estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=6;  e='Autenticando'; ev='POST /users/me/password/' },
                     @{ t=20; e='Validando';    ev='check_password()' },
                     @{ t=32; e='Escribiendo';  ev='set_password()' },
                     @{ t=44; e='Confirmada';   ev='COMMIT' },
                     @{ t=54; e='Inactiva';     ev='200 (access, refresh)' } ) },
        @{ n='Refresco de otro dispositivo'
           estados=@('Vigente', 'Revocado')
           marcas=@( @{ t=0;  e='Vigente' },
                     @{ t=44; e='Revocado'; ev='revoke_all_sessions()' } ) },
        @{ n='Acceso de otro dispositivo'
           estados=@('Vigente', 'Vencido')
           marcas=@( @{ t=0;  e='Vigente' },
                     @{ t=84; e='Vencido'; ev='expira'; r='30 min' } ) }
      )
    }
    # ---- 2.1.3 Comunicacion: los pasos, sobre UNA linea por par ----
    grupos = [ordered]@{
      1 = 'consultar y editar el perfil'
      2 = 'cambiar la contraseña'
      3 = 'excepciones'
    }
    # EA apila bien hasta DOS rotulos por sentido en una misma linea; con
    # tres o mas los encima (GUIA-DIAGRAMAS-EA, seccion 10). Por eso el
    # cambio de contrasena entra por su propia frontera y la autenticacion
    # vive en GestorAutenticacion, como en Violet.
    mensajes = @(
      @{ g=1; d='usuario';  a='pantalla';   m='solicitarPerfil()' },
      @{ g=1; d='pantalla'; a='gestor';     m='obtenerPerfil()' },
      @{ g=1; d='gestor';   a='auth';       m='autenticar(token)' },
      @{ g=1; d='usuario';  a='pantalla';   m='modificar(datos)' },
      @{ g=1; d='pantalla'; a='gestor';     m='actualizar(datos)' },
      @{ g=1; d='gestor';   a='gestor';     m='validarDatos(datos)' },
      @{ g=1; d='gestor';   a='entusuario'; m='guardar(usuario)' },
      @{ g=1; d='gestor';   a='paciente';   m='sincronizar(nombres, telefono)' },
      @{ g=1; d='gestor';   a='bitgestor';  m='registrar(PROFILE_UPDATE)' },
      @{ g=1; d='bitgestor'; a='bitacora';  m='insertar(asiento)' },

      @{ g=2; d='usuario';  a='form';       m='cambiarContrasena(actual, nueva)' },
      @{ g=2; d='form';     a='gestor';     m='cambiarContrasena(actual, nueva)' },
      @{ g=2; d='gestor';   a='entusuario'; m='cambiarContrasena(actual, nueva)' },
      @{ g=2; d='gestor';   a='auth';       m='renovarSesiones(usuario)' },
      @{ g=2; d='auth';     a='token';      m='revocar(token)' },
      @{ g=2; d='gestor';   a='bitgestor';  m='registrar(PASSWORD_CHANGE)' },

      @{ g=3; d='gestor';   a='pantalla';   m='datosInvalidos(campo)' },
      @{ g=3; d='gestor';   a='form';       m='contrasenaActualIncorrecta()' }
    )

    # ---- 2.1.4.2 Secuencia: el mismo caso con el eje del tiempo ----
    # La numeracion se hereda de la comunicacion; las respuestas, que la
    # comunicacion no tiene, van como subnivel (1.3 -> 1.3.1). Contra la
    # entidad va la consulta literal. 'alt' solo donde hay una rama real.
    #   nota = separador de flujo, a la izquierda | msg (o, d, n, ret) |
    #   alt / op (guarda, sin corchetes: los pone EA) / fin
    secuencia = @(
      @{ t='nota'; txt='FLUJO 1 Consultar y editar el perfil' },
      @{ t='msg'; o='usuario';  d='pantalla';   n='1.1: solicitarPerfil()' },
      @{ t='msg'; o='pantalla'; d='gestor';     n='1.2: GET /api/accounts/users/me/()' },
      @{ t='msg'; o='gestor';   d='auth';       n='1.3: autenticar(token)  {el usuario sale del token}' },
      @{ t='msg'; o='auth';     d='entusuario'; n='1.3.1: SELECT * FROM users WHERE id = :token_user_id()' },
      @{ t='msg'; o='entusuario'; d='auth';     n='1.3.2: Usuario(id, organization_id)'; ret=$true },
      @{ t='msg'; o='gestor';   d='pantalla';   n='1.3.3: ProfileOut(perfil, roles)'; ret=$true },
      @{ t='msg'; o='usuario';  d='pantalla';   n='1.4: modificar(datos)' },
      @{ t='msg'; o='pantalla'; d='gestor';     n='1.5: PATCH /api/accounts/users/me/(cambios)' },
      @{ t='msg'; o='gestor';   d='gestor';     n='1.6: validarDatos(datos)  {sólo nombres, teléfono y correo}' },
      @{ t='alt' },
      @{ t='op'; g='sólo campos editables y correo libre' },
      @{ t='msg'; o='gestor';   d='entusuario'; n='1.7a: UPDATE users SET first_name, last_name, phone, email WHERE id = :id()' },
      @{ t='msg'; o='gestor';   d='paciente';   n='1.8a: UPDATE patients SET first_name, last_name, phone WHERE user_id = :id()' },
      @{ t='msg'; o='gestor';   d='bitgestor';  n='1.9a: registrar(PROFILE_UPDATE)  {sin valores}' },
      @{ t='msg'; o='bitgestor'; d='bitacora';  n='1.10a: INSERT INTO audit_log (action, entity, detail)()' },
      @{ t='msg'; o='gestor';   d='pantalla';   n='1.10a.1: ProfileOut(perfil)'; ret=$true },
      @{ t='msg'; o='pantalla'; d='usuario';    n='1.11a: mostrarConfirmacion()'; ret=$true },
      @{ t='op'; g='campo no editable o correo ya usado' },
      @{ t='msg'; o='gestor';   d='pantalla';   n='1.7b: datosInvalidos(campo) -> 400'; ret=$true },
      @{ t='msg'; o='pantalla'; d='usuario';    n='1.8b: mostrarErrorBajoLaCasilla()'; ret=$true },
      @{ t='fin' },
      @{ t='nota'; txt='FLUJO 2 Cambiar la contraseña' },
      @{ t='msg'; o='usuario';  d='form';       n='2.1: cambiarContrasena(actual, nueva, repetida)' },
      @{ t='msg'; o='form';     d='gestor';     n='2.2: POST /api/accounts/users/me/password/()' },
      @{ t='msg'; o='gestor';   d='entusuario'; n='2.3: check_password(actual)' },
      @{ t='msg'; o='entusuario'; d='gestor';   n='2.3.1: bool()'; ret=$true },
      @{ t='alt' },
      @{ t='op'; g='actual correcta y nueva válida' },
      @{ t='msg'; o='gestor';   d='auth';       n='2.4a: validate_password_strength(nueva, usuario)' },
      @{ t='msg'; o='gestor';   d='entusuario'; n='2.5a: UPDATE users SET password = :hash WHERE id = :id()' },
      @{ t='msg'; o='gestor';   d='auth';       n='2.6a: renovarSesiones(usuario)' },
      @{ t='loop'; g='por cada refresco vigente del usuario' },
      @{ t='msg'; o='auth';     d='token';      n='2.7a: INSERT INTO token_blacklist_blacklistedtoken (token_id)()' },
      @{ t='fin' },
      @{ t='msg'; o='auth';     d='gestor';     n='2.8a: tokens_for_user(usuario)  {par nuevo}'; ret=$true },
      @{ t='msg'; o='gestor';   d='bitgestor';  n='2.9a: registrar(PASSWORD_CHANGE)' },
      @{ t='msg'; o='gestor';   d='form';       n='2.10a: 200(access, refresh)'; ret=$true },
      @{ t='msg'; o='form';     d='form';       n='2.11a: guardarTokens(access, refresh)  {la sesión sigue}' },
      @{ t='op'; g='actual incorrecta o nueva repetida' },
      @{ t='msg'; o='gestor';   d='bitgestor';  n='2.4b: registrar(PASSWORD_CHANGE, fallido)' },
      @{ t='msg'; o='gestor';   d='form';       n='2.5b: contrasenaActualIncorrecta() -> 400'; ret=$true },
      @{ t='fin' }
    )
  }
}

# =========================================================================
# 2.1.4.5 Diagramas de NAVEGACION: UNO POR CASO DE USO, con la clave del
# caso en $CASOS_SPRINT2 (el titulo sale de ahi).
#
# No es UML: es la extension UWE. Cada caja es una clase con estereotipo:
#   menu            la pantalla eje que deja el login
#   navigationClass una pantalla; atributos: la ruta y lo que muestra
#   formClass       un formulario; atributos: los campos reales (el 'name')
#   controller      el archivo de vistas del backend; operaciones: las funciones
# NUNCA 'view' ni 'form': son reservados de EA y la caja sale vacia.
#
# Solo las pantallas por las que pasa el caso de uso. Una banda por area:
# la pantalla arriba, sus formularios debajo, el controlador a la derecha.
# La navegacion va en CADENA (menu -build-> pantalla -build-> formulario
# -submit-> controlador), sin flechas de vuelta.
# Las rutas salen de frontend/src/App.tsx y las guardas del 'requiere' de
# frontend/src/componentes/BarraPlataforma.tsx.
# =========================================================================

$NAVEGACION_SPRINT2 = [ordered]@{

  'CU6' = @{
    actor  = 'Usuario'
    nota   = 'CU6 · US-05. Lo usa todo el que entra, de cualquier rol: la entrada «Mi perfil» de BarraPlataforma.tsx no tiene «requiere», sólo RutaProtegida. Los dos formularios son componentes de la misma página Perfil.tsx (DatosDeContacto y CambioDeContrasena); en el móvil, mobile/lib/features/profile/profile_screen.dart. Ninguna ruta lleva identificador: el usuario sale del token.'
    menu   = @{ n='Panel.tsx'; ruta='/panel' }
    publicas = @()
    controladores = @{
      profile = @{ n='accounts/views/profile.py'; ops=@('profile(request)', 'change_password(request)') }
    }
    areas = @(
      @{ guarda='[sesión]'
         vista=@{ n='Perfil.tsx'; ruta='/perfil'; atr=@('document_type', 'document_number', 'roles') }; vistaCtrl='profile'
         forms=@(
           @{ n='DatosDeContacto'; atr=@('first_name', 'last_name', 'phone', 'email'); ctrl='profile' },
           @{ n='CambioDeContrasena'; atr=@('current_password', 'password', 'password_confirmation'); ctrl='profile' }
         ) }
    )
  }
}

# =========================================================================
# Los demás casos de uso del Sprint 2. Se agregan después de crear los dos
# diccionarios, cada uno con su clave; el orden de acá es el de generación.
# =========================================================================

$CASOS_SPRINT2['CU18'] = @{
    cu     = 'CU18'
    nombre = 'Reserva de Ficha Médica'
    us     = 'US-17'
    nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Sólo existe en la web (Disponibilidad.tsx + ModalReservarFicha.tsx); la pantalla móvil de reserva no está hecha (mobile/lib/features/availability/availability_screen.dart:181 dice que la reserva llega en el Sprint 2). El pago con Stripe (US-18) y el comprobante (US-19) no tienen código: no hay app payments ni webhook, así que no se dibuja la Pasarela de Pago y ninguna ficha pasa a confirmed. La ficha nace pending_payment con expires_at = ahora + APPOINTMENT_HOLD_MINUTES, pero nada la marca expired ni la saca de la disponibilidad al vencer: _booked_slots (scheduling/availability.py:62) y el índice uq_appointment_active_slot cuentan toda pending_payment sin mirar expires_at. El diagrama de estado es el flujo de la transacción; los estados de la ficha van en el de tiempo.'
    participantes = @(
      @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2.2 },

      @{ k='pantalla'; n='PantallaDisponibilidad'; rol='boundary'; col=1; f=0.8
         nota='Web: frontend/src/paginas/Disponibilidad.tsx y frontend/src/api/disponibilidad.ts. Llega desde BuscarProfesionales.tsx con ?professional=. Backend: AvailabilityView en scheduling/availability.py. Móvil: mobile/lib/features/availability/ (sólo consulta, sin reserva).'
         atr=@('GET /api/scheduling/availability/ : 200 | 400 | 401 | 403')
         ops=@('disponibilidadConsolidada(filtros, contexto, senal)', 'confirmarReserva(patientId)', 'AvailabilityView.get(request)') },

      @{ k='form';     n='FormularioReserva'; rol='boundary'; col=1; f=3.4
         nota='Web: frontend/src/componentes/ModalReservarFicha.tsx, frontend/src/api/fichas.ts y frontend/src/api/pacientes.ts. Backend: AppointmentViewSet.create en appointments/booking.py y la acción patient-options de patients/dependents.py. Sin par móvil.'
         atr=@('GET /api/patients/dependents/patient-options/ : 200 | 401', 'POST /api/appointments/appointments/ : 201 | 400 | 401 | 403 | 409')
         ops=@('listarOpcionesDePaciente(contexto, senal)', 'reservarFicha(datos, contexto)', 'AppointmentViewSet.create(request)') },

      @{ k='gdisp';    n='GestorDisponibilidad'; rol='control'; col=2; f=0.6
         nota='scheduling/availability.py. Deriva los espacios de cada regla de agenda y les resta los bloqueos y las fichas activas. El horizonte máximo es AVAILABILITY_MAX_HORIZON_DAYS (config/settings.py:252).'
         atr=@()
         ops=@('consolidated_availability(practitioner_id, date_from, date_to, branch_id, now)', 'generate_slots(schedule, date_from, date_to, tz)', '_booked_slots(practitioner_id, date_from, date_to)', '_blocked(start_aware, end_aware, blocks)') },

      @{ k='gres';     n='GestorReserva'; rol='control'; col=2; f=2.6
         nota='appointments/booking.py (book_appointment, en un transaction.atomic con select_for_update sobre la agenda) y appointments/serializers.py (BookAppointmentSerializer). El selector de paciente sale de patient_options en patients/dependents.py.'
         atr=@()
         ops=@('book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)', '_validate_slot_is_real(schedule, starts_at)', 'patient_options(user)') },

      @{ k='auth';     n='GestorAutenticacion'; rol='control'; col=2; f=4.4
         nota='accounts/authentication.py (usuario e inquilino desde el token), scheduling/permissions.py (CanReadSlots) y appointments/permissions.py (CanCreateAppointments).'
         atr=@()
         ops=@('authenticate(request)', 'has_permission(code)') },

      @{ k='agenda';   n='Agenda'; rol='entity'; col=3; f=0
         nota='Tabla schedules (la regla de agenda de US-13). Los bloqueos de US-14 viven en schedule_blocks y se leen en la misma consulta por rango.'
         atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'valid_from : date', 'valid_until : date', 'is_active : boolean')
         ops=@('filter(practitioner_id, is_active)', 'select_for_update()') },

      @{ k='ficha';    n='Ficha'; rol='entity'; col=3; f=1.4
         nota='Tabla appointments. UNIQUE parcial uq_appointment_active_slot (schedule_id, starts_at) WHERE status IN (pending_payment, confirmed): dos reservas del mismo turno terminan en una fila y un IntegrityError.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar(16)', 'expires_at : timestamptz')
         ops=@('filter(practitioner_id, status__in=ACTIVE_STATUSES)', 'create(status=pending_payment, expires_at)') },

      @{ k='entpac';   n='Paciente'; rol='entity'; col=3; f=2.8
         nota='Tabla patients: el titular y sus dependientes (guardian_id), de US-07.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'is_active : boolean')
         ops=@('filter(pk, organization, is_active)') },

      @{ k='prof';     n='Profesional'; rol='entity'; col=3; f=4.2
         nota='Tabla practitioners (US-12).'
         atr=@('id : uuid', 'organization_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'is_active : boolean')
         ops=@('filter(pk, organization, is_active)') },

      @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=5.4
         nota='Tabla branches. Su timezone fija el corte de hora pasada y la reconstrucción del turno.'
         atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'timezone : varchar(40)', 'is_active : boolean')
         ops=@('filter(pk, organization, is_active)') }
    )

    estado = @{
      estados = @(
        @{ k='ini';    tipo='inicial'; col=0; f=0 },
        @{ k='aut';    n='Autenticar Paciente';             col=0; f=2 },
        @{ k='fin401'; tipo='final';   col=0; f=4.5 },
        @{ k='menu';   n='Seleccionar operación';           col=1; f=2 },
        @{ k='disp';   n='Desplegar disponibilidad';        col=2; f=0 },
        @{ k='cap';    n='Capturar espacio y paciente';     col=2; f=2 },
        @{ k='val';    n='Validar datos';                   col=3; f=2 },
        @{ k='lock';   n='Bloquear agenda y validar turno'; col=3; f=4 },
        @{ k='error';  n='Informar error';                  col=4; f=5.5 },
        @{ k='ok';     n='Transacción completada';          col=4; f=1 },
        @{ k='fin';    tipo='final';   col=4; f=3 }
      )
      transiciones = @(
        @{ de='ini';   a='aut' },
        @{ de='aut';   a='menu';   r='[token y permiso] {IsAuthenticated + CanReadSlots, availability.py:251}' },
        @{ de='aut';   a='fin401'; r='[sin token o sin permiso] {401 | 403}' },
        @{ de='menu';  a='disp';   r='[consultar] {GET /scheduling/availability/}' },
        @{ de='menu';  a='cap';    r='[reservar] {CanCreateAppointments, booking.py:171}' },
        @{ de='disp';  a='ok';     r='[rango válido] / consolidated_availability() {availability.py:266}' },
        @{ de='disp';  a='error';  r='[rango invertido o mayor a 30 días] {400 availability.py:115, :119}' },
        @{ de='cap';   a='val';    r='confirmarReserva() {POST /appointments/appointments/}' },
        @{ de='val';   a='lock';   r='[paciente, profesional y sucursal activos y turno futuro] / select_for_update() {booking.py:113}' },
        @{ de='val';   a='error';  r='[dato inválido o turno pasado] {400 booking.py:87, :107}' },
        @{ de='lock';  a='ok';     r='[turno real y libre] / create(pending_payment) {201 booking.py:130}' },
        @{ de='lock';  a='error';  r='[turno no real u ocupado] {400 booking.py:127, 409 :143}' },
        @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
        @{ de='ok';    a='fin' }
      )
    }

    tiempo = @{
      escenario = 'reservar un turno y dejarlo sin pagar'
      nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:257), que fija expires_at en appointments/booking.py:140. La ficha nace pending_payment en el mismo COMMIT y no sale de ahí: confirmed lo pondría el webhook de Stripe (US-18, sin código) y expired no lo escribe nada. Por eso, vencido el plazo, el turno sigue ocupado: _booked_slots (scheduling/availability.py:62) y uq_appointment_active_slot (appointments/models.py:113) no miran expires_at.'
      lineas = @(
        @{ n='Transacción'
           estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=6;  e='Autenticando'; ev='POST /appointments/appointments/' },
                     @{ t=16; e='Validando';    ev='book_appointment()' },
                     @{ t=26; e='Escribiendo';  ev='select_for_update()' },
                     @{ t=36; e='Confirmada';   ev='COMMIT' },
                     @{ t=44; e='Inactiva';     ev='201 (Ficha)' } ) },
        @{ n='Ficha'
           estados=@('Sin ficha', 'pending_payment', 'confirmed', 'expired')
           marcas=@( @{ t=0;  e='Sin ficha' },
                     @{ t=36; e='pending_payment'; ev='create()' } ) },
        @{ n='Plazo de pago'
           estados=@('Sin plazo', 'Corriendo', 'Vencido')
           marcas=@( @{ t=0;  e='Sin plazo' },
                     @{ t=36; e='Corriendo'; ev='expires_at' },
                     @{ t=84; e='Vencido';   ev='vence'; r='15 min' } ) },
        @{ n='Turno en disponibilidad'
           estados=@('Libre', 'Ocupado')
           marcas=@( @{ t=0;  e='Libre' },
                     @{ t=36; e='Ocupado'; ev='_booked_slots()' } ) }
      )
    }

    grupos = [ordered]@{
      1 = 'consultar la disponibilidad'
      2 = 'reservar la ficha'
      3 = 'excepciones'
    }

    mensajes = @(
      @{ g=1; d='paciente'; a='pantalla'; m='elegirProfesional(profesional, desde, hasta, sucursal)' },
      @{ g=1; d='pantalla'; a='gdisp';    m='consultarDisponibilidad(practitioner, from, to, branch)' },
      @{ g=1; d='gdisp';    a='auth';     m='autorizar(scheduling.slot.read)' },
      @{ g=1; d='gdisp';    a='agenda';   m='derivarEspacios(rango)' },
      @{ g=1; d='gdisp';    a='ficha';    m='restarOcupados(ACTIVE_STATUSES)' },

      @{ g=2; d='paciente'; a='pantalla'; m='elegirEspacio(slot)' },
      @{ g=2; d='pantalla'; a='form';     m='abrirModal(slot)' },
      @{ g=2; d='form';     a='gres';     m='listarOpcionesDePaciente()' },
      @{ g=2; d='paciente'; a='form';     m='confirmarReserva(paciente)' },
      @{ g=2; d='form';     a='gres';     m='reservar(paciente, schedule, starts_at)' },
      @{ g=2; d='gres';     a='auth';     m='autorizar(appointments.appointment.create)' },
      @{ g=2; d='gres';     a='entpac';   m='validarPaciente(patient_id)' },
      @{ g=2; d='gres';     a='prof';     m='validarProfesional(practitioner_id)' },
      @{ g=2; d='gres';     a='sucursal'; m='validarSucursal(branch_id)' },
      @{ g=2; d='gres';     a='agenda';   m='bloquearAgenda(schedule_id)' },
      @{ g=2; d='gres';     a='gres';     m='validarTurnoReal(starts_at)' },
      @{ g=2; d='gres';     a='ficha';    m='crear(pending_payment, expires_at)' },

      @{ g=3; d='gdisp';    a='pantalla'; m='rangoInvalido() -> 400' },
      @{ g=3; d='gres';     a='form';     m='reservaInvalida(code) -> 400' },
      @{ g=3; d='gres';     a='form';     m='turnoOcupado() -> 409' }
    )

    secuencia = @(
      @{ t='nota'; txt='FLUJO 1 Consultar la disponibilidad' },
      @{ t='msg'; o='paciente'; d='pantalla'; n='1.1: elegirProfesional(profesional, desde, hasta, sucursal)' },
      @{ t='msg'; o='pantalla'; d='gdisp';    n='1.2: GET /api/scheduling/availability/?practitioner=&from=&to=&branch=()' },
      @{ t='msg'; o='gdisp';    d='auth';     n='1.3: authenticate(request)  {IsAuthenticated, CanReadSlots}' },
      @{ t='msg'; o='gdisp';    d='agenda';   n='1.4: SELECT * FROM schedules WHERE practitioner_id = :p AND is_active AND valid_from <= :to()' },
      @{ t='msg'; o='agenda';   d='gdisp';    n='1.4.1: list(Schedule)'; ret=$true },
      @{ t='msg'; o='gdisp';    d='agenda';   n='1.5: SELECT * FROM schedule_blocks WHERE is_active AND starts_at < :fin AND ends_at > :inicio()' },
      @{ t='msg'; o='gdisp';    d='ficha';    n='1.6: SELECT schedule_id, starts_at FROM appointments WHERE practitioner_id = :p AND status IN (pending_payment, confirmed)()' },
      @{ t='msg'; o='ficha';    d='gdisp';    n='1.6.1: set(schedule_id, starts_at)'; ret=$true },
      @{ t='loop'; g='por cada regla de agenda y cada espacio del rango' },
      @{ t='msg'; o='gdisp';    d='gdisp';    n='1.7: generate_slots(schedule, desde, hasta)  {descarta pasados, bloqueados y ocupados}' },
      @{ t='fin' },
      @{ t='msg'; o='gdisp';    d='pantalla'; n='1.7.1: 200(days, slots)'; ret=$true },
      @{ t='msg'; o='pantalla'; d='paciente'; n='1.8: mostrarGrilla(espacios)'; ret=$true },

      @{ t='nota'; txt='FLUJO 2 Reservar la ficha' },
      @{ t='msg'; o='paciente'; d='pantalla'; n='2.1: elegirEspacio(slot)' },
      @{ t='msg'; o='pantalla'; d='form';     n='2.2: abrirModal(slot)' },
      @{ t='msg'; o='form';     d='gres';     n='2.3: GET /api/patients/dependents/patient-options/()' },
      @{ t='msg'; o='gres';     d='form';     n='2.3.1: opciones(titular, dependientes)'; ret=$true },
      @{ t='msg'; o='paciente'; d='form';     n='2.4: confirmarReserva(paciente)' },
      @{ t='msg'; o='form';     d='gres';     n='2.5: POST /api/appointments/appointments/(patient, practitioner, branch, schedule, starts_at)' },
      @{ t='msg'; o='gres';     d='auth';     n='2.6: authenticate(request)  {CanCreateAppointments}' },
      @{ t='msg'; o='gres';     d='entpac';   n='2.7: SELECT * FROM patients WHERE id = :patient AND organization_id = :org AND is_active()' },
      @{ t='msg'; o='gres';     d='prof';     n='2.8: SELECT * FROM practitioners WHERE id = :practitioner AND organization_id = :org AND is_active()' },
      @{ t='msg'; o='gres';     d='sucursal'; n='2.9: SELECT * FROM branches WHERE id = :branch AND organization_id = :org AND is_active()' },
      @{ t='msg'; o='gres';     d='agenda';   n='2.10: SELECT * FROM schedules WHERE id = :schedule AND branch_id = :branch AND practitioner_id = :practitioner FOR UPDATE()' },
      @{ t='msg'; o='agenda';   d='gres';     n='2.10.1: Schedule(branch)'; ret=$true },
      @{ t='msg'; o='gres';     d='gres';     n='2.11: _validate_slot_is_real(schedule, starts_at)  {no confía en la hora del cliente}' },
      @{ t='alt' },
      @{ t='op'; g='turno real y libre' },
      @{ t='msg'; o='gres';     d='ficha';    n='2.12a: INSERT INTO appointments (status = pending_payment, expires_at = now + 15 min)()' },
      @{ t='msg'; o='gres';     d='form';     n='2.12a.1: 201(Ficha pending_payment)'; ret=$true },
      @{ t='msg'; o='form';     d='paciente'; n='2.13a: mostrarAviso(quedó pendiente de pago)'; ret=$true },
      @{ t='op'; g='otra ficha activa en el mismo turno' },
      @{ t='msg'; o='gres';     d='ficha';    n='2.12b: INSERT INTO appointments -> IntegrityError uq_appointment_active_slot()' },
      @{ t='msg'; o='gres';     d='form';     n='2.13b: turnoOcupado() -> 409'; ret=$true },
      @{ t='msg'; o='form';     d='pantalla'; n='2.14b: recargarDisponibilidad()  {cierra el modal}' },
      @{ t='op'; g='paciente, profesional, sucursal, agenda o turno inválidos' },
      @{ t='msg'; o='gres';     d='form';     n='2.12c: reservaInvalida(code) -> 400'; ret=$true },
      @{ t='msg'; o='form';     d='paciente'; n='2.13c: mostrarAviso(code)'; ret=$true },
      @{ t='fin' }
    )
}

$NAVEGACION_SPRINT2['CU18'] = @{
    actor  = 'Paciente'
    nota   = 'CU18 · US-17. Navegación WEB: la reserva no existe en el móvil (mobile/lib/features/ no tiene appointments). Búsqueda -> disponibilidad -> reserva; Mis fichas muestra la ficha pendiente de pago. No hay pantalla de pago ni de comprobante: US-18 y US-19 no tienen código. ModalReservarFicha es un componente que abre Disponibilidad.tsx con el espacio elegido; sus campos son el cuerpo del POST, y el selector de paciente sale de patients/dependents.py (patient-options). Rutas de frontend/src/App.tsx; guardas del requiere de BarraPlataforma.tsx.'
    menu   = @{ n='Panel.tsx'; ruta='/panel' }
    publicas = @()
    controladores = @{
      search       = @{ n='catalog/search.py'; ops=@('ProfessionalSearchView.get_queryset()', 'get_next_available_slot(obj)') }
      availability = @{ n='scheduling/availability.py'; ops=@('AvailabilityView.get(request)', 'consolidated_availability(practitioner_id, date_from, date_to, branch_id)', 'generate_slots(schedule, date_from, date_to, tz)', '_booked_slots(practitioner_id, date_from, date_to)') }
      booking      = @{ n='appointments/booking.py'; ops=@('AppointmentViewSet.create(request)', 'AppointmentViewSet.get_queryset()', 'book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)', '_validate_slot_is_real(schedule, starts_at)') }
    }
    areas = @(
      @{ guarda='[sesión + catalog.professional.read]'
         vista=@{ n='BuscarProfesionales.tsx'; ruta='/buscar-profesionales'; atr=@('q', 'specialty', 'branch', 'next_available_slot') }; vistaCtrl='search'
         forms=@() },
      @{ guarda='[sesión + scheduling.slot.read]'; desde='BuscarProfesionales.tsx'
         vista=@{ n='Disponibilidad.tsx'; ruta='/disponibilidad?professional='; atr=@('practitioner', 'from', 'to', 'branch') }; vistaCtrl='availability'
         forms=@(
           @{ n='ModalReservarFicha'; atr=@('patient', 'practitioner', 'branch', 'schedule', 'starts_at'); ctrl='booking' }
         ) },
      @{ guarda='[sesión + appointments.appointment.read]'
         vista=@{ n='MisFichas.tsx'; ruta='/mis-fichas'; atr=@('practitioner_name', 'branch_name', 'starts_at', 'status') }; vistaCtrl='booking'
         forms=@() }
    )
}

$CASOS_SPRINT2['CU21'] = @{
  cu = 'CU21'; nombre = 'Cancelación / Reprogramación de Ficha'; us = 'US-20'
  nota = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Sólo web: la pantalla móvil de US-20 todavía no existe (no hay mobile/lib/features/appointments/). La anticipación (cancellation_notice_hours, tenancy/models.py:99) no bloquea la cancelación: sólo decide refund_eligible (changes.py:66). La devolución no se ejecuta: no hay app de pagos, así que no hay Pasarela de Pago. Reprogramar no deja asiento en la bitácora. Estado: flujo de la transacción; los estados de la ficha van en el diagrama de tiempo.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2.2 },

    @{ k='pantalla'; n='PantallaMisFichas'; rol='boundary'; col=1; f=1
       nota='Web: frontend/src/paginas/MisFichas.tsx y frontend/src/api/fichas.ts. Móvil: sin implementar. Backend: AppointmentViewSet en appointments/booking.py (el listado) y CancelAppointmentView en appointments/changes.py.'
       atr=@('GET /api/appointments/appointments/ : 200 | 401 | 403', 'POST /api/appointments/appointments/{id}/cancel/ : 200 | 400 | 401 | 403 | 404')
       ops=@('misFichas(contexto, senal)', 'cancelarFicha(id, contexto)', 'cancelar(ficha)', 'list(request)', 'post(request, pk)') },

    @{ k='form'; n='FormularioReprogramacion'; rol='boundary'; col=1; f=3.4
       nota='Web: frontend/src/componentes/ModalReprogramarFicha.tsx, confirmarReprogramacion de MisFichas.tsx, frontend/src/api/fichas.ts y frontend/src/api/disponibilidad.ts. Móvil: sin implementar. Backend: RescheduleAppointmentView en appointments/changes.py y AvailabilityView en scheduling/availability.py.'
       atr=@('GET /api/scheduling/availability/ : 200 | 400 | 401 | 403', 'POST /api/appointments/appointments/{id}/reschedule/ : 200 | 400 | 401 | 403 | 404 | 409')
       ops=@('disponibilidadConsolidada(parametros, contexto, senal)', 'reprogramarFicha(id, datos, contexto)', 'confirmarReprogramacion(slot)', 'get(request)', 'post(request, pk)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token) y appointments/permissions.py (CanCancelAppointments, CanRescheduleAppointments: appointments.appointment.cancel / .reschedule, sembrados al rol Paciente en accounts/migrations/0006).'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)', 'has_permission(code)') },

    @{ k='gestor'; n='GestorCambiosFicha'; rol='control'; col=2; f=1.6
       nota='appointments/changes.py, appointments/mixins.py (owns_appointment) y appointments/serializers.py (RescheduleAppointmentSerializer). Decide si corresponde devolución; reprogramar es liberar y volver a tomar en un solo transaction.atomic().'
       atr=@()
       ops=@('_get_appointment_or_404(request, pk)', '_puede_operar(user, appointment)', 'owns_appointment(user, appointment)', '_assert_cancellable(appointment, now)', '_notice(appointment, now)', 'cancel_appointment(appointment, now)', 'reschedule_appointment(appointment, branch_id, schedule_id, starts_at, now)') },

    @{ k='reserva'; n='GestorReserva'; rol='control'; col=2; f=3.4
       nota='appointments/booking.py (la reserva de US-17, que reprogramar reutiliza) y scheduling/availability.py (los espacios libres de US-15). Cancelar libera el turno porque _booked_slots sólo cuenta ACTIVE_STATUSES.'
       atr=@()
       ops=@('get_queryset()', 'consolidated_availability(practitioner_id, date_from, date_to, branch_id)', '_booked_slots(practitioner_id, date_from, date_to)', 'book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)', '_validate_slot_is_real(schedule, starts_at)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
       nota='Tabla audit_log. La escribe record() de audit/services.py con Action.APPOINTMENT_CANCEL; sólo la cancelación deja asiento.'
       atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='organizacion'; n='Organizacion'; rol='entity'; col=3; f=1.2
       nota='Tabla organizations. cancellation_notice_hours es la política de anticipación de cada centro médico, 24 por omisión.'
       atr=@('id : uuid', 'name : varchar(120)', 'timezone : varchar(40)', 'cancellation_notice_hours : integer')
       ops=@('leer(cancellation_notice_hours)') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=2.4
       nota='Tabla appointments. uq_appointment_active_slot: un solo turno activo (pending_payment o confirmed) por (schedule_id, starts_at); al cancelar o reprogramar, el índice libera el turno en el acto.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)', 'expires_at : timestamptz', 'cancelled_at : timestamptz', 'cancellation_reason : varchar(20)', 'refund_eligible : boolean', 'rescheduled_from_id : uuid')
       ops=@('filter(pk, organization)', 'save(update_fields)', 'create(...)') },

    @{ k='agenda'; n='Agenda'; rol='entity'; col=3; f=3.6
       nota='Tabla schedules: la regla de agenda de la que sale cada turno (US-13). Se bloquea con select_for_update() al tomar el turno nuevo.'
       atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'is_active : boolean')
       ops=@('filter(practitioner, is_active)', 'select_for_update()') }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';         col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar operación';       col=1; f=2 },
      @{ k='ver';    n='Desplegar mis fichas';        col=2; f=0 },
      @{ k='capc';   n='Confirmar cancelación';       col=2; f=2 },
      @{ k='capr';   n='Elegir nuevo turno';          col=2; f=4 },
      @{ k='valf';   n='Validar ficha';               col=3; f=2 },
      @{ k='valt';   n='Validar turno';               col=3; f=4 },
      @{ k='error';  n='Informar error';              col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';      col=4; f=1 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token válido y permiso] {CanCancelAppointments, changes.py:146, :179}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='ver';    r='[consultar] {GET /appointments/appointments/}' },
      @{ de='menu';  a='capc';   r='[cancelar] {MisFichas.tsx:80}' },
      @{ de='menu';  a='capr';   r='[reprogramar] {GET /scheduling/availability/}' },
      @{ de='capc';  a='valf';   r='aceptar() {POST .../cancel/}' },
      @{ de='capr';  a='valf';   r='confirmar(slot) {POST .../reschedule/}' },
      @{ de='valf';  a='ok';     r='[cancelar, activa y futura] / refund_eligible = notice >= umbral {changes.py:66}' },
      @{ de='valf';  a='valt';   r='[reprogramar, activa y futura] / transaction.atomic() {changes.py:91}' },
      @{ de='valf';  a='error';  r='[inexistente, ajena, no activa o pasada] {404 | 403 | 400 changes.py:150, :155, :39, :44}' },
      @{ de='valt';  a='ok';     r='[turno real y libre] / book_appointment(), status = rescheduled {changes.py:93, :112}' },
      @{ de='valt';  a='error';  r='[turno inválido u ocupado] / ROLLBACK {400 booking.py:66, 409 changes.py:211}' },
      @{ de='ver';   a='ok' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'cancelar una ficha confirmada fuera del plazo de anticipación'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 24 h = cancellation_notice_hours por omisión (tenancy/models.py:99), que cada organización cambia; el umbral se arma en changes.py:61 y se compara en changes.py:66 (refund_eligible = notice >= umbral). Pasado el plazo se puede cancelar igual, sin devolución; pasada la hora de la cita, _assert_cancellable rechaza con ficha_pasada (changes.py:44). El turno queda libre en el mismo COMMIT: _booked_slots sólo cuenta ACTIVE_STATUSES (scheduling/availability.py:51, appointments/models.py:35).'
    lineas = @(
      @{ n='Plazo de devolución'
         estados=@('Abierto', 'Cerrado', 'Cita pasada')
         marcas=@( @{ t=0;  e='Abierto' },
                   @{ t=20; e='Cerrado';     ev='starts_at - umbral'; r='24 h' },
                   @{ t=84; e='Cita pasada'; ev='starts_at' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=30; e='Autenticando'; ev='POST .../cancel/' },
                   @{ t=40; e='Validando';    ev='_assert_cancellable()' },
                   @{ t=50; e='Escribiendo';  ev='save()' },
                   @{ t=58; e='Confirmada';   ev='COMMIT' },
                   @{ t=66; e='Inactiva';     ev='200 (refund_eligible)' } ) },
      @{ n='Ficha'
         estados=@('confirmed', 'cancelled')
         marcas=@( @{ t=0;  e='confirmed' },
                   @{ t=58; e='cancelled'; ev='refund_eligible = false' } ) },
      @{ n='Turno'
         estados=@('Ocupado', 'Libre')
         marcas=@( @{ t=0;  e='Ocupado' },
                   @{ t=58; e='Libre'; ev='_booked_slots()' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'consultar y cancelar la ficha'
    2 = 'reprogramar la ficha'
    3 = 'excepciones'
  }

  mensajes = @(
    @{ g=1; d='paciente'; a='pantalla';     m='solicitarMisFichas()' },
    @{ g=1; d='pantalla'; a='reserva';      m='listarFichas()' },
    @{ g=1; d='paciente'; a='pantalla';     m='cancelar(ficha)' },
    @{ g=1; d='pantalla'; a='gestor';       m='cancelar(id)' },
    @{ g=1; d='gestor';   a='auth';         m='verificarPermiso(cancel)' },
    @{ g=1; d='gestor';   a='organizacion'; m='leerAnticipacion()' },
    @{ g=1; d='gestor';   a='ficha';        m='marcarCancelada(refund_eligible)' },
    @{ g=1; d='gestor';   a='bitacora';     m='registrar(APPOINTMENT_CANCEL)' },

    @{ g=2; d='paciente'; a='form';         m='reprogramar(ficha)' },
    @{ g=2; d='form';     a='reserva';      m='consultarDisponibilidad(practitioner, from, to)' },
    @{ g=2; d='reserva';  a='agenda';       m='leerAgendas(practitioner)' },
    @{ g=2; d='paciente'; a='form';         m='elegirTurno(slot)' },
    @{ g=2; d='form';     a='gestor';       m='reprogramar(id, turno)' },
    @{ g=2; d='gestor';   a='auth';         m='verificarPermiso(reschedule)' },
    @{ g=2; d='gestor';   a='reserva';      m='tomarTurno(turno)' },
    @{ g=2; d='reserva';  a='agenda';       m='bloquearAgenda(schedule)' },
    @{ g=2; d='reserva';  a='ficha';        m='crearFicha(turno)' },
    @{ g=2; d='gestor';   a='ficha';        m='marcarReprogramada(vieja, nueva)' },

    @{ g=3; d='gestor';   a='pantalla';     m='fichaNoCancelable(code)' },
    @{ g=3; d='gestor';   a='form';         m='turnoNoDisponible(code)' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Consultar y cancelar la ficha' },
    @{ t='msg'; o='paciente'; d='pantalla';     n='1.1: solicitarMisFichas()' },
    @{ t='msg'; o='pantalla'; d='reserva';      n='1.2: GET /api/appointments/appointments/()' },
    @{ t='msg'; o='reserva';  d='ficha';        n='1.2.1: SELECT * FROM appointments WHERE organization_id = :org AND (patient_id = :pac OR patient_id IN (SELECT id FROM patients WHERE guardian_id = :pac))()' },
    @{ t='msg'; o='reserva';  d='pantalla';     n='1.2.2: 200 (list(Ficha))'; ret=$true },
    @{ t='msg'; o='paciente'; d='pantalla';     n='1.3: cancelar(ficha)  {window.confirm}' },
    @{ t='msg'; o='pantalla'; d='gestor';       n='1.4: POST /api/appointments/appointments/{id}/cancel/()' },
    @{ t='msg'; o='gestor';   d='auth';         n='1.5: verificarPermiso(appointments.appointment.cancel)' },
    @{ t='msg'; o='auth';     d='gestor';       n='1.5.1: has_permission(code) -> True'; ret=$true },
    @{ t='msg'; o='gestor';   d='ficha';        n='1.5.2: SELECT * FROM appointments JOIN organizations, patients WHERE id = :pk AND organization_id = :org()' },
    @{ t='msg'; o='ficha';    d='gestor';       n='1.5.3: Ficha(status, starts_at, patient_id)'; ret=$true },
    @{ t='msg'; o='gestor';   d='gestor';       n='1.5.4: _puede_operar(user, ficha)  {suya o de su dependiente}' },
    @{ t='alt' },
    @{ t='op'; g='ficha propia, activa y futura' },
    @{ t='msg'; o='gestor';   d='organizacion'; n='1.6a: SELECT cancellation_notice_hours FROM organizations WHERE id = :organization_id()  {viene en el JOIN de 1.5.2}' },
    @{ t='msg'; o='gestor';   d='ficha';        n='1.7a: UPDATE appointments SET status = ''cancelled'', cancelled_at, cancellation_reason = ''patient'', refund_eligible = (notice >= umbral) WHERE id = :id()' },
    @{ t='msg'; o='gestor';   d='bitacora';     n='1.8a: INSERT INTO audit_log (action = appointment.cancel, detail = refund_eligible)()' },
    @{ t='msg'; o='gestor';   d='pantalla';     n='1.8a.1: 200 (Ficha, refund_eligible)'; ret=$true },
    @{ t='msg'; o='pantalla'; d='paciente';     n='1.9a: mostrarAviso(corresponde devolución o no)'; ret=$true },
    @{ t='op'; g='ficha inexistente, ajena, no activa o pasada' },
    @{ t='msg'; o='gestor';   d='pantalla';     n='1.6b: fichaNoCancelable(code) -> 404 | 403 | 400'; ret=$true },
    @{ t='msg'; o='pantalla'; d='paciente';     n='1.7b: mostrarError(detail)'; ret=$true },
    @{ t='fin' },
    @{ t='nota'; txt='FLUJO 2 Reprogramar la ficha' },
    @{ t='msg'; o='paciente'; d='form';         n='2.1: reprogramar(ficha)' },
    @{ t='msg'; o='form';     d='reserva';      n='2.2: GET /api/scheduling/availability/?practitioner&from&to(hoy, hoy + 14)' },
    @{ t='msg'; o='reserva';  d='agenda';       n='2.3: SELECT * FROM schedules WHERE practitioner_id = :p AND is_active()' },
    @{ t='msg'; o='reserva';  d='ficha';        n='2.3.1: SELECT schedule_id, starts_at FROM appointments WHERE status IN (''pending_payment'', ''confirmed'')()' },
    @{ t='msg'; o='reserva';  d='form';         n='2.3.2: 200 (espacios por día)'; ret=$true },
    @{ t='msg'; o='paciente'; d='form';         n='2.4: elegirTurno(slot)' },
    @{ t='msg'; o='form';     d='gestor';       n='2.5: POST /api/appointments/appointments/{id}/reschedule/(branch, schedule, starts_at)' },
    @{ t='msg'; o='gestor';   d='auth';         n='2.6: verificarPermiso(appointments.appointment.reschedule)' },
    @{ t='msg'; o='gestor';   d='gestor';       n='2.6.1: _assert_cancellable(ficha, now)  {mismo SELECT y _puede_operar del flujo 1}' },
    @{ t='msg'; o='gestor';   d='reserva';      n='2.7: book_appointment(organization, patient_id, branch_id, schedule_id, starts_at)  {dentro de transaction.atomic()}' },
    @{ t='msg'; o='reserva';  d='agenda';       n='2.8: SELECT * FROM schedules WHERE id = :schedule FOR UPDATE()' },
    @{ t='msg'; o='reserva';  d='reserva';      n='2.8.1: _validate_slot_is_real(schedule, starts_at)' },
    @{ t='loop'; g='por cada espacio que generate_slots arma ese día' },
    @{ t='msg'; o='reserva';  d='reserva';      n='2.8.2: comparar(slot_start, starts_at)  {booking.py:63}' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='turno real y libre' },
    @{ t='msg'; o='reserva';  d='ficha';        n='2.9a: INSERT INTO appointments (status = ''pending_payment'', expires_at = now + 15 min)()' },
    @{ t='msg'; o='reserva';  d='gestor';       n='2.9a.1: Ficha(nueva)'; ret=$true },
    @{ t='msg'; o='gestor';   d='ficha';        n='2.10a: UPDATE appointments SET status = ''confirmed'', expires_at = NULL WHERE id = :nueva  {sólo si la vieja estaba confirmada}()' },
    @{ t='msg'; o='gestor';   d='ficha';        n='2.10a.1: UPDATE appointments SET status = ''rescheduled'' WHERE id = :vieja; SET rescheduled_from = :vieja WHERE id = :nueva()' },
    @{ t='msg'; o='gestor';   d='form';         n='2.11a: 200 (Ficha nueva)'; ret=$true },
    @{ t='msg'; o='form';     d='paciente';     n='2.12a: mostrarAviso(Ficha reprogramada)'; ret=$true },
    @{ t='op'; g='turno inválido u ocupado' },
    @{ t='msg'; o='reserva';  d='gestor';       n='2.9b: ValidationError(turno_invalido) | SlotAlreadyTaken()'; ret=$true },
    @{ t='msg'; o='gestor';   d='form';         n='2.10b: turnoNoDisponible(code) -> 400 | 409  {ROLLBACK: la ficha original queda intacta}'; ret=$true },
    @{ t='fin' }
  )
}

$CASOS_SPRINT2['CU25'] = @{
    cu     = 'CU25'
    nombre = 'Registro de Atención Médica'
    us     = 'US-24'
    nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Sólo web: no hay pantalla móvil del médico (mobile/lib no tiene nada de encounters). Tener el permiso no alcanza: además hay que ser el profesional de la ficha (services.is_own, practitioner_of), y un encuentro ajeno responde 404, no 403. El encuentro cuelga de la ficha (OneToOne) y copia de ella paciente, profesional y sucursal. Firmado no se edita: lo impone también la base con el trigger trg_encounters_inmutable (migrations/0002_rls_e_inmutabilidad.py:90) y las correcciones van como enmienda. Estado: flujo de la transacción, como el ejemplo de cátedra; los estados del encuentro (draft, signed) y de la ficha (confirmed, attended) van en el diagrama de tiempo. No implementado: el estado no_show (Ausente) existe en appointments/models.py:30 pero ningún código lo asigna; tampoco hay plazo para firmar un borrador.'

    participantes = @(
      @{ k='medico';   n='Médico'; rol='actor'; col=0; f=2 },

      @{ k='agenda';   n='PantallaAgendaAtencion'; rol='boundary'; col=1; f=0.6
         nota='Web: frontend/src/paginas/AgendaAtencion.tsx y frontend/src/api/atencion.ts. Sin pantalla móvil. Backend: AgendaView y EncounterOpenView en encounters/views.py.'
         atr=@('GET /api/encounters/agenda/?date= : 200 | 400 | 403', 'POST /api/encounters/ : 201 | 200 | 400 | 404 | 409')
         ops=@('verAgenda(fecha, contexto)', 'abrirAtencion(fichaId, contexto)', 'AgendaView.get(request)', 'EncounterOpenView.post(request)') },

      @{ k='form';     n='FormularioAtencion'; rol='boundary'; col=1; f=2.2
         nota='Web: frontend/src/paginas/Atencion.tsx (el formulario de las cinco secciones y el diálogo de firma) y frontend/src/api/atencion.ts. Backend: EncounterDetailView y EncounterSignView en encounters/views.py.'
         atr=@('GET /api/encounters/<id>/ : 200 | 404', 'PATCH /api/encounters/<id>/ : 200 | 400 | 404 | 409', 'POST /api/encounters/<id>/sign/ : 200 | 400 | 404 | 409')
         ops=@('verEncuentro(id, contexto)', 'guardarBorrador(id, datos, contexto)', 'firmarEncuentro(id, contexto)', 'EncounterDetailView.get(request, pk)', 'EncounterDetailView.patch(request, pk)', 'EncounterSignView.post(request, pk)') },

      @{ k='fenm';     n='FormularioEnmienda'; rol='boundary'; col=1; f=3.8
         nota='El formulario «Agregar una enmienda» de frontend/src/paginas/Atencion.tsx: sólo aparece con el encuentro firmado y el permiso encounters.encounter.amend. Backend: EncounterAmendView en encounters/views.py.'
         atr=@('POST /api/encounters/<id>/amendments/ : 201 | 400 | 404 | 409')
         ops=@('agregarEnmienda(id, section, text, contexto)', 'EncounterAmendView.post(request, pk)') },

      @{ k='gestor';   n='GestorAtencion'; rol='control'; col=2; f=2
         nota='encounters/services.py (las reglas), encounters/views.py (_own_encounter, _audit), encounters/serializers.py y encounters/permissions.py. Decide quién atiende qué: sólo el profesional de la ficha, sólo una ficha en pie y no antes del día del turno.'
         atr=@()
         ops=@('practitioner_of(user)', 'is_own(user, encounter)', 'local_today(appointment)', 'appointment_local_date(appointment)', 'open_encounter(user, appointment)', 'update_draft(encounter, data)', 'sign(encounter, user)', 'amend(encounter, user, section, text)', '_own_encounter(request, pk)') },

      @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=0
         nota='audit/services.py. Encola el asiento y lo escribe el middleware al terminar la petición. Guarda quién abrió qué historia, nunca su contenido (encounters/views.py:62).'
         atr=@()
         ops=@('record(request, action, entity, entity_id, detail)') },

      @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
         nota='Tabla audit_log.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
         ops=@('insert(asiento)') },

      @{ k='prof';     n='Profesional'; rol='entity'; col=3; f=1
         nota='Tabla practitioners. El vínculo user_id es el que dice si quien pide es el profesional de la ficha; se consulta en cada petición.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'is_active : boolean')
         ops=@('filter(user, is_active).first()') },

      @{ k='ficha';    n='Ficha'; rol='entity'; col=3; f=2
         nota='Tabla appointments (US-17). Sólo se atienden pending_payment, confirmed y attended (ATTENDABLE_STATUSES, services.py:36). Firmar la pasa a attended.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)', 'expires_at : timestamptz')
         ops=@('filter(practitioner, starts_at, status__in)', 'select_for_update().get(pk)', 'save(status)') },

      @{ k='encuentro'; n='Atencion'; rol='entity'; col=3; f=3
         nota='Tabla encounters. UNIQUE(appointment_id): una ficha tiene a lo sumo un encuentro. CHECK ck_encounter_signature: firmado si y sólo si tiene signed_at y signed_by. El trigger trg_encounters_inmutable rechaza modificar uno firmado y borrar cualquiera.'
         atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'status : varchar(10)', 'reason : text', 'evolution : text', 'diagnosis : text', 'indications : text', 'treatment : text', 'signed_at : timestamptz', 'signed_by_id : uuid')
         ops=@('filter(appointment).first()', 'create(appointment, patient, practitioner, branch)', 'save(update_fields)') },

      @{ k='enmienda'; n='Enmienda'; rol='entity'; col=3; f=4
         nota='Tabla encounter_amendments. No reemplaza el texto original: se muestra al lado. El trigger trg_encounter_amendments_inmutable impide modificarla o borrarla.'
         atr=@('id : uuid', 'organization_id : uuid', 'encounter_id : uuid', 'section : varchar(20)', 'text : text', 'author_id : uuid', 'created_at : timestamptz')
         ops=@('create(encounter, section, text, author)') }
    )

    estado = @{
      estados = @(
        @{ k='ini';    tipo='inicial'; col=0; f=0 },
        @{ k='aut';    n='Autenticar Médico';           col=0; f=2 },
        @{ k='fin403'; tipo='final';   col=0; f=4.5 },
        @{ k='menu';   n='Seleccionar operación';       col=1; f=2 },
        @{ k='ver';    n='Desplegar agenda del día';    col=2; f=0 },
        @{ k='capb';   n='Capturar secciones';          col=2; f=1.6 },
        @{ k='capf';   n='Confirmar firma';             col=2; f=3.2 },
        @{ k='cape';   n='Capturar enmienda';           col=2; f=4.8 },
        @{ k='valf';   n='Validar ficha';               col=3; f=0 },
        @{ k='valg';   n='Validar firma';               col=3; f=3.2 },
        @{ k='vale';   n='Validar enmienda';            col=3; f=4.8 },
        @{ k='error';  n='Informar error';              col=4; f=5.5 },
        @{ k='ok';     n='Transacción completada';      col=4; f=1.5 },
        @{ k='fin';    tipo='final';   col=4; f=3 }
      )
      transiciones = @(
        @{ de='ini';   a='aut' },
        @{ de='aut';   a='menu';   r='[token y encounters.encounter.read] {CanReadEncounters, permissions.py:25}' },
        @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
        @{ de='menu';  a='ver';    r='[consultar agenda] {GET /encounters/agenda/}' },
        @{ de='menu';  a='capb';   r='[editar borrador] {PATCH /encounters/<id>/}' },
        @{ de='menu';  a='capf';   r='[firmar] {POST /encounters/<id>/sign/}' },
        @{ de='menu';  a='cape';   r='[enmendar] {POST /encounters/<id>/amendments/}' },
        @{ de='ver';   a='valf';   r='atender() {POST /encounters/}' },
        @{ de='valf';  a='ok';     r='[suya, atendible y su día ya llegó] / open_encounter() {services.py:79}' },
        @{ de='valf';  a='error';  r='[ajena, no atendible u otro día] {400 services.py:87, 409 :96, :101}' },
        @{ de='capb';  a='ok';     r='[borrador] / update_draft() {services.py:114}' },
        @{ de='capb';  a='error';  r='[ya firmado] {409 services.py:116}' },
        @{ de='capf';  a='valg';   r='firmar()' },
        @{ de='valg';  a='ok';     r='[motivo y diagnóstico] / sign(), ficha attended {services.py:139, :148}' },
        @{ de='valg';  a='error';  r='[falta motivo o diagnóstico] {400 services.py:137}' },
        @{ de='cape';  a='vale';   r='agregarEnmienda()' },
        @{ de='vale';  a='ok';     r='[firmado] / amend() {services.py:158}' },
        @{ de='vale';  a='error';  r='[todavía borrador] {409 services.py:155}' },
        @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
        @{ de='ok';    a='fin' }
      )
    }

    tiempo = @{
      escenario = 'abrir la atención el día del turno y firmarla'
      nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. La ventana se abre a las 00:00 del día del turno en la hora de la sucursal: open_encounter rechaza con 409 si appointment_local_date > local_today (services.py:100), con la zona de branch.timezone o America/La_Paz por defecto (services.py:69 y :74). Después de ese día sigue abierta: sólo se rechaza el futuro. La agenda pide el día completo, de 00:00 a 00:00 del siguiente (views.py:96-97). Firmar pone signed_at = now() (services.py:140) y pasa la ficha a attended bajo select_for_update (services.py:146-149). No hay plazo para firmar el borrador, y una ficha pending_payment con expires_at vencido todavía se puede atender (ATTENDABLE_STATUSES, services.py:36, no mira expires_at).'
      lineas = @(
        @{ n='Transacción'
           estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=28; e='Autenticando'; ev='POST /encounters/' },
                     @{ t=36; e='Validando';    ev='open_encounter()' },
                     @{ t=44; e='Escribiendo';  ev='create()' },
                     @{ t=52; e='Confirmada';   ev='COMMIT' },
                     @{ t=58; e='Inactiva';     ev='201 (Encuentro)' } ) },
        @{ n='Ventana para abrir'
           estados=@('Cerrada', 'Abierta')
           marcas=@( @{ t=0;  e='Cerrada' },
                     @{ t=18; e='Abierta'; ev='00:00 local'; r='día del turno' } ) },
        @{ n='Atención'
           estados=@('Sin encuentro', 'draft', 'signed')
           marcas=@( @{ t=0;  e='Sin encuentro' },
                     @{ t=52; e='draft';  ev='INSERT' },
                     @{ t=80; e='signed'; ev='sign()' } ) },
        @{ n='Ficha'
           estados=@('confirmed', 'attended')
           marcas=@( @{ t=0;  e='confirmed' },
                     @{ t=80; e='attended'; ev='UPDATE' } ) }
      )
    }

    grupos = [ordered]@{
      1 = 'abrir la atención desde la agenda'
      2 = 'registrar, firmar y enmendar'
      3 = 'excepciones'
    }

    mensajes = @(
      @{ g=1; d='medico';    a='agenda';    m='verAgenda(fecha)' },
      @{ g=1; d='agenda';    a='gestor';    m='listarFichasDelDia(fecha)' },
      @{ g=1; d='gestor';    a='prof';      m='obtenerProfesional(usuario)' },
      @{ g=1; d='gestor';    a='ficha';     m='listarFichas(profesional, dia)' },
      @{ g=1; d='medico';    a='agenda';    m='atender(ficha)' },
      @{ g=1; d='agenda';    a='gestor';    m='abrirAtencion(ficha)' },
      @{ g=1; d='gestor';    a='gestor';    m='validarFicha(ficha)' },
      @{ g=1; d='gestor';    a='encuentro'; m='crearBorrador(ficha)' },
      @{ g=1; d='gestor';    a='bitgestor'; m='registrar(ENCOUNTER_OPEN, RECORD_READ)' },
      @{ g=1; d='bitgestor'; a='bitacora';  m='insertar(asiento)' },

      @{ g=2; d='medico';    a='form';      m='guardarBorrador(secciones)' },
      @{ g=2; d='form';      a='gestor';    m='actualizarBorrador(secciones)' },
      @{ g=2; d='gestor';    a='encuentro'; m='guardar(secciones)' },
      @{ g=2; d='medico';    a='form';      m='firmar()' },
      @{ g=2; d='form';      a='gestor';    m='firmar(encuentro)' },
      @{ g=2; d='gestor';    a='ficha';     m='marcarAtendida()' },
      @{ g=2; d='gestor';    a='bitgestor'; m='registrar(ENCOUNTER_SIGN, ENCOUNTER_AMEND)' },
      @{ g=2; d='medico';    a='fenm';      m='agregarEnmienda(seccion, texto)' },
      @{ g=2; d='fenm';      a='gestor';    m='enmendar(seccion, texto)' },
      @{ g=2; d='gestor';    a='enmienda';  m='insertar(enmienda)' },

      @{ g=3; d='gestor';    a='agenda';    m='fichaNoAtendible()' },
      @{ g=3; d='gestor';    a='form';      m='faltanSecciones(motivo, diagnostico)' }
    )

    secuencia = @(
      @{ t='nota'; txt='FLUJO 1 Abrir la atención desde la agenda del día' },
      @{ t='msg'; o='medico';    d='agenda';    n='1.1: verAgenda(fecha)' },
      @{ t='msg'; o='agenda';    d='gestor';    n='1.2: GET /api/encounters/agenda/?date=AAAA-MM-DD()' },
      @{ t='msg'; o='gestor';    d='prof';      n='1.3: SELECT * FROM practitioners WHERE user_id = :user_id AND is_active()' },
      @{ t='msg'; o='gestor';    d='ficha';     n='1.4: SELECT * FROM appointments WHERE practitioner_id = :id AND starts_at del día AND status IN (pending_payment, confirmed, attended)()' },
      @{ t='msg'; o='gestor';    d='agenda';    n='1.4.1: 200(date, practitioner, appointments)'; ret=$true },
      @{ t='msg'; o='medico';    d='agenda';    n='1.5: atender(ficha)' },
      @{ t='msg'; o='agenda';    d='gestor';    n='1.6: POST /api/encounters/(appointment)' },
      @{ t='msg'; o='gestor';    d='gestor';    n='1.7: open_encounter(user, appointment)  {sólo el profesional de la ficha}' },
      @{ t='msg'; o='gestor';    d='encuentro'; n='1.8: SELECT * FROM encounters WHERE appointment_id = :ficha()' },
      @{ t='alt' },
      @{ t='op'; g='la ficha ya tiene encuentro' },
      @{ t='msg'; o='gestor';    d='agenda';    n='1.9a: 200(Encuentro)  {idempotente}'; ret=$true },
      @{ t='op'; g='ficha atendible y su día ya llegó' },
      @{ t='msg'; o='gestor';    d='encuentro'; n='1.9b: INSERT INTO encounters (appointment_id, patient_id, practitioner_id, branch_id, status = draft)()' },
      @{ t='msg'; o='gestor';    d='bitgestor'; n='1.10b: registrar(ENCOUNTER_OPEN)' },
      @{ t='msg'; o='bitgestor'; d='bitacora';  n='1.11b: INSERT INTO audit_log (action, entity, detail)()' },
      @{ t='msg'; o='gestor';    d='agenda';    n='1.11b.1: 201(Encuentro)'; ret=$true },
      @{ t='op'; g='ficha ajena, no atendible o de otro día' },
      @{ t='msg'; o='gestor';    d='agenda';    n='1.9c: fichaNoAtendible() -> 400 | 409'; ret=$true },
      @{ t='fin' },

      @{ t='nota'; txt='FLUJO 2 Registrar y firmar la atención' },
      @{ t='msg'; o='medico';    d='form';      n='2.1: abrirAtencion(id)' },
      @{ t='msg'; o='form';      d='gestor';    n='2.2: GET /api/encounters/<id>/()' },
      @{ t='msg'; o='gestor';    d='encuentro'; n='2.3: SELECT * FROM encounters WHERE organization_id = :org AND id = :id()' },
      @{ t='msg'; o='encuentro'; d='gestor';    n='2.3.1: Atencion(practitioner_id, status)  {ajena -> 404}'; ret=$true },
      @{ t='msg'; o='gestor';    d='bitgestor'; n='2.4: registrar(RECORD_READ)  {quién abrió, nunca el contenido}' },
      @{ t='msg'; o='gestor';    d='form';      n='2.4.1: 200(Encuentro)'; ret=$true },
      @{ t='msg'; o='medico';    d='form';      n='2.5: guardarBorrador(secciones)' },
      @{ t='msg'; o='form';      d='gestor';    n='2.6: PATCH /api/encounters/<id>/(secciones)' },
      @{ t='loop'; g='por cada sección enviada de Encounter.SECTIONS' },
      @{ t='msg'; o='gestor';    d='gestor';    n='2.6.1: setattr(encounter, campo, valor)  {services.py:120}' },
      @{ t='fin' },
      @{ t='msg'; o='gestor';    d='encuentro'; n='2.7: UPDATE encounters SET reason, evolution, diagnosis, indications, treatment WHERE id = :id()' },
      @{ t='msg'; o='medico';    d='form';      n='2.8: firmar()' },
      @{ t='msg'; o='form';      d='gestor';    n='2.9: POST /api/encounters/<id>/sign/()' },
      @{ t='msg'; o='gestor';    d='gestor';    n='2.10: sign(encounter, user)  {REQUIRED_TO_SIGN = reason, diagnosis}' },
      @{ t='loop'; g='por cada campo de REQUIRED_TO_SIGN' },
      @{ t='msg'; o='gestor';    d='gestor';    n='2.10.1: verificar(campo no vacío)  {services.py:133}' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='motivo y diagnóstico completos' },
      @{ t='msg'; o='gestor';    d='encuentro'; n='2.11a: UPDATE encounters SET status = signed, signed_at = now(), signed_by_id = :user WHERE id = :id()' },
      @{ t='msg'; o='gestor';    d='ficha';     n='2.12a: SELECT * FROM appointments WHERE id = :ficha FOR UPDATE()' },
      @{ t='msg'; o='gestor';    d='ficha';     n='2.13a: UPDATE appointments SET status = attended WHERE id = :ficha AND status IN (pending_payment, confirmed)()' },
      @{ t='msg'; o='gestor';    d='bitgestor'; n='2.14a: registrar(ENCOUNTER_SIGN)' },
      @{ t='msg'; o='gestor';    d='form';      n='2.14a.1: 200(Encuentro firmado)'; ret=$true },
      @{ t='op'; g='falta motivo o diagnóstico' },
      @{ t='msg'; o='gestor';    d='form';      n='2.11b: faltanSecciones(reason, diagnosis) -> 400'; ret=$true },
      @{ t='fin' },

      @{ t='nota'; txt='FLUJO 3 Enmendar la atención firmada' },
      @{ t='msg'; o='medico';    d='fenm';      n='3.1: agregarEnmienda(seccion, texto)' },
      @{ t='msg'; o='fenm';      d='gestor';    n='3.2: POST /api/encounters/<id>/amendments/(section, text)' },
      @{ t='msg'; o='gestor';    d='gestor';    n='3.3: amend(encounter, user, section, text)' },
      @{ t='alt' },
      @{ t='op'; g='el encuentro está firmado' },
      @{ t='msg'; o='gestor';    d='enmienda';  n='3.4a: INSERT INTO encounter_amendments (encounter_id, section, text, author_id)()' },
      @{ t='msg'; o='gestor';    d='bitgestor'; n='3.5a: registrar(ENCOUNTER_AMEND, section)' },
      @{ t='msg'; o='gestor';    d='fenm';      n='3.5a.1: 201(Enmienda)'; ret=$true },
      @{ t='op'; g='todavía es borrador' },
      @{ t='msg'; o='gestor';    d='fenm';      n='3.4b: corregirDirectamente() -> 409'; ret=$true },
      @{ t='fin' }
    )
}

$NAVEGACION_SPRINT2['CU25'] = @{
    actor  = 'Médico'
    nota   = 'CU25 · US-24. Sólo web: no hay pantallas del médico en Flutter. La entrada «Atención» de BarraPlataforma.tsx pide encounters.encounter.read; dentro, «Atender» necesita encounters.encounter.create y el formulario de enmienda encounters.encounter.amend (los consulta la pantalla con puede). Atencion.tsx (/atencion/:id) no está en el menú: se llega desde la agenda. El diálogo «Firmar la atención» es un botón del mismo formulario, sin campos. El enlace «Historial» es de CU26 y no se dibuja acá. Cliente HTTP: frontend/src/api/atencion.ts.'
    menu   = @{ n='Panel.tsx'; ruta='/panel' }
    publicas = @()
    controladores = @{
      encounters = @{ n='encounters/views.py'; ops=@('AgendaView.get(request)', 'EncounterOpenView.post(request)', 'EncounterDetailView.get(request, pk)', 'EncounterDetailView.patch(request, pk)', 'EncounterSignView.post(request, pk)', 'EncounterAmendView.post(request, pk)') }
    }
    areas = @(
      @{ guarda='[sesión + encounters.encounter.read]'
         vista=@{ n='AgendaAtencion.tsx'; ruta='/atencion'; atr=@('date', 'starts_at', 'patient', 'status_display', 'encounter') }; vistaCtrl='encounters'
         forms=@(
           @{ n='Atencion.tsx'; ruta='/atencion/:id'; atr=@('reason', 'evolution', 'diagnosis', 'indications', 'treatment'); ctrl='encounters' },
           @{ n='AgregarEnmienda'; atr=@('section', 'text'); ctrl='encounters' }
         ) }
    )
}

$CASOS_SPRINT2['CU26'] = @{
    cu     = 'CU26'
    nombre = 'Consulta de Historia Clínica'
    us     = 'US-25'
    nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Actor: el Médico. El permiso encounters.history.read también lo tiene el Paciente (encounters/migrations/0004_permiso_historial.py:13), con alcance propio, pero no tiene entrada en el menú ni pantalla móvil: el historial en el móvil es US-27, del Sprint 3 (mobile/lib/features/history/ son los antecedentes de US-08). El permiso solo no abre nada: hace falta un alcance (services.history_scope), y sin alcance la respuesta es 404, no 403, para no confirmar que la atención existe. Sólo se leen encuentros firmados. Cada lectura deja un asiento record.read en audit_log, sin contenido clínico. El filtro por sucursal es del cliente: no hay paginación ni otra petición. El estado es el flujo de la transacción de consulta (autenticar, autorizar, resolver alcance, listar, registrar), no el ciclo de vida del encuentro, que es de CU25.'
    participantes = @(
      @{ k='medico';   n='Médico'; rol='actor'; col=0; f=2 },

      @{ k='agenda';   n='PantallaAgendaAtencion'; rol='boundary'; col=1; f=0.8
         nota='La puerta del caso: el enlace «Historial» de frontend/src/paginas/AgendaAtencion.tsx:94 y «Ver historial clínico» de frontend/src/paginas/Atencion.tsx:120, sólo si puede(encounters.history.read). La agenda en sí la carga CU25 (AgendaView en encounters/views.py). Sin pantalla móvil.'
         atr=@('GET /api/encounters/agenda/?date= : 200 | 400 | 401 | 403')
         ops=@('verAgenda(fecha, contexto, senal)', 'puede(codigo)') },

      @{ k='pantalla'; n='PantallaHistorial'; rol='boundary'; col=1; f=3
         nota='Web: frontend/src/paginas/Historial.tsx y verHistorial en frontend/src/api/atencion.ts. Móvil: no hay (US-27, Sprint 3). Backend: PatientHistoryView en encounters/history_views.py.'
         atr=@('GET /api/encounters/history/<patient_id>/ : 200 | 401 | 403 | 404')
         ops=@('verHistorial(pacienteId, contexto, senal)', 'cargar(signal)', 'setSucursal(nombre)', 'get(request, patient_id)') },

      @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=0
         nota='audit/services.py. Encola el asiento y lo escribe el middleware al terminar la petición. Del historial guarda el alcance y cuántos encuentros, nunca su texto.'
         atr=@()
         ops=@('record(request, action, entity, entity_id, detail)', 'flush(request)') },

      @{ k='gestor';   n='GestorHistorial'; rol='control'; col=2; f=2
         nota='encounters/services.py (history_scope, practitioner_of), patients/dependents.py (titular_de), encounters/serializers.py y el conteo por sucursal de encounters/history_views.py.'
         atr=@()
         ops=@('history_scope(user, patient)', 'practitioner_of(user)', 'titular_de(user)', 'EncounterSerializer(encuentros, many)', 'PatientSummarySerializer(paciente)') },

      @{ k='auth';     n='GestorAutenticacion'; rol='control'; col=2; f=4
         nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token), encounters/permissions.py (RequiresPermission), CanReadHistory en encounters/history_views.py y User.has_permission en accounts/models.py.'
         atr=@()
         ops=@('authenticate(request)', 'get_user(validated_token)', 'has_permission(request, view)', 'permission_codes()') },

      @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
         nota='Tabla audit_log. El asiento es record.read («Historia clínica consultada», audit/actions.py:94).'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar(60)', 'entity : varchar(60)', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
         ops=@('insert(asiento)') },

      @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=1
         nota='Tabla patients. user_id dice si es el propio paciente; guardian_id, si es un dependiente del titular (US-07).'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'document_number : varchar(20)', 'first_name : varchar(80)', 'last_name : varchar(80)', 'birth_date : date', 'sex : varchar(1)')
         ops=@('filter(organization, pk)') },

      @{ k='profesional'; n='Profesional'; rol='entity'; col=3; f=2
         nota='Tabla practitioners. El vínculo user_id se consulta en cada petición: dar de baja al profesional le corta el acceso.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'license_number : varchar(40)', 'is_active : boolean')
         ops=@('filter(user, is_active)') },

      @{ k='ficha';    n='Ficha'; rol='entity'; col=3; f=3
         nota='Tabla appointments. Una ficha pending_payment, confirmed o attended con el paciente es el vínculo de atención que da el alcance profesional.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)')
         ops=@('exists(patient, practitioner, status__in)') },

      @{ k='atencion'; n='Atencion'; rol='entity'; col=3; f=4
         nota='Tabla encounters, con sus enmiendas en encounter_amendments (prefetch) y la sucursal de branches (JOIN). Firmado no se modifica: lo impiden los triggers de la migración 0002.'
         atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'status : varchar(10)', 'reason : text', 'evolution : text', 'diagnosis : text', 'indications : text', 'treatment : text', 'signed_at : timestamptz', 'signed_by_id : uuid')
         ops=@('filter(patient, status=signed)', 'prefetch_related(amendments__author)') }
    )

    estado = @{
      estados = @(
        @{ k='ini';    tipo='inicial'; col=0; f=0 },
        @{ k='aut';    n='Autenticar Médico';            col=0; f=2 },
        @{ k='fin401'; tipo='final';   col=0; f=4.5 },
        @{ k='sel';    n='Seleccionar paciente';         col=1; f=2 },
        @{ k='perm';   n='Verificar permiso';            col=2; f=2 },
        @{ k='alc';    n='Resolver alcance';             col=3; f=2 },
        @{ k='list';   n='Listar encuentros firmados';   col=3; f=0 },
        @{ k='reg';    n='Registrar acceso';             col=4; f=0 },
        @{ k='ok';     n='Transacción completada';       col=4; f=2 },
        @{ k='fin';    tipo='final';   col=4; f=3.5 },
        @{ k='error';  n='Informar error';               col=4; f=5.5 }
      )
      transiciones = @(
        @{ de='ini';   a='aut' },
        @{ de='aut';   a='sel';    r='[sesión y encounters.encounter.read] {AgendaAtencion.tsx:37}' },
        @{ de='aut';   a='fin401'; r='[sin token o acceso vencido] {401}' },
        @{ de='sel';   a='perm';   r='verHistorial(paciente) {GET /history/<patient_id>/}' },
        @{ de='perm';  a='alc';    r='[encounters.history.read] {CanReadHistory, history_views.py:33}' },
        @{ de='perm';  a='error';  r='[sin el permiso] {403 permissions.py:18}' },
        @{ de='alc';   a='list';   r='[propio o profesional con ficha] {services.py:198, :205}' },
        @{ de='alc';   a='error';  r='[sin alcance] {404 history_views.py:45}' },
        @{ de='list';  a='reg';    r='/ filter(status=SIGNED) {history_views.py:51}' },
        @{ de='reg';   a='ok';     r='/ record(RECORD_READ) {history_views.py:58}' },
        @{ de='ok';    a='fin' },
        @{ de='error'; a='sel';    r='reintentar()'; ortogonal=$true }
      )
    }

    tiempo = @{
      escenario = 'consultar el historial antes y después de renovar el acceso'
      nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. El historial no tiene reloj propio (ni vencimiento ni paginación): manda la sesión. 30 min = ACCESS_TOKEN_LIFETIME (config/settings.py:294); 25 min = MINUTOS_HASTA_RENOVAR (frontend/src/sesion/ContextoSesion.tsx:38), el setTimeout de ContextoSesion.tsx:81 renueva el par 5 minutos antes de que venza. El refresco rota y el viejo va a la lista negra (ROTATE_REFRESH_TOKENS y BLACKLIST_AFTER_ROTATION, config/settings.py:296-297). La segunda consulta sale con el acceso nuevo. Si el acceso venciera sin renovarse, el GET respondería 401 y Historial.tsx mostraría el error: frontend/src/api/cliente.ts no reintenta.'
      lineas = @(
        @{ n='Transacción'
           estados=@('Inactiva', 'Autenticando', 'Validando', 'Leyendo', 'Confirmada')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=4;  e='Autenticando'; ev='GET /history/<patient_id>/' },
                     @{ t=10; e='Validando';    ev='history_scope()' },
                     @{ t=16; e='Leyendo';      ev='SELECT encounters' },
                     @{ t=22; e='Confirmada';   ev='INSERT audit_log' },
                     @{ t=26; e='Inactiva';     ev='200 (historial)' },
                     @{ t=88; e='Autenticando'; ev='GET con el acceso nuevo' },
                     @{ t=92; e='Validando' },
                     @{ t=95; e='Leyendo' },
                     @{ t=98; e='Confirmada' } ) },
        @{ n='Renovación de la sesión'
           estados=@('Esperando', 'Renovando')
           marcas=@( @{ t=0;  e='Esperando' },
                     @{ t=70; e='Renovando'; ev='renovarSesion(refresh)'; r='25 min' },
                     @{ t=76; e='Esperando'; ev='persistir(access, refresh)' } ) },
        @{ n='Acceso viejo'
           estados=@('Vigente', 'Vencido')
           marcas=@( @{ t=0;  e='Vigente' },
                     @{ t=84; e='Vencido'; ev='expira'; r='30 min' } ) },
        @{ n='Refresco viejo'
           estados=@('Vigente', 'Revocado')
           marcas=@( @{ t=0;  e='Vigente' },
                     @{ t=76; e='Revocado'; ev='BLACKLIST_AFTER_ROTATION' } ) }
      )
    }

    grupos = [ordered]@{
      1 = 'abrir el historial del paciente'
      2 = 'leer la línea de tiempo'
      3 = 'excepciones'
    }
    mensajes = @(
      @{ g=1; d='medico';   a='agenda';      m='verHistorial(paciente)' },
      @{ g=1; d='agenda';   a='pantalla';    m='abrirHistorial(pacienteId)' },
      @{ g=1; d='pantalla'; a='gestor';      m='consultarHistorial(pacienteId)' },
      @{ g=1; d='gestor';   a='auth';        m='autorizar(token, encounters.history.read)' },
      @{ g=1; d='gestor';   a='paciente';    m='buscar(organizacion, pacienteId)' },
      @{ g=1; d='gestor';   a='gestor';      m='resolverAlcance(usuario, paciente)' },
      @{ g=1; d='gestor';   a='profesional'; m='profesionalActivo(usuario)' },
      @{ g=1; d='gestor';   a='ficha';       m='existeFicha(paciente, profesional)' },
      @{ g=1; d='gestor';   a='atencion';    m='listarFirmadas(paciente)' },
      @{ g=1; d='gestor';   a='bitgestor';   m='registrar(RECORD_READ)' },
      @{ g=1; d='bitgestor'; a='bitacora';   m='insertar(asiento)' },
      @{ g=1; d='gestor';   a='pantalla';    m='historial(paciente, alcance, sucursales, encuentros)' },

      @{ g=2; d='medico';   a='pantalla';    m='filtrarSucursal(nombre)' },
      @{ g=2; d='pantalla'; a='medico';      m='mostrarLineaDeTiempo(encuentros, enmiendas)' },

      @{ g=3; d='auth';     a='pantalla';    m='sinPermiso(401 | 403)' },
      @{ g=3; d='gestor';   a='pantalla';    m='sinAlcance(404)' },
      @{ g=3; d='pantalla'; a='medico';      m='mostrarError(mensaje)' }
    )

    secuencia = @(
      @{ t='nota'; txt='FLUJO 1 Abrir el historial y autorizar' },
      @{ t='msg'; o='medico';   d='agenda';      n='1.1: verHistorial(paciente)  {enlace Historial}' },
      @{ t='msg'; o='agenda';   d='pantalla';    n='1.2: navegar(/historial/:pacienteId)' },
      @{ t='msg'; o='pantalla'; d='gestor';      n='1.3: GET /api/encounters/history/<patient_id>/()' },
      @{ t='msg'; o='gestor';   d='auth';        n='1.4: authenticate(request)  {IsAuthenticated}' },
      @{ t='msg'; o='auth';     d='auth';        n='1.4.1: has_permission(encounters.history.read)  {SELECT code FROM permissions JOIN role_permissions JOIN user_roles}' },
      @{ t='msg'; o='auth';     d='gestor';      n='1.4.2: Usuario(id, organization_id)'; ret=$true },
      @{ t='alt' },
      @{ t='op'; g='sin token o sin el permiso' },
      @{ t='msg'; o='auth';     d='pantalla';    n='1.5a: sinPermiso() -> 401 | 403'; ret=$true },
      @{ t='msg'; o='pantalla'; d='medico';      n='1.6a: mostrarError(mensaje)'; ret=$true },
      @{ t='op'; g='token válido y con encounters.history.read' },
      @{ t='msg'; o='gestor';   d='paciente';    n='1.5b: SELECT * FROM patients WHERE organization_id = :org AND id = :patient_id()' },
      @{ t='msg'; o='paciente'; d='gestor';      n='1.5b.1: Paciente(user_id, guardian_id)'; ret=$true },
      @{ t='msg'; o='gestor';   d='gestor';      n='1.6b: history_scope(user, patient)  {propio: user_id o titular del dependiente}' },
      @{ t='msg'; o='gestor';   d='profesional'; n='1.7b: SELECT * FROM practitioners WHERE user_id = :user AND is_active()' },
      @{ t='msg'; o='profesional'; d='gestor';   n='1.7b.1: Profesional(id)'; ret=$true },
      @{ t='msg'; o='gestor';   d='ficha';       n='1.8b: SELECT EXISTS (FROM appointments WHERE patient_id = :p AND practitioner_id = :pr AND status IN (pending_payment, confirmed, attended))()' },
      @{ t='msg'; o='ficha';    d='gestor';      n='1.8b.1: bool()'; ret=$true },
      @{ t='fin' },
      @{ t='nota'; txt='FLUJO 2 Listar los encuentros y dejar el asiento' },
      @{ t='alt' },
      @{ t='op'; g='alcance is None' },
      @{ t='msg'; o='gestor';   d='pantalla';    n='2.1a: sinAlcance() -> 404'; ret=$true },
      @{ t='msg'; o='pantalla'; d='medico';      n='2.2a: mostrarError(mensaje)'; ret=$true },
      @{ t='op'; g='alcance own o professional' },
      @{ t='msg'; o='gestor';   d='atencion';    n='2.1b: SELECT * FROM encounters WHERE organization_id = :org AND patient_id = :id AND status = signed ORDER BY starts_at DESC()' },
      @{ t='msg'; o='atencion'; d='gestor';      n='2.1b.1: Atencion[](secciones, firma)'; ret=$true },
      @{ t='msg'; o='gestor';   d='atencion';    n='2.2b: SELECT * FROM encounter_amendments WHERE encounter_id IN (:ids)()  {prefetch_related}' },
      @{ t='msg'; o='atencion'; d='gestor';      n='2.2b.1: Enmienda[](section, text, author)'; ret=$true },
      @{ t='msg'; o='gestor';   d='bitgestor';   n='2.3b: registrar(RECORD_READ)  {alcance y cantidad, sin contenido}' },
      @{ t='msg'; o='bitgestor'; d='bitacora';   n='2.4b: INSERT INTO audit_log (action, entity, entity_id, detail)()' },
      @{ t='loop'; g='por cada encuentro firmado' },
      @{ t='msg'; o='gestor';   d='gestor';      n='2.5b: Counter(branch.name)  {por_sucursal}' },
      @{ t='fin' },
      @{ t='msg'; o='gestor';   d='pantalla';    n='2.6b: 200(patient, scope, branches, encounters)'; ret=$true },
      @{ t='msg'; o='pantalla'; d='medico';      n='2.7b: mostrarLineaDeTiempo()'; ret=$true },
      @{ t='fin' },
      @{ t='nota'; txt='FLUJO 3 Filtrar por sucursal' },
      @{ t='msg'; o='medico';   d='pantalla';    n='3.1: filtrarSucursal(nombre)' },
      @{ t='msg'; o='pantalla'; d='pantalla';    n='3.2: setSucursal(nombre)  {en el cliente, sin otra petición}' },
      @{ t='msg'; o='pantalla'; d='medico';      n='3.3: mostrarEncuentros(secciones, enmiendas)'; ret=$true }
    )
  }

$NAVEGACION_SPRINT2['CU26'] = @{
    actor  = 'Médico'
    nota   = 'CU26 · US-25. Sólo web: el historial en el móvil es US-27 (Sprint 3). El historial no tiene entrada propia en BarraPlataforma.tsx: se llega desde «Atención» (requiere encounters.encounter.read), por el enlace «Historial» de cada ficha (AgendaAtencion.tsx:94) o «Ver historial clínico» del encuentro (Atencion.tsx:120), los dos sólo si puede(encounters.history.read). Historial.tsx es una pantalla (navigationClass) que cuelga de la agenda: lo único que manda es el pacienteId de la ruta, y la sucursal filtra en el cliente. El Paciente tiene el permiso pero ningún camino de menú hasta esta ruta. Clientes HTTP: verAgenda y verHistorial en frontend/src/api/atencion.ts.'
    menu   = @{ n='Panel.tsx'; ruta='/panel' }
    publicas = @()
    controladores = @{
      agenda    = @{ n='encounters/views.py'; ops=@('AgendaView.get(request)') }
      historial = @{ n='encounters/history_views.py'; ops=@('PatientHistoryView.get(request, patient_id)') }
    }
    areas = @(
      @{ guarda='[sesión + encounters.encounter.read]'
         vista=@{ n='AgendaAtencion.tsx'; ruta='/atencion'; atr=@('date', 'appointments', 'patient') }; vistaCtrl='agenda'
         forms=@(
           @{ n='Historial.tsx'; tipo='navigationClass'; ruta='/historial/:pacienteId'; atr=@('pacienteId', 'sucursal'); ctrl='historial' }
         ) }
    )
}

$CASOS_SPRINT2['CU32'] = @{
  cu     = 'CU32'
  nombre = 'Orientación Médica mediante Chatbot'
  us     = 'US-31'
  nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. La web y el móvil llaman al mismo POST /api/assistant/suggest/; la organización sale del token, nunca del cuerpo. El orden del endpoint es el de assistant/views.py: barrera de triage (CU35 extiende acá), recuperación filtrada por organización antes de ordenar por similitud, y redacción sólo sobre lo recuperado. Si el fragmento más parecido es de una sede, servicio o política, la misma vista contesta lo administrativo (_administrativa, CU33): esa rama no se dibuja acá. El estado es el flujo de la transacción y no un ciclo de vida: el asistente no guarda conversaciones ni tiene objeto con estados (assistant/models.py sólo guarda fragmentos).'

  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2 },

    @{ k='pantalla'; n='PantallaAsistente'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Asistente.tsx y frontend/src/api/asistente.ts. Móvil: mobile/lib/features/assistant/assistant_screen.dart y assistant_api.dart. Backend: SuggestView en backend/assistant/views.py. La conversación vive sólo en memoria: nada en localStorage.'
       atr=@('POST /api/assistant/suggest/ : 200 | 400 | 401 | 403 | 503')
       ops=@('consultarAsistente(pregunta, contexto, senal)', 'enviar(reintento)', 'motivoDelFallo(fallo)', 'post(request)') },

    @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=0
       nota='audit/services.py. Asienta quién consultó y si derivó, por cuál capa. Nunca guarda el texto de la consulta (views.py::_audit).'
       atr=@()
       ops=@('record(request, action, entity, entity_id, detail)') },

    @{ k='triage'; n='GestorTriage'; rol='control'; col=2; f=1
       nota='backend/assistant/triage.py: primera capa de US-34, por coincidencia de texto normalizado. Corre antes que todo y no depende del proveedor.'
       atr=@()
       ops=@('check(question)', 'normalize_text(text)') },

    @{ k='gestor'; n='GestorOrientacion'; rol='control'; col=2; f=2
       nota='backend/assistant/views.py (SuggestView), assistant/serializers.py (SuggestRequestSerializer, tope de 1000 caracteres) y assistant/permissions.py (CanUseAssistant, assistant.suggest.use).'
       atr=@()
       ops=@('post(request)', 'is_valid(raise_exception)', 'has_permission(request, view)', '_emergency_response(generated_by)', '_audit(request, emergency_layer, specialty_suggested, kind)') },

    @{ k='recup'; n='GestorRecuperacion'; rol='control'; col=2; f=3
       nota='backend/assistant/retrieval.py (filtro de organización antes del ORDER BY, umbral ASSISTANT_MIN_SIMILARITY) y assistant/embeddings.py (vector de 768, normalizado; proveedor gemini o local).'
       atr=@()
       ops=@('retrieve(organization, question, limit)', 'embed_query(text)', '_source_names(organization, fragments)', 'rank_specialties(fragments)', 'is_administrative(fragment)') },

    @{ k='redac'; n='GestorRedaccion'; rol='control'; col=2; f=4
       nota='backend/assistant/generation.py. Redacta sólo sobre los fragmentos; si el proveedor no responde degrada a una plantilla armada con lo recuperado (generated_by plantilla). La marca de urgencia es la segunda capa de US-34.'
       atr=@()
       ops=@('answer(question, fragments, specialty_name)', '_call_model(question, context, system_prompt)', '_grounded_fallback(specialty_name)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
       nota='Tabla audit_log. Acciones assistant.query y assistant.emergency (audit/actions.py).'
       atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='especialidad'; n='Especialidad'; rol='entity'; col=3; f=2
       nota='Tabla specialties (catalog/models.py). Sólo se lee para poner nombre a los fragmentos: source_id no es FK.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'description : text', 'is_active : boolean')
       ops=@('values_list(id, name)') },

    @{ k='fragmento'; n='FragmentoCatalogo'; rol='entity'; col=3; f=3
       nota='Tabla assistant_catalog_fragments (assistant/models.py), con RLS por organización e índice vectorial de pgvector (migración 0002). UNIQUE(organization_id, source_type, source_id, position).'
       atr=@('id : uuid', 'organization_id : uuid', 'source_type : varchar(20)', 'source_id : uuid', 'position : smallint', 'text : text', 'embedding : vector(768)', 'embedding_model : varchar(80)')
       ops=@('filter(organization).order_by(CosineDistance)') },

    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=3.5 }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';          col=0; f=2 },
      @{ k='fin401'; tipo='final';   col=0; f=4.5 },
      @{ k='cap';    n='Capturar síntomas';            col=1; f=1 },
      @{ k='val';    n='Validar consulta';             col=1; f=3 },
      @{ k='tri';    n='Revisar señales de urgencia';  col=2; f=1 },
      @{ k='rec';    n='Recuperar fragmentos';         col=2; f=3 },
      @{ k='der';    n='Derivar a emergencia';         col=3; f=0 },
      @{ k='red';    n='Redactar sugerencia';          col=3; f=3 },
      @{ k='error';  n='Informar error';               col=2; f=5.5 },
      @{ k='ok';     n='Transacción completada';       col=4; f=1.5 },
      @{ k='fin';    tipo='final';   col=4; f=3.5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='cap';    r='[token válido y assistant.suggest.use] {CanUseAssistant, views.py:51}' },
      @{ de='aut';   a='fin401'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='cap';   a='val';    r='enviar() {Asistente.tsx:71}' },
      @{ de='val';   a='tri';    r='[question válida y con organización] / check() {views.py:69}' },
      @{ de='val';   a='error';  r='[vacía, más de 1000 o sin organización] {400 serializers.py:15, 403 views.py:65}' },
      @{ de='tri';   a='der';    r='[señal de urgencia] / record(ASSISTANT_EMERGENCY) {triage.py:231}' },
      @{ de='tri';   a='rec';    r='[sin señales] / retrieve() {views.py:76}' },
      @{ de='rec';   a='error';  r='[EmbeddingError] {503 views.py:91}' },
      @{ de='rec';   a='red';    r='[descartado lo bajo el umbral] / rank_specialties() {retrieval.py:152, views.py:101}' },
      @{ de='red';   a='der';    r='[marca URGENCIA del modelo] {generation.py:115, views.py:112}' },
      @{ de='red';   a='ok';     r='[sin urgencia] / record(ASSISTANT_QUERY) {views.py:116}' },
      @{ de='der';   a='ok';     r='/ _emergency_response() {views.py:164}' },
      @{ de='error'; a='cap';    r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'consulta con el modelo de lenguaje, contra el plazo del cliente móvil'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 1000 caracteres = max_length de question (assistant/serializers.py:15): cada consulta se vectoriza y el largo consume la cuota del proveedor. 300 tokens = max_output_tokens, con temperature 0.2 (assistant/generation.py:231-232). 20 s = Config.timeout del móvil (mobile/lib/core/config.dart:40): pasado ese plazo client.dart:115 lanza ApiError.offline y la pantalla ofrece reintentar. La web no tiene plazo propio: sólo aborta al salir o al reenviar (frontend/src/api/cliente.ts:52). El backend no fija timeout a Gemini: si embed_content falla, EmbeddingError (embeddings.py:198) y 503 (views.py:91); si generate_content falla, la redacción degrada a plantilla (generation.py:109-113). La cuota del nivel gratuito (peticiones por minuto) no está en ninguna constante del código: sólo se menciona en assistant/indexing.py:127.'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Triage', 'Recuperando', 'Redactando', 'Respondida')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Autenticando'; ev='POST /assistant/suggest/' },
                   @{ t=12; e='Triage';       ev='check()' },
                   @{ t=18; e='Recuperando';  ev='retrieve()' },
                   @{ t=40; e='Redactando';   ev='answer()' },
                   @{ t=68; e='Respondida';   ev='record()' },
                   @{ t=74; e='Inactiva';     ev='200 (orientacion)' } ) },
      @{ n='Servicio de IA'
         estados=@('Inactivo', 'Vectorizando', 'Generando')
         marcas=@( @{ t=0;  e='Inactivo' },
                   @{ t=20; e='Vectorizando'; ev='embed_content()'; r='1000 caracteres' },
                   @{ t=30; e='Inactivo';     ev='vector (768)' },
                   @{ t=42; e='Generando';    ev='generate_content()'; r='300 tokens' },
                   @{ t=64; e='Inactivo';     ev='text' } ) },
      @{ n='Cliente móvil'
         estados=@('Inactivo', 'Esperando', 'Mostrando')
         marcas=@( @{ t=0;  e='Inactivo' },
                   @{ t=4;  e='Esperando'; ev='post()' },
                   @{ t=78; e='Mostrando'; ev='200 (respuesta)'; r='20 s' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'orientar por síntomas'
    2 = 'redactar sin el modelo de lenguaje'
    3 = 'excepciones'
  }

  mensajes = @(
    @{ g=1; d='paciente';  a='pantalla';     m='describirSintomas(pregunta)' },
    @{ g=1; d='pantalla';  a='gestor';       m='consultar(pregunta)' },
    @{ g=1; d='gestor';    a='triage';       m='revisarUrgencia(pregunta)' },
    @{ g=1; d='gestor';    a='recup';        m='recuperar(organizacion, pregunta)' },
    @{ g=1; d='recup';     a='ia';           m='vectorizar(pregunta)' },
    @{ g=1; d='recup';     a='fragmento';    m='buscarSimilares(vector, organizacion)' },
    @{ g=1; d='recup';     a='especialidad'; m='nombrar(source_ids)' },
    @{ g=1; d='gestor';    a='recup';        m='clasificar(fragmentos)' },
    @{ g=1; d='gestor';    a='redac';        m='redactar(pregunta, fragmentos, especialidad)' },
    @{ g=1; d='redac';     a='ia';           m='generar(prompt, fragmentos)' },
    @{ g=1; d='gestor';    a='bitgestor';    m='registrar(ASSISTANT_QUERY)' },
    @{ g=1; d='bitgestor'; a='bitacora';     m='insertar(asiento)' },
    @{ g=1; d='gestor';    a='pantalla';     m='sugerencia(especialidad, alternativas, fragmentos)' },

    @{ g=2; d='redac';     a='redac';        m='armarPlantilla(especialidad)' },

    @{ g=3; d='triage';    a='gestor';       m='urgenciaDetectada(senales)' },
    @{ g=3; d='redac';     a='gestor';       m='marcaDeUrgencia()' },
    @{ g=3; d='gestor';    a='bitgestor';    m='registrar(ASSISTANT_EMERGENCY)' },
    @{ g=3; d='gestor';    a='pantalla';     m='derivarAEmergencia(mensaje)' },
    @{ g=3; d='recup';     a='gestor';       m='proveedorCaido(EmbeddingError)' },
    @{ g=3; d='pantalla';  a='paciente';     m='noPuedoResponderAhora()' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Orientar por síntomas' },
    @{ t='msg'; o='paciente';  d='pantalla';     n='1.1: describirSintomas(pregunta)' },
    @{ t='msg'; o='pantalla';  d='gestor';       n='1.2: POST /api/assistant/suggest/(question)' },
    @{ t='msg'; o='gestor';    d='gestor';       n='1.3: is_valid(raise_exception)  {question hasta 1000 caracteres}' },
    @{ t='msg'; o='gestor';    d='triage';       n='1.4: check(question)' },
    @{ t='msg'; o='triage';    d='gestor';       n='1.4.1: TriageResult(is_emergency = False)'; ret=$true },
    @{ t='msg'; o='gestor';    d='recup';        n='1.5: retrieve(organization, question)  {la organización sale del token}' },
    @{ t='msg'; o='recup';     d='ia';           n='1.6: embed_content(question, RETRIEVAL_QUERY, 768)' },
    @{ t='msg'; o='ia';        d='recup';        n='1.6.1: embedding(768)'; ret=$true },
    @{ t='msg'; o='recup';     d='fragmento';    n='1.7: SELECT * FROM assistant_catalog_fragments WHERE organization_id = :org ORDER BY embedding <=> :vector LIMIT 5()' },
    @{ t='msg'; o='fragmento'; d='recup';        n='1.7.1: CatalogFragment(text, source_type, source_id, distance)'; ret=$true },
    @{ t='msg'; o='recup';     d='especialidad'; n='1.8: SELECT id, name FROM specialties WHERE organization_id = :org AND id IN (:source_ids)()' },
    @{ t='msg'; o='especialidad'; d='recup';     n='1.8.1: Specialty(id, name)'; ret=$true },
    @{ t='loop'; g='por cada fragmento recuperado' },
    @{ t='msg'; o='recup';     d='recup';        n='1.9: descartar(similarity < ASSISTANT_MIN_SIMILARITY)' },
    @{ t='fin' },
    @{ t='msg'; o='recup';     d='gestor';       n='1.9.1: RetrievedFragment(similarity)'; ret=$true },
    @{ t='msg'; o='gestor';    d='recup';        n='1.10: rank_specialties(fragments)' },
    @{ t='msg'; o='recup';     d='gestor';       n='1.10.1: RankedSpecialty(id, name, similarity)'; ret=$true },
    @{ t='msg'; o='gestor';    d='redac';        n='1.11: answer(question, fragments, mejor.name)' },
    @{ t='alt' },
    @{ t='op'; g='ASSISTANT_CHAT_PROVIDER = gemini y hay GEMINI_API_KEY' },
    @{ t='msg'; o='redac';     d='ia';           n='1.12a: generate_content(SYSTEM_PROMPT, fragmentos, max_output_tokens = 300)' },
    @{ t='msg'; o='ia';        d='redac';        n='1.12a.1: text(2 o 3 oraciones)'; ret=$true },
    @{ t='op'; g='proveedor local, sin clave o la llamada falló' },
    @{ t='msg'; o='redac';     d='redac';        n='1.12b: _grounded_fallback(specialty_name)  {generated_by plantilla}' },
    @{ t='fin' },
    @{ t='msg'; o='redac';     d='gestor';       n='1.13: redactado(text, generated_by, emergency = False)'; ret=$true },
    @{ t='msg'; o='gestor';    d='bitgestor';    n='1.14: record(ASSISTANT_QUERY, specialty_suggested)  {sin el texto de la consulta}' },
    @{ t='msg'; o='bitgestor'; d='bitacora';     n='1.15: INSERT INTO audit_log (action, entity, detail)()' },
    @{ t='msg'; o='gestor';    d='pantalla';     n='1.16: 200(kind orientacion, specialty, alternatives, fragments)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';     n='1.17: mostrarSugerencia(especialidad, Ver profesionales)'; ret=$true },

    @{ t='nota'; txt='FLUJO 2 Excepciones' },
    @{ t='alt' },
    @{ t='op'; g='emergency.is_emergency, regla de triage.py' },
    @{ t='msg'; o='gestor';    d='bitgestor';    n='2.1a: record(ASSISTANT_EMERGENCY, layer regla)' },
    @{ t='msg'; o='gestor';    d='pantalla';     n='2.2a: 200(emergency true, EMERGENCY_MESSAGE)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';     n='2.3a: mostrarAlertaEmergencia()'; ret=$true },
    @{ t='op'; g='redactado emergency, el modelo devolvió la marca URGENCIA' },
    @{ t='msg'; o='redac';     d='gestor';       n='2.1b: redactado(emergency = True)'; ret=$true },
    @{ t='msg'; o='gestor';    d='bitgestor';    n='2.2b: record(ASSISTANT_EMERGENCY, layer modelo)' },
    @{ t='msg'; o='gestor';    d='pantalla';     n='2.3b: 200(emergency true, generated_by gemini)'; ret=$true },
    @{ t='op'; g='EmbeddingError' },
    @{ t='msg'; o='ia';        d='recup';        n='2.1c: error(cuota, red o clave)'; ret=$true },
    @{ t='msg'; o='recup';     d='gestor';       n='2.2c: EmbeddingError(Gemini no respondió)'; ret=$true },
    @{ t='msg'; o='gestor';    d='pantalla';     n='2.3c: 503(No puedo responderte ahora)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';     n='2.4c: mostrarErrorConReintento()'; ret=$true },
    @{ t='op'; g='request.user.organization is None' },
    @{ t='msg'; o='gestor';    d='pantalla';     n='2.1d: 403(El asistente funciona dentro de una organización)'; ret=$true },
    @{ t='fin' }
  )
}

$NAVEGACION_SPRINT2['CU32'] = @{
  actor  = 'Paciente'
  nota   = 'CU32 · US-31. El asistente es una entrada alternativa a la reserva: en vez de elegir la especialidad, el paciente cuenta sus síntomas y el botón «Ver profesionales» de Asistente.tsx lleva a /buscar-profesionales?especialidad=<id>; cada tarjeta lleva a /disponibilidad?professional=<id>, donde ModalReservarFicha reserva (sólo con appointments.appointment.create, Disponibilidad.tsx:120). Ante una urgencia no hay botón: la cadena se corta. Rutas de frontend/src/App.tsx, guardas del requiere de BarraPlataforma.tsx. En el móvil, el mismo camino: _HomeScreen, /assistant (SoloPacientes), /search?specialty= y /professionals/:id/availability (mobile/lib/core/router/app_router.dart). Clientes HTTP: frontend/src/api/asistente.ts, catalogo.ts, disponibilidad.ts y fichas.ts.'
  menu   = @{ n='Panel.tsx'; ruta='/panel' }
  publicas = @()
  controladores = @{
    assistant    = @{ n='assistant/views.py'; ops=@('SuggestView.post(request)') }
    search       = @{ n='catalog/search.py'; ops=@('ProfessionalSearchView.get_queryset()') }
    availability = @{ n='scheduling/availability.py'; ops=@('AvailabilityView.get(request)') }
    booking      = @{ n='appointments/booking.py'; ops=@('AppointmentViewSet.create(request)') }
  }
  areas = @(
    @{ guarda='[sesión + assistant.suggest.use]'
       vista=@{ n='Asistente.tsx'; ruta='/asistente'; atr=@('answer', 'specialty', 'alternatives', 'fragments') }
       forms=@(
         @{ n='ConsultaAsistente'; atr=@('question'); ctrl='assistant' }
       ) },
    @{ guarda='[sesión + catalog.professional.read]'; desde='Asistente.tsx'
       vista=@{ n='BuscarProfesionales.tsx'; ruta='/buscar-profesionales'; atr=@('q', 'specialty', 'branch') }; vistaCtrl='search'
       forms=@() },
    @{ guarda='[sesión + scheduling.slot.read]'; desde='BuscarProfesionales.tsx'
       vista=@{ n='Disponibilidad.tsx'; ruta='/disponibilidad'; atr=@('practitioner', 'from', 'to', 'branch') }; vistaCtrl='availability'
       forms=@(
         @{ n='ModalReservarFicha'; atr=@('patient', 'practitioner', 'branch', 'schedule', 'starts_at'); ctrl='booking' }
       ) }
  )
}

$CASOS_SPRINT2['CU33'] = @{
  cu = 'CU33'; nombre = 'Consulta de Información mediante Chatbot'; us = 'US-32'
  nota = 'CU33 corresponde a US-32 (consultas administrativas, PR #47), no a US-34: así lo dicen scripts/ea-cu-modelo-sprint2.ps1 (nota de cu33) y docs/sprints/sprint-2/reparto.md (sección US-32). Actor principal: el Paciente; el permiso assistant.suggest.use lo tienen también Recepción y el Administrador de Organización. Es el MISMO endpoint que CU32 (POST /api/assistant/suggest/): no hay clasificador de intención, lo decide el fragmento más parecido. Si es de una sede, un servicio o la política de cancelación, la consulta es administrativa (kind = administrativa) y no se sugiere especialidad; si es de una especialidad, o no se recupera nada, sigue CU32. Las urgencias (triage.py y la marca [[URGENCIA]] del modelo) son CU35 y aquí sólo se dibuja el camino sin urgencia. El estado es el flujo de la transacción: ningún objeto del caso tiene estados en el código (assistant_catalog_fragments no lleva columna de estado). La web y el móvil llaman al mismo endpoint; la conversación vive sólo en memoria y no se guarda. Fuera de este caso: la reindexación (POST /api/assistant/reindex/, assistant.catalog.reindex), que también es de US-32 pero la ejecuta el Administrador.'

  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2 },

    @{ k='pantalla'; n='PantallaAsistente'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Asistente.tsx y frontend/src/api/asistente.ts. Móvil: mobile/lib/features/assistant/assistant_screen.dart y assistant_api.dart. Backend: SuggestView.post en assistant/views.py. La respuesta administrativa se muestra sin especialidad y sin botón de reservar, con sus fragmentos bajo «De dónde sale».'
       atr=@('POST /api/assistant/suggest/ : 200 | 400 | 401 | 403 | 503')
       ops=@('enviar(reintento)', 'consultarAsistente(pregunta, contexto, senal)', 'motivoDelFallo(fallo)', '_enviar(reintento)', 'post(request)') },

    @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=0
       nota='audit/services.py. Asiento assistant.query con kind = administrativa. Nunca guarda el texto de la consulta: quien escribe al chatbot puede estar escribiendo información de salud.'
       atr=@()
       ops=@('record(request, action, entity, entity_id, detail)') },

    @{ k='gestor'; n='GestorAsistente'; rol='control'; col=2; f=1.5
       nota='assistant/views.py (SuggestView, _administrativa, _audit), assistant/permissions.py (CanUseAssistant) y la primera capa de assistant/triage.py. La organización sale del token, nunca del cuerpo de la petición.'
       atr=@()
       ops=@('post(request)', '_administrativa(request, question, fragments)', 'has_permission(request, view)', 'check(question)', '_audit(request, kind)') },

    @{ k='recup'; n='GestorRecuperacion'; rol='control'; col=2; f=3
       nota='assistant/retrieval.py y assistant/embeddings.py. Filtra por organización ANTES de ordenar por similitud (regla 9) y descarta lo que no llega a ASSISTANT_MIN_SIMILARITY: 0,62 con Gemini y 0,12 con el proveedor local (config/settings.py:451).'
       atr=@()
       ops=@('retrieve(organization, question, limit)', 'embed_query(text)', '_gemini_embeddings(texts, task_type)', '_source_names(organization, fragments)', 'is_administrative(fragment)') },

    @{ k='redac'; n='GestorRedaccion'; rol='control'; col=2; f=4.5
       nota='assistant/generation.py. Redacta sólo sobre lo recuperado, con ADMINISTRATIVE_PROMPT. Si el proveedor falla o no hay GEMINI_API_KEY, devuelve lo recuperado tal cual (generated_by = plantilla). Nunca lanza.'
       atr=@()
       ops=@('answer_administrative(question, fragments)', '_call_model(question, context, system_prompt)', '_administrative_fallback(fragments)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
       nota='Tabla audit_log.'
       atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='fragmento'; n='FragmentoCatalogo'; rol='entity'; col=3; f=2
       nota='Tabla assistant_catalog_fragments, con RLS (tenant_isolation) e índice vectorial de pgvector. La llenan assistant/corpus.py e index_administrative (assistant/indexing.py): un fragmento por sede y por pregunta (dirección, horario, quién atiende), y precio y preparación por servicio.'
       atr=@('id : uuid', 'organization_id : uuid', 'source_type : varchar(20)', 'source_id : uuid', 'position : smallint', 'text : text', 'embedding : vector(768)', 'embedding_model : varchar(80)')
       ops=@('filter(organization)', 'annotate(distance = CosineDistance(embedding, vector))', 'order_by(distance)') },

    @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=3.2
       nota='Tabla branches (source_type = branch). Sólo se le pide el nombre de las sedes recuperadas: el horario y la dirección ya viajan dentro del fragmento.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'address : varchar(200)', 'phone : varchar(30)', 'is_active : boolean')
       ops=@('values_list(id, name)') },

    @{ k='servicio'; n='Servicio'; rol='entity'; col=3; f=4.4
       nota='Tabla services (source_type = service). La política de cancelación (source_type = policy) no tiene tabla propia: se nombra sola con POLICY_SOURCE_NAME (assistant/retrieval.py:64).'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'kind : varchar(20)', 'price : numeric', 'currency : varchar(3)', 'preparation : text')
       ops=@('values_list(id, name)') },

    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=3.5
       nota='Google Gemini, por el paquete google-genai: gemini-embedding-001 truncado a 768 dimensiones y ASSISTANT_CHAT_MODEL = gemini-3.5-flash-lite (config/settings.py:43). Con ASSISTANT_EMBEDDING_PROVIDER y ASSISTANT_CHAT_PROVIDER en local no se llama.'
       atr=@()
       ops=@('embed_content(model, contents, config)', 'generate_content(model, contents, config)') }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Usuario';      col=0; f=2 },
      @{ k='fin401'; tipo='final';   col=0; f=4.5 },
      @{ k='cap';    n='Capturar pregunta';       col=1; f=2 },
      @{ k='der';    n='Derivar a emergencia';    col=2; f=4 },
      @{ k='urg';    n='Validar pregunta';        col=2; f=2 },
      @{ k='red';    n='Redactar respuesta';      col=3; f=0 },
      @{ k='rec';    n='Recuperar fragmentos';    col=3; f=2 },
      @{ k='ok';     n='Transacción completada';  col=4; f=1 },
      @{ k='fin';    tipo='final';   col=4; f=3 },
      @{ k='error';  n='Informar error';          col=4; f=5.5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='cap';    r='[token válido y assistant.suggest.use] {IsAuthenticated, CanUseAssistant, views.py:51}' },
      @{ de='aut';   a='fin401'; r='[sin token, sin permiso o sin organización] {401 | 403, views.py:58}' },
      @{ de='cap';   a='urg';    r='enviar()' },
      @{ de='urg';   a='error';  r='[pregunta vacía o de más de 1000 caracteres] {400 serializers.py:15}' },
      @{ de='urg';   a='rec';    r='[válida y sin señales de urgencia] / retrieve() {views.py:76}' },
      @{ de='urg';   a='der';    r='[señal de urgencia de triage.py] {CU35, views.py:69}' },
      @{ de='der';   a='fin';    r='/ EMERGENCY_MESSAGE {200 emergency = true}' },
      @{ de='rec';   a='red';    r='[fragments[0] es sede, servicio o política] / answer_administrative() {views.py:95}' },
      @{ de='rec';   a='error';  r='[EmbeddingError] {503 views.py:77}' },
      @{ de='red';   a='ok';     r='[texto del modelo o plantilla] / record(ASSISTANT_QUERY) {views.py:151}' },
      @{ de='error'; a='cap';    r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'preguntar el horario de una sede con la cuota del modelo de lenguaje agotada'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 20 s = Config.timeout (mobile/lib/core/config.dart:40), que aplica client.dart:115; pasado ese tiempo el celular da ApiError.offline y ofrece reintentar. La web no tiene tope propio: pedir() sólo acepta una AbortSignal (frontend/src/api/cliente.ts:33). El backend tampoco fija timeout al proveedor (_call_model, generation.py:214, sin timeout). La cuota del nivel gratuito es por peticiones por minuto (indexing.py:127), sin número en el código: si se agota en generate_content, la excepción se traga y responde la plantilla (generation.py:203 y :209); si se agota en embed_content, EmbeddingError y 503 (embeddings.py:198, views.py:77). Latencia medida de gemini-3.5-flash-lite: 0,8 s (config/settings.py:40). Tope de la pregunta: 1000 caracteres (serializers.py:15), porque el largo consume cuota.'
    lineas = @(
      @{ n='Petición del celular'
         estados=@('Inactiva', 'Esperando', 'Respondida')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Esperando';  ev='client.post(/assistant/suggest/)' },
                   @{ t=80; e='Respondida'; ev='200 (administrativa, plantilla)'; r='< 20 s' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Validando', 'Recuperando', 'Redactando', 'Respondida')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=10; e='Validando';   ev='is_valid()' },
                   @{ t=16; e='Recuperando'; ev='retrieve()' },
                   @{ t=40; e='Redactando';  ev='answer_administrative()' },
                   @{ t=70; e='Respondida';  ev='record(ASSISTANT_QUERY)' },
                   @{ t=78; e='Inactiva';    ev='200 (kind = administrativa)' } ) },
      @{ n='Servicio de IA'
         estados=@('Libre', 'Vectorizando', 'Generando')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=18; e='Vectorizando'; ev='embed_content(RETRIEVAL_QUERY)' },
                   @{ t=30; e='Libre';        ev='vector(768)' },
                   @{ t=42; e='Generando';    ev='generate_content()' },
                   @{ t=60; e='Libre';        ev='429 (cuota agotada)' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'consultar información administrativa'
    2 = 'responder sin el modelo de lenguaje'
    3 = 'excepciones'
  }

  mensajes = @(
    @{ g=1; d='paciente';  a='pantalla';  m='preguntar(question)' },
    @{ g=1; d='pantalla';  a='gestor';    m='consultar(question)' },
    @{ g=1; d='gestor';    a='gestor';    m='verificarUrgencia(question)' },
    @{ g=1; d='gestor';    a='recup';     m='recuperar(organization, question)' },
    @{ g=1; d='recup';     a='ia';        m='vectorizar(question)' },
    @{ g=1; d='recup';     a='fragmento'; m='buscarParecidos(organization, vector)' },
    @{ g=1; d='recup';     a='sucursal';  m='nombrar(ids)' },
    @{ g=1; d='recup';     a='servicio';  m='nombrar(ids)' },
    @{ g=1; d='gestor';    a='redac';     m='redactarAdministrativa(question, fragmentos)' },
    @{ g=1; d='redac';     a='ia';        m='generar(prompt, fragmentos)' },
    @{ g=1; d='gestor';    a='bitgestor'; m='registrar(ASSISTANT_QUERY)' },
    @{ g=1; d='bitgestor'; a='bitacora';  m='insertar(asiento)' },
    @{ g=1; d='gestor';    a='pantalla';  m='200 (administrativa, fragmentos)' },
    @{ g=1; d='pantalla';  a='paciente';  m='mostrarRespuesta(answer, fragmentos)' },

    @{ g=2; d='redac';     a='redac';     m='armarRespaldo(fragmentos)' },
    @{ g=2; d='redac';     a='gestor';    m='respuesta(plantilla)' },

    @{ g=3; d='recup';     a='gestor';    m='errorDeEmbeddings()' },
    @{ g=3; d='gestor';    a='pantalla';  m='503 (noDisponible)' },
    @{ g=3; d='pantalla';  a='paciente';  m='ofrecerReintento()' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Recuperar la información' },
    @{ t='msg'; o='paciente';  d='pantalla';  n='1.1: preguntar(question)  {¿A qué hora abre la sucursal?}' },
    @{ t='msg'; o='pantalla';  d='gestor';    n='1.2: POST /api/assistant/suggest/(question)' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.3: has_permission(assistant.suggest.use)  {la organización sale del token}' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.4: check(question)  {triage.py; si es urgencia, CU35}' },
    @{ t='msg'; o='gestor';    d='recup';     n='1.5: retrieve(organization, question)' },
    @{ t='msg'; o='recup';     d='ia';        n='1.6: embed_content(question, RETRIEVAL_QUERY, 768)' },
    @{ t='alt' },
    @{ t='op'; g='el proveedor de embeddings responde' },
    @{ t='msg'; o='ia';        d='recup';     n='1.6.1a: vector(768)'; ret=$true },
    @{ t='msg'; o='recup';     d='fragmento'; n='1.7a: SELECT id, text, source_type, source_id FROM assistant_catalog_fragments WHERE organization_id = :org ORDER BY embedding <=> :vector LIMIT 5()' },
    @{ t='msg'; o='fragmento'; d='recup';     n='1.7a.1: fragmentos(distance)'; ret=$true },
    @{ t='msg'; o='recup';     d='sucursal';  n='1.8a: SELECT id, name FROM branches WHERE organization_id = :org AND id IN (:ids)()' },
    @{ t='msg'; o='recup';     d='servicio';  n='1.9a: SELECT id, name FROM services WHERE organization_id = :org AND id IN (:ids)()' },
    @{ t='loop'; g='por cada fragmento recuperado' },
    @{ t='msg'; o='recup';     d='recup';     n='1.10a: descartar(similitud menor que ASSISTANT_MIN_SIMILARITY)' },
    @{ t='fin' },
    @{ t='msg'; o='recup';     d='gestor';    n='1.10a.1: RetrievedFragment(source_type, source_name, similarity)'; ret=$true },
    @{ t='op'; g='el proveedor no responde, sin cuota o sin clave' },
    @{ t='msg'; o='ia';        d='recup';     n='1.6.1b: excepción(cuota, red o clave)'; ret=$true },
    @{ t='msg'; o='recup';     d='gestor';    n='1.7b: EmbeddingError()'; ret=$true },
    @{ t='msg'; o='gestor';    d='pantalla';  n='1.8b: 503(No puedo responderte ahora)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='1.9b: ofrecerReintento()'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 2 Redactar la respuesta administrativa' },
    @{ t='msg'; o='gestor';    d='gestor';    n='2.1: is_administrative(fragments[0])  {sede, servicio o política; si es especialidad, CU32}' },
    @{ t='msg'; o='gestor';    d='redac';     n='2.2: answer_administrative(question, fragments)' },
    @{ t='msg'; o='redac';     d='ia';        n='2.3: generate_content(ADMINISTRATIVE_PROMPT, fragmentos, temperature = 0.2)' },
    @{ t='alt' },
    @{ t='op'; g='el modelo responde' },
    @{ t='msg'; o='ia';        d='redac';     n='2.3.1a: texto(copiado de los fragmentos)'; ret=$true },
    @{ t='msg'; o='redac';     d='gestor';    n='2.4a: respuesta(text, generated_by = gemini)'; ret=$true },
    @{ t='op'; g='el modelo falla o se agotó la cuota' },
    @{ t='msg'; o='ia';        d='redac';     n='2.3.1b: excepción(cuota)'; ret=$true },
    @{ t='msg'; o='redac';     d='redac';     n='2.4b: _administrative_fallback(fragments)  {lo recuperado, tal cual}' },
    @{ t='msg'; o='redac';     d='gestor';    n='2.5b: respuesta(text, generated_by = plantilla)'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='gestor';    d='bitgestor'; n='2.6: record(ASSISTANT_QUERY, kind = administrativa)  {sin el texto}' },
    @{ t='msg'; o='bitgestor'; d='bitacora';  n='2.7: INSERT INTO audit_log (action, entity, detail)()' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='2.8: 200(kind = administrativa, answer, fragments)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='2.9: mostrarRespuesta(answer, De dónde sale)'; ret=$true }
  )
}

$CASOS_SPRINT2['CU35'] = @{
  cu = 'CU35'; nombre = 'Derivación a Atención de Emergencia'; us = 'US-34'
  nota = 'Extiende CU32 y CU33: vive en el mismo endpoint (POST /api/assistant/suggest/) y en la misma respuesta. Dos capas: las reglas de triage.py corren antes que todo y, si disparan, no se recupera nada ni se llama al Servicio de IA (views.py:69-72); la segunda es la marca [[URGENCIA]] que levanta el modelo (generation.py:34), y sólo existe con ASSISTANT_CHAT_PROVIDER=gemini y GEMINI_API_KEY (generation.py:91): con el proveedor local, que es el valor por omisión, sólo derivan las reglas. Si el modelo falla, su excepción se traga (generation.py:109) y la segunda capa no actúa. Las dos capas responden el mismo EMERGENCY_MESSAGE (triage.py:224) sin especialidad ni fragmentos, y la bitácora guarda sólo la capa, nunca el texto (views.py:182). El diagrama de estado es el flujo de la transacción: no hay un objeto con estados propios. NO implementado: llamar al número de emergencias desde la app (ni tel: ni botón), ubicar el servicio de emergencias más cercano, avisar al personal del centro, y la revisión clínica del catálogo de señales (pendiente, triage.py:22).'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2 },

    @{ k='pantalla'; n='PantallaAsistente'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/paginas/Asistente.tsx (BurbujaAsistente, AlertaEmergencia) y frontend/src/api/asistente.ts. Móvil: mobile/lib/features/assistant/assistant_screen.dart (_AlertaEmergencia) y assistant_api.dart. Backend: SuggestView.post en assistant/views.py. La pantalla no decide la urgencia: sólo obedece emergency.'
       atr=@('POST /api/assistant/suggest/ : 200 | 400 | 401 | 403 | 503')
       ops=@('enviar(reintento)', 'consultarAsistente(pregunta, contexto, senal)', 'AlertaEmergencia(mensaje)', 'post(request)') },

    @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=0
       nota='audit/services.py. Encola el asiento y lo escribe el middleware al terminar la petición. Acciones assistant.emergency y assistant.query (audit/actions.py:69-72).'
       atr=@()
       ops=@('record(request, action, entity, entity_id, detail)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=1
       nota='accounts/authentication.py (usuario e inquilino desde el token) y assistant/permissions.py (CanUseAssistant, código assistant.suggest.use).'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)', 'has_permission(code)') },

    @{ k='gestor'; n='GestorAsistente'; rol='control'; col=2; f=2
       nota='assistant/views.py y assistant/serializers.py. Orquesta las dos capas: corta con la primera antes de recuperar, y con la segunda descarta todo lo recuperado.'
       atr=@()
       ops=@('post(request)', '_administrativa(request, question, fragments)', '_emergency_response(generated_by)', '_audit(request, emergency_layer, specialty_suggested, kind)') },

    @{ k='triage'; n='GestorTriage'; rol='control'; col=2; f=3
       nota='assistant/triage.py: EMERGENCY_SIGNALS, COMBINED_SIGNALS y EMERGENCY_MESSAGE. Coincidencia por texto normalizado, sin red ni umbral. Usa normalize_text de assistant/embeddings.py.'
       atr=@()
       ops=@('check(question)', 'normalize_text(text)') },

    @{ k='rag'; n='GestorOrientacion'; rol='control'; col=2; f=4
       nota='assistant/retrieval.py, assistant/embeddings.py y assistant/generation.py (SYSTEM_PROMPT, ADMINISTRATIVE_PROMPT y EMERGENCY_MARK = [[URGENCIA]]).'
       atr=@()
       ops=@('retrieve(organization, question, limit)', 'embed_query(text)', 'is_administrative(fragment)', 'rank_specialties(fragments)', 'answer(question, fragments, specialty_name)', 'answer_administrative(question, fragments)', '_call_model(question, context, system_prompt)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
       nota='Tabla audit_log. El detalle de una derivación es sólo {layer: regla | modelo}.'
       atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='fragmento'; n='FragmentoCatalogo'; rol='entity'; col=3; f=4
       nota='Tabla assistant_catalog_fragments (modelo CatalogFragment, assistant/models.py). Se filtra por organización antes de ordenar por distancia.'
       atr=@('id : uuid', 'organization_id : uuid', 'source_type : varchar(20)', 'source_id : uuid', 'position : smallint', 'text : text', 'embedding : vector(768)', 'embedding_model : varchar(80)')
       ops=@('filter(organization).order_by(distance)[:5]') },

    @{ k='ia'; n='Servicio de IA'; rol='externo'; col=4; f=4
       nota='Google Gemini por google-genai: embed_content (assistant/embeddings.py:186) y generate_content (assistant/generation.py:221). Sólo se llama si las reglas no dispararon.' }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';         col=0; f=2 },
      @{ k='fin401'; tipo='final';   col=0; f=4.5 },
      @{ k='cap';    n='Capturar síntomas';           col=1; f=2 },
      @{ k='error';  n='Informar error';              col=1; f=5.5 },
      @{ k='val';    n='Validar consulta';            col=2; f=2 },
      @{ k='rec';    n='Recuperar fragmentos';        col=2; f=4 },
      @{ k='tri';    n='Evaluar señales de alarma';   col=3; f=2 },
      @{ k='mod';    n='Consultar al modelo';         col=3; f=4 },
      @{ k='fin';    tipo='final';   col=3; f=0 },
      @{ k='der';    n='Derivar a emergencia';        col=4; f=1.5 },
      @{ k='ok';     n='Transacción completada';      col=4; f=3 },
      @{ k='sug';    n='Sugerir especialidad';        col=4; f=4.5 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='cap';    r='[token válido y assistant.suggest.use] {views.py:51, permissions.py:18}' },
      @{ de='aut';   a='fin401'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='cap';   a='val';    r='enviar() {Asistente.tsx:71}' },
      @{ de='val';   a='tri';    r='[question válida y con organización] / check() {views.py:69}' },
      @{ de='val';   a='error';  r='[vacía, más de 1000 o sin organización] {400 serializers.py:15 | 403 views.py:63}' },
      @{ de='tri';   a='der';    r='[is_emergency] / _audit(regla) {views.py:70}' },
      @{ de='tri';   a='rec';    r='[ninguna señal] / retrieve() {views.py:76}' },
      @{ de='rec';   a='mod';    r='[hay vector] / answer() {views.py:105, :143}' },
      @{ de='rec';   a='error';  r='[EmbeddingError] {503 views.py:77}' },
      @{ de='mod';   a='der';    r='[marca de urgencia en el texto] / _audit(modelo) {views.py:112, :147}' },
      @{ de='mod';   a='sug';    r='[sin marca] / _audit(specialty_suggested) {views.py:116}' },
      @{ de='der';   a='ok';     r='/ _emergency_response() {200 emergency=true, views.py:164}' },
      @{ de='sug';   a='ok';     r='{200 emergency=false, views.py:117}' },
      @{ de='error'; a='cap';    r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'derivar por la marca del modelo'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. Se elige la segunda capa porque es la única que espera al Servicio de IA: la primera corta en check() (views.py:69) sin red, y respondería en el instante 16. 20 s = Config.timeout del móvil (mobile/lib/core/config.dart:40): si la respuesta no llega antes, client.dart:115 lanza ApiError.offline y la pantalla muestra el error con reintentar, sin derivar. La web no tiene tope propio (frontend/src/api/cliente.ts sólo admite una AbortSignal). El modelo no tiene timeout en el código (generation.py:221); su tope es de largo, max_output_tokens=300.'
    lineas = @(
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Evaluando reglas', 'Recuperando', 'Redactando', 'Derivada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=6;  e='Autenticando';     ev='POST /assistant/suggest/' },
                   @{ t=12; e='Evaluando reglas'; ev='check()' },
                   @{ t=20; e='Recuperando';      ev='retrieve()' },
                   @{ t=38; e='Redactando';       ev='answer()' },
                   @{ t=62; e='Derivada';         ev='[[URGENCIA]]' },
                   @{ t=70; e='Inactiva';         ev='200 (emergency)' } ) },
      @{ n='Servicio de IA'
         estados=@('Libre', 'Vectorizando', 'Generando')
         marcas=@( @{ t=0;  e='Libre' },
                   @{ t=22; e='Vectorizando'; ev='embed_content()' },
                   @{ t=32; e='Libre' },
                   @{ t=40; e='Generando';    ev='generate_content()' },
                   @{ t=60; e='Libre' } ) },
      @{ n='Petición del móvil'
         estados=@('Sin enviar', 'Esperando', 'Respondida')
         marcas=@( @{ t=0;  e='Sin enviar' },
                   @{ t=6;  e='Esperando';  ev='send()' },
                   @{ t=72; e='Respondida'; ev='AlertaEmergencia'; r='20 s' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'derivar por las reglas'
    2 = 'derivar por la marca del modelo'
    3 = 'excepciones'
  }
  mensajes = @(
    @{ g=1; d='paciente';  a='pantalla';  m='describirSintomas(texto)' },
    @{ g=1; d='pantalla';  a='gestor';    m='consultar(question)' },
    @{ g=1; d='gestor';    a='auth';      m='autorizar(assistant.suggest.use)' },
    @{ g=1; d='gestor';    a='triage';    m='check(question)' },
    @{ g=1; d='triage';    a='triage';    m='normalize_text(question)' },
    @{ g=1; d='gestor';    a='bitgestor'; m='registrar(ASSISTANT_EMERGENCY, layer)' },
    @{ g=1; d='bitgestor'; a='bitacora';  m='insertar(asiento)' },
    @{ g=1; d='gestor';    a='pantalla';  m='derivarAEmergencia(EMERGENCY_MESSAGE)' },
    @{ g=1; d='pantalla';  a='paciente';  m='mostrarAlertaEmergencia()' },

    @{ g=2; d='gestor';    a='rag';       m='retrieve(organization, question)' },
    @{ g=2; d='rag';       a='ia';        m='embed_content(question)' },
    @{ g=2; d='rag';       a='fragmento'; m='buscarSimilares(organization_id, vector)' },
    @{ g=2; d='gestor';    a='rag';       m='redactar(question, fragments)' },
    @{ g=2; d='rag';       a='rag';       m='_call_model(question, context)' },
    @{ g=2; d='rag';       a='ia';        m='generate_content(SYSTEM_PROMPT, consulta)' },
    @{ g=2; d='rag';       a='gestor';    m='marcaDeUrgencia(emergency)' },

    @{ g=3; d='rag';       a='gestor';    m='EmbeddingError()' },
    @{ g=3; d='gestor';    a='pantalla';  m='noPuedoResponderAhora() -> 503' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Primera capa: las reglas de triage' },
    @{ t='msg'; o='paciente';  d='pantalla';  n='1.1: describirSintomas(texto)' },
    @{ t='msg'; o='pantalla';  d='gestor';    n='1.2: POST /api/assistant/suggest/(question)' },
    @{ t='msg'; o='gestor';    d='auth';      n='1.3: autorizar(assistant.suggest.use)  {IsAuthenticated, CanUseAssistant}' },
    @{ t='msg'; o='auth';      d='gestor';    n='1.3.1: Usuario(organization)'; ret=$true },
    @{ t='msg'; o='gestor';    d='triage';    n='1.4: check(question)  {antes de recuperar nada}' },
    @{ t='msg'; o='triage';    d='triage';    n='1.5: normalize_text(question)  {sin tildes y en minúsculas}' },
    @{ t='loop'; g='por cada frase de EMERGENCY_SIGNALS y cada grupo de COMBINED_SIGNALS' },
    @{ t='msg'; o='triage';    d='triage';    n='1.5.1: buscar(frase, texto normalizado)  {triage.py:234-238}' },
    @{ t='fin' },
    @{ t='msg'; o='triage';    d='gestor';    n='1.5.2: TriageResult(is_emergency, matched, message)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='emergency.is_emergency: alguna frase de EMERGENCY_SIGNALS o COMBINED_SIGNALS' },
    @{ t='msg'; o='gestor';    d='bitgestor'; n='1.6a: registrar(ASSISTANT_EMERGENCY, layer=regla)  {sin el texto}' },
    @{ t='msg'; o='bitgestor'; d='bitacora';  n='1.7a: INSERT INTO audit_log (action, entity, detail)()' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='1.8a: 200(emergency=true, answer=EMERGENCY_MESSAGE, specialty=null, fragments=[])'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='1.9a: mostrarAlertaEmergencia()  {sin especialidad ni botón de reservar}'; ret=$true },
    @{ t='op'; g='ninguna señal' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.6b: seguirConLaRecuperacion()  {FLUJO 2}' },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 2 Segunda capa: la marca del modelo' },
    @{ t='msg'; o='gestor';    d='rag';       n='2.1: retrieve(organization, question, limit=5)' },
    @{ t='msg'; o='rag';       d='ia';        n='2.2: embed_content(question, RETRIEVAL_QUERY)' },
    @{ t='msg'; o='ia';        d='rag';       n='2.2.1: vector(768)'; ret=$true },
    @{ t='msg'; o='rag';       d='fragmento'; n='2.3: SELECT * FROM assistant_catalog_fragments WHERE organization_id = :org ORDER BY embedding <=> :vector LIMIT 5()' },
    @{ t='msg'; o='fragmento'; d='rag';       n='2.3.1: list(CatalogFragment)'; ret=$true },
    @{ t='msg'; o='gestor';    d='rag';       n='2.4: redactar(question, fragments)  {answer() o answer_administrative() según is_administrative(fragments[0])}' },
    @{ t='msg'; o='rag';       d='rag';       n='2.5: _call_model(question, context)' },
    @{ t='msg'; o='rag';       d='ia';        n='2.6: generate_content(SYSTEM_PROMPT, fragmentos, consulta)' },
    @{ t='msg'; o='ia';        d='rag';       n='2.6.1: texto()'; ret=$true },
    @{ t='msg'; o='rag';       d='gestor';    n='2.7: dict(text, generated_by, emergency)  {emergency si EMERGENCY_MARK está en el texto}'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='redactado emergency: el modelo levantó la marca de urgencia' },
    @{ t='msg'; o='gestor';    d='bitgestor'; n='2.8a: registrar(ASSISTANT_EMERGENCY, layer=modelo)  {se descarta lo recuperado}' },
    @{ t='msg'; o='bitgestor'; d='bitacora';  n='2.9a: INSERT INTO audit_log (action, entity, detail)()' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='2.10a: 200(emergency=true, answer=EMERGENCY_MESSAGE, generated_by=gemini)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='2.11a: mostrarAlertaEmergencia()'; ret=$true },
    @{ t='op'; g='sin marca' },
    @{ t='msg'; o='gestor';    d='bitgestor'; n='2.8b: registrar(ASSISTANT_QUERY, specialty_suggested, kind)' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='2.9b: 200(emergency=false, kind, specialty, fragments)  {sigue CU32 o CU33}'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='2.10b: mostrarSugerencia()'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 3 Excepciones' },
    @{ t='alt' },
    @{ t='op'; g='request.user.organization is None' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='3.1a: 403(El asistente funciona dentro de una organización)'; ret=$true },
    @{ t='op'; g='EmbeddingError en embed_query()' },
    @{ t='msg'; o='rag';       d='gestor';    n='3.1b: EmbeddingError(Gemini no respondió)'; ret=$true },
    @{ t='msg'; o='gestor';    d='pantalla';  n='3.2b: noPuedoResponderAhora() -> 503  {sin segunda capa}'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='3.3b: mostrarErrorConReintentar()'; ret=$true },
    @{ t='fin' }
  )
}
