/// Pruebas de US-15 — disponibilidad consolidada (móvil).
///
/// Cubren la construcción de la query y el parseo de la respuesta agrupada
/// por día, más que la pantalla entra en un `MockClient`.
///
///     flutter test test/availability_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/availability/availability_api.dart';
import 'package:mobile/features/availability/availability_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _respuestaConDosDias() => {
      'practitioner': {
        'id': 'p1',
        'full_name': 'Laura Gómez',
        'is_active': true,
      },
      'range': {'from': '2026-09-07', 'to': '2026-09-21'},
      'days': [
        {
          'date': '2026-09-07',
          'slots': [
            {
              'start': '2026-09-07T09:00:00-04:00',
              'end': '2026-09-07T09:30:00-04:00',
              'branch': {'id': 'b1', 'name': 'Sede Centro'},
              'capacity': 1,
              'reservable': true,
              'reason': null,
            },
          ],
        },
        {
          'date': '2026-09-08',
          'slots': [
            {
              'start': '2026-09-08T10:00:00-04:00',
              'end': '2026-09-08T10:30:00-04:00',
              'branch': {'id': 'b2', 'name': 'Sede Norte'},
              'capacity': 2,
              'reservable': false,
              'reason': 'sucursal_inactiva',
            },
          ],
        },
      ],
    };

void main() {
  test('disponibilidadConsolidada arma la query y parsea por día', () async {
    http.Request? capturada;
    final mock = MockClient((req) async {
      capturada = req;
      return _json(_respuestaConDosDias(), 200);
    });

    final resultado = await disponibilidadConsolidada(
      ApiClient(httpClient: mock),
      practitionerId: 'p1',
      from: '2026-09-07',
      to: '2026-09-21',
      branchId: 'b1',
    );

    expect(capturada!.url.path, '/api/scheduling/availability/');
    expect(capturada!.url.queryParameters, {
      'practitioner': 'p1',
      'from': '2026-09-07',
      'to': '2026-09-21',
      'branch': 'b1',
    });
    expect(resultado.days, hasLength(2));
    expect(resultado.days.first.slots.first.branchName, 'Sede Centro');
    expect(resultado.days.first.slots.first.horaInicio, '09:00');
    expect(resultado.totalEspacios, 2);
  });

  test('sin branchId la query no lleva el parámetro', () async {
    http.Request? capturada;
    final mock = MockClient((req) async {
      capturada = req;
      return _json(_respuestaConDosDias(), 200);
    });

    await disponibilidadConsolidada(
      ApiClient(httpClient: mock),
      practitionerId: 'p1',
      from: '2026-09-07',
      to: '2026-09-21',
    );

    expect(capturada!.url.queryParameters.containsKey('branch'), isFalse);
  });

  testWidgets('la pantalla muestra la sede y atenúa los no reservables',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mock = MockClient(
      (req) async => _json(_respuestaConDosDias(), 200),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: AvailabilityScreen(
          practitionerId: 'p1',
          practitionerName: 'Laura Gómez',
          client: ApiClient(httpClient: mock),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('09:00'), findsOneWidget);
    expect(find.text('Sede Centro'), findsOneWidget);
    expect(find.text('Sede Norte'), findsOneWidget);
    // El slot no reservable se pinta tachado.
    final tachado = tester.widget<Text>(find.text('10:00'));
    expect(tachado.style?.decoration, TextDecoration.lineThrough);
  });

  testWidgets('un error de la API ofrece reintentar', (tester) async {
    final mock = MockClient(
      (req) async => _json({'detail': 'El profesional no existe.'}, 400),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: AvailabilityScreen(
          practitionerId: 'zzz',
          client: ApiClient(httpClient: mock),
        ),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('El profesional no existe.'), findsOneWidget);
    expect(find.text('Reintentar'), findsOneWidget);
  });
}
