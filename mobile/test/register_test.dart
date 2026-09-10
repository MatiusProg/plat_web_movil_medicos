/// US-01 — Pruebas del registro de paciente.
///
/// El backend no deja tokens en la respuesta del alta (`.to_representation`
/// en `accounts/serializers/registration.py` no los incluye), así que lo que
/// hay que comprobar es que, creada la cuenta, se entra con las mismas
/// credenciales — y que un error de validación no llega a intentarlo.
///
///     flutter test
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

/// El almacenamiento seguro, pero en un mapa — igual que en `auth_test.dart`.
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

/// Un backend de mentira que contesta según el método: `POST /register/` una
/// vez, `POST /login/` la próxima. Devuelve también las peticiones recibidas,
/// para comprobar qué se manda a cada endpoint.
({ApiClient client, List<http.Request> requests}) fakeBackend(
  Map<String, ({int status, Map<String, dynamic> body})> responsesByPath, {
  Session? session,
}) {
  final requests = <http.Request>[];
  final pending = Map.of(responsesByPath);

  final http.Client mock = MockClient((request) async {
    requests.add(request);
    final path = request.url.path;
    final response = pending.remove(
      pending.keys.firstWhere((key) => path.endsWith(key)),
    );
    return http.Response(
      jsonEncode(response!.body),
      response.status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );
  });

  return (
    client: ApiClient(httpClient: mock, auth: session),
    requests: requests,
  );
}

Map<String, dynamic> get respuestaDeAlta => {
      'id': 'p1',
      'email': 'nueva@kolping.com',
      'organization': 'kolping',
      'role': 'patient',
      'patient_id': 'pac-1',
    };

Map<String, dynamic> get respuestaDeIngreso => {
      'access': 'access.de.prueba',
      'refresh': 'refresh.de.prueba',
      'user': {
        'id': 'p1',
        'email': 'nueva@kolping.com',
        'full_name': 'Nueva Paciente',
        'organization': 'kolping',
        'is_platform_admin': false,
        'permissions': <String>[],
      },
    };

void main() {
  group('registro de paciente', () {
    test('crear la cuenta deja la sesión iniciada', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend({
        '/accounts/register/': (status: 201, body: respuestaDeAlta),
        '/accounts/login/': (status: 200, body: respuestaDeIngreso),
      }, session: session);

      await AuthService(session: session, client: backend.client).registerPatient(
        organization: 'kolping',
        email: 'nueva@kolping.com',
        password: 'una-clave-larga',
        passwordConfirmation: 'una-clave-larga',
        documentNumber: '12345678',
        firstName: 'Nueva',
        lastName: 'Paciente',
      );

      expect(session.isSignedIn, isTrue);
      expect(session.user?.fullName, 'Nueva Paciente');
      expect(backend.requests, hasLength(2));
      expect(backend.requests[0].url.path, endsWith('/accounts/register/'));
      expect(backend.requests[1].url.path, endsWith('/accounts/login/'));
    });

    test('lo que se manda al registrar trae los siete campos', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend({
        '/accounts/register/': (status: 201, body: respuestaDeAlta),
        '/accounts/login/': (status: 200, body: respuestaDeIngreso),
      }, session: session);

      await AuthService(session: session, client: backend.client).registerPatient(
        organization: 'kolping',
        email: 'nueva@kolping.com',
        password: 'una-clave-larga',
        passwordConfirmation: 'una-clave-larga',
        documentNumber: '12345678',
        firstName: 'Nueva',
        lastName: 'Paciente',
      );

      final enviado = jsonDecode(backend.requests.first.body);
      expect(enviado, {
        'organization': 'kolping',
        'email': 'nueva@kolping.com',
        'password': 'una-clave-larga',
        'password_confirmation': 'una-clave-larga',
        'document_number': '12345678',
        'first_name': 'Nueva',
        'last_name': 'Paciente',
      });
    });

    test('un documento ya usado deja la sesión cerrada y no entra', () async {
      final session = Session(storage: MemoryStorage());
      final backend = fakeBackend({
        '/accounts/register/': (
          status: 400,
          body: {
            'code': 'validacion',
            'document_number': [
              'Ya existe una cuenta con este documento en la organizacion.',
            ],
          },
        ),
      }, session: session);

      final service = AuthService(session: session, client: backend.client);

      await expectLater(
        service.registerPatient(
          organization: 'kolping',
          email: 'nueva@kolping.com',
          password: 'una-clave-larga',
          passwordConfirmation: 'una-clave-larga',
          documentNumber: '12345678',
          firstName: 'Nueva',
          lastName: 'Paciente',
        ),
        throwsA(
          isA<ApiError>().having(
            (e) => e.forField('document_number'),
            'forField(document_number)',
            'Ya existe una cuenta con este documento en la organizacion.',
          ),
        ),
      );

      expect(session.isSignedIn, isFalse);
      // No debe haber intentado entrar después de un alta que falló.
      expect(backend.requests, hasLength(1));
    });
  });
}
