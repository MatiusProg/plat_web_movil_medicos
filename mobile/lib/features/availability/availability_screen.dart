/// US-15 — Pantalla de disponibilidad consolidada.
///
/// Los espacios libres del profesional entre todas sus sucursales, agrupados
/// por día y etiquetados con la sede. Los que ya no se pueden reservar
/// —profesional o sucursal inactivos— se ven atenuados con el motivo, no
/// desaparecen.
///
/// US-17 (Sprint 2): tocar un espacio libre lo reserva. Se elige para quién
/// es la ficha —uno mismo o una persona a cargo—, se confirma, y la ficha
/// nace pendiente de pago: de ahí se va directo a su detalle para pagarla.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

import 'availability_api.dart';

class AvailabilityScreen extends StatefulWidget {
  const AvailabilityScreen({
    super.key,
    required this.practitionerId,
    this.practitionerName,
    this.client,
  });

  final String practitionerId;
  final String? practitionerName;

  /// Sólo para pruebas: un cliente con un `http.Client` de mentira.
  @visibleForTesting
  final ApiClient? client;

  @override
  State<AvailabilityScreen> createState() => _AvailabilityScreenState();
}

class _AvailabilityScreenState extends State<AvailabilityScreen> {
  ApiClient? _client;
  Future<Disponibilidad>? _futuro;

  /// El nombre que vino en la respuesta.
  ///
  /// Quien llega desde la búsqueda no trae `practitionerName` -ahí se navega
  /// sólo con el id-, así que el título decía "Disponibilidad" a secas y el
  /// paciente veía una grilla de horarios sin saber de quién eran. El dato ya
  /// venía en la respuesta y nadie lo usaba.
  String? _nombreDeLaRespuesta;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // `SessionScope.of` no se puede llamar en `initState`; acá sí.
    _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));
    _futuro ??= _pedir();
  }

  Future<Disponibilidad> _pedir() {
    final hoy = DateTime.now();
    String iso(DateTime d) =>
        '${d.year.toString().padLeft(4, '0')}-'
        '${d.month.toString().padLeft(2, '0')}-'
        '${d.day.toString().padLeft(2, '0')}';

    return disponibilidadConsolidada(
      _client!,
      practitionerId: widget.practitionerId,
      from: iso(hoy),
      to: iso(hoy.add(const Duration(days: 14))),
    ).then((datos) {
      // `_futuro` se fija en `didChangeDependencies` y no en `build`, así que
      // este `setState` repinta el título sin volver a disparar la petición.
      if (mounted && datos.practitionerName.isNotEmpty) {
        setState(() => _nombreDeLaRespuesta = datos.practitionerName);
      }
      return datos;
    });
  }

  void _cargar() => setState(() {
        _futuro = _pedir();
      });

  /// US-17 — Confirma el turno y reserva.
  ///
  /// El backend recalcula el turno contra la agenda y decide; acá sólo se
  /// pide. Si otro paciente lo tomó entre que se mostró y que se tocó, vuelve
  /// `turno_ocupado` y se recarga la grilla para que desaparezca.
  Future<void> _reservar(SlotDisponible slot, String fecha) async {
    final paraQuien = await showModalBottomSheet<PatientOption>(
      context: context,
      isScrollControlled: true,
      builder: (context) => _ConfirmarReserva(
        slot: slot,
        fecha: fecha,
        profesional:
            widget.practitionerName ?? _nombreDeLaRespuesta ?? 'el profesional',
        client: _client!,
      ),
    );
    if (paraQuien == null || !mounted) return;

    final messenger = ScaffoldMessenger.of(context);
    try {
      final ficha = await reservarFicha(
        _client!,
        patientId: paraQuien.id,
        practitionerId: widget.practitionerId,
        branchId: slot.branchId,
        scheduleId: slot.scheduleId,
        startsAt: slot.start,
      );
      if (!mounted) return;
      messenger.showSnackBar(const SnackBar(
        content: Text('Ficha reservada. Pagala para confirmarla.'),
      ));
      await context.push('/appointments/${ficha.id}');
      if (mounted) _cargar();
    } on ApiError catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.message)));
      if (error.code == 'turno_ocupado' && mounted) _cargar();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(
          widget.practitionerName ?? _nombreDeLaRespuesta ?? 'Disponibilidad',
        ),
      ),
      body: FutureBuilder<Disponibilidad>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            final mensaje = error is ApiError
                ? error.message
                : 'No se pudo cargar la disponibilidad.';
            return _Reintentar(mensaje: mensaje, onReintentar: _cargar);
          }

          final datos = snapshot.data;
          if (datos == null || datos.totalEspacios == 0) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text('No hay espacios libres en las próximas dos semanas.'),
              ),
            );
          }

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              if (!datos.practitionerActive)
                const Padding(
                  padding: EdgeInsets.only(bottom: 12),
                  child: Text(
                    'Este profesional está inactivo: los espacios no se pueden '
                    'reservar.',
                    style: TextStyle(color: Marca.waiting),
                  ),
                ),
              for (final dia in datos.days)
                _DiaSeccion(dia: dia, onReservar: _reservar),
            ],
          );
        },
      ),
    );
  }
}

