/// Característica general 5 — El constructor de reportes en el móvil.
///
///     flutter test test/reporting_test.dart
///
/// Lo que se prueba es lo del teléfono: que el formulario se arme **con lo que
/// dice el catálogo** y no con campos escritos a mano, que la definición que
/// sale hacia `run/` sea la que la persona eligió, y que un error del servidor
/// no se convierta en una tabla vacía que parece un reporte sin filas. Lo que
/// devuelve cada conjunto se prueba en el backend.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/reporting/reporting_api.dart';
import 'package:mobile/features/reporting/reports_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

/// El catálogo tal como lo devuelve `GET /api/reporting/datasets/`.
const _catalogo = {
  'datasets': [
    {
      'code': 'patients',
      'label': 'Pacientes',
      'description': 'El padrón de la organización.',
      'columns': [
        {
          'code': 'full_name',
          'label': 'Nombre',
          'kind': 'text',
          'choices': null,
        },
        {
          'code': 'document',
          'label': 'Documento',
          'kind': 'text',
          'choices': null,
        },
        {
          'code': 'sex',
          'label': 'Sexo',
          'kind': 'choice',
          'choices': [
            {'value': 'M', 'label': 'Masculino'},
            {'value': 'F', 'label': 'Femenino'},
          ],
        },
      ],
      'filters': [
        {
          'code': 'sex',
          'label': 'Sexo',
          'kind': 'choice',
          'choices': [
            {'value': 'M', 'label': 'Masculino'},
            {'value': 'F', 'label': 'Femenino'},
          ],
          'operators': ['eq', 'in'],
        },
      ],
      'default_columns': ['full_name', 'document'],
    },
  ],
  'formats': ['csv', 'xlsx', 'html', 'pdf'],
  'max_rows': 5000,
};

const _resultado = {
  'dataset': 'patients',
  'title': 'Pacientes',
  'columns': [
    {'code': 'full_name', 'label': 'Nombre', 'kind': 'text'},
    {'code': 'document', 'label': 'Documento', 'kind': 'text'},
  ],
  'rows': [
    ['Ana Pérez', '1234567'],
    ['Juan Gómez', '7654321'],
  ],
  'truncated': false,
};

/// Contesta el catálogo a `datasets/` y `_resultado` a `run/`, y guarda el
/// último cuerpo enviado para poder mirarlo.
MockClient _mockNormal(void Function(Map<String, dynamic>) alEjecutar) {
  return MockClient((req) async {
    if (req.url.path.endsWith('/reporting/datasets/')) {
      return _json(_catalogo, 200);
    }
    alEjecutar(jsonDecode(req.body) as Map<String, dynamic>);
    return _json(_resultado, 200);
  });
}

Future<void> _abrir(WidgetTester tester, MockClient mock) async {
  tester.view.physicalSize = const Size(1200, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      home: ReportsScreen(client: ApiClient(httpClient: mock)),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('lectura del catálogo', () {
    test('arma los conjuntos con sus columnas, filtros y operadores', () async {
      final mock = MockClient((_) async => _json(_catalogo, 200));
      final catalogo = await listarConjuntos(ApiClient(httpClient: mock));

      expect(catalogo.maxRows, 5000);
      expect(catalogo.formats, ['csv', 'xlsx', 'html', 'pdf']);

      final pacientes = catalogo.datasets.single;
      expect(pacientes.label, 'Pacientes');
      expect(pacientes.defaultColumns, ['full_name', 'document']);
      expect(pacientes.columns.length, 3);

      final sexo = pacientes.filters.single;
      expect(sexo.kind, 'choice');
      expect(sexo.operators, ['eq', 'in']);
      // El orden de las opciones es el del backend, no alfabético.
      expect(sexo.choices.map((o) => o.label), ['Masculino', 'Femenino']);
    });

    test('las filas del resultado llegan alineadas con las columnas', () {
      final resultado = ResultadoDeReporte.fromJson(
        Map<String, dynamic>.from(_resultado),
      );

      expect(resultado.columns.map((c) => c.label), ['Nombre', 'Documento']);
      expect(resultado.rows.first, ['Ana Pérez', '1234567']);
      expect(resultado.truncated, isFalse);
    });
  });

  testWidgets('se abre con el primer conjunto y sus columnas por omisión', (
    tester,
  ) async {
    await _abrir(tester, _mockNormal((_) {}));

    expect(find.text('Pacientes'), findsWidgets);
    expect(find.text('El padrón de la organización.'), findsOneWidget);
    // `default_columns` son dos de las tres.
    expect(find.text('Columnas (2)'), findsOneWidget);
    expect(find.text('Sin criterios: entran todas las filas.'), findsOneWidget);
  });

  testWidgets('ejecutar manda las columnas elegidas y muestra la tabla', (
    tester,
  ) async {
    Map<String, dynamic>? enviado;
    await _abrir(tester, _mockNormal((cuerpo) => enviado = cuerpo));

    // Se agrega la tercera columna, que no venía por omisión.
    await tester.tap(find.widgetWithText(FilterChip, 'Sexo'));
    await tester.pumpAndSettle();
    expect(find.text('Columnas (3)'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Ejecutar'));
    await tester.pumpAndSettle();

    expect(enviado, isNotNull);
    expect(enviado!['dataset'], 'patients');
    // En el orden del catálogo, no en el que se fueron tocando.
    expect(enviado!['columns'], ['full_name', 'document', 'sex']);
    expect(enviado!['format'], 'json');

    expect(find.text('Ana Pérez'), findsOneWidget);
    expect(find.text('7654321'), findsOneWidget);
    expect(find.text('2 filas.'), findsOneWidget);
  });

  testWidgets('un criterio viaja como campo, operador y valor', (tester) async {
    Map<String, dynamic>? enviado;
    await _abrir(tester, _mockNormal((cuerpo) => enviado = cuerpo));

    await tester.tap(find.widgetWithText(TextButton, 'Agregar'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, 'Agregar criterio'));
    await tester.pumpAndSettle();

    // Se lee con las etiquetas, no con los códigos.
    expect(find.text('Sexo es Masculino'), findsOneWidget);

    await tester.tap(find.widgetWithText(FilledButton, 'Ejecutar'));
    await tester.pumpAndSettle();

    expect(enviado!['filters'], [
      {'field': 'sex', 'operator': 'eq', 'value': 'M'},
    ]);
  });

  testWidgets('sin columnas no se puede ejecutar', (tester) async {
    await _abrir(tester, _mockNormal((_) {}));

    await tester.tap(find.widgetWithText(FilterChip, 'Nombre'));
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilterChip, 'Documento'));
    await tester.pumpAndSettle();

    expect(find.text('Elegí al menos una columna.'), findsOneWidget);
    final boton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Ejecutar'),
    );
    expect(boton.onPressed, isNull);
  });

  testWidgets('un error del servidor se muestra y no finge un reporte vacío', (
    tester,
  ) async {
    await _abrir(
      tester,
      MockClient((req) async {
        if (req.url.path.endsWith('/reporting/datasets/')) {
          return _json(_catalogo, 200);
        }
        return _json({
          'code': 'columna_desconocida',
          'detail': 'La columna «sex» no existe en este conjunto.',
        }, 400);
      }),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Ejecutar'));
    await tester.pumpAndSettle();

    expect(find.textContaining('no existe en este conjunto'), findsOneWidget);
    expect(find.byType(DataTable), findsNothing);
  });
}
