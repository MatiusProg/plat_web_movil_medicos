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
///
/// US-39: y, si su médico lo aprobó, el resumen de la consulta en palabras
/// simples. Sale de `GET /api/ai/texts/mine/`, que **sólo devuelve textos
/// aprobados** (regla 14 del Sprint 4): un borrador nunca llega al teléfono.
library;

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/features/medications/medications_api.dart';

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
    this.id = '',
    required this.medication,
    required this.dose,
    required this.frequency,
    required this.duration,
    required this.instructions,
    this.horario,
    this.motivoSinHorario,
  });

  final String id;
  final String medication;
  final String dose;
  final String frequency;
  final String duration;
  final String instructions;

  /// US-49: el horario de tomas, o `null` si no tiene horario fijo.
  final HorarioDeTomas? horario;
  final String? motivoSinHorario;

  factory Medicamento.fromJson(Map<String, dynamic> json) => Medicamento(
    id: json['id'] as String? ?? '',
    horario: HorarioDeTomas.fromJson(json['schedule']),
    motivoSinHorario: json['schedule_reason'] as String?,
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
    this.id = '',
    required this.kindDisplay,
    required this.description,
    required this.notes,
    this.preparacion,
  });

  final String id;
  final String kindDisplay;
  final String description;
  final String notes;

  /// US-40: cómo prepararse, aprobado por el médico, o `null` si no hay.
  final TextoAprobado? preparacion;

  Orden conPreparacion(TextoAprobado? preparacion) => Orden(
    id: id,
    kindDisplay: kindDisplay,
    description: description,
    notes: notes,
    preparacion: preparacion,
  );

  factory Orden.fromJson(Map<String, dynamic> json) => Orden(
    id: json['id'] as String? ?? '',
    kindDisplay: json['kind_display'] as String? ?? '',
    description: json['description'] as String? ?? '',
    notes: json['notes'] as String? ?? '',
  );
}

/// US-53 — Los signos vitales que tomó el médico en la atención.
///
/// Todos opcionales: se muestra sólo lo que se tomó. El IMC y lo anormal
/// (`alertas`) ya vienen calculados del backend, con los mismos umbrales que
/// ve el médico en la web.
class SignosVitales {
  const SignosVitales({
    this.sistolica,
    this.diastolica,
    this.frecuencia,
    this.temperatura,
    this.saturacion,
    this.glucosa,
    this.peso,
    this.talla,
    this.imc,
    this.alertas = const {},
  });

  final int? sistolica;
  final int? diastolica;
  final int? frecuencia;
  final double? temperatura;
  final int? saturacion;
  final int? glucosa;
  final double? peso;
  final double? talla;
  final double? imc;

  /// `blood_pressure`, `temperature`, `spo2` → «Alta» / «Baja».
  final Map<String, String> alertas;

  static int? _entero(Object? v) => v is num ? v.toInt() : null;
  static double? _decimal(Object? v) =>
      v is num ? v.toDouble() : (v is String ? double.tryParse(v) : null);

  factory SignosVitales.fromJson(Map<String, dynamic> json) => SignosVitales(
    sistolica: _entero(json['systolic']),
    diastolica: _entero(json['diastolic']),
    frecuencia: _entero(json['heart_rate']),
    temperatura: _decimal(json['temperature']),
    saturacion: _entero(json['spo2']),
    glucosa: _entero(json['glucose']),
    peso: _decimal(json['weight_kg']),
    talla: _decimal(json['height_cm']),
    imc: _decimal(json['bmi']),
    alertas: {
      for (final e in (json['alerts'] as Map? ?? const {}).entries)
        if (e.value is String) '${e.key}': e.value as String,
    },
  );

