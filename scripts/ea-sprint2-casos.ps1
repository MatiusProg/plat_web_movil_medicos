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
         atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
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

$CASOS_SPRINT2['CU10'] = @{
  cu = 'CU10'; nombre = 'Búsqueda y Consulta de Pacientes'; us = 'US-09'
  nota = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Sólo web: no hay pantalla móvil ni ruta en app_router.dart. Sólo lee: no hay transacción ni asiento en la bitácora, por eso no lleva secuencia, estado ni tiempo. El filtro por documento (document) y por sucursal (branch) existe en la API (search.py:178, :227) pero la web no los manda: Pacientes.tsx:107 sólo envía q, status y page_size = 100. La consulta no expone antecedentes ni contenido clínico. Una ficha de otra organización responde 404: get_queryset filtra por organization y RLS hace lo mismo en la base.'
  participantes = @(
    @{ k='recep'; n='Recepcionista'; rol='actor'; col=0; f=1.6 },

    @{ k='pantalla'; n='PantallaPacientes'; rol='boundary'; col=1; f=1.6
       nota='Web: frontend/src/paginas/Pacientes.tsx (lista y detalle en la misma página, ruta /pacientes) y frontend/src/api/pacientes.ts. Móvil: sin implementar. Backend: PatientSearchViewSet en patients/search.py, registrado como "search" en patients/urls.py.'
       atr=@('GET /api/patients/search/?q&document&status&branch&page&page_size : 200 | 401 | 403', 'GET /api/patients/search/{id}/ : 200 | 401 | 403 | 404')
       ops=@('buscarPacientes(filtros, contexto, senal)', 'obtenerPaciente(id, contexto, senal)', 'cargar()', 'verDetalle(id)', 'list(request)', 'retrieve(request, pk)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token) y patients/permissions.py (CanReadPatients: patients.patient.read, sembrado a org_admin, receptionist y practitioner en tenancy/migrations/0003_seed_catalog.py:102).'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)', 'has_permission(code)') },

    @{ k='gestor'; n='GestorBusquedaPacientes'; rol='control'; col=2; f=1.8
       nota='patients/search.py: PatientSearchViewSet, PatientSearchSerializer, PatientDetailSerializer y PatientSearchPagination (20 por página, 100 como máximo). El documento se compara exacto; el nombre, parcial y sin tildes, recorriendo en Python los pacientes de la organización (search.py:194).'
       atr=@()
       ops=@('organization()', 'get_queryset()', 'normalizar(texto)', 'get_serializer_class()', 'get_upcoming_appointments(patient)') },

    @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=0.4
       nota='Tabla patients: la ficha demográfica. UNIQUE(organization_id, document_type, document_number) cuando hay documento (uq_patient_document).'
       atr=@('id : uuid', 'organization_id : uuid', 'document_type : varchar(10)', 'document_number : varchar(20)', 'first_name : varchar(80)', 'last_name : varchar(80)', 'birth_date : date', 'sex : varchar(1)', 'phone : varchar(30)', 'is_active : boolean', 'created_at : timestamptz', 'updated_at : timestamptz')
       ops=@('filter(organization, document_number, is_active)', 'iterator(chunk_size=500)', 'get(pk)') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=1.8
       nota='Tabla appointments. El detalle muestra hasta 10 fichas futuras y descarta cancelled, rescheduled y expired (search.py:106).'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar(16)')
       ops=@('filter(organization, starts_at__gte)', 'exclude(status__in)') },

    @{ k='profesional'; n='Profesional'; rol='entity'; col=3; f=2.8
       nota='Tabla practitioners. Sólo aporta el nombre del profesional de cada ficha (select_related, search.py:122).'
       atr=@('id : uuid', 'organization_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)')
       ops=@('full_name()') },

    @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=3.7
       nota='Tabla branches. Sólo aporta el nombre de la sucursal de cada ficha.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)')
       ops=@('leer(name)') }
  )

  grupos = [ordered]@{
    1 = 'buscar pacientes'
    2 = 'consultar la ficha demográfica'
    3 = 'excepciones'
  }

  mensajes = @(
    @{ g=1; d='recep';    a='pantalla';    m='buscar(texto, estado)' },
    @{ g=1; d='pantalla'; a='gestor';      m='buscarPacientes(q, status)' },
    @{ g=1; d='gestor';   a='auth';        m='verificarPermiso(patients.patient.read)' },
    @{ g=1; d='gestor';   a='gestor';      m='normalizar(texto)' },
    @{ g=1; d='gestor';   a='paciente';    m='buscar(organización, nombre o documento, estado)' },

    @{ g=2; d='recep';    a='pantalla';    m='verDetalle(paciente)' },
    @{ g=2; d='pantalla'; a='gestor';      m='obtenerPaciente(id)' },
    @{ g=2; d='gestor';   a='auth';        m='verificarPermiso(patients.patient.read)' },
    @{ g=2; d='gestor';   a='paciente';    m='obtener(id)' },
    @{ g=2; d='gestor';   a='ficha';       m='proximasFichas(paciente)' },
    @{ g=2; d='gestor';   a='profesional'; m='leerNombre(practitioner)' },
    @{ g=2; d='gestor';   a='sucursal';    m='leerNombre(branch)' },

    @{ g=3; d='gestor';   a='pantalla';    m='sinPermiso()' },
    @{ g=3; d='gestor';   a='pantalla';    m='pacienteNoEncontrado()' }
  )
}

# =========================================================================
# CU11 Administración de Pacientes (US-10). Bloque para
# scripts/ea-sprint2-casos.ps1: se pega después de crear los dos
# diccionarios, como los de CU18, CU21 y CU25.
# =========================================================================

$CASOS_SPRINT2['CU11'] = @{
    cu     = 'CU11'
    nombre = 'Administración de Pacientes'
    us     = 'US-10'
    nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Sólo web: el móvil no tiene pantalla ni llamadas a /patients/admin/. Actor: el Administrador de Organización, que recibe todo el módulo patients (tenancy/migrations/0003_seed_catalog.py:104 y accounts/migrations/0003_seed_permissions_sprint_1.py:63). La Recepcionista también registra, corrige y da de baja (tenancy/migrations/0003_seed_catalog.py:105-107 y accounts/migrations/0003_seed_permissions_sprint_1.py:77), pero NO fusiona: patients.patient.merge es sólo del administrador. La lista y la carga del paciente a editar usan los endpoints de CU10 (patients/search.py); acá se dibujan sólo los if que esta pantalla activa (q y status). Nunca se borra una fila: la baja es is_active = false. El alta no deja asiento en la bitácora (perform_create, admin_ops.py:180, no llama a record). La fusión pasa al destino los antecedentes, las fichas y los dependientes del origen, y desactiva el origen. Estado: flujo de la transacción; los estados del paciente van en el diagrama de tiempo.'

    participantes = @(
      @{ k='admin';    n='Administrador de Organización'; rol='actor'; col=0; f=2.4 },

      @{ k='pantalla'; n='PantallaPacientes'; rol='boundary'; col=1; f=0.6
         nota='Web: frontend/src/paginas/Pacientes.tsx (la lista con sus filtros, el botón Desactivar y su modal, Pacientes.tsx:1015) y frontend/src/api/pacientes.ts. Sin móvil. Backend: PatientSearchViewSet en patients/search.py (la lista, de CU10) y PatientAdminViewSet.destroy en patients/admin_ops.py.'
         atr=@('GET /api/patients/search/ : 200 | 401 | 403', 'DELETE /api/patients/admin/{id}/ : 204 | 401 | 403 | 404')
         ops=@('buscarPacientes(filtros, contexto, senal)', 'desactivarPaciente(id, contexto)', 'cargar()', 'confirmarDesactivacion()', 'list(request)', 'destroy(request, pk)') },

      @{ k='form';     n='FormularioPaciente'; rol='boundary'; col=1; f=2.2
         nota='El formulario «Registrar paciente» / «Editar paciente» de frontend/src/paginas/Pacientes.tsx (:476-640), visible con puede(patients.patient.create) o puede(patients.patient.update). Cliente HTTP: crearPaciente, editarPaciente y obtenerPaciente de frontend/src/api/pacientes.ts. Backend: PatientAdminViewSet en patients/admin_ops.py y PatientSearchViewSet.retrieve en patients/search.py.'
         atr=@('GET /api/patients/search/{id}/ : 200 | 401 | 403 | 404', 'POST /api/patients/admin/ : 201 | 400 | 401 | 403', 'PATCH /api/patients/admin/{id}/ : 200 | 400 | 401 | 403 | 404')
         ops=@('obtenerPaciente(id, contexto, senal)', 'crearPaciente(datos, contexto)', 'editarPaciente(id, datos, contexto)', 'prepararEdicion(id)', 'guardar(evento)', 'create(request)', 'partial_update(request, pk)') },

      @{ k='ffusion';  n='FormularioFusion'; rol='boundary'; col=1; f=3.8
         nota='La sección «Fusionar duplicados» y su modal de confirmación en frontend/src/paginas/Pacientes.tsx (:816 y :1114), visibles sólo con puede(patients.patient.merge). Los dos selectores ofrecen sólo pacientes activos de la lista ya cargada (Pacientes.tsx:846, :878). Cliente HTTP: fusionarPacientes de frontend/src/api/pacientes.ts. Backend: PatientAdminViewSet.merge en patients/admin_ops.py.'
         atr=@('POST /api/patients/admin/merge/ : 200 | 400 | 401 | 403 | 404')
         ops=@('fusionarPacientes(datos, contexto)', 'solicitarFusion()', 'confirmarFusion()', 'merge(request)') },

      @{ k='auth';     n='GestorAutenticacion'; rol='control'; col=2; f=0
         nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token) y patients/permissions.py (RequiresPermission y CanCreatePatients, CanUpdatePatients, CanDeactivatePatients, CanMergePatients). get_permissions (admin_ops.py:141) elige la clase según la acción.'
         atr=@()
         ops=@('authenticate(request)', 'get_permissions()', 'has_permission(request, view)', 'has_permission(code)') },

      @{ k='busqueda'; n='GestorBusqueda'; rol='control'; col=2; f=1.2
         nota='patients/search.py, de CU10: arma la lista que muestra la pantalla y el detalle con que se precarga la edición. Filtra siempre por la organización del usuario (get_queryset, search.py:156).'
         atr=@()
         ops=@('get_queryset()', 'normalizar(texto)', 'retrieve(request, pk)') },

      @{ k='gestor';   n='GestorPacientes'; rol='control'; col=2; f=2.4
         nota='patients/admin_ops.py: PatientAdminSerializer (rechaza un documento repetido dentro de la organización) y PatientAdminViewSet (alta, corrección y baja lógica). get_object pasa por get_queryset: un paciente de otra organización responde 404, no 403.'
         atr=@()
         ops=@('validate_document_number(value)', 'validate(attrs)', 'get_queryset()', 'perform_create(serializer)', 'perform_update(serializer)', 'destroy(request)') },

      @{ k='fusion';   n='GestorFusion'; rol='control'; col=2; f=3.8
         nota='patients/admin_ops.py: MergePatientsSerializer y PatientAdminViewSet.merge. Todo dentro de transaction.atomic() (admin_ops.py:285), que es un savepoint de la transacción que abre TenantMiddleware (tenancy/middleware.py:39): los bloqueos FOR UPDATE duran hasta el COMMIT de la petición.'
         atr=@()
         ops=@('validate(attrs)', 'merge(request)') },

      @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=5
         nota='audit/services.py. record() sólo encola el asiento; lo escribe AuditTrailMiddleware (flush) después de que TenantMiddleware cerró la transacción, cada uno en su propia transacción (audit/services.py:134, :149).'
         atr=@()
         ops=@('record(request, action, entity, entity_id, detail)', 'flush(request)') },

      @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=1.2
         nota='Tabla patients. uq_patient_document: UNIQUE(organization_id, document_type, document_number) sólo si hay número. ck_patient_doc_or_guardian: sin documento hace falta un titular. ck_patient_guardian: nadie es su propio titular. user_id es OneToOne y admite NULL.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'relationship : varchar(20)', 'document_type : varchar(10)', 'document_number : varchar(20)', 'first_name : varchar(80)', 'last_name : varchar(80)', 'birth_date : date', 'sex : varchar(1)', 'phone : varchar(30)', 'is_active : boolean', 'created_at : timestamptz', 'updated_at : timestamptz')
         ops=@('filter(organization, document_type, document_number).exists()', 'create(organization, ...)', 'save(update_fields)', 'select_for_update().filter(organization, id).first()', 'filter(organization, guardian).update(guardian)') },

      @{ k='antecedente'; n='Antecedente'; rol='entity'; col=3; f=2.6
         nota='Tabla patient_history_entries (US-08): los antecedentes declarados. La fusión los pasa enteros al destino.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'kind : varchar(20)', 'description : varchar(200)', 'severity : varchar(20)', 'source : varchar(20)', 'declared_by_id : uuid', 'recorded_at : date', 'is_active : boolean')
         ops=@('update(patient)') },

      @{ k='ficha';    n='Ficha'; rol='entity'; col=3; f=3.6
         nota='Tabla appointments (US-17). La fusión pasa al destino todas las fichas del origen, de cualquier estado; el pago (payments) cuelga de la ficha y la sigue.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)')
         ops=@('update(patient)') },

      @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=5
         nota='Tabla audit_log. Acciones patient.update, patient.deactivate y patient.merge (audit/actions.py:45-47), con before y after en detail. El alta no deja asiento.'
         atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar(60)', 'entity : varchar(60)', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
         ops=@('insert(asiento)') }
    )

    estado = @{
      estados = @(
        @{ k='ini';    tipo='inicial'; col=0; f=0 },
        @{ k='aut';    n='Autenticar Administrador';     col=0; f=2 },
        @{ k='fin403'; tipo='final';   col=0; f=4.5 },
        @{ k='menu';   n='Seleccionar operación';        col=1; f=2 },
        @{ k='ver';    n='Desplegar pacientes';          col=2; f=0 },
        @{ k='capd';   n='Capturar datos del paciente';  col=2; f=1.6 },
        @{ k='capb';   n='Confirmar baja';               col=2; f=3.2 },
        @{ k='capf';   n='Elegir origen y destino';      col=2; f=4.8 },
        @{ k='vald';   n='Validar documento';            col=3; f=1.6 },
        @{ k='valf';   n='Validar fusión';               col=3; f=4.8 },
        @{ k='error';  n='Informar error';               col=4; f=5.5 },
        @{ k='ok';     n='Transacción completada';       col=4; f=1.5 },
        @{ k='fin';    tipo='final';   col=4; f=3 }
      )
      transiciones = @(
        @{ de='ini';   a='aut' },
        @{ de='aut';   a='menu';   r='[token y patients.patient.read] {CanReadPatients, permissions.py:53; BarraPlataforma.tsx:205}' },
        @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
        @{ de='menu';  a='ver';    r='[consultar] {GET /patients/search/}' },
        @{ de='menu';  a='capd';   r='[registrar o corregir] {POST /patients/admin/ | PATCH /patients/admin/{id}/}' },
        @{ de='menu';  a='capb';   r='[desactivar] {Pacientes.tsx:787}' },
        @{ de='menu';  a='capf';   r='[fusionar] {Pacientes.tsx:816}' },
        @{ de='capd';  a='vald';   r='guardar()' },
        @{ de='vald';  a='ok';     r='[documento libre o vacío] / save() {admin_ops.py:181, :203}' },
        @{ de='vald';  a='error';  r='[documento ya usado en la organización] {400 admin_ops.py:98}' },
        @{ de='capb';  a='ok';     r='confirmar() [de la organización] / is_active = false {admin_ops.py:238}' },
        @{ de='capb';  a='error';  r='[de otra organización o sin permiso] {404 | 403}' },
        @{ de='capf';  a='valf';   r='confirmar() [origen y destino elegidos y distintos] {Pacientes.tsx:321, :331}' },
        @{ de='valf';  a='ok';     r='[ambos de la organización y origen activo] / transaction.atomic(), origen is_active = false {admin_ops.py:285, :414}' },
        @{ de='valf';  a='error';  r='[mismo paciente, no encontrado u origen inactivo] {400 admin_ops.py:114, 404 :306, 400 :315}' },
        @{ de='ver';   a='ok' },
        @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
        @{ de='ok';    a='fin' }
      )
    }

    tiempo = @{
      escenario = 'fusionar dos registros mientras otra petición corrige el paciente origen'
      nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. Los dos SELECT ... FOR UPDATE (admin_ops.py:286-304) bloquean las filas del origen y del destino. El transaction.atomic() de admin_ops.py:285 es un savepoint de la transacción que abre TenantMiddleware, que hace el COMMIT al terminar la petición (tenancy/middleware.py:39, :69-71): ahí se liberan los bloqueos. Una corrección (PATCH) o una baja (DELETE) del mismo paciente espera ese COMMIT para escribir. El asiento patient.merge se pide dentro del atomic (record, admin_ops.py:429) pero sólo se encola: lo escribe AuditTrailMiddleware después del COMMIT (audit/services.py:134). Ninguna constante de tiempo del código interviene en este caso de uso: por eso no hay restricciones {...} en el diagrama.'
      lineas = @(
        @{ n='Transacción de la fusión'
           estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=6;  e='Autenticando'; ev='POST .../merge/' },
                     @{ t=14; e='Validando';    ev='validate()' },
                     @{ t=22; e='Escribiendo';  ev='FOR UPDATE' },
                     @{ t=60; e='Confirmada';   ev='COMMIT' },
                     @{ t=66; e='Inactiva';     ev='200 (destino)' } ) },
        @{ n='Filas de origen y destino'
           estados=@('Libres', 'Bloqueadas')
           marcas=@( @{ t=0;  e='Libres' },
                     @{ t=22; e='Bloqueadas'; ev='select_for_update()' },
                     @{ t=60; e='Libres';     ev='COMMIT' } ) },
        @{ n='Corrección concurrente'
           estados=@('Inactiva', 'Esperando', 'Escribiendo')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=32; e='Esperando';   ev='UPDATE (PATCH)' },
                     @{ t=60; e='Escribiendo'; ev='bloqueo liberado' } ) },
        @{ n='Paciente origen'
           estados=@('activo', 'inactivo')
           marcas=@( @{ t=0;  e='activo' },
                     @{ t=60; e='inactivo'; ev='is_active = false' } ) },
        @{ n='Asiento patient.merge'
           estados=@('Sin asiento', 'Encolado', 'Escrito')
           marcas=@( @{ t=0;  e='Sin asiento' },
                     @{ t=54; e='Encolado'; ev='record()' },
                     @{ t=72; e='Escrito';  ev='flush()' } ) }
      )
    }

    grupos = [ordered]@{
      1 = 'registrar o corregir un paciente'
      2 = 'dar de baja un paciente'
      3 = 'fusionar duplicados'
      4 = 'excepciones'
    }

    # Ningún par lleva más de dos mensajes en el mismo sentido: por eso la
    # fusión tiene su frontera (FormularioFusion) y su controlador
    # (GestorFusion), y el alta y la corrección comparten mensajes.
    mensajes = @(
      @{ g=1; d='admin';     a='form';        m='editar(paciente)' },
      @{ g=1; d='form';      a='busqueda';    m='obtenerPaciente(id)' },
      @{ g=1; d='busqueda';  a='paciente';    m='leerPaciente(id)' },
      @{ g=1; d='admin';     a='form';        m='guardar(datos)' },
      @{ g=1; d='form';      a='gestor';      m='guardarPaciente(datos)' },
      @{ g=1; d='gestor';    a='auth';        m='verificarPermiso(create | update)' },
      @{ g=1; d='gestor';    a='gestor';      m='validarDocumento(tipo, numero)' },
      @{ g=1; d='gestor';    a='paciente';    m='guardar(paciente)' },
      @{ g=1; d='gestor';    a='bitgestor';   m='registrar(PATIENT_UPDATE)' },
      @{ g=1; d='bitgestor'; a='bitacora';    m='insertar(asiento)' },

      @{ g=2; d='admin';     a='pantalla';    m='buscar(q, estado)' },
      @{ g=2; d='pantalla';  a='busqueda';    m='buscarPacientes(q, status)' },
      @{ g=2; d='busqueda';  a='paciente';    m='buscar(q, status)' },
      @{ g=2; d='admin';     a='pantalla';    m='desactivar(paciente)' },
      @{ g=2; d='pantalla';  a='gestor';      m='desactivarPaciente(id)' },
      @{ g=2; d='gestor';    a='auth';        m='verificarPermiso(deactivate)' },
      @{ g=2; d='gestor';    a='paciente';    m='marcarInactivo(paciente)' },
      @{ g=2; d='gestor';    a='bitgestor';   m='registrar(PATIENT_DEACTIVATE)' },

      @{ g=3; d='admin';     a='ffusion';     m='elegir(origen, destino)' },
      @{ g=3; d='ffusion';   a='ffusion';     m='solicitarFusion()' },
      @{ g=3; d='admin';     a='ffusion';     m='confirmar()' },
      @{ g=3; d='ffusion';   a='fusion';      m='fusionarPacientes(origen, destino)' },
      @{ g=3; d='fusion';    a='auth';        m='verificarPermiso(merge)' },
      @{ g=3; d='fusion';    a='fusion';      m='validarPar(origen, destino)' },
      @{ g=3; d='fusion';    a='paciente';    m='bloquear(origen, destino)' },
      @{ g=3; d='fusion';    a='paciente';    m='absorber(origen, destino)' },
      @{ g=3; d='fusion';    a='antecedente'; m='reasignar(origen, destino)' },
      @{ g=3; d='fusion';    a='ficha';       m='reasignar(origen, destino)' },
      @{ g=3; d='fusion';    a='bitgestor';   m='registrar(PATIENT_MERGE)' },

      @{ g=4; d='gestor';    a='pantalla';    m='rechazar(code)' },
      @{ g=4; d='gestor';    a='form';        m='documentoDuplicado(document_number)' },
      @{ g=4; d='fusion';    a='ffusion';     m='fusionNoValida(code)' }
    )

    secuencia = @(
      @{ t='nota'; txt='FLUJO 1 Registrar o corregir un paciente' },
      @{ t='msg'; o='admin';     d='form';        n='1.1: editar(paciente)  {sólo la corrección: botón Editar, Pacientes.tsx:777; el alta parte del formulario vacío}' },
      @{ t='msg'; o='form';      d='busqueda';    n='1.2: GET /api/patients/search/{id}/()  {prepararEdicion, endpoint de CU10}' },
      @{ t='msg'; o='busqueda';  d='paciente';    n='1.3: SELECT * FROM patients WHERE organization_id = :org AND id = :id()' },
      @{ t='msg'; o='paciente';  d='busqueda';    n='1.3.1: Paciente(document_type, document_number, nombres, birth_date, sex, phone)'; ret=$true },
      @{ t='msg'; o='busqueda';  d='form';        n='1.3.2: 200(PacienteDetalle)  {precarga el formulario}'; ret=$true },
      @{ t='msg'; o='admin';     d='form';        n='1.4: guardar(document_type, document_number, first_name, last_name, birth_date, sex, phone)' },
      @{ t='alt' },
      @{ t='op'; g='editandoId  {Pacientes.tsx:249}' },
      @{ t='msg'; o='form';      d='gestor';      n='1.5a: PATCH /api/patients/admin/{id}/(cambios)' },
      @{ t='msg'; o='gestor';    d='auth';        n='1.6a: verificarPermiso(patients.patient.update)' },
      @{ t='msg'; o='auth';      d='gestor';      n='1.6a.1: has_permission(code) -> True'; ret=$true },
      @{ t='msg'; o='gestor';    d='paciente';    n='1.6a.2: SELECT * FROM patients WHERE organization_id = :org AND id = :id()  {get_object}' },
      @{ t='op'; g='alta: sin editandoId' },
      @{ t='msg'; o='form';      d='gestor';      n='1.5b: POST /api/patients/admin/(datos)' },
      @{ t='msg'; o='gestor';    d='auth';        n='1.6b: verificarPermiso(patients.patient.create)' },
      @{ t='msg'; o='auth';      d='gestor';      n='1.6b.1: has_permission(code) -> True'; ret=$true },
      @{ t='fin' },
      @{ t='msg'; o='gestor';    d='gestor';      n='1.7: validate_document_number(value)  {admin_ops.py:56}' },
      @{ t='alt' },
      @{ t='op'; g='value is None' },
      @{ t='msg'; o='gestor';    d='gestor';      n='1.7.1a: return None' },
      @{ t='op'; g='con valor' },
      @{ t='msg'; o='gestor';    d='gestor';      n='1.7.1b: value.strip() or None  {vacío -> None}' },
      @{ t='fin' },
      @{ t='msg'; o='gestor';    d='gestor';      n='1.7.2: validate(attrs)  {tipo y número de attrs, o los de la instancia}' },
      @{ t='alt' },
      @{ t='op'; g='document_number  {admin_ops.py:86}' },
      @{ t='alt' },
      @{ t='op'; g='self.instance is not None  {corrección}' },
      @{ t='msg'; o='gestor';    d='paciente';    n='1.7.3a: SELECT 1 FROM patients WHERE organization_id = :org AND document_type = :tipo AND document_number = :numero AND id <> :id LIMIT 1()' },
      @{ t='op'; g='alta' },
      @{ t='msg'; o='gestor';    d='paciente';    n='1.7.3b: SELECT 1 FROM patients WHERE organization_id = :org AND document_type = :tipo AND document_number = :numero LIMIT 1()' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='duplicado.exists()  {admin_ops.py:98}' },
      @{ t='msg'; o='gestor';    d='form';        n='1.7.4a: documentoDuplicado(document_number) -> 400'; ret=$true },
      @{ t='msg'; o='form';      d='admin';       n='1.7.5a: mostrarError(Ya existe un paciente con ese documento)'; ret=$true },
      @{ t='op'; g='documento libre' },
      @{ t='msg'; o='gestor';    d='gestor';      n='1.7.4b: return attrs' },
      @{ t='fin' },
      @{ t='op'; g='sin document_number' },
      @{ t='msg'; o='gestor';    d='gestor';      n='1.7.3c: return attrs  {sin consulta de duplicados}' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='corrección: perform_update' },
      @{ t='msg'; o='gestor';    d='paciente';    n='1.8a: UPDATE patients SET document_type, document_number, first_name, last_name, birth_date, sex, phone, updated_at = now() WHERE id = :id()' },
      @{ t='msg'; o='gestor';    d='bitgestor';   n='1.9a: registrar(PATIENT_UPDATE, before, after)  {admin_ops.py:220}' },
      @{ t='msg'; o='bitgestor'; d='bitacora';    n='1.10a: INSERT INTO audit_log (action = ''patient.update'', entity = ''patients'', entity_id, detail)()  {después del COMMIT}' },
      @{ t='msg'; o='gestor';    d='form';        n='1.10a.1: 200(Paciente)'; ret=$true },
      @{ t='op'; g='alta: perform_create' },
      @{ t='msg'; o='gestor';    d='paciente';    n='1.8b: INSERT INTO patients (organization_id, document_type, document_number, first_name, last_name, birth_date, sex, phone, is_active = true)()' },
      @{ t='msg'; o='gestor';    d='form';        n='1.8b.1: 201(Paciente)  {sin asiento en la bitácora}'; ret=$true },
      @{ t='fin' },
      @{ t='msg'; o='form';      d='admin';       n='1.11: mostrarListaActualizada()  {setFormulario(VACIO) y cargar()}'; ret=$true },

      @{ t='nota'; txt='FLUJO 2 Dar de baja un paciente (baja lógica)' },
      @{ t='msg'; o='admin';     d='pantalla';    n='2.1: buscar(q, estado)' },
      @{ t='msg'; o='pantalla';  d='busqueda';    n='2.2: GET /api/patients/search/?q&status&page_size=100()' },
      @{ t='alt' },
      @{ t='op'; g='q no vacío  {search.py:184}' },
      @{ t='msg'; o='busqueda';  d='paciente';    n='2.2.1: SELECT id, first_name, last_name, document_number FROM patients WHERE organization_id = :org()' },
      @{ t='loop'; g='por cada candidato, iterator(chunk_size=500)  {search.py:197}' },
      @{ t='msg'; o='busqueda';  d='busqueda';    n='2.2.2: normalizar(nombre y apellido) contiene normalizar(q)' },
      @{ t='fin' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='status == active  {search.py:220}' },
      @{ t='msg'; o='busqueda';  d='paciente';    n='2.3a: SELECT * FROM patients WHERE organization_id = :org AND (document_number = :q OR id IN (:ids)) AND is_active = true ORDER BY last_name, first_name LIMIT 100()' },
      @{ t='op'; g='status == inactive  {search.py:222}' },
      @{ t='msg'; o='busqueda';  d='paciente';    n='2.3b: SELECT * FROM patients WHERE organization_id = :org AND (document_number = :q OR id IN (:ids)) AND is_active = false ORDER BY last_name, first_name LIMIT 100()' },
      @{ t='op'; g='status vacío (Todos)' },
      @{ t='msg'; o='busqueda';  d='paciente';    n='2.3c: SELECT * FROM patients WHERE organization_id = :org AND (document_number = :q OR id IN (:ids)) ORDER BY last_name, first_name LIMIT 100()' },
      @{ t='fin' },
      @{ t='msg'; o='busqueda';  d='pantalla';    n='2.3.1: 200(count, results)'; ret=$true },
      @{ t='msg'; o='admin';     d='pantalla';    n='2.4: desactivar(paciente)  {sólo si is_active y puede(deactivate), Pacientes.tsx:787; abre el modal}' },
      @{ t='msg'; o='admin';     d='pantalla';    n='2.4.1: confirmarDesactivacion()  {Pacientes.tsx:1096}' },
      @{ t='msg'; o='pantalla';  d='gestor';      n='2.5: DELETE /api/patients/admin/{id}/()' },
      @{ t='msg'; o='gestor';    d='auth';        n='2.6: verificarPermiso(patients.patient.deactivate)  {administrador o recepción}' },
      @{ t='msg'; o='auth';      d='gestor';      n='2.6.1: has_permission(code) -> True'; ret=$true },
      @{ t='msg'; o='gestor';    d='paciente';    n='2.6.2: SELECT * FROM patients WHERE organization_id = :org AND id = :id()  {get_object}' },
      @{ t='msg'; o='gestor';    d='paciente';    n='2.7: UPDATE patients SET is_active = false, updated_at = now() WHERE id = :id()  {nunca DELETE; admin_ops.py:238}' },
      @{ t='msg'; o='gestor';    d='bitgestor';   n='2.8: registrar(PATIENT_DEACTIVATE, before, after)  {admin_ops.py:246}' },
      @{ t='msg'; o='bitgestor'; d='bitacora';    n='2.8.1: INSERT INTO audit_log (action = ''patient.deactivate'', entity = ''patients'', entity_id, detail)()  {después del COMMIT}' },
      @{ t='msg'; o='gestor';    d='pantalla';    n='2.8.2: 204()'; ret=$true },
      @{ t='alt' },
      @{ t='op'; g='detalle?.id === pacienteADesactivar.id  {Pacientes.tsx:294}' },
      @{ t='msg'; o='pantalla';  d='pantalla';    n='2.9: setDetalle(null)  {cierra el detalle abierto}' },
      @{ t='fin' },
      @{ t='msg'; o='pantalla';  d='admin';       n='2.10: mostrarListaActualizada()  {cargar(), vuelve a 2.2}'; ret=$true },

      @{ t='nota'; txt='FLUJO 3 Fusionar pacientes duplicados' },
      @{ t='msg'; o='admin';     d='ffusion';     n='3.1: elegir(fusionOrigen, fusionDestino)  {sólo activos de la lista cargada, Pacientes.tsx:846, :878}' },
      @{ t='msg'; o='ffusion';   d='ffusion';     n='3.2: solicitarFusion()  {Pacientes.tsx:316}' },
      @{ t='alt' },
      @{ t='op'; g='!fusionOrigen || !fusionDestino  {Pacientes.tsx:321}' },
      @{ t='msg'; o='ffusion';   d='admin';       n='3.2.1a: mostrarError(Falta el origen o el destino)'; ret=$true },
      @{ t='op'; g='fusionOrigen === fusionDestino  {Pacientes.tsx:331}' },
      @{ t='msg'; o='ffusion';   d='admin';       n='3.2.1b: mostrarError(El origen y el destino no pueden ser el mismo)'; ret=$true },
      @{ t='op'; g='par elegido y distinto' },
      @{ t='msg'; o='ffusion';   d='ffusion';     n='3.2.1c: setConfirmandoFusion(true)  {abre el modal, Pacientes.tsx:1114}' },
      @{ t='fin' },
      @{ t='msg'; o='admin';     d='ffusion';     n='3.3: confirmar()  {confirmarFusion, Pacientes.tsx:1237}' },
      @{ t='msg'; o='ffusion';   d='fusion';      n='3.4: POST /api/patients/admin/merge/(source_patient, target_patient)' },
      @{ t='msg'; o='fusion';    d='auth';        n='3.5: verificarPermiso(patients.patient.merge)  {sólo el administrador}' },
      @{ t='msg'; o='auth';      d='fusion';      n='3.5.1: has_permission(code) -> True'; ret=$true },
      @{ t='msg'; o='fusion';    d='fusion';      n='3.6: MergePatientsSerializer.validate(attrs)  {admin_ops.py:113}' },
      @{ t='alt' },
      @{ t='op'; g='source_patient == target_patient  {admin_ops.py:114}' },
      @{ t='msg'; o='fusion';    d='ffusion';     n='3.6.1: fusionNoValida(target_patient) -> 400'; ret=$true },
      @{ t='fin' },
      @{ t='msg'; o='fusion';    d='paciente';    n='3.7: SELECT * FROM patients WHERE organization_id = :org AND id = :source FOR UPDATE()  {dentro de transaction.atomic(), admin_ops.py:285}' },
      @{ t='msg'; o='fusion';    d='paciente';    n='3.7.1: SELECT * FROM patients WHERE organization_id = :org AND id = :target FOR UPDATE()' },
      @{ t='msg'; o='paciente';  d='fusion';      n='3.7.2: Paciente(source) | None, Paciente(target) | None'; ret=$true },
      @{ t='alt' },
      @{ t='op'; g='source is None or target is None  {admin_ops.py:306}' },
      @{ t='msg'; o='fusion';    d='ffusion';     n='3.7.3a: fusionNoValida(paciente_no_encontrado) -> 404'; ret=$true },
      @{ t='op'; g='not source.is_active  {admin_ops.py:315}' },
      @{ t='msg'; o='fusion';    d='ffusion';     n='3.7.3b: fusionNoValida(paciente_origen_inactivo) -> 400'; ret=$true },
      @{ t='fin' },
      @{ t='msg'; o='fusion';    d='paciente';    n='3.8: UPDATE patients SET guardian_id = :target WHERE organization_id = :org AND guardian_id = :source()  {los dependientes del origen pasan al destino}' },
      @{ t='msg'; o='fusion';    d='antecedente'; n='3.9: UPDATE patient_history_entries SET patient_id = :target WHERE patient_id = :source()' },
      @{ t='msg'; o='fusion';    d='ficha';       n='3.10: UPDATE appointments SET patient_id = :target WHERE patient_id = :source()  {el pago cuelga de la ficha y la sigue}' },
      @{ t='alt' },
      @{ t='op'; g='source.user_id is not None and target.user_id is None  {admin_ops.py:353}' },
      @{ t='msg'; o='fusion';    d='paciente';    n='3.11: UPDATE patients SET user_id = NULL, updated_at = now() WHERE id = :source()  {libera la cuenta: user_id es OneToOne}' },
      @{ t='msg'; o='fusion';    d='fusion';      n='3.11.1: target.user = usuario  {se guarda en 3.13}' },
      @{ t='fin' },
      @{ t='loop'; g='por cada campo de birth_date, sex, phone  {admin_ops.py:372}' },
      @{ t='alt' },
      @{ t='op'; g='not destino and origen  {admin_ops.py:386}' },
      @{ t='msg'; o='fusion';    d='fusion';      n='3.12: setattr(target, campo, origen); campos_actualizados.append(campo)' },
      @{ t='fin' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='target.user_id is not None  {admin_ops.py:396}' },
      @{ t='msg'; o='fusion';    d='fusion';      n='3.12.1: campos_actualizados.append(user)' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='campos_actualizados  {admin_ops.py:401}' },
      @{ t='msg'; o='fusion';    d='paciente';    n='3.13: UPDATE patients SET <campos_actualizados>, updated_at = now() WHERE id = :target()  {sólo completa lo que falta}' },
      @{ t='fin' },
      @{ t='msg'; o='fusion';    d='paciente';    n='3.14: UPDATE patients SET is_active = false, updated_at = now() WHERE id = :source()  {admin_ops.py:414}' },
      @{ t='msg'; o='fusion';    d='bitgestor';   n='3.15: registrar(PATIENT_MERGE, before, after)  {admin_ops.py:429, sólo encola}' },
      @{ t='msg'; o='bitgestor'; d='bitacora';    n='3.15.1: INSERT INTO audit_log (action = ''patient.merge'', entity = ''patients'', entity_id = :target, detail)()  {después del COMMIT}' },
      @{ t='msg'; o='fusion';    d='ffusion';     n='3.15.2: 200(Paciente destino)'; ret=$true },
      @{ t='msg'; o='ffusion';   d='admin';       n='3.16: mostrarListaActualizada()  {cierra el modal y cargar()}'; ret=$true },

      @{ t='nota'; txt='FLUJO 4 Excepciones comunes a /patients/admin/' },
      @{ t='alt' },
      @{ t='op'; g='has_permission(code) es False  {permissions.py:21}' },
      @{ t='msg'; o='auth';      d='gestor';      n='4.1a: has_permission(code) -> False'; ret=$true },
      @{ t='msg'; o='gestor';    d='pantalla';    n='4.2a: rechazar(sin permiso) -> 403'; ret=$true },
      @{ t='op'; g='el paciente no es de la organización  {get_queryset, admin_ops.py:134}' },
      @{ t='msg'; o='gestor';    d='paciente';    n='4.1b: SELECT * FROM patients WHERE organization_id = :org AND id = :id()  {0 filas}' },
      @{ t='msg'; o='gestor';    d='pantalla';    n='4.2b: rechazar(No encontrado) -> 404'; ret=$true },
      @{ t='fin' }
    )
}

