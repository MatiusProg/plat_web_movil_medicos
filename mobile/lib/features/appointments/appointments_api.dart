/// US-17, US-20 y US-21 — La ficha, vista desde el paciente.
///
/// **El móvil muestra, el backend decide** (regla 10 del reparto del Sprint
/// 2). Ningún estado de pago ni confirmación se calcula acá: [Appointment]
/// sólo traduce lo que devolvió la API, y las acciones piden y vuelven a leer.
library;

import 'package:mobile/core/api/client.dart';

class AppointmentStatus {
  const AppointmentStatus._();

  static const String pendingPayment = 'pending_payment';
  static const String confirmed = 'confirmed';
  static const String attended = 'attended';
  static const String cancelled = 'cancelled';
  static const String rescheduled = 'rescheduled';
  static const String expired = 'expired';
  static const String noShow = 'no_show';

  static const Map<String, String> _etiquetas = {
    pendingPayment: 'Pendiente de pago',
    confirmed: 'Confirmada',
    attended: 'Atendida',
    cancelled: 'Cancelada',
    rescheduled: 'Reprogramada',
    expired: 'Vencida',
    noShow: 'Ausente',
  };

  static String etiqueta(String status) => _etiquetas[status] ?? status;
}

/// El importe que cobra el centro por la ficha. Llega como texto decimal
/// ("120.00") y así se muestra: convertirlo a `double` para dibujarlo sólo
/// agrega errores de redondeo.
class Fee {
  const Fee({required this.amount, required this.currency});

  final String amount;
  final String currency;

  factory Fee.fromJson(Map<String, dynamic> json) => Fee(
    amount: '${json['amount'] ?? ''}',
    currency: json['currency'] as String? ?? 'BOB',
  );

  /// "Bs 120.00" para bolivianos; el código ISO para cualquier otra moneda.
  String get texto {
    final simbolo = currency == 'BOB' ? 'Bs' : currency;
    return '$simbolo $amount';
  }
}

class Appointment {
  const Appointment({
    required this.id,
    required this.patientId,
    required this.patientName,
    required this.practitionerName,
    required this.branchName,
    required this.startsAt,
    required this.endsAt,
    required this.status,
    this.expiresAt,
    this.cancelledAt,
    this.refundEligible,
    this.checkedInAt,
    this.attendanceConfirmedAt,
    this.fee,
    this.paymentStatus,
  });

  final String id;
  final String patientId;
  final String patientName;
  final String practitionerName;
  final String branchName;
  final DateTime startsAt;
  final DateTime endsAt;
  final String status;
  final DateTime? expiresAt;
  final DateTime? cancelledAt;
  final bool? refundEligible;
  final DateTime? checkedInAt;
  final DateTime? attendanceConfirmedAt;
  final Fee? fee;

  /// `null` | `pending` | `succeeded` | `refunded` | `failed`.
  final String? paymentStatus;

  static DateTime? _fecha(Object? valor) =>
      valor is String ? DateTime.tryParse(valor)?.toLocal() : null;

  factory Appointment.fromJson(Map<String, dynamic> json) {
    final fee = json['fee'];
    return Appointment(
      id: json['id'] as String? ?? '',
      patientId: json['patient'] as String? ?? '',
      patientName: json['patient_name'] as String? ?? '',
      practitionerName: json['practitioner_name'] as String? ?? '',
      branchName: json['branch_name'] as String? ?? '',
      startsAt:
          _fecha(json['starts_at']) ?? DateTime.fromMillisecondsSinceEpoch(0),
      endsAt: _fecha(json['ends_at']) ?? DateTime.fromMillisecondsSinceEpoch(0),
      status: json['status'] as String? ?? '',
      expiresAt: _fecha(json['expires_at']),
      cancelledAt: _fecha(json['cancelled_at']),
      refundEligible: json['refund_eligible'] as bool?,
      checkedInAt: _fecha(json['checked_in_at']),
      attendanceConfirmedAt: _fecha(json['attendance_confirmed_at']),
      fee: fee is Map<String, dynamic> ? Fee.fromJson(fee) : null,
      paymentStatus: json['payment_status'] as String?,
    );
  }

  String get statusLabel => AppointmentStatus.etiqueta(status);

  bool get isPendingPayment => status == AppointmentStatus.pendingPayment;
  bool get isConfirmed => status == AppointmentStatus.confirmed;

  /// Todavía ocupa el turno: es lo que se puede cancelar (US-20).
  bool get isActive => isPendingPayment || isConfirmed;

  bool isPast([DateTime? ahora]) => !startsAt.isAfter(ahora ?? DateTime.now());

  /// US-21: se ofrece confirmar sólo sobre una ficha pagada, futura y que el
  /// paciente todavía no confirmó.
  bool canConfirmAttendance([DateTime? ahora]) =>
      isConfirmed && attendanceConfirmedAt == null && !isPast(ahora);
}

/// Ordena "próximas primero" y después las pasadas, de la más reciente a la
/// más vieja: es lo que el paciente busca al abrir la lista.
List<Appointment> ordenarParaLista(
  List<Appointment> fichas, [
  DateTime? ahora,
]) {
  final referencia = ahora ?? DateTime.now();
  final proximas = fichas.where((f) => !f.isPast(referencia)).toList()
    ..sort((a, b) => a.startsAt.compareTo(b.startsAt));
  final pasadas = fichas.where((f) => f.isPast(referencia)).toList()
    ..sort((a, b) => b.startsAt.compareTo(a.startsAt));
  return [...proximas, ...pasadas];
}

Appointment _ficha(Object? data) => Appointment.fromJson(
  data is Map<String, dynamic> ? data : const <String, dynamic>{},
);

/// US-17 — Reserva un turno. La ficha nace `pending_payment`.
Future<Appointment> reservarFicha(
  ApiClient client, {
  required String patientId,
  required String practitionerId,
  required String branchId,
  required String scheduleId,
  required String startsAt,
}) async => _ficha(
  await client.post(
    '/appointments/appointments/',
    body: {
      'patient': patientId,
      'practitioner': practitionerId,
      'branch': branchId,
      'schedule': scheduleId,
      'starts_at': startsAt,
    },
  ),
);

Future<List<Appointment>> misFichas(ApiClient client) async {
  final data = await client.get('/appointments/appointments/');
  final lista = data is List
      ? data
      : (data is Map<String, dynamic> ? data['results'] as List? : null) ??
            const [];
  return lista
      .whereType<Map<String, dynamic>>()
      .map(Appointment.fromJson)
      .toList();
}

Future<Appointment> verFicha(ApiClient client, String id) async =>
    _ficha(await client.get('/appointments/appointments/$id/'));

/// US-21 — El paciente avisa que va a ir. Idempotente del lado del backend.
Future<Appointment> confirmarAsistencia(ApiClient client, String id) async =>
    _ficha(
      await client.post('/appointments/appointments/$id/confirm-attendance/'),
    );

/// US-20 — Cancela. Si corresponde devolución lo decide el backend.
Future<Appointment> cancelarFicha(ApiClient client, String id) async =>
    _ficha(await client.post('/appointments/appointments/$id/cancel/'));
