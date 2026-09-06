/// US-07 (h) — El selector de *"¿para quién es esta ficha?"*.
///
/// **Es un widget compartido, no una parte privada de la pantalla de
/// dependientes.** Lo consume US-08 para elegir de quién son los antecedentes,
/// y la reserva del Sprint 2 para elegir de quién es la ficha. Está publicado
/// con esa intención: si cada pantalla armara su propia lista de "para quién",
/// dentro de dos sprints habría tres versiones con tres criterios distintos
/// sobre qué dependiente mostrar y en qué orden.
///
/// La lista la arma el backend en un solo endpoint —titular primero, después
/// los dependientes activos— por la misma razón.
///
/// Uso:
///
///     PatientSelector(
///       selectedId: _paraQuien?.id,
///       onChanged: (opcion) => setState(() => _paraQuien = opcion),
///     )
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';

import 'dependents_api.dart';

class PatientSelector extends StatefulWidget {
  const PatientSelector({
    super.key,
    required this.onChanged,
    this.selectedId,
    this.label = '¿Para quién es?',
    this.client,
  });

  /// Se llama al cargar —con el titular ya elegido— y en cada cambio.
  ///
  /// Avisar de la selección inicial es a propósito: quien usa el selector no
  /// tiene que repetir la regla de "por omisión, uno mismo".
  final ValueChanged<PatientOption> onChanged;

  final String? selectedId;
  final String label;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<PatientSelector> createState() => _PatientSelectorState();
}

class _PatientSelectorState extends State<PatientSelector> {
  List<PatientOption>? _opciones;
  String? _elegido;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_opciones == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    final client = widget.client ?? ApiClient(auth: SessionScope.of(context));
    try {
      final opciones = await listarOpcionesDePaciente(client);
      if (!mounted) return;
      setState(() {
        _opciones = opciones;
        _elegido = widget.selectedId ??
            (opciones.isEmpty ? null : opciones.first.id);
      });
      // El titular queda elegido por omisión: reservar para uno mismo es el
      // caso más común y buscarse a uno mismo en una lista sería absurdo.
      final inicial = _opcionPorId(_elegido);
      if (inicial != null) widget.onChanged(inicial);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  PatientOption? _opcionPorId(String? id) {
    if (id == null) return null;
    for (final opcion in _opciones ?? const <PatientOption>[]) {
      if (opcion.id == id) return opcion;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error));
    }

    final opciones = _opciones;
    if (opciones == null) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 12),
        child: LinearProgressIndicator(),
      );
    }

    // Con una sola opción no hay nada que elegir: mostrar un desplegable de un
    // elemento es ruido. Se dice de quién es y listo.
    if (opciones.length == 1) {
      return ListTile(
        contentPadding: EdgeInsets.zero,
        leading: const Icon(Icons.person_outline),
        title: Text(widget.label),
        subtitle: Text(opciones.first.fullName),
      );
    }

    return DropdownButtonFormField<String>(
      initialValue: _elegido,
      decoration: InputDecoration(
        labelText: widget.label,
        border: const OutlineInputBorder(),
      ),
      items: [
        for (final opcion in opciones)
          DropdownMenuItem(
            value: opcion.id,
            child: Text(
              opcion.isSelf
                  ? opcion.fullName
                  : '${opcion.fullName} · ${opcion.relationshipLabel}',
              overflow: TextOverflow.ellipsis,
            ),
          ),
      ],
      onChanged: (id) {
        final opcion = _opcionPorId(id);
        if (opcion == null) return;
        setState(() => _elegido = id);
        widget.onChanged(opcion);
      },
    );
  }
}
