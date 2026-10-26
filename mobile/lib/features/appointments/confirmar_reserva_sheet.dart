/// La hoja de confirmación de una reserva: qué turno, con quién y para quién.
///
/// La comparten la disponibilidad (US-17) y el asistente (US-33). Sólo
/// muestra el turno y devuelve la persona elegida con `Navigator.pop`; la
/// reserva la hace quien abrió la hoja, cada uno por su endpoint. Cerrarla sin
/// tocar *Reservar* devuelve `null` y no reserva nada.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

class ConfirmarReservaSheet extends StatefulWidget {
  const ConfirmarReservaSheet({
    super.key,
    required this.profesional,
    required this.sede,
    required this.cuando,
    required this.client,
  });

  final String profesional;
  final String sede;

  /// La fecha y la hora, ya escritas para leer: "jue 15/10/2026 a las 08:00".
  final String cuando;
  final ApiClient client;

  @override
  State<ConfirmarReservaSheet> createState() => _ConfirmarReservaSheetState();
}

class _ConfirmarReservaSheetState extends State<ConfirmarReservaSheet> {
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
          Text('${widget.profesional} · ${widget.sede}'),
          Text(widget.cuando),
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
