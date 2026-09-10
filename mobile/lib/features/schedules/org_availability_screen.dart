/// US-14 — Disponibilidad consolidada, para quien administra.
///
/// Equivale a `frontend/src/paginas/Disponibilidad.tsx`: los espacios libres
/// de un profesional en todas las sedes donde atiende, en una sola vista.
///
/// **No reimplementa la grilla de horarios.** Elegir el profesional es lo
/// único que falta acá; mostrar los huecos ya lo hace
/// `features/availability/availability_screen.dart`, que se escribió para el
/// paciente y sirve igual. Duplicarla habría dejado dos vistas del mismo dato
/// que envejecen distinto.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import '../search/search_api.dart';

class OrgAvailabilityScreen extends StatefulWidget {
  const OrgAvailabilityScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<OrgAvailabilityScreen> createState() => _OrgAvailabilityScreenState();
}

class _OrgAvailabilityScreenState extends State<OrgAvailabilityScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<ProfesionalTarjeta>? _profesionales;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_profesionales == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final pagina = await buscarProfesionales(client);
      if (!mounted) return;
      setState(() => _profesionales = pagina.results);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final profesionales = _profesionales;

    return Scaffold(
      appBar: AppBar(title: const Text('Disponibilidad')),
      drawer: const OrganizationDrawer(),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            Text(
              'Elegí un profesional para ver sus espacios libres de las '
              'próximas dos semanas, en todas las sedes donde atiende.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),

            if (_error != null)
              Column(
                children: [
                  Text(
                    _error!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: _cargar,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reintentar'),
                  ),
                ],
              )
            else if (profesionales == null)
              const Center(child: Padding(
                padding: EdgeInsets.all(24),
                child: CircularProgressIndicator(),
              ))
            else if (profesionales.isEmpty)
              const Text('Todavía no hay profesionales cargados.')
            else
              for (final p in profesionales)
                Card(
                  margin: const EdgeInsets.only(bottom: 8),
                  child: ListTile(
                    title: Text(p.fullName),
                    subtitle: p.specialties.isEmpty
                        ? null
                        : Text(p.specialties.join(' · ')),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push(
                      '/professionals/${p.id}/availability',
                    ),
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