$NAVEGACION_SPRINT2['CU11'] = @{
    actor  = 'Administrador de Organización'
    nota   = 'CU11 · US-10. Sólo web: no hay pantalla móvil de pacientes. La entrada «Pacientes» de BarraPlataforma.tsx:200-206 pide patients.patient.read, y la ruta /pacientes (App.tsx:210) sólo exige sesión: quien protege es el backend. Dentro de la misma pantalla, el formulario se muestra con puede(patients.patient.create) o puede(patients.patient.update) (Pacientes.tsx:476), el botón Desactivar con puede(patients.patient.deactivate) (:787) y la fusión con puede(patients.patient.merge) (:816), que sólo tiene el administrador. Los dos modales (:1015 y :1114) son componentes de Pacientes.tsx sin campos propios: confirman el id ya elegido. La lista y el detalle usan patients/search.py, de CU10. Cliente HTTP: frontend/src/api/pacientes.ts.'
    menu   = @{ n='Panel.tsx'; ruta='/panel' }
    publicas = @()
    controladores = @{
      search = @{ n='patients/search.py'; ops=@('PatientSearchViewSet.list(request)', 'PatientSearchViewSet.retrieve(request, pk)') }
      admin  = @{ n='patients/admin_ops.py'; ops=@('PatientAdminViewSet.create(request)', 'PatientAdminViewSet.partial_update(request, pk)', 'PatientAdminViewSet.destroy(request, pk)', 'PatientAdminViewSet.merge(request)') }
    }
    areas = @(
      @{ guarda='[sesión + patients.patient.read]'
         vista=@{ n='Pacientes.tsx'; ruta='/pacientes'; atr=@('q', 'status', 'page_size', 'full_name', 'document_number', 'is_active') }; vistaCtrl='search'
         forms=@(
           @{ n='FormularioPaciente'; atr=@('document_type', 'document_number', 'first_name', 'last_name', 'birth_date', 'sex', 'phone'); ctrl='admin' },
           @{ n='ModalDesactivarPaciente'; atr=@('id'); ctrl='admin' },
           @{ n='ModalFusionarPacientes'; atr=@('source_patient', 'target_patient'); ctrl='admin' }
         ) }
    )
}

