/// Pruebas de US-17/18/19/21 en el móvil: la ficha, el pago y el comprobante.
///
/// Lo que importa probar es la regla 10 del reparto: el móvil **no** confirma
/// la ficha al volver del navegador; la muestra confirmada sólo cuando el
/// backend lo dice. Y que el comprobante se pueda ver sin red.
///
///     flutter test test/appointments_payments_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/appointments/appointment_detail_screen.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/receipts/receipt_screen.dart';
import 'package:mobile/features/receipts/receipt_store.dart';
import 'package:mobile/features/receipts/receipts_api.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Map<String, dynamic> _ficha({
  String status = 'pending_payment',
  String? attendance,
  DateTime? startsAt,
}) {
  final inicio = startsAt ?? DateTime.now().add(const Duration(days: 2));
  return {
    'id': 'f1',
    'patient': 'p1',
    'patient_name': 'Ana Pérez',
    'practitioner': 'pr1',
    'practitioner_name': 'Laura Gómez',
    'branch': 'b1',
    'branch_name': 'Sede Centro',
    'starts_at': inicio.toUtc().toIso8601String(),
    'ends_at': inicio.add(const Duration(minutes: 30)).toUtc().toIso8601String(),
    'status': status,
    'expires_at': null,
    'cancelled_at': null,
    'cancellation_reason': '',
    'refund_eligible': null,
    'rescheduled_from': null,
    'checked_in_at': null,
    'attendance_confirmed_at': attendance,
    'fee': {'amount': '120.00', 'currency': 'BOB'},
    'payment_status': status == 'confirmed' ? 'succeeded' : null,
  };
}

Map<String, dynamic> _comprobante() => {
  'appointment_id': 'f1',
  'code': 'MC1.firmado.abc',
  'issued_at': '2026-10-04T10:00:00Z',
  'organization_name': 'Clínica Demo',
  'patient_name': 'Ana Pérez',
  'document_number': '1234567',
  'practitioner_name': 'Laura Gómez',
  'branch_name': 'Sede Centro',
  'branch_address': 'Av. Siempre Viva 1',
  'starts_at': '2026-10-06T13:00:00Z',
  'ends_at': '2026-10-06T13:30:00Z',
  'status': 'confirmed',
};

void main() {
  group('Appointment', () {
    test('parsea la ficha con importe y estado de pago', () {
      final ficha = Appointment.fromJson(_ficha(status: 'confirmed'));
      expect(ficha.isConfirmed, isTrue);
      expect(ficha.fee?.texto, 'Bs 120.00');
      expect(ficha.paymentStatus, 'succeeded');
      expect(ficha.statusLabel, 'Confirmada');
      expect(ficha.canConfirmAttendance(), isTrue);
    });

    test('no ofrece confirmar asistencia si ya confirmó o si no pagó', () {
      expect(
        Appointment.fromJson(
          _ficha(status: 'confirmed', attendance: '2026-10-04T10:00:00Z'),
        ).canConfirmAttendance(),
        isFalse,
      );
      expect(Appointment.fromJson(_ficha()).canConfirmAttendance(), isFalse);
    });

    test('ordena próximas primero y después las pasadas', () {
      final ahora = DateTime.now();
      Appointment en(int dias) => Appointment.fromJson(
        _ficha(startsAt: ahora.add(Duration(days: dias))),
      );
      final orden = ordenarParaLista([en(-5), en(3), en(-1), en(1)], ahora);
      expect(
        orden.map((f) => f.startsAt.difference(ahora).inDays).toList(),
        [1, 3, -1, -5],
      );
    });
  });

  group('ReceiptStore', () {
    setUp(() => FlutterSecureStorage.setMockInitialValues({}));

    test('guarda y recupera el comprobante tal como vino', () async {
      final store = ReceiptStore();
      await store.save(Receipt.fromJson(_comprobante()));
      final leido = await store.read('f1');
      expect(leido?.code, 'MC1.firmado.abc');
      expect((await store.all()).single.branchAddress, 'Av. Siempre Viva 1');
      await store.remove('f1');
      expect(await store.read('f1'), isNull);
    });
  });

  testWidgets('pagar no confirma la ficha: espera a que el backend lo diga', (
    tester,
  ) async {
    var lecturas = 0;
    Uri? abierta;
    final client = ApiClient(
      httpClient: MockClient((request) async {
        if (request.url.path.endsWith('/checkout/')) {
          return _json({
            'payment_id': 'pay1',
            'provider': 'simulated',
            'checkout_url': 'https://pago.test/checkout/pay1',
            'amount': '120.00',
            'currency': 'BOB',
            'status': 'pending',
          }, 201);
        }
        lecturas++;
        // Las dos primeras lecturas siguen pendientes; recién la tercera,
        // después de "acreditarse" el pago, viene confirmada.
        return _json(
          _ficha(status: lecturas >= 3 ? 'confirmed' : 'pending_payment'),
          200,
        );
      }),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: AppointmentDetailScreen(
          appointmentId: 'f1',
          client: client,
          openUrl: (url) async {
            abierta = url;
            return true;
          },
          pollInterval: const Duration(milliseconds: 100),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Pagar Bs 120.00'), findsOneWidget);
    await tester.tap(find.text('Pagar Bs 120.00'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ir a pagar'));
    await tester.pump();
    await tester.pump();

    expect(abierta.toString(), 'https://pago.test/checkout/pay1');
    // Volvió del navegador pero el backend todavía no confirmó.
    expect(find.text('Ver comprobante'), findsNothing);
    expect(find.text('Ya pagué — actualizar'), findsOneWidget);

    await tester.pump(const Duration(milliseconds: 150));
    await tester.pump(const Duration(milliseconds: 150));
    await tester.pumpAndSettle();

    expect(find.text('Ver comprobante'), findsOneWidget);
    expect(find.text('Confirmada'), findsOneWidget);
  });

  testWidgets('sin red muestra la copia guardada del comprobante', (
    tester,
  ) async {
    FlutterSecureStorage.setMockInitialValues({});
    final store = ReceiptStore();
    await store.save(Receipt.fromJson(_comprobante()));

    final client = ApiClient(
      httpClient: MockClient((_) async => throw http.ClientException('sin red')),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: ReceiptScreen(appointmentId: 'f1', client: client, store: store),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Sin conexión — copia guardada'), findsOneWidget);
    expect(find.text('1234567'), findsOneWidget);
  });
}
