/// El estado de la sesión y su renovación automática.
///
/// Es lo que sostiene a las ocho pantallas móviles del sprint: quién está
/// dentro, con qué token, de qué organización, y qué pasa cuando el token se
/// vence.
///
/// **Qué hace el shell y qué no.** Guardar la sesión, renovarla, cerrarla y
/// decirle al router si hay alguien adentro. Lo que **no** hace es el ingreso:
/// pedir las credenciales y llamar a `/accounts/login/` es US-02, y va en
/// `features/auth/`. El shell expone [saveSession] para que esa pantalla
/// deposite lo que reciba, y [signOut] para el cierre —que según el reparto lo
/// invoca la pantalla de perfil de US-05, no la de auth—.
library;

import 'package:flutter/foundation.dart';

import '../api/client.dart';
import '../api/errors.dart';
import '../config.dart';
import 'jwt.dart';
import 'token_storage.dart';

/// Los datos de quien inició sesión, tal como los devuelve `/accounts/login/`.
///
/// Viven en memoria y no en el almacenamiento: al reabrir la aplicación se
/// vuelven a pedir. Una copia guardada se desactualiza —los permisos cambian
/// cuando el administrador toca un rol (US-04)— y hay que acordarse de
/// borrarla al cerrar sesión.
class CurrentUser {
  const CurrentUser({
    required this.id,
    required this.email,
    required this.fullName,
    required this.organization,
    required this.isPlatformAdmin,
    required this.permissions,
  });

  final String id;
  final String email;
  final String fullName;
  final String? organization;
  final bool isPlatformAdmin;
  final List<String> permissions;

  /// Atajo de `permissions.contains`, para decidir qué se muestra.
  ///
  /// Esconder un botón no autoriza nada: la puerta real la pone el backend con
  /// `user.has_permission`. Esto sólo evita ofrecer lo que va a dar 403.
  bool can(String permission) => permissions.contains(permission);

  factory CurrentUser.fromJson(Map<String, dynamic> json) => CurrentUser(
        id: json['id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        organization: json['organization'] as String?,
        isPlatformAdmin: json['is_platform_admin'] as bool? ?? false,
        permissions:
            (json['permissions'] as List?)?.cast<String>() ?? const <String>[],
      );
}

enum SessionStatus {
  /// Todavía no se leyó el almacenamiento: no se sabe si hay sesión.
  unknown,
  signedOut,
  signedIn,
}

class Session extends ChangeNotifier implements AuthContext {
  Session({TokenStorage? storage, ApiClient? refreshClient})
      : _storage = storage ?? TokenStorage(),
        // Cliente SIN contexto de autenticación: es el que renueva. Si tuviera
        // contexto, pedir un token para renovar dispararía otra renovación.
        _refreshClient = refreshClient ?? ApiClient();

  final TokenStorage _storage;
  final ApiClient _refreshClient;

  SessionStatus _status = SessionStatus.unknown;
  CurrentUser? _user;
  String? _access;
  String? _refresh;
  String? _organization;

  /// Una renovación a la vez.
  ///
  /// Al abrir una pantalla salen varias peticiones juntas y todas ven el token
  /// por vencer. Sin esto, cada una lanzaría su propia renovación, y como el
  /// backend **rota** el refresco (`ROTATE_REFRESH_TOKENS`), la primera manda
  /// el refresco a la lista negra y las demás fallan con la sesión recién
  /// renovada. Compartir el Future hace que todas esperen la misma.
  Future<void>? _refreshing;

  SessionStatus get status => _status;
  CurrentUser? get user => _user;
  bool get isSignedIn => _status == SessionStatus.signedIn;

  @override
  String? get organizationSlug => _organization;

  /// Lee lo guardado al arrancar la aplicación.
  ///
  /// Se llama una vez desde `main`. Mientras tanto el estado es
  /// [SessionStatus.unknown], y el router muestra la pantalla de carga en vez
  /// de mandar al ingreso a alguien que sí tenía sesión.
  Future<void> restore() async {
    _organization = await _storage.readOrganization();
    _access = await _storage.readAccess();
    _refresh = await _storage.readRefresh();

    if (_refresh == null) {
      _setStatus(SessionStatus.signedOut);
      return;
    }

    // Con el refresco vencido no hay nada que hacer: dura 7 días y ya pasaron.
    if (Jwt.expiresWithin(_refresh!, Duration.zero)) {
      await signOut();
      return;
    }

    _setStatus(SessionStatus.signedIn);
  }