$CASOS_SPRINT2['CU18'] = @{
    cu     = 'CU18'
    nombre = 'Reserva de Ficha Médica'
    us     = 'US-17'
    nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Web (Disponibilidad.tsx + ModalReservarFicha.tsx; la ficha se ve en MisFichas.tsx) y móvil (availability_screen.dart reserva con la hoja _ConfirmarReserva y abre /appointments/{id}, AppointmentDetailScreen). La ficha nace pending_payment con expires_at = ahora + APPOINTMENT_HOLD_MINUTES (config/settings.py:260) y con su precio: AppointmentSerializer expone fee = quote() (appointments/serializers.py:24-31, payments/pricing.py:39). El pago en sí (checkout, Pasarela de Pago, webhook y confirm_payment, que pasa la ficha a confirmed) es el CU19 y no se dibuja acá. El serializer también lee payment_status (SELECT de payments ORDER BY created_at DESC LIMIT 1, serializers.py:33-37), que al nacer la ficha es null. Vencido el plazo, start_checkout rechaza el cobro con ficha_vencida (payments/services.py:44). El diagrama de estado es el flujo de la transacción; los estados de la ficha van en el de tiempo.'
    participantes = @(
      @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=3 },

      @{ k='pantalla'; n='PantallaDisponibilidad'; rol='boundary'; col=1; f=0.8
         nota='Web: frontend/src/paginas/Disponibilidad.tsx y frontend/src/api/disponibilidad.ts; llega desde BuscarProfesionales.tsx con ?professional=. Móvil: mobile/lib/features/availability/availability_screen.dart (AvailabilityScreen, ruta /professionals/:id/availability, app_router.dart:436) y availability_api.dart. Backend: AvailabilityView en scheduling/availability.py.'
         atr=@('GET /api/scheduling/availability/ : 200 | 400 | 401 | 403')
         ops=@('disponibilidadConsolidada(filtros, contexto, senal)', 'confirmarReserva(patientId)', '_reservar(slot, fecha)', 'AvailabilityView.get(request)') },

      @{ k='form';     n='FormularioReserva'; rol='boundary'; col=1; f=3.2
         nota='Web: frontend/src/componentes/ModalReservarFicha.tsx, frontend/src/api/fichas.ts (reservarFicha) y frontend/src/api/pacientes.ts (listarOpcionesDePaciente). Móvil: la hoja _ConfirmarReserva de availability_screen.dart:287, mobile/lib/features/dependents/patient_selector.dart y dependents_api.dart:195, y reservarFicha en mobile/lib/features/appointments/appointments_api.dart:160. Backend: AppointmentViewSet.create en appointments/booking.py y la acción patient-options de patients/dependents.py.'
         atr=@('GET /api/patients/dependents/patient-options/ : 200 | 401', 'POST /api/appointments/appointments/ : 201 | 400 | 401 | 403 | 409')
         ops=@('listarOpcionesDePaciente(contexto, senal)', 'reservarFicha(datos, contexto)', 'AppointmentViewSet.create(request)', 'patient_options(request)') },

      @{ k='pantficha'; n='PantallaFicha'; rol='boundary'; col=1; f=5.6
         nota='Web: frontend/src/paginas/MisFichas.tsx (/mis-fichas; importe(ficha) en :54 muestra el fee) y misFichas de frontend/src/api/fichas.ts. Móvil: mobile/lib/features/appointments/appointment_detail_screen.dart (AppointmentDetailScreen, /appointments/:id, abierta por availability_screen.dart:124) y my_appointments_screen.dart (MyAppointmentsScreen, /appointments), con verFicha y misFichas de appointments_api.dart:180-193. Backend: AppointmentViewSet.retrieve / list en appointments/booking.py.'
         atr=@('GET /api/appointments/appointments/ : 200 | 401 | 403', 'GET /api/appointments/appointments/{id}/ : 200 | 401 | 403 | 404')
         ops=@('misFichas(contexto, senal)', 'verFicha(client, id)', '_recargar(silencioso)', 'importe(ficha)', 'retrieve(request, pk)') },

      @{ k='gdisp';    n='GestorDisponibilidad'; rol='control'; col=2; f=0.4
         nota='scheduling/availability.py. Deriva los espacios de cada regla de agenda y les resta los bloqueos y las fichas activas. El horizonte máximo es AVAILABILITY_MAX_HORIZON_DAYS (config/settings.py:255).'
         atr=@()
         ops=@('consolidated_availability(practitioner_id, date_from, date_to, branch_id, now)', 'generate_slots(schedule, date_from, date_to, tz)', '_booked_slots(practitioner_id, date_from, date_to)', '_blocked(start_aware, end_aware, blocks)') },

      @{ k='auth';     n='GestorAutenticacion'; rol='control'; col=2; f=1.8
         nota='accounts/authentication.py (usuario e inquilino desde el token), scheduling/permissions.py (CanReadSlots) y appointments/permissions.py (CanCreateAppointments, CanReadAppointments).'
         atr=@()
         ops=@('authenticate(request)', 'has_permission(code)') },

      @{ k='gres';     n='GestorReserva'; rol='control'; col=2; f=3.2
         nota='appointments/booking.py (book_appointment, en un transaction.atomic con select_for_update sobre la agenda; get_queryset filtra por el paciente y sus dependientes) y appointments/serializers.py (BookAppointmentSerializer, AppointmentSerializer). El selector de paciente sale de patient_options y titular_de en patients/dependents.py.'
         atr=@()
         ops=@('book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)', '_validate_slot_is_real(schedule, starts_at)', 'get_queryset()', 'patient_options(user)', 'titular_de(user)') },

      @{ k='gplan';    n='GestorPlan'; rol='control'; col=2; f=4.8
         nota='tenancy/plans.py (CG-08: lo que promete el plan se cumple). AppointmentViewSet.create lo llama antes de reservar (booking.py:200-203). Sin plan vigente o con el tope max_appointments_month alcanzado lanza PlanLimitExceeded, un 403 (plans.py:67-70).'
         atr=@()
         ops=@('appointments_this_month(organization)', 'check_limit(organization, field, usados, que, singular)', 'current_plan(organization)') },

      @{ k='gtarifa';  n='GestorTarifa'; rol='control'; col=2; f=6.4
         nota='payments/pricing.py (quote) y AppointmentSerializer.get_fee en appointments/serializers.py:27-31. Cobra lo mismo que informa el asistente: consulta asociada a la especialidad del profesional, después la que la nombra, después la consulta genérica y, si no hay ninguna, APPOINTMENT_DEFAULT_FEE (config/settings.py:292-293, 100.00 BOB). Se calcula al serializar: no se guarda en appointments.'
         atr=@()
         ops=@('get_fee(obj)', 'quote(appointment)', '_mas_barato(servicios)') },

      @{ k='agenda';   n='Agenda'; rol='entity'; col=3; f=0
         nota='Tabla schedules (la regla de agenda de US-13). Los bloqueos de US-14 viven en schedule_blocks y se leen en la misma consulta por rango.'
         atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'valid_from : date', 'valid_until : date', 'is_active : boolean')
         ops=@('filter(practitioner_id, is_active)', 'select_for_update()') },

      @{ k='ficha';    n='Ficha'; rol='entity'; col=3; f=1.2
         nota='Tabla appointments. UNIQUE parcial uq_appointment_active_slot (schedule_id, starts_at) WHERE status IN (pending_payment, confirmed): dos reservas del mismo turno terminan en una fila y un IntegrityError.'
         atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar(16)', 'expires_at : timestamptz', 'created_at : timestamptz')
         ops=@('filter(practitioner_id, status__in=ACTIVE_STATUSES)', 'filter(organization, created_at__gte).count()', 'create(status=pending_payment, expires_at)') },

      @{ k='entpac';   n='Paciente'; rol='entity'; col=3; f=2.4
         nota='Tabla patients: el titular y sus dependientes (guardian_id), de US-07.'
         atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'is_active : boolean')
         ops=@('filter(user, is_active)', 'dependents.filter(is_active)', 'filter(pk, organization, is_active)') },

      @{ k='prof';     n='Profesional'; rol='entity'; col=3; f=3.4
         nota='Tabla practitioners (US-12).'
         atr=@('id : uuid', 'organization_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)', 'is_active : boolean')
         ops=@('filter(pk, organization, is_active)') },

      @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=4.4
         nota='Tabla branches. Su timezone fija el corte de hora pasada y la reconstrucción del turno.'
         atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'timezone : varchar(40)', 'is_active : boolean')
         ops=@('filter(pk, organization, is_active)') },

      @{ k='suscripcion'; n='Suscripcion'; rol='entity'; col=3; f=5.4
         nota='Tabla subscriptions, unida a subscription_plans por plan_id. Se lee en platform_admin_context (plans.py:85). max_appointments_month NULL es ilimitado.'
         atr=@('id : uuid', 'organization_id : uuid', 'plan_id : uuid', 'starts_at : date', 'ends_at : date', 'status : varchar(12)', 'max_appointments_month : integer')
         ops=@('filter(organization_id, status=active, starts_at__lte).exclude(ends_at__lt).first()') },

      @{ k='servicio'; n='Servicio'; rol='entity'; col=3; f=6.4
         nota='Tabla services (catálogo de US-32). El precio de la consulta sale de acá.'
         atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'kind : varchar(20)', 'specialty_id : uuid', 'price : numeric(10,2)', 'currency : varchar(3)', 'is_active : boolean')
         ops=@('filter(organization_id, kind=consultation, is_active, price__gt=0)') },

      @{ k='especialidad'; n='Especialidad'; rol='entity'; col=3; f=7.4
         nota='Tabla specialties, unida al profesional por practitioner_specialties.'
         atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'is_active : boolean')
         ops=@('practitioner.specialties.all()', 'filter(organization_id).values_list(name)') }
    )

    estado = @{
      estados = @(
        @{ k='ini';    tipo='inicial'; col=0; f=0 },
        @{ k='aut';    n='Autenticar Paciente';             col=0; f=2 },
        @{ k='fin401'; tipo='final';   col=0; f=4.5 },
        @{ k='menu';   n='Seleccionar operación';           col=1; f=2 },
        @{ k='disp';   n='Desplegar disponibilidad';        col=2; f=0 },
        @{ k='cap';    n='Capturar espacio y paciente';     col=2; f=2 },
        @{ k='ver';    n='Desplegar ficha y precio';        col=2; f=4.2 },
        @{ k='val';    n='Validar plan y datos';            col=3; f=2 },
        @{ k='lock';   n='Bloquear agenda y validar turno'; col=3; f=3.6 },
        @{ k='error';  n='Informar error';                  col=4; f=5.5 },
        @{ k='ok';     n='Transacción completada';          col=4; f=1 },
        @{ k='fin';    tipo='final';   col=4; f=3 }
      )
      transiciones = @(
        @{ de='ini';   a='aut' },
        @{ de='aut';   a='menu';   r='[token y permiso] {IsAuthenticated + CanReadSlots, availability.py:251}' },
        @{ de='aut';   a='fin401'; r='[sin token o sin permiso] {401 | 403}' },
        @{ de='menu';  a='disp';   r='[consultar] {GET /scheduling/availability/}' },
        @{ de='menu';  a='cap';    r='[reservar] {CanCreateAppointments, booking.py:168}' },
        @{ de='menu';  a='ver';    r='[ver la ficha] {GET /appointments/appointments/{id}/, booking.py:167}' },
        @{ de='disp';  a='ok';     r='[rango válido] / consolidated_availability() {availability.py:266}' },
        @{ de='disp';  a='error';  r='[rango invertido o mayor a 30 días] {400 availability.py:115, :119}' },
        @{ de='cap';   a='val';    r='confirmarReserva() {POST /appointments/appointments/}' },
        @{ de='val';   a='lock';   r='[plan con cupo; paciente, profesional y sucursal activos; turno futuro] / select_for_update() {booking.py:200, :113}' },
        @{ de='val';   a='error';  r='[sin plan o sin cupo, dato inválido o turno pasado] {403 plans.py:130, 400 booking.py:87, :107}' },
        @{ de='lock';  a='ok';     r='[turno real y libre] / create(pending_payment) {201 booking.py:130}' },
        @{ de='lock';  a='error';  r='[turno no real u ocupado] {400 booking.py:66, 409 :143}' },
        @{ de='ver';   a='ok';     r='/ quote() {fee, serializers.py:27, pricing.py:39}' },
        @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
        @{ de='ok';    a='fin' }
      )
    }

    tiempo = @{
      escenario = 'reservar un turno y dejarlo sin pagar'
      nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:260), que fija expires_at en appointments/booking.py:140. La ficha nace pending_payment en el mismo COMMIT, con su fee (quote, payments/pricing.py:39). Desde ese COMMIT el turno deja de ofrecerse en la disponibilidad (_booked_slots, scheduling/availability.py:62-67). Mientras el plazo corre, el CU19 puede abrir el cobro y confirm_payment pasa la ficha a confirmed (CU19, payments/services.py:113); vencido el plazo, start_checkout rechaza el cobro con ficha_vencida (payments/services.py:44).'
      lineas = @(
        @{ n='Transacción'
           estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
           marcas=@( @{ t=0;  e='Inactiva' },
                     @{ t=6;  e='Autenticando'; ev='POST /appointments/appointments/' },
                     @{ t=16; e='Validando';    ev='book_appointment()' },
                     @{ t=26; e='Escribiendo';  ev='select_for_update()' },
                     @{ t=36; e='Confirmada';   ev='COMMIT' },
                     @{ t=44; e='Inactiva';     ev='201 (Ficha, fee)' } ) },
        @{ n='Ficha'
           estados=@('Sin ficha', 'pending_payment', 'confirmed')
           marcas=@( @{ t=0;  e='Sin ficha' },
                     @{ t=36; e='pending_payment'; ev='create()' } ) },
        @{ n='Plazo de pago'
           estados=@('Sin plazo', 'Corriendo', 'Vencido')
           marcas=@( @{ t=0;  e='Sin plazo' },
                     @{ t=36; e='Corriendo'; ev='expires_at' },
                     @{ t=84; e='Vencido';   ev='vence'; r='15 min' } ) },
        @{ n='Cobro (CU19)'
           estados=@('Sin ficha', 'Admitido', 'Rechazado')
           marcas=@( @{ t=0;  e='Sin ficha' },
                     @{ t=36; e='Admitido';  ev='fee' },
                     @{ t=84; e='Rechazado'; ev='ficha_vencida' } ) }
      )
    }

    grupos = [ordered]@{
      1 = 'consultar la disponibilidad'
      2 = 'reservar la ficha'
      3 = 'ver la ficha con su precio'
      4 = 'excepciones'
    }

    # Pares con dos mensajes en el mismo sentido (el tope): paciente->pantalla,
    # form->gres, gres->entpac, gres->ficha, gres->auth y gres->gtarifa. El
    # precio vive en su propio controlador para no pasar de dos sobre gres->ficha.
    mensajes = @(
      @{ g=1; d='paciente'; a='pantalla';    m='elegirProfesional(profesional, desde, hasta, sucursal)' },
      @{ g=1; d='pantalla'; a='gdisp';       m='consultarDisponibilidad(practitioner, from, to, branch)' },
      @{ g=1; d='gdisp';    a='auth';        m='autorizar(scheduling.slot.read)' },
      @{ g=1; d='gdisp';    a='agenda';      m='derivarEspacios(rango)' },
      @{ g=1; d='gdisp';    a='ficha';       m='restarOcupados(ACTIVE_STATUSES)' },

      @{ g=2; d='paciente'; a='pantalla';    m='elegirEspacio(slot)' },
      @{ g=2; d='pantalla'; a='form';        m='abrirConfirmacion(slot)' },
      @{ g=2; d='form';     a='gres';        m='listarOpcionesDePaciente()' },
      @{ g=2; d='gres';     a='entpac';      m='leerTitularYDependientes(user)' },
      @{ g=2; d='paciente'; a='form';        m='confirmarReserva(paciente)' },
      @{ g=2; d='form';     a='gres';        m='reservar(paciente, schedule, starts_at)' },
      @{ g=2; d='gres';     a='auth';        m='autorizar(appointments.appointment.create)' },
      @{ g=2; d='gres';     a='gplan';       m='verificarCupo(max_appointments_month)' },
      @{ g=2; d='gplan';    a='ficha';       m='contarFichasDelMes()' },
      @{ g=2; d='gplan';    a='suscripcion'; m='leerPlanVigente()' },
      @{ g=2; d='gres';     a='entpac';      m='validarPaciente(patient_id)' },
      @{ g=2; d='gres';     a='prof';        m='validarProfesional(practitioner_id)' },
      @{ g=2; d='gres';     a='sucursal';    m='validarSucursal(branch_id)' },
      @{ g=2; d='gres';     a='agenda';      m='bloquearAgenda(schedule_id)' },
      @{ g=2; d='gres';     a='gres';        m='validarTurnoReal(starts_at)' },
      @{ g=2; d='gres';     a='ficha';       m='crear(pending_payment, expires_at)' },
      @{ g=2; d='gres';     a='gtarifa';     m='cotizar(fichaNueva)' },

      @{ g=3; d='form';     a='pantficha';   m='abrirFicha(id)' },
      @{ g=3; d='pantficha'; a='gres';       m='verFicha(id)' },
      @{ g=3; d='gres';     a='auth';        m='autorizar(appointments.appointment.read)' },
      @{ g=3; d='gres';     a='ficha';       m='leerFicha(id)' },
      @{ g=3; d='gres';     a='gtarifa';     m='cotizar(ficha)' },
      @{ g=3; d='gtarifa';  a='servicio';    m='leerConsultas()' },
      @{ g=3; d='gtarifa';  a='especialidad'; m='leerEspecialidades(profesional)' },

      @{ g=4; d='gdisp';    a='pantalla';    m='rangoInvalido() -> 400' },
      @{ g=4; d='gplan';    a='form';        m='limiteDelPlan() -> 403' },
      @{ g=4; d='gres';     a='form';        m='reservaInvalida(code) -> 400' },
      @{ g=4; d='gres';     a='form';        m='turnoOcupado() -> 409' }
    )

    secuencia = @(
      @{ t='nota'; txt='FLUJO 1 Consultar la disponibilidad' },
      @{ t='msg'; o='paciente'; d='pantalla'; n='1.1: elegirProfesional(profesional, desde, hasta, sucursal)' },
      @{ t='msg'; o='pantalla'; d='gdisp';    n='1.2: GET /api/scheduling/availability/?practitioner=&from=&to=&branch=()' },
      @{ t='msg'; o='gdisp';    d='auth';     n='1.3: authenticate(request)  {IsAuthenticated, CanReadSlots}' },
      @{ t='alt' },
      @{ t='op'; g='to < from o más de AVAILABILITY_MAX_HORIZON_DAYS' },
      @{ t='msg'; o='gdisp';    d='pantalla'; n='1.4a: rangoInvalido() -> 400  {availability.py:115, :119}'; ret=$true },
      @{ t='msg'; o='pantalla'; d='paciente'; n='1.5a: mostrarError(detail)'; ret=$true },
      @{ t='op'; g='rango válido' },
      @{ t='msg'; o='gdisp';    d='agenda';   n='1.4b: SELECT * FROM schedules WHERE practitioner_id = :p AND is_active AND valid_from <= :to()' },
      @{ t='msg'; o='agenda';   d='gdisp';    n='1.4b.1: list(Schedule)'; ret=$true },
      @{ t='msg'; o='gdisp';    d='agenda';   n='1.5b: SELECT * FROM schedule_blocks WHERE is_active AND starts_at < :fin AND ends_at > :inicio()' },
      @{ t='msg'; o='gdisp';    d='ficha';    n='1.6b: SELECT schedule_id, starts_at FROM appointments WHERE practitioner_id = :p AND status IN (''pending_payment'', ''confirmed'')()' },
      @{ t='msg'; o='ficha';    d='gdisp';    n='1.6b.1: set(schedule_id, starts_at)'; ret=$true },
      @{ t='loop'; g='por cada regla de agenda y cada espacio del rango' },
      @{ t='msg'; o='gdisp';    d='gdisp';    n='1.7b: generate_slots(schedule, desde, hasta)  {descarta pasados, bloqueados y ocupados}' },
      @{ t='fin' },
      @{ t='msg'; o='gdisp';    d='pantalla'; n='1.7b.1: 200(days, slots)'; ret=$true },
      @{ t='msg'; o='pantalla'; d='paciente'; n='1.8b: mostrarGrilla(espacios)'; ret=$true },
      @{ t='fin' },

      @{ t='nota'; txt='FLUJO 2 Reservar la ficha' },
      @{ t='msg'; o='paciente'; d='pantalla'; n='2.1: elegirEspacio(slot)' },
      @{ t='msg'; o='pantalla'; d='form';     n='2.2: abrirConfirmacion(slot)  {web: ModalReservarFicha; móvil: _ConfirmarReserva}' },
      @{ t='msg'; o='form';     d='gres';     n='2.3: GET /api/patients/dependents/patient-options/()' },
      @{ t='msg'; o='gres';     d='entpac';   n='2.3.1: SELECT * FROM patients WHERE user_id = :user AND is_active LIMIT 1()' },
      @{ t='msg'; o='gres';     d='entpac';   n='2.3.2: SELECT * FROM patients WHERE guardian_id = :titular AND is_active()' },
      @{ t='loop'; g='por cada dependiente activo del titular' },
      @{ t='msg'; o='gres';     d='gres';     n='2.3.3: armarOpcion(dependiente)  {dependents.py:186-196}' },
      @{ t='fin' },
      @{ t='msg'; o='gres';     d='form';     n='2.3.4: opciones(titular, dependientes)'; ret=$true },
      @{ t='msg'; o='paciente'; d='form';     n='2.4: confirmarReserva(paciente)' },
      @{ t='msg'; o='form';     d='gres';     n='2.5: POST /api/appointments/appointments/(patient, practitioner, branch, schedule, starts_at)' },
      @{ t='msg'; o='gres';     d='auth';     n='2.6: authenticate(request)  {IsAuthenticated, CanCreateAppointments}' },
      @{ t='msg'; o='gres';     d='gplan';    n='2.7: appointments_this_month(organization)  {booking.py:201}' },
      @{ t='msg'; o='gplan';    d='ficha';    n='2.7.1: SELECT COUNT(*) FROM appointments WHERE organization_id = :org AND created_at >= :inicio_de_mes()' },
      @{ t='msg'; o='gres';     d='gplan';    n='2.8: check_limit(organization, max_appointments_month, usados)' },
      @{ t='msg'; o='gplan';    d='suscripcion'; n='2.8.1: SELECT * FROM subscriptions JOIN subscription_plans WHERE organization_id = :org AND status = ''active'' AND starts_at <= :hoy AND NOT ends_at < :hoy ORDER BY starts_at DESC LIMIT 1()' },
      @{ t='alt' },
      @{ t='op'; g='sin plan vigente, o max_appointments_month no nulo y usados >= tope' },
      @{ t='msg'; o='gplan';    d='form';     n='2.9a: limiteDelPlan() -> 403 plan_limit  {plans.py:127-135}'; ret=$true },
      @{ t='msg'; o='form';     d='paciente'; n='2.10a: mostrarAviso(detail)'; ret=$true },
      @{ t='op'; g='plan con cupo o ilimitado' },
      @{ t='msg'; o='gres';     d='gres';     n='2.9b: book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)' },
      @{ t='fin' },
      @{ t='msg'; o='gres';     d='entpac';   n='2.11: SELECT * FROM patients WHERE id = :patient AND organization_id = :org AND is_active()' },
      @{ t='msg'; o='gres';     d='prof';     n='2.12: SELECT * FROM practitioners WHERE id = :practitioner AND organization_id = :org AND is_active()' },
      @{ t='msg'; o='gres';     d='sucursal'; n='2.13: SELECT * FROM branches WHERE id = :branch AND organization_id = :org AND is_active()' },
      @{ t='msg'; o='gres';     d='gres';     n='2.14: comparar(starts_at, now)  {turno_pasado, booking.py:106}' },
      @{ t='msg'; o='gres';     d='agenda';   n='2.15: SELECT * FROM schedules WHERE id = :schedule AND branch_id = :branch AND practitioner_id = :practitioner AND is_active FOR UPDATE()' },
      @{ t='msg'; o='agenda';   d='gres';     n='2.15.1: Schedule(branch)'; ret=$true },
      @{ t='msg'; o='gres';     d='gres';     n='2.16: _validate_slot_is_real(schedule, starts_at)  {no confía en la hora del cliente}' },
      @{ t='loop'; g='por cada espacio que generate_slots arma ese día' },
      @{ t='msg'; o='gres';     d='gres';     n='2.16.1: comparar(slot_start, starts_at)  {booking.py:63-65}' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='turno real y libre' },
      @{ t='msg'; o='gres';     d='ficha';    n='2.17a: INSERT INTO appointments (status = ''pending_payment'', expires_at = now + 15 min)()' },
      @{ t='msg'; o='gres';     d='gtarifa';  n='2.18a: get_fee(ficha)  {AppointmentSerializer; el cálculo es el del FLUJO 3}' },
      @{ t='msg'; o='gtarifa';  d='gres';     n='2.18a.1: fee(amount, currency)'; ret=$true },
      @{ t='msg'; o='gres';     d='form';     n='2.18a.2: 201(Ficha pending_payment, fee, payment_status = null)'; ret=$true },
      @{ t='msg'; o='form';     d='paciente'; n='2.19a: mostrarAviso(Ficha reservada, pendiente de pago)  {el pago sigue en CU19}'; ret=$true },
      @{ t='op'; g='otra ficha activa en el mismo turno' },
      @{ t='msg'; o='gres';     d='ficha';    n='2.17b: INSERT INTO appointments -> IntegrityError uq_appointment_active_slot()' },
      @{ t='msg'; o='gres';     d='form';     n='2.18b: turnoOcupado() -> 409'; ret=$true },
      @{ t='msg'; o='form';     d='pantalla'; n='2.19b: recargarDisponibilidad()  {cierra el modal o la hoja}' },
      @{ t='op'; g='paciente, profesional, sucursal o agenda inválidos, turno pasado o no real' },
      @{ t='msg'; o='gres';     d='form';     n='2.17c: reservaInvalida(code) -> 400  {booking.py:87, :94, :102, :107, :122, :66}'; ret=$true },
      @{ t='msg'; o='form';     d='paciente'; n='2.18c: mostrarAviso(code)'; ret=$true },
      @{ t='fin' },

      @{ t='nota'; txt='FLUJO 3 Ver la ficha con su precio' },
      @{ t='msg'; o='form';     d='pantficha'; n='3.1: abrirFicha(id)  {móvil: context.push(/appointments/id), availability_screen.dart:124; web: Mis fichas}' },
      @{ t='msg'; o='pantficha'; d='gres';    n='3.2: GET /api/appointments/appointments/{id}/()' },
      @{ t='msg'; o='gres';     d='auth';     n='3.3: authenticate(request)  {CanReadAppointments}' },
      @{ t='msg'; o='gres';     d='ficha';    n='3.4: SELECT * FROM appointments JOIN patients, practitioners, branches WHERE id = :id AND organization_id = :org AND (patient_id = :pac OR patients.guardian_id = :pac)()' },
      @{ t='msg'; o='ficha';    d='gres';     n='3.4.1: Ficha(practitioner, status, expires_at)'; ret=$true },
      @{ t='msg'; o='gres';     d='gtarifa';  n='3.5: get_fee(ficha) -> quote(ficha)  {serializers.py:27-31}' },
      @{ t='msg'; o='gtarifa';  d='servicio'; n='3.6: SELECT * FROM services WHERE organization_id = :org AND kind = ''consultation'' AND is_active AND price > 0()' },
      @{ t='msg'; o='servicio'; d='gtarifa';  n='3.6.1: list(Service)'; ret=$true },
      @{ t='msg'; o='gtarifa';  d='especialidad'; n='3.7: SELECT specialties.* FROM specialties JOIN practitioner_specialties ON specialty_id = specialties.id WHERE practitioner_id = :p()' },
      @{ t='msg'; o='especialidad'; d='gtarifa'; n='3.7.1: list(Specialty)'; ret=$true },
      @{ t='loop'; g='por cada consulta: asociada a la especialidad o que la nombra' },
      @{ t='msg'; o='gtarifa';  d='gtarifa';  n='3.8: _mas_barato(candidatos)  {pricing.py:53-57}' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='servicio is None' },
      @{ t='msg'; o='gtarifa';  d='especialidad'; n='3.9a: SELECT name FROM specialties WHERE organization_id = :org()  {pricing.py:59-63}' },
      @{ t='loop'; g='por cada consulta sin especialidad que no nombra ninguna' },
      @{ t='msg'; o='gtarifa';  d='gtarifa';  n='3.10a: _mas_barato(genericas)  {pricing.py:64-67}' },
      @{ t='fin' },
      @{ t='op'; g='ya hay servicio' },
      @{ t='msg'; o='gtarifa';  d='gtarifa';  n='3.9b: usar(servicio)' },
      @{ t='fin' },
      @{ t='alt' },
      @{ t='op'; g='servicio is not None' },
      @{ t='msg'; o='gtarifa';  d='gres';     n='3.11a: (servicio.price, servicio.currency)  {pricing.py:69-70}'; ret=$true },
      @{ t='op'; g='ninguna consulta con precio' },
      @{ t='msg'; o='gtarifa';  d='gres';     n='3.11b: (APPOINTMENT_DEFAULT_FEE, APPOINTMENT_FEE_CURRENCY)  {100.00 BOB, settings.py:292-293}'; ret=$true },
      @{ t='fin' },
      @{ t='msg'; o='gres';     d='pantficha'; n='3.12: 200(Ficha pending_payment, fee, expires_at)'; ret=$true },
      @{ t='msg'; o='pantficha'; d='paciente'; n='3.13: mostrarImporte(fee)  {botón Pagar: sigue en CU19}'; ret=$true }
    )
}