class _DiaSeccion extends StatelessWidget {
  const _DiaSeccion({required this.dia, required this.onReservar});

  final DiaDisponible dia;
  final void Function(SlotDisponible slot, String fecha) onReservar;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            dia.date,
            style: Theme.of(context).textTheme.titleSmall,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final slot in dia.slots)
                _SlotChip(
                  slot: slot,
                  onTap: slot.reservable && slot.scheduleId.isNotEmpty
                      ? () => onReservar(slot, dia.date)
                      : null,
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _SlotChip extends StatelessWidget {
  const _SlotChip({required this.slot, this.onTap});

  final SlotDisponible slot;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final atenuado = !slot.reservable;
    final motivo = slot.reason == 'profesional_inactivo'
        ? 'Profesional inactivo'
        : slot.reason == 'sucursal_inactiva'
            ? 'Sucursal inactiva'
            : null;

    return Tooltip(
      message: motivo ?? 'Tocá para reservar',
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: atenuado ? Marca.ink100 : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Marca.ink300),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              slot.horaInicio,
              style: TextStyle(
                fontWeight: FontWeight.w600,
                decoration: atenuado ? TextDecoration.lineThrough : null,
                color: atenuado ? Marca.ink500 : Marca.ink900,
              ),
            ),
            const SizedBox(width: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Marca.surfaceTint,
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                slot.branchName,
                style: const TextStyle(fontSize: 11, color: Marca.primaryDark),
              ),
            ),
            if (slot.capacity > 1) ...[
              const SizedBox(width: 6),
              Text('cupo ${slot.capacity}',
                  style: const TextStyle(fontSize: 11, color: Marca.ink500)),
            ],
          ],
        ),
      ),
      ),
    );
  }
}

/// La hoja de confirmación: qué turno, con quién y para quién.
class _ConfirmarReserva extends StatefulWidget {
  const _ConfirmarReserva({
    required this.slot,
    required this.fecha,
    required this.profesional,
    required this.client,
  });

  final SlotDisponible slot;
  final String fecha;
  final String profesional;
  final ApiClient client;

  @override
  State<_ConfirmarReserva> createState() => _ConfirmarReservaState();
}

class _ConfirmarReservaState extends State<_ConfirmarReserva> {
  PatientOption? _paraQuien;
  bool _sinOpciones = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20, 20, 20, 20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Reservar ficha', style: theme.textTheme.titleLarge),
          const SizedBox(height: 12),
          Text('${widget.profesional} · ${widget.slot.branchName}'),
          Text('${widget.fecha} a las ${widget.slot.horaInicio}'),
          const SizedBox(height: 16),
          PatientSelector(
            label: '¿Para quién es la ficha?',
            client: widget.client,
            onChanged: (opcion) => setState(() => _paraQuien = opcion),
            onSinSeleccion: () => setState(() => _sinOpciones = true),
          ),
          if (_sinOpciones)
            const Padding(
              padding: EdgeInsets.only(top: 8),
              child: Text('No se pudo saber para quién reservar.'),
            ),
          const SizedBox(height: 12),
          Text(
            'La ficha queda reservada y pendiente de pago: se confirma cuando '
            'el pago se acredita.',
            style: theme.textTheme.bodySmall,
          ),
          const SizedBox(height: 16),
          FilledButton(
            onPressed: _paraQuien == null
                ? null
                : () => Navigator.pop(context, _paraQuien),
            child: const Text('Reservar'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Cancelar'),
          ),
        ],
      ),
    );
  }
}

class _Reintentar extends StatelessWidget {
  const _Reintentar({required this.mensaje, required this.onReintentar});

  final String mensaje;
  final VoidCallback onReintentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(mensaje, textAlign: TextAlign.center),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: onReintentar,
              child: const Text('Reintentar'),
            ),
          ],
        ),
      ),
    );
  }
}
