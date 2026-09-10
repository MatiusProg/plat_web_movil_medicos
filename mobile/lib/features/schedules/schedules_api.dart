/// US-13 — Agendas médicas: las reglas de las que salen los espacios.
///
/// Es el espejo móvil de `frontend/src/api/agenda.ts`, con el mismo contrato:
/// una agenda es **una regla semanal** —este profesional, en esta sede, los
/// martes de 08:00 a 12:00, en turnos de 30 minutos— y de ella el backend
/// deriva los espacios reservables. No se guardan turnos sueltos.
///
/// La baja es `DELETE` y no un `PATCH is_active: false`: así lo resuelve el
/// backend, que la convierte en baja lógica. Reactivar, en cambio, sí es un
/// `PATCH`, porque no hay endpoint para revivir.
library;

import '../../core/api/client.dart';

/// Los días como los numera el backend (`weekday`), de lunes a domingo.
///
/// Se guarda acá y no en la pantalla porque lo usan el listado, el formulario
/// y el calendario, y tres copias del mismo array terminan discrepando.
const diasDeLaSemana = <String>[
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo',
];

String nombreDelDia(int weekday) =>
    weekday >= 0 && weekday < diasDeLaSemana.length
        ? diasDeLaSemana[weekday]
        : 'Día $weekday';

/// `"08:00:00"` -> `"08:00"`. El backend manda segundos que nadie necesita ver.
String horaCorta(String hora) => hora.length >= 5 ? hora.substring(0, 5) : hora;

class Agenda {
  const Agenda({
    required this.id,
    required this.practitioner,
    required this.practitionerName,
    required this.branch,
    required this.branchName,
    required this.weekday,
    required this.startTime,
    required this.endTime,
    required this.slotMinutes,
    required this.capacity,
    required this.validFrom,
    required this.validUntil,
    required this.isActive,
  });

  final String id;
  final String practitioner;
  final String practitionerName;
  final String branch;
  final String branchName;

  /// 0 = lunes, 6 = domingo.
  final int weekday;

  /// `"HH:MM:SS"`, tal como viaja.
  final String startTime;
  final String endTime;

  final int slotMinutes;
  final int capacity;

  /// `"YYYY-MM-DD"`. `validUntil` nulo = sin fecha de fin.
  final String validFrom;
  final String? validUntil;

  final bool isActive;

  factory Agenda.fromJson(Map<String, dynamic> json) => Agenda(
        id: json['id'] as String? ?? '',
        practitioner: json['practitioner'] as String? ?? '',
        practitionerName: json['practitioner_name'] as String? ?? '',
        branch: json['branch'] as String? ?? '',
        branchName: json['branch_name'] as String? ?? '',
        weekday: json['weekday'] as int? ?? 0,
        startTime: json['start_time'] as String? ?? '',
        endTime: json['end_time'] as String? ?? '',
        slotMinutes: json['slot_minutes'] as int? ?? 0,
        capacity: json['capacity'] as int? ?? 1,
        validFrom: json['valid_from'] as String? ?? '',
        validUntil: json['valid_until'] as String?,
        isActive: json['is_active'] as bool? ?? false,
      );
}

/// Las reglas, opcionalmente filtradas por profesional o sede.
///
/// Sin scroll infinito, como el resto del catálogo administrativo: son unas
/// pocas reglas por profesional, no cientos de filas.
Future<List<Agenda>> listarAgendas(
  ApiClient client, {
  String? practitionerId,
  String? branchId,
}) async {
  final parametros = <String>[
    if (practitionerId != null && practitionerId.isNotEmpty)
      'practitioner=$practitionerId',
    if (branchId != null && branchId.isNotEmpty) 'branch=$branchId',
  ];
  final sufijo = parametros.isEmpty ? '' : '?${parametros.join('&')}';

  final data = await client.get('/scheduling/schedules/$sufijo');
  final mapa = data as Map<String, dynamic>;
  return (mapa['results'] as List? ?? const [])
      .map((e) => Agenda.fromJson(e as Map<String, dynamic>))
      .toList();
}

Map<String, dynamic> _cuerpo({
  required String practitioner,
  required String branch,
  required int weekday,
  required String startTime,
  required String endTime,
  required int slotMinutes,
  required int capacity,
  required String validFrom,
  String? validUntil,
}) => {
      'practitioner': practitioner,
      'branch': branch,
      'weekday': weekday,
      'start_time': startTime,
      'end_time': endTime,
      'slot_minutes': slotMinutes,
      'capacity': capacity,
      'valid_from': validFrom,
      'valid_until': validUntil,
    };

Future<Agenda> crearAgenda(
  ApiClient client, {
  required String practitioner,
  required String branch,
  required int weekday,
  required String startTime,
  required String endTime,
  required int slotMinutes,
  required int capacity,
  required String validFrom,
  String? validUntil,
}) async {
  final data = await client.post(
    '/scheduling/schedules/',
    body: _cuerpo(
      practitioner: practitioner,
      branch: branch,
      weekday: weekday,
      startTime: startTime,
      endTime: endTime,
      slotMinutes: slotMinutes,
      capacity: capacity,
      validFrom: validFrom,
      validUntil: validUntil,
    ),
  );
  return Agenda.fromJson(data as Map<String, dynamic>);
}

Future<Agenda> editarAgenda(
  ApiClient client,
  String id, {
  required String practitioner,
  required String branch,
  required int weekday,
  required String startTime,
  required String endTime,
  required int slotMinutes,
  required int capacity,
  required String validFrom,
  String? validUntil,
}) async {
  final data = await client.patch(
    '/scheduling/schedules/$id/',
    body: _cuerpo(
      practitioner: practitioner,
      branch: branch,
      weekday: weekday,
      startTime: startTime,
      endTime: endTime,
      slotMinutes: slotMinutes,
      capacity: capacity,
      validFrom: validFrom,
      validUntil: validUntil,
    ),
  );
  return Agenda.fromJson(data as Map<String, dynamic>);
}

/// Baja lógica. El backend la marca inactiva, no la borra.
Future<void> darDeBajaAgenda(ApiClient client, String id) =>
    client.delete('/scheduling/schedules/$id/');

/// Vuelve a activar una regla dada de baja.
Future<Agenda> reactivarAgenda(ApiClient client, String id) async {
  final data = await client.patch(
    '/scheduling/schedules/$id/',
    body: {'is_active': true},
  );
  return Agenda.fromJson(data as Map<String, dynamic>);
}
