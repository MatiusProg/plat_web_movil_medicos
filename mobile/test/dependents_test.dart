/// Pruebas de US-07 — pacientes dependientes (móvil).
///
///     flutter test test/dependents_test.dart
///
/// Lo que se prueba acá es lo que sólo existe en el móvil: que el alta mande el
/// cuerpo correcto cuando no hay documento, que el 409 del punto (c) se
/// resuelva preguntando y reenviando con `confirm_link`, y que el selector
/// compartido del punto (h) arranque con el titular elegido. Las reglas de
/// negocio se prueban en el backend, en `tests/test_us07.py`.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/dependents/dependent_form_screen.dart';
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/dependents_screen.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _dependiente(
  String id,
  String nombre, {
  String parentesco = 'child',
  String etiqueta = 'Hijo/a',
  String? documento,
  int? edad,
}) =>
    {
      'id': id,
      'first_name': nombre.split(' ').first,
      'last_name': nombre.split(' ').last,
      'full_name': nombre,
      'relationship': parentesco,
      'relationship_label': etiqueta,
      'document_type': 'CI',
      'document_number': documento,
      'birth_date': '2020-03-15',
      'age': edad,
      'sex': 'M',
    };

void _pantallaGrande(WidgetTester tester) {
  tester.view.physicalSize = const Size(1200, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  group('crearDependiente', () {
    test('sin documento no manda document_number ni document_type', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_dependiente('d1', 'Mateo Ríos'), 201);
      });

      await crearDependiente(
        ApiClient(httpClient: mock),
        const DependienteNuevo(
          firstName: 'Mateo',
          lastName: 'Ríos',
          relationship: 'child',
          documentNumber: '',
          birthDate: '2020-03-15',
        ),
      );

      final cuerpo = jsonDecode(capturada!.body) as Map<String, dynamic>;
      expect(cuerpo.containsKey('document_number'), isFalse);
      expect(cuerpo.containsKey('document_type'), isFalse);
      expect(cuerpo['relationship'], 'child');
      expect(cuerpo.containsKey('confirm_link'), isFalse);
    });

    test('confirmLink agrega confirm_link al cuerpo', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_dependiente('d1', 'José Peña'), 200);
      });

      await crearDependiente(
        ApiClient(httpClient: mock),
        const DependienteNuevo(
          firstName: 'José',
          lastName: 'Peña',
          relationship: 'ward',
          documentNumber: '9001',
        ),
        confirmLink: true,
      );

      final cuerpo = jsonDecode(capturada!.body) as Map<String, dynamic>;
      expect(cuerpo['confirm_link'], isTrue);
      expect(cuerpo['document_number'], '9001');
    });
  });

  testWidgets('el listado vacío explica para qué sirve la pantalla',
      (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient(
      (req) async => _json(
        {'count': 0, 'next': null, 'previous': null, 'results': []},
        200,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(home: DependentsScreen(client: ApiClient(httpClient: mock))),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Todavía no agregaste a nadie'), findsOneWidget);
    expect(find.textContaining('No necesitan tener cuenta propia'),
        findsOneWidget);
  });

  testWidgets('el listado muestra parentesco, edad y documento',
      (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient(
      (req) async => _json(
        {
          'count': 1,
          'next': null,
          'previous': null,
          'results': [
            _dependiente('d1', 'Mateo Ríos', documento: '9001', edad: 6),
          ],
        },
        200,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(home: DependentsScreen(client: ApiClient(httpClient: mock))),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Mateo Ríos'), findsOneWidget);
    expect(find.text('Hijo/a · 6 años · CI 9001'), findsOneWidget);
  });

  testWidgets('la baja avisa que la ficha y el historial no se borran',
      (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient(
      (req) async => _json(
        {
          'count': 1,
          'next': null,
          'previous': null,
          'results': [_dependiente('d1', 'Mateo Ríos')],
        },
        200,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(home: DependentsScreen(client: ApiClient(httpClient: mock))),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    await tester.tap(find.byType(PopupMenuButton<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ya no está a mi cargo'));
    await tester.pumpAndSettle();

    // El botón no dice "Eliminar" y el texto lo explica: la ficha queda.
    expect(find.textContaining('no se borran'), findsOneWidget);
    expect(find.text('Quitar de mi cargo'), findsOneWidget);
    expect(find.text('Eliminar'), findsNothing);
  });

  testWidgets('un documento ya registrado ofrece vincular y reenvía confirmado',
      (tester) async {
    _pantallaGrande(tester);

    final cuerpos = <Map<String, dynamic>>[];
    final mock = MockClient((req) async {
      cuerpos.add(jsonDecode(req.body) as Map<String, dynamic>);
      if (cuerpos.length == 1) {
        return _json(
          {
            'code': 'documento_existente',
            'detail': 'Ya hay una ficha con ese documento.',
            'can_link': true,
          },
          409,
        );
      }
      return _json(_dependiente('d9', 'José Peña'), 200);
    });

    await tester.pumpWidget(
      MaterialApp(
        home: DependentFormScreen(client: ApiClient(httpClient: mock)),
      ),
    );
    await tester.pump();

    await tester.enterText(find.byType(TextFormField).at(0), 'José');
    await tester.enterText(find.byType(TextFormField).at(1), 'Peña');
    await tester.enterText(find.byType(TextFormField).at(2), '9001');
    await tester.tap(find.text('Agregar'));
    await tester.pumpAndSettle();

    expect(find.text('Esa persona ya está registrada'), findsOneWidget);

    await tester.tap(find.text('Es la misma persona'));
    await tester.pumpAndSettle();

    expect(cuerpos.length, 2);
    expect(cuerpos.first.containsKey('confirm_link'), isFalse);
    expect(cuerpos.last['confirm_link'], isTrue);
  });

  testWidgets('el selector arranca con el titular elegido', (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient(
      (req) async => _json(
        [
          {
            'id': 't1',
            'full_name': 'Ana Ríos',
            'relationship': '',
            'relationship_label': 'Yo',
            'is_self': true,
            'birth_date': '1990-05-20',
          },
          {
            'id': 'd1',
            'full_name': 'Mateo Ríos',
            'relationship': 'child',
            'relationship_label': 'Hijo/a',
            'is_self': false,
            'birth_date': '2020-03-15',
          },
        ],
        200,
      ),
    );

    PatientOption? elegido;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PatientSelector(
            client: ApiClient(httpClient: mock),
            onChanged: (opcion) => elegido = opcion,
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    // Avisa de la selección inicial sin que la pantalla que lo usa tenga que
    // repetir la regla de "por omisión, uno mismo".
    expect(elegido, isNotNull);
    expect(elegido!.isSelf, isTrue);
    expect(elegido!.fullName, 'Ana Ríos');
    expect(find.text('Ana Ríos'), findsOneWidget);

    // El dependiente aparece con su parentesco al desplegar: un desplegable
    // sólo dibuja la opción elegida hasta que se lo abre.
    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    expect(find.text('Mateo Ríos · Hijo/a'), findsOneWidget);

    await tester.tap(find.text('Mateo Ríos · Hijo/a').last);
    await tester.pumpAndSettle();
    expect(elegido!.isSelf, isFalse);
    expect(elegido!.relationshipLabel, 'Hijo/a');
  });

  testWidgets('con una sola opción el selector no dibuja un desplegable',
      (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient(
      (req) async => _json(
        [
          {
            'id': 't1',
            'full_name': 'Ana Ríos',
            'relationship': '',
            'relationship_label': 'Yo',
            'is_self': true,
            'birth_date': '1990-05-20',
          },
        ],
        200,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: PatientSelector(
            client: ApiClient(httpClient: mock),
            onChanged: (_) {},
          ),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.byType(DropdownButtonFormField<String>), findsNothing);
    expect(find.text('Ana Ríos'), findsOneWidget);
  });
}
