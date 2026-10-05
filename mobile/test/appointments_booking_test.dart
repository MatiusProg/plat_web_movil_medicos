/// Pruebas de US-17 y US-20 en el móvil: reservar, cancelar y reprogramar.
///
/// El móvil muestra y el backend decide (regla 10 del reparto): acá se
/// comprueba qué se pide, qué se le dice a la persona según lo que respondió
/// el backend, y que un turno ocupado no deja la pantalla en un estado falso.
///
///     flutter test test/appointments_booking_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/features/appointments/appointment_detail_screen.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/appointments/reschedule_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

/// El turno actual de las fichas de prueba. Fijo y lejano para que nunca sea
/// "pasado" y para poder armar un espacio idéntico en la grilla.
final _inicio = DateTime.utc(2099, 1, 1, 13);

Map<String, dynamic> _ficha({
  String id = 'f1',
  String status = 'pending_payment',
  bool? refundEligible,
  String? paymentStatus,
  String? rescheduledFrom,
  DateTime? startsAt,
}) {
  final inicio = startsAt ?? _inicio;
  return {
    'id': id,
    'patient': 'p1',
    'patient_name': 'Ana Pérez',
    'practitioner': 'pr1',
    'practitioner_name': 'Laura Gómez',
    'branch': 'b1',
    'branch_name': 'Sede Centro',
    'starts_at': inicio.toIso8601String(),
    'ends_at': inicio.add(const Duration(minutes: 30)).toIso8601String(),
    'status': status,
    'expires_at': null,
    'cancelled_at': null,
    'cancellation_reason': '',
    'refund_eligible': refundEligible,
    'rescheduled_from': rescheduledFrom,
    'checked_in_at': null,
    'attendance_confirmed_at': null,
    'fee': {'amount': '120.00', 'currency': 'BOB'},
    'payment_status':
        paymentStatus ?? (status == 'confirmed' ? 'succeeded' : null),
  };
}

Map<String, dynamic> _slot(String hora, {String schedule = 's1'}) => {
  'start': '2099-01-0${hora == '13:00' ? 1 : 2}T$hora:00Z',
  'end': '2099-01-0${hora == '13:00' ? 1 : 2}T$hora:30Z',
  'branch': {'id': 'b1', 'name': 'Sede Centro'},
  'schedule': {'id': schedule},
  'capacity': 1,
  'reservable': true,
  'reason': null,
};

Map<String, dynamic> _disponibilidad(List<Map<String, dynamic>> dias) => {
  'practitioner': {'full_name': 'Laura Gómez', 'is_active': true},
  'days': dias,
};

