/// US-07 — El alta de una persona a cargo.
///
/// El documento es opcional y está dicho en la pantalla: el caso que da sentido
/// a la historia es el recién nacido, que todavía no tiene ninguno. Es también
/// lo que la base admite —una ficha sin documento vale si hay un titular que
/// responda por ella— y lo que la pantalla tiene que dejar claro, o quien la
/// use va a inventar un número para poder seguir.
///
/// El punto (c) —documento ya registrado— llega como un 409 con código
/// `documento_existente`, y se resuelve preguntando en vez de fallando: si es
/// la misma persona, se vincula la ficha que ya está en el centro médico en
/// lugar de crear un duplicado. El backend sólo vincula si el nombre, el
/// apellido y la fecha de nacimiento coinciden con los que la ficha ya tenía,
/// así que la confirmación no es un cheque en blanco.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';

import 'dependents_api.dart';

class DependentFormScreen extends StatefulWidget {
  const DependentFormScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<DependentFormScreen> createState() => _DependentFormScreenState();
}

class _DependentFormScreenState extends State<DependentFormScreen> {
  final _formulario = GlobalKey<FormState>();
  final _nombre = TextEditingController();
  final _apellido = TextEditingController();
  final _documento = TextEditingController();

  String _parentesco = 'child';
  String? _sexo;
  DateTime? _nacimiento;

  bool _guardando = false;
  ApiError? _error;

  ApiClient? _client;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void dispose() {
    _nombre.dispose();
    _apellido.dispose();
    _documento.dispose();
    super.dispose();
  }

  DependienteNuevo get _datos => DependienteNuevo(
        firstName: _nombre.text.trim(),
        lastName: _apellido.text.trim(),
        relationship: _parentesco,
        documentNumber: _documento.text.trim(),
        birthDate: _nacimiento?.toIso8601String().substring(0, 10),
        sex: _sexo,
      );

  Future<void> _guardar({bool confirmLink = false}) async {
    if (!(_formulario.currentState?.validate() ?? false)) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    // El `finally` no es de estilo: sin él, cualquier excepción que no sea
    // `ApiError` -por ejemplo la que tira el cast del cuerpo si el servidor
    // contesta 201 sin JSON- dejaba `_guardando` en `true` para siempre. El
    // botón quedaba deshabilitado, sin ningún mensaje, y la única salida era
    // abandonar el formulario perdiendo todo lo cargado.
    var salio = false;
    try {
      await crearDependiente(client, _datos, confirmLink: confirmLink);
      if (!mounted) return;
      salio = true;
      Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
      if (error.code == 'documento_existente') await _ofrecerVincular();
    } finally {
      if (mounted && !salio) setState(() => _guardando = false);
    }
  }

  Future<void> _ofrecerVincular() async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Esa persona ya está registrada'),
        content: const Text(
          'Ya hay una ficha con ese documento en el centro médico. Si es la '
          'persona que querés agregar, se vincula la ficha que ya existe con '
          'todo su historial, en lugar de crear una nueva.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Revisar los datos'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Es la misma persona'),
          ),
        ],
      ),
    );
    if (confirmado == true) await _guardar(confirmLink: true);
  }

  Future<void> _elegirFecha() async {
    final hoy = DateTime.now();
    final elegida = await showDatePicker(
      context: context,
      initialDate: _nacimiento ?? DateTime(hoy.year - 8, hoy.month, hoy.day),
      firstDate: DateTime(hoy.year - 120),
      lastDate: hoy,
      helpText: 'Fecha de nacimiento',
    );
    if (elegida != null) setState(() => _nacimiento = elegida);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(title: const Text('Agregar persona a cargo')),
      body: Form(
        key: _formulario,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            if (_error != null && _error!.code != 'documento_existente')
              Padding(
                padding: const EdgeInsets.only(bottom: 16),
                child: Text(
                  _error!.message,
                  style: TextStyle(color: theme.colorScheme.error),
                ),
              ),

            TextFormField(
              controller: _nombre,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                labelText: 'Nombres',
                border: OutlineInputBorder(),
              ),
              validator: (valor) =>
                  (valor ?? '').trim().isEmpty ? 'Poné el nombre.' : null,
            ),
            const SizedBox(height: 12),

            TextFormField(
              controller: _apellido,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(
                labelText: 'Apellidos',
                border: OutlineInputBorder(),
              ),
              validator: (valor) =>
                  (valor ?? '').trim().isEmpty ? 'Poné el apellido.' : null,
            ),
            const SizedBox(height: 12),

            DropdownButtonFormField<String>(
              initialValue: _parentesco,
              decoration: const InputDecoration(
                labelText: 'Qué es tuyo',
                border: OutlineInputBorder(),
              ),
              items: [
                for (final entrada in parentescos.entries)
                  DropdownMenuItem(
                    value: entrada.key,
                    child: Text(entrada.value),
                  ),
              ],
              onChanged: (valor) =>
                  setState(() => _parentesco = valor ?? 'child'),
            ),
            const SizedBox(height: 12),

            TextFormField(
              controller: _documento,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Documento (opcional)',
                helperText: 'Dejalo vacío si todavía no tiene.',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 12),

            OutlinedButton.icon(
              onPressed: _elegirFecha,
              icon: const Icon(Icons.calendar_today_outlined),
              label: Text(
                _nacimiento == null
                    ? 'Fecha de nacimiento'
                    : _nacimiento!.toIso8601String().substring(0, 10),
              ),
            ),
            const SizedBox(height: 12),

            DropdownButtonFormField<String>(
              initialValue: _sexo,
              decoration: const InputDecoration(
                labelText: 'Sexo (opcional)',
                border: OutlineInputBorder(),
              ),
              items: const [
                DropdownMenuItem(value: 'F', child: Text('Femenino')),
                DropdownMenuItem(value: 'M', child: Text('Masculino')),
                DropdownMenuItem(value: 'X', child: Text('Otro')),
              ],
              onChanged: (valor) => setState(() => _sexo = valor),
            ),
            const SizedBox(height: 24),

            FilledButton(
              onPressed: _guardando ? null : () => _guardar(),
              child: Text(_guardando ? 'Guardando…' : 'Agregar'),
            ),
          ],
        ),
      ),
    );
  }
}