  /// Lo que se tomó, en el orden en que lo lee el médico.
  List<({String etiqueta, String valor, String? alerta})> get filas {
    String n(num v) => v == v.roundToDouble()
        ? v.toInt().toString()
        : v.toString().replaceAll('.', ',');
    final presion = '${sistolica ?? '—'}/${diastolica ?? '—'} mmHg';
    return [
      if (sistolica != null || diastolica != null)
        (
          etiqueta: 'Presión arterial',
          valor: presion,
          alerta: alertas['blood_pressure'],
        ),
      if (frecuencia != null)
        (etiqueta: 'Frecuencia cardíaca', valor: '$frecuencia lpm', alerta: null),
      if (temperatura != null)
        (
          etiqueta: 'Temperatura',
          valor: '${n(temperatura!)} °C',
          alerta: alertas['temperature'],
        ),
      if (saturacion != null)
        (
          etiqueta: 'Saturación O₂',
          valor: '$saturacion %',
          alerta: alertas['spo2'],
        ),
      if (glucosa != null)
        (etiqueta: 'Glucosa', valor: '$glucosa mg/dL', alerta: null),
      if (peso != null) (etiqueta: 'Peso', valor: '${n(peso!)} kg', alerta: null),
      if (talla != null)
        (etiqueta: 'Talla', valor: '${n(talla!)} cm', alerta: null),
      if (imc != null) (etiqueta: 'IMC', valor: n(imc!), alerta: null),
    ];
  }
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
    this.resumen,
    this.calificacion,
    this.signos,
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

  /// US-39: el resumen aprobado por el médico, o `null` si no hay.
  final ResumenConsulta? resumen;

  /// US-48: lo que el paciente calificó, o `null` si todavía no.
  final Calificacion? calificacion;

  /// US-53: los signos vitales, o `null` si no se tomaron.
  final SignosVitales? signos;

  Atencion conResumen(
    ResumenConsulta? resumen, [
    Map<String, TextoAprobado> preparaciones = const {},
  ]) => Atencion(
    id: id,
    startsAt: startsAt,
    practitionerName: practitionerName,
    branchName: branchName,
    secciones: secciones,
    signedByName: signedByName,
    signedAt: signedAt,
    enmiendas: enmiendas,
    medicamentos: medicamentos,
    ordenes: [for (final o in ordenes) o.conPreparacion(preparaciones[o.id])],
    resumen: resumen,
    calificacion: calificacion,
    signos: signos,
  );

  /// Hay algo que bajar en PDF.
  bool get tieneReceta => medicamentos.isNotEmpty || ordenes.isNotEmpty;

  factory Atencion.fromJson(Map<String, dynamic> json) => Atencion(
    id: json['id'] as String? ?? '',
    startsAt: DateTime.tryParse(json['appointment_starts_at'] as String? ?? ''),
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
    calificacion: json['rating'] is Map<String, dynamic>
        ? Calificacion.fromJson(json['rating'] as Map<String, dynamic>)
        : null,
    signos: json['vital_signs'] is Map<String, dynamic>
        ? SignosVitales.fromJson(json['vital_signs'] as Map<String, dynamic>)
        : null,
  );
}

/// US-39 y US-40 — Un texto de la IA tal como lo aprobó el médico.
typedef TextoAprobado = ResumenConsulta;

/// US-48 — La calificación de una atención, tal como la dejó el paciente.
///
/// Se corrige durante 7 días (`editable`); después queda fija. El médico
/// nunca la recibe: sólo ve su promedio, sin nombres.
class Calificacion {
  const Calificacion({
    required this.estrellas,
    required this.comentario,
    required this.editable,
    required this.editableHasta,
  });

  final int estrellas;
  final String comentario;
  final bool editable;
  final DateTime? editableHasta;

  factory Calificacion.fromJson(Map<String, dynamic> json) => Calificacion(
    estrellas: (json['stars'] as num?)?.toInt() ?? 0,
    comentario: json['comment'] as String? ?? '',
    editable: json['editable'] as bool? ?? false,
    editableHasta: DateTime.tryParse(json['editable_until'] as String? ?? ''),
  );
}

/// El máximo de caracteres del comentario; lo vuelve a revisar el backend.
const maxComentarioCalificacion = 500;

/// US-39 — El resumen de una consulta, tal como lo aprobó el médico.
class ResumenConsulta {
  const ResumenConsulta({
    required this.encounterId,
    required this.texto,
    required this.aprobadoPor,
    required this.aprobadoEl,
    this.kind = 'consultation_summary',
    this.orderId,
  });

