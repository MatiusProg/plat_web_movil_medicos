/// Pruebas de US-44 — planes de suscripción (móvil).
///
///     flutter test test/plans_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/plans/plans_api.dart';
import 'package:mobile/features/plans/plans_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _plan({int? maxUsers}) => {
      'id': 'p1', 'code': 'pro', 'name': 'Plan Pro', 'description': '',
      'monthly_price': '199.00', 'currency': 'BOB',
      'max_branches': null, 'max_users': maxUsers, 'max_practitioners': null,
      'max_appointments_month': null, 'max_ai_queries_month': null,
      'storage_mb': null, 'is_active': true,
    };

Map<String, dynamic> _pagina(List<Map<String, dynamic>> results) =>
    {'count': results.length, 'next': null, 'previous': null, 'results': results};

void main() {
  group('listPlans', () {
    test('con isActive arma el query param', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_pagina([_plan()]), 200);
      });

      final planes = await listPlans(ApiClient(httpClient: mock), isActive: true);

      expect(capturada!.url.path, endsWith('/platform/plans/'));
      expect(capturada!.url.queryParameters['is_active'], 'true');
      expect(planes.single.name, 'Plan Pro');
      expect(planes.single.maxUsers, isNull);
    });

    test('sin isActive no manda el query param', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_pagina([]), 200);
      });

      await listPlans(ApiClient(httpClient: mock));

      expect(capturada!.url.hasQuery, isFalse);
    });
  });

  group('createPlan / updatePlan', () {
    test('un límite vacío se manda como null, no como 0 ni ausente', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_plan(), 201);
      });

      await createPlan(
        ApiClient(httpClient: mock),
        code: 'pro',
        name: 'Plan Pro',
        description: '',
        monthlyPrice: '199.00',
        currency: 'BOB',
        maxBranches: null,
        maxUsers: 10,
        maxPractitioners: null,
        maxAppointmentsMonth: null,
        maxAiQueriesMonth: null,
        storageMb: null,
        isActive: true,
      );

      final enviado = jsonDecode(capturada!.body);
      expect(enviado['max_users'], 10);
      expect(enviado.containsKey('max_branches'), isTrue);
      expect(enviado['max_branches'], isNull);
    });

    test('updatePlan pega a PATCH /platform/plans/{id}/', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_plan(maxUsers: 5), 200);
      });

      final actualizado = await updatePlan(
        ApiClient(httpClient: mock),
        'p1',
        name: 'Plan Pro',
        description: '',
        monthlyPrice: '199.00',
        currency: 'BOB',
        maxBranches: null,
        maxUsers: 5,
        maxPractitioners: null,
        maxAppointmentsMonth: null,
        maxAiQueriesMonth: null,
        storageMb: null,
        isActive: true,
      );

      expect(capturada!.method, 'PATCH');
      expect(capturada!.url.path, endsWith('/platform/plans/p1/'));
      expect(actualizado.maxUsers, 5);
    });
  });

  group('PlansScreen', () {
    testWidgets('el pull-to-refresh no revienta y trae datos nuevos',
        (tester) async {
      // Mismo bug que en `SubscriptionsScreen`: `setState(() => _futuro =
      // futuro)` devuelve el Future en vez de nada y Flutter revienta antes
      // de reconstruir el widget, así que la recarga nunca se ve en pantalla
      // aunque el backend haya contestado bien.
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      var llamadas = 0;
      final mock = MockClient((req) async {
        llamadas++;
        return _json(_pagina([_plan(maxUsers: llamadas == 1 ? null : 20)]), 200);
      });

      await tester.pumpWidget(
        MaterialApp(home: PlansScreen(client: ApiClient(httpClient: mock))),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      final refreshIndicator =
          tester.widget<RefreshIndicator>(find.byType(RefreshIndicator));
      await refreshIndicator.onRefresh();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tester.takeException(), isNull);
      expect(llamadas, greaterThanOrEqualTo(2));
    });
  });
}
