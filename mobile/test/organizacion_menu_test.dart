/// El menú del centro médico se arma por permisos, no por rol.
///
/// Es la regla que hace que un rol nuevo —los arma cada organización en
/// US-04— funcione sin tocar la aplicación. Si esto se rompe, el síntoma es
/// silencioso y feo: alguien ve una sección que no puede usar y se come un
/// 403, o al revés, pierde una que sí le corresponde.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/session/session.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/session/token_storage.dart';
import 'package:mobile/features/organization/organization_home_screen.dart';

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

String tokenQueVence(Duration desdeAhora) {
  final exp = DateTime.now().add(desdeAhora).millisecondsSinceEpoch ~/ 1000;
  String parte(Map<String, dynamic> data) =>
      base64Url.encode(utf8.encode(jsonEncode(data))).replaceAll('=', '');
  return '${parte({'alg': 'HS256'})}.${parte({'exp': exp})}.firma';
}

/// Una sesión ya abierta con los permisos que se le pidan.
Future<Session> sesionCon(List<String> permisos) async {
  final storage = MemoryStorage()
    ..values['access'] = tokenQueVence(const Duration(hours: 1))
    ..values['refresh'] = tokenQueVence(const Duration(days: 7))
    ..values['organization'] = 'pruebas';

  final session = Session(
    storage: storage,
    // Mockeado a propósito: sin esto la prueba le pega al backend de
    // desarrollo si está levantado, y el resultado cambia según eso.
    meClient: ApiClient(
      httpClient: MockClient(
        (_) async => http.Response(
          jsonEncode({
            'id': 'u1',
            'email': 'quien@pruebas.test',
            'full_name': 'Quien Sea',
            'organization': 'pruebas',
            'is_platform_admin': false,
            'roles': [
              {'code': 'org_admin', 'name': 'Administrador'}
            ],
            'permissions': permisos,
          }),
          200,
          headers: {'content-type': 'application/json'},
        ),
      ),
    ),
  );
  await session.restore();
  return session;
}

Future<void> montarPanel(WidgetTester tester, Session session) async {
  await tester.pumpWidget(
    SessionScope(
      session: session,
      child: const MaterialApp(home: OrganizationHomeScreen()),
    ),
  );
  await tester.pump();
}

void main() {
  testWidgets('con todos los permisos se ven las nueve secciones',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 3200);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final session = await sesionCon(const [
      'scheduling.schedule.read',
      'scheduling.slot.read',
      'catalog.branch.read',
      'catalog.specialty.read',
      'catalog.professional.read',
      'audit.log.read',
      'users.user.read',
      'users.role.read',
    ]);
    await montarPanel(tester, session);

    expect(find.text('Agendas'), findsOneWidget);
    expect(find.text('Disponibilidad'), findsOneWidget);
    expect(find.text('Sucursales'), findsOneWidget);
    expect(find.text('Bitácora'), findsOneWidget);
    expect(find.text('Roles y permisos'), findsOneWidget);
  });

  testWidgets('un rol recortado ve sólo lo suyo', (tester) async {
    // Una recepcionista con agendas pero sin bitácora ni roles. La aplicación
    // no sabe que existe el rol "recepcionista": mira los permisos.
    final session = await sesionCon(const [
      'scheduling.schedule.read',
      'scheduling.slot.read',
    ]);
    await montarPanel(tester, session);

    expect(find.text('Agendas'), findsOneWidget);
    expect(find.text('Disponibilidad'), findsOneWidget);

    expect(find.text('Bitácora'), findsNothing);
    expect(find.text('Roles y permisos'), findsNothing);
    expect(find.text('Usuarios'), findsNothing);
    expect(find.text('Sucursales'), findsNothing);
  });

  testWidgets('sin ningún permiso se explica, no se muestra una pantalla vacía',
      (tester) async {
    final session = await sesionCon(const []);
    await montarPanel(tester, session);

    expect(
      find.textContaining('todavía no tiene permisos de administración'),
      findsOneWidget,
    );
  });
}
