/// El asistente de orientación: US-31 (sugerencia de especialidad), US-34
/// (derivación a emergencia) y US-33 (reserva conversacional).
///
/// **US-33.** `suggest/` trae además `booking`, la pista de si se puede
/// reservar desde la conversación. Los horarios salen de `slots/` y la
/// reserva va por `book/`, que por dentro usa `book_appointment`: el modelo
/// propone, nunca reserva, y nada se reserva sin que el paciente confirme.
///
/// **Contrato real del endpoint** (`backend/assistant/views.py`, US-31 de
/// Karen, integrado el 16/09):
///
///     POST /api/assistant/suggest/   {"question": "…"}
///     → {"emergency": false,
///        "answer": "…",
///        "generated_by": "gemini|plantilla|regla",
///        "specialty": {"id": "…", "name": "…", "similarity": 0.71} | null,
///        "alternatives": [{…}],
///        "fragments": [{"text": "…", "source_name": "…", "similarity": …}],
///        "retrieval": {"embedding_model": "…"}}
///
/// Es el que suponía el plan del sprint, así que la pantalla lo lee sin
/// cambios. La lectura vive **sólo en este archivo** y sigue aceptando además
/// la otra forma que llegó a existir —`answer` como objeto `{text, source}` y
/// la urgencia dentro de `triage`—, porque no cuesta nada y evita que un
/// cambio de contrato deje la pantalla muda sin que nadie se entere.
library;

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/features/appointments/appointments_api.dart';

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
      source: _firstString(json, const [
        'source',
        'source_name',
        'title',
        'name',
      ]),
    );
  }
}

/// US-33 — Si se puede reservar desde la conversación, y para qué especialidad.
class BookingHint {
  const BookingHint({
    required this.available,
    required this.bookingIntent,
    this.specialtyId,
    this.specialtyName,
  });

  /// El usuario es paciente, tiene los permisos y hay especialidad. Si es
  /// `false` la pantalla no muestra nada de reserva.
  final bool available;

  /// El mensaje ya pedía un turno: los horarios se buscan solos.
  final bool bookingIntent;
  final String? specialtyId;
  final String? specialtyName;

  /// Hay con qué pedir horarios.
  bool get puedeReservar => available && specialtyId != null;

  static BookingHint? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    final specialty = json['specialty'];
    return BookingHint(
      available: json['available'] == true,
      bookingIntent: json['booking_intent'] == true,
      specialtyId: specialty is Map<String, dynamic>
          ? _firstString(specialty, const ['id'])
          : null,
      specialtyName: specialty is Map<String, dynamic>
          ? _firstString(specialty, const ['name'])
          : null,
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
    this.booking,
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

  /// US-33: `null` si el backend no la mandó.
  final BookingHint? booking;

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

    // US-34 viaja dentro de `triage`; se acepta igual en la raíz, y un objeto
    // de emergencia (con motivo, por ejemplo) también cuenta.
    final triage = _first(json, const ['triage']);
    final emergency =
        (triage is Map<String, dynamic>
            ? _first(triage, const ['is_emergency', 'emergency'])
            : null) ??
        _first(json, const ['emergency', 'is_emergency']);

    return AssistantReply(
      answer: _texto(_first(json, const ['answer', 'reply', 'message'])) ?? '',
      specialtyId: specialtyId,
      specialtyName: specialtyName,
      fragments: fragments,
      emergency: emergency == true || emergency is Map,
      booking: BookingHint.fromJson(json['booking']),
    );
  }
}

/// US-33 — Un horario real que ofrece `slots/`.
class OfferedSlot {
  const OfferedSlot({
    required this.practitionerId,
    required this.practitionerName,
    required this.branchId,
    required this.branchName,
    required this.scheduleId,
    required this.start,
    this.end,
  });

  final String practitionerId;
  final String practitionerName;
  final String branchId;
  final String branchName;
  final String scheduleId;

  /// Tal cual vino, con su zona horaria: es lo que se manda de vuelta a
  /// `book/` como `starts_at`, para que el backend lo compare con la agenda.
  final String start;
  final String? end;

  DateTime? get inicio => DateTime.tryParse(start)?.toLocal();

  static OfferedSlot? fromJson(Object? json) {
    if (json is! Map<String, dynamic>) return null;
    Map<String, dynamic> obj(String k) =>
        json[k] is Map<String, dynamic> ? json[k] as Map<String, dynamic> : const {};
    final start = json['start'];
    final scheduleId = _firstString(obj('schedule'), const ['id']);
    if (start is! String || scheduleId == null) return null;
    return OfferedSlot(
      practitionerId: _firstString(obj('practitioner'), const ['id']) ?? '',
      practitionerName:
          _firstString(obj('practitioner'), const ['full_name', 'name']) ?? '',
      branchId: _firstString(obj('branch'), const ['id']) ?? '',
      branchName: _firstString(obj('branch'), const ['name']) ?? '',
      scheduleId: scheduleId,
      start: start,
      end: json['end'] as String?,
    );
  }
}

