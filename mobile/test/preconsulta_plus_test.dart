// US-51: la preconsulta de la «Experiencia Plus» de una ficha pagada.
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/files/archivos.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/appointments/preconsulta_plus.dart';

Appointment _ficha(String status, DateTime inicio, {String? mapa = _mapa}) =>
    Appointment.fromJson({
      'id': 'f1', 'patient': 'p1', 'patient_name': 'Ana Pérez',
      'practitioner': 'pr1', 'practitioner_name': 'Laura Gómez',
      'branch': 'b1', 'branch_name': 'Sede Centro',
      'branch_address': 'Av. 6 de Agosto 2170', 'branch_maps_url': mapa,
      'starts_at': inicio.toUtc().toIso8601String(),
      'ends_at': inicio.add(const Duration(minutes: 30)).toUtc().toIso8601String(),
      'status': status, 'expires_at': null, 'cancelled_at': null,
      'cancellation_reason': '', 'refund_eligible': null, 'rescheduled_from': null,
      'checked_in_at': null, 'attendance_confirmed_at': null,
      'fee': {'amount': '120.00', 'currency': 'BOB'}, 'payment_status': 'succeeded',
    });

const _mapa = 'https://www.google.com/maps/search/?api=1&query=-16.5,-68.1';

class _Guardado implements GuardadoDeArchivos {
  final guardados = <String, List<int>>{};
  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    guardados[nombre] = bytes;
    return '/descargas/$nombre';
  }
}

class _Abridor implements AbridorDeArchivos {
  final abiertos = <String>[];
  @override
  Future<String?> abrir(String ruta) async {
    abiertos.add(ruta);
    return null;
  }
}

http.Response _json(Object c, [int s = 200]) => http.Response(jsonEncode(c), s,
    headers: {'content-type': 'application/json; charset=utf-8'});

Future<List<http.Request>> _abrir(WidgetTester tester, Appointment ficha,
    {Map<String, dynamic> guardado = const {'reason': '', 'questions': ''},
    List<Uri>? urls, _Guardado? archivos, _Abridor? abridor}) async {
  final pedidos = <http.Request>[];
  final client = ApiClient(httpClient: MockClient((r) async {
    pedidos.add(r);
    if (r.method == 'PUT') return _json(jsonDecode(r.body) as Object);
    if (r.url.path.endsWith('calendar.ics')) {
      return http.Response('BEGIN:VCALENDAR', 200, headers: {
        'content-type': 'text/calendar',
        'content-disposition': 'attachment; filename="ficha-2026-12-03-1030.ics"',
      });
    }
    return _json(guardado);
  }));
  tester.view.physicalSize = const Size(1080, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(MaterialApp(
    home: Scaffold(body: PreconsultaPlusSheet(
      client: client, ficha: ficha,
      openUrl: (u) async { urls?.add(u); return true; },
      guardado: archivos, abridor: abridor,
    )),
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
    expect(find.text('Preconsulta guardada: tu médico la verá al atenderte.'),
        findsOneWidget);
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

  // ---------- El plus: calendario, cómo llegar y cuenta regresiva ----------

  test('la cuenta regresiva cuenta días de calendario', () {
    final ahora = DateTime(2026, 11, 21, 22, 0);
    expect(cuentaRegresiva(DateTime(2026, 11, 21, 23, 30), ahora), 'Es hoy a las 23:30');
    // A dos horas, pero ya es mañana.
    expect(cuentaRegresiva(DateTime(2026, 11, 22, 0, 30), ahora), 'Es mañana a las 00:30');
    expect(cuentaRegresiva(DateTime(2026, 11, 24, 10, 0), ahora), 'Faltan 3 días');
    expect(cuentaRegresiva(DateTime(2026, 11, 21, 21, 0), ahora), isNull);
  });

  testWidgets('agrega la ficha al calendario: baja el .ics y lo abre', (tester) async {
    final archivos = _Guardado();
    final abridor = _Abridor();
    final pedidos = await _abrir(tester, _ficha('confirmed', manana),
        archivos: archivos, abridor: abridor);
    expect(find.textContaining('para tu ficha con Laura Gómez'), findsOneWidget);
    await tester.tap(find.text('Agregar'));
    await tester.pumpAndSettle();
    expect(pedidos.last.url.path,
        endsWith('/appointments/appointments/f1/calendar.ics'));
    expect(archivos.guardados.keys, ['ficha-2026-12-03-1030.ics']);
    expect(abridor.abiertos, ['/descargas/ficha-2026-12-03-1030.ics']);
  });

  testWidgets('cómo llegar abre el mapa de la sede', (tester) async {
    final urls = <Uri>[];
    await _abrir(tester, _ficha('confirmed', manana), urls: urls);
    expect(find.text('Av. 6 de Agosto 2170'), findsOneWidget);
    await tester.tap(find.text('Abrir el mapa'));
    await tester.pumpAndSettle();
    expect(urls.single.toString(), _mapa);
  });

  testWidgets('sin coordenadas no hay cómo llegar', (tester) async {
    await _abrir(tester, _ficha('confirmed', manana, mapa: null));
    expect(find.text('Cómo llegar'), findsNothing);
    expect(find.text('Cómo prepararte'), findsOneWidget);
  });

  testWidgets('atendida: ni calendario ni cuenta regresiva', (tester) async {
    await _abrir(tester, _ficha('attended', ayer));
    expect(find.text('Agregar a mi calendario'), findsNothing);
    expect(find.textContaining('para tu ficha con'), findsNothing);
    // Cómo llegar sigue: la sede no cambió.
    expect(find.text('Cómo llegar'), findsOneWidget);
  });
}
