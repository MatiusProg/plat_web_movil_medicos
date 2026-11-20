/// US-49 — El interruptor «Recordarme» de cada medicamento.
///
/// Va en la receta de *Mi historia clínica* y en *Mis medicamentos*. Al
/// activarlo pide la hora de la primera toma y programa los avisos. Si la
/// indicación no tiene horario fijo («según dolor») no se ofrece: se dice por
/// qué.
library;

import 'package:flutter/material.dart';

import 'medications_api.dart';
import 'recordatorios.dart';

String dosDigitos(int n) => n.toString().padLeft(2, '0');

/// «hoy 08:00», «mañana 16:00» o «22/11 08:00».
String cuandoEnTexto(DateTime momento, DateTime ahora) {
  final m = momento.toLocal();
  final hoy = DateTime(ahora.year, ahora.month, ahora.day);
  final dia = DateTime(m.year, m.month, m.day);
  final hora = '${dosDigitos(m.hour)}:${dosDigitos(m.minute)}';
  final diferencia = dia.difference(hoy).inDays;
  if (diferencia == 0) return 'hoy $hora';
  if (diferencia == 1) return 'mañana $hora';
  if (diferencia == -1) return 'ayer $hora';
  return '${dosDigitos(m.day)}/${dosDigitos(m.month)} $hora';
}

class InterruptorRecordatorio extends StatelessWidget {
  const InterruptorRecordatorio({
    super.key,
    required this.recordatorios,
    required this.itemId,
    required this.patientId,
    required this.medicamento,
    required this.dosis,
    required this.horario,
    required this.motivoSinHorario,
    this.reloj,
  });

  final Recordatorios recordatorios;
  final String itemId;
  final String patientId;
  final String medicamento;
  final String dosis;
  final HorarioDeTomas? horario;
  final String? motivoSinHorario;
  final DateTime Function()? reloj;

  DateTime _ahora() => (reloj ?? DateTime.now)();

  Future<void> _activar(BuildContext context, HorarioDeTomas horario) async {
    final avisos = ScaffoldMessenger.of(context);
    final ahora = _ahora();
    final hora = await showTimePicker(
      context: context,
      helpText: 'Hora de la primera toma',
      initialTime: TimeOfDay.fromDateTime(ahora),
    );
    if (hora == null) return;
    final primera =
        DateTime(ahora.year, ahora.month, ahora.day, hora.hour, hora.minute);
    final permiso = await recordatorios.pedirPermiso();
    await recordatorios.activar(RecordatorioActivo(
      itemId: itemId,
      patientId: patientId,
      medicamento: medicamento,
      dosis: dosis,
      horario: horario,
      primeraToma: primera,
    ));
    avisos.showSnackBar(SnackBar(
      content: Text(permiso
          ? 'Te avisaremos ${horario.descripcion}.'
          : 'Recordatorio guardado, pero el teléfono no deja mostrar '
              'notificaciones: actívalas en los ajustes de la app.'),
    ));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final suave = theme.colorScheme.onSurfaceVariant;
    final horario = this.horario;
    if (horario == null) {
      return Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Text(
          motivoSinHorario ?? 'Esta indicación no tiene horario fijo.',
          style: theme.textTheme.labelSmall?.copyWith(color: suave),
        ),
      );
    }
    return ListenableBuilder(
      listenable: recordatorios,
      builder: (context, _) {
        final activo = recordatorios.activos[itemId];
        final ahora = _ahora();
        final proxima = activo?.proximaToma(ahora);
        final detalle = activo == null
            ? horario.descripcion
            : proxima == null
                ? 'Tratamiento terminado'
                : 'Próxima toma: ${cuandoEnTexto(activo.momentoDe(proxima), ahora)}';
        return SwitchListTile(
          contentPadding: EdgeInsets.zero,
          dense: true,
          title: const Text('Recordarme'),
          subtitle: Text(detalle),
          value: activo != null,
          onChanged: (encender) => encender
              ? _activar(context, horario)
              : recordatorios.desactivar(itemId),
        );
      },
    );
  }
}
