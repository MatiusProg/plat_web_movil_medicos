// US-51: la preconsulta de la «Experiencia Plus» de una ficha pagada.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/appointments/preconsulta_plus.dart';

Appointment _ficha(String status, DateTime inicio) => Appointment.fromJson({
      'id': 'f1', 'patient': 'p1', 'patient_name': 'Ana Pérez',
      'practitioner': 'pr1', 'practitioner_name': 'Laura Gómez',
      'branch': 'b1', 'branch_name': 'Sede Centro',
      'starts_at': inicio.toUtc().toIso8601String(),
      'ends_at': inicio.add(const Duration(minutes: 30)).toUtc().toIso8601String(),
      'status': status, 'expires_at': null, 'cancelled_at': null,
      'cancellation_reason': '', 'refund_eligible': null, 'rescheduled_from': null,
      'checked_in_at': null, 'attendance_confirmed_at': null,
      'fee': {'amount': '120.00', 'currency': 'BOB'}, 'payment_status': 'succeeded',
    });

http.Response _json(Object c, [int s = 200]) => http.Response(jsonEncode(c), s,
    headers: {'content-type': 'application/json; charset=utf-8'});

Future<List<http.Request>> _abrir(WidgetTester tester, Appointment ficha,
    {Map<String, dynamic> guardado = const {'reason': '', 'questions': ''}}) async {
  final pedidos = <http.Request>[];
  final client = ApiClient(httpClient: MockClient((r) async {
    pedidos.add(r);
    if (r.method == 'PUT') return _json(jsonDecode(r.body) as Object);
    return _json(guardado);
  }));
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(body: PreconsultaPlusSheet(client: client, ficha: ficha)),
  ));
  await tester.pumpAndSettle();
  return pedidos;
}

void main() {
  final manana = DateTime.now().add(const Duration(days: 1));
  final ayer = DateTime.now().subtract(const Duration(days: 1));

  testWidgets('antes del turno se anota y se guarda', (tester) async {
    final pedidos = await _abrir(tester, _ficha('confirmed', manana));
    await tester.enterText(find.widgetWithText(TextField, 'Motivo de consulta'), ' Migraña ');
    await tester.enterText(
        find.widgetWithText(TextField, 'Preguntas para el médico'), '¿Ibuprofeno?');
    await tester.tap(find.text('Guardar preconsulta'));
    await tester.pumpAndSettle();
    final put = pedidos.singleWhere((r) => r.method == 'PUT');
    expect(put.url.path, endsWith('/appointments/appointments/f1/preconsultation/'));
    expect(jsonDecode(put.body), {'reason': 'Migraña', 'questions': '¿Ibuprofeno?'});
    expect(find.text('Preconsulta guardada.'), findsOneWidget);
  });

  testWidgets('trae lo que ya había anotado', (tester) async {
    await _abrir(tester, _ficha('confirmed', manana),
        guardado: {'reason': 'Control', 'questions': ''});
    expect(find.text('Control'), findsOneWidget);
  });

  testWidgets('atendida: explica por qué y muestra lo anotado, sin campos',
      (tester) async {
    final pedidos = await _abrir(tester, _ficha('attended', ayer),
        guardado: {'reason': 'Fiebre', 'questions': '¿Reposo?'});
    expect(find.byType(TextField), findsNothing);
    expect(find.text('Guardar preconsulta'), findsNothing);
    expect(find.textContaining('esta ficha ya no está pendiente'), findsOneWidget);
    expect(find.text('Fiebre'), findsOneWidget);
    expect(find.text('¿Reposo?'), findsOneWidget);
    expect(pedidos.where((r) => r.method == 'PUT'), isEmpty);
  });

  testWidgets('atendida sin nada anotado lo dice', (tester) async {
    await _abrir(tester, _ficha('attended', ayer));
    expect(find.text('No anotaste una preconsulta para esta ficha.'), findsOneWidget);
  });

  testWidgets('confirmada pero con el turno empezado, no se edita', (tester) async {
    await _abrir(tester, _ficha('confirmed', ayer));
    expect(find.byType(TextField), findsNothing);
    expect(find.textContaining('El turno ya empezó'), findsOneWidget);
  });
}
