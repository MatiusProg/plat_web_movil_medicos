/// US-49 — Los medicamentos de la receta y las tomas marcadas.
///
/// - `GET  /api/encounters/medications/<paciente>/`: lo recetado en las
///   atenciones firmadas recientes, con su horario (o el motivo por el que no
///   tiene), el cumplimiento y las tomas ya marcadas.
/// - `POST /api/encounters/prescription/<medicamento>/intakes/`: marcar una.
///
/// El horario lo calcula el backend (`encounters/frequency.py`) con la misma
/// regla para el paciente y para el médico: la app no vuelve a interpretar
/// «cada 8 horas», sólo lo programa.
library;

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';

/// Cada cuántas horas y cuántas tomas en total.
class HorarioDeTomas {
  const HorarioDeTomas({
    required this.intervaloHoras,
    required this.dias,
    required this.totalTomas,
  });

  final int intervaloHoras;
  final int dias;
  final int totalTomas;

  static HorarioDeTomas? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final intervalo = (json['interval_hours'] as num?)?.toInt() ?? 0;
    final total = (json['total_doses'] as num?)?.toInt() ?? 0;
    if (intervalo <= 0 || total <= 0) return null;
    return HorarioDeTomas(
      intervaloHoras: intervalo,
      dias: (json['days'] as num?)?.toInt() ?? 0,
      totalTomas: total,
    );
  }

  Map<String, dynamic> toJson() => {
        'interval_hours': intervaloHoras,
        'days': dias,
        'total_doses': totalTomas,
      };

  /// «cada 8 horas por 5 días · 15 tomas».
  String get descripcion =>
      'cada $intervaloHoras ${intervaloHoras == 1 ? 'hora' : 'horas'} por '
      '$dias ${dias == 1 ? 'día' : 'días'} · $totalTomas '
      '${totalTomas == 1 ? 'toma' : 'tomas'}';
}

/// Una toma marcada en el servidor.
class TomaMarcada {
  const TomaMarcada({required this.numero, required this.tomada});

  final int numero;
  final bool tomada;

  factory TomaMarcada.fromJson(Map<String, dynamic> json) => TomaMarcada(
        numero: (json['dose_number'] as num?)?.toInt() ?? 0,
        tomada: json['status'] == 'taken',
      );
}

/// Un medicamento recetado, como lo necesita *Mis medicamentos*.
class Tratamiento {
  const Tratamiento({
    required this.id,
    required this.medicamento,
    required this.dosis,
    required this.frecuencia,
    required this.duracion,
    required this.indicaciones,
    required this.medico,
    required this.recetadoEl,
    required this.horario,
    required this.motivoSinHorario,
    this.tomas = const [],
  });

  final String id;
  final String medicamento;
  final String dosis;
  final String frecuencia;
  final String duracion;
  final String indicaciones;
  final String medico;
  final DateTime? recetadoEl;

  /// `null` si la indicación no tiene horario fijo o no dice cuántos días.
  final HorarioDeTomas? horario;
  final String? motivoSinHorario;
  final List<TomaMarcada> tomas;

  factory Tratamiento.fromJson(Map<String, dynamic> json) => Tratamiento(
        id: json['id'] as String? ?? '',
        medicamento: json['medication'] as String? ?? '',
        dosis: json['dose'] as String? ?? '',
        frecuencia: json['frequency'] as String? ?? '',
        duracion: json['duration'] as String? ?? '',
        indicaciones: json['instructions'] as String? ?? '',
        medico: json['practitioner_name'] as String? ?? '',
        recetadoEl: DateTime.tryParse(json['prescribed_at'] as String? ?? ''),
        horario: HorarioDeTomas.fromJson(json['schedule']),
        motivoSinHorario: json['schedule_reason'] as String?,
        tomas: (json['intakes'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(TomaMarcada.fromJson)
            .toList(),
      );
}

Future<List<Tratamiento>> verMisMedicamentos(
  ApiClient client, {
  required String patientId,
}) async {
  final data = await client
      .get('/encounters/medications/${Uri.encodeComponent(patientId)}/');
  final filas = data is Map<String, dynamic>
      ? (data['medications'] as List? ?? const [])
      : const [];
  return filas
      .whereType<Map<String, dynamic>>()
      .map(Tratamiento.fromJson)
      .toList();
}

/// Marca una toma. Si ya estaba marcada (409), cuenta como hecha: el
/// teléfono pudo haber reintentado después de perder la conexión.
Future<void> marcarToma(
  ApiClient client, {
  required String itemId,
  required int numero,
  required bool tomada,
  DateTime? programadaPara,
}) async {
  try {
    await client.post(
      '/encounters/prescription/${Uri.encodeComponent(itemId)}/intakes/',
      body: {
        'dose_number': numero,
        'status': tomada ? 'taken' : 'skipped',
        if (programadaPara != null)
          'scheduled_at': programadaPara.toUtc().toIso8601String(),
      },
    );
  } on ApiError catch (error) {
    if (error.status == 409) return;
    rethrow;
  }
}
