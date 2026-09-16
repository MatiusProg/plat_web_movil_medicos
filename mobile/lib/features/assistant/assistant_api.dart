/// Pantalla de chat del asistente de orientación — armazón para el corte del
/// 16/09. La historia es US-31 (y US-34 para la derivación a emergencia), de
/// Karen; desde el 17/09 este módulo pasa a ella.
///
/// **El contrato del endpoint todavía no está publicado.** El que se supone
/// acá es el del plan del sprint:
///
///     POST /api/assistant/suggest/   {"message": "…"}
///     → {"answer": "…",
///        "specialty": {"id": "…", "name": "…"} | null,
///        "fragments": [{"text": "…", "source": "…"}],
///        "emergency": false}
///
/// Por eso la lectura de la respuesta vive **sólo en este archivo** y acepta
/// también los nombres alternativos más probables (`reply`, `sources`,
/// `is_emergency`, …): si el endpoint real usa otros, se corrige acá y la
/// pantalla no se entera.
library;

import 'package:mobile/core/api/client.dart';

/// `flutter run --dart-define=ASSISTANT_DEMO=true` responde con ejemplos fijos
/// sin llamar al backend. Sirve para mostrar la pantalla mientras el endpoint
/// no esté desplegado; cada respuesta sale rotulada como ejemplo.
const bool assistantDemoMode = bool.fromEnvironment('ASSISTANT_DEMO');

class AssistantFragment {
  const AssistantFragment({required this.text, this.source});

  final String text;

  /// De dónde salió el fragmento: una especialidad, una sucursal, …
  final String? source;

  static AssistantFragment? fromJson(Object? json) {
    if (json is String) {
      return json.trim().isEmpty ? null : AssistantFragment(text: json);
    }
    if (json is! Map<String, dynamic>) return null;
    final text = _firstString(json, const ['text', 'content', 'chunk']);
    if (text == null) return null;
    return AssistantFragment(
      text: text,
      source: _firstString(json, const ['source', 'title', 'name']),
    );
  }
}

class AssistantReply {
  const AssistantReply({
    required this.answer,
    this.specialtyId,
    this.specialtyName,
    this.fragments = const [],
    this.emergency = false,
    this.isExample = false,
  });

  final String answer;
  final String? specialtyId;
  final String? specialtyName;

  /// Los fragmentos recuperados que respaldan la respuesta. Mostrarlos es lo
  /// que demuestra que el asistente no inventó.
  final List<AssistantFragment> fragments;

  /// US-34: la descripción es compatible con una urgencia. La pantalla corta
  /// el camino a la reserva y deriva.
  final bool emergency;

  /// Respuesta del modo de ejemplo, no del backend.
  final bool isExample;

  factory AssistantReply.fromJson(Map<String, dynamic> json) {
    String? specialtyId;
    String? specialtyName;
    final specialty = _first(json, const ['specialty', 'suggested_specialty']);
    if (specialty is Map<String, dynamic>) {
      specialtyId = _firstString(specialty, const ['id']);
      specialtyName = _firstString(specialty, const ['name']);
    } else if (specialty is String && specialty.trim().isNotEmpty) {
      specialtyName = specialty;
    }

    final rawFragments = _first(json, const ['fragments', 'sources', 'chunks']);
    final fragments = (rawFragments is List ? rawFragments : const [])
        .map(AssistantFragment.fromJson)
        .whereType<AssistantFragment>()
        .toList();

    // Un objeto de emergencia (con motivo, por ejemplo) también cuenta.
    final emergency = _first(json, const ['emergency', 'is_emergency']);

    return AssistantReply(
      answer: _firstString(json, const ['answer', 'reply', 'message']) ?? '',
      specialtyId: specialtyId,
      specialtyName: specialtyName,
      fragments: fragments,
      emergency: emergency == true || emergency is Map,
    );
  }
}

Object? _first(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    if (json[key] != null) return json[key];
  }
  return null;
}

String? _firstString(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    final value = json[key];
    if (value is String && value.trim().isNotEmpty) return value;
  }
  return null;
}

/// Manda el mensaje del paciente y devuelve la respuesta del asistente.
///
/// Lanza `ApiError` como cualquier otra llamada: la pantalla decide qué
/// mostrar, y nunca muestra una respuesta inventada en su lugar.
Future<AssistantReply> consultarAsistente(
  ApiClient client,
  String mensaje, {
  bool demo = assistantDemoMode,
}) async {
  if (demo) return _respuestaDeEjemplo(mensaje);

  final data = await client.post(
    '/assistant/suggest/',
    body: {'message': mensaje},
  );
  if (data is! Map<String, dynamic>) {
    throw const FormatException('Respuesta del asistente sin formato.');
  }
  return AssistantReply.fromJson(data);
}

Future<AssistantReply> _respuestaDeEjemplo(String mensaje) async {
  await Future<void>.delayed(const Duration(milliseconds: 600));
  final texto = mensaje.toLowerCase();

  bool menciona(List<String> palabras) => palabras.any(texto.contains);

  if (menciona(const [
    'dolor de pecho',
    'no puedo respirar',
    'desmay',
    'convuls',
    'sangrado',
  ])) {
    return const AssistantReply(
      answer: 'Lo que describís puede ser una urgencia.',
      emergency: true,
      isExample: true,
    );
  }

  final (
    String especialidad,
    String fragmento,
  ) = menciona(const ['piel', 'mancha', 'granos'])
      ? (
          'Dermatología',
          'Dermatología atiende afecciones de la piel, el cabello y las uñas.',
        )
      : menciona(const ['presión', 'corazón', 'palpitaciones'])
      ? (
          'Cardiología',
          'Cardiología atiende hipertensión, arritmias y controles del corazón.',
        )
      : menciona(const ['hijo', 'hija', 'bebé', 'niño', 'niña'])
      ? (
          'Pediatría',
          'Pediatría atiende a niñas y niños desde el nacimiento hasta la adolescencia.',
        )
      : (
          'Medicina General',
          'Medicina General es la primera consulta ante síntomas generales.',
        );

  return AssistantReply(
    answer: 'Por lo que contás, te conviene consultar en $especialidad.',
    specialtyName: especialidad,
    fragments: [AssistantFragment(text: fragmento, source: especialidad)],
    isExample: true,
  );
}
