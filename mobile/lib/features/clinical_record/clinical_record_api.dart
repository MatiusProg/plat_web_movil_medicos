/// US-25 — La historia clínica longitudinal, vista por el propio paciente.
///
/// El mismo endpoint que usa el médico en la web
/// (`GET /api/encounters/history/<paciente>/`). El backend decide el alcance:
/// el paciente ve la suya y la de las personas a su cargo (US-07); cualquier
/// otro paciente le da 404. Sólo trae atenciones **firmadas**: un borrador
/// todavía no es historia clínica.
library;

import 'package:mobile/core/api/client.dart';

/// Las secciones de una atención, en el orden en que las escribe el médico.
/// Las mismas palabras que `SECCIONES` en `frontend/src/api/atencion.ts`.
const seccionesDeAtencion = [
  ('reason', 'Motivo de consulta'),
  ('evolution', 'Evolución'),
  ('diagnosis', 'Diagnóstico'),
  ('indications', 'Indicaciones'),
  ('treatment', 'Tratamiento'),
];

class Enmienda {
  const Enmienda({
    required this.section,
    required this.text,
    required this.authorName,
    required this.createdAt,
  });

  final String section;
  final String text;
  final String authorName;
  final DateTime? createdAt;

  factory Enmienda.fromJson(Map<String, dynamic> json) => Enmienda(
        section: json['section'] as String? ?? '',
        text: json['text'] as String? ?? '',
        authorName: json['author_name'] as String? ?? '',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
      );
}

class Atencion {
  const Atencion({
    required this.id,
    required this.startsAt,
    required this.practitionerName,
    required this.branchName,
    required this.secciones,
    required this.signedByName,
    required this.signedAt,
    required this.enmiendas,
  });

  final String id;
  final DateTime? startsAt;
  final String practitionerName;
  final String branchName;

  /// Sección → texto, sólo las que el médico escribió.
  final Map<String, String> secciones;
  final String signedByName;
  final DateTime? signedAt;
  final List<Enmienda> enmiendas;

  factory Atencion.fromJson(Map<String, dynamic> json) => Atencion(
        id: json['id'] as String? ?? '',
        startsAt:
            DateTime.tryParse(json['appointment_starts_at'] as String? ?? ''),
        practitionerName: json['practitioner_name'] as String? ?? '',
        branchName: json['branch_name'] as String? ?? '',
        secciones: {
          for (final (campo, _) in seccionesDeAtencion)
            if ((json[campo] as String? ?? '').trim().isNotEmpty)
              campo: (json[campo] as String).trim(),
        },
        signedByName: json['signed_by_name'] as String? ?? '',
        signedAt: DateTime.tryParse(json['signed_at'] as String? ?? ''),
        enmiendas: (json['amendments'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Enmienda.fromJson)
            .toList(),
      );
}

class HistoriaClinica {
  const HistoriaClinica({
    required this.patientName,
    required this.sucursales,
    required this.atenciones,
  });

  final String patientName;

  /// Nombre de la sucursal → cuántas atenciones tiene ahí.
  final Map<String, int> sucursales;
  final List<Atencion> atenciones;

  factory HistoriaClinica.fromJson(Map<String, dynamic> json) {
    final paciente = json['patient'] as Map<String, dynamic>? ?? const {};
    return HistoriaClinica(
      patientName: paciente['full_name'] as String? ?? '',
      sucursales: {
        for (final s in (json['branches'] as List? ?? const [])
            .whereType<Map<String, dynamic>>())
          s['name'] as String? ?? '': s['encounters'] as int? ?? 0,
      },
      atenciones: (json['encounters'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(Atencion.fromJson)
          .toList(),
    );
  }
}

Future<HistoriaClinica> verHistoriaClinica(
  ApiClient client, {
  required String patientId,
}) async {
  final data = await client
      .get('/encounters/history/${Uri.encodeComponent(patientId)}/');
  return HistoriaClinica.fromJson(
    data is Map<String, dynamic> ? data : const <String, dynamic>{},
  );
}
