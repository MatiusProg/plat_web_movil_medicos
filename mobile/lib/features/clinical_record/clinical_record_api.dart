/// US-25 — La historia clínica longitudinal, vista por el propio paciente.
///
/// El mismo endpoint que usa el médico en la web
/// (`GET /api/encounters/history/<paciente>/`). El backend decide el alcance:
/// el paciente ve la suya y la de las personas a su cargo (US-07); cualquier
/// otro paciente le da 404. Sólo trae atenciones **firmadas**: un borrador
/// todavía no es historia clínica.
///
/// US-27: cada atención trae además la receta y las órdenes que el médico
/// emitió (US-26), y la receta se baja en PDF con [descargarReceta].
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

/// US-26 — Un medicamento de la receta.
class Medicamento {
  const Medicamento({
    required this.medication,
    required this.dose,
    required this.frequency,
    required this.duration,
    required this.instructions,
  });

  final String medication;
  final String dose;
  final String frequency;
  final String duration;
  final String instructions;

  factory Medicamento.fromJson(Map<String, dynamic> json) => Medicamento(
        medication: json['medication'] as String? ?? '',
        dose: json['dose'] as String? ?? '',
        frequency: json['frequency'] as String? ?? '',
        duration: json['duration'] as String? ?? '',
        instructions: json['instructions'] as String? ?? '',
      );
}

/// US-26 — Una orden de laboratorio o de estudio.
class Orden {
  const Orden({
    required this.kindDisplay,
    required this.description,
    required this.notes,
  });

  final String kindDisplay;
  final String description;
  final String notes;

  factory Orden.fromJson(Map<String, dynamic> json) => Orden(
        kindDisplay: json['kind_display'] as String? ?? '',
        description: json['description'] as String? ?? '',
        notes: json['notes'] as String? ?? '',
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
    this.medicamentos = const [],
    this.ordenes = const [],
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
  final List<Medicamento> medicamentos;
  final List<Orden> ordenes;

  /// Hay algo que bajar en PDF.
  bool get tieneReceta => medicamentos.isNotEmpty || ordenes.isNotEmpty;

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
        medicamentos: (json['prescription_items'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Medicamento.fromJson)
            .toList(),
        ordenes: (json['orders'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Orden.fromJson)
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

/// US-27 — La receta firmada de una atención, en PDF.
///
/// El backend la entrega sólo de una atención firmada y a quien tiene alcance
/// sobre el historial (el paciente o el titular de un dependiente), y deja el
/// asiento en la bitácora.
Future<ArchivoRecibido> descargarReceta(
  ApiClient client, {
  required String encounterId,
}) =>
    client.download(
      'GET',
      '/encounters/${Uri.encodeComponent(encounterId)}/prescription.pdf',
    );