$NAVEGACION_SPRINT2['CU18'] = @{
    actor  = 'Paciente'
    nota   = 'CU18 · US-17. Navegación WEB: búsqueda -> disponibilidad -> reserva; Mis fichas muestra la ficha pendiente de pago con su importe (fee) y el plazo (expires_at). ModalReservarFicha es un componente que abre Disponibilidad.tsx con el espacio elegido; sus campos son el cuerpo del POST, y el selector de paciente sale de patients/dependents.py (patient-options). Al reservar, la web sólo avisa y recarga la grilla (Disponibilidad.tsx:138). El precio lo calcula payments/pricing.py (quote) dentro de AppointmentSerializer. Pagar es el CU19 y no se dibuja acá. Rutas de frontend/src/App.tsx; guardas del requiere de BarraPlataforma.tsx. Par MÓVIL (mobile/lib/core/router/app_router.dart): _HomeScreen -> /search -> /professionals/:id/availability (AvailabilityScreen, con la hoja _ConfirmarReserva y su selector de paciente) -> /appointments/:id (AppointmentDetailScreen, que abre sola tras reservar, availability_screen.dart:124); y _HomeScreen «Mis fichas» -> /appointments (MyAppointmentsScreen). Las de /appointments van con SoloPacientes. Clientes HTTP: frontend/src/api/disponibilidad.ts, fichas.ts y pacientes.ts; mobile/lib/features/availability/availability_api.dart y appointments/appointments_api.dart.'
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
         vista=@{ n='MisFichas.tsx'; ruta='/mis-fichas'; atr=@('practitioner_name', 'branch_name', 'starts_at', 'status', 'fee', 'expires_at') }; vistaCtrl='booking'
         forms=@() }
    )
}

$CASOS_SPRINT2['CU19'] = @{
  cu     = 'CU19'
  nombre = 'Pago de Ficha en Línea'
  us     = 'US-18'
  nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Flujo principal MÓVIL (docs/sprints/sprint-2/reparto.md:371 marca US-18 como MÓVIL y return_to cae en app por omisión, payments/views.py:78-80); la web (MisFichas.tsx) hace lo mismo con return_to = web y vuelve por un 302. Dos disparadores: el Paciente abre el cobro (CheckoutView) y la Pasarela de Pago (Stripe) avisa por el webhook firmado, que es lo único que confirma la ficha (confirm_payment, payments/services.py:74). La página de regreso no confirma nada: sólo devuelve al paciente, que sondea hasta ver confirmed. Toda la petición corre dentro de la transacción de TenantMiddleware (tenancy/middleware.py:39): los atomic() de services.py son savepoints, el correo sale en on_commit al cerrar esa transacción y la bitácora la escribe AuditTrailMiddleware después. No se dibuja el proveedor simulado (SimulatedProvider, providers.py:150, y simulated_checkout, views.py:246): sin STRIPE_SECRET_KEY es una página propia que llama a la misma confirm_payment. Estado: flujo de la transacción; los estados de la ficha y del pago van en el diagrama de tiempo.'

  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2.4 },

    @{ k='pantalla'; n='PantallaFicha'; rol='boundary'; col=1; f=0.6
       nota='Móvil (principal): mobile/lib/features/appointments/appointment_detail_screen.dart (_pagar :156, _empezarAEsperar :124, didChangeAppLifecycleState :96) y mobile/lib/features/payments/payments_api.dart (iniciarPago :46). Web: frontend/src/paginas/MisFichas.tsx (pagar :140, sondeo :113-138) y frontend/src/api/fichas.ts (iniciarPago :124, misFichas :80). Backend: CheckoutView en payments/views.py:47 y AppointmentViewSet en appointments/booking.py:150.'
       atr=@('POST /api/payments/appointments/{id}/checkout/ : 201 | 400 | 401 | 403 | 404 | 502', 'GET /api/appointments/appointments/{id}/ : 200 | 401 | 403 | 404', 'GET /api/appointments/appointments/ : 200 | 401 | 403')
       ops=@('_pagar()', 'iniciarPago(client, appointmentId)', '_empezarAEsperar()', 'didChangeAppLifecycleState(state)', 'pagar(ficha)', 'iniciarPago(id, contexto)', 'CheckoutView.post(request, pk)') },

    @{ k='regreso'; n='PaginaRegreso'; rol='boundary'; col=1; f=2.6
       nota='return_page en payments/views.py:186. Sin sesión y sin confirmar nada: con origen=web redirige a FRONTEND_BASE_URL/mis-fichas (config/settings.py:404); con origen=app devuelve un HTML que salta al deep link MOBILE_DEEP_LINK_BASE/appointments/{id} (settings.py:307) a los 600 ms, con botón por si el navegador lo frena. El intent-filter está en mobile/android/app/src/main/AndroidManifest.xml:51-56.'
       atr=@('GET /api/payments/return/?resultado=&ficha=&origen= : 302 | 200')
       ops=@('return_page(request)', '_pagina(titulo, cuerpo)', '_js_string(valor)') },

    @{ k='webhook'; n='ReceptorWebhook'; rol='boundary'; col=1; f=3.8
       nota='stripe_webhook en payments/views.py:110-157. csrf_exempt y sin JWT: se autentica con la firma Stripe-Signature. Lo llama la Pasarela de Pago, no el paciente. Atiende checkout.session.completed, checkout.session.async_payment_succeeded (PAID_EVENTS, :107) y checkout.session.expired (:124); todo lo demás responde 200 y se ignora.'
       atr=@('POST /api/payments/webhooks/stripe/ : 200 | 400 | 405')
       ops=@('stripe_webhook(request)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (usuario e inquilino desde el token), payments/permissions.py (CanCreatePayments: payments.payment.create, sembrado sólo al rol patient en payments/migrations/0003_seed_permissions.py:17-29) y tenancy/plans.py (require_feature :104, current_plan :80; PlanLimitExceeded es 403 plan_limit, :67-71).'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(code)', 'require_feature(organization, feature, que)', 'current_plan(organization)') },

    @{ k='gcobro'; n='GestorCobro'; rol='control'; col=2; f=1
       nota='payments/services.py (start_checkout :32), payments/pricing.py (quote :39, _mas_barato :34) y appointments/mixins.py (owns_appointment :24). Cobra lo mismo que informa el asistente: servicio de consulta asociado a la especialidad, el que la nombra, la consulta genérica y, si no hay, APPOINTMENT_DEFAULT_FEE (config/settings.py:292-293). El importe se fija al crear el intento y no se recalcula (payments/models.py:9-11).'
       atr=@()
       ops=@('start_checkout(appointment, user, request, return_to)', 'quote(appointment)', '_mas_barato(servicios)', 'owns_appointment(user, appointment)') },

    @{ k='gfichas'; n='GestorFichas'; rol='control'; col=2; f=2
       nota='appointments/booking.py (AppointmentViewSet: get_queryset :177, sólo las fichas del paciente y de sus dependientes) y appointments/serializers.py (get_fee :27, el precio con quote(), y get_payment_status :33, el último intento).'
       atr=@()
       ops=@('get_queryset()', 'retrieve(request, pk)', 'get_fee(obj)', 'get_payment_status(obj)') },

    @{ k='gprov'; n='GestorProveedor'; rol='control'; col=2; f=3
       nota='payments/providers.py. active_provider (:39) elige stripe si hay STRIPE_SECRET_KEY (config/settings.py:280, PAYMENTS_PROVIDER :288). StripeProvider arma la sesión de Checkout con la hora de la sucursal (_hora_local :56) y la metadata {payment_id, organization_id, appointment_id}, verifica la firma del webhook con STRIPE_WEBHOOK_SECRET (:140) y devuelve con Refund.create (:123).'
       atr=@()
       ops=@('active_provider()', 'provider_for(name)', 'return_url(request, appointment_id, return_to)', 'create_checkout(payment, request, return_to)', 'refund(payment)', 'parse_event(payload, signature)', '_hora_local(appointment)') },

    @{ k='gconf'; n='GestorConfirmacion'; rol='control'; col=2; f=4
       nota='payments/services.py (confirm_payment :74, refund_payment :129, _asentar :202) y la rama de stripe_webhook que fija el inquilino con la organización firmada, busca el pago y marca expired (payments/views.py:138-157). Es el único lugar donde una ficha pasa a confirmed por un pago; idempotente, y si la ficha ya no espera pago devuelve el dinero.'
       atr=@()
       ops=@('confirm_payment(payment, provider_payment_id, request)', 'refund_payment(payment, reason, request)', '_asentar(request, payment, evento)', 'tenant_context(organization_id)') },

    @{ k='gaviso'; n='GestorAviso'; rol='control'; col=2; f=5
       nota='appointments/attendance.py (send_confirmation_email :113, _destinatario :103, attendance_link :93) y appointments/receipts.py (issue_code :53). Corre en transaction.on_commit (payments/services.py:122), en su propio tenant_context, y nunca propaga un error (:148): un correo caído no deshace un pago.'
       atr=@()
       ops=@('send_confirmation_email(appointment_id, organization_id)', '_destinatario(appointment)', 'attendance_link(appointment)', 'issue_code(appointment)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
       nota='Tabla audit_log. Acción payment.movement (audit/actions.py:102) con evento checkout, pagado o devuelto. La encola record() y la escribe AuditTrailMiddleware después del COMMIT.'
       atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar(60)', 'entity : varchar(60)', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='servicio'; n='Servicio'; rol='entity'; col=3; f=1
       nota='Tabla services (catalog/models.py:280, US-32). El precio de lista que informa el asistente; price NULL es «a consultar».'
       atr=@('id : uuid', 'organization_id : uuid', 'specialty_id : uuid', 'name : varchar(120)', 'kind : varchar(20)', 'price : numeric(10,2)', 'currency : varchar(3)', 'is_active : boolean')
       ops=@('filter(kind=consultation, is_active, price__gt=0)') },

    @{ k='especialidad'; n='Especialidad'; rol='entity'; col=3; f=2
       nota='Tabla specialties, unida a practitioner_specialties para saber las especialidades del profesional de la ficha.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)')
       ops=@('practitioner.specialties.all()', 'values_list(name)') },

    @{ k='entpago'; n='Pago'; rol='entity'; col=3; f=3
       nota='Tabla payments (payments/models.py:68, migración 0001_initial). Una fila por intento de cobro. uq_payment_one_success: UNIQUE parcial (appointment_id) WHERE status = succeeded; uq_payment_id_org; ck_payment_amount (amount > 0); provider_session_id UNIQUE. RLS tenant_isolation y FK compuesta (appointment_id, organization_id) en 0002_rls_policies.py:67-69.'
       atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'created_by_id : uuid', 'amount : numeric(10,2)', 'currency : varchar(3)', 'provider : varchar(12)', 'status : varchar(12)', 'provider_session_id : varchar(255)', 'provider_payment_id : varchar(255)', 'checkout_url : text', 'paid_at : timestamptz', 'refunded_at : timestamptz', 'refund_reason : varchar(40)', 'created_at : timestamptz')
       ops=@('create(status=pending)', 'select_for_update()', 'save(update_fields)', 'filter(appointment_id, status=succeeded).exists()') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=4.4
       nota='Tabla appointments. Nace pending_payment con expires_at = ahora + APPOINTMENT_HOLD_MINUTES (appointments/booking.py:140); confirm_payment la pasa a confirmed y deja expires_at en NULL (payments/services.py:113).'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)', 'expires_at : timestamptz', 'updated_at : timestamptz')
       ops=@('filter(pk, organization)', 'select_for_update(of=self)', 'save(update_fields)') },

    @{ k='pasarela'; n='Pasarela de Pago'; rol='externo'; col=4; f=2 },

    @{ k='correo'; n='Servicio de Correo'; rol='externo'; col=4; f=5 }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';         col=0; f=2 },
      @{ k='fin403'; tipo='final';   col=0; f=4.5 },
      @{ k='val';    n='Validar ficha y plan';        col=1; f=1 },
      @{ k='cob';    n='Abrir cobro en la pasarela';  col=1; f=3 },
      @{ k='chk';    n='Pagar en el Checkout';        col=2; f=1 },
      @{ k='firma';  n='Verificar evento firmado';    col=2; f=3 },
      @{ k='error';  n='Informar error';              col=2; f=5.5 },
      @{ k='conf';   n='Confirmar ficha';             col=3; f=0.5 },
      @{ k='dev';    n='Devolver pago';               col=3; f=3.5 },
      @{ k='ok';     n='Transacción completada';      col=4; f=2 },
      @{ k='fin';    tipo='final';   col=4; f=4 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='val';    r='[token y payments.payment.create] {CanCreatePayments, payments/views.py:55}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='val';   a='cob';    r='[propia, pending_payment, sin vencer y plan con online_payment] / quote() {views.py:67, :73, services.py:40, :44, :50}' },
      @{ de='val';   a='error';  r='[inexistente, ajena, sin plan, no pendiente o vencida] {404 views.py:65, 403 :69, :73, 400 services.py:41, :45}' },
      @{ de='cob';   a='chk';    r='[sesión creada] / Session.create(expires_at + 31 min) {providers.py:87, :112}' },
      @{ de='cob';   a='error';  r='[StripeError] / ROLLBACK {502 views.py:88}' },
      @{ de='chk';   a='firma';  r='pagar() / POST /webhooks/stripe/ {checkout.session.completed}' },
      @{ de='chk';   a='ok';     r='[cancela o vence la sesión] / payments.status = expired {views.py:147}' },
      @{ de='firma'; a='conf';   r='[firma válida, ficha pending_payment y sin otro pago] / select_for_update() {services.py:84, :91, :103}' },
      @{ de='firma'; a='dev';    r='[ya pagada o la ficha ya no espera pago] {services.py:103-106}' },
      @{ de='firma'; a='ok';     r='[evento repetido: succeeded o refunded] {services.py:85}' },
      @{ de='firma'; a='error';  r='[firma inválida o sin STRIPE_WEBHOOK_SECRET] {400 views.py:119}' },
      @{ de='conf';  a='ok';     r='/ status = confirmed, on_commit(send_confirmation_email) {services.py:113, :122}' },
      @{ de='dev';   a='ok';     r='/ Refund.create(), status = refunded {providers.py:123, services.py:134}' },
      @{ de='error'; a='val';    r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  # Escenario normal: se reserva, se abre el cobro y se paga dentro del plazo
  # de 15 min; el webhook confirma la ficha y la app lo ve en su sondeo.
  tiempo = @{
    escenario = 'reservar, abrir el cobro y pagar dentro del plazo de 15 minutos'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 15 min = APPOINTMENT_HOLD_MINUTES (config/settings.py:260), que fija expires_at al reservar (appointments/booking.py:140); start_checkout sólo abre el cobro si la ficha sigue pending_payment y dentro del plazo (payments/services.py:40, :44). 31 min = expires_at de la sesión de Checkout (payments/providers.py:112; Stripe no acepta menos de 30). El paciente paga dentro del plazo; Stripe avisa por el webhook firmado y confirm_payment pasa la ficha de pending_payment a confirmed y deja expires_at en NULL (payments/services.py:113). En el webhook, Autenticando es verificar la firma de Stripe, no un JWT. 3 s y 2 min = pollInterval y pollTimeout del móvil (appointment_detail_screen.dart:40-41): la app sondea la ficha cada 3 s y, si la espera se agota mientras el paciente está en el navegador, vuelve a empezar al regresar a la app (:96-100). En la web, 3 s × 20 intentos (MisFichas.tsx:51-52).'
    lineas = @(
      @{ n='Plazo de reserva'
         estados=@('Corriendo', 'Cerrado')
         marcas=@( @{ t=0;  e='Corriendo'; ev='expires_at' },
                   @{ t=62; e='Cerrado';   ev='expires_at = NULL'; r='< 15 min' } ) },
      @{ n='Sesión de Checkout'
         estados=@('Sin sesión', 'Abierta', 'Pagada')
         marcas=@( @{ t=0;  e='Sin sesión' },
                   @{ t=14; e='Abierta'; ev='Session.create()' },
                   @{ t=40; e='Pagada';  ev='completed'; r='< 31 min' } ) },
      @{ n='Transacción del webhook'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=42; e='Autenticando'; ev='parse_event()' },
                   @{ t=49; e='Validando';    ev='FOR UPDATE' },
                   @{ t=56; e='Escribiendo';  ev='confirmed' },
                   @{ t=62; e='Confirmada';   ev='COMMIT' },
                   @{ t=69; e='Inactiva';     ev='200' } ) },
      @{ n='Ficha'
         estados=@('pending_payment', 'confirmed')
         marcas=@( @{ t=0;  e='pending_payment'; ev='reserva (CU18)' },
                   @{ t=62; e='confirmed'; ev='confirm_payment()' } ) },
      @{ n='App móvil'
         estados=@('Inactiva', 'Esperando', 'Mostrando')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=14; e='Esperando'; ev='launchUrl()' },
                   @{ t=66; e='Mostrando'; ev='confirmed'; r='3 s' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'pagar desde la app y confirmar por el webhook'
    2 = 'pagar desde la web'
    3 = 'excepciones'
  }

  # Nunca mas de DOS mensajes en el mismo sentido por par: por eso el cobro
  # (GestorCobro) y la confirmacion (GestorConfirmacion) son dos gestores, y
  # la lectura de la ficha que se sondea vive en GestorFichas.
  mensajes = @(
    @{ g=1; d='paciente';  a='pantalla';     m='pagar(ficha)' },
    @{ g=1; d='pantalla';  a='gcobro';       m='iniciarPago(id, return_to = app)' },
    @{ g=1; d='gcobro';    a='auth';         m='autorizar(payments.payment.create, online_payment)' },
    @{ g=1; d='gcobro';    a='ficha';        m='validarFicha(pending_payment, expires_at)' },
    @{ g=1; d='gcobro';    a='servicio';     m='cotizar(consultas activas)' },
    @{ g=1; d='gcobro';    a='especialidad'; m='especialidadesDelProfesional(practitioner)' },
    @{ g=1; d='gcobro';    a='entpago';      m='crearIntento(amount, currency, provider)' },
    @{ g=1; d='gcobro';    a='gprov';        m='crearCheckout(pago, return_to)' },
    @{ g=1; d='gprov';     a='pasarela';     m='crearSesion(line_items, metadata, 31 min)' },
    @{ g=1; d='gcobro';    a='entpago';      m='guardarSesion(provider_session_id, checkout_url)' },
    @{ g=1; d='gcobro';    a='bitacora';     m='registrar(PAYMENT_MOVEMENT, checkout)' },
    @{ g=1; d='pantalla';  a='pasarela';     m='abrirCheckout(checkout_url)' },
    @{ g=1; d='paciente';  a='pasarela';     m='pagarConTarjeta()' },
    @{ g=1; d='pasarela';  a='webhook';      m='checkout.session.completed(firma)' },
    @{ g=1; d='webhook';   a='gprov';        m='verificarFirma(payload, Stripe-Signature)' },
    @{ g=1; d='webhook';   a='gconf';        m='confirmarPago(pago, payment_intent)' },
    @{ g=1; d='gconf';     a='entpago';      m='marcarPagado(succeeded, paid_at)' },
    @{ g=1; d='gconf';     a='ficha';        m='confirmarFicha(confirmed, expires_at = NULL)' },
    @{ g=1; d='gconf';     a='gaviso';       m='avisarTrasCommit(ficha)' },
    @{ g=1; d='gaviso';    a='ficha';        m='leerFicha(id)' },
    @{ g=1; d='gaviso';    a='correo';       m='enviarComprobante(código MC1, enlace de asistencia)' },
    @{ g=1; d='gconf';     a='bitacora';     m='registrar(PAYMENT_MOVEMENT, pagado)' },
    @{ g=1; d='pasarela';  a='regreso';      m='volver(success_url, origen = app)' },
    @{ g=1; d='regreso';   a='pantalla';     m='abrirApp(centromedico://app/appointments/{id})' },
    @{ g=1; d='pantalla';  a='gfichas';      m='sondearFicha(cada 3 s, hasta 2 min)' },
    @{ g=1; d='gfichas';   a='ficha';        m='leerFicha(id)' },
    @{ g=1; d='gfichas';   a='entpago';      m='ultimoIntento(ficha)' },

    @{ g=2; d='pantalla';  a='gcobro';       m='iniciarPago(id, return_to = web)' },
    @{ g=2; d='regreso';   a='pantalla';     m='redirigir(/mis-fichas?ficha&pago=pagado)' },
    @{ g=2; d='pantalla';  a='gfichas';      m='sondearFichas(cada 3 s, 20 veces)' },

    @{ g=3; d='gcobro';    a='pantalla';     m='fichaNoPagable(code) -> 400 | 403 | 404' },
    @{ g=3; d='gcobro';    a='pantalla';     m='proveedorDePago() -> 502' },
    @{ g=3; d='webhook';   a='pasarela';     m='firmaInvalida() -> 400' },
    @{ g=3; d='pasarela';  a='webhook';      m='checkout.session.expired()' },
    @{ g=3; d='webhook';   a='gconf';        m='marcarVencido(pago)' },
    @{ g=3; d='gconf';     a='entpago';      m='marcar(expired | refunded)' },
    @{ g=3; d='gconf';     a='gprov';        m='devolver(pago, pago_duplicado | ficha_no_disponible)' },
    @{ g=3; d='gprov';     a='pasarela';     m='crearDevolucion(payment_intent)' },
    @{ g=3; d='gconf';     a='bitacora';     m='registrar(PAYMENT_MOVEMENT, devuelto)' },
    @{ g=3; d='pasarela';  a='regreso';      m='volver(cancel_url)' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Abrir el cobro desde la app' },
    @{ t='msg'; o='paciente';  d='pantalla';     n='1.1: pagar(ficha)  {diálogo «Ir a pagar», appointment_detail_screen.dart:159}' },
    @{ t='msg'; o='pantalla';  d='gcobro';       n='1.2: POST /api/payments/appointments/{id}/checkout/(return_to = app)' },
    @{ t='msg'; o='gcobro';    d='auth';         n='1.3: authenticate(request)  {IsAuthenticated, CanCreatePayments}' },
    @{ t='msg'; o='auth';      d='gcobro';       n='1.3.1: has_permission(payments.payment.create) -> True'; ret=$true },
    @{ t='msg'; o='gcobro';    d='ficha';        n='1.4: SELECT * FROM appointments JOIN patients, practitioners, branches WHERE id = :pk AND organization_id = :org()' },
    @{ t='msg'; o='ficha';     d='gcobro';       n='1.4.1: Ficha(status, expires_at, patient_id)'; ret=$true },
    @{ t='msg'; o='gcobro';    d='gcobro';       n='1.5: owns_appointment(user, ficha)  {suya o de su dependiente}' },
    @{ t='msg'; o='gcobro';    d='auth';         n='1.6: require_feature(organization, online_payment)  {suscripción vigente y su plan}' },
    @{ t='msg'; o='gcobro';    d='gcobro';       n='1.7: start_checkout(ficha, user, return_to)  {status y expires_at; un return_to desconocido cae en app, views.py:79}' },
    @{ t='msg'; o='gcobro';    d='servicio';     n='1.8: SELECT * FROM services WHERE organization_id = :org AND kind = ''consultation'' AND is_active AND price > 0()' },
    @{ t='msg'; o='servicio';  d='gcobro';       n='1.8.1: list(Service)'; ret=$true },
    @{ t='msg'; o='gcobro';    d='especialidad'; n='1.9: SELECT s.* FROM specialties s JOIN practitioner_specialties ps ON ps.specialty_id = s.id WHERE ps.practitioner_id = :practitioner()' },
    @{ t='msg'; o='especialidad'; d='gcobro';    n='1.9.1: list(Specialty)'; ret=$true },
    @{ t='loop'; g='por cada servicio de consulta: asociado, que nombra la especialidad o genérico' },
    @{ t='msg'; o='gcobro';    d='gcobro';       n='1.10: _mas_barato(candidatos)  {pricing.py:34, :53-67}' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='hay un servicio candidato con precio' },
    @{ t='msg'; o='gcobro';    d='gcobro';       n='1.11a: quote(ficha) -> (service.price, service.currency)' },
    @{ t='op'; g='ninguno' },
    @{ t='msg'; o='gcobro';    d='gcobro';       n='1.11b: quote(ficha) -> (APPOINTMENT_DEFAULT_FEE, APPOINTMENT_FEE_CURRENCY)  {100.00 BOB, pricing.py:71, settings.py:292}' },
    @{ t='fin' },
    @{ t='msg'; o='gcobro';    d='gprov';        n='1.12: active_provider()  {stripe si hay STRIPE_SECRET_KEY}' },
    @{ t='msg'; o='gcobro';    d='entpago';      n='1.13: INSERT INTO payments (organization_id, appointment_id, created_by_id, amount, currency, provider, status = ''pending'')()' },
    @{ t='msg'; o='gcobro';    d='gprov';        n='1.14: create_checkout(pago, request, return_to)' },
    @{ t='msg'; o='gprov';     d='pasarela';     n='1.15: stripe.checkout.Session.create(line_items, metadata, success_url, cancel_url, expires_at = now + 31 min)' },
    @{ t='alt' },
    @{ t='op'; g='Stripe crea la sesión' },
    @{ t='msg'; o='pasarela';  d='gprov';        n='1.16a: Session(id, url)'; ret=$true },
    @{ t='msg'; o='gcobro';    d='entpago';      n='1.17a: UPDATE payments SET provider_session_id = :cs, checkout_url = :url WHERE id = :id()' },
    @{ t='msg'; o='gcobro';    d='bitacora';     n='1.18a: INSERT INTO audit_log (action = payment.movement, detail.evento = checkout)()  {después del COMMIT}' },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='1.18a.1: 201(payment_id, provider, checkout_url, amount, currency, status)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='pasarela';     n='1.19a: launchUrl(checkout_url, externalApplication)' },
    @{ t='msg'; o='pantalla';  d='pantalla';     n='1.20a: _empezarAEsperar()  {Timer.periodic 3 s, hasta 2 min}' },
    @{ t='msg'; o='paciente';  d='pasarela';     n='1.21a: pagarConTarjeta(4242 4242 4242 4242)  {modo prueba}' },
    @{ t='op'; g='StripeError' },
    @{ t='msg'; o='gprov';     d='gcobro';       n='1.16b: ProviderError(user_message)'; ret=$true },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='1.17b: proveedorDePago() -> 502  {ROLLBACK del savepoint: el INSERT no queda}'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 2 Recibir el webhook de Stripe' },
    @{ t='msg'; o='pasarela';  d='webhook';      n='2.1: POST /api/payments/webhooks/stripe/(evento, Stripe-Signature)  {sin JWT}' },
    @{ t='msg'; o='webhook';   d='gprov';        n='2.2: parse_event(payload, signature)  {STRIPE_WEBHOOK_SECRET}' },
    @{ t='alt' },
    @{ t='op'; g='firma válida, PAID_EVENTS y payment_status = paid' },
    @{ t='msg'; o='gprov';     d='webhook';      n='2.3a: Event(type, data.object.metadata)'; ret=$true },
    @{ t='msg'; o='webhook';   d='gconf';        n='2.4a: tenant_context(metadata.organization_id)  {la organización viaja firmada}' },
    @{ t='msg'; o='gconf';     d='entpago';      n='2.5a: SELECT * FROM payments WHERE id = :payment_id AND provider = ''stripe'' AND provider_session_id = :session_id()' },
    @{ t='msg'; o='entpago';   d='gconf';        n='2.5a.1: Pago(status)'; ret=$true },
    @{ t='msg'; o='gconf';     d='gconf';        n='2.6a: confirm_payment(pago, provider_payment_id = payment_intent)  {FLUJO 3}' },
    @{ t='msg'; o='webhook';   d='pasarela';     n='2.7a: 200()'; ret=$true },
    @{ t='op'; g='checkout.session.expired y el pago sigue pending' },
    @{ t='msg'; o='webhook';   d='gconf';        n='2.3b: marcarVencido(pago)' },
    @{ t='msg'; o='gconf';     d='entpago';      n='2.4b: UPDATE payments SET status = ''expired'' WHERE id = :id()  {views.py:147}' },
    @{ t='msg'; o='webhook';   d='pasarela';     n='2.5b: 200()'; ret=$true },
    @{ t='op'; g='otro tipo, sin metadata o pago inexistente' },
    @{ t='msg'; o='webhook';   d='pasarela';     n='2.3c: 200()  {se ignora; si no, Stripe reintenta durante tres días}'; ret=$true },
    @{ t='op'; g='firma inválida o sin STRIPE_WEBHOOK_SECRET' },
    @{ t='msg'; o='gprov';     d='webhook';      n='2.3d: ProviderError(Firma de Stripe inválida)'; ret=$true },
    @{ t='msg'; o='webhook';   d='pasarela';     n='2.4d: firmaInvalida() -> 400'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 3 Confirmar el pago (idempotente)' },
    @{ t='msg'; o='gconf';     d='entpago';      n='3.1: SELECT * FROM payments WHERE id = :id FOR UPDATE()  {transaction.atomic(), services.py:83}' },
    @{ t='msg'; o='entpago';   d='gconf';        n='3.1.1: Pago(status)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='status succeeded o refunded: el evento llegó repetido' },
    @{ t='msg'; o='gconf';     d='gconf';        n='3.2a: return pago  {no cambia nada}' },
    @{ t='op'; g='status pending, expired o failed' },
    @{ t='msg'; o='gconf';     d='ficha';        n='3.2b: SELECT * FROM appointments WHERE id = :appointment_id FOR UPDATE OF appointments()' },
    @{ t='msg'; o='ficha';     d='gconf';        n='3.2b.1: Ficha(status, expires_at)'; ret=$true },
    @{ t='msg'; o='gconf';     d='entpago';      n='3.3b: SELECT EXISTS (SELECT 1 FROM payments WHERE appointment_id = :ficha AND status = ''succeeded'')()' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='ficha pending_payment y sin otro pago succeeded' },
    @{ t='msg'; o='gconf';     d='entpago';      n='3.4a: UPDATE payments SET status = ''succeeded'', provider_payment_id = :pi, paid_at = now() WHERE id = :id()' },
    @{ t='msg'; o='gconf';     d='ficha';        n='3.5a: UPDATE appointments SET status = ''confirmed'', expires_at = NULL WHERE id = :ficha()' },
    @{ t='msg'; o='gconf';     d='gaviso';       n='3.6a: transaction.on_commit(send_confirmation_email(ficha, organización))' },
    @{ t='msg'; o='gaviso';    d='ficha';        n='3.7a: SELECT * FROM appointments JOIN organizations, patients, users, practitioners, branches WHERE id = :ficha()  {tras el COMMIT}' },
    @{ t='msg'; o='gaviso';    d='gaviso';       n='3.8a: _destinatario(ficha), issue_code(ficha), attendance_link(ficha)  {sin correo del paciente ni del titular, no envía}' },
    @{ t='msg'; o='gaviso';    d='correo';       n='3.9a: send_mail(Tu ficha está confirmada, código MC1, enlace de asistencia)  {Brevo si hay BREVO_API_KEY}' },
    @{ t='msg'; o='gconf';     d='bitacora';     n='3.10a: INSERT INTO audit_log (action = payment.movement, detail.evento = pagado)()  {AuditTrailMiddleware}' },
    @{ t='op'; g='ya hay un pago succeeded o la ficha ya no está pending_payment' },
    @{ t='msg'; o='gconf';     d='entpago';      n='3.4b: UPDATE payments SET provider_payment_id = :pi, paid_at = now() WHERE id = :id()' },
    @{ t='msg'; o='gconf';     d='gprov';        n='3.5b: refund_payment(pago, reason = pago_duplicado | ficha_no_disponible)' },
    @{ t='msg'; o='gprov';     d='pasarela';     n='3.6b: stripe.Refund.create(payment_intent, metadata)  {providers.py:123}' },
    @{ t='msg'; o='gconf';     d='entpago';      n='3.7b: UPDATE payments SET status = ''refunded'', refunded_at = now(), refund_reason = :motivo WHERE id = :id()' },
    @{ t='msg'; o='gconf';     d='bitacora';     n='3.8b: INSERT INTO audit_log (action = payment.movement, detail.evento = devuelto)()' },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 4 Volver a la app y esperar la confirmación' },
    @{ t='msg'; o='pasarela';  d='regreso';      n='4.1: GET /api/payments/return/?ficha=:id&origen=app&resultado=pagado()  {success_url; con cancel_url, resultado=cancelado}' },
    @{ t='alt' },
    @{ t='op'; g='origen = app y ficha es un UUID' },
    @{ t='msg'; o='regreso';   d='pantalla';     n='4.2a: abrirApp(centromedico://app/appointments/{id})  {setTimeout 600 ms o botón «Volver a la aplicación»}' },
    @{ t='op'; g='origen = web' },
    @{ t='msg'; o='regreso';   d='pantalla';     n='4.2b: 302(FRONTEND_BASE_URL/mis-fichas?ficha=:id&pago=pagado)'; ret=$true },
    @{ t='op'; g='sin origen o sin ficha' },
    @{ t='msg'; o='regreso';   d='paciente';     n='4.2c: 200(Pago recibido)  {página sin enlace}'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='pantalla';  d='pantalla';     n='4.3: didChangeAppLifecycleState(resumed) -> _empezarAEsperar()' },
    @{ t='loop'; g='cada 3 s, hasta 2 min (web: cada 3 s, 20 intentos)' },
    @{ t='msg'; o='pantalla';  d='gfichas';      n='4.4: GET /api/appointments/appointments/{id}/()  {la web pide la lista entera}' },
    @{ t='msg'; o='gfichas';   d='ficha';        n='4.5: SELECT * FROM appointments WHERE id = :id AND organization_id = :org AND (patient_id = :pac OR patient_id IN (SELECT id FROM patients WHERE guardian_id = :pac))()' },
    @{ t='msg'; o='gfichas';   d='entpago';      n='4.6: SELECT status FROM payments WHERE appointment_id = :id ORDER BY created_at DESC LIMIT 1()  {payment_status}' },
    @{ t='msg'; o='gfichas';   d='pantalla';     n='4.6.1: 200(Ficha status, fee, payment_status)'; ret=$true },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='status != pending_payment' },
    @{ t='msg'; o='pantalla';  d='paciente';     n='4.7a: mostrarAviso(¡Pago recibido! Tu ficha está confirmada.)'; ret=$true },
    @{ t='op'; g='sigue pending_payment al agotarse la espera' },
    @{ t='msg'; o='pantalla';  d='paciente';     n='4.7b: mostrarAviso(Todavía no llegó la confirmación del pago.)'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 5 Excepciones al abrir el cobro' },
    @{ t='alt' },
    @{ t='op'; g='appointment is None' },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='5.1a: fichaNoExiste() -> 404'; ret=$true },
    @{ t='op'; g='es paciente y not owns_appointment' },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='5.1b: fichaAjena() -> 403'; ret=$true },
    @{ t='op'; g='sin suscripción vigente o el plan no incluye online_payment' },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='5.1c: PlanLimitExceeded() -> 403 plan_limit'; ret=$true },
    @{ t='op'; g='status != pending_payment' },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='5.1d: fichaNoPendiente() -> 400 ficha_no_pendiente'; ret=$true },
    @{ t='op'; g='expires_at <= now' },
    @{ t='msg'; o='gcobro';    d='pantalla';     n='5.1e: fichaVencida() -> 400 ficha_vencida'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='pantalla';  d='paciente';     n='5.2: mostrarAviso(error.message)  {y recarga la ficha, appointment_detail_screen.dart:200-203}'; ret=$true }
  )
}

