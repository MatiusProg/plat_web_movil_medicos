/// US-13 — Agendas médicas.
///
/// Equivale a `frontend/src/paginas/Agendas.tsx`. Se elige un profesional y se
/// ven sus reglas semanales: de ellas el backend deriva los espacios que la
/// gente reserva. Acá se pueden crear, editar, dar de baja y reactivar.
///
/// **Se pide por profesional y no todo junto** por lo mismo que la web: una
/// organización con veinte profesionales tiene cien reglas, y una lista de
/// cien líneas en un teléfono no se lee. El selector es el filtro.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import '../search/search_api.dart';
import 'schedules_api.dart';

class SchedulesScreen extends StatefulWidget {
  const SchedulesScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<SchedulesScreen> createState() => _SchedulesScreenState();
}

class _SchedulesScreenState extends State<SchedulesScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<ProfesionalTarjeta>? _profesionales;
  String? _elegido;

  List<Agenda>? _agendas;
  bool _cargandoAgendas = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_profesionales == null && _error == null) _cargarProfesionales();
  }

  Future<void> _cargarProfesionales() async {
    try {
      final pagina = await buscarProfesionales(client);
      if (!mounted) return;
      setState(() {
        _profesionales = pagina.results;
        _elegido = pagina.results.isEmpty ? null : pagina.results.first.id;
      });
      if (_elegido != null) await _cargarAgendas();
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _cargarAgendas() async {
    final profesional = _elegido;
    if (profesional == null) return;

    setState(() {
      _cargandoAgendas = true;
      _error = null;
    });
    try {
      final agendas = await listarAgendas(client, practitionerId: profesional);
      if (!mounted) return;
      // Ordenadas por día y hora: la semana se lee de corrido, que es como se
      // piensa una agenda. El backend no garantiza ningún orden.
      agendas.sort((a, b) {
        final dia = a.weekday.compareTo(b.weekday);
        return dia != 0 ? dia : a.startTime.compareTo(b.startTime);
      });
      setState(() => _agendas = agendas);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _cargandoAgendas = false);
    }
  }

  Future<void> _alternarActiva(Agenda agenda) async {
    try {
      if (agenda.isActive) {
        await darDeBajaAgenda(client, agenda.id);
      } else {
        await reactivarAgenda(client, agenda.id);
      }
      await _cargarAgendas();
    } on ApiError catch (error) {
      _avisar(error.message);
    } catch (_) {
      _avisar('No se pudo cambiar la regla. Intentá de nuevo.');
    }
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(mensaje)));
  }

  Future<void> _abrirFormulario({Agenda? existente}) async {
    final profesional = _elegido;
    if (profesional == null) return;

    final guardado = await context.push<bool>(
      '/org/agendas/form',
      extra: {'practitioner': profesional, 'agenda': existente},
    );
    if (guardado == true) await _cargarAgendas();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profesionales = _profesionales;

    return Scaffold(
      appBar: AppBar(title: const Text('Agendas')),
      drawer: const OrganizationDrawer(),
      floatingActionButton: _elegido == null
          ? null
          : FloatingActionButton.extended(
              onPressed: () => _abrirFormulario(),
              icon: const Icon(Icons.add),
              label: const Text('Nueva regla'),
            ),
      body: RefreshIndicator(
        onRefresh: _cargarAgendas,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            Text(
              'La agenda se guarda como regla; de ella se derivan los espacios '
              'reservables.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),

            if (profesionales == null && _error == null)
              const Center(child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ))
            else if (profesionales != null && profesionales.isEmpty)
              const Text(
                'Todavía no hay profesionales cargados. Agregá uno desde '
                'Profesionales para poder darle agenda.',
              )
            else if (profesionales != null)
              DropdownButtonFormField<String>(
                initialValue: _elegido,
                decoration: const InputDecoration(
                  labelText: 'Profesional',
                  border: OutlineInputBorder(),
                ),
                items: [
                  for (final p in profesionales)
                    DropdownMenuItem(value: p.id, child: Text(p.fullName)),
                ],
                onChanged: (valor) {
                  setState(() {
                    _elegido = valor;
                    _agendas = null;
                  });
                  _cargarAgendas();
                },
              ),

            const SizedBox(height: 16),

            if (_error != null)
              _ErrorConReintento(mensaje: _error!, onReintentar: _cargarAgendas)
            else if (_cargandoAgendas || (_elegido != null && _agendas == null))
              const Center(child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ))
            else if (_agendas != null && _agendas!.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  'Este profesional todavía no tiene reglas de agenda. '
                  'Tocá "Nueva regla" para crear la primera.',
                ),
              )
            else
              for (final agenda in _agendas ?? const <Agenda>[])
                _TarjetaDeRegla(
                  agenda: agenda,
                  onEditar: () => _abrirFormulario(existente: agenda),
                  onAlternar: () => _alternarActiva(agenda),
                ),
          ],
        ),
      ),
    );
  }
}

class _TarjetaDeRegla extends StatelessWidget {
  const _TarjetaDeRegla({
    required this.agenda,
    required this.onEditar,
    required this.onAlternar,
  });

  final Agenda agenda;
  final VoidCallback onEditar;
  final VoidCallback onAlternar;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Text(
                  nombreDelDia(agenda.weekday),
                  style: theme.textTheme.titleMedium,
                ),
                const SizedBox(width: 8),
                Text(
                  '${horaCorta(agenda.startTime)}–${horaCorta(agenda.endTime)}',
                  style: theme.textTheme.titleSmall,
                ),
                const Spacer(),
                if (!agenda.isActive)
                  Chip(
                    label: const Text('De baja'),
                    visualDensity: VisualDensity.compact,
                    backgroundColor: theme.colorScheme.surfaceContainerHighest,
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${agenda.branchName} · turnos de ${agenda.slotMinutes} min · '
              'cupo ${agenda.capacity}',
              style: theme.textTheme.bodySmall,
            ),
            if (agenda.validUntil != null)
              Text(
                'Vigente hasta ${agenda.validUntil}',
                style: theme.textTheme.bodySmall,
              ),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(onPressed: onEditar, child: const Text('Editar')),
                TextButton(
                  onPressed: onAlternar,
                  child: Text(agenda.isActive ? 'Dar de baja' : 'Reactivar'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Un error que no deja la pantalla inservible: se puede volver a intentar sin
/// salir y entrar.
class _ErrorConReintento extends StatelessWidget {
  const _ErrorConReintento({required this.mensaje, required this.onReintentar});

  final String mensaje;
  final Future<void> Function() onReintentar;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 24),
      child: Column(
        children: [
          Text(
            mensaje,
            textAlign: TextAlign.center,
            style: TextStyle(color: theme.colorScheme.error),
          ),
          const SizedBox(height: 12),
          FilledButton.tonalIcon(
            onPressed: onReintentar,
            icon: const Icon(Icons.refresh),
            label: const Text('Reintentar'),
          ),
        ],
      ),
    );
  }
}
