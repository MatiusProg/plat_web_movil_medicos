/// US-08 — Los antecedentes propios y los de las personas a cargo.
///
/// Una sola pantalla para ambos casos (punto c), con el selector compartido de
/// US-07 arriba: cambiar de persona recarga la lista, y no hay dos pantallas
/// casi iguales que mantener.
///
/// **La leyenda de "declarado, no diagnosticado" está a la vista y no en la
/// letra chica.** Es el punto (d), y es lo que evita que alguien anote acá lo
/// que le dijo el médico creyendo que queda como diagnóstico —o al revés, que
/// no lo anote creyendo que el médico ya lo sabe—.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

import 'history_api.dart';

class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  ApiClient? _client;
  PatientOption? _paraQuien;
  List<Antecedente>? _antecedentes;
  String? _error;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  Future<void> _cargar() async {
    final paciente = _paraQuien;
    if (paciente == null) return;
    try {
      final lista = await listarAntecedentes(client, patientId: paciente.id);
      if (!mounted) return;
      setState(() {
        _antecedentes = lista;
        _error = null;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  void _cambiarPersona(PatientOption opcion) {
    if (_paraQuien?.id == opcion.id) return;
    setState(() {
      _paraQuien = opcion;
      _antecedentes = null;
      _error = null;
    });
    _cargar();
  }

  /// El selector terminó y no hay a quién elegir.
  ///
  /// Se sale del estado de carga con una lista vacía: así la pantalla muestra
  /// sus secciones vacías en vez del indicador eterno. El selector ya explica
  /// arriba lo suyo si lo que hubo fue un error.
  void _sinPersona() {
    if (!mounted || _paraQuien != null) return;
    setState(() => _antecedentes = const []);
  }

  Future<void> _agregar() async {
    final paciente = _paraQuien;
    if (paciente == null) return;

    final nuevo = await showModalBottomSheet<
        ({String kind, String description, String severity})>(
      context: context,
      isScrollControlled: true,
      builder: (context) => const _FormularioAntecedente(),
    );
    if (nuevo == null) return;

    try {
      await registrarAntecedente(
        client,
        patientId: paciente.id,
        kind: nuevo.kind,
        description: nuevo.description,
        severity: nuevo.severity,
      );
      await _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
    } catch (_) {
      // Lo que no es `ApiError` -el cast del cuerpo cuando el servidor
      // contesta sin JSON, por ejemplo- se escapaba en silencio: el
      // antecedente no se guardaba y el paciente no se enteraba de nada.
      _avisar('No se pudo guardar el antecedente. Intentá de nuevo.');
    }
  }

  Future<void> _quitar(Antecedente antecedente) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('¿Quitar "${antecedente.description}"?'),
        content: const Text(
          'Deja de figurar entre los antecedentes vigentes. Queda registrado '
          'que alguna vez lo declaraste.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Quitar'),
          ),
        ],
      ),
    );
    if (confirmado != true) return;

    try {
      await quitarAntecedente(client, antecedente.id);
      await _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
    }
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(mensaje)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Antecedentes')),
      floatingActionButton: _paraQuien == null
          ? null
          : FloatingActionButton.extended(
              onPressed: _agregar,
              icon: const Icon(Icons.add),
              label: const Text('Agregar'),
            ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
        children: [
          // El selector es de US-07 y se reutiliza tal cual. La regla de "por
          // omisión, uno mismo" vive allá, no acá.
          PatientSelector(
            client: widget.client,
            onChanged: _cambiarPersona,
            // Sin esto, cuando el selector no tenía a quién elegir -lista
            // vacía, o error- nunca avisaba, y acá abajo quedaba un indicador
            // de carga girando para siempre.
            onSinSeleccion: _sinPersona,
            label: '¿De quién son?',
          ),
          const SizedBox(height: 12),

          Card(
            color: theme.colorScheme.surfaceContainerHighest,
            child: const Padding(
              padding: EdgeInsets.all(12),
              child: Text(
                'Esto es lo que declarás vos. No reemplaza al diagnóstico del '
                'médico: sirve para que el profesional lo vea al abrir la '
                'consulta.',
              ),
            ),
          ),
          const SizedBox(height: 12),

          if (_error != null)
            Text(_error!, style: TextStyle(color: theme.colorScheme.error))
          else if (_antecedentes == null)
            const Center(child: Padding(
              padding: EdgeInsets.all(24),
              child: CircularProgressIndicator(),
            ))
          else
            ..._secciones(theme),
        ],
      ),
    );
  }

  List<Widget> _secciones(ThemeData theme) {
    final antecedentes = _antecedentes ?? const <Antecedente>[];
    if (antecedentes.isEmpty) {
      return [
        Padding(
          padding: const EdgeInsets.symmetric(vertical: 24),
          child: Text(
            'Todavía no hay nada cargado. Agregá alergias, condiciones '
            'crónicas y la medicación que tomás habitualmente.',
            style: theme.textTheme.bodyMedium,
          ),
        ),
      ];
    }

    final widgets = <Widget>[];
    for (final tipo in tiposDeAntecedente) {
      final delTipo =
          antecedentes.where((a) => a.kind == tipo.code).toList();
      if (delTipo.isEmpty) continue;

      widgets
        ..add(Padding(
          padding: const EdgeInsets.fromLTRB(4, 12, 4, 6),
          child: Text(tipo.plural, style: theme.textTheme.titleSmall),
        ))
        ..addAll(delTipo.map(
          (antecedente) => Card(
            child: ListTile(
              leading: CircleAvatar(
                radius: 18,
                backgroundColor: Marca.surfaceTint,
                child: const Icon(
                  Icons.medical_information_outlined,
                  color: Marca.primary,
                  size: 18,
                ),
              ),
              title: Text(antecedente.description),
              subtitle: Text(
                antecedente.severity.isEmpty
                    ? 'Declarado el ${antecedente.recordedAt}'
                    : '${antecedente.severityLabel} · declarado el '
                        '${antecedente.recordedAt}',
              ),
              trailing: IconButton(
                icon: const Icon(Icons.close),
                tooltip: 'Quitar',
                onPressed: () => _quitar(antecedente),
              ),
            ),
          ),
        ));
    }
    return widgets;
  }
}

