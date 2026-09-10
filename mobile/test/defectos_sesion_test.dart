/// Pruebas de los defectos de sesión y de errores corregidos el 2026-09-09.
///
/// Cada `test` de acá nombra el defecto que cubre. Son los tres que dejaban
/// al usuario con datos incorrectos o afuera del sistema sin motivo, y no los
/// detectaba ninguna prueba anterior porque todas asumían el camino feliz.
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session.dart';
import 'package:mobile/core/session/token_storage.dart';

class MemoryStorage extends TokenStorage {
  final Map<String, String> values = {};

  @override
  Future<String?> readAccess() async => values['access'];

  @override
  Future<String?> readRefresh() async => values['refresh'];

  @override
  Future<String?> readOrganization() async => values['organization'];

  @override
  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    values['access'] = access;
    values['refresh'] = refresh;
  }

  @override
  Future<void> saveOrganization(String slug) async {
    values['organization'] = slug;
  }

  @override
  Future<void> clearTokens() async {
    values.remove('access');
    values.remove('refresh');
  }
}

/// Un JWT de mentira con el vencimiento que se le pida.
String tokenQueVence(Duration desdeAhora) {
  final exp = DateTime.now().add(desdeAhora).millisecondsSinceEpoch ~/ 1000;

  String parte(Map<String, dynamic> data) =>
      base64Url.encode(utf8.encode(jsonEncode(data))).replaceAll('=', '');

  final header = parte({'alg': 'HS256', 'typ': 'JWT'});
  final payload = parte({'exp': exp, 'user_id': 'a1b2'});
  return '$header.$payload.firma-que-no-se-verifica';
}

http.Response _json(Map<String, dynamic> body, int status) => http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json'},
    );

void main() {
  group('B-04: qué cierra la sesión y qué no', () {
    /// Con el token de acceso vencido, cualquier petición dispara la
    /// renovación. Lo que conteste `/accounts/token/refresh/` decide si la
    /// sesión sobrevive.
    Future<Session> sesionQueRenueva(http.Response respuesta) async {
      final storage = MemoryStorage()
        ..values['access'] = tokenQueVence(const Duration(seconds: -10))
        ..values['refresh'] = tokenQueVence(const Duration(days: 7));

      final session = Session(
        storage: storage,
        refreshClient: ApiClient(httpClient: MockClient((_) async => respuesta)),
        // `meClient` también va mockeado, y no es un detalle: sin esto usa la
        // URL por omisión -`http://localhost:8000/api`- y la prueba le pega al
        // backend de desarrollo si está levantado. Con un token de mentira
        // contesta 401, la sesión se cierra por eso, y la prueba parece estar
        // midiendo la renovación cuando en realidad mide otra cosa.
        meClient: ApiClient(
          httpClient: MockClient(
            (_) async => _json({'id': 'u1', 'roles': [], 'permissions': []}, 200),
          ),
        ),
      );
      await session.restore();
      await session.accessToken();
      return session;
    }

    test('un 500 del servidor NO cierra la sesión', () async {
      final session = await sesionQueRenueva(
        _json({'detail': 'error interno'}, 500),
      );

      // El refresco sigue siendo válido: la caída es del servidor, no de la
      // sesión. Cerrarla acá le hace perder el trabajo a la persona y encima
      // le miente sobre la causa.
      expect(session.isSignedIn, isTrue);
    });

    test('un 502 del proxy NO cierra la sesión', () async {
      final session = await sesionQueRenueva(
        http.Response('<html>Bad Gateway</html>', 502),
      );
      expect(session.isSignedIn, isTrue);
    });

    test('un 404 por URL mal configurada NO cierra la sesión', () async {
      final session = await sesionQueRenueva(_json({}, 404));
      expect(session.isSignedIn, isTrue);
    });

    test('un 401 SÍ cierra la sesión', () async {
      final session = await sesionQueRenueva(
        _json({'code': 'token_not_valid', 'detail': 'sin valor'}, 401),
      );

      // Acá sí: el backend dijo que este refresco no sirve más.
      expect(session.isSignedIn, isFalse);
    });
  });

  group('B-03 y B-07: no saber el rol no es ser paciente', () {
    test('si /accounts/me/ falla, el perfil queda marcado como no disponible',
        () async {
      final storage = MemoryStorage()
        ..values['access'] = tokenQueVence(const Duration(hours: 1))
        ..values['refresh'] = tokenQueVence(const Duration(days: 7));

      final session = Session(
        storage: storage,
        meClient: ApiClient(
          httpClient: MockClient((_) async => _json({}, 500)),
        ),
      );
      await session.restore();

      // Entró igual -el token es válido- pero sin datos de quién es. La
      // pantalla de inicio tiene que decirlo, no suponer "paciente" y
      // ofrecerle a un administrador pantallas que le van a dar 403.
      expect(session.isSignedIn, isTrue);
      expect(session.user, isNull);
      expect(session.perfilNoDisponible, isTrue);
    });

    test('con /accounts/me/ respondiendo, el rol y los permisos quedan puestos',
        () async {
      final storage = MemoryStorage()
        ..values['access'] = tokenQueVence(const Duration(hours: 1))
        ..values['refresh'] = tokenQueVence(const Duration(days: 7));

      final session = Session(
        storage: storage,
        meClient: ApiClient(
          httpClient: MockClient(
            (_) async => _json({
              'id': 'u1',
              'email': 'ana@pruebas.test',
              'full_name': 'Ana Admin',
              'organization': 'pruebas',
              'is_platform_admin': false,
              'roles': [
                {'code': 'org_admin', 'name': 'Administrador'}
              ],
              'permissions': ['scheduling.schedule.read', 'audit.log.read'],
            }, 200),
          ),
        ),
      );
      await session.restore();

      expect(session.perfilNoDisponible, isFalse);
      expect(session.user?.isPatient, isFalse);
      expect(session.user?.can('audit.log.read'), isTrue);
      expect(session.user?.can('users.role.delete'), isFalse);
    });
  });

  group('A-11: los errores de librerías se traducen', () {
    test('el mensaje de SimpleJWT no llega en inglés a la pantalla', () {
      final error = ApiError.fromResponse(401, {
        'detail': 'Given token not valid for any token type',
        'code': 'token_not_valid',
      });

      expect(error.message, 'Tu sesión venció. Volvé a entrar.');
      expect(error.message, isNot(contains('token')));
      // Y ahora sí se reconoce como sesión vencida, que era la otra mitad:
      // `isSessionExpired` no conocía este código.
      expect(error.isSessionExpired, isTrue);
    });

    test('el mensaje que escribe el backend del proyecto pasa intacto', () {
      final error = ApiError.fromResponse(401, {
        'detail': 'El correo o la contraseña no son correctos.',
        'code': 'credenciales_invalidas',
      });

      // La traducción es sólo para los códigos de librerías: lo que el equipo
      // escribió a propósito para una persona no se toca.
      expect(error.message, 'El correo o la contraseña no son correctos.');
    });

    test('sin detail, el mensaje por omisión sigue en español', () {
      expect(
        ApiError.fromResponse(500, const <String, dynamic>{}).message,
        contains('El servidor tuvo un problema'),
      );
    });
  });
}