/// US-33 — La respuesta de `slots/`.
class SlotsReply {
  const SlotsReply({
    required this.answer,
    this.emergency = false,
    this.specialtyId,
    this.specialtyName,
    this.relaxed,
    this.offers = const [],
    this.isExample = false,
  });

  final String answer;

  /// La preferencia describía una urgencia: se deriva y no hay horarios.
  final bool emergency;
  final String? specialtyId;
  final String? specialtyName;

  /// Qué se aflojó para encontrar horarios: `mismo_dia`, `misma_franja`,
  /// `proximos` o `null`. `answer` ya lo explica.
  final String? relaxed;
  final List<OfferedSlot> offers;
  final bool isExample;

  factory SlotsReply.fromJson(Map<String, dynamic> json) {
    final specialty = json['specialty'];
    final emergency = json['emergency'] == true;
    return SlotsReply(
      answer: _texto(json['answer']) ?? '',
      emergency: emergency,
      specialtyId: specialty is Map<String, dynamic>
          ? _firstString(specialty, const ['id'])
          : null,
      specialtyName: specialty is Map<String, dynamic>
          ? _firstString(specialty, const ['name'])
          : null,
      relaxed: json['relaxed'] as String?,
      // Con una urgencia no se muestra ningún horario, aunque vinieran.
      offers: emergency
          ? const []
          : (json['offers'] as List? ?? const [])
              .map(OfferedSlot.fromJson)
              .whereType<OfferedSlot>()
              .toList(),
    );
  }
}

Object? _first(Map<String, dynamic> json, List<String> keys) {
  for (final key in keys) {
    if (json[key] != null) return json[key];
  }
  return null;
}

/// El texto de `answer`. El backend lo manda como objeto `{text, source}` y el
/// plan del sprint lo suponía un String pelado; se aceptan los dos.
String? _texto(Object? value) {
  if (value is String) return value.trim().isEmpty ? null : value;
  if (value is Map<String, dynamic>) {
    return _firstString(value, const ['text', 'answer', 'message']);
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
    // `question`, no `message`: es como se llama el campo en
    // `assistant/serializers.py`. Con el nombre equivocado la respuesta es un
    // 400 y la pantalla no muestra nada.
    body: {'question': mensaje},
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
      answer: 'Lo que describes puede ser una urgencia.',
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
    answer: 'Por lo que cuentas, te conviene consultar en $especialidad.',
    specialtyName: especialidad,
    fragments: [AssistantFragment(text: fragmento, source: especialidad)],
    isExample: true,
  );
}

/// US-33 — Los horarios reales de una especialidad, según lo que el paciente
/// pidió ("el jueves por la tarde"). La preferencia puede ir vacía.
Future<SlotsReply> pedirTurnos(
  ApiClient client,
  String specialtyId,
  String preferencia, {
  bool demo = assistantDemoMode,
}) async {
  if (demo) return _turnosDeEjemplo(specialtyId);
  final texto = preferencia.trim();
  final data = await client.post(
    '/assistant/slots/',
    body: {
      'specialty': specialtyId,
      'preference': texto.length > 200 ? texto.substring(0, 200) : texto,
    },
  );
  if (data is! Map<String, dynamic>) {
    throw const FormatException('Respuesta de horarios sin formato.');
  }
  return SlotsReply.fromJson(data);
}

/// US-33 — Reserva el horario que el paciente confirmó en la hoja.
///
/// Por `/assistant/book/` y nunca por `/appointments/appointments/`: el del
/// asistente revisa que la ficha sea del titular o de un dependiente suyo y
/// deja el asiento en la bitácora. `patientId` `null` es para el titular.
Future<Appointment> reservarDesdeAsistente(
  ApiClient client, {
  String? patientId,
  required OfferedSlot turno,
  bool demo = assistantDemoMode,
}) async {
  // En el modo de ejemplo nunca se reserva de verdad.
  if (demo) {
    throw const ApiError(
      'En el modo de ejemplo no se reservan fichas.',
      'modo_ejemplo',
      400,
    );
  }
  final data = await client.post(
    '/assistant/book/',
    body: {
      'patient': patientId,
      'practitioner': turno.practitionerId,
      'branch': turno.branchId,
      'schedule': turno.scheduleId,
      'starts_at': turno.start,
    },
  );
  if (data is! Map<String, dynamic>) {
    throw const FormatException('Respuesta de la reserva sin formato.');
  }
  return Appointment.fromJson(data);
}

Future<SlotsReply> _turnosDeEjemplo(String specialtyId) async {
  await Future<void>.delayed(const Duration(milliseconds: 400));
  final manana = DateTime.now().add(const Duration(days: 1));
  String iso(int hora) => DateTime(manana.year, manana.month, manana.day, hora)
      .toIso8601String();
  OfferedSlot turno(int hora) => OfferedSlot(
        practitionerId: 'demo',
        practitionerName: 'Profesional de ejemplo',
        branchId: 'demo',
        branchName: 'Sede de ejemplo',
        scheduleId: 'demo',
        start: iso(hora),
      );
  return SlotsReply(
    answer: 'Horarios de ejemplo: en este modo no se reserva.',
    specialtyId: specialtyId,
    offers: [turno(9), turno(10)],
    isExample: true,
  );
}
