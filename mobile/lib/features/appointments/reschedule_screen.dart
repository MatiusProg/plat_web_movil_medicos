/// US-20 — Elegir el nuevo horario de una ficha.
///
/// Para quien reprograma es volver a elegir un turno como en US-17: se
/// reutiliza la disponibilidad de US-15 sobre el profesional de la ficha. El
/// backend hace el resto —libera el turno viejo y toma el nuevo en una sola
/// transacción— y devuelve la ficha **nueva**; la pantalla se cierra con ella
/// para que quien la abrió vaya a verla.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/availability/availability_api.dart';

import 'appointments_api.dart';
import 'formato.dart';

class RescheduleScreen extends StatefulWidget {
  const RescheduleScreen({super.key, required this.appointmentId, this.client});

  final String appointmentId;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<RescheduleScreen> createState() => _RescheduleScreenState();
}

/// La ficha que se mueve junto con los horarios entre los que se puede elegir.
class _Datos {
  const _Datos(this.ficha, this.disponibilidad);

  final Appointment ficha;
  final Disponibilidad disponibilidad;
}

class _RescheduleScreenState extends State<RescheduleScreen> {
  ApiClient? _client;
  Future<_Datos>? _futuro;
  SlotDisponible? _elegido;
  String? _fechaElegida;
  bool _ocupado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _client ??= widget.client ?? ApiClient(auth: SessionScope.maybeOf(context));
    _futuro ??= _pedir();
  }

  Future<_Datos> _pedir() async {
    final ficha = await verFicha(_client!, widget.appointmentId);
    final hoy = DateTime.now();
    String iso(DateTime d) =>
        '${d.year.toString().padLeft(4, '0')}-'
        '${d.month.toString().padLeft(2, '0')}-'
        '${d.day.toString().padLeft(2, '0')}';
    final disponibilidad = await disponibilidadConsolidada(
      _client!,
      practitionerId: ficha.practitionerId,
      from: iso(hoy),
      to: iso(hoy.add(const Duration(days: 14))),
    );
    return _Datos(ficha, disponibilidad);
  }

  void _cargar() => setState(() {
    _elegido = null;
    _fechaElegida = null;
    _futuro = _pedir();
  });

  /// Los espacios que se pueden tomar. Se descarta el turno que la ficha ya
  /// tiene: "reprogramar" al mismo horario no cambia nada.
  List<DiaDisponible> _dias(_Datos datos) {
    final actual = datos.ficha;
    final dias = <DiaDisponible>[];
    for (final dia in datos.disponibilidad.days) {
      final libres = dia.slots.where((slot) {
        if (!slot.reservable || slot.scheduleId.isEmpty) return false;
        final inicio = DateTime.tryParse(slot.start);
        final esElActual =
            inicio != null &&
            inicio.isAtSameMomentAs(actual.startsAt) &&
            slot.branchName == actual.branchName;
        return !esElActual;
      }).toList();
      if (libres.isNotEmpty) {
        dias.add(DiaDisponible(date: dia.date, slots: libres));
      }
    }
    return dias;
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(mensaje)));
  }

  Future<void> _reprogramar(Appointment ficha) async {
    final slot = _elegido!;
    final fecha = _fechaElegida ?? '';
    final seguir = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Reprogramar la ficha?'),
        content: Text(
          'Pasa de ${fechaHora(ficha.startsAt)} a $fecha a las '
          '${slot.horaInicio} en ${slot.branchName}.\n\n'
          'El turno actual queda libre para otra persona. Si la ficha ya '
          'estaba pagada, sigue pagada: no se cobra de nuevo.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Volver'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sí, reprogramar'),
          ),
        ],
      ),
    );
    if (seguir != true || !mounted) return;

    setState(() => _ocupado = true);
    try {
      final nueva = await reprogramarFicha(
        _client!,
        ficha.id,
        branchId: slot.branchId,
        scheduleId: slot.scheduleId,
        startsAt: slot.start,
      );
      if (!mounted) return;
      _avisar('Ficha reprogramada.');
      Navigator.pop(context, nueva);
    } on ApiError catch (error) {
      _avisar(error.message);
      // Otro paciente tomó el turno: se recarga para que desaparezca.
      if (error.code == 'turno_ocupado' && mounted) _cargar();
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Reprogramar ficha')),
      body: FutureBuilder<_Datos>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      error is ApiError
                          ? error.message
                          : 'No se pudieron cargar los horarios.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _cargar,
                      child: const Text('Reintentar'),
                    ),
                  ],
                ),
              ),
            );
          }

          final datos = snapshot.requireData;
          final dias = _dias(datos);
          return Column(
            children: [
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                  children: [
                    Text(
                      datos.ficha.practitionerName,
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Turno actual: ${fechaHora(datos.ficha.startsAt)} · '
                      '${datos.ficha.branchName}',
                    ),
                    const SizedBox(height: 16),
                    if (dias.isEmpty)
                      const Text(
                        'No hay otros horarios libres en las próximas dos '
                        'semanas.',
                      )
                    else
                      for (final dia in dias) _dia(dia),
                  ],
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
                  child: SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _elegido == null || _ocupado
                          ? null
                          : () => _reprogramar(datos.ficha),
                      child: Text(
                        _elegido == null
                            ? 'Elegí un horario'
                            : 'Reprogramar a las ${_elegido!.horaInicio}',
                      ),
                    ),
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Widget _dia(DiaDisponible dia) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(dia.date, style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final slot in dia.slots)
                ChoiceChip(
                  label: Text('${slot.horaInicio} · ${slot.branchName}'),
                  selected: identical(_elegido, slot),
                  selectedColor: Marca.surfaceTint,
                  onSelected: _ocupado
                      ? null
                      : (_) => setState(() {
                          _elegido = slot;
                          _fechaElegida = dia.date;
                        }),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
