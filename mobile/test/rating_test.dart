/// Pruebas de US-48 en el móvil — «¿Cómo te atendieron?».
///
///     flutter test test/rating_test.dart
///
/// Lo que se prueba acá es la tarjeta: que se califique tocando estrellas, que
/// la ya calificada muestre «Calificaste con» y «Cambiar» mientras quedan
/// días, y que un error del backend se muestre. Quién puede calificar qué, los
/// 7 días y que el médico no vea nombres se prueban en el backend
/// (`tests/test_us48.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/clinical_record/clinical_record_api.dart';
import 'package:mobile/features/clinical_record/rating_card.dart';

http.Response _json(Object cuerpo, [int estado = 200]) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _rating(int estrellas,
        {String comentario = '', bool editable = true}) =>
    {
      'stars': estrellas,
      'comment': comentario,
      'created_at': '2026-11-19T15:00:00Z',
      'updated_at': '2026-11-19T15:00:00Z',
      'editable_until': '2026-11-26T15:00:00Z',
      'editable': editable,
    };

Future<List<http.Request>> _montar(
  WidgetTester tester, {
  Calificacion? inicial,
  http.Response Function(http.Request)? responder,
}) async {
  final pedidos = <http.Request>[];
  final client = ApiClient(
    httpClient: MockClient((request) async {
      pedidos.add(request);
      if (responder != null) return responder(request);
      final cuerpo = jsonDecode(request.body) as Map<String, dynamic>;
      return _json({
        'rating': _rating(cuerpo['stars'] as int,
            comentario: cuerpo['comment'] as String),
      }, request.method == 'POST' ? 201 : 200);
    }),
  );
  // Con el tema real de la app: su `FilledButton` pide todo el ancho
  // (`Size.fromHeight`), y sin él la prueba no ve que el botón no se dibuja
  // dentro de un `Row` (pasó en el celu el 20/11/26).
  await tester.pumpWidget(MaterialApp(
    theme: AppTheme.light,
    home: Scaffold(
      body: SingleChildScrollView(
        child: TarjetaCalificacion(
          client: client,
          encounterId: 'e1',
          inicial: inicial,
        ),
      ),
    ),
  ));
  return pedidos;
}

void main() {
  test('lee la calificación que viene en el historial', () {
    final a = Atencion.fromJson({
      'id': 'e1',
      'rating': _rating(4, comentario: 'Muy amable.'),
    });
    expect(a.calificacion?.estrellas, 4);
    expect(a.calificacion?.comentario, 'Muy amable.');
    expect(a.calificacion?.editable, isTrue);
    expect(Atencion.fromJson({'id': 'e2', 'rating': null}).calificacion, isNull);
    expect(estrellasEnTexto(3), '★★★☆☆');
  });

  testWidgets('sin calificar: se tocan las estrellas y se envía con POST',
      (tester) async {
    final pedidos = await _montar(tester);
    expect(find.text('¿Cómo te atendieron?'), findsOneWidget);

    // Sin estrellas el botón no hace nada.
    final boton = find.widgetWithText(FilledButton, 'Enviar calificación');
    expect(tester.widget<FilledButton>(boton).onPressed, isNull);

    await tester.tap(find.bySemanticsLabel('4 estrellas: Buena'));
    await tester.pump();
    expect(find.text('Buena'), findsOneWidget);
    await tester.enterText(find.byType(TextField), '  Puntual.  ');
    await tester.tap(boton);
    await tester.pumpAndSettle();

    expect(pedidos.single.method, 'POST');
    expect(pedidos.single.url.path, '/api/encounters/e1/rating/');
    expect(jsonDecode(pedidos.single.body), {'stars': 4, 'comment': 'Puntual.'});
    expect(find.textContaining('Calificaste con'), findsOneWidget);
    expect(find.textContaining('Cambiar'), findsOneWidget);
  });

  testWidgets('ya calificada: «Cambiar» la corrige con PATCH', (tester) async {
    final pedidos = await _montar(
      tester,
      inicial: Calificacion.fromJson(_rating(2, comentario: 'Demoró.')),
    );
    expect(find.textContaining('Calificaste con'), findsOneWidget);
    expect(find.text('«Demoró.»'), findsOneWidget);

    await tester.tap(find.textContaining('Cambiar'));
    await tester.pump();
    await tester.tap(find.bySemanticsLabel('5 estrellas: Muy buena'));
    await tester.pump();
    await tester.tap(find.text('Guardar cambio'));
    await tester.pumpAndSettle();

    expect(pedidos.single.method, 'PATCH');
    expect((jsonDecode(pedidos.single.body) as Map)['stars'], 5);
  });

  testWidgets('pasados los 7 días no ofrece cambiarla', (tester) async {
    await _montar(
      tester,
      inicial: Calificacion.fromJson(_rating(3, editable: false)),
    );
    expect(find.textContaining('Cambiar'), findsNothing);
    expect(find.text('Ya no se puede cambiar.'), findsOneWidget);
  });

  testWidgets('un error del backend se muestra y la tarjeta sigue abierta',
      (tester) async {
    await _montar(
      tester,
      responder: (_) => _json({
        'code': 'already_rated',
        'detail': 'Esta atención ya está calificada. Puedes cambiarla.',
      }, 409),
    );
    await tester.tap(find.bySemanticsLabel('5 estrellas: Muy buena'));
    await tester.pump();
    await tester.tap(find.text('Enviar calificación'));
    await tester.pumpAndSettle();

    expect(find.text('Esta atención ya está calificada. Puedes cambiarla.'),
        findsOneWidget);
    expect(find.text('¿Cómo te atendieron?'), findsOneWidget);
  });
}
