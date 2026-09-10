/// US-02 — La llamada al inicio de sesión.
///
/// Separada de la pantalla a propósito: la pantalla se ocupa del formulario y
/// de los mensajes, y esto de hablar con el backend y depositar el resultado en
/// la sesión del shell. Así el ingreso se puede probar sin construir widgets, y
/// el día que haya que entrar desde otro lado —el registro de US-01, que deja a
/// la persona adentro después de crear la cuenta— se reutiliza esto y no se
/// copia el `post`.
///
/// El contrato está en `backend/accounts/views/auth.py`:
///
///     POST /accounts/login/   {organization?, email, password}
///       200 {access, refresh, user{…}}
///       400 organizacion_no_disponible   el slug no existe o está inactivo
///       401 credenciales_invalidas       correo o contraseña
///       403 cuenta_inactiva              la cuenta fue dada de baja
///       423 cuenta_bloqueada             RNF-07, con `locked_until`
library;

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session.dart';

class AuthService {
  AuthService({required Session session, ApiClient? client})
      : _session = session,
        // Con el contexto de la sesión, para que el cliente ponga
        // `X-Organization` en las peticiones que siguen.
        _client = client ?? ApiClient(auth: session);

  final Session _session;
  final ApiClient _client;

  /// CU1 — Entra y deja la sesión iniciada en el shell.
  ///
  /// Lanza [ApiError] si el backend rechaza; la pantalla decide qué mensaje
  /// mostrar según el código.
  ///
  /// **El slug viaja en el cuerpo y no en `Session.useOrganization`.** El
  /// backend acepta las dos formas y le da prioridad al cuerpo, y guardar el
  /// slug antes de saber si es válido deja escrito en el teléfono el error de
  /// tipeo de quien se equivocó al escribirlo. Se guarda al volver, cuando ya
  /// se sabe que existe: de eso se encarga [Session.saveSession].
  ///
  /// [organization] vacío es el Superadministrador de Plataforma, el único
  /// usuario que no pertenece a ningún centro médico.
  Future<void> signIn({
    required String organization,
    required String email,
    required String password,
  }) async {
    final data = await _client.post(
      '/accounts/login/',
      authenticated: false,
      body: {
        'organization': organization,
        'email': email,
        'password': password,
      },
    );

    if (data is! Map<String, dynamic>) {
      throw ApiError.offline;
    }

    final user = data['user'];
    final currentUser = user is Map<String, dynamic>
        ? CurrentUser.fromJson(user)
        : null;

    await _session.saveSession(
      access: data['access'] as String? ?? '',
      refresh: data['refresh'] as String? ?? '',
      // El slug que devuelve el backend, no el que se escribió: llega
      // normalizado y, para el superadministrador, es `null`.
      organization: currentUser?.organization ?? '',
      user: currentUser,
    );
  }

  /// US-01 — Crea la cuenta del paciente y deja a la persona adentro.
  ///
  /// El contrato está en `backend/accounts/views/registration.py`:
  ///
  ///     POST /accounts/register/   {organization, email, password,
  ///                                  password_confirmation, document_number,
  ///                                  first_name, last_name}
  ///       201 {id, email, organization, role, patient_id}
  ///       400 validacion           por campo, en la forma de DRF
  ///
  /// El backend no devuelve tokens: registrar no es entrar. Por eso, creada
  /// la cuenta, se llama a [signIn] con las mismas credenciales — se
  /// reutiliza el ingreso en vez de copiar el `post` que arma la sesión.
  Future<void> registerPatient({
    required String organization,
    required String email,
    required String password,
    required String passwordConfirmation,
    required String documentNumber,
    required String firstName,
    required String lastName,
  }) async {
    await _client.post(
      '/accounts/register/',
      authenticated: false,
      body: {
        'organization': organization,
        'email': email,
        'password': password,
        'password_confirmation': passwordConfirmation,
        'document_number': documentNumber,
        'first_name': firstName,
        'last_name': lastName,
      },
    );

    await signIn(organization: organization, email: email, password: password);
  }
}
