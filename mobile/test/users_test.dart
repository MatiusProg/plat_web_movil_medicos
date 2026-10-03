/// Pruebas de US-04 — usuarios y roles (móvil), centradas en la paginación.
///
///     flutter test test/users_test.dart
///
/// Con datos reales una organización tiene unas 80 cuentas y más de 25
/// asignaciones de rol: con el backend paginando de a 25, la pantalla
/// mostraba sólo la primera página y quitar un rol fallaba con "No se
/// encontró la asignación" para quien caía en otra.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/users/users_api.dart';
import 'package:mobile/features/users/users_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

/// Una respuesta de `PageNumberPagination` de a 25 sobre [filas].
http.Response _paginaDe(List<Map<String, dynamic>> filas, http.Request req) {
  final pagina = int.parse(req.url.queryParameters['page'] ?? '1');
  final desde = (pagina - 1) * 25;
  final hasta = (desde + 25).clamp(0, filas.length);
  return _json({
    'count': filas.length,
    'next': hasta < filas.length ? 'http://x/?page=${pagina + 1}' : null,
    'previous': null,
    'results': filas.sublist(desde, hasta),
  }, 200);
}

Map<String, dynamic> _usuario(int n, {List<Map<String, dynamic>>? roles}) => {
  'id': 'u$n',
  'email': 'persona$n@demo.test',
  'full_name': 'Persona $n',
  'is_active': true,
  'roles': roles ?? const [],
};

final _rolMedico = {
  'id': 'r-medico',
  'code': 'medico',
  'name': 'Médico',
  'description': '',
  'is_system': true,
  'is_active': true,
  'assigned_users': 1,
  'permissions': <String>[],
};

List<Map<String, dynamic>> _ochentaUsuarios() => [
  for (var i = 1; i <= 80; i++) _usuario(i),
];

/// El `ListView` de la pantalla: el buscador también es desplazable, y sin
/// esto `scrollUntilVisible` no sabe cuál mover.
final _lista = find.byType(Scrollable).first;