void main() {
  group('Appointment', () {
    test('lee el profesional y de qué ficha viene una reprogramada', () {
      final ficha = Appointment.fromJson(
        _ficha(id: 'f2', status: 'confirmed', rescheduledFrom: 'f1'),
      );
      expect(ficha.practitionerId, 'pr1');
      expect(ficha.rescheduledFrom, 'f1');
      expect(ficha.isActive, isTrue);
    });

    test('una ficha común no trae origen', () {
      expect(Appointment.fromJson(_ficha()).rescheduledFrom, isNull);
    });
  });

  group('reservarFicha (US-17)', () {
    test('pide la ficha con el turno exacto y nace pendiente de pago', () async {
      Map<String, dynamic>? enviado;
      final client = ApiClient(
        httpClient: MockClient((request) async {
          expect(request.method, 'POST');
          expect(request.url.path, endsWith('/appointments/appointments/'));
          enviado = jsonDecode(request.body) as Map<String, dynamic>;
          return _json(_ficha(), 201);
        }),
      );

      final ficha = await reservarFicha(
        client,
        patientId: 'p1',
        practitionerId: 'pr1',
        branchId: 'b1',
        scheduleId: 's1',
        startsAt: '2099-01-01T13:00:00Z',
      );

      expect(enviado, {
        'patient': 'p1',
        'practitioner': 'pr1',
        'branch': 'b1',
        'schedule': 's1',
        'starts_at': '2099-01-01T13:00:00Z',
      });
      expect(ficha.isPendingPayment, isTrue);
    });

    test('si otro tomó el turno llega turno_ocupado', () async {
      final client = ApiClient(
        httpClient: MockClient(
          (_) async => _json({
            'code': 'turno_ocupado',
            'detail': 'Ese turno ya fue tomado.',
          }, 409),
        ),
      );

      expect(
        () => reservarFicha(
          client,
          patientId: 'p1',
          practitionerId: 'pr1',
          branchId: 'b1',
          scheduleId: 's1',
          startsAt: '2099-01-01T13:00:00Z',
        ),
        throwsA(
          isA<ApiError>()
              .having((e) => e.code, 'code', 'turno_ocupado')
              .having((e) => e.status, 'status', 409),
        ),
      );
    });
  });

  group('cancelar (US-20)', () {
    /// Abre el detalle de una ficha y deja que el POST de cancelación
    /// responda [respuesta].
    Future<void> abrirYCancelar(
      WidgetTester tester, {
      required Map<String, dynamic> actual,
      required Map<String, dynamic> respuesta,
    }) async {
      final client = ApiClient(
        httpClient: MockClient((request) async {
          if (request.url.path.endsWith('/cancel/')) {
            return _json(respuesta, 200);
          }
          return _json(actual, 200);
        }),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: AppointmentDetailScreen(
            appointmentId: 'f1',
            client: client,
          ),
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Cancelar ficha'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sí, cancelar'));
      await tester.pumpAndSettle();
    }

    testWidgets('sin pago: no hay nada que devolver', (tester) async {
      await abrirYCancelar(
        tester,
        actual: _ficha(),
        respuesta: _ficha(status: 'cancelled'),
      );

      expect(find.text('Ficha cancelada.'), findsOneWidget);
      expect(find.text('Cancelada'), findsOneWidget);
      // Cancelada ya no se puede cancelar ni reprogramar.
      expect(find.text('Cancelar ficha'), findsNothing);
      expect(find.text('Reprogramar ficha'), findsNothing);
    });

    testWidgets('pagada y a tiempo: se devuelve el pago', (tester) async {
      await abrirYCancelar(
        tester,
        actual: _ficha(status: 'confirmed'),
        respuesta: _ficha(
          status: 'cancelled',
          refundEligible: true,
          paymentStatus: 'refunded',
        ),
      );

      expect(
        find.text('Ficha cancelada. El pago se devolvió.'),
        findsOneWidget,
      );
    });

    testWidgets('pagada y fuera de plazo: no hay devolución', (tester) async {
      await abrirYCancelar(
        tester,
        actual: _ficha(status: 'confirmed'),
        respuesta: _ficha(
          status: 'cancelled',
          refundEligible: false,
          paymentStatus: 'succeeded',
        ),
      );

      expect(
        find.text('Ficha cancelada. Por la anticipación, no hay devolución.'),
        findsOneWidget,
      );
    });
  });

  group('detalle de la ficha', () {
    Future<void> abrir(WidgetTester tester, Map<String, dynamic> ficha) async {
      final client = ApiClient(
        httpClient: MockClient((_) async => _json(ficha, 200)),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: AppointmentDetailScreen(appointmentId: 'f1', client: client),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('ofrece reprogramar una ficha activa y futura', (tester) async {
      await abrir(tester, _ficha());
      expect(find.text('Reprogramar ficha'), findsOneWidget);
    });

    testWidgets('no la ofrece si ya fue reprogramada o pasó', (tester) async {
      await abrir(tester, _ficha(status: 'rescheduled'));
      expect(find.text('Reprogramar ficha'), findsNothing);

      await abrir(
        tester,
        _ficha(status: 'confirmed', startsAt: DateTime(2020, 1, 1, 9)),
      );
      expect(find.text('Reprogramar ficha'), findsNothing);
    });
  });

  group('RescheduleScreen (US-20)', () {
    /// Abre la pantalla desde un botón y guarda con qué se cerró.
    Future<ValueNotifier<Appointment?>> abrir(
      WidgetTester tester,
      ApiClient client,
    ) async {
      final resultado = ValueNotifier<Appointment?>(null);
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (context) => Scaffold(
              body: Center(
                child: FilledButton(
                  onPressed: () async {
                    resultado.value = await Navigator.of(context)
                        .push<Appointment>(
                          MaterialPageRoute(
                            builder: (_) => RescheduleScreen(
                              appointmentId: 'f1',
                              client: client,
                            ),
                          ),
                        );
                  },
                  child: const Text('abrir'),
                ),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('abrir'));
      await tester.pumpAndSettle();
      return resultado;
    }

    testWidgets('no ofrece el turno que la ficha ya tiene', (tester) async {
      final client = ApiClient(
        httpClient: MockClient((request) async {
          if (request.url.path.endsWith('/availability/')) {
            return _json(
              _disponibilidad([
                {
                  'date': '2099-01-01',
                  'slots': [_slot('13:00')],
                },
                {
                  'date': '2099-01-02',
                  'slots': [_slot('09:00')],
                },
              ]),
              200,
            );
          }
          return _json(_ficha(), 200);
        }),
      );
      await abrir(tester, client);

      expect(find.text('13:00 · Sede Centro'), findsNothing);
      expect(find.text('09:00 · Sede Centro'), findsOneWidget);
      expect(find.text('Elegí un horario'), findsOneWidget);
    });

    testWidgets('sin otros horarios lo dice', (tester) async {
      final client = ApiClient(
        httpClient: MockClient((request) async {
          if (request.url.path.endsWith('/availability/')) {
            return _json(_disponibilidad([]), 200);
          }
          return _json(_ficha(), 200);
        }),
      );
      await abrir(tester, client);

      expect(find.textContaining('No hay otros horarios libres'), findsOneWidget);
    });

    testWidgets('elige, confirma y se cierra con la ficha nueva', (
      tester,
    ) async {
      Map<String, dynamic>? enviado;
      final client = ApiClient(
        httpClient: MockClient((request) async {
          if (request.url.path.endsWith('/reschedule/')) {
            enviado = jsonDecode(request.body) as Map<String, dynamic>;
            return _json(
              _ficha(
                id: 'f2',
                status: 'confirmed',
                rescheduledFrom: 'f1',
                startsAt: DateTime.utc(2099, 1, 2, 9),
              ),
              200,
            );
          }
          if (request.url.path.endsWith('/availability/')) {
            return _json(
              _disponibilidad([
                {
                  'date': '2099-01-02',
                  'slots': [_slot('09:00', schedule: 's9')],
                },
              ]),
              200,
            );
          }
          return _json(_ficha(status: 'confirmed'), 200);
        }),
      );
      final resultado = await abrir(tester, client);

      await tester.tap(find.text('09:00 · Sede Centro'));
      await tester.pump();
      await tester.tap(find.text('Reprogramar a las 09:00'));
      await tester.pumpAndSettle();

      // La confirmación avisa que no se cobra de nuevo.
      expect(find.textContaining('no se cobra de nuevo'), findsOneWidget);
      await tester.tap(find.text('Sí, reprogramar'));
      await tester.pumpAndSettle();

      expect(enviado, {
        'branch': 'b1',
        'schedule': 's9',
        'starts_at': '2099-01-02T09:00:00Z',
      });
      expect(resultado.value?.id, 'f2');
      expect(resultado.value?.rescheduledFrom, 'f1');
      // La pantalla se cerró: volvió al botón de partida.
      expect(find.text('abrir'), findsOneWidget);
    });

    testWidgets('si el turno se ocupó, avisa y recarga la grilla', (
      tester,
    ) async {
      var lecturasDeGrilla = 0;
      final client = ApiClient(
        httpClient: MockClient((request) async {
          if (request.url.path.endsWith('/reschedule/')) {
            return _json({
              'code': 'turno_ocupado',
              'detail': 'Ese turno ya fue tomado.',
            }, 409);
          }
          if (request.url.path.endsWith('/availability/')) {
            lecturasDeGrilla++;
            // Después del conflicto, el 09:00 ya no está libre.
            return _json(
              _disponibilidad([
                {
                  'date': '2099-01-02',
                  'slots': [
                    if (lecturasDeGrilla == 1) _slot('09:00'),
                    _slot('10:00'),
                  ],
                },
              ]),
              200,
            );
          }
          return _json(_ficha(), 200);
        }),
      );
      final resultado = await abrir(tester, client);

      await tester.tap(find.text('09:00 · Sede Centro'));
      await tester.pump();
      await tester.tap(find.text('Reprogramar a las 09:00'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sí, reprogramar'));
      await tester.pumpAndSettle();

      expect(find.text('Ese turno ya fue tomado.'), findsOneWidget);
      expect(lecturasDeGrilla, 2);
      expect(find.text('09:00 · Sede Centro'), findsNothing);
      expect(find.text('10:00 · Sede Centro'), findsOneWidget);
      // Sigue en la pantalla, sin elegir nada, y no se cerró con una ficha.
      expect(find.text('Elegí un horario'), findsOneWidget);
      expect(resultado.value, isNull);
    });
  });
}
