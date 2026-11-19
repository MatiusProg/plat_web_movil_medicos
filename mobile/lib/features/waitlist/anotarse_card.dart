/// US-52 — La tarjeta «¿Quieres que te avisemos?» de la disponibilidad.
///
/// Se muestra cuando el profesional no tiene turnos libres: el paciente elige
/// el rango de fechas y para quién es, y se anota en la lista de espera. El
/// backend decide todo lo demás (plan, posición, si en realidad ya hay turnos):
/// acá sólo se pide y se traduce la respuesta.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/features/appointments/formato.dart' as formato;
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

import 'waitlist_api.dart';

/// El máximo de días que admite el backend entre `date_from` y `date_to`.
const int maximoDiasDeEspera = 30;

String _iso(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-'
    '${d.month.toString().padLeft(2, '0')}-'
    '${d.day.toString().padLeft(2, '0')}';

/// El mensaje que se le dice a la persona según el código del backend.
String mensajeDeListaDeEspera(ApiError error) => switch (error.code) {
  'hay_turnos' => 'Ya hay turnos libres en esas fechas: reserva uno.',
  'ya_anotado' =>
    'Ya estás en la lista de espera de este profesional en esas fechas.',
  'rango_largo' => 'Elige un rango de hasta $maximoDiasDeEspera días.',
  'rango_pasado' => 'Las fechas no pueden empezar en el pasado.',
  'rango_invalido' => 'La fecha final no puede ser anterior a la inicial.',
  _ => error.message,
};

class AnotarseCard extends StatefulWidget {
  const AnotarseCard({
    super.key,
    required this.practitionerId,
    required this.client,
    this.onHayTurnos,
  });

  final String practitionerId;
  final ApiClient client;

  /// El backend dijo `hay_turnos`: la pantalla recarga la grilla.
  final VoidCallback? onHayTurnos;

  @override
  State<AnotarseCard> createState() => _AnotarseCardState();
}

class _AnotarseCardState extends State<AnotarseCard> {
  late DateTime _desde;
  late DateTime _hasta;
  PatientOption? _paraQuien;
  bool _enviando = false;

  /// El plan no incluye la función: se dice y no se insiste.
  String? _sinPlan;

  @override
  void initState() {
    super.initState();
    final hoy = DateTime.now();
    _desde = DateTime(hoy.year, hoy.month, hoy.day);
    _hasta = _desde.add(const Duration(days: 14));
  }

  Future<void> _elegirFechas() async {
    final hoy = DateTime.now();
    final primero = DateTime(hoy.year, hoy.month, hoy.day);
    final elegido = await showDateRangePicker(
      context: context,
      initialDateRange: DateTimeRange(start: _desde, end: _hasta),
      firstDate: primero,
      lastDate: primero.add(const Duration(days: 90)),
      helpText: 'Fechas en las que te sirve un turno',
      saveText: 'Listo',
    );
    if (elegido == null || !mounted) return;
    if (elegido.end.difference(elegido.start).inDays > maximoDiasDeEspera) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Elige un rango de hasta $maximoDiasDeEspera días.'),
        ),
      );
      return;
    }
    setState(() {
      _desde = elegido.start;
      _hasta = elegido.end;
    });
  }

  Future<void> _anotarme() async {
    final paraQuien = _paraQuien;
    if (paraQuien == null) return;
    final messenger = ScaffoldMessenger.of(context);
    setState(() => _enviando = true);
    try {
      final entrada = await anotarseEnListaDeEspera(
        widget.client,
        patientId: paraQuien.id,
        practitionerId: widget.practitionerId,
        dateFrom: _iso(_desde),
        dateTo: _iso(_hasta),
      );
      final posicion = entrada.position;
      messenger.showSnackBar(
        SnackBar(
          content: Text(
            posicion == null
                ? 'Quedaste anotado. Te avisaremos cuando se libere un turno.'
                : 'Quedaste anotado. Eres el N.º $posicion de la fila.',
          ),
        ),
      );
    } on ApiError catch (error) {
      if (error.code == 'plan_limit') {
        if (mounted) setState(() => _sinPlan = error.message);
      } else {
        messenger.showSnackBar(
          SnackBar(content: Text(mensajeDeListaDeEspera(error))),
        );
        if (error.code == 'hay_turnos') widget.onHayTurnos?.call();
      }
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              '¿Quieres que te avisemos?',
              style: theme.textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            if (_sinPlan != null)
              Text(_sinPlan!)
            else ...[
              const Text(
                'Anótate en la lista de espera: si alguien cancela, te '
                'guardamos el turno 15 minutos y te avisamos.',
              ),
              const SizedBox(height: 12),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.date_range),
                title: const Text('Fechas'),
                subtitle: Text(
                  '${formato.fecha(_desde)} al ${formato.fecha(_hasta)}',
                ),
                trailing: TextButton(
                  onPressed: _enviando ? null : _elegirFechas,
                  child: const Text('Cambiar'),
                ),
              ),
              PatientSelector(
                label: '¿Para quién es?',
                client: widget.client,
                onChanged: (opcion) => setState(() => _paraQuien = opcion),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _paraQuien == null || _enviando ? null : _anotarme,
                icon: const Icon(Icons.notifications_active_outlined),
                label: const Text('Anotarme en lista de espera'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
