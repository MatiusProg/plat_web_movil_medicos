/// Pruebas de US-44 — suscripciones (móvil).
///
///     flutter test test/subscriptions_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/plans/plans_api.dart';
import 'package:mobile/features/subscriptions/change_plan_screen.dart';
import 'package:mobile/features/subscriptions/subscriptions_api.dart';
import 'package:mobile/features/subscriptions/subscriptions_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _pagina(List<Map<String, dynamic>> results) =>
    {'count': results.length, 'next': null, 'previous': null, 'results': results};

Map<String, dynamic> _suscripcion() => {
      'id': 's1', 'organization': 'o1', 'organization_name': 'Centro Demo',
      'organization_slug': 'demo', 'plan': 'p1', 'plan_code': 'basic',
      'plan_name': 'Básico', 'starts_at': '2026-01-01', 'ends_at': null,
      'status': 'active', 'change_reason': '', 'assigned_by': 'u1',
      'assigned_by_email': 'super@plataforma.local', 'created_at': '2026-01-01T10:00:00Z',
    };

Subscription _suscripcionActual() => Subscription.fromJson(_suscripcion());

void main() {
  group('assignPlan', () {
    test('manda el body correcto', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_suscripcion(), 201);
      });

      await assignPlan(
        ApiClient(httpClient: mock),
        organizationId: 'o1',
        planId: 'p2',
        startsAt: '2026-02-01',
        changeReason: 'Cambio de plan',
      );

      final enviado = jsonDecode(capturada!.body);
      expect(enviado, {
        'organization_id': 'o1',
        'plan_id': 'p2',
        'starts_at': '2026-02-01',
        'change_reason': 'Cambio de plan',
      });
    });
  });

  group('organizationSubscriptionHistory', () {
    test('desenvuelve la paginación del backend', () async {
      final mock = MockClient((req) async => _json(_pagina([_suscripcion()]), 200));

      final historial =
          await organizationSubscriptionHistory(ApiClient(httpClient: mock), 'o1');

      expect(historial, hasLength(1));
      expect(historial.single.organizationName, 'Centro Demo');
    });
  });

  group('SubscriptionsScreen', () {
    testWidgets('renderiza la tarjeta con sus dos botones sin romper el layout',
        (tester) async {
      // Esta prueba existe porque la anterior (sólo `ChangePlanScreen`) no
      // hubiera detectado el bug real que apareció en el emulador: un
      // `FilledButton` dentro de un `Row` sin acotar su `minimumSize` -el
      // tema global le pone `Size.fromHeight(52)`, ancho infinito, pensado
      // para un botón solo en una columna a todo el ancho- revienta el
      // layout con "BoxConstraints forces an infinite width" apenas se
      // pinta la pantalla, no al tocar el botón.
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mock = MockClient((req) async => _json(_pagina([_suscripcion()]), 200));

      await tester.pumpWidget(
        MaterialApp(
          home: SubscriptionsScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tester.takeException(), isNull);
      expect(find.text('Centro Demo'), findsOneWidget);
      expect(find.widgetWithText(TextButton, 'Historial'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Cambiar plan'), findsOneWidget);
    });

    testWidgets('el pull-to-refresh no revienta y trae el plan nuevo',
        (tester) async {
      // El bug real encontrado en vivo: `setState(() => _futuro = futuro)`
      // devuelve el valor de la propia asignación (el Future), y Flutter
      // revienta con "setState() callback argument returned a Future" ANTES
      // de marcar el widget para reconstruir. El backend sí guardaba el
      // plan nuevo (confirmado por curl y por la base), pero la pantalla se
      // quedaba pintando el Future viejo -"Básico"- para siempre. La prueba
      // de arriba nunca lo detectó porque sólo cubre la primera carga.
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      var llamadas = 0;
      final mock = MockClient((req) async {
        llamadas++;
        final suscripcion = llamadas == 1
            ? _suscripcion()
            : {..._suscripcion(), 'plan_name': 'Pro', 'plan_code': 'pro'};
        return _json(_pagina([suscripcion]), 200);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: SubscriptionsScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.widgetWithText(Chip, 'Básico'), findsOneWidget);

      final refreshIndicator =
          tester.widget<RefreshIndicator>(find.byType(RefreshIndicator));
      await refreshIndicator.onRefresh();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tester.takeException(), isNull);
      expect(find.widgetWithText(Chip, 'Pro'), findsOneWidget);
      expect(find.widgetWithText(Chip, 'Básico'), findsNothing);
    });
  });

  group('ChangePlanScreen', () {
    testWidgets('un 400 con plan_id se muestra como error de campo', (tester) async {
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mock = MockClient((req) async {
        if (req.method == 'GET') {
          return _json(
            _pagina([
              {
                'id': 'p2', 'code': 'pro', 'name': 'Plan Pro', 'description': '',
                'monthly_price': '199.00', 'currency': 'BOB',
                'max_branches': null, 'max_users': null, 'max_practitioners': null,
                'max_appointments_month': null, 'max_ai_queries_month': null,
                'storage_mb': null, 'is_active': true,
              },
            ]),
            200,
          );
        }
        return _json(
          {'code': 'validacion', 'plan_id': ['Ese plan ya es el vigente de esta organización.']},
          400,
        );
      });

      await tester.pumpWidget(
        MaterialApp(
          home: ChangePlanScreen(
            suscripcionActual: _suscripcionActual(),
            client: ApiClient(httpClient: mock),
          ),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      await tester.tap(find.byType(DropdownButtonFormField<Plan>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Plan Pro — 199.00 BOB/mes').last);
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Confirmar cambio'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(
        find.text('Ese plan ya es el vigente de esta organización.'),
        findsOneWidget,
      );
    });
  });
}
