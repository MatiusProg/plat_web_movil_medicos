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

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _client ??= widget.client ?? ApiClient(auth: SessionScope.maybeOf(context));
    _futuro ??= _pedir();
  }

  Future<List<Appointment>> _pedir() async =>
      ordenarParaLista(await misFichas(_client!));

  Future<void> _recargar() async {
    setState(() => _futuro = _pedir());
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
          if (fichas.isEmpty) {
            return RefreshIndicator(
              onRefresh: _recargar,
              child: ListView(
                children: [
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
              itemCount: fichas.length,
              separatorBuilder: (_, _) => const Divider(height: 1),
              itemBuilder: (context, i) {
                final ficha = fichas[i];
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