  /// Guarda lo que devolvió el login. Lo llama la pantalla de US-02.
  Future<void> saveSession({
    required String access,
    required String refresh,
    required String organization,
    CurrentUser? user,
  }) async {
    _access = access;
    _refresh = refresh;
    _organization = organization;
    _user = user;

    await _storage.saveTokens(access: access, refresh: refresh);
    if (organization.isNotEmpty) {
      await _storage.saveOrganization(organization);
    }

    _setStatus(SessionStatus.signedIn);
  }

  /// El slug elegido antes de autenticar, para que el interceptor lo mande.
  ///
  /// El formulario de ingreso lo necesita: sin `X-Organization`, el backend no
  /// sabe en qué inquilino buscar el correo.
  Future<void> useOrganization(String slug) async {
    _organization = slug;
    if (slug.isNotEmpty) await _storage.saveOrganization(slug);
    notifyListeners();
  }

  @override
  Future<String?> accessToken({bool forceRefresh = false}) async {
    if (_refresh == null) return null;

    final vencido = _access == null ||
        Jwt.expiresWithin(_access!, Config.refreshMargin);

    if (forceRefresh || vencido) {
      await (_refreshing ??= _renew().whenComplete(() => _refreshing = null));
    }

    return _access;
  }

  Future<void> _renew() async {
    final refresh = _refresh;
    if (refresh == null) return;

    try {
      final data = await _refreshClient.post(
        '/accounts/token/refresh/',
        body: {'refresh': refresh},
        authenticated: false,
      );

      if (data is Map<String, dynamic>) {
        _access = data['access'] as String?;
        // Llega un refresco nuevo porque el backend rota: hay que guardar los
        // dos o la renovación siguiente falla con el anterior en la lista
        // negra.
        _refresh = data['refresh'] as String? ?? refresh;
        await _storage.saveTokens(access: _access!, refresh: _refresh!);
      }
    } on ApiError catch (error) {
      // Sin red no se cierra la sesión: el token sigue siendo válido, lo que
      // falta es conexión. Cerrarla acá echaría a la gente del sistema cada
      // vez que entra al ascensor.
      if (error.isOffline) return;
      await signOut();
    }
  }

  @override
  Future<void> onSessionExpired() => signOut();

  /// CU4 — Cierre de sesión.
  ///
  /// Manda el refresco a la lista negra para que la sesión no se pueda
  /// renovar, y borra lo guardado. Si la llamada al backend falla —sin red,
  /// por ejemplo— se limpia igual: dejar la sesión abierta en el teléfono
  /// porque el servidor no contestó es lo peor de los dos mundos.
  Future<void> signOut() async {
    final refresh = _refresh;
    final access = _access;

    _access = null;
    _refresh = null;
    _user = null;
    await _storage.clearTokens();
    _setStatus(SessionStatus.signedOut);

    if (refresh == null || access == null) return;

    try {
      await ApiClient(auth: _StaticAuth(access, _organization)).post(
        '/accounts/logout/',
        body: {'refresh': refresh},
      );
    } on ApiError {
      // Ya está cerrada del lado del teléfono. El refresco expira solo.
    }
  }

  void _setStatus(SessionStatus status) {
    _status = status;
    notifyListeners();
  }
}

/// Contexto de un solo uso para el cierre de sesión.
///
/// El endpoint exige estar autenticado, pero para entonces la sesión ya se
/// limpió en memoria. Esto le presta el token que se acaba de dar de baja, sin
/// reabrir la sesión ni disparar una renovación.
class _StaticAuth implements AuthContext {
  _StaticAuth(this._access, this._organization);

  final String _access;
  final String? _organization;

  @override
  Future<String?> accessToken({bool forceRefresh = false}) async => _access;

  @override
  String? get organizationSlug => _organization;

  @override
  Future<void> onSessionExpired() async {}
}
