/// Característica general 5 — Pedir el reporte hablando, en el móvil.
///
///     flutter test test/reporting_voz_test.dart
///
/// El micrófono no se prueba: en el entorno de pruebas no hay reconocedor, así
/// que el dictado se inyecta ya transcrito con [_DictadoFalso]. Lo que se
/// prueba es lo que importa del lado del teléfono:
///
/// - que lo entendido quede **marcado en el formulario** y no se ejecute solo;
/// - que lo que el backend no pudo resolver se vea;
/// - que sin reconocimiento disponible el botón no aparezca y el formulario
///   siga armándose a mano.
///
/// Qué se entiende de cada frase se prueba en el backend
/// (`tests/test_caracteristica_5_voz.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/theme/theme.dart';
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
        {'code': 'phone', 'label': 'Teléfono', 'kind': 'text', 'choices': null},
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

/// Un dictado que no toca el micrófono: entrega el texto que se le dio.
class _DictadoFalso implements DictadoDeVoz {
  _DictadoFalso({required this.texto, this.disponible = true});

  final String texto;
  final bool disponible;
  bool soltado = false;

  @override
  Future<bool> preparar() async => disponible;

  @override
  String get motivo => disponible ? '' : 'Este teléfono no puede dictar.';

  @override
  bool get escuchando => false;

  @override
  Future<void> empezar({
    required void Function(String texto) alCambiar,
    required void Function(String texto) alTerminar,
  }) async {
    alCambiar(texto.split(' ').first);
    alTerminar(texto);
  }

  @override
  Future<void> terminar() async {}

  @override
  void soltar() => soltado = true;
}

MockClient _mock({
  required Map<String, dynamic> interpretacion,
  void Function(Map<String, dynamic> cuerpo)? alInterpretar,
  void Function()? alEjecutar,
}) {
  return MockClient((req) async {
    if (req.url.path.endsWith('/reporting/datasets/')) {
      return _json(_catalogo, 200);
    }
    if (req.url.path.endsWith('/reporting/interpret/')) {
      alInterpretar?.call(jsonDecode(req.body) as Map<String, dynamic>);
      return _json(interpretacion, 200);
    }
    alEjecutar?.call();
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

Future<void> _abrir(
  WidgetTester tester,
  MockClient mock,
  DictadoDeVoz dictado,
) async {
  tester.view.physicalSize = const Size(1200, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      // **Con el tema de la aplicación, no con el de Material por omisión.**
      // El tema propio da a los botones ancho completo (`Size.fromHeight`), y
      // un botón así dentro de una fila pide ancho infinito y deja la pantalla
      // entera en blanco. Con el tema por omisión la prueba pasaba y el
      // teléfono no mostraba nada: es el defecto que apareció en el Xiaomi el
      // 05/10.
      theme: AppTheme.light,
      home: ReportsScreen(
        client: ApiClient(httpClient: mock),
        dictado: dictado,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('lo dictado queda marcado en el formulario', (tester) async {
    Map<String, dynamic>? enviado;
    await _abrir(
      tester,
      _mock(
        interpretacion: const {
          'understood': true,
          'definition': {
            'dataset': 'patients',
            'columns': ['full_name', 'phone'],
            'filters': [
              {'field': 'sex', 'operator': 'eq', 'value': 'F'},
            ],
            'order_by': [],
            'format': 'json',
          },
          'spoken_summary': 'Pacientes: Nombre, Teléfono · Sexo es Femenino',
          'unresolved': <String>[],
          'generated_by': 'gemini',
        },
        alInterpretar: (cuerpo) => enviado = cuerpo,
      ),
      _DictadoFalso(texto: 'pacientes mujeres con nombre y teléfono'),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Hablar'));
    await tester.pumpAndSettle();

    // Viajó el texto, no audio.
    expect(enviado?['text'], 'pacientes mujeres con nombre y teléfono');
    expect(enviado?['dataset'], 'patients');

    // Y quedó marcado en los mismos controles que se usan a mano.
    expect(find.text('Columnas (2)'), findsOneWidget);
    expect(find.textContaining('Entendí:'), findsOneWidget);
    expect(find.text('Sexo es Femenino'), findsOneWidget);
  });

  testWidgets('hablar no genera el reporte: hay que confirmar', (tester) async {
    var ejecutado = false;
    await _abrir(
      tester,
      _mock(
        interpretacion: const {
          'understood': true,
          'definition': {
            'dataset': 'patients',
            'columns': ['full_name'],
            'filters': <Map<String, dynamic>>[],
            'order_by': [],
            'format': 'json',
          },
          'spoken_summary': 'Pacientes: Nombre',
          'unresolved': <String>[],
          'generated_by': 'gemini',
        },
        alEjecutar: () => ejecutado = true,
      ),
      _DictadoFalso(texto: 'pacientes'),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Hablar'));
    await tester.pumpAndSettle();

    expect(ejecutado, isFalse, reason: 'la voz propone, no ejecuta');
  });

  testWidgets('lo que no se pudo resolver se muestra', (tester) async {
    await _abrir(
      tester,
      _mock(
        interpretacion: const {
          'understood': true,
          'definition': {
            'dataset': 'patients',
            'columns': ['full_name'],
            'filters': <Map<String, dynamic>>[],
            'order_by': [],
            'format': 'json',
          },
          'spoken_summary': 'Pacientes: Nombre',
          'unresolved': ['No hay una columna «obra social» en Pacientes.'],
          'generated_by': 'gemini',
        },
      ),
      _DictadoFalso(texto: 'pacientes con nombre y obra social'),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Hablar'));
    await tester.pumpAndSettle();

    // La frase dictada también se muestra, así que se busca el aviso exacto.
    expect(
      find.text('· No hay una columna «obra social» en Pacientes.'),
      findsOneWidget,
    );
  });

  testWidgets('cuando no se entiende, se dice y no se cambia el formulario', (
    tester,
  ) async {
    await _abrir(
      tester,
      _mock(
        interpretacion: const {
          'understood': false,
          'definition': null,
          'spoken_summary': 'No reconocí sobre qué querés el reporte.',
          'unresolved': <String>[],
          'generated_by': 'gemini',
        },
      ),
      _DictadoFalso(texto: 'las ventas del mes'),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Hablar'));
    await tester.pumpAndSettle();

    expect(
      find.text('No reconocí sobre qué querés el reporte.'),
      findsOneWidget,
    );
    // El formulario sigue como estaba: las columnas por omisión del catálogo.
    expect(find.text('Columnas (2)'), findsOneWidget);
  });

  testWidgets('sin reconocimiento disponible, el botón no aparece', (
    tester,
  ) async {
    await _abrir(
      tester,
      _mock(interpretacion: const {}),
      _DictadoFalso(texto: 'pacientes', disponible: false),
    );

    expect(find.widgetWithText(FilledButton, 'Hablar'), findsNothing);
    // Y el constructor sigue entero.
    expect(find.text('Columnas (2)'), findsOneWidget);
  });

  testWidgets('al salir de la pantalla se suelta el micrófono', (tester) async {
    final dictado = _DictadoFalso(texto: 'pacientes');
    await _abrir(tester, _mock(interpretacion: const {}), dictado);

    await tester.pumpWidget(const MaterialApp(home: SizedBox()));
    await tester.pumpAndSettle();

    expect(dictado.soltado, isTrue);
  });
}
