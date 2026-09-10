/// Pruebas de US-43 — organizaciones (móvil).
///
///     flutter test test/organizations_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/organizations/organizations_api.dart';
import 'package:mobile/features/organizations/organizations_screen.dart';
import 'package:mobile/features/organizations/register_organization_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _organizacion({String status = 'active', bool conPlan = true}) => {
      'id': 'o1',
      'slug': 'demo',
      'name': 'Centro Demo',
      'legal_name': 'Centro Demo SRL',
      'tax_id': '1234',
      'contact_email': 'contacto@demo.test',
      'city': 'Santa Cruz',
      'status': status,
      'current_plan':
          conPlan ? {'code': 'basic', 'name': 'Básico', 'starts_at': '2026-01-01'} : null,
    };

Map<String, dynamic> _pagina(List<Map<String, dynamic>> results) =>
    {'count': results.length, 'next': null, 'previous': null, 'results': results};

Map<String, dynamic> _altaExitosa() => {
      ..._organizacion(),
      'admin': {
        'id': 'u1',
        'email': 'admin@demo.test',
        'role': 'org_admin',
        'temporary_password': 'clave-temporal-123',
      },
    };

void main() {
  group('registerOrganization', () {
    test('manda el body exacto, con el sub-objeto admin', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_altaExitosa(), 201);
      });

      final creada = await registerOrganization(
        ApiClient(httpClient: mock),
        slug: 'demo',
        name: 'Centro Demo',
        legalName: 'Centro Demo SRL',
        taxId: '1234',
        contactEmail: 'contacto@demo.test',
        contactPhone: '',
        address: '',
        city: 'Santa Cruz',
        planCode: 'basic',
        adminEmail: 'admin@demo.test',
        adminFirstName: 'Admin',
        adminLastName: 'Demo',
        adminDocumentNumber: '999',
        adminPhone: '',
      );

      final enviado = jsonDecode(capturada!.body);
      expect(enviado['slug'], 'demo');
      expect(enviado['plan_code'], 'basic');
      expect(enviado['admin']['email'], 'admin@demo.test');
      expect(enviado['admin']['document_number'], '999');
      expect(creada.admin.temporaryPassword, 'clave-temporal-123');
      expect(creada.organization.slug, 'demo');
    });
  });

  group('OrganizationsScreen', () {
    testWidgets('muestra estado y plan de cada organización', (tester) async {
      tester.view.physicalSize = const Size(1200, 2400);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mock = MockClient(
        (req) async => _json(_pagina([_organizacion(status: 'suspended')]), 200),
      );

      await tester.pumpWidget(
        MaterialApp(
          home: OrganizationsScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Centro Demo'), findsOneWidget);
      expect(find.text('Suspendida'), findsOneWidget);
      expect(find.text('Básico'), findsOneWidget);
    });
  });

  group('RegisterOrganizationScreen', () {
    testWidgets('tras el alta, se ve la vista de credenciales y no el formulario',
        (tester) async {
      tester.view.physicalSize = const Size(1200, 3200);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      final mock = MockClient((req) async {
        if (req.method == 'GET') {
          return _json(
            _pagina([
              {
                'id': 'p1', 'code': 'basic', 'name': 'Básico',
                'description': '', 'monthly_price': '99.00', 'currency': 'BOB',
                'max_branches': null, 'max_users': null, 'max_practitioners': null,
                'max_appointments_month': null, 'max_ai_queries_month': null,
                'storage_mb': null, 'is_active': true,
              },
            ]),
            200,
          );
        }
        return _json(_altaExitosa(), 201);
      });

      await tester.pumpWidget(
        MaterialApp(
          home: RegisterOrganizationScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      await tester.enterText(find.widgetWithText(TextFormField, 'Nombre comercial'), 'Centro Demo');
      await tester.enterText(find.widgetWithText(TextFormField, 'Razón social'), 'Centro Demo SRL');
      await tester.enterText(find.widgetWithText(TextFormField, 'Identificador'), 'demo');
      await tester.enterText(find.widgetWithText(TextFormField, 'NIT'), '1234');
      await tester.enterText(
        find.widgetWithText(TextFormField, 'Correo de contacto'),
        'contacto@demo.test',
      );

      await tester.tap(find.byType(DropdownButtonFormField<String>));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Básico — 99.00 BOB/mes').last);
      await tester.pumpAndSettle();

      await tester.enterText(find.widgetWithText(TextFormField, 'Nombres'), 'Admin');
      await tester.enterText(find.widgetWithText(TextFormField, 'Apellidos'), 'Demo');
      await tester.enterText(find.widgetWithText(TextFormField, 'Correo'), 'admin@demo.test');
      await tester.enterText(find.widgetWithText(TextFormField, 'Documento'), '999');

      await tester.tap(find.widgetWithText(FilledButton, 'Registrar organización'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Copiá la contraseña ahora'), findsOneWidget);
      expect(find.text('clave-temporal-123'), findsOneWidget);
      expect(find.text('Registrar organización'), findsNothing);
    });
  });

  group('OrganizationsScreen pull-to-refresh', () {
    testWidgets('no revienta y trae datos nuevos', (tester) async {
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
        return _json(
          _pagina([_organizacion(status: llamadas == 1 ? 'active' : 'suspended')]),
          200,
        );
      });

      await tester.pumpWidget(
        MaterialApp(
          home: OrganizationsScreen(client: ApiClient(httpClient: mock)),
        ),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(find.text('Activa'), findsOneWidget);

      final refreshIndicator =
          tester.widget<RefreshIndicator>(find.byType(RefreshIndicator));
      await refreshIndicator.onRefresh();
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 100));

      expect(tester.takeException(), isNull);
      expect(find.text('Suspendida'), findsOneWidget);
    });
  });
}
