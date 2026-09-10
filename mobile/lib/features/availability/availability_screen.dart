/// US-15 — Pantalla de disponibilidad consolidada.
///
/// Los espacios libres del profesional entre todas sus sucursales, agrupados
/// por día y etiquetados con la sede. Los que ya no se pueden reservar
/// —profesional o sucursal inactivos— se ven atenuados con el motivo, no
/// desaparecen. La reserva llega en el Sprint 2.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';

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
    );
  }

  void _cargar() => setState(() {
        _futuro = _pedir();
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.practitionerName ?? 'Disponibilidad'),
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
              for (final dia in datos.days) _DiaSeccion(dia: dia),
            ],
          );
        },
      ),
    );
  }
}

class _DiaSeccion extends StatelessWidget {
  const _DiaSeccion({required this.dia});

  final DiaDisponible dia;

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
              for (final slot in dia.slots) _SlotChip(slot: slot),
            ],
          ),
        ],
      ),
    );
  }
}

class _SlotChip extends StatelessWidget {
  const _SlotChip({required this.slot});

  final SlotDisponible slot;

  @override
  Widget build(BuildContext context) {
    final atenuado = !slot.reservable;
    final motivo = slot.reason == 'profesional_inactivo'
        ? 'Profesional inactivo'
        : slot.reason == 'sucursal_inactiva'
            ? 'Sucursal inactiva'
            : null;

    return Tooltip(
      message: motivo ?? 'La reserva llega en el Sprint 2',
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
