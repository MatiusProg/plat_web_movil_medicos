/// Pruebas del shell.
///
/// Cubren lo que sostiene a las ocho pantallas móviles del sprint y que, si
/// falla, falla en todas a la vez: la lectura del vencimiento del token —de la
/// que depende la renovación automática— y la traducción de la respuesta de
/// error del backend.
///
/// No hace falta emulador ni dispositivo: son pruebas de Dart puro.
///
///     flutter test
///
/// Los nombres van en español, como pide `docs/convenciones-de-codigo.md` §3.
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/jwt.dart';
import 'package:mobile/core/session/session.dart';
import 'package:mobile/core/session/token_storage.dart';

/// El almacenamiento seguro, pero en un mapa — igual que en `auth_test.dart`
/// y `register_test.dart`: cada archivo de test arma el suyo a propósito, en
/// vez de compartir uno entre archivos de test.
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

/// Arma un JWT de mentira con el `exp` que se le pida.
///
/// La firma es basura a propósito: el cliente no la verifica —no puede, no
/// tiene la clave— y esta prueba comprueba justamente que leer el payload no
/// dependa de ella.
String tokenQueVence(Duration desdeAhora) {
  final exp = DateTime.now().add(desdeAhora).millisecondsSinceEpoch ~/ 1000;

  String parte(Map<String, dynamic> data) =>
      base64Url.encode(utf8.encode(jsonEncode(data))).replaceAll('=', '');

  final header = parte({'alg': 'HS256', 'typ': 'JWT'});
  final payload = parte({
    'exp': exp,
    'user_id': 'a1b2',
    'organization_id': 'c3d4',
    'is_platform_admin': false,
  });

  return '$header.$payload.firma-que-no-se-verifica';
}

void main() {
  group('lectura del token', () {
    test('se lee el vencimiento sin verificar la firma', () {
      final token = tokenQueVence(const Duration(minutes: 30));
      final vence = Jwt.expiry(token);

      expect(vence, isNotNull);
      expect(vence!.isAfter(DateTime.now()), isTrue);
    });

    test('se leen los claims del proyecto', () {
      final claims = Jwt.payload(tokenQueVence(const Duration(minutes: 30)));

      expect(claims!['organization_id'], 'c3d4');
      expect(claims['is_platform_admin'], false);
    });

    test('un token que vence dentro del margen se renueva', () {
      final token = tokenQueVence(const Duration(seconds: 30));

      expect(Jwt.expiresWithin(token, const Duration(minutes: 1)), isTrue);
    });

    test('un token con margen de sobra no se renueva', () {
      final token = tokenQueVence(const Duration(minutes: 30));

      expect(Jwt.expiresWithin(token, const Duration(minutes: 1)), isFalse);
    });

    test('un token ilegible cuenta como vencido', () {
      // Es preferible una renovación de más que una petición con 401 seguro.
      expect(Jwt.expiresWithin('no-es-un-jwt', Duration.zero), isTrue);
      expect(Jwt.payload('no-es-un-jwt'), isNull);
    });
  });

  group('errores de la API', () {
    test('se conserva el código del backend', () {
      final error = ApiError.fromResponse(401, {
        'code': 'credenciales_invalidas',
        'detail': 'El correo o la contraseña no son correctos.',
      });

      expect(error.code, 'credenciales_invalidas');
      expect(error.status, 401);
      expect(error.message, 'El correo o la contraseña no son correctos.');
    });

    test('las validaciones de DRF quedan por campo', () {
      final error = ApiError.fromResponse(400, {
        'organization': ['El centro médico no existe o no está activo.'],
      });

      expect(error.forField('organization'),
          'El centro médico no existe o no está activo.');
      // Sin `detail`, el mensaje general es el primer error de campo: es lo
      // que la pantalla muestra si no mira campo por campo.
      expect(error.message,
          'El centro médico no existe o no está activo.');
    });

    test('el bloqueo del RNF-07 trae hasta cuándo dura', () {
      final hasta = DateTime.now().add(const Duration(minutes: 15));
      final error = ApiError.fromResponse(423, {
        'code': 'cuenta_bloqueada',
        'detail': 'La cuenta está bloqueada temporalmente.',
        'locked_until': hasta.toIso8601String(),
      });

      expect(error.code, 'cuenta_bloqueada');
      expect(error.lockedUntil, isNotNull);
    });

    test('una respuesta sin código no rompe', () {
      final error = ApiError.fromResponse(500, null);

      expect(error.code, 'desconocido');
      expect(error.message, contains('servidor'));
    });

    test('la sesión vencida se reconoce por el código', () {
      final error = ApiError.fromResponse(401, {'code': 'refresh_invalido'});

      expect(error.isSessionExpired, isTrue);
      expect(ApiError.offline.isOffline, isTrue);
    });
  });

  group('reconstrucción de la sesión al reabrir la app', () {
    final usuario = {
          'id': 'a1b2',
          'email': 'karen@kolping.com',
          'full_name': 'Karen Ortega',
          'organization': 'kolping',
          'is_platform_admin': false,
          'roles': [
            {'code': 'patient', 'name': 'Paciente'},
          ],
          'permissions': <String>[],
        };

    test('con el refresco vigente, se pide y guarda el usuario', () async {
      final storage = MemoryStorage()
        ..values['refresh'] = tokenQueVence(const Duration(days: 5))
        ..values['access'] = tokenQueVence(const Duration(minutes: 20));
      final requests = <http.Request>[];
      final mock = MockClient((request) async {
        requests.add(request);
        return http.Response(
          jsonEncode(usuario),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });
      final session = Session(
        storage: storage,
        meClient: ApiClient(httpClient: mock),
      );

      await session.restore();

      expect(session.isSignedIn, isTrue);
      expect(session.user?.fullName, 'Karen Ortega');
      expect(session.user?.isPatient, isTrue);
      expect(requests.single.url.path, endsWith('/accounts/me/'));
    });

    test('sin red, la sesión sigue abierta pero sin datos del usuario',
        () async {
      final storage = MemoryStorage()
        ..values['refresh'] = tokenQueVence(const Duration(days: 5))
        ..values['access'] = tokenQueVence(const Duration(minutes: 20));
      final mock = MockClient((request) async {
        throw http.ClientException('sin conexión, simulado');
      });
      final session = Session(
        storage: storage,
        meClient: ApiClient(httpClient: mock),
      );

      await session.restore();

      // El gate por rol simplemente no tiene datos hasta que haya conexión
      // -las pantallas van a fallar solas con su propio error si hacía
      // falta-, pero no hay que echar a alguien que sí tenía sesión.
      expect(session.isSignedIn, isTrue);
      expect(session.user, isNull);
    });

    test('con el refresco vencido, no se llega a pedir el usuario', () async {
      final storage = MemoryStorage()
        ..values['refresh'] = tokenQueVence(-const Duration(days: 1));
      final requests = <http.Request>[];
      final mock = MockClient((request) async {
        requests.add(request);
        return http.Response(jsonEncode(usuario), 200);
      });
      final session = Session(
        storage: storage,
        meClient: ApiClient(httpClient: mock),
      );

      await session.restore();

      expect(session.isSignedIn, isFalse);
      expect(requests, isEmpty);
    });
  });
}
