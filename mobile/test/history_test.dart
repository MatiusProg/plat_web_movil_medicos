/// Pruebas de US-08 — antecedentes del paciente (móvil).
///
///     flutter test test/history_test.dart
///
/// Lo que se prueba acá es lo del móvil: que la severidad sólo se pida en las
/// alergias, que la leyenda de "declarado, no diagnosticado" esté a la vista, y
/// que cambiar de persona en el selector de US-07 recargue la lista. Las reglas
/// de acceso —quién puede leer la ficha de quién— se prueban en el backend, en
/// `tests/test_us08.py`.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/history/history_api.dart';
import 'package:mobile/features/history/history_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _antecedente(
  String id,
  String descripcion, {
  String kind = 'allergy',
  String kindLabel = 'Alergia',
  String severity = 'severe',
  String severityLabel = 'Grave',
}) =>
    {
      'id': id,
      'patient': 't1',
      'kind': kind,
      'kind_label': kindLabel,
      'description': descripcion,
      'severity': severity,
      'severity_label': severityLabel,
      'source': 'self_reported',
      'recorded_at': '2026-09-06',
      'is_active': true,
    };

const _opciones = [
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
];

Map<String, dynamic> _pagina(List<Map<String, dynamic>> results) =>
    {'count': results.length, 'next': null, 'previous': null, 'results': results};

void _pantallaGrande(WidgetTester tester) {
  tester.view.physicalSize = const Size(1200, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  group('registrarAntecedente', () {
    test('no manda severidad cuando el tipo no es una alergia', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(
          _antecedente('h1', 'Metformina',
              kind: 'medication', severity: '', severityLabel: ''),
          201,
        );
      });

      await registrarAntecedente(
        ApiClient(httpClient: mock),
        patientId: 't1',
        kind: 'medication',
        description: 'Metformina',
      );

      final cuerpo = jsonDecode(capturada!.body) as Map<String, dynamic>;
      expect(cuerpo.containsKey('severity'), isFalse);
      expect(cuerpo['patient'], 't1');
    });

    test('manda severidad en las alergias', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_antecedente('h1', 'Penicilina'), 201);
      });

      await registrarAntecedente(
        ApiClient(httpClient: mock),
        patientId: 't1',
        kind: 'allergy',
        description: 'Penicilina',
        severity: 'anaphylactic',
      );

      final cuerpo = jsonDecode(capturada!.body) as Map<String, dynamic>;
      expect(cuerpo['severity'], 'anaphylactic');
    });
  });

  testWidgets('la pantalla agrupa por tipo y avisa que es declarado',
      (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient((req) async {
      if (req.url.path.contains('patient-options')) {
        return _json(_opciones, 200);
      }
      return _json(
        _pagina([
          _antecedente('h1', 'Penicilina'),
          _antecedente('h2', 'Hipertensión',
              kind: 'condition',
              kindLabel: 'Condición crónica',
              severity: '',
              severityLabel: ''),
        ]),
        200,
      );
    });

    await tester.pumpWidget(
      MaterialApp(home: HistoryScreen(client: ApiClient(httpClient: mock))),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.textContaining('No reemplaza al diagnóstico'), findsOneWidget);
    expect(find.text('Alergias'), findsOneWidget);
    expect(find.text('Condiciones crónicas'), findsOneWidget);
    expect(find.text('Penicilina'), findsOneWidget);
    expect(find.text('Grave · declarado el 2026-09-06'), findsOneWidget);
    expect(find.text('Declarado el 2026-09-06'), findsOneWidget);
  });

  testWidgets('la severidad sólo aparece cuando el tipo es alergia',
      (tester) async {
    _pantallaGrande(tester);
    final mock = MockClient((req) async {
      if (req.url.path.contains('patient-options')) {
        return _json(_opciones, 200);
      }
      return _json(_pagina([]), 200);
    });

    await tester.pumpWidget(
      MaterialApp(home: HistoryScreen(client: ApiClient(httpClient: mock))),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    await tester.tap(find.text('Agregar'));
    await tester.pumpAndSettle();

    // Arranca en alergia, así que la severidad está.
    expect(find.text('Qué tan grave es la reacción'), findsOneWidget);

    await tester.tap(find.text('Alergia').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Medicación habitual').last);
    await tester.pumpAndSettle();

    // Una medicación "grave" no significa nada, y el backend la rechaza.
    expect(find.text('Qué tan grave es la reacción'), findsNothing);
  });

  testWidgets('cambiar de persona pide los antecedentes de esa persona',
      (tester) async {
    _pantallaGrande(tester);
    final pedidos = <String>[];
    final mock = MockClient((req) async {
      if (req.url.path.contains('patient-options')) {
        return _json(_opciones, 200);
      }
      pedidos.add(req.url.queryParameters['patient'] ?? '');
      return _json(_pagina([]), 200);
    });

    await tester.pumpWidget(
      MaterialApp(home: HistoryScreen(client: ApiClient(httpClient: mock))),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(pedidos, ['t1']);

    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mateo Ríos · Hijo/a').last);
    await tester.pumpAndSettle();

    expect(pedidos, ['t1', 'd1']);
  });
}
