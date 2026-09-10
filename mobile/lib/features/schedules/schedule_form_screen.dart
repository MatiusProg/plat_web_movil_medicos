/// US-13 — Alta y edición de una regla de agenda.
///
/// Un solo widget para las dos cosas, como el formulario de planes:
/// `existente == null` es alta. El profesional no se elige acá —viene del
/// listado, que ya filtró por él— para no ofrecer mover una regla de un
/// profesional a otro, que es una operación distinta y peligrosa.
///
/// Las horas se piden con el reloj del sistema y no como texto: escribir
/// "8:00" a mano se presta a "800", "8", "08:00 am", y el backend espera
/// `HH:MM:SS`.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../catalog/branches_api.dart';
import 'schedules_api.dart';

class ScheduleFormScreen extends StatefulWidget {
  const ScheduleFormScreen({
    super.key,
    required this.practitionerId,
    this.existente,
    this.client,
  });

  final String practitionerId;
  final Agenda? existente;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<ScheduleFormScreen> createState() => _ScheduleFormScreenState();
}

class _ScheduleFormScreenState extends State<ScheduleFormScreen> {
  final _formulario = GlobalKey<FormState>();

  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<Sucursal>? _sucursales;
  String? _errorSucursales;

  late String? _sucursal = widget.existente?.branch;
  late int _dia = widget.existente?.weekday ?? DateTime.now().weekday - 1;
  late TimeOfDay _desde = _hora(widget.existente?.startTime, 8);
  late TimeOfDay _hasta = _hora(widget.existente?.endTime, 12);
  late final _duracion = TextEditingController(
    text: '${widget.existente?.slotMinutes ?? 30}',
  );
  late final _cupo = TextEditingController(
    text: '${widget.existente?.capacity ?? 1}',
  );
  late DateTime _vigenteDesde = _fecha(widget.existente?.validFrom);
  late DateTime? _vigenteHasta = widget.existente?.validUntil == null
      ? null
      : _fecha(widget.existente!.validUntil);

  bool _guardando = false;
  ApiError? _error;

  bool get _esEdicion => widget.existente != null;

  static TimeOfDay _hora(String? valor, int porOmision) {
    if (valor == null || valor.length < 5) {
      return TimeOfDay(hour: porOmision, minute: 0);
    }
    return TimeOfDay(
      hour: int.tryParse(valor.substring(0, 2)) ?? porOmision,
      minute: int.tryParse(valor.substring(3, 5)) ?? 0,
    );
  }

  static DateTime _fecha(String? iso) =>
      iso == null ? DateTime.now() : DateTime.tryParse(iso) ?? DateTime.now();

