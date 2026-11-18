/// "Mis fichas": las del paciente y las de sus personas a cargo (US-07).
///
/// Próximas primero. Si la lista no carga por falta de red, se ofrecen los
/// comprobantes guardados en el teléfono (US-19): es justo el momento en que
/// el paciente está en la puerta del centro médico sin señal.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/features/waitlist/waitlist_api.dart';

import 'appointment_detail_screen.dart';
import 'appointments_api.dart';
import 'formato.dart';

class MyAppointmentsScreen extends StatefulWidget {
  const MyAppointmentsScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<MyAppointmentsScreen> createState() => _MyAppointmentsScreenState();
}

class _MyAppointmentsScreenState extends State<MyAppointmentsScreen> {
  ApiClient? _client;
  Future<List<Appointment>>? _futuro;

  /// US-52: la lista de espera. Vacía y deshabilitada hasta que llegue, y si
  /// falla se queda así: nunca debe romper la pantalla de fichas.
  ListaDeEspera _espera = ListaDeEspera.vacia;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_client == null) {
      _client =
          widget.client ?? ApiClient(auth: SessionScope.maybeOf(context));
      _futuro = _pedir();
      _cargarEspera();
    }
  }

  Future<void> _cargarEspera() async {
    try {
      final espera = await miListaDeEspera(_client!);
      if (mounted) setState(() => _espera = espera);
    } catch (_) {
      // Un fallo acá no es asunto de esta pantalla: se ignora en silencio.
    }
  }

  Future<void> _salirDeLaLista(WaitlistEntry entrada) async {
    final seguir = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Salir de la lista de espera?'),
        content: Text(
          'Ya no te avisaremos si se libera un turno con '
          '${entrada.destino}.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No, quedarme'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sí, salir'),
          ),
        ],
      ),
    );
    if (seguir != true || !mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    try {
      await salirDeListaDeEspera(_client!, entrada.id);
      messenger.showSnackBar(
        const SnackBar(content: Text('Saliste de la lista de espera.')),
      );
    } on ApiError catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.message)));
    }
    await _cargarEspera();
  }

  Future<List<Appointment>> _pedir() async =>
      ordenarParaLista(await misFichas(_client!));

  Future<void> _recargar() async {
    setState(() => _futuro = _pedir());
    _cargarEspera();
    await _futuro!.catchError((_) => <Appointment>[]);
  }

  Future<void> _abrir(Appointment ficha) async {
    await context.push('/appointments/${ficha.id}');
    if (mounted) _recargar();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mis fichas'),
        actions: [
          IconButton(
            tooltip: 'Mis comprobantes',
            onPressed: () => context.push('/receipts'),
            icon: const Icon(Icons.qr_code_2),
          ),
        ],
      ),
      body: FutureBuilder<List<Appointment>>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            final sinRed = error is ApiError && error.isOffline;
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      error is ApiError
                          ? error.message
                          : 'No se pudieron cargar tus fichas.',
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 16),
                    FilledButton(
                      onPressed: _recargar,
                      child: const Text('Reintentar'),
                    ),
                    if (sinRed) ...[
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        onPressed: () => context.push('/receipts'),
                        icon: const Icon(Icons.qr_code_2),
                        label: const Text('Ver comprobantes guardados'),
                      ),
                    ],
                  ],
                ),
              ),
            );
          }

          final fichas = snapshot.data ?? const <Appointment>[];
          final hayEspera = _espera.enabled && _espera.entries.isNotEmpty;
          if (fichas.isEmpty) {
            return RefreshIndicator(
              onRefresh: _recargar,
              child: ListView(
                children: [
                  if (hayEspera)
                    _EnListaDeEspera(
                      entradas: _espera.entries,
                      onSalir: _salirDeLaLista,
                    ),
                  const SizedBox(height: 80),
                  const Padding(
                    padding: EdgeInsets.symmetric(horizontal: 24),
                    child: Text(
                      'Todavía no tenés fichas. Buscá un profesional y elegí un '
                      'horario libre para reservar.',
                      textAlign: TextAlign.center,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Center(
                    child: FilledButton.icon(
                      onPressed: () => context.push('/specialties'),
                      icon: const Icon(Icons.search),
                      label: const Text('Buscar profesionales'),
                    ),
                  ),
                ],
              ),
            );
          }

          return RefreshIndicator(
            onRefresh: _recargar,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 8),
              itemCount: fichas.length + (hayEspera ? 1 : 0),
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, i) {
                if (hayEspera && i == 0) {
                  return _EnListaDeEspera(
                    entradas: _espera.entries,
                    onSalir: _salirDeLaLista,
                  );
                }
                final ficha = fichas[hayEspera ? i - 1 : i];
                return ListTile(
                  title: Text(ficha.practitionerName),
                  subtitle: Text(
                    '${fechaHora(ficha.startsAt)} · ${ficha.branchName}'
                    '${ficha.patientName.isEmpty ? '' : '\n${ficha.patientName}'}',
                  ),
                  isThreeLine: ficha.patientName.isNotEmpty,
                  trailing: StatusChip(status: ficha.status),
                  onTap: () => _abrir(ficha),
                );
              },
            ),
          );
        },
      ),
    );
  }
}

/// US-52 — «En lista de espera»: a quién se espera, cuándo y en qué lugar de
/// la fila. Si ya se le ofreció un turno (`position == null`) la ficha
/// pendiente aparece abajo, en la lista de fichas.
class _EnListaDeEspera extends StatelessWidget {
  const _EnListaDeEspera({required this.entradas, required this.onSalir});

  final List<WaitlistEntry> entradas;
  final void Function(WaitlistEntry entrada) onSalir;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('En lista de espera', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final entrada in entradas)
            Card(
              margin: const EdgeInsets.only(bottom: 8),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(entrada.destino, style: theme.textTheme.titleSmall),
                    const SizedBox(height: 4),
                    Text('Fechas: ${entrada.rango}'),
                    if (entrada.patientName.isNotEmpty)
                      Text('Para: ${entrada.patientName}'),
                    if (entrada.position != null)
                      Text('Eres el ${entrada.position}.º'),
                    if (entrada.isOffered)
                      const Text('Te guardamos un turno: revisa tus fichas.'),
                    Align(
                      alignment: Alignment.centerRight,
                      child: TextButton(
                        onPressed: () => onSalir(entrada),
                        child: const Text('Salir de la lista'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
