/// Pruebas del armazón de la pantalla del asistente (US-31 / US-34, móvil).
///
///     flutter test test/assistant_test.dart
///
/// Lo que se prueba es lo del móvil: que se lea la respuesta aunque el
/// endpoint use nombres alternativos, que una urgencia no ofrezca reservar y
/// que un error nunca se convierta en una respuesta inventada. Lo que responde
/// el asistente —y el aislamiento entre organizaciones— se prueba en el
/// backend, junto con el endpoint.
///
/// US-33: que los horarios salgan de `slots/`, que tocar uno no reserve hasta
/// confirmar en la hoja, que la reserva vaya por `/assistant/book/` y que un
/// `409` o una urgencia se traten como corresponde.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
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
    test('lee el contrato real del endpoint', () {
      // Tal cual lo devuelve `backend/assistant/views.py`.
      final r = AssistantReply.fromJson({
        'emergency': false,
        'answer': 'Te conviene Cardiología.',
        'generated_by': 'gemini',
        'specialty': {'id': 's1', 'name': 'Cardiología', 'similarity': 0.71},
        'alternatives': [
          {'id': 's2', 'name': 'Medicina General', 'similarity': 0.55},
        ],
        'fragments': [
          {
            'id': 'f1',
            'text': 'Cardiología atiende hipertensión.',
            'source_type': 'specialty',
            'source_id': 's1',
            'source_name': 'Cardiología',
            'similarity': 0.71,
          },
        ],
        'retrieval': {'embedding_model': 'local'},
      });

      expect(r.answer, 'Te conviene Cardiología.');
      expect(r.specialtyId, 's1');
      expect(r.specialtyName, 'Cardiología');
      expect(r.fragments.single.text, 'Cardiología atiende hipertensión.');
      // `source_name` es como se llama en el endpoint; la pantalla lo muestra
      // como el origen del fragmento.
      expect(r.fragments.single.source, 'Cardiología');
      expect(r.emergency, isFalse);
    });

    test('lee una urgencia del contrato real', () {
      final r = AssistantReply.fromJson({
        'emergency': true,
        'answer': 'Esto puede ser una urgencia.',
        'generated_by': 'regla',
        'specialty': null,
        'alternatives': [],
        'fragments': [],
      });

      expect(r.emergency, isTrue);
      expect(r.specialtyName, isNull);
      expect(r.answer, 'Esto puede ser una urgencia.');
    });

    test('tolera la otra forma: answer objeto y la urgencia en triage', () {
      final r = AssistantReply.fromJson({
        'triage': {'is_emergency': true, 'reasons': [], 'message': ''},
        'answer': {'text': 'Puede ser una urgencia.', 'source': 'template'},
        'specialty': null,
        'fragments': [
          {'content': 'Texto del fragmento.', 'title': 'Cardiología'},
        ],
      });

      expect(r.answer, 'Puede ser una urgencia.');
      expect(r.emergency, isTrue);
      expect(r.fragments.single.text, 'Texto del fragmento.');
      expect(r.fragments.single.source, 'Cardiología');
    });

    test('lee también el contrato que suponía el plan del sprint', () {
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
      return _json({'emergency': false, 'answer': 'ok'}, 200);
    });

    await consultarAsistente(
      ApiClient(httpClient: mock),
      'me duele la cabeza',
      demo: false,
    );

    expect(capturada.method, 'POST');
    expect(capturada.url.path, endsWith('/assistant/suggest/'));
    expect(jsonDecode(capturada.body), {'question': 'me duele la cabeza'});
  });

  testWidgets('muestra la sugerencia con sus fragmentos', (tester) async {
    await _abrir(
      tester,
      MockClient(
        (_) async => _json({
          'emergency': false,
          'answer': 'Te conviene Cardiología.',
          'generated_by': 'gemini',
          'specialty': {'id': 's1', 'name': 'Cardiología', 'similarity': 0.71},
          'fragments': [
            {
              'text': 'Cardiología atiende hipertensión.',
              'source_name': 'Cardiología',
              'similarity': 0.71,
            },
          ],
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
          'emergency': true,
          'answer': 'Puede ser una urgencia.',
          'generated_by': 'regla',
          'specialty': {'id': 's1', 'name': 'Cardiología', 'similarity': 0.71},
          'fragments': [],
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
        return _json({'emergency': false, 'answer': 'Ahora sí.'}, 200);
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

  // ------------------------------------------------------------------------
  //  US-33 — Reserva conversacional
  // ------------------------------------------------------------------------

  group('US-33: lectura', () {
    test('AssistantReply lee booking y tolera que no venga', () {
      final con = AssistantReply.fromJson({
        'answer': 'Te conviene Cardiología.',
        'booking': {
          'available': true,
          'booking_intent': true,
          'specialty': {'id': 's1', 'name': 'Cardiología'},
        },
      });
      expect(con.booking!.available, isTrue);
      expect(con.booking!.bookingIntent, isTrue);
      expect(con.booking!.specialtyId, 's1');
      expect(con.booking!.specialtyName, 'Cardiología');

      final sin = AssistantReply.fromJson({'answer': 'Hola.'});
      expect(sin.booking, isNull);
    });

    test('SlotsReply lee offers, relaxed y la urgencia', () {
      final r = SlotsReply.fromJson(_slots(relaxed: 'mismo_dia'));
      expect(r.relaxed, 'mismo_dia');
      expect(r.offers.single.practitionerName, 'Laura Gómez');
      expect(r.offers.single.branchName, 'Sede Norte');
      expect(r.offers.single.scheduleId, 'h1');
      expect(r.offers.single.start, '2026-10-15T08:00:00-04:00');

      final urgencia = SlotsReply.fromJson({
        ..._slots(),
        'emergency': true,
        'answer': 'Puede ser una urgencia.',
      });
      expect(urgencia.emergency, isTrue);
      expect(urgencia.offers, isEmpty);
    });

    test('pedirTurnos manda specialty y preference a slots/', () async {
      late http.Request capturada;
      await pedirTurnos(
        ApiClient(httpClient: MockClient((req) async {
          capturada = req;
          return _json(_slots(), 200);
        })),
        's1',
        'el jueves por la tarde',
        demo: false,
      );
      expect(capturada.url.path, endsWith('/assistant/slots/'));
      expect(jsonDecode(capturada.body),
          {'specialty': 's1', 'preference': 'el jueves por la tarde'});
    });

    test('reservarDesdeAsistente va a /assistant/book/, nunca a appointments',
        () async {
      late http.Request capturada;
      final turno = SlotsReply.fromJson(_slots()).offers.single;
      await reservarDesdeAsistente(
        ApiClient(httpClient: MockClient((req) async {
          capturada = req;
          return _json(_ficha(), 201);
        })),
        patientId: 't1',
        turno: turno,
        demo: false,
      );
      expect(capturada.url.path, endsWith('/assistant/book/'));
      expect(capturada.url.path, isNot(contains('/appointments/appointments/')));
      expect(jsonDecode(capturada.body), {
        'patient': 't1',
        'practitioner': 'p1',
        'branch': 'b1',
        'schedule': 'h1',
        'starts_at': '2026-10-15T08:00:00-04:00',
      });
    });

    test('en el modo de ejemplo nunca se reserva', () async {
      final turno = SlotsReply.fromJson(_slots()).offers.single;
      var llamadas = 0;
      await expectLater(
        reservarDesdeAsistente(
          ApiClient(httpClient: MockClient((_) async {
            llamadas++;
            return _json(_ficha(), 201);
          })),
          turno: turno,
          demo: true,
        ),
        throwsA(isA<ApiError>()),
      );
      expect(llamadas, 0);
    });
  });

  group('US-33: pantalla', () {
    testWidgets('con intención de reservar los horarios aparecen solos',
        (tester) async {
      final pedidos = <String>[];
      await _abrir(tester, _servidor(pedidos, intencion: true));

      await _preguntar(tester, 'quiero un turno de cardiología el jueves');

      expect(pedidos, contains('/assistant/slots/'));
      expect(find.text('Laura Gómez · Sede Norte'), findsOneWidget);
      expect(find.text('Por la tarde'), findsOneWidget);
    });

    testWidgets('sin intención aparece Ver horarios y busca al tocarlo',
        (tester) async {
      final pedidos = <String>[];
      await _abrir(tester, _servidor(pedidos, intencion: false));

      await _preguntar(tester, 'tengo la presión alta');
      expect(pedidos, isNot(contains('/assistant/slots/')));

      await tester.tap(find.text('Ver horarios'));
      await tester.pumpAndSettle();
      expect(pedidos, contains('/assistant/slots/'));
      expect(find.text('Laura Gómez · Sede Norte'), findsOneWidget);
    });

    testWidgets('tocar un horario no reserva hasta confirmar en la hoja',
        (tester) async {
      _pantallaGrande(tester);
      final pedidos = <String>[];
      await _abrir(tester, _servidor(pedidos, intencion: true));
      await _preguntar(tester, 'quiero un turno de cardiología');

      await tester.tap(find.text('Laura Gómez · Sede Norte'));
      await tester.pumpAndSettle();
      expect(find.text('Reservar ficha'), findsOneWidget);
      expect(pedidos, isNot(contains('/assistant/book/')));

      // Cancelar no reserva nada.
      await tester.tap(find.text('Cancelar'));
      await tester.pumpAndSettle();
      expect(pedidos, isNot(contains('/assistant/book/')));

      await tester.tap(find.text('Laura Gómez · Sede Norte'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Reservar'));
      await tester.pumpAndSettle();

      expect(pedidos, contains('/assistant/book/'));
      expect(pedidos, isNot(contains('/appointments/appointments/')));
      expect(find.text('Ficha reservada'), findsOneWidget);
      expect(find.text('Ir a la ficha'), findsOneWidget);
    });

    testWidgets('un 409 avisa y vuelve a pedir horarios', (tester) async {
      _pantallaGrande(tester);
      final pedidos = <String>[];
      await _abrir(tester, _servidor(pedidos, intencion: true, ocupado: true));
      await _preguntar(tester, 'quiero un turno de cardiología');
      final antes = pedidos.where((p) => p == '/assistant/slots/').length;

      await tester.tap(find.text('Laura Gómez · Sede Norte'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Reservar'));
      await tester.pumpAndSettle();

      expect(find.text('Ese horario se acaba de ocupar. Estos son los que quedan.'),
          findsOneWidget);
      expect(pedidos.where((p) => p == '/assistant/slots/').length, antes + 1);
      expect(find.text('Ficha reservada'), findsNothing);
    });

    testWidgets('una urgencia en los horarios no muestra tarjetas',
        (tester) async {
      final pedidos = <String>[];
      await _abrir(tester, _servidor(pedidos, intencion: true, urgencia: true));
      await _preguntar(tester, 'quiero turno ya, me desmayé');

      expect(find.textContaining('Esto puede ser una urgencia'), findsOneWidget);
      expect(find.text('Laura Gómez · Sede Norte'), findsNothing);
      expect(find.text('Por la tarde'), findsNothing);
    });

    testWidgets('un chip pide horarios con ese texto', (tester) async {
      _pantallaGrande(tester);
      final cuerpos = <Map<String, dynamic>>[];
      await _abrir(tester, _servidor([], intencion: true, alPedirTurnos: cuerpos.add));
      await _preguntar(tester, 'quiero un turno de cardiología');

      await tester.tap(find.text('Por la tarde'));
      await tester.pumpAndSettle();

      expect(cuerpos.last, {'specialty': 's1', 'preference': 'Por la tarde'});
    });
  });
}

void _pantallaGrande(WidgetTester tester) {
  tester.view.physicalSize = const Size(1200, 4000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Map<String, dynamic> _slots({String? relaxed}) => {
  'emergency': false,
  'kind': 'reserva',
  'answer': 'Estos son los próximos horarios de Cardiología.',
  'generated_by': 'regla',
  'specialty': {'id': 's1', 'name': 'Cardiología'},
  'relaxed': relaxed,
  'offers': [
    {
      'practitioner': {'id': 'p1', 'full_name': 'Laura Gómez'},
      'branch': {'id': 'b1', 'name': 'Sede Norte'},
      'schedule': {'id': 'h1'},
      'start': '2026-10-15T08:00:00-04:00',
      'end': '2026-10-15T08:30:00-04:00',
    },
  ],
};

Map<String, dynamic> _ficha() => {
  'id': 'f1',
  'patient': 't1',
  'patient_name': 'Ana Ríos',
  'practitioner': 'p1',
  'practitioner_name': 'Laura Gómez',
  'branch_name': 'Sede Norte',
  'starts_at': '2026-10-15T12:00:00Z',
  'ends_at': '2026-10-15T12:30:00Z',
  'status': 'pending_payment',
};

/// Un servidor de mentira que contesta los cuatro endpoints del flujo.
MockClient _servidor(
  List<String> pedidos, {
  required bool intencion,
  bool ocupado = false,
  bool urgencia = false,
  void Function(Map<String, dynamic> cuerpo)? alPedirTurnos,
}) =>
    MockClient((req) async {
      final ruta = req.url.path.replaceFirst(RegExp(r'^/api'), '');
      pedidos.add(ruta);
      if (ruta.endsWith('/assistant/suggest/')) {
        return _json({
          'emergency': false,
          'answer': 'Te conviene Cardiología.',
          'specialty': {'id': 's1', 'name': 'Cardiología'},
          'fragments': [],
          'booking': {
            'available': true,
            'booking_intent': intencion,
            'specialty': {'id': 's1', 'name': 'Cardiología'},
          },
        }, 200);
      }
      if (ruta.endsWith('/assistant/slots/')) {
        alPedirTurnos?.call(jsonDecode(req.body) as Map<String, dynamic>);
        if (urgencia) {
          return _json({
            'emergency': true,
            'answer': 'Puede ser una urgencia.',
            'generated_by': 'regla',
          }, 200);
        }
        return _json(_slots(), 200);
      }
      if (ruta.endsWith('/assistant/book/')) {
        if (ocupado) {
          return _json({
            'code': 'turno_ocupado',
            'detail': 'Ese horario ya no está libre.',
          }, 409);
        }
        return _json(_ficha(), 201);
      }
      if (ruta.endsWith('/patient-options/')) {
        return _json([
          {
            'id': 't1',
            'full_name': 'Ana Ríos',
            'relationship': '',
            'relationship_label': 'Yo',
            'is_self': true,
            'birth_date': '1990-05-20',
          },
        ], 200);
      }
      return _json({'detail': 'no encontrado'}, 404);
    });
