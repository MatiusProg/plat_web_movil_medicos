/// US-52 — Lista de espera con aviso de cupo liberado.
///
/// **El móvil muestra, el backend decide.** La posición en la fila, si el plan
/// incluye la función y si ya hay turnos libres lo resuelve el backend; acá
/// sólo se pide y se traduce la respuesta. Cuando alguien cancela, el backend
/// le guarda el turno 15 minutos al primero de la fila y le avisa por push: esa
/// ficha llega como una ficha pendiente de pago más (`appointments_api.dart`).
library;

import 'package:mobile/core/api/client.dart';

class WaitlistStatus {
  const WaitlistStatus._();

  static const String waiting = 'waiting';
  static const String offered = 'offered';
  static const String booked = 'booked';
  static const String expired = 'expired';
  static const String cancelled = 'cancelled';
}

class WaitlistEntry {
  const WaitlistEntry({
    required this.id,
    this.patientId = '',
    required this.patientName,
    this.practitionerId,
    this.practitionerName,
    this.specialtyId,
    this.specialtyName,
    this.branchId,
    this.branchName,
    required this.dateFrom,
    required this.dateTo,
    required this.status,
    this.position,
    this.offeredAppointmentId,
    this.offeredExpiresAt,
  });

  final String id;
  final String patientId;
  final String patientName;
  final String? practitionerId;
  final String? practitionerName;
  final String? specialtyId;
  final String? specialtyName;
  final String? branchId;
  final String? branchName;

  /// `YYYY-MM-DD`, tal cual lo manda el backend.
  final String dateFrom;
  final String dateTo;

  /// `waiting` | `offered` | `booked` | `expired` | `cancelled`.
  final String status;

  /// El lugar en la fila (1 = primero). `null` si ya se le ofreció un turno.
  final int? position;
  final String? offeredAppointmentId;
  final DateTime? offeredExpiresAt;

  factory WaitlistEntry.fromJson(Map<String, dynamic> json) => WaitlistEntry(
    id: json['id'] as String? ?? '',
    patientId: json['patient'] as String? ?? '',
    patientName: json['patient_name'] as String? ?? '',
    practitionerId: json['practitioner'] as String?,
    practitionerName: json['practitioner_name'] as String?,
    specialtyId: json['specialty'] as String?,
    specialtyName: json['specialty_name'] as String?,
    branchId: json['branch'] as String?,
    branchName: json['branch_name'] as String?,
    dateFrom: json['date_from'] as String? ?? '',
    dateTo: json['date_to'] as String? ?? '',
    status: json['status'] as String? ?? '',
    position: (json['position'] as num?)?.toInt(),
    offeredAppointmentId: json['offered_appointment'] as String?,
    offeredExpiresAt: json['offered_expires_at'] is String
        ? DateTime.tryParse(json['offered_expires_at'] as String)?.toLocal()
        : null,
  );

  bool get isOffered => status == WaitlistStatus.offered;

  /// A quién se espera: el profesional, o la especialidad si no hay profesional.
  String get destino {
    final profesional = practitionerName;
    if (profesional != null && profesional.isNotEmpty) return profesional;
    final especialidad = specialtyName;
    if (especialidad != null && especialidad.isNotEmpty) return especialidad;
    return 'Lista de espera';
  }

  /// "2026-11-18" → "18/11/2026"; si no se puede leer, el texto original.
  static String _legible(String iso) {
    final partes = iso.split('-');
    if (partes.length != 3) return iso;
    return '${partes[2]}/${partes[1]}/${partes[0]}';
  }

  String get rango => '${_legible(dateFrom)} al ${_legible(dateTo)}';
}

/// Lo que devuelve `GET /appointments/waitlist/`.
class ListaDeEspera {
  const ListaDeEspera({required this.enabled, required this.entries});

  /// `false` si el plan del centro no incluye la función: no se muestra nada.
  final bool enabled;
  final List<WaitlistEntry> entries;

  static const ListaDeEspera vacia = ListaDeEspera(
    enabled: false,
    entries: [],
  );

  factory ListaDeEspera.fromJson(Map<String, dynamic> json) => ListaDeEspera(
    enabled: json['enabled'] as bool? ?? false,
    entries: (json['results'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(WaitlistEntry.fromJson)
        .toList(),
  );
}

Future<ListaDeEspera> miListaDeEspera(ApiClient client) async {
  final data = await client.get('/appointments/waitlist/');
  return data is Map<String, dynamic>
      ? ListaDeEspera.fromJson(data)
      : ListaDeEspera.vacia;
}

/// Anota al paciente. Por ahora el móvil sólo anota por profesional; el
/// backend también acepta [specialtyId] (profesional **o** especialidad).
Future<WaitlistEntry> anotarseEnListaDeEspera(
  ApiClient client, {
  required String patientId,
  String? practitionerId,
  String? specialtyId,
  String? branchId,
  required String dateFrom,
  required String dateTo,
}) async {
  final data = await client.post(
    '/appointments/waitlist/',
    body: {
      'patient': patientId,
      'practitioner': ?practitionerId,
      'specialty': ?specialtyId,
      'branch': ?branchId,
      'date_from': dateFrom,
      'date_to': dateTo,
    },
  );
  return WaitlistEntry.fromJson(
    data is Map<String, dynamic> ? data : const <String, dynamic>{},
  );
}

Future<void> salirDeListaDeEspera(ApiClient client, String id) async {
  await client.delete('/appointments/waitlist/$id/');
}