Future<void> _montar(WidgetTester tester, MockClient mock) async {
  tester.view.physicalSize = const Size(1200, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      home: UsersScreen(client: ApiClient(httpClient: mock)),
    ),
  );
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  group('listarUsuarios', () {
    test('pide la página y devuelve total y si hay más', () async {
      final pedidas = <Uri>[];
      final mock = MockClient((req) async {
        pedidas.add(req.url);
        return _paginaDe(_ochentaUsuarios(), req);
      });

      final pagina = await listarUsuarios(ApiClient(httpClient: mock), page: 2);

      expect(pedidas.single.queryParameters['page'], '2');
      expect(pagina.results.first.email, 'persona26@demo.test');
      expect(pagina.total, 80);
      expect(pagina.hayMas, isTrue);
    });

    test('manda search sólo cuando hay algo escrito', () async {
      final pedidas = <Uri>[];
      final mock = MockClient((req) async {
        pedidas.add(req.url);
        return _paginaDe(const [], req);
      });
      final client = ApiClient(httpClient: mock);

      await listarUsuarios(client, search: '  ');
      await listarUsuarios(client, search: 'ana@');

      expect(pedidas[0].hasQuery, isFalse);
      expect(pedidas[1].queryParameters, {'search': 'ana@'});
    });
  });

  group('mapaDeAsignaciones', () {
    test('filtra por el usuario y recorre todas sus páginas', () async {
      final pedidas = <Uri>[];
      // 30 asignaciones del mismo usuario: la que importa queda en la página 2.
      final filas = [
        for (var i = 1; i <= 30; i++)
          {'id': 100 + i, 'user': 'u7', 'role': 'r$i'},
      ];
      final mock = MockClient((req) async {
        pedidas.add(req.url);
        return _paginaDe(filas, req);
      });

      final mapa = await mapaDeAsignaciones(
        ApiClient(httpClient: mock),
        userId: 'u7',
      );

      expect(pedidas, hasLength(2));
      expect(
        pedidas.every((u) => u.path == '/api/accounts/user-roles/'),
        isTrue,
      );
      expect(pedidas.every((u) => u.queryParameters['user'] == 'u7'), isTrue);
      expect(mapa, hasLength(30));
      expect(mapa['u7|r30'], 130);
    });
  });

  group('UsersScreen', () {
    testWidgets('muestra 25 de 80 y "Cargar más" trae la siguiente página', (
      tester,
    ) async {
      final mock = MockClient((req) async {
        if (req.url.path == '/api/accounts/roles/') {
          return _paginaDe([_rolMedico], req);
        }
        return _paginaDe(_ochentaUsuarios(), req);
      });

      await _montar(tester, mock);

      expect(find.text('Mostrando 25 de 80 usuarios'), findsOneWidget);
      expect(find.text('Persona 1'), findsOneWidget);
      expect(find.text('Persona 26', skipOffstage: false), findsNothing);

      await tester.scrollUntilVisible(
        find.text('Cargar más'),
        300,
        scrollable: _lista,
      );
      await tester.tap(find.text('Cargar más'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      // La página 2 quedó debajo, hasta la persona 50 y no más.
      await tester.scrollUntilVisible(
        find.text('Persona 50'),
        300,
        scrollable: _lista,
      );
      expect(find.text('Persona 50'), findsOneWidget);
      expect(find.text('Persona 51', skipOffstage: false), findsNothing);

      // Y el conteo de arriba lo refleja.
      await tester.scrollUntilVisible(
        find.text('Mostrando 50 de 80 usuarios'),
        -300,
        scrollable: _lista,
      );
      expect(find.text('Mostrando 50 de 80 usuarios'), findsOneWidget);
    });

    testWidgets('el buscador filtra por correo en el backend', (tester) async {
      final pedidas = <Uri>[];
      final mock = MockClient((req) async {
        if (req.url.path == '/api/accounts/roles/') {
          return _paginaDe([_rolMedico], req);
        }
        pedidas.add(req.url);
        final buscado = req.url.queryParameters['search'];
        final filas = buscado == null
            ? _ochentaUsuarios()
            : _ochentaUsuarios()
                  .where((u) => (u['email'] as String).contains(buscado))
                  .toList();
        return _paginaDe(filas, req);
      });

      await _montar(tester, mock);
      await tester.enterText(
        find.byKey(const Key('usuarios-buscar')),
        'persona7',
      );
      // La espera del buscador, para no pedir en cada letra.
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pump(const Duration(milliseconds: 100));

      expect(pedidas.last.queryParameters['search'], 'persona7');
      // persona7 y persona70..79.
      expect(find.text('Mostrando 11 de 11 usuarios'), findsOneWidget);
      expect(find.text('Cargar más'), findsNothing);
    });

    testWidgets('quitar un rol usa la asignación de esa persona', (
      tester,
    ) async {
      http.Request? borrado;
      final mock = MockClient((req) async {
        if (req.method == 'DELETE') {
          borrado = req;
          return http.Response('', 204);
        }
        if (req.url.path == '/api/accounts/roles/') {
          return _paginaDe([_rolMedico], req);
        }
        if (req.url.path == '/api/accounts/user-roles/') {
          // Sólo contesta bien si se pidió filtrado por la persona.
          if (req.url.queryParameters['user'] != 'u1') {
            return _paginaDe([], req);
          }
          return _paginaDe([
            {'id': 4242, 'user': 'u1', 'role': 'r-medico'},
          ], req);
        }
        return _paginaDe([
          _usuario(
            1,
            roles: [
              {'id': 'r-medico', 'code': 'medico', 'name': 'Médico'},
            ],
          ),
        ], req);
      });

      await _montar(tester, mock);
      await tester.tap(find.text('Gestionar roles'));
      await tester.pumpAndSettle();

      await tester.tap(find.byType(SwitchListTile));
      await tester.pumpAndSettle();

      expect(find.textContaining('No se encontró la asignación'), findsNothing);
      expect(borrado, isNotNull);
      expect(borrado!.url.path, '/api/accounts/user-roles/4242/');
    });
  });
}
