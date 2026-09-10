/// US-45 — Panel del superadministrador de plataforma.
///
/// Sólo lo que ya expone `/platform/dashboard/`: cuántas organizaciones hay
/// por estado, cuántas suscripciones vigentes por plan, y cuántas alertas de
/// aislamiento están pendientes. Sin librería de gráficos: son ocho números
/// en total, tiles de texto alcanzan y no hay una serie temporal que graficar
/// todavía.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../../core/widgets/platform_drawer.dart';
import '../../core/widgets/stat_tile.dart';
import 'metrics_api.dart';

class PlatformDashboardScreen extends StatefulWidget {
  const PlatformDashboardScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<PlatformDashboardScreen> createState() =>
      _PlatformDashboardScreenState();
}

class _PlatformDashboardScreenState extends State<PlatformDashboardScreen> {
  Future<PlatformDashboard>? _futuro;
  ApiClient? _client;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _futuro ??= fetchDashboard(client);
  }

  Future<void> _recargar() {
    final futuro = fetchDashboard(client);
    setState(() {
      _futuro = futuro;
    });
    return futuro;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Panel de la plataforma')),
      drawer: const PlatformDrawer(),
      body: FutureBuilder<PlatformDashboard>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Text(
                  error is ApiError
                      ? error.message
                      : 'No se pudo cargar el panel.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          return _Panel(datos: snapshot.data!, onRefresh: _recargar);
        },
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.datos, required this.onRefresh});

  final PlatformDashboard datos;
  final Future<void> Function() onRefresh;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final org = datos.organizations;
    final alertas = datos.alerts;

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Organizaciones', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: StatTile(label: 'Total', value: '${org.total}'),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: StatTile(
                  label: 'Activas',
                  value: '${org.active}',
                  color: Marca.primary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: 'Suspendidas',
                  value: '${org.suspended}',
                  color: org.suspended > 0 ? Marca.waiting : null,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: StatTile(label: 'Inactivas', value: '${org.inactive}'),
              ),
            ],
          ),
          const SizedBox(height: 24),

          Text('Por plan', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          if (datos.byPlan.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(
                'Todavía no hay suscripciones vigentes.',
                style: theme.textTheme.bodyMedium
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
            )
          else
            for (final plan in datos.byPlan)
              Card(
                child: ListTile(
                  title: Text(plan.planName),
                  trailing: Text(
                    '${plan.count}',
                    style: theme.textTheme.titleMedium,
                  ),
                ),
              ),
          const SizedBox(height: 24),

          Text('Alertas de aislamiento', style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: 'Pendientes',
                  value: '${alertas.pending}',
                  color: alertas.pending > 0 ? Marca.waiting : null,
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: StatTile(
                  label: 'Críticas',
                  value: '${alertas.criticalPending}',
                  color: alertas.criticalPending > 0 ? Marca.danger : null,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
