/// Característica general 5 — Descargar un reporte en el móvil y abrirlo.
///
///     flutter test test/reporting_descarga_test.dart
///
/// Pedido de Luis el 06/10/26: «que se descargue cualquier reporte generado,
/// que aparezca como descargado y se pueda abrir». Hasta entonces el móvil
/// sólo lo mandaba por correo.
///
/// El disco y la aplicación que abre el archivo se inyectan: lo que se prueba
/// es que lo guardado sean **los bytes exactos** que mandó el servidor (un
/// Excel decodificado y vuelto a armar queda roto), que aparezca en
/// «Descargados» y que «Abrir» pida abrir esa ruta.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/files/archivos.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/reporting/reporting_api.dart';
import 'package:mobile/features/reporting/reports_screen.dart';
import 'package:mobile/features/reporting/voice_input.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

const _catalogo = {
  'datasets': [
    {
      'code': 'patients',
      'label': 'Pacientes',
      'description': 'El padrón de la organización.',
      'columns': [
        {'code': 'full_name', 'label': 'Nombre', 'kind': 'text', 'choices': null},
        {'code': 'document', 'label': 'Documento', 'kind': 'text', 'choices': null},
      ],
      'filters': [],
      'default_columns': ['full_name', 'document'],
    },
  ],
  'formats': ['csv', 'xlsx', 'html', 'pdf'],
  'max_rows': 5000,
};

// Los primeros bytes de un .xlsx (es un ZIP) más uno que no es UTF-8 válido:
// si algo en el camino los decodificara como texto, no volverían iguales.
final _excel = <int>[0x50, 0x4B, 0x03, 0x04, 0xFF, 0x00, 0x9C, 0x10];

class _DictadoApagado implements DictadoDeVoz {
  @override
  Future<bool> preparar() async => false;
  @override
  String get motivo => '';
  @override
  bool get escuchando => false;
  @override
  Future<void> empezar({
    required void Function(String texto) alCambiar,
    required void Function(String texto) alTerminar,
  }) async {}
  @override
  Future<void> terminar() async {}
  @override
  void soltar() {}
}

class _GuardadoFalso implements GuardadoDeArchivos {
  final guardados = <String, List<int>>{};

  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    guardados[nombre] = bytes;
    return '/storage/emulated/0/Download/$nombre';
  }
}

class _AbridorFalso implements AbridorDeArchivos {
  _AbridorFalso({this.problema});

  final String? problema;
  final abiertos = <String>[];

  @override
  Future<String?> abrir(String ruta) async {
    abiertos.add(ruta);
    return problema;
  }
}

MockClient _mock({
  void Function(Map<String, dynamic> cuerpo)? alExportar,
  http.Response? respuestaExportar,
}) {
  return MockClient((req) async {
    if (req.url.path.endsWith('/reporting/datasets/')) {
      return _json(_catalogo, 200);
    }
    final cuerpo = jsonDecode(req.body) as Map<String, dynamic>;
    if (cuerpo['format'] != 'json') {
      alExportar?.call(cuerpo);
      return respuestaExportar ??
          http.Response.bytes(_excel, 200, headers: {
            'content-type':
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'content-disposition': 'attachment; filename="pacientes.xlsx"',
          });
    }
    return _json(const {
      'dataset': 'patients',
      'title': 'Pacientes',
      'columns': [
        {'code': 'full_name', 'label': 'Nombre', 'kind': 'text'},
      ],
      'rows': [
        ['Ana Pérez'],
      ],
      'truncated': false,
    }, 200);
  });
}

Future<void> _abrirPantalla(
  WidgetTester tester,
  MockClient mock, {
  required GuardadoDeArchivos guardado,
  required AbridorDeArchivos abridor,
}) async {
  tester.view.physicalSize = const Size(1200, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      // Con el tema real: sus botones son de ancho completo y dentro de una
      // fila dejaban la pantalla en blanco (ver reporting_voz_test.dart).
      theme: AppTheme.light,
      home: ReportsScreen(
        client: ApiClient(httpClient: mock),
        dictado: _DictadoApagado(),
        guardado: guardado,
        abridor: abridor,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _descargarExcel(WidgetTester tester) async {
  await tester.tap(find.widgetWithText(OutlinedButton, 'Descargar'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Excel'));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('descarga el reporte con los bytes exactos y lo lista', (
    tester,
  ) async {
    Map<String, dynamic>? pedido;
    final guardado = _GuardadoFalso();
    final abridor = _AbridorFalso();
    await _abrirPantalla(
      tester,
      _mock(alExportar: (c) => pedido = c),
      guardado: guardado,
      abridor: abridor,
    );

    await _descargarExcel(tester);

    // Se pidió el mismo reporte de la pantalla, en Excel.
    expect(pedido?['format'], 'xlsx');
    expect(pedido?['dataset'], 'patients');
    expect(pedido?['columns'], ['full_name', 'document']);

    // Guardado tal cual vino, con el momento en el nombre.
    expect(guardado.guardados, hasLength(1));
    final nombre = guardado.guardados.keys.single;
    expect(nombre, matches(RegExp(r'^pacientes-\d{8}-\d{4}\.xlsx$')));
    expect(guardado.guardados[nombre], _excel);

    // Aparece como descargado...
    expect(find.text('Descargados (1)'), findsOneWidget);
    expect(find.textContaining('Descargado'), findsWidgets);

    // ...y «Abrir» abre ese archivo.
    await tester.tap(find.widgetWithText(TextButton, 'Abrir').first);
    await tester.pumpAndSettle();
    expect(abridor.abiertos, ['/storage/emulated/0/Download/$nombre']);
  });

  testWidgets('si no se puede abrir, lo dice', (tester) async {
    final abridor = _AbridorFalso(problema: 'No hay ninguna aplicación');
    await _abrirPantalla(
      tester,
      _mock(),
      guardado: _GuardadoFalso(),
      abridor: abridor,
    );

    await _descargarExcel(tester);
    await tester.tap(find.widgetWithText(TextButton, 'Abrir').first);
    await tester.pumpAndSettle();

    expect(find.text('No hay ninguna aplicación'), findsOneWidget);
  });

  testWidgets('un error del servidor se muestra y no guarda nada', (
    tester,
  ) async {
    final guardado = _GuardadoFalso();
    await _abrirPantalla(
      tester,
      _mock(
        respuestaExportar: _json(const {
          'detail': 'Tu plan no incluye exportar reportes.',
          'code': 'plan_limit',
        }, 403),
      ),
      guardado: guardado,
      abridor: _AbridorFalso(),
    );

    await _descargarExcel(tester);

    expect(guardado.guardados, isEmpty);
    expect(find.textContaining('Tu plan no incluye exportar'), findsOneWidget);
  });

  test('el nombre lleva el momento y conserva la extensión', () {
    final ahora = DateTime(2026, 10, 6, 1, 7);
    expect(
      nombreDeReporte(
        const ArchivoRecibido(bytes: [], nombre: 'pacientes.xlsx'),
        dataset: 'patients',
        format: 'xlsx',
        ahora: ahora,
      ),
      'pacientes-20261006-0107.xlsx',
    );
    // Sin nombre del servidor, sale del conjunto y el formato.
    expect(
      nombreDeReporte(
        const ArchivoRecibido(bytes: []),
        dataset: 'patients',
        format: 'pdf',
        ahora: ahora,
      ),
      'patients-20261006-0107.pdf',
    );
  });
}
