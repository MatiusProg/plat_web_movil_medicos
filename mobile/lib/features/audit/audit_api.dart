/// US-06 — Bitácora de auditoría.
///
/// **Sólo lectura, y no es un olvido**: el backend no expone `POST`, `PUT`,
/// `PATCH` ni `DELETE` sobre `/audit/logs/` — es el punto (f) de la historia.
/// Un registro que se puede editar desde la aplicación no sirve como registro.
///
/// Es el espejo móvil de `frontend/src/paginas/Bitacora.tsx`.
library;

import '../../core/api/client.dart';

/// Quién hizo la acción. Puede faltar: hay asientos del sistema.
class Actor {
  const Actor({required this.email, required this.fullName});

  final String email;
  final String fullName;

  factory Actor.fromJson(Map<String, dynamic> json) => Actor(
        email: json['email'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
      );
}

class Asiento {
  const Asiento({
    required this.id,
    required this.actor,
    required this.action,
    required this.actionLabel,
    required this.entity,
    required this.detail,
    required this.ipAddress,
    required this.userAgent,
    required this.occurredAt,
  });

  final int id;
  final Actor? actor;

  /// El código estable (`patient.update`) y su texto legible.
  final String action;
  final String actionLabel;

  final String entity;

  /// Lo que cambió, tal como lo guardó el backend: claves libres.
  final Map<String, dynamic> detail;

  final String ipAddress;
  final String userAgent;
  final String occurredAt;

  factory Asiento.fromJson(Map<String, dynamic> json) => Asiento(
        id: json['id'] as int? ?? 0,
        actor: json['actor'] is Map<String, dynamic>
            ? Actor.fromJson(json['actor'] as Map<String, dynamic>)
            : null,
        action: json['action'] as String? ?? '',
        actionLabel: json['action_label'] as String? ?? '',
        entity: json['entity'] as String? ?? '',
        detail: json['detail'] is Map<String, dynamic>
            ? json['detail'] as Map<String, dynamic>
            : const {},
        ipAddress: json['ip_address'] as String? ?? '',
        userAgent: json['user_agent'] as String? ?? '',
        occurredAt: json['occurred_at'] as String? ?? '',
      );

  /// `2026-09-09T15:56:40.041824-04:00` -> `09/09/2026 15:56`.
  ///
  /// El backend manda el instante completo con microsegundos. Mostrarlo tal
  /// cual —como todavía hacen otras pantallas— es ilegible en una lista.
  String get cuando {
    final fecha = DateTime.tryParse(occurredAt);
    if (fecha == null) return occurredAt;
    String dos(int n) => n.toString().padLeft(2, '0');
    return '${dos(fecha.day)}/${dos(fecha.month)}/${fecha.year} '
        '${dos(fecha.hour)}:${dos(fecha.minute)}';
  }
}

class PaginaDeBitacora {
  const PaginaDeBitacora({required this.total, required this.asientos});

  final int total;
  final List<Asiento> asientos;
}

/// Una acción del catálogo, para el filtro.
class AccionAuditable {
  const AccionAuditable({required this.code, required this.label});

  final String code;
  final String label;
}

Future<List<AccionAuditable>> listarAcciones(ApiClient client) async {
  final data = await client.get('/audit/logs/actions/');
  return (data as List? ?? const [])
      .whereType<Map<String, dynamic>>()
      .map((e) => AccionAuditable(
            code: e['code'] as String? ?? '',
            label: e['label'] as String? ?? '',
          ))
      .toList();
}

/// La bitácora, paginada y en orden cronológico inverso.
Future<PaginaDeBitacora> listarBitacora(
  ApiClient client, {
  String? action,
  int page = 1,
}) async {
  final params = <String>[
    if (action != null && action.isNotEmpty) 'action=$action',
    if (page > 1) 'page=$page',
  ];
  final sufijo = params.isEmpty ? '' : '?${params.join('&')}';

  final data = await client.get('/audit/logs/$sufijo');
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  return PaginaDeBitacora(
    total: mapa['count'] as int? ?? 0,
    asientos: (mapa['results'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(Asiento.fromJson)
        .toList(),
  );
}