$NAVEGACION_SPRINT2['CU19'] = @{
  actor  = 'Paciente'
  nota   = 'CU19 · US-18. Navegación MÓVIL: docs/sprints/sprint-2/reparto.md:371 marca US-18 como MÓVIL y el backend toma return_to = app por omisión (payments/views.py:78-80). Rutas de mobile/lib/core/router/app_router.dart (/home :158, /appointments :371, /appointments/:id :379; la entrada «Mis fichas» del inicio, :714-716); guardas: redirect (:116) y SoloPacientes (mobile/lib/core/session/patient_gate.dart:16). DialogoPagarFicha es el AlertDialog «Pagar la ficha» de appointment_detail_screen.dart:159, y su único campo es return_to = app (payments_api.dart:55). El Checkout de Stripe es una página externa (launchUrl en el navegador): su submit es el webhook firmado. return_page vuelve a la app por el deep link centromedico://app/appointments/{id} (AndroidManifest.xml:51-56), que go_router abre en AppointmentDetailScreen; esa vuelta no se dibuja como flecha (sección 7.5). Par web: Panel.tsx -> MisFichas.tsx (/mis-fichas, [sesión + appointments.appointment.read], BarraPlataforma.tsx:250-256) -> botón Pagar (MisFichas.tsx:309-316, return_to = web) -> Checkout -> return_page, que redirige con 302 a /mis-fichas?ficha=&pago=pagado (views.py:207-211). Clientes HTTP: payments_api.dart, appointments_api.dart y frontend/src/api/fichas.ts.'
  menu   = @{ n='_HomeScreen'; ruta='/home' }
  publicas = @()
  controladores = @{
    booking  = @{ n='appointments/booking.py'; ops=@('AppointmentViewSet.list(request)', 'AppointmentViewSet.retrieve(request, pk)', 'AppointmentViewSet.get_queryset()') }
    payments = @{ n='payments/views.py'; ops=@('CheckoutView.post(request, pk)', 'stripe_webhook(request)', 'return_page(request)') }
  }
  areas = @(
    @{ guarda='[sesión + SoloPacientes]'
       vista=@{ n='MyAppointmentsScreen'; ruta='/appointments'; atr=@('practitioner_name', 'starts_at', 'status') }; vistaCtrl='booking'
       forms=@() },
    @{ guarda='[appointments.appointment.read]'; desde='MyAppointmentsScreen'
       vista=@{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; atr=@('status', 'fee', 'expires_at', 'payment_status') }; vistaCtrl='booking'
       forms=@(
         @{ n='DialogoPagarFicha'; atr=@('return_to'); ctrl='payments' }
       ) },
    @{ guarda='[checkout_url]'; desde='AppointmentDetailScreen'
       vista=@{ n='Checkout de Stripe'; ruta='checkout_url'; atr=@('line_items', 'success_url', 'cancel_url', 'expires_at') }; vistaCtrl='payments'
       forms=@(
         @{ n='return_page'; tipo='navigationClass'; ruta='/api/payments/return/?resultado=&ficha=&origen=app'; atr=@('centromedico://app/appointments/{id}') }
       ) }
  )
}

$CASOS_SPRINT2['CU20'] = @{
  cu     = 'CU20'
  nombre = 'Generación de Comprobante Digital'
  us     = 'US-19'
  nota   = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Actor: el Paciente (1.3). La web y el móvil llaman al mismo GET /api/appointments/appointments/<id>/receipt/ (ReceiptView, appointments/receipts.py:104). El comprobante NO tiene tabla: es un código firmado, MC1.<signing.dumps({a, o})> con HMAC sobre la SECRET_KEY y sal appointments.receipt (receipts.py:40-59); por eso quien lo emite es un controlador (FirmadorComprobante) y no una entidad. Determinístico: la misma ficha da siempre el mismo código, y la firma no vence; lo que se consume es la ficha (attended en el check-in, CU23, que lo verifica con read_code). Sólo lee: ni atomic, ni save, ni bitácora. Sólo hay comprobante de una ficha confirmed o attended (409 ficha_no_confirmada, receipts.py:126-132); un paciente sólo ve los suyos y los de sus dependientes (owns_appointment, mixins.py:24), y si no, 404. El móvil guarda la respuesta entera en flutter_secure_storage (receipt_store.dart) para mostrarla sin señal: no es una tabla, va en la nota de GestorAlmacenLocal.'

  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2 },

    @{ k='fichas'; n='PantallaMisFichas'; rol='boundary'; col=1; f=0.5
       nota='La puerta del caso. Web: el botón «Ver comprobante» de frontend/src/paginas/MisFichas.tsx:318-324, sólo si la ficha está confirmed o attended (:262). Móvil: mobile/lib/features/appointments/my_appointments_screen.dart (el ícono «Mis comprobantes», :59-63, y «Ver comprobantes guardados» sin red, :94-98) y appointment_detail_screen.dart («Ver comprobante», :449-456, sólo si isConfirmed). Backend: AppointmentViewSet en appointments/booking.py:150 (lo carga CU18).'
       atr=@('GET /api/appointments/appointments/ : 200 | 401 | 403', 'GET /api/appointments/appointments/<id>/ : 200 | 401 | 403 | 404')
       ops=@('misFichas(contexto, senal)', 'verFicha(client, id)', 'setComprobanteId(id)') },

    @{ k='pantalla'; n='PantallaComprobante'; rol='boundary'; col=1; f=2
       nota='Web: frontend/src/componentes/ModalComprobante.tsx (QRCodeSVG :90, copiar el código :47-55) y comprobante en frontend/src/api/fichas.ts:148. Móvil: ReceiptScreen en mobile/lib/features/receipts/receipt_screen.dart:22 (QrImageView :180) y pedirComprobante en receipts_api.dart:63. Primero muestra la copia guardada y después pide al servidor (_cargar, :62-105). Backend: ReceiptView.get en appointments/receipts.py:113.'
       atr=@('GET /api/appointments/appointments/<id>/receipt/ : 200 | 401 | 403 | 404 | 409')
       ops=@('comprobante(id, contexto)', 'copiar()', 'pedirComprobante(client, appointmentId)', '_cargar()', 'get(request, pk)') },

    @{ k='guardados'; n='PantallaComprobantesGuardados'; rol='boundary'; col=1; f=3.6
       nota='Sólo móvil: SavedReceiptsScreen en mobile/lib/features/receipts/receipt_screen.dart:226, ruta /receipts (app_router.dart:414-424). No llama al backend: lista lo guardado en el teléfono y abre ReceiptScreen con context.push (app_router.dart:420-421). Sin par web.'
       atr=@()
       ops=@('build(context)', 'onOpen(context, receipt)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token), CanReadAppointments en appointments/permissions.py:26 (appointments.appointment.read, sembrado en accounts/migrations/0006_seed_permissions_sprint_2_appointments.py:30-43 para org_admin, receptionist y patient) y User.has_permission en accounts/models.py.'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)') },

    @{ k='gestor'; n='GestorComprobante'; rol='control'; col=2; f=1.5
       nota='appointments/receipts.py (ReceiptView.get :113, receipt_payload :87) y owns_appointment en appointments/mixins.py:24. Lee la ficha con select_related de organización, paciente, profesional y sucursal en una sola consulta (:114-119). El paciente sólo ve las suyas o las de sus dependientes; el personal con el permiso ve las de su organización.'
       atr=@()
       ops=@('get(request, pk)', 'owns_appointment(user, appointment)', 'receipt_payload(appointment)') },

    @{ k='firmador'; n='FirmadorComprobante'; rol='control'; col=2; f=2.8
       nota='issue_code en appointments/receipts.py:53, sobre django.core.signing: HMAC-SHA256 con la SECRET_KEY, sal appointments.receipt y prefijo de versión MC1. (:40-41). Es un controlador porque el comprobante no se guarda: se recalcula en cada pedido y sale igual. Su inverso, read_code (:62), lo usa el check-in (CU23).'
       atr=@()
       ops=@('issue_code(appointment)', 'dumps(obj, salt, compress)') },

    @{ k='almacen'; n='GestorAlmacenLocal'; rol='control'; col=2; f=4
       nota='Sólo móvil: ReceiptStore en mobile/lib/features/receipts/receipt_store.dart:18. Guarda el JSON entero de la respuesta en flutter_secure_storage con la clave receipt.<appointment_id> (:24-31), cifrado por el sistema operativo como los tokens. No es una tabla ni una entidad del modelo: no está en la base y nadie más la lee, así que no se dibuja como entidad (sería inventar una tabla). Si el servidor responde 4xx, ReceiptScreen borra la copia (receipt_screen.dart:84-85); sin red, la conserva.'
       atr=@()
       ops=@('save(receipt)', 'read(appointmentId)', 'remove(appointmentId)', 'all()') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=0
       nota='Tabla appointments. Sólo con status confirmed o attended hay comprobante. updated_at se publica como issued_at (receipts.py:91).'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar(16)', 'updated_at : timestamptz')
       ops=@('filter(pk, organization).select_related(organization, patient, practitioner, branch)') },

    @{ k='entpaciente'; n='Paciente'; rol='entity'; col=3; f=1.3
       nota='Tabla patients (JOIN). user_id dice si la ficha es del propio usuario; guardian_id, si es de un dependiente suyo (US-07).'
       atr=@('id : uuid', 'organization_id : uuid', 'user_id : uuid', 'guardian_id : uuid', 'document_number : varchar(20)', 'first_name : varchar(80)', 'last_name : varchar(80)')
       ops=@('full_name()') },

    @{ k='profesional'; n='Profesional'; rol='entity'; col=3; f=2.4
       nota='Tabla practitioners (JOIN). Sólo se lee el nombre.'
       atr=@('id : uuid', 'organization_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)')
       ops=@('full_name()') },

    @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=3.3
       nota='Tabla branches (JOIN).'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)', 'address : varchar(200)')
       ops=@('values(name, address)') },

    @{ k='organizacion'; n='Organizacion'; rol='entity'; col=3; f=4.2
       nota='Tabla organizations (JOIN). Su id va firmado dentro del código: un comprobante de otro centro se rechaza en el check-in.'
       atr=@('id : uuid', 'name : varchar(120)')
       ops=@('values(name)') }
  )

  # Sólo lee: sin estado, tiempo ni secuencia (GUIA-DE-DIAGRAMAS.md, sección 1, regla 5).

  grupos = [ordered]@{
    1 = 'ver el comprobante con conexión'
    2 = 'abrir uno guardado, sin conexión'
    3 = 'excepciones'
  }

  # Ningún par lleva más de dos mensajes en el mismo sentido (sección 4.3).
  # Por eso guardar y borrar la copia son un solo paso, actualizarCopia: el
  # 200 la guarda y un 4xx la borra (receipt_screen.dart:73 y :85).
  mensajes = @(
    @{ g=1; d='paciente';  a='fichas';       m='verComprobante(ficha)' },
    @{ g=1; d='fichas';    a='pantalla';     m='abrir(fichaId)' },
    @{ g=1; d='pantalla';  a='almacen';      m='leerCopia(fichaId)' },
    @{ g=1; d='pantalla';  a='gestor';       m='pedirComprobante(fichaId)' },
    @{ g=1; d='gestor';    a='auth';         m='autorizar(token, appointments.appointment.read)' },
    @{ g=1; d='gestor';    a='ficha';        m='buscar(fichaId, organizacion)' },
    @{ g=1; d='gestor';    a='entpaciente';  m='titularYDocumento(patient_id)' },
    @{ g=1; d='gestor';    a='profesional';  m='nombre(practitioner_id)' },
    @{ g=1; d='gestor';    a='sucursal';     m='nombreYDireccion(branch_id)' },
    @{ g=1; d='gestor';    a='organizacion'; m='nombre(organization_id)' },
    @{ g=1; d='gestor';    a='gestor';       m='verificarDueno(usuario, ficha)' },
    @{ g=1; d='gestor';    a='gestor';       m='verificarEstado(confirmed | attended)' },
    @{ g=1; d='gestor';    a='firmador';     m='emitirCodigo(ficha)' },
    @{ g=1; d='firmador';  a='firmador';     m='firmar({a, o}, appointments.receipt)' },
    @{ g=1; d='gestor';    a='pantalla';     m='comprobante(code, datos)' },
    @{ g=1; d='pantalla';  a='almacen';      m='actualizarCopia(respuesta)' },
    @{ g=1; d='pantalla';  a='paciente';     m='mostrarQR(code, datos)' },
    @{ g=1; d='paciente';  a='pantalla';     m='copiarCodigo()' },

    @{ g=2; d='paciente';  a='fichas';       m='verGuardados()' },
    @{ g=2; d='fichas';    a='guardados';    m='abrir(/receipts)' },
    @{ g=2; d='guardados'; a='almacen';      m='listarGuardados()' },
    @{ g=2; d='guardados'; a='paciente';     m='mostrarLista(profesional, fecha, sucursal)' },
    @{ g=2; d='paciente';  a='guardados';    m='elegir(comprobante)' },
    @{ g=2; d='guardados'; a='pantalla';     m='abrir(fichaId)' },

    @{ g=3; d='auth';      a='pantalla';     m='sinPermiso(401 | 403)' },
    @{ g=3; d='gestor';    a='pantalla';     m='rechazo(404 | 409 ficha_no_confirmada)' },
    @{ g=3; d='pantalla';  a='paciente';     m='mostrarAviso(copia sin conexión | error)' }
  )
}

