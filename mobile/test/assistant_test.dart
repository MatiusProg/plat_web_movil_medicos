/// Pruebas del armazón de la pantalla del asistente (US-31 / US-34, móvil).
///
///     flutter test test/assistant_test.dart
///
/// Lo que se prueba es lo del móvil: que se lea la respuesta aunque el
/// endpoint use nombres alternativos, que una urgencia no ofrezca reservar y
/// que un error nunca se convierta en una respuesta inventada. Lo que responde
/// el asistente —y el aislamiento entre organizaciones— se prueba en el
/// backend, junto con el endpoint.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/assistant/assistant_api.dart';
import 'package:mobile/features/assistant/assistant_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Future<void> _abrir(WidgetTester tester, MockClient mock) async {
  await tester.pumpWidget(
    MaterialApp(
      home: AssistantScreen(client: ApiClient(httpClient: mock), demo: false),
    ),
  );
}

Future<void> _preguntar(WidgetTester tester, String texto) async {
  await tester.enterText(find.byType(TextField), texto);
  await tester.tap(find.byTooltip('Enviar'));
  await tester.pumpAndSettle();
}

void main() {
  group('lectura de la respuesta', () {
    test('lee el contrato supuesto', () {
      final r = AssistantReply.fromJson({
        'answer': 'Te conviene Cardiología.',
        'specialty': {'id': 's1', 'name': 'Cardiología'},
        'fragments': [
          {'text': 'Cardiología atiende hipertensión.', 'source': 'catálogo'},
        ],
        'emergency': false,
      });

      expect(r.answer, 'Te conviene Cardiología.');
      expect(r.specialtyId, 's1');
      expect(r.specialtyName, 'Cardiología');
      expect(r.fragments.single.source, 'catálogo');
      expect(r.emergency, isFalse);
    });

    test('acepta los nombres alternativos más probables', () {
      final r = AssistantReply.fromJson({
        'reply': 'Consultá en Dermatología.',
        'suggested_specialty': 'Dermatología',
        'sources': ['Dermatología atiende la piel.'],
        'is_emergency': {'reason': 'x'},
      });

      expect(r.answer, 'Consultá en Dermatología.');
      expect(r.specialtyName, 'Dermatología');
      expect(r.specialtyId, isNull);
      expect(r.fragments.single.text, 'Dermatología atiende la piel.');
      expect(r.emergency, isTrue);
    });
  });

  test('manda el mensaje al endpoint del asistente', () async {
    late http.Request capturada;
    final mock = MockClient((req) async {
      capturada = req;
      return _json({'answer': 'ok', 'emergency': false}, 200);
    });

    await consultarAsistente(
      ApiClient(httpClient: mock),
      'me duele la cabeza',
      demo: false,
    );

    expect(capturada.method, 'POST');
    expect(capturada.url.path, endsWith('/assistant/suggest/'));
    expect(jsonDecode(capturada.body), {'message': 'me duele la cabeza'});
  });

  testWidgets('muestra la sugerencia con sus fragmentos', (tester) async {
    await _abrir(
      tester,
      MockClient(
        (_) async => _json({
          'answer': 'Te conviene Cardiología.',
          'specialty': {'id': 's1', 'name': 'Cardiología'},
          'fragments': [
            {'text': 'Cardiología atiende hipertensión.', 'source': 'catálogo'},
          ],
          'emergency': false,
        }, 200),
      ),
    );

    await _preguntar(tester, 'tengo la presión alta');

    expect(find.text('tengo la presión alta'), findsOneWidget);
    expect(find.text('Te conviene Cardiología.'), findsOneWidget);
    expect(find.text('Especialidad sugerida: Cardiología'), findsOneWidget);
    expect(find.text('Ver profesionales'), findsOneWidget);

    await tester.tap(find.text('En qué se basa (1)'));
    await tester.pumpAndSettle();
    expect(find.text('Cardiología atiende hipertensión.'), findsOneWidget);
  });

  testWidgets('una urgencia deriva y no ofrece reservar', (tester) async {
    await _abrir(
      tester,
      MockClient(
        (_) async => _json({
          'answer': 'Puede ser una urgencia.',
          'specialty': {'id': 's1', 'name': 'Cardiología'},
          'fragments': [],
          'emergency': true,
        }, 200),
      ),
    );

    await _preguntar(tester, 'tengo dolor de pecho fuerte');

    expect(find.textContaining('Esto puede ser una urgencia'), findsOneWidget);
    expect(find.text('Ver profesionales'), findsNothing);
    expect(find.textContaining('Especialidad sugerida'), findsNothing);
  });

  testWidgets('si el servidor falla no inventa respuesta y deja reintentar', (
    tester,
  ) async {
    var llamadas = 0;
    await _abrir(
      tester,
      MockClient((_) async {
        llamadas++;
        if (llamadas == 1) return _json({'detail': 'caído'}, 503);
        return _json({'answer': 'Ahora sí.', 'emergency': false}, 200);
      }),
    );

    await _preguntar(tester, 'me duele la garganta');

    expect(find.text('No puedo responder ahora.'), findsOneWidget);
    expect(find.text('El asistente no está disponible.'), findsOneWidget);
    expect(find.textContaining('Especialidad sugerida'), findsNothing);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    expect(llamadas, 2);
    expect(find.text('No puedo responder ahora.'), findsNothing);
    expect(find.text('Ahora sí.'), findsOneWidget);
    // El mensaje del paciente no se duplica al reintentar.
    expect(find.text('me duele la garganta'), findsOneWidget);
  });

  testWidgets('el modo de ejemplo queda rotulado', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: AssistantScreen(demo: true)),
    );

    expect(find.textContaining('MODO EJEMPLO'), findsOneWidget);
  });
}