  static String _iso(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-'
      '${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')}';

  /// El backend espera `HH:MM:SS`.
  static String _hhmmss(TimeOfDay t) =>
      '${t.hour.toString().padLeft(2, '0')}:'
      '${t.minute.toString().padLeft(2, '0')}:00';

  /// Los minutos desde medianoche, para comparar dos horas sin fecha.
  static int _minutos(TimeOfDay t) => t.hour * 60 + t.minute;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_sucursales == null && _errorSucursales == null) _cargarSucursales();
  }

  Future<void> _cargarSucursales() async {
    try {
      final sucursales = await listarSucursales(client);
      if (!mounted) return;
      setState(() {
        _sucursales = sucursales;
        // Al crear, la primera sede activa viene elegida: es lo más común y
        // ahorra un toque.
        _sucursal ??= sucursales.isEmpty ? null : sucursales.first.id;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _errorSucursales = error.message);
    }
  }

  @override
  void dispose() {
    _duracion.dispose();
    _cupo.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!(_formulario.currentState?.validate() ?? false)) return;
    if (_sucursal == null) {
      setState(() => _error = null);
      _avisar('Elegí una sucursal.');
      return;
    }
    if (_minutos(_hasta) <= _minutos(_desde)) {
      _avisar('La hora de fin tiene que ser posterior a la de inicio.');
      return;
    }

    setState(() {
      _guardando = true;
      _error = null;
    });

    var salio = false;
    try {
      if (_esEdicion) {
        await editarAgenda(
          client,
          widget.existente!.id,
          practitioner: widget.practitionerId,
          branch: _sucursal!,
          weekday: _dia,
          startTime: _hhmmss(_desde),
          endTime: _hhmmss(_hasta),
          slotMinutes: int.parse(_duracion.text.trim()),
          capacity: int.parse(_cupo.text.trim()),
          validFrom: _iso(_vigenteDesde),
          validUntil: _vigenteHasta == null ? null : _iso(_vigenteHasta!),
        );
      } else {
        await crearAgenda(
          client,
          practitioner: widget.practitionerId,
          branch: _sucursal!,
          weekday: _dia,
          startTime: _hhmmss(_desde),
          endTime: _hhmmss(_hasta),
          slotMinutes: int.parse(_duracion.text.trim()),
          capacity: int.parse(_cupo.text.trim()),
          validFrom: _iso(_vigenteDesde),
          validUntil: _vigenteHasta == null ? null : _iso(_vigenteHasta!),
        );
      }
      if (!mounted) return;
      salio = true;
      Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } catch (_) {
      if (!mounted) return;
      _avisar('No se pudo guardar la regla. Intentá de nuevo.');
    } finally {
      // Como en el resto de los formularios: sin esto, una excepción que no
      // sea `ApiError` deja el botón deshabilitado para siempre.
      if (mounted && !salio) setState(() => _guardando = false);
    }
  }

  void _avisar(String mensaje) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(mensaje)));

  Future<void> _elegirHora({required bool inicio}) async {
    final elegida = await showTimePicker(
      context: context,
      initialTime: inicio ? _desde : _hasta,
    );
    if (elegida == null) return;
    setState(() => inicio ? _desde = elegida : _hasta = elegida);
  }

  Future<void> _elegirFecha({required bool desde}) async {
    final base = desde ? _vigenteDesde : (_vigenteHasta ?? _vigenteDesde);
    final elegida = await showDatePicker(
      context: context,
      initialDate: base,
      firstDate: DateTime(DateTime.now().year - 1),
      lastDate: DateTime(DateTime.now().year + 5),
    );
    if (elegida == null) return;
    setState(() => desde ? _vigenteDesde = elegida : _vigenteHasta = elegida);
  }

  @override
  Widget build(BuildContext context) {
    final sucursales = _sucursales;

    return Scaffold(
      appBar: AppBar(
        title: Text(_esEdicion ? 'Editar regla' : 'Nueva regla'),
      ),
      body: Form(
        key: _formulario,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            if (_errorSucursales != null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _errorSucursales!,
                  style: TextStyle(color: Theme.of(context).colorScheme.error),
                ),
              ),

            DropdownButtonFormField<String>(
              initialValue: _sucursal,
              decoration: const InputDecoration(
                labelText: 'Sucursal',
                border: OutlineInputBorder(),
              ),
              items: [
                for (final s in sucursales ?? const <Sucursal>[])
                  DropdownMenuItem(value: s.id, child: Text(s.name)),
              ],
              onChanged: sucursales == null
                  ? null
                  : (valor) => setState(() => _sucursal = valor),
              validator: (v) =>
                  v == null || v.isEmpty ? 'Elegí una sucursal.' : null,
            ),
            const SizedBox(height: 16),

            DropdownButtonFormField<int>(
              initialValue: _dia,
              decoration: const InputDecoration(
                labelText: 'Día de la semana',
                border: OutlineInputBorder(),
              ),
              items: [
                for (var i = 0; i < diasDeLaSemana.length; i++)
                  DropdownMenuItem(value: i, child: Text(diasDeLaSemana[i])),
              ],
              onChanged: (valor) => setState(() => _dia = valor ?? _dia),
            ),
            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: _BotonDeCampo(
                    etiqueta: 'Desde',
                    valor: _desde.format(context),
                    icono: Icons.schedule,
                    onTap: () => _elegirHora(inicio: true),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _BotonDeCampo(
                    etiqueta: 'Hasta',
                    valor: _hasta.format(context),
                    icono: Icons.schedule,
                    onTap: () => _elegirHora(inicio: false),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            Row(
              children: [
                Expanded(
                  child: TextFormField(
                    controller: _duracion,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Minutos por turno',
                      border: OutlineInputBorder(),
                    ),
                    validator: _enteroPositivo,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: TextFormField(
                    controller: _cupo,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Cupo por turno',
                      border: OutlineInputBorder(),
                    ),
                    validator: _enteroPositivo,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            _BotonDeCampo(
              etiqueta: 'Vigente desde',
              valor: _iso(_vigenteDesde),
              icono: Icons.event,
              onTap: () => _elegirFecha(desde: true),
            ),
            const SizedBox(height: 12),
            _BotonDeCampo(
              etiqueta: 'Vigente hasta (opcional)',
              valor: _vigenteHasta == null ? 'Sin fecha de fin' : _iso(_vigenteHasta!),
              icono: Icons.event_busy,
              onTap: () => _elegirFecha(desde: false),
              onLimpiar: _vigenteHasta == null
                  ? null
                  : () => setState(() => _vigenteHasta = null),
            ),

            if (_error != null) ...[
              const SizedBox(height: 16),
              Text(
                _error!.message,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],

            const SizedBox(height: 24),
            FilledButton(
              onPressed: _guardando ? null : _guardar,
              child: Text(_guardando ? 'Guardando…' : 'Guardar'),
            ),
          ],
        ),
      ),
    );
  }

  static String? _enteroPositivo(String? valor) {
    final n = int.tryParse((valor ?? '').trim());
    if (n == null || n <= 0) return 'Poné un número mayor que cero.';
    return null;
  }
}

/// Un campo que en vez de escribirse se toca y abre un selector.
class _BotonDeCampo extends StatelessWidget {
  const _BotonDeCampo({
    required this.etiqueta,
    required this.valor,
    required this.icono,
    required this.onTap,
    this.onLimpiar,
  });

  final String etiqueta;
  final String valor;
  final IconData icono;
  final VoidCallback onTap;
  final VoidCallback? onLimpiar;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: InputDecorator(
          decoration: InputDecoration(
            labelText: etiqueta,
            border: const OutlineInputBorder(),
            suffixIcon: onLimpiar == null
                ? Icon(icono)
                : IconButton(
                    icon: const Icon(Icons.clear),
                    tooltip: 'Quitar la fecha de fin',
                    onPressed: onLimpiar,
                  ),
          ),
          child: Text(valor),
        ),
      );
}