$NAVEGACION_SPRINT2['CU20'] = @{
  actor  = 'Paciente'
  nota   = 'CU20 · US-19. Navegación MÓVIL, que es donde el comprobante se usa: se muestra en recepción y se guarda para verlo sin señal. Rutas de mobile/lib/core/router/app_router.dart: la tarjeta «Mis fichas» de _HomeScreen (:711-717) abre /appointments (:370-376); cada ficha, /appointments/:id (:378-386), donde «Ver comprobante» aparece sólo si la ficha está confirmed (appointment_detail_screen.dart:449-456) y abre /appointments/:id/receipt (:399-408). /receipts (:414-424) se abre desde el ícono de Mis fichas o, sin red, desde «Ver comprobantes guardados» (my_appointments_screen.dart:61, :95), y cada comprobante guardado vuelve a abrir la misma ReceiptScreen con context.push (:420-421): esa flecha no se dibuja para no repetir la caja. Guardas: redirect exige sesión (:116-132) y cada ruta va envuelta en SoloPacientes (core/session/patient_gate.dart), que filtra en la interfaz; el permiso que decide es appointments.appointment.read en el backend. En la web no hay ruta propia: es el modal ModalComprobante, que abre el botón «Ver comprobante» de MisFichas.tsx (/mis-fichas, requiere appointments.appointment.read) sobre la misma página. Clientes HTTP: appointments_api.dart y receipts_api.dart; en la web, frontend/src/api/fichas.ts.'
  menu   = @{ n='_HomeScreen'; ruta='/home' }
  publicas = @()
  controladores = @{
    booking  = @{ n='appointments/booking.py'; ops=@('AppointmentViewSet.get_queryset()') }
    receipts = @{ n='appointments/receipts.py'; ops=@('ReceiptView.get(request, pk)', 'receipt_payload(appointment)', 'issue_code(appointment)') }
  }
  areas = @(
    @{ guarda='[sesión + SoloPacientes]'
       vista=@{ n='MyAppointmentsScreen'; ruta='/appointments'; atr=@('practitioner_name', 'branch_name', 'starts_at', 'status') }; vistaCtrl='booking'
       forms=@() },
    @{ guarda='[SoloPacientes]'; desde='MyAppointmentsScreen'
       vista=@{ n='AppointmentDetailScreen'; ruta='/appointments/:id'; atr=@('status', 'fee', 'payment_status', 'attendance_confirmed_at') }; vistaCtrl='booking'
       forms=@(
         @{ n='ReceiptScreen'; tipo='navigationClass'; ruta='/appointments/:id/receipt'; atr=@('code', 'patient_name', 'document_number', 'practitioner_name', 'branch_name', 'branch_address', 'starts_at', 'issued_at'); ctrl='receipts' }
       ) },
    @{ guarda='[SoloPacientes]'; desde='MyAppointmentsScreen'
       vista=@{ n='SavedReceiptsScreen'; ruta='/receipts'; atr=@('practitioner_name', 'starts_at', 'branch_name') }
       forms=@() }
  )
}