/// El alta, en una hoja y no en una pantalla: son tres campos y se vuelve al
/// listado enseguida.
class _FormularioAntecedente extends StatefulWidget {
  const _FormularioAntecedente();

  @override
  State<_FormularioAntecedente> createState() => _FormularioAntecedenteState();
}

class _FormularioAntecedenteState extends State<_FormularioAntecedente> {
  final _descripcion = TextEditingController();
  String _tipo = 'allergy';
  String _severidad = 'moderate';

  @override
  void dispose() {
    _descripcion.dispose();
    super.dispose();
  }

  bool get _esAlergia => _tipo == 'allergy';

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        16, 16, 16, MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('Nuevo antecedente',
              style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 16),

          DropdownButtonFormField<String>(
            initialValue: _tipo,
            decoration: const InputDecoration(
              labelText: 'Tipo',
              border: OutlineInputBorder(),
            ),
            items: [
              for (final tipo in tiposDeAntecedente)
                DropdownMenuItem(value: tipo.code, child: Text(tipo.label)),
            ],
            onChanged: (valor) => setState(() => _tipo = valor ?? 'allergy'),
          ),
          const SizedBox(height: 12),

          TextField(
            controller: _descripcion,
            decoration: InputDecoration(
              labelText: _esAlergia ? 'A qué sos alérgico/a' : 'Cuál',
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),

          // La severidad es sólo de las alergias (punto b): en los otros dos
          // tipos no se muestra, porque una medicación "grave" no significa
          // nada y el backend la rechaza.
          if (_esAlergia)
            DropdownButtonFormField<String>(
              initialValue: _severidad,
              decoration: const InputDecoration(
                labelText: 'Qué tan grave es la reacción',
                border: OutlineInputBorder(),
              ),
              items: [
                for (final entrada in severidades.entries)
                  DropdownMenuItem(
                    value: entrada.key,
                    child: Text(entrada.value),
                  ),
              ],
              onChanged: (valor) =>
                  setState(() => _severidad = valor ?? 'moderate'),
            ),
          const SizedBox(height: 20),

          FilledButton(
            onPressed: () {
              final descripcion = _descripcion.text.trim();
              if (descripcion.isEmpty) return;
              Navigator.of(context).pop((
                kind: _tipo,
                description: descripcion,
                severity: _esAlergia ? _severidad : '',
              ));
            },
            child: const Text('Guardar'),
          ),
        ],
      ),
    );
  }
}