  final String kind;

  /// US-40: la orden de la que sale, si es una preparación.
  final String? orderId;
  final String encounterId;
  final String texto;
  final String aprobadoPor;
  final DateTime? aprobadoEl;

  factory ResumenConsulta.fromJson(Map<String, dynamic> json) =>
      ResumenConsulta(
        encounterId: json['encounter'] as String? ?? '',
        texto: (json['text'] as String? ?? '').trim(),
        aprobadoPor: json['practitioner_name'] as String? ?? '',
        aprobadoEl: DateTime.tryParse(json['approved_at'] as String? ?? ''),
        kind: json['kind'] as String? ?? 'consultation_summary',
        orderId: json['medical_order'] as String?,
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
        for (final s
            in (json['branches'] as List? ?? const [])
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
  final data = await client.get(
    '/encounters/history/${Uri.encodeComponent(patientId)}/',
  );
  final historia = HistoriaClinica.fromJson(
    data is Map<String, dynamic> ? data : const <String, dynamic>{},
  );
  if (historia.atenciones.isEmpty) return historia;

  final (resumenes, preparaciones) = await verTextosAprobados(
    client,
    patientId: patientId,
  );
  return HistoriaClinica(
    patientName: historia.patientName,
    sucursales: historia.sucursales,
    atenciones: [
      for (final a in historia.atenciones)
        a.conResumen(resumenes[a.id], preparaciones),
    ],
  );
}

/// US-39 y US-40 — Los textos aprobados de un paciente, en un solo pedido:
/// los resúmenes por atención y las preparaciones por orden.
///
/// Si no se pueden traer, la historia se muestra igual sin ellos: son una
/// ayuda, la historia clínica es lo que el paciente vino a ver.
Future<(Map<String, TextoAprobado>, Map<String, TextoAprobado>)>
verTextosAprobados(ApiClient client, {required String patientId}) async {
  try {
    final query = Uri(
      queryParameters: {'patient': patientId, 'page_size': '100'},
    ).query;
    final data = await client.get('/ai/texts/mine/?$query');
    final filas =
        (data is Map<String, dynamic>
                ? (data['results'] as List? ?? const [])
                : const [])
            .whereType<Map<String, dynamic>>()
            .map(ResumenConsulta.fromJson)
            .where((r) => r.texto.isNotEmpty)
            .toList();
    return (
      {
        for (final r in filas)
          if (r.kind == 'consultation_summary') r.encounterId: r,
      },
      {
        for (final r in filas)
          if (r.kind == 'preparation' && (r.orderId ?? '').isNotEmpty)
            r.orderId!: r,
      },
    );
  } on ApiError {
    return (const <String, TextoAprobado>{}, const <String, TextoAprobado>{});
  }
}

/// US-27 — La receta firmada de una atención, en PDF.
///
/// El backend la entrega sólo de una atención firmada y a quien tiene alcance
/// sobre el historial (el paciente o el titular de un dependiente), y deja el
/// asiento en la bitácora.
Future<ArchivoRecibido> descargarReceta(
  ApiClient client, {
  required String encounterId,
}) => client.download(
  'GET',
  '/encounters/${Uri.encodeComponent(encounterId)}/prescription.pdf',
);

/// US-48 — Calificar una atención firmada (`primera`) o cambiar lo calificado.
Future<Calificacion> calificarAtencion(
  ApiClient client, {
  required String encounterId,
  required bool primera,
  required int estrellas,
  required String comentario,
}) async {
  final ruta = '/encounters/${Uri.encodeComponent(encounterId)}/rating/';
  final cuerpo = {'stars': estrellas, 'comment': comentario};
  final data = primera
      ? await client.post(ruta, body: cuerpo)
      : await client.patch(ruta, body: cuerpo);
  final rating = data is Map<String, dynamic> ? data['rating'] : null;
  return Calificacion.fromJson(
    rating is Map<String, dynamic> ? rating : const <String, dynamic>{},
  );
}