$CASOS_SPRINT2['CU21'] = @{
  cu = 'CU21'; nombre = 'Cancelación / Reprogramación de Ficha'; us = 'US-20'
  nota = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Web (MisFichas.tsx + ModalReprogramarFicha.tsx) y móvil (AppointmentDetailScreen cancela y abre RescheduleScreen en /appointments/:id/reschedule). La anticipación (cancellation_notice_hours, tenancy/models.py:99) no bloquea la cancelación: sólo decide refund_eligible (changes.py:66). Después, la vista llama refund_for_cancellation (changes.py:178-180): con refund_eligible y un pago succeeded devuelve el 100 % por la Pasarela de Pago; si el proveedor falla (ProviderError), la ficha queda cancelada, el pago sigue succeeded y se registra con logger.exception para devolverlo a mano (payments/services.py:162-167). Con el proveedor simulado (sin STRIPE_SECRET_KEY) no se llama a Stripe. Reprogramar es liberar y volver a tomar en un transaction.atomic() (changes.py:94-122): si la vieja estaba confirmed, la nueva nace confirmed y transfer_payment le muda el pago (fix aa1e4b1); si algo falla, todo revierte y el pago vuelve a la original. Reprogramar no deja asiento de ficha en la bitácora: sólo payment.movement «reprogramado» cuando había pago. Estado: flujo de la transacción; los estados de la ficha y del pago van en el diagrama de tiempo.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2.6 },

    @{ k='pantalla'; n='PantallaMisFichas'; rol='boundary'; col=1; f=1
       nota='Web: frontend/src/paginas/MisFichas.tsx (cancelar en :167, con window.confirm y el aviso de devolución) y frontend/src/api/fichas.ts (misFichas, cancelarFicha). Móvil: mobile/lib/features/appointments/my_appointments_screen.dart (MyAppointmentsScreen, /appointments) y appointment_detail_screen.dart (AppointmentDetailScreen, /appointments/:id; _cancelar en :233 con la política de devolución en un AlertDialog), con cancelarFicha de appointments_api.dart:202. Backend: AppointmentViewSet en appointments/booking.py (el listado) y CancelAppointmentView en appointments/changes.py.'
       atr=@('GET /api/appointments/appointments/ : 200 | 401 | 403', 'POST /api/appointments/appointments/{id}/cancel/ : 200 | 400 | 401 | 403 | 404')
       ops=@('misFichas(contexto, senal)', 'cancelarFicha(id, contexto)', 'cancelar(ficha)', '_cancelar()', 'list(request)', 'CancelAppointmentView.post(request, pk)') },

    @{ k='form'; n='FormularioReprogramacion'; rol='boundary'; col=1; f=4
       nota='Web: frontend/src/componentes/ModalReprogramarFicha.tsx, confirmarReprogramacion de MisFichas.tsx:194, frontend/src/api/fichas.ts y frontend/src/api/disponibilidad.ts. Móvil: mobile/lib/features/appointments/reschedule_screen.dart (RescheduleScreen, /appointments/:id/reschedule, app_router.dart:389-398), con verFicha y reprogramarFicha de appointments_api.dart:192, :209; al volver, el detalle hace pushReplacement a la ficha nueva (appointment_detail_screen.dart:225-231). Backend: RescheduleAppointmentView en appointments/changes.py y AvailabilityView en scheduling/availability.py.'
       atr=@('GET /api/appointments/appointments/{id}/ : 200 | 401 | 403 | 404', 'GET /api/scheduling/availability/ : 200 | 400 | 401 | 403', 'POST /api/appointments/appointments/{id}/reschedule/ : 200 | 400 | 401 | 403 | 404 | 409')
       ops=@('disponibilidadConsolidada(parametros, contexto, senal)', 'reprogramarFicha(id, datos, contexto)', 'confirmarReprogramacion(slot)', '_dias(datos)', '_reprogramar(ficha)', 'RescheduleAppointmentView.post(request, pk)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token) y appointments/permissions.py (CanCancelAppointments, CanRescheduleAppointments: appointments.appointment.cancel / .reschedule).'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)', 'has_permission(code)') },

    @{ k='gestor'; n='GestorCambiosFicha'; rol='control'; col=2; f=1.4
       nota='appointments/changes.py, appointments/mixins.py (owns_appointment) y appointments/serializers.py (RescheduleAppointmentSerializer). Decide si corresponde devolución y delega el dinero en payments/services.py; reprogramar es liberar y volver a tomar en un solo transaction.atomic().'
       atr=@()
       ops=@('_get_appointment_or_404(request, pk)', '_puede_operar(user, appointment)', 'owns_appointment(user, appointment)', '_assert_cancellable(appointment, now)', '_notice(appointment, now)', 'cancel_appointment(appointment, now)', 'reschedule_appointment(appointment, branch_id, schedule_id, starts_at, now, request)') },

    @{ k='gdev'; n='GestorDevolucion'; rol='control'; col=2; f=2.8
       nota='payments/services.py (refund_for_cancellation, refund_payment, _asentar) y payments/providers.py (provider_for, StripeProvider.refund, SimulatedProvider.refund). Política del PO en US-18: a tiempo se devuelve el 100 %; fuera de plazo, nada. refund_payment también corta si el pago ya está refunded (services.py:131).'
       atr=@()
       ops=@('refund_for_cancellation(appointment, request)', 'refund_payment(payment, reason, request)', 'provider_for(name)', 'refund(payment)', '_asentar(request, payment, evento, extra)') },

    @{ k='reserva'; n='GestorReserva'; rol='control'; col=2; f=4.2
       nota='appointments/booking.py (la reserva de US-17, que reprogramar reutiliza, y el listado/detalle de AppointmentViewSet) y scheduling/availability.py (los espacios libres de US-15). Cancelar libera el turno porque _booked_slots sólo cuenta ACTIVE_STATUSES.'
       atr=@()
       ops=@('get_queryset()', 'consolidated_availability(practitioner_id, date_from, date_to, branch_id)', '_booked_slots(practitioner_id, date_from, date_to)', 'book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at, booked_by)', '_validate_slot_is_real(schedule, starts_at)') },

    @{ k='gtras'; n='GestorTraspasoPago'; rol='control'; col=2; f=5.6
       nota='transfer_payment y _asentar de payments/services.py:170-211 (fix aa1e4b1). Se llama dentro del atomic de la reprogramación: bloquea el pago con select_for_update y, si algo falla después, el pago vuelve a la ficha original. Los intentos pending se quedan en la vieja.'
       atr=@()
       ops=@('transfer_payment(origen, destino, request)', '_asentar(request, payment, evento, extra)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0
       nota='Tabla audit_log. La escribe record() de audit/services.py: appointment.cancel al cancelar (changes.py:182) y payment.movement al devolver o mudar el pago (services.py:202-211).'
       atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='organizacion'; n='Organizacion'; rol='entity'; col=3; f=1.1
       nota='Tabla organizations. cancellation_notice_hours es la política de anticipación de cada centro médico, 24 por omisión.'
       atr=@('id : uuid', 'name : varchar(120)', 'timezone : varchar(40)', 'cancellation_notice_hours : integer')
       ops=@('leer(cancellation_notice_hours)') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=2.3
       nota='Tabla appointments. uq_appointment_active_slot: un solo turno activo (pending_payment o confirmed) por (schedule_id, starts_at); al cancelar o reprogramar, el índice libera el turno en el acto.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'schedule_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)', 'expires_at : timestamptz', 'cancelled_at : timestamptz', 'cancellation_reason : varchar(20)', 'refund_eligible : boolean', 'rescheduled_from_id : uuid')
       ops=@('filter(pk, organization)', 'save(update_fields)', 'create(...)') },

    @{ k='pago'; n='Pago'; rol='entity'; col=3; f=3.7
       nota='Tabla payments (US-18, payments/models.py:68). Un intento de cobro por fila; uq_payment_one_success: un solo succeeded por ficha, por eso el traspaso no choca (la ficha nueva no tiene pagos).'
       atr=@('id : uuid', 'organization_id : uuid', 'appointment_id : uuid', 'created_by_id : uuid', 'amount : numeric(10,2)', 'currency : varchar(3)', 'provider : varchar(12)', 'status : varchar(12)', 'provider_payment_id : varchar(255)', 'paid_at : timestamptz', 'refunded_at : timestamptz', 'refund_reason : varchar(40)')
       ops=@('filter(appointment_id, status=succeeded).first()', 'select_for_update()', 'save(update_fields)') },

    @{ k='agenda'; n='Agenda'; rol='entity'; col=3; f=5.1
       nota='Tabla schedules: la regla de agenda de la que sale cada turno (US-13). Se bloquea con select_for_update() al tomar el turno nuevo.'
       atr=@('id : uuid', 'organization_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'weekday : smallint', 'start_time : time', 'end_time : time', 'slot_minutes : smallint', 'is_active : boolean')
       ops=@('filter(practitioner, is_active)', 'select_for_update()') },

    @{ k='pasarela'; n='Pasarela de Pago'; rol='externo'; col=4; f=2.8
       nota='Stripe, en modo prueba, por el paquete stripe: stripe.Refund.create sobre el PaymentIntent (payments/providers.py:118-129). Con PAYMENTS_PROVIDER = auto y sin STRIPE_SECRET_KEY el proveedor es el simulado y no se la llama (providers.py:39-44, :164-166).'
       atr=@()
       ops=@('Refund.create(api_key, payment_intent, metadata)') }
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
      @{ k='dev';    n='Devolver pago';               col=3; f=0.6 },
      @{ k='valf';   n='Validar ficha';               col=3; f=2.2 },
      @{ k='valt';   n='Validar turno';               col=3; f=4 },
      @{ k='mover';  n='Heredar estado y pago';       col=3; f=5.6 },
      @{ k='error';  n='Informar error';              col=4; f=6.4 },
      @{ k='ok';     n='Transacción completada';      col=4; f=1.4 },
      @{ k='fin';    tipo='final';   col=4; f=3.4 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token válido y permiso] {CanCancelAppointments, CanRescheduleAppointments, changes.py:153, :192}' },
      @{ de='aut';   a='fin403'; r='[sin token o sin permiso] {401 | 403}' },
      @{ de='menu';  a='ver';    r='[consultar] {GET /appointments/appointments/}' },
      @{ de='menu';  a='capc';   r='[cancelar] {MisFichas.tsx:167, appointment_detail_screen.dart:233}' },
      @{ de='menu';  a='capr';   r='[reprogramar] {GET /scheduling/availability/}' },
      @{ de='capc';  a='valf';   r='aceptar() {POST .../cancel/}' },
      @{ de='capr';  a='valf';   r='confirmar(slot) {POST .../reschedule/}' },
      @{ de='valf';  a='dev';    r='[cancelar, activa y futura] / refund_eligible = notice >= umbral {changes.py:66}' },
      @{ de='valf';  a='valt';   r='[reprogramar, activa y futura] / transaction.atomic() {changes.py:94}' },
      @{ de='valf';  a='error';  r='[inexistente, ajena, no activa o pasada] {404 | 403 | 400 changes.py:157, :162, :39, :44}' },
      @{ de='dev';   a='ok';     r='[no elegible, sin pago, devuelto o ProviderError] / refund_for_cancellation() {services.py:155, :160, :163, :164}' },
      @{ de='valt';  a='mover';  r='[turno real y libre] / book_appointment() {changes.py:96}' },
      @{ de='valt';  a='error';  r='[turno inválido u ocupado] / ROLLBACK {400 booking.py:66, 409 changes.py:225}' },
      @{ de='mover'; a='ok';     r='[vieja confirmed: confirmed + transfer_payment()] / status = rescheduled {changes.py:110-122}' },
      @{ de='ver';   a='ok' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'cancelar a tiempo una ficha pagada con Stripe'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. 24 h = cancellation_notice_hours por omisión (tenancy/models.py:99), que cada organización cambia; el umbral se arma en changes.py:61 y se compara en changes.py:66 (refund_eligible = notice >= umbral). Cancelando antes de starts_at - umbral se devuelve el 100 % (payments/services.py:142-163); después, se cancela igual sin devolución, y pasada la hora de la cita _assert_cancellable rechaza con ficha_pasada (changes.py:44). La devolución se pide con stripe.Refund.create (providers.py:123) y el pago queda refunded en la misma petición. Si Stripe falla, la ficha queda cancelled y el pago succeeded (services.py:164-167). El turno queda libre en el mismo COMMIT: _booked_slots sólo cuenta ACTIVE_STATUSES (scheduling/availability.py:62-67, appointments/models.py:35).'
    lineas = @(
      @{ n='Plazo de devolución'
         estados=@('Abierto', 'Cerrado', 'Cita pasada')
         marcas=@( @{ t=0;  e='Abierto' },
                   @{ t=62; e='Cerrado';     ev='starts_at - umbral'; r='24 h' },
                   @{ t=84; e='Cita pasada'; ev='starts_at' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=8;  e='Autenticando'; ev='POST .../cancel/' },
                   @{ t=16; e='Validando';    ev='_assert_cancellable()' },
                   @{ t=24; e='Escribiendo';  ev='save()' },
                   @{ t=42; e='Confirmada';   ev='COMMIT' },
                   @{ t=50; e='Inactiva';     ev='200 (refunded)' } ) },
      @{ n='Ficha'
         estados=@('confirmed', 'cancelled')
         marcas=@( @{ t=0;  e='confirmed' },
                   @{ t=42; e='cancelled'; ev='refund_eligible = true' } ) },
      @{ n='Pago'
         estados=@('succeeded', 'refunded')
         marcas=@( @{ t=0;  e='succeeded' },
                   @{ t=42; e='refunded'; ev='refund_payment()' } ) },
      @{ n='Cobro en Stripe'
         estados=@('Cobrado', 'Devuelto')
         marcas=@( @{ t=0;  e='Cobrado' },
                   @{ t=32; e='Devuelto'; ev='Refund.create()' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'consultar y cancelar la ficha'
    2 = 'reprogramar la ficha'
    3 = 'excepciones'
  }

  # Pares con dos mensajes en el mismo sentido (el tope): paciente->pantalla,
  # paciente->form, gestor->auth, gestor->ficha, gdev->pago, reserva->ficha,
  # reserva->agenda y form->reserva. El dinero se parte en dos controladores
  # (devolucion y traspaso) para no poner tres mensajes sobre una sola linea
  # hacia payments.
  mensajes = @(
    @{ g=1; d='paciente'; a='pantalla';     m='solicitarMisFichas()' },
    @{ g=1; d='pantalla'; a='reserva';      m='listarFichas()' },
    @{ g=1; d='reserva';  a='ficha';        m='leerFichas(paciente)' },
    @{ g=1; d='paciente'; a='pantalla';     m='cancelar(ficha)' },
    @{ g=1; d='pantalla'; a='gestor';       m='cancelar(id)' },
    @{ g=1; d='gestor';   a='auth';         m='verificarPermiso(cancel)' },
    @{ g=1; d='gestor';   a='organizacion'; m='leerAnticipacion()' },
    @{ g=1; d='gestor';   a='ficha';        m='marcarCancelada(refund_eligible)' },
    @{ g=1; d='gestor';   a='gdev';         m='devolverSiCorresponde(ficha)' },
    @{ g=1; d='gdev';     a='pago';         m='buscarPagoExitoso(ficha)' },
    @{ g=1; d='gdev';     a='pasarela';     m='devolver(provider_payment_id)' },
    @{ g=1; d='gdev';     a='pago';         m='marcarDevuelto(cancelacion_a_tiempo)' },
    @{ g=1; d='gdev';     a='bitacora';     m='registrar(PAYMENT_MOVEMENT, devuelto)' },
    @{ g=1; d='gestor';   a='bitacora';     m='registrar(APPOINTMENT_CANCEL)' },

    @{ g=2; d='paciente'; a='form';         m='reprogramar(ficha)' },
    @{ g=2; d='form';     a='reserva';      m='verFicha(id)' },
    @{ g=2; d='form';     a='reserva';      m='consultarDisponibilidad(practitioner, from, to)' },
    @{ g=2; d='reserva';  a='agenda';       m='leerAgendas(practitioner)' },
    @{ g=2; d='paciente'; a='form';         m='elegirTurno(slot)' },
    @{ g=2; d='form';     a='gestor';       m='reprogramar(id, turno)' },
    @{ g=2; d='gestor';   a='auth';         m='verificarPermiso(reschedule)' },
    @{ g=2; d='gestor';   a='reserva';      m='tomarTurno(turno)' },
    @{ g=2; d='reserva';  a='agenda';       m='bloquearAgenda(schedule)' },
    @{ g=2; d='reserva';  a='ficha';        m='crearFicha(turno)' },
    @{ g=2; d='gestor';   a='ficha';        m='heredarEstadoYMarcarReprogramada(vieja, nueva)' },
    @{ g=2; d='gestor';   a='gtras';        m='transferirPago(vieja, nueva)' },
    @{ g=2; d='gtras';    a='pago';         m='moverPago(nueva)' },
    @{ g=2; d='gtras';    a='bitacora';     m='registrar(PAYMENT_MOVEMENT, reprogramado)' },

    @{ g=3; d='gestor';   a='pantalla';     m='fichaNoCancelable(code)' },
    @{ g=3; d='gestor';   a='form';         m='turnoNoDisponible(code)' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Consultar y cancelar la ficha' },
    @{ t='msg'; o='paciente'; d='pantalla';     n='1.1: solicitarMisFichas()' },
    @{ t='msg'; o='pantalla'; d='reserva';      n='1.2: GET /api/appointments/appointments/()' },
    @{ t='msg'; o='reserva';  d='ficha';        n='1.2.1: SELECT * FROM appointments WHERE organization_id = :org AND (patient_id = :pac OR patient_id IN (SELECT id FROM patients WHERE guardian_id = :pac))()' },
    @{ t='msg'; o='reserva';  d='pantalla';     n='1.2.2: 200 (list(Ficha, fee, payment_status, refund_eligible))'; ret=$true },
    @{ t='msg'; o='paciente'; d='pantalla';     n='1.3: cancelar(ficha)  {web: window.confirm, MisFichas.tsx:169; móvil: AlertDialog con la política, appointment_detail_screen.dart:236}' },
    @{ t='msg'; o='pantalla'; d='gestor';       n='1.4: POST /api/appointments/appointments/{id}/cancel/()' },
    @{ t='msg'; o='gestor';   d='auth';         n='1.5: verificarPermiso(appointments.appointment.cancel)' },
    @{ t='msg'; o='auth';     d='gestor';       n='1.5.1: has_permission(code) -> True'; ret=$true },
    @{ t='msg'; o='gestor';   d='ficha';        n='1.5.2: SELECT * FROM appointments JOIN organizations, patients, users WHERE id = :pk AND organization_id = :org()' },
    @{ t='msg'; o='ficha';    d='gestor';       n='1.5.3: Ficha(status, starts_at, patient_id, organization)'; ret=$true },
    @{ t='msg'; o='gestor';   d='gestor';       n='1.5.4: _puede_operar(user, ficha)  {suya o de su dependiente}' },
    @{ t='msg'; o='gestor';   d='gestor';       n='1.5.5: _assert_cancellable(ficha, now)  {is_active y starts_at > now}' },
    @{ t='alt' },
    @{ t='op'; g='ficha propia, activa y futura' },
    @{ t='msg'; o='gestor';   d='organizacion'; n='1.6a: SELECT cancellation_notice_hours FROM organizations WHERE id = :organization_id()  {viene en el JOIN de 1.5.2}' },
    @{ t='msg'; o='gestor';   d='ficha';        n='1.7a: UPDATE appointments SET status = ''cancelled'', cancelled_at, cancellation_reason = ''patient'', refund_eligible = (notice >= umbral) WHERE id = :id()' },
    @{ t='msg'; o='gestor';   d='gdev';         n='1.8a: refund_for_cancellation(ficha, request)  {changes.py:180; sigue en el FLUJO 2}' },
    @{ t='msg'; o='gestor';   d='bitacora';     n='1.9a: INSERT INTO audit_log (action = ''appointment.cancel'', detail = refund_eligible)()' },
    @{ t='msg'; o='gestor';   d='pantalla';     n='1.9a.1: 200 (Ficha, refund_eligible, payment_status)'; ret=$true },
    @{ t='msg'; o='pantalla'; d='paciente';     n='1.10a: mostrarAviso(se devolvió, corresponde o no corresponde devolución)'; ret=$true },
    @{ t='op'; g='ficha inexistente, ajena, no activa o pasada' },
    @{ t='msg'; o='gestor';   d='pantalla';     n='1.6b: fichaNoCancelable(code) -> 404 | 403 | 400'; ret=$true },
    @{ t='msg'; o='pantalla'; d='paciente';     n='1.7b: mostrarError(detail)'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 2 Decidir la devolución' },
    @{ t='alt' },
    @{ t='op'; g='not appointment.refund_eligible' },
    @{ t='msg'; o='gdev';     d='gestor';       n='2.1a: None  {fuera de plazo: sin devolución, services.py:155}'; ret=$true },
    @{ t='op'; g='refund_eligible' },
    @{ t='msg'; o='gdev';     d='pago';         n='2.1b: SELECT * FROM payments WHERE appointment_id = :id AND status = ''succeeded'' LIMIT 1()' },
    @{ t='msg'; o='pago';     d='gdev';         n='2.1b.1: Optional(Payment succeeded)'; ret=$true },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='payment is None' },
    @{ t='msg'; o='gdev';     d='gestor';       n='2.2a: None  {nunca se pagó: nada que devolver, services.py:160}'; ret=$true },
    @{ t='op'; g='hay pago succeeded' },
    @{ t='msg'; o='gdev';     d='gdev';         n='2.2b: refund_payment(pago, reason = ''cancelacion_a_tiempo'')  {sigue en el FLUJO 3}' },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 3 Devolver con el proveedor' },
    @{ t='msg'; o='gdev';     d='gdev';         n='3.1: provider_for(pago.provider)  {stripe o simulated}' },
    @{ t='alt' },
    @{ t='op'; g='provider = stripe y Stripe acepta' },
    @{ t='msg'; o='gdev';     d='pasarela';     n='3.2a: stripe.Refund.create(payment_intent = provider_payment_id, metadata = payment_id)' },
    @{ t='msg'; o='pasarela'; d='gdev';         n='3.2a.1: Refund()'; ret=$true },
    @{ t='msg'; o='gdev';     d='pago';         n='3.3a: UPDATE payments SET status = ''refunded'', refunded_at = now, refund_reason = ''cancelacion_a_tiempo'' WHERE id = :id()' },
    @{ t='msg'; o='gdev';     d='bitacora';     n='3.4a: INSERT INTO audit_log (action = ''payment.movement'', detail.evento = ''devuelto'')()' },
    @{ t='msg'; o='gdev';     d='gestor';       n='3.5a: Payment(refunded)'; ret=$true },
    @{ t='op'; g='provider = simulated' },
    @{ t='msg'; o='gdev';     d='gdev';         n='3.2b: SimulatedProvider.refund(pago)  {no hay dinero: sólo cambia el estado}' },
    @{ t='msg'; o='gdev';     d='pago';         n='3.3b: UPDATE payments SET status = ''refunded'', refunded_at = now, refund_reason = ''cancelacion_a_tiempo'' WHERE id = :id()' },
    @{ t='msg'; o='gdev';     d='bitacora';     n='3.4b: INSERT INTO audit_log (action = ''payment.movement'', detail.evento = ''devuelto'')()' },
    @{ t='msg'; o='gdev';     d='gestor';       n='3.5b: Payment(refunded)'; ret=$true },
    @{ t='op'; g='ProviderError: sin provider_payment_id o StripeError' },
    @{ t='msg'; o='gdev';     d='pasarela';     n='3.2c: stripe.Refund.create(payment_intent)  {sólo si hay PaymentIntent, providers.py:120}' },
    @{ t='msg'; o='pasarela'; d='gdev';         n='3.2c.1: StripeError()'; ret=$true },
    @{ t='msg'; o='gdev';     d='gdev';         n='3.3c: logger.exception(pago, ficha)  {services.py:164-167: la ficha sigue cancelada}' },
    @{ t='msg'; o='gdev';     d='gestor';       n='3.4c: Payment(succeeded)  {queda para devolver a mano}'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 4 Reprogramar la ficha' },
    @{ t='msg'; o='paciente'; d='form';         n='4.1: reprogramar(ficha)  {web: ModalReprogramarFicha; móvil: /appointments/:id/reschedule}' },
    @{ t='msg'; o='form';     d='reserva';      n='4.2: GET /api/appointments/appointments/{id}/()  {sólo el móvil, reschedule_screen.dart:56}' },
    @{ t='msg'; o='reserva';  d='form';         n='4.2.1: 200 (Ficha)'; ret=$true },
    @{ t='msg'; o='form';     d='reserva';      n='4.3: GET /api/scheduling/availability/?practitioner&from&to(hoy, hoy + 14)' },
    @{ t='msg'; o='reserva';  d='agenda';       n='4.4: SELECT * FROM schedules WHERE practitioner_id = :p AND is_active()' },
    @{ t='msg'; o='reserva';  d='ficha';        n='4.4.1: SELECT schedule_id, starts_at FROM appointments WHERE practitioner_id = :p AND status IN (''pending_payment'', ''confirmed'')()' },
    @{ t='msg'; o='reserva';  d='form';         n='4.4.2: 200 (espacios por día)'; ret=$true },
    @{ t='loop'; g='por cada día y cada espacio reservable' },
    @{ t='msg'; o='form';     d='form';         n='4.5: _dias(datos)  {descarta el turno actual, reschedule_screen.dart:82-91}' },
    @{ t='fin' },
    @{ t='msg'; o='paciente'; d='form';         n='4.6: elegirTurno(slot)' },
    @{ t='msg'; o='form';     d='gestor';       n='4.7: POST /api/appointments/appointments/{id}/reschedule/(branch, schedule, starts_at)' },
    @{ t='msg'; o='gestor';   d='auth';         n='4.8: verificarPermiso(appointments.appointment.reschedule)' },
    @{ t='msg'; o='gestor';   d='gestor';       n='4.8.1: _puede_operar(user, ficha); _assert_cancellable(ficha, now)  {mismo SELECT del flujo 1}' },
    @{ t='msg'; o='gestor';   d='reserva';      n='4.9: book_appointment(organization, patient_id, practitioner_id, branch_id, schedule_id, starts_at)  {dentro de transaction.atomic(), changes.py:94}' },
    @{ t='msg'; o='reserva';  d='agenda';       n='4.10: SELECT * FROM schedules WHERE id = :schedule AND branch_id = :branch AND practitioner_id = :p FOR UPDATE()' },
    @{ t='msg'; o='reserva';  d='reserva';      n='4.10.1: _validate_slot_is_real(schedule, starts_at)' },
    @{ t='loop'; g='por cada espacio que generate_slots arma ese día' },
    @{ t='msg'; o='reserva';  d='reserva';      n='4.10.2: comparar(slot_start, starts_at)  {booking.py:63}' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='turno real y libre' },
    @{ t='msg'; o='reserva';  d='ficha';        n='4.11a: INSERT INTO appointments (status = ''pending_payment'', expires_at = now + 15 min)()' },
    @{ t='msg'; o='reserva';  d='gestor';       n='4.11a.1: Ficha(nueva)'; ret=$true },
    @{ t='msg'; o='gestor';   d='gestor';       n='4.12a: heredarEstadoYPago(vieja, nueva)  {sigue en el FLUJO 5}' },
    @{ t='op'; g='turno inválido u ocupado' },
    @{ t='msg'; o='reserva';  d='gestor';       n='4.11b: ValidationError(turno_invalido) | SlotAlreadyTaken()'; ret=$true },
    @{ t='msg'; o='gestor';   d='form';         n='4.12b: turnoNoDisponible(code) -> 400 | 409  {ROLLBACK: la ficha original y su pago quedan intactos}'; ret=$true },
    @{ t='msg'; o='form';     d='paciente';     n='4.13b: mostrarError(detail)  {si turno_ocupado, recarga la grilla}'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 5 Heredar el estado y el pago' },
    @{ t='alt' },
    @{ t='op'; g='appointment.status == confirmed' },
    @{ t='msg'; o='gestor';   d='ficha';        n='5.1a: UPDATE appointments SET status = ''confirmed'', expires_at = NULL WHERE id = :nueva()  {changes.py:110-113}' },
    @{ t='msg'; o='gestor';   d='gtras';        n='5.2a: transfer_payment(vieja, nueva, request)  {changes.py:117}' },
    @{ t='msg'; o='gtras';    d='pago';         n='5.3a: SELECT * FROM payments WHERE appointment_id = :vieja AND status = ''succeeded'' LIMIT 1 FOR UPDATE()' },
    @{ t='msg'; o='pago';     d='gtras';        n='5.3a.1: Optional(Payment succeeded)'; ret=$true },
    @{ t='op'; g='appointment.status == pending_payment' },
    @{ t='msg'; o='gestor';   d='gestor';       n='5.1b: dejarPendiente(nueva)  {sin pago que mover: la nueva queda pending_payment}' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='transfer_payment encontró el pago succeeded' },
    @{ t='msg'; o='gtras';    d='pago';         n='5.4a: UPDATE payments SET appointment_id = :nueva, updated_at = now WHERE id = :pago()' },
    @{ t='msg'; o='gtras';    d='bitacora';     n='5.5a: INSERT INTO audit_log (action = ''payment.movement'', detail.evento = ''reprogramado'', ficha_origen)()' },
    @{ t='msg'; o='gtras';    d='gestor';       n='5.5a.1: Payment(appointment = nueva)'; ret=$true },
    @{ t='op'; g='no hay pago que mover' },
    @{ t='msg'; o='gestor';   d='gestor';       n='5.4b: seguir()  {transfer_payment devuelve None, services.py:194}' },
    @{ t='fin' },
    @{ t='msg'; o='gestor';   d='ficha';        n='5.6: UPDATE appointments SET status = ''rescheduled'' WHERE id = :vieja; SET rescheduled_from_id = :vieja WHERE id = :nueva()' },
    @{ t='msg'; o='gestor';   d='form';         n='5.7: 200 (Ficha nueva)  {COMMIT}'; ret=$true },
    @{ t='msg'; o='form';     d='paciente';     n='5.8: mostrarAviso(Ficha reprogramada)  {móvil: pushReplacement a /appointments/nueva}'; ret=$true }
  )
}

$NAVEGACION_SPRINT2['CU21'] = @{
  actor  = 'Paciente'
  nota   = 'CU21 · US-20. Navegación WEB: Mis fichas lista las fichas (GET de appointments/booking.py, AppointmentViewSet.list) y, sobre una activa, ofrece «Reprogramar» y «Cancelar». Cancelar es un botón con window.confirm, sin campos (MisFichas.tsx:167-192): postea /cancel/ a appointments/changes.py, que devuelve el pago con payments/services.py (refund_for_cancellation). ModalReprogramarFicha es un componente de la misma página: pide la disponibilidad de los próximos 14 días (scheduling/availability.py) y postea /reschedule/; el pago lo muda transfer_payment. Rutas de frontend/src/App.tsx; guarda del requiere de BarraPlataforma.tsx. Par MÓVIL (mobile/lib/core/router/app_router.dart, todas con SoloPacientes): _HomeScreen «Mis fichas» -> /appointments (MyAppointmentsScreen) -> /appointments/:id (AppointmentDetailScreen, con «Cancelar» y la política de devolución en un AlertDialog) -> /appointments/:id/reschedule (RescheduleScreen), que se cierra con la ficha nueva y el detalle salta a /appointments/{nueva}. Clientes HTTP: frontend/src/api/fichas.ts y disponibilidad.ts; mobile/lib/features/appointments/appointments_api.dart y availability/availability_api.dart.'
  menu   = @{ n='Panel.tsx'; ruta='/panel' }
  publicas = @()
  controladores = @{
    changes = @{ n='appointments/changes.py'; ops=@('CancelAppointmentView.post(request, pk)', 'RescheduleAppointmentView.post(request, pk)', 'cancel_appointment(appointment, now)', 'reschedule_appointment(appointment, branch_id, schedule_id, starts_at, now, request)', '_get_appointment_or_404(request, pk)', '_puede_operar(user, appointment)') }
  }
  areas = @(
    @{ guarda='[sesión + appointments.appointment.read]'
       vista=@{ n='MisFichas.tsx'; ruta='/mis-fichas'; atr=@('starts_at', 'status', 'fee', 'payment_status', 'refund_eligible') }; vistaCtrl='changes'
       forms=@(
         @{ n='ModalReprogramarFicha'; atr=@('branch', 'schedule', 'starts_at'); ctrl='changes' }
       ) }
  )
}

$CASOS_SPRINT2['CU22'] = @{
  cu = 'CU22'; nombre = 'Confirmación de Asistencia'; us = 'US-21'
  nota = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Dos disparadores: el botón de la web y del móvil (POST .../confirm-attendance/, ConfirmAttendanceView) y el enlace firmado del correo (attendance_link_view: GET muestra el botón y POST confirma, sin sesión). El correo lo dispara confirm_payment (CU19) con transaction.on_commit (payments/services.py:122), por Brevo vía django-anymail si hay BREVO_API_KEY y por consola si no (config/settings.py:385). Las dos vías terminan en confirm_attendance (attendance.py:48), que es idempotente: sólo escribe attendance_confirmed_at si estaba en NULL, y la bitácora sólo asienta la primera vez (:85, :182). No hay notificación push: es US-28 (Sprint 3). Estado: flujo de la transacción; el plazo y la confirmación van en el diagrama de tiempo.'
  participantes = @(
    @{ k='paciente'; n='Paciente'; rol='actor'; col=0; f=2.2 },

    @{ k='pantalla'; n='PantallaMisFichas'; rol='boundary'; col=1; f=1
       nota='Web: confirmar() de frontend/src/paginas/MisFichas.tsx:153 (botón «Confirmar asistencia» sólo si status = confirmed, futura y sin confirmar, :263) y confirmarAsistencia en frontend/src/api/fichas.ts:152. Móvil: _confirmarAsistencia de mobile/lib/features/appointments/appointment_detail_screen.dart:209 (botón en :461, guarda canConfirmAttendance de appointments_api.dart:137) y confirmarAsistencia en appointments_api.dart:196. Backend: ConfirmAttendanceView en appointments/attendance.py:64.'
       atr=@('POST /api/appointments/appointments/{id}/confirm-attendance/ : 200 | 400 | 401 | 403 | 404')
       ops=@('confirmarAsistencia(id, contexto)', 'confirmar(ficha)', '_confirmarAsistencia()', 'post(request, pk)') },

    @{ k='pagina'; n='PaginaEnlaceAsistencia'; rol='boundary'; col=1; f=3.6
       nota='La página HTML que arma el backend para el enlace del correo: attendance_link_view en appointments/attendance.py:154 (ruta attendance/<str:token>/ de appointments/urls.py:51) y _pagina (:209). Sin JWT ni sesión: la autentica la firma del token. GET muestra el botón «Sí, voy a asistir» y POST confirma, porque los clientes de correo y los antivirus abren los enlaces solos (:157-159). Lleva @csrf_exempt.'
       atr=@('GET /api/appointments/attendance/{token}/ : 200 | 400 | 404 (HTML)', 'POST /api/appointments/attendance/{token}/ : 200 | 400 | 404 (HTML)')
       ops=@('attendance_link_view(request, token)', '_pagina(titulo, texto, status)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (resuelve el usuario y el inquilino desde el token) y appointments/permissions.py:42 (CanConfirmAttendance: appointments.appointment.confirm_attendance, sembrado sólo al rol Paciente en payments/migrations/0003_seed_permissions.py:19, :26). El enlace del correo no pasa por acá.'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)', 'has_permission(code)') },

    @{ k='gestor'; n='GestorAsistencia'; rol='control'; col=2; f=1.2
       nota='confirm_attendance en appointments/attendance.py:48 (las dos vías terminan acá) y owns_appointment en appointments/mixins.py:24 (la ficha es suya o de su dependiente). Rechaza con ValidationError y code estable: ficha_no_confirmada (:51) y ficha_pasada (:56). No abre transaction.atomic(): la escritura va en la transacción por petición de TenantMiddleware.'
       atr=@()
       ops=@('confirm_attendance(appointment, now)', 'owns_appointment(user, appointment)') },

    @{ k='bitgestor'; n='GestorBitacora'; rol='control'; col=2; f=2.3
       nota='audit/services.py. record encola el asiento en la petición y AuditTrailMiddleware lo escribe con flush después de que TenantMiddleware cerró la transacción. Desde el enlace se pasan organization y user = booked_by explícitos, porque no hay usuario autenticado (attendance.py:183-186).'
       atr=@()
       ops=@('record(request, action, entity, entity_id, detail, organization, user)', 'flush(request)') },

    @{ k='enlace'; n='GestorEnlaceAsistencia'; rol='control'; col=2; f=3.5
       nota='appointments/attendance.py: send_confirmation_email (:113), _destinatario (:103), attendance_link (:93, signing.dumps con salt appointments.attendance-link sobre PUBLIC_API_BASE_URL, config/settings.py:298) y la verificación con signing.loads (:162). issue_code de appointments/receipts.py:53 pone el código del comprobante en el cuerpo. Corre fuera de la petición del pago, en su propio tenant_context (:120), y nunca propaga un error (:148).'
       atr=@()
       ops=@('send_confirmation_email(appointment_id, organization_id)', '_destinatario(appointment)', 'attendance_link(appointment)', 'issue_code(appointment)', 'signing.loads(token, salt)', 'tenant_context(organization_id)') },

    @{ k='pago'; n='GestorPago'; rol='control'; col=2; f=4.7
       nota='confirm_payment en payments/services.py:74 (CU19): pasa la ficha a confirmed (:113-115) y, dentro del mismo transaction.atomic() (:83), registra el aviso con transaction.on_commit (:122). Si la transacción se revierte, el correo no sale. Acá sólo aparece como origen del aviso.'
       atr=@()
       ops=@('confirm_payment(payment, provider_payment_id, request)') },

    @{ k='bitacora'; n='Bitacora'; rol='entity'; col=3; f=0.6
       nota='Tabla audit_log. Acción appointment.attendance.confirm (Action.APPOINTMENT_ATTENDANCE_CONFIRM, audit/actions.py:104), con detail = {canal: app} (attendance.py:86) o {canal: correo} (:184).'
       atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
       ops=@('insert(asiento)') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=2.6
       nota='Tabla appointments (db_table, appointments/models.py:162). Columna nueva attendance_confirmed_at, timestamptz NULL (migración appointments/0004_attendance_confirmed_at.py, modelo :111-114): NULL = no confirmó, con fecha = confirmó; es la etiqueta del modelo de inasistencia del Sprint 4. El aviso lee también patients, users (el correo del paciente o del titular), organizations, practitioners y branches con select_related, en la misma consulta.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'booked_by_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'status : varchar(16)', 'attendance_confirmed_at : timestamptz', 'updated_at : timestamptz')
       ops=@('filter(pk, organization)', 'get(pk)', 'save(update_fields)') },

    @{ k='correo'; n='Servicio de Correo'; rol='externo'; col=4; f=4.4
       nota='Brevo, por django-anymail (anymail.backends.brevo.EmailBackend) cuando hay BREVO_API_KEY; si no, django.core.mail.backends.console.EmailBackend (config/settings.py:383-390). Remitente DEFAULT_FROM_EMAIL (:397), que Brevo exige verificado.'
       atr=@()
       ops=@('send_mail(subject, message, from_email, recipient_list, fail_silently)') }
  )

  estado = @{
    estados = @(
      @{ k='ini';    tipo='inicial'; col=0; f=0 },
      @{ k='aut';    n='Autenticar Paciente';           col=0; f=2 },
      @{ k='fin401'; tipo='final';   col=0; f=4.5 },
      @{ k='menu';   n='Seleccionar ficha';             col=1; f=1 },
      @{ k='pag';    n='Desplegar página del enlace';   col=1; f=3.4 },
      @{ k='bus';    n='Buscar ficha';                  col=2; f=2.2 },
      @{ k='val';    n='Validar ficha';                 col=3; f=2.2 },
      @{ k='error';  n='Informar error';                col=4; f=5.5 },
      @{ k='ok';     n='Transacción completada';        col=4; f=1 },
      @{ k='fin';    tipo='final';   col=4; f=3 }
    )
    transiciones = @(
      @{ de='ini';   a='aut' },
      @{ de='aut';   a='menu';   r='[token válido y permiso] {CanConfirmAttendance, attendance.py:67}' },
      @{ de='aut';   a='pag';    r='[enlace del correo con firma válida] {signing.loads, attendance.py:162}' },
      @{ de='aut';   a='fin401'; r='[sin token, sin permiso o firma inválida] {401 | 403 | 400 attendance.py:166}' },
      @{ de='menu';  a='bus';    r='confirmarAsistencia() {POST .../confirm-attendance/}' },
      @{ de='pag';   a='bus';    r='Sí, voy a asistir {POST /attendance/{token}/}' },
      @{ de='pag';   a='ok';     r='[ya había confirmado] {GET, attendance.py:189}' },
      @{ de='bus';   a='val';    r='[existe y es suya o de su dependiente] {owns_appointment, attendance.py:76}' },
      @{ de='bus';   a='error';  r='[inexistente o ajena] {404 attendance.py:76, :173}' },
      @{ de='val';   a='ok';     r='[confirmed y starts_at > now] / attendance_confirmed_at = now si era NULL {attendance.py:58}' },
      @{ de='val';   a='error';  r='[no confirmed o ya pasó] {400 attendance.py:51, :56}' },
      @{ de='error'; a='menu';   r='reintentar()'; ortogonal=$true },
      @{ de='ok';    a='fin' }
    )
  }

  tiempo = @{
    escenario = 'confirmar con el enlace del correo antes de la hora del turno'
    nota = 'Regla relativa (0 a 100): instantes del escenario, no milisegundos medidos. El plazo para confirmar se abre cuando la ficha queda confirmed (confirm_payment, payments/services.py:113) y se cierra a la hora del turno: confirm_attendance rechaza con ficha_pasada si starts_at <= now (attendance.py:56). No hay ventana mínima ni máxima antes del turno. El aviso sale después del COMMIT del pago (transaction.on_commit, services.py:122). El enlace sirve mientras la ficha esté confirmed y por venir: en cada uso se verifica la firma (attendance.py:162) y confirm_attendance revisa el estado y starts_at. En el enlace, Autenticando es verificar la firma, no un JWT. Confirmar dos veces no mueve la fecha (attendance.py:58).'
    lineas = @(
      @{ n='Plazo para confirmar'
         estados=@('Cerrado', 'Abierto')
         marcas=@( @{ t=0;  e='Cerrado' },
                   @{ t=8;  e='Abierto';  ev='confirm_payment()' },
                   @{ t=84; e='Cerrado';  ev='starts_at'; r='hora del turno' } ) },
      @{ n='Enlace del correo'
         estados=@('Sin emitir', 'Vigente')
         marcas=@( @{ t=0;  e='Sin emitir' },
                   @{ t=14; e='Vigente'; ev='send_mail()' } ) },
      @{ n='Transacción'
         estados=@('Inactiva', 'Autenticando', 'Validando', 'Escribiendo', 'Confirmada')
         marcas=@( @{ t=0;  e='Inactiva' },
                   @{ t=36; e='Autenticando'; ev='POST /attendance/{token}/' },
                   @{ t=44; e='Validando';    ev='confirm_attendance()' },
                   @{ t=50; e='Escribiendo';  ev='save()' },
                   @{ t=56; e='Confirmada';   ev='COMMIT' },
                   @{ t=64; e='Inactiva';     ev='200 (¡Gracias!)' } ) },
      @{ n='Asistencia'
         estados=@('Sin confirmar', 'Confirmada')
         marcas=@( @{ t=0;  e='Sin confirmar' },
                   @{ t=56; e='Confirmada'; ev='attendance_confirmed_at' } ) }
    )
  }

  grupos = [ordered]@{
    1 = 'confirmar desde la web o la app'
    2 = 'aviso por correo después del pago'
    3 = 'confirmar con el enlace del correo'
    4 = 'excepciones'
  }

  # Ningun par lleva mas de DOS mensajes en el mismo sentido: el enlace del
  # correo entra por su propia frontera (PaginaEnlaceAsistencia) y su propio
  # controlador (GestorEnlaceAsistencia), y la escritura queda en
  # GestorAsistencia, que es donde terminan las dos vias.
  mensajes = @(
    @{ g=1; d='paciente';  a='pantalla';  m='confirmarAsistencia(ficha)' },
    @{ g=1; d='pantalla';  a='gestor';    m='confirmar(id)' },
    @{ g=1; d='gestor';    a='auth';      m='verificarPermiso(confirm_attendance)' },
    @{ g=1; d='gestor';    a='ficha';     m='leerFicha(id)' },
    @{ g=1; d='gestor';    a='ficha';     m='marcarAsistencia(ahora)' },
    @{ g=1; d='gestor';    a='bitgestor'; m='registrar(ATTENDANCE_CONFIRM, app)' },
    @{ g=1; d='bitgestor'; a='bitacora';  m='insertar(asiento)' },

    @{ g=2; d='pago';      a='enlace';    m='enviarAviso(ficha)' },
    @{ g=2; d='enlace';    a='ficha';     m='leerFichaYDestinatario(id)' },
    @{ g=2; d='enlace';    a='enlace';    m='armarAviso(comprobante, enlace)' },
    @{ g=2; d='enlace';    a='correo';    m='enviarCorreo(destino, cuerpo)' },
    @{ g=2; d='correo';    a='paciente';  m='entregarCorreo(comprobante, enlace)' },

    @{ g=3; d='paciente';  a='pagina';    m='abrirEnlace(token)' },
    @{ g=3; d='pagina';    a='enlace';    m='verEnlace(token)' },
    @{ g=3; d='enlace';    a='enlace';    m='verificarFirma(token)' },
    @{ g=3; d='enlace';    a='ficha';     m='leerFicha(a)' },
    @{ g=3; d='paciente';  a='pagina';    m='confirmar()' },
    @{ g=3; d='pagina';    a='enlace';    m='confirmar(token)' },
    @{ g=3; d='enlace';    a='gestor';    m='confirmarAsistencia(ficha)' },
    @{ g=3; d='enlace';    a='bitgestor'; m='registrar(ATTENDANCE_CONFIRM, correo)' },

    @{ g=4; d='gestor';    a='pantalla';  m='fichaNoConfirmable(code)' },
    @{ g=4; d='gestor';    a='enlace';    m='ValidationError(code)' },
    @{ g=4; d='enlace';    a='pagina';    m='enlaceInvalido(detalle)' },
    @{ g=4; d='correo';    a='enlace';    m='error(envío)' }
  )

  secuencia = @(
    @{ t='nota'; txt='FLUJO 1 Confirmar desde la web o la app' },
    @{ t='msg'; o='paciente';  d='pantalla';  n='1.1: confirmarAsistencia(ficha)  {sólo confirmed, futura y sin confirmar}' },
    @{ t='msg'; o='pantalla';  d='gestor';    n='1.2: POST /api/appointments/appointments/{id}/confirm-attendance/()' },
    @{ t='msg'; o='gestor';    d='auth';      n='1.3: verificarPermiso(appointments.appointment.confirm_attendance)' },
    @{ t='msg'; o='auth';      d='gestor';    n='1.3.1: has_permission(code) -> True'; ret=$true },
    @{ t='msg'; o='gestor';    d='ficha';     n='1.4: SELECT appointments.*, patients.*, practitioners.*, branches.* FROM appointments JOIN patients, practitioners, branches WHERE appointments.id = :pk AND appointments.organization_id = :org LIMIT 1()' },
    @{ t='msg'; o='ficha';     d='gestor';    n='1.4.1: Ficha(status, starts_at, attendance_confirmed_at, patient_id)'; ret=$true },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.5: owns_appointment(user, ficha)  {suya o de su dependiente}' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.6: confirm_attendance(ficha, now)  {status = confirmed y starts_at > now}' },
    @{ t='alt' },
    @{ t='op'; g='attendance_confirmed_at IS NULL' },
    @{ t='msg'; o='gestor';    d='ficha';     n='1.7a: UPDATE appointments SET attendance_confirmed_at = :now, updated_at = :now WHERE id = :id()' },
    @{ t='msg'; o='gestor';    d='bitgestor'; n='1.8a: registrar(APPOINTMENT_ATTENDANCE_CONFIRM, canal = app)' },
    @{ t='msg'; o='bitgestor'; d='bitacora';  n='1.9a: INSERT INTO audit_log (action = ''appointment.attendance.confirm'', entity = ''appointment'', detail = {canal: app})()' },
    @{ t='op'; g='ya estaba confirmada' },
    @{ t='msg'; o='gestor';    d='gestor';    n='1.7b: sinCambios()  {idempotente: no escribe ni asienta}' },
    @{ t='fin' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='1.10: 200(Ficha, attendance_confirmed_at)'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='1.11: mostrarAviso(Asistencia confirmada)'; ret=$true },

    @{ t='nota'; txt='FLUJO 2 Aviso por correo después del pago' },
    @{ t='msg'; o='pago';      d='enlace';    n='2.1: on_commit(send_confirmation_email(appointment_id, organization_id))  {después del COMMIT del pago}' },
    @{ t='msg'; o='enlace';    d='ficha';     n='2.2: SELECT appointments.*, organizations.*, patients.*, users.*, titular.*, practitioners.*, branches.* FROM appointments JOIN organizations, patients, practitioners, branches LEFT JOIN users, patients titular WHERE appointments.id = :appointment_id()' },
    @{ t='msg'; o='ficha';     d='enlace';    n='2.2.1: Ficha(paciente, titular, profesional, sucursal)'; ret=$true },
    @{ t='msg'; o='enlace';    d='enlace';    n='2.3: _destinatario(ficha)' },
    @{ t='loop'; g='por cada candidato en (paciente, titular)' },
    @{ t='msg'; o='enlace';    d='enlace';    n='2.3.1: candidato.user.email  {el primero que tenga correo}' },
    @{ t='fin' },
    @{ t='alt' },
    @{ t='op'; g='hay destinatario' },
    @{ t='msg'; o='enlace';    d='enlace';    n='2.4a: issue_code(ficha)  {MC1. + firma del comprobante}' },
    @{ t='msg'; o='enlace';    d='enlace';    n='2.5a: attendance_link(ficha)  {signing.dumps(a, o)}' },
    @{ t='msg'; o='enlace';    d='correo';    n='2.6a: send_mail(Tu ficha está confirmada, cuerpo, DEFAULT_FROM_EMAIL, [destino])' },
    @{ t='msg'; o='correo';    d='paciente';  n='2.7a: entregarCorreo(comprobante, enlace)' },
    @{ t='msg'; o='enlace';    d='pago';      n='2.7a.1: True()'; ret=$true },
    @{ t='op'; g='ni el paciente ni el titular tienen correo' },
    @{ t='msg'; o='enlace';    d='pago';      n='2.4b: False()  {no se envía}'; ret=$true },
    @{ t='fin' },

    @{ t='nota'; txt='FLUJO 3 Confirmar con el enlace del correo' },
    @{ t='msg'; o='paciente';  d='pagina';    n='3.1: abrirEnlace(token)' },
    @{ t='msg'; o='pagina';    d='enlace';    n='3.2: GET /api/appointments/attendance/{token}/()' },
    @{ t='msg'; o='enlace';    d='enlace';    n='3.3: signing.loads(token, salt = appointments.attendance-link)' },
    @{ t='msg'; o='enlace';    d='ficha';     n='3.4: SELECT appointments.*, practitioners.*, branches.* FROM appointments JOIN practitioners, branches WHERE appointments.id = :a LIMIT 1  {tenant_context(o)}()' },
    @{ t='msg'; o='ficha';     d='enlace';    n='3.4.1: Ficha(starts_at, attendance_confirmed_at)'; ret=$true },
    @{ t='alt' },
    @{ t='op'; g='attendance_confirmed_at IS NOT NULL' },
    @{ t='msg'; o='enlace';    d='pagina';    n='3.5a: 200(Ya habías confirmado esta ficha)'; ret=$true },
    @{ t='op'; g='todavía sin confirmar' },
    @{ t='msg'; o='enlace';    d='pagina';    n='3.5b: 200(profesional, sucursal, fecha, botón Sí, voy a asistir)'; ret=$true },
    @{ t='fin' },
    @{ t='msg'; o='paciente';  d='pagina';    n='3.6: confirmar()' },
    @{ t='msg'; o='pagina';    d='enlace';    n='3.7: POST /api/appointments/attendance/{token}/()  {misma firma y mismo SELECT de 3.3 y 3.4}' },
    @{ t='msg'; o='enlace';    d='gestor';    n='3.8: confirm_attendance(ficha, now)  {status = confirmed y starts_at > now}' },
    @{ t='alt' },
    @{ t='op'; g='attendance_confirmed_at IS NULL' },
    @{ t='msg'; o='gestor';    d='ficha';     n='3.9a: UPDATE appointments SET attendance_confirmed_at = :now, updated_at = :now WHERE id = :id()' },
    @{ t='msg'; o='enlace';    d='bitgestor'; n='3.10a: registrar(APPOINTMENT_ATTENDANCE_CONFIRM, canal = correo, user = booked_by)' },
    @{ t='msg'; o='bitgestor'; d='bitacora';  n='3.11a: INSERT INTO audit_log (action = ''appointment.attendance.confirm'', entity = ''appointment'', detail = {canal: correo})()' },
    @{ t='op'; g='ya estaba confirmada' },
    @{ t='msg'; o='gestor';    d='gestor';    n='3.9b: sinCambios()  {idempotente: no escribe ni asienta}' },
    @{ t='fin' },
    @{ t='msg'; o='enlace';    d='pagina';    n='3.12: 200(¡Gracias! Confirmaste tu asistencia)'; ret=$true },
    @{ t='msg'; o='pagina';    d='paciente';  n='3.13: mostrarPagina(¡Gracias!)'; ret=$true },

    @{ t='nota'; txt='FLUJO 4 Excepciones' },
    @{ t='alt' },
    @{ t='op'; g='appointment is None or not owns_appointment' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='4.1a: fichaNoEncontrada() -> 404'; ret=$true },
    @{ t='msg'; o='pantalla';  d='paciente';  n='4.2a: mostrarError(La ficha no existe)'; ret=$true },
    @{ t='op'; g='status != confirmed' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='4.1b: fichaNoConfirmable(ficha_no_confirmada) -> 400'; ret=$true },
    @{ t='msg'; o='gestor';    d='enlace';    n='4.2b: ValidationError(ficha_no_confirmada)  {cancelada, reprogramada o sin pagar}'; ret=$true },
    @{ t='msg'; o='enlace';    d='pagina';    n='4.3b: 400(No se pudo confirmar)'; ret=$true },
    @{ t='op'; g='starts_at <= now' },
    @{ t='msg'; o='gestor';    d='pantalla';  n='4.1c: fichaNoConfirmable(ficha_pasada) -> 400'; ret=$true },
    @{ t='msg'; o='gestor';    d='enlace';    n='4.2c: ValidationError(ficha_pasada)'; ret=$true },
    @{ t='msg'; o='enlace';    d='pagina';    n='4.3c: 400(Esta ficha ya pasó)'; ret=$true },
    @{ t='op'; g='BadSignature, KeyError o ValueError al leer el token' },
    @{ t='msg'; o='enlace';    d='pagina';    n='4.1d: enlaceInvalido() -> 400  {El enlace no es válido}'; ret=$true },
    @{ t='msg'; o='pagina';    d='paciente';  n='4.2d: mostrarPagina(Enlace inválido)'; ret=$true },
    @{ t='op'; g='la ficha del token no existe' },
    @{ t='msg'; o='enlace';    d='pagina';    n='4.1e: enlaceInvalido() -> 404  {La ficha no existe}'; ret=$true },
    @{ t='op'; g='send_mail lanza una excepción' },
    @{ t='msg'; o='correo';    d='enlace';    n='4.1f: error(Brevo rechaza o no responde)'; ret=$true },
    @{ t='msg'; o='enlace';    d='pago';      n='4.2f: False()  {logger.exception: el pago no se deshace}'; ret=$true },
    @{ t='fin' }
  )
}

$CASOS_SPRINT2['CU23'] = @{
  cu = 'CU23'; nombre = 'Check-in del Paciente'; us = 'US-22'
  nota = 'Clases conceptuales: la nota de cada una dice qué archivos la implementan. Sólo web: no hay pantalla móvil de check-in (el móvil sólo muestra el comprobante, mobile/lib/features/receipts/). Un solo endpoint, POST /api/appointments/checkin/ (checkin.py:49), con QR o con documento, nunca los dos (checkin.py:34, :40). El check-in pasa la ficha de confirmed a attended y anota checked_in_at (checkin.py:118-127) dentro de un transaction.atomic() (checkin.py:64); el QR se verifica antes de tocar la base (receipts.py:62). Por documento busca la ficha del paciente con ese document_number dentro de la organización (checkin.py:156-177); por QR, la ficha cuyo id va firmado en el comprobante (checkin.py:179-204). Si la ficha no está confirmed responde 409 (ficha_no_confirmada, o comprobante_ya_utilizado si ya está attended). El permiso es appointments.appointment.read (checkin.py:52, permissions.py:27). No deja asiento en la bitácora: no hay Bitacora. Sin secuencia, estado, tiempo ni navegación por decisión de alcance.'
  participantes = @(
    @{ k='recep'; n='Recepcionista'; rol='actor'; col=0; f=1.6 },

    @{ k='pantalla'; n='PantallaCheckIn'; rol='boundary'; col=1; f=1.6
       nota='Web: frontend/src/paginas/CheckIn.tsx (ruta /check-in, App.tsx:213; menú en BarraPlataforma.tsx:209-215 con requiere appointments.appointment.read) y realizarCheckIn en frontend/src/api/fichas.ts:193. Un solo formulario con dos modos, documento (por omisión) y QR, que se pega o se escanea como texto. Móvil: sin implementar. Backend: CheckInView en appointments/checkin.py, registrada como "checkin/" en appointments/urls.py:57.'
       atr=@('POST /api/appointments/checkin/ : 200 | 400 | 401 | 403 | 404 | 409')
       ops=@('realizarCheckIn(datos, contexto)', 'enviar(evento)', 'setModo(modo)', 'post(request)') },

    @{ k='auth'; n='GestorAutenticacion'; rol='control'; col=2; f=0
       nota='accounts/authentication.py (TenantJWTAuthentication: resuelve el usuario y el inquilino desde el token) y appointments/permissions.py (CanReadAppointments: appointments.appointment.read). Rechaza antes de entrar a post().'
       atr=@()
       ops=@('authenticate(request)', 'has_permission(request, view)', 'has_permission(code)') },

    @{ k='gestor'; n='GestorCheckIn'; rol='control'; col=2; f=1.2
       nota='appointments/checkin.py: CheckInSerializer (exige QR o documento, no los dos, :30-46) y CheckInView.post (:55-154), que decide por el estado de la ficha y la marca attended. Responde con la ficha, el paciente, la sucursal y el profesional que vienen del mismo SELECT.'
       atr=@()
       ops=@('validate(attrs)', 'post(request)', 'save(update_fields)') },

    @{ k='busq'; n='GestorBusquedaFicha'; rol='control'; col=2; f=2.5
       nota='Los dos métodos privados de CheckInView en appointments/checkin.py: _find_by_document (:156-177) y _find_by_qr (:179-204). Se separa de GestorCheckIn sólo para que el diagrama se lea; en el código es la misma clase. Los dos bloquean con select_for_update() y traen paciente, sucursal y profesional con select_related(): son INNER JOIN (las tres FK son NOT NULL).'
       atr=@()
       ops=@('_find_by_document(organization, document_number)', '_find_by_qr(organization, qr_code)') },

    @{ k='comprobante'; n='GestorComprobante'; rol='control'; col=2; f=3.7
       nota='appointments/receipts.py (US-19): read_code verifica el formato MC1.<firma> con django.core.signing (HMAC sobre SECRET_KEY, sal appointments.receipt) y que la organización firmada sea la del usuario. No consulta la base. La firma no vence ni se consume: lo que se consume es la ficha.'
       atr=@()
       ops=@('read_code(code, organization)', 'loads(value, salt)') },

    @{ k='ficha'; n='Ficha'; rol='entity'; col=3; f=0.8
       nota='Tabla appointments. checked_in_at la agrega la migración appointments/0003_appointment_checked_in_at.py (DateTimeField null=True): NULL hasta el check-in. Meta.ordering = -starts_at (models.py:164), que es el orden que usa _find_by_qr.'
       atr=@('id : uuid', 'organization_id : uuid', 'patient_id : uuid', 'practitioner_id : uuid', 'branch_id : uuid', 'starts_at : timestamptz', 'ends_at : timestamptz', 'status : varchar(16)', 'checked_in_at : timestamptz', 'updated_at : timestamptz')
       ops=@('select_for_update()', 'select_related(patient, branch, practitioner)', 'filter(organization, patient__document_number)', 'filter(organization, id)', 'order_by(starts_at)', 'first()', 'save(update_fields)') },

    @{ k='paciente'; n='Paciente'; rol='entity'; col=3; f=1.9
       nota='Tabla patients. document_number admite NULL (un recién nacido no tiene documento) y es único junto con organization_id y document_type (uq_patient_document).'
       atr=@('id : uuid', 'organization_id : uuid', 'document_type : varchar(10)', 'document_number : varchar(20)', 'first_name : varchar(80)', 'last_name : varchar(80)')
       ops=@('full_name()') },

    @{ k='profesional'; n='Profesional'; rol='entity'; col=3; f=2.9
       nota='Tabla practitioners. Sólo aporta el nombre, que se arma en checkin.py:145-148.'
       atr=@('id : uuid', 'organization_id : uuid', 'first_name : varchar(80)', 'last_name : varchar(80)')
       ops=@('leer(first_name, last_name)') },

    @{ k='sucursal'; n='Sucursal'; rol='entity'; col=3; f=3.8
       nota='Tabla branches. Sólo aporta el nombre.'
       atr=@('id : uuid', 'organization_id : uuid', 'name : varchar(120)')
       ops=@('leer(name)') }
  )

  grupos = [ordered]@{
    1 = 'check-in por número de documento'
    2 = 'check-in por código QR (comprobante firmado de US-19)'
    3 = 'excepciones de la solicitud: sin permiso, identificador requerido o ambiguo, comprobante inválido, adulterado o de otra organización'
    4 = 'excepciones de la ficha: no encontrada, ya utilizada o no confirmada'
  }

  # Ningun par lleva mas de dos mensajes en el mismo sentido: por eso la
  # busqueda de la ficha vive en GestorBusquedaFicha y la firma del QR en
  # GestorComprobante. Los INNER JOIN de paciente, sucursal y profesional se
  # dibujan una vez, en el grupo 1; el grupo 2 hace el mismo JOIN.
  mensajes = @(
    @{ g=1; d='recep';    a='pantalla';    m='registrarLlegada(documento)' },
    @{ g=1; d='pantalla'; a='gestor';      m='realizarCheckIn(document_number)' },
    @{ g=1; d='gestor';   a='auth';        m='verificarPermiso(appointments.appointment.read)' },
    @{ g=1; d='gestor';   a='gestor';      m='validate(attrs)' },
    @{ g=1; d='gestor';   a='busq';        m='_find_by_document(organization, document_number)' },
    @{ g=1; d='busq';     a='ficha';       m='SELECT * FROM appointments INNER JOIN patients, branches, practitioners WHERE appointments.organization_id = :org AND patients.document_number = :doc ORDER BY appointments.starts_at ASC LIMIT 1 FOR UPDATE' },
    @{ g=1; d='busq';     a='paciente';    m='INNER JOIN patients ON patients.id = appointments.patient_id WHERE patients.document_number = :doc' },
    @{ g=1; d='busq';     a='profesional'; m='INNER JOIN practitioners ON practitioners.id = appointments.practitioner_id' },
    @{ g=1; d='busq';     a='sucursal';    m='INNER JOIN branches ON branches.id = appointments.branch_id' },
    @{ g=1; d='gestor';   a='ficha';       m='UPDATE appointments SET status = ''attended'', checked_in_at = :now, updated_at = :now WHERE id = :id  {status era confirmed}' },

    @{ g=2; d='recep';    a='pantalla';    m='registrarLlegada(codigoQR)' },
    @{ g=2; d='pantalla'; a='gestor';      m='realizarCheckIn(qr_code)' },
    @{ g=2; d='gestor';   a='auth';        m='verificarPermiso(appointments.appointment.read)' },
    @{ g=2; d='gestor';   a='gestor';      m='validate(attrs)' },
    @{ g=2; d='gestor';   a='busq';        m='_find_by_qr(organization, qr_code)' },
    @{ g=2; d='busq';     a='comprobante'; m='read_code(qr_code, organization)  {MC1., firma, organización}' },
    @{ g=2; d='busq';     a='ficha';       m='SELECT * FROM appointments INNER JOIN patients, branches, practitioners WHERE appointments.organization_id = :org AND appointments.id = :id ORDER BY appointments.starts_at DESC LIMIT 1 FOR UPDATE' },
    @{ g=2; d='gestor';   a='ficha';       m='UPDATE appointments SET status = ''attended'', checked_in_at = :now, updated_at = :now WHERE id = :id  {status era confirmed}' },

    @{ g=3; d='auth';        a='pantalla'; m='sinPermiso() -> 401 | 403' },
    @{ g=3; d='comprobante'; a='busq';     m='ReceiptError(comprobante_invalido | comprobante_adulterado | comprobante_de_otra_organizacion)' },
    @{ g=3; d='busq';        a='gestor';   m='ReceiptError(code, detail)' },
    @{ g=3; d='gestor';      a='pantalla'; m='solicitudRechazada(code) -> 400  {identificador_requerido | identificador_ambiguo | comprobante_*}' },

    @{ g=4; d='busq';        a='gestor';   m='None  {ninguna ficha}' },
    @{ g=4; d='gestor';      a='pantalla'; m='fichaRechazada(code) -> 404 ficha_no_encontrada | 409 comprobante_ya_utilizado | 409 ficha_no_confirmada' }
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
         atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
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
         atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar(60)', 'entity : varchar(60)', 'entity_id : varchar(64)', 'detail : jsonb', 'occurred_at : timestamptz')
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
       atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
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
       atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
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
       atr=@('id : bigint', 'organization_id : uuid', 'user_id : uuid', 'action : varchar', 'entity : varchar', 'detail : jsonb', 'occurred_at : timestamptz')
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
