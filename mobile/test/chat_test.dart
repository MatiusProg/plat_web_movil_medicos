/// Pruebas de US-47 en el móvil — el chat del paciente con su médico.
///
///     flutter test test/chat_test.dart
///
/// Lo que se prueba acá es la pantalla y el aviso: el cartel de que no es
/// para urgencias, la receta, los mensajes, la derivación cuando el backend
/// la devuelve, el estado cerrado y que tocar el aviso del médico abra el
/// chat. Quién entra a qué conversación se prueba en el backend
/// (`tests/test_us47.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/notifications/push.dart';
import 'package:mobile/features/chat/chat_screen.dart';

const _aviso = 'Este chat es para consultas sobre tu atención. No es para urgencias.';
const _derivacion = 'Ve ahora mismo al servicio de emergencias más cercano.';

http.Response _json(Object cuerpo, [int status = 200]) => http.Response(
      jsonEncode(cuerpo),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _conversacion({
  List<Map<String, dynamic>> mensajes = const [],
  bool abierta = true,
  String? motivo,
}) =>
    {
      'encounter': 'e1',
      'side': 'patient',
      'patient_name': 'Pedro Mamani',
      'practitioner_name': 'Laura Gómez',
      'encounter_date': '2026-11-12T14:00:00Z',
      'signed_at': '2026-11-12T15:00:00Z',
      'closes_at': '2026-11-27T15:00:00Z',
      'can_write': abierta,
      'closed_reason': motivo,
      'window_days': 15,
      'notice': _aviso,
      'prescription': [
        {
          'medication': 'Paracetamol',
          'dose': '500 mg',
          'frequency': 'cada 8 horas',
          'duration': '5 días',
          'instructions': '',
        },
      ],
      'orders': [
        {'kind': 'lab', 'kind_display': 'Laboratorio', 'description': 'Hemograma'},
      ],
      'messages': mensajes,
    };

Map<String, dynamic> _mensaje(String body, {bool mio = true}) => {
      'id': body.hashCode.toString(),
      'side': mio ? 'patient' : 'practitioner',
      'author_name': mio ? 'Pedro Mamani' : 'Laura Gómez',
      'body': body,
      'created_at': '2026-11-12T16:00:00Z',
      'mine': mio,
      'flagged_emergency': false,
    };

/// Monta la pantalla con un backend falso que guarda lo que se escribe.
Future<List<String>> _abrir(
  WidgetTester tester, {
  bool abierta = true,
  String? motivo,
  String? urgencia,
  List<Map<String, dynamic>> iniciales = const [],
}) async {
  final mensajes = [...iniciales];
  final enviados = <String>[];
  final client = ApiClient(
    httpClient: MockClient((request) async {
      if (request.method == 'POST') {
        final body = (jsonDecode(request.body) as Map)['body'] as String;
        enviados.add(body);
        mensajes.add(_mensaje(body));
        return _json({
          'message': _mensaje(body),
          'emergency': urgencia == null ? null : {'message': urgencia},
        }, 201);
      }
      return _json(_conversacion(mensajes: mensajes, abierta: abierta, motivo: motivo));
    }),
  );
  await tester.pumpWidget(MaterialApp(
    home: ChatScreen(
      encounterId: 'e1',
      client: client,
      cadaCuanto: const Duration(hours: 1),
    ),
  ));
  await tester.pumpAndSettle();
  return enviados;
}

void main() {
  testWidgets('muestra que no es para urgencias, la receta y los mensajes',
      (tester) async {
    await _abrir(tester, iniciales: [
      _mensaje('¿Lo tomo antes de comer?'),
      _mensaje('Después de comer.', mio: false),
    ]);
    expect(find.text(_aviso), findsOneWidget);
    expect(find.textContaining('Paracetamol · 500 mg'), findsOneWidget);
    expect(find.textContaining('Laboratorio: Hemograma'), findsOneWidget);
    expect(find.text('¿Lo tomo antes de comer?'), findsOneWidget);
    expect(find.text('Después de comer.'), findsOneWidget);
    expect(find.textContaining('Laura Gómez ·'), findsOneWidget);
    expect(find.textContaining('Tú ·'), findsOneWidget);
  });

  testWidgets('escribe un mensaje y aparece en la conversación', (tester) async {
    final enviados = await _abrir(tester);
    await tester.enterText(find.byType(TextField), '  ¿Puedo tomar ibuprofeno?  ');
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();
    expect(enviados, ['¿Puedo tomar ibuprofeno?']);
    expect(find.text('¿Puedo tomar ibuprofeno?'), findsOneWidget);
    expect(find.byKey(const Key('urgencia')), findsNothing);
  });

  testWidgets('un mensaje vacío no se manda', (tester) async {
    final enviados = await _abrir(tester);
    await tester.enterText(find.byType(TextField), '   ');
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();
    expect(enviados, isEmpty);
  });

  testWidgets('si el backend devuelve una derivación, se muestra antes que nada',
      (tester) async {
    await _abrir(tester, urgencia: _derivacion);
    await tester.enterText(find.byType(TextField), 'Me duele el pecho y no puedo respirar');
    await tester.tap(find.byTooltip('Enviar'));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('urgencia')), findsOneWidget);
    expect(find.text(_derivacion), findsOneWidget);
  });

  testWidgets('cerrada por el médico: sin caja para escribir y con la reserva',
      (tester) async {
    await _abrir(tester, abierta: false, motivo: 'closed');
    expect(find.byType(TextField), findsNothing);
    expect(find.text('El médico cerró esta conversación.'), findsOneWidget);
    expect(find.text('Reservar una ficha nueva'), findsOneWidget);
  });

  testWidgets('vencida la ventana: lo dice con los días', (tester) async {
    await _abrir(tester, abierta: false, motivo: 'expired');
    expect(find.byType(TextField), findsNothing);
    expect(find.textContaining('pasaron 15 días'), findsOneWidget);
  });

  test('el aviso de una respuesta del médico abre el chat de esa atención', () {
    expect(Push.destinoDe({'event': 'chat', 'encounter_id': 'e1'}), 'chat:e1');
    expect(Push.destinoDe({'event': 'chat', 'encounter_id': ''}), isNull);
    expect(Push.destinoDe({'event': 'chat'}), isNull);
    // Los avisos de ficha de US-28 siguen abriendo la ficha.
    expect(Push.destinoDe({'event': 'recordatorio', 'appointment_id': 'f1'}), 'f1');
  });
}
