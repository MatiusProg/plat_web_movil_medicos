/// US-08 — Antecedentes: alergias, condiciones crónicas y medicación habitual.
///
/// Son **declarados por el paciente**, no diagnosticados. La pantalla lo dice y
/// el backend lo guarda marcado como tal: el diagnóstico clínico lo registra el
/// médico en el Sprint 3, en otra tabla, y no vale lo mismo.
library;

import 'package:mobile/core/api/client.dart';

/// Los tres tipos, con su etiqueta y su orden de presentación.
///
/// Las alergias van primero porque son el dato que cambia una receta.
const List<({String code, String label, String plural})> tiposDeAntecedente = [
  (code: 'allergy', label: 'Alergia', plural: 'Alergias'),
  (code: 'condition', label: 'Condición crónica', plural: 'Condiciones crónicas'),
  (code: 'medication', label: 'Medicación habitual', plural: 'Medicación habitual'),
];

/// Sólo aplica a las alergias (punto b). De más grave a menos: es el orden en
/// que hay que poder leerlas.
const Map<String, String> severidades = {
  'anaphylactic': 'Anafiláctica',
  'severe': 'Grave',
  'moderate': 'Moderada',
  'mild': 'Leve',
};

class Antecedente {
  const Antecedente({
    required this.id,
    required this.patient,
    required this.kind,
    required this.kindLabel,
    required this.description,
    required this.severity,
    required this.severityLabel,
    required this.recordedAt,
  });

  final String id;
  final String patient;
  final String kind;
  final String kindLabel;
  final String description;

  /// Vacío salvo en las alergias.
  final String severity;
  final String severityLabel;
  final String recordedAt;

  factory Antecedente.fromJson(Map<String, dynamic> json) => Antecedente(
        id: json['id'] as String? ?? '',
        patient: json['patient'] as String? ?? '',
        kind: json['kind'] as String? ?? '',
        kindLabel: json['kind_label'] as String? ?? '',
        description: json['description'] as String? ?? '',
        severity: json['severity'] as String? ?? '',
        severityLabel: json['severity_label'] as String? ?? '',
        recordedAt: json['recorded_at'] as String? ?? '',
      );
}

Future<List<Antecedente>> listarAntecedentes(
  ApiClient client, {
  required String patientId,
}) async {
  final data = await client.get(
    '/patients/history/?patient=${Uri.encodeQueryComponent(patientId)}',
  );
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  return (mapa['results'] as List? ?? const [])
      .whereType<Map<String, dynamic>>()
      .map(Antecedente.fromJson)
      .toList();
}

Future<Antecedente> registrarAntecedente(
  ApiClient client, {
  required String patientId,
  required String kind,
  required String description,
  String severity = '',
}) async {
  final data = await client.post('/patients/history/', body: {
    'patient': patientId,
    'kind': kind,
    'description': description,
    // El backend rechaza una severidad fuera de las alergias, así que no se
    // manda vacía: sería mandar un campo que no aplica.
    if (severity.isNotEmpty) 'severity': severity,
  });
  return Antecedente.fromJson(data as Map<String, dynamic>);
}

/// Baja lógica. Lo declarado no se pierde: deja de estar vigente (punto e).
Future<void> quitarAntecedente(ApiClient client, String id) =>
    client.delete('/patients/history/$id/');
