/// US-15 — Disponibilidad consolidada de un profesional entre sus sucursales.
///
/// El mismo endpoint que consume el frontend web. La respuesta viene agrupada
/// por día, que es como la dibuja la pantalla.
library;

import 'package:mobile/core/api/client.dart';

class SlotDisponible {
  const SlotDisponible({
    required this.start,
    required this.end,
    required this.branchId,
    required this.branchName,
    required this.capacity,
    required this.reservable,
    this.reason,
  });

  final String start;
  final String end;
  final String branchId;
  final String branchName;
  final int capacity;
  final bool reservable;

  /// `profesional_inactivo` | `sucursal_inactiva` | `null`.
  final String? reason;

  factory SlotDisponible.fromJson(Map<String, dynamic> json) {
    final branch = json['branch'] as Map<String, dynamic>? ?? const {};
    return SlotDisponible(
      start: json['start'] as String? ?? '',
      end: json['end'] as String? ?? '',
      branchId: branch['id'] as String? ?? '',
      branchName: branch['name'] as String? ?? '',
      capacity: json['capacity'] as int? ?? 1,
      reservable: json['reservable'] as bool? ?? false,
      reason: json['reason'] as String?,
    );
  }

  /// La hora `HH:mm` del inicio, ya en la zona de la sucursal.
  String get horaInicio =>
      start.length >= 16 ? start.substring(11, 16) : start;
}

class DiaDisponible {
  const DiaDisponible({required this.date, required this.slots});

  final String date;
  final List<SlotDisponible> slots;

  factory DiaDisponible.fromJson(Map<String, dynamic> json) => DiaDisponible(
        date: json['date'] as String? ?? '',
        slots: (json['slots'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(SlotDisponible.fromJson)
            .toList(),
      );
}

class Disponibilidad {
  const Disponibilidad({
    required this.practitionerName,
    required this.practitionerActive,
    required this.days,
  });

  final String practitionerName;
  final bool practitionerActive;
  final List<DiaDisponible> days;

  factory Disponibilidad.fromJson(Map<String, dynamic> json) {
    final profesional =
        json['practitioner'] as Map<String, dynamic>? ?? const {};
    return Disponibilidad(
      practitionerName: profesional['full_name'] as String? ?? '',
      practitionerActive: profesional['is_active'] as bool? ?? true,
      days: (json['days'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(DiaDisponible.fromJson)
          .toList(),
    );
  }

  int get totalEspacios =>
      days.fold(0, (suma, dia) => suma + dia.slots.length);
}

Future<Disponibilidad> disponibilidadConsolidada(
  ApiClient client, {
  required String practitionerId,
  required String from,
  required String to,
  String? branchId,
}) async {
  final params = <String, String>{
    'practitioner': practitionerId,
    'from': from,
    'to': to,
    if (branchId != null && branchId.isNotEmpty) 'branch': branchId,
  };
  final query = params.entries
      .map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}')
      .join('&');

  final data = await client.get('/scheduling/availability/?$query');
  return Disponibilidad.fromJson(
    data is Map<String, dynamic> ? data : const <String, dynamic>{},
  );
}
