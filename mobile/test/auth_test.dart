/// US-02 — Pruebas del inicio de sesión.
///
/// Cubren lo que decide si la persona entra o no, y los tres finales que la
/// pantalla tiene que distinguir: credenciales que no son, cuenta bloqueada por
/// el RNF-07 y slug de centro médico que no existe.
///
/// No hace falta emulador ni dispositivo:
///
///     flutter test
///
/// El almacenamiento seguro se reemplaza por uno en memoria. Tocar el Keystore
/// del teléfono desde una prueba de Dart puro no se puede —es un canal de
/// plataforma— y tampoco es lo que se está probando acá.
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session.dart';
import 'package:mobile/core/session/token_storage.dart';
import 'package:mobile/features/auth/auth_service.dart';

/// El almacenamiento seguro, pero en un mapa.
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

/// Un backend de mentira que contesta lo que se le diga.
///
/// Devuelve también la petición recibida, porque parte de lo que hay que
/// comprobar es **qué se manda**: sin el slug, el backend no sabe en qué
/// inquilino buscar el correo.
({ApiClient client, List<http.Request> requests}) fakeBackend(
  int status,
  Map<String, dynamic> body, {
  Session? session,
}) {
  final requests = <http.Request>[];

  final http.Client mock = MockClient((request) async {
    requests.add(request);
    return http.Response(
      jsonEncode(body),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  });

  return (
    client: ApiClient(httpClient: mock, auth: session),
    requests: requests,
  );
}

Map<String, dynamic> get respuestaDeIngreso => {
      'access': 'access.de.prueba',
      'refresh': 'refresh.de.prueba',
      'user': {
        'id': 'a1b2',
        'email': 'karen@kolping.com',
        'full_name': 'Karen Ortega',
        'organization': 'kolping',
        'is_platform_admin': false,
        'roles': [
          {'code': 'patient', 'name': 'Paciente'},
        ],
        'permissions': ['accounts.role.read'],
      },
    };

void main() {
  group('inicio de sesión', () {
    test('entrar guarda los tokens, el centro médico y al usuario', () async {
      final storage = MemoryStorage();
      final session = Session(storage: storage);
      final backend = fakeBackend(200, respuestaDeIngreso, session: session);

      await AuthService(session: session, client: backend.client).signIn(
        organization: 'kolping',
        email: 'karen@kolping.com',
        password: 'una-clave',
      );

      expect(session.isSignedIn, isTrue);
      expect(session.user?.fullName, 'Karen Ortega');
      expect(session.organizationSlug, 'kolping');
      expect(storage.values['access'], 'access.de.prueba');
      expect(storage.values['refresh'], 'refresh.de.prueba');
    });

    test('el slug del centro médico viaja en el cuerpo', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend(200, respuestaDeIngreso, session: session);

      await AuthService(session: session, client: backend.client).signIn(
        organization: 'kolping',
        email: 'karen@kolping.com',
        password: 'una-clave',
      );

      final enviado = jsonDecode(backend.requests.single.body);
      expect(enviado['organization'], 'kolping');
      expect(enviado['email'], 'karen@kolping.com');
    });

    test('el permiso del usuario llega y se puede consultar', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend(200, respuestaDeIngreso, session: session);

      await AuthService(session: session, client: backend.client).signIn(
        organization: 'kolping',
        email: 'karen@kolping.com',
        password: 'una-clave',
      );

      expect(session.user!.can('accounts.role.read'), isTrue);
      expect(session.user!.can('scheduling.slot.write'), isFalse);
    });

    test('el rol de paciente se reconoce y habilita el auto-servicio', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend(200, respuestaDeIngreso, session: session);

      await AuthService(session: session, client: backend.client).signIn(
        organization: 'kolping',
        email: 'karen@kolping.com',
        password: 'una-clave',
      );

      expect(session.user!.isPatient, isTrue);
    });

    test('sin el rol de paciente, el auto-servicio no se habilita', () async {
      final session = Session(storage: MemoryStorage());
      final respuesta = {
        ...respuestaDeIngreso,
        'user': {
          ...respuestaDeIngreso['user'] as Map<String, dynamic>,
          'roles': <Map<String, String>>[],
        },
      };
      final backend = fakeBackend(200, respuesta, session: session);

      await AuthService(session: session, client: backend.client).signIn(
        organization: 'kolping',
        email: 'karen@kolping.com',
        password: 'una-clave',
      );

      expect(session.user!.isPatient, isFalse);
    });

    test('unas credenciales que no son dejan la sesión cerrada', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend(401, {
        'code': 'credenciales_invalidas',
        'detail': 'El correo o la contraseña no son correctos.',
      }, session: session);

      final service = AuthService(session: session, client: backend.client);

      await expectLater(
        service.signIn(
          organization: 'kolping',
          email: 'karen@kolping.com',
          password: 'la-que-no-era',
        ),
        throwsA(
          isA<ApiError>().having(
            (e) => e.code,
            'code',
            'credenciales_invalidas',
          ),
        ),
      );

      expect(session.isSignedIn, isFalse);
    });

    test('la cuenta bloqueada trae hasta cuándo lo está', () async {
      final hasta = DateTime.now().add(const Duration(minutes: 15));
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend(423, {
        'code': 'cuenta_bloqueada',
        'detail': 'La cuenta está bloqueada temporalmente por intentos '
            'fallidos. Volvé a intentar más tarde.',
        'locked_until': hasta.toIso8601String(),
      }, session: session);

      final service = AuthService(session: session, client: backend.client);

      try {
        await service.signIn(
          organization: 'kolping',
          email: 'karen@kolping.com',
          password: 'una-clave',
        );
        fail('tenía que lanzar ApiError');
      } on ApiError catch (error) {
        expect(error.code, 'cuenta_bloqueada');
        expect(error.status, 423);
        expect(error.lockedUntil, isNotNull);
        expect(error.lockedUntil!.isAfter(DateTime.now()), isTrue);
      }
    });

    test('un centro médico que no existe se señala en su campo', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend(400, {
        'code': 'organizacion_no_disponible',
        'organization': ['El centro médico no existe o no está activo.'],
      }, session: session);

      final service = AuthService(session: session, client: backend.client);

      try {
        await service.signIn(
          organization: 'no-existe',
          email: 'karen@kolping.com',
          password: 'una-clave',
        );
        fail('tenía que lanzar ApiError');
      } on ApiError catch (error) {
        expect(error.code, 'organizacion_no_disponible');
        expect(
          error.forField('organization'),
          'El centro médico no existe o no está activo.',
        );
      }
    });
  });
}
