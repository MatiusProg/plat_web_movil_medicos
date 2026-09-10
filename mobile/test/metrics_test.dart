/// Pruebas de US-45 — panel del superadministrador de plataforma (móvil).
///
///     flutter test test/metrics_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/metrics/metrics_api.dart';
import 'package:mobile/features/metrics/metrics_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> get _tablero => {
      'organizations': {
        'total': 5,
        'active': 3,
        'suspended': 1,
        'inactive': 1,
      },
      'by_plan': [
        {'plan_code': 'basic', 'plan_name': 'Básico', 'count': 2},
        {'plan_code': 'premium', 'plan_name': 'Premium', 'count': 1},
      ],
      'alerts': {'pending': 4, 'critical_pending': 1},
    };

void main() {
  group('fetchDashboard', () {
    test('parsea organizaciones, planes y alertas', () async {
      final mock = MockClient((req) async => _json(_tablero, 200));

      final tablero = await fetchDashboard(ApiClient(httpClient: mock));

      expect(tablero.organizations.total, 5);
      expect(tablero.organizations.active, 3);
      expect(tablero.byPlan, hasLength(2));
      expect(tablero.byPlan.first.planName, 'Básico');
      expect(tablero.byPlan.first.count, 2);
      expect(tablero.alerts.pending, 4);
      expect(tablero.alerts.criticalPending, 1);
    });

    test('sin suscripciones vigentes, by_plan llega vacío', () async {
      final sinPlanes = {..._tablero, 'by_plan': <Map<String, dynamic>>[]};
      final mock = MockClient((req) async => _json(sinPlanes, 200));

      final tablero = await fetchDashboard(ApiClient(httpClient: mock));

      expect(tablero.byPlan, isEmpty);
    });
  });

  group('PlatformDashboardScreen', () {
    testWidgets('muestra los conteos del tablero', (tester) async {
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mock = MockClient((req) async => _json(_tablero, 200));

      await tester.pumpWidget(
        MaterialApp(
          home: PlatformDashboardScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('5'), findsOneWidget); // total
      expect(find.text('3'), findsOneWidget); // activas
      expect(find.text('Básico'), findsOneWidget);
      expect(find.text('Premium'), findsOneWidget);
      expect(find.text('4'), findsOneWidget); // alertas pendientes
    });

    testWidgets('un error del backend se muestra en vez de romper la pantalla',
        (tester) async {
      final mock = MockClient(
        (req) async => _json(
          {'code': 'permiso_denegado', 'detail': 'No tenés permiso para hacer esto.'},
          403,
        ),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: PlatformDashboardScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('No tenés permiso para hacer esto.'), findsOneWidget);
    });

    testWidgets('el pull-to-refresh no revienta y trae datos nuevos',
        (tester) async {
      // `setState(() => _futuro = futuro)` devuelve el valor de la propia
      // asignación (el Future), y Flutter revienta con "setState() callback
      // argument returned a Future" antes de marcar el widget para
      // reconstruir -el dato nuevo llega del backend pero la pantalla se
      // queda pintando el Future viejo-. Esta prueba existe porque ese bug
      // apareció en vivo en `SubscriptionsScreen` y las pruebas de entonces
      // sólo cubrían la primera carga, nunca la recarga.
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      var llamadas = 0;
      final mock = MockClient((req) async {
        llamadas++;
        final tablero = llamadas == 1
            ? _tablero
            : {
                ..._tablero,
                'organizations': {
                  ...(_tablero['organizations'] as Map<String, dynamic>),
                  'total': 9,
                },
              };
        return _json(tablero, 200);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: PlatformDashboardScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('5'), findsOneWidget);

      // Se invoca directamente el `onRefresh` del `RefreshIndicator` -el
      // mismo `_recargar` que usa el pull-to-refresh real- en vez de simular
      // el gesto de arrastre, que es frágil en el entorno de pruebas.
      final refreshIndicator =
          tester.widget<RefreshIndicator>(find.byType(RefreshIndicator));
      await refreshIndicator.onRefresh();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tester.takeException(), isNull);
      expect(find.text('9'), findsOneWidget);
    });
  });
}
