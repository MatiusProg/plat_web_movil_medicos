/// US-47 — El chat entre el paciente atendido y el médico de esa atención.
///
/// Una conversación por atención firmada
/// (`/api/messaging/encounters/<id>/chat/`). Quién entra lo decide el backend:
/// el paciente o el titular del dependiente, y el médico de la atención; a
/// cualquier otro, 404. No hay tiempo real: la pantalla abierta vuelve a pedir
/// la conversación cada 10 segundos.
library;

import 'package:mobile/core/api/client.dart';

const maxCaracteresMensaje = 2000;

class MensajeChat {
  const MensajeChat({
    required this.id,
    required this.body,
    required this.authorName,
    required this.createdAt,
    required this.mine,
  });

  final String id;
  final String body;
  final String authorName;
  final DateTime? createdAt;
  final bool mine;

  factory MensajeChat.fromJson(Map<String, dynamic> json) => MensajeChat(
        id: json['id'] as String? ?? '',
        body: json['body'] as String? ?? '',
        authorName: json['author_name'] as String? ?? '',
        createdAt: DateTime.tryParse(json['created_at'] as String? ?? ''),
        mine: json['mine'] as bool? ?? false,
      );
}

class Conversacion {
  const Conversacion({
    required this.practitionerName,
    required this.patientName,
    required this.encounterDate,
    required this.closesAt,
    required this.canWrite,
    required this.closedReason,
    required this.windowDays,
    required this.notice,
    required this.receta,
    required this.ordenes,
    required this.mensajes,
  });

  final String practitionerName;
  final String patientName;
  final DateTime? encounterDate;
  final DateTime? closesAt;
  final bool canWrite;

  /// `closed` (la cerró el médico), `expired` (venció la ventana) o `null`.
  final String? closedReason;
  final int windowDays;
  final String notice;

  /// Una línea por medicamento: «Paracetamol · 500 mg · cada 8 h · 5 días».
  final List<String> receta;

  /// Una línea por orden: «Laboratorio: Hemograma».
  final List<String> ordenes;
  final List<MensajeChat> mensajes;

  factory Conversacion.fromJson(Map<String, dynamic> json) {
    String linea(Map<String, dynamic> p) => [
          p['medication'],
          p['dose'],
          p['frequency'],
          p['duration'],
        ].whereType<String>().where((s) => s.isNotEmpty).join(' · ');
    return Conversacion(
      practitionerName: json['practitioner_name'] as String? ?? '',
      patientName: json['patient_name'] as String? ?? '',
      encounterDate: DateTime.tryParse(json['encounter_date'] as String? ?? ''),
      closesAt: DateTime.tryParse(json['closes_at'] as String? ?? ''),
      canWrite: json['can_write'] as bool? ?? false,
      closedReason: json['closed_reason'] as String?,
      windowDays: json['window_days'] as int? ?? 15,
      notice: json['notice'] as String? ?? '',
      receta: [
        for (final p in (json['prescription'] as List? ?? const []))
          linea(p as Map<String, dynamic>),
      ],
      ordenes: [
        for (final o in (json['orders'] as List? ?? const []))
          '${(o as Map<String, dynamic>)['kind_display']}: ${o['description']}',
      ],
      mensajes: [
        for (final m in (json['messages'] as List? ?? const []))
          MensajeChat.fromJson(m as Map<String, dynamic>),
      ],
    );
  }
}

String _ruta(String encounterId, [String resto = '']) =>
    '/messaging/encounters/${Uri.encodeComponent(encounterId)}/chat/$resto';

Future<Conversacion> verConversacion(ApiClient client, {required String encounterId}) async =>
    Conversacion.fromJson(
        await client.get(_ruta(encounterId)) as Map<String, dynamic>);

/// Manda el mensaje. Devuelve el texto de la derivación a emergencias si la
/// barrera de US-34 disparó con lo que escribió el paciente, o `null`.
Future<String?> escribirMensaje(
  ApiClient client, {
  required String encounterId,
  required String body,
}) async {
  final respuesta = await client.post(_ruta(encounterId, 'messages/'),
      body: {'body': body}) as Map<String, dynamic>;
  final urgencia = respuesta['emergency'] as Map<String, dynamic>?;
  return urgencia?['message'] as String?;
}
