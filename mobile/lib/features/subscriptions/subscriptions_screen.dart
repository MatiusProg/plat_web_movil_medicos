/// US-44 — Suscripciones vigentes de todas las organizaciones.
///
/// Espejo de `frontend/src/paginas/Suscripciones.tsx`: resumen calculado en
/// cliente sobre la lista ya traída (nada de esto le pega de nuevo al
/// backend), búsqueda local, y dos acciones por fila.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../../core/widgets/platform_drawer.dart';
import '../../core/widgets/stat_tile.dart';
import 'subscriptions_api.dart';

class SubscriptionsScreen extends StatefulWidget {
  const SubscriptionsScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<SubscriptionsScreen> createState() => _SubscriptionsScreenState();
}

class _SubscriptionsScreenState extends State<SubscriptionsScreen> {
  Future<List<Subscription>>? _futuro;
  ApiClient? _client;
  String _busqueda = '';

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _futuro ??= listSubscriptions(client);
  }

  Future<void> _recargar() async {
    final futuro = listSubscriptions(client);
    setState(() {
      _futuro = futuro;
    });
    await futuro;
  }

  Future<void> _cambiarPlan(Subscription suscripcion) async {
    final cambiada = await context.push<bool>(
      '/platform/subscriptions/change',
      extra: suscripcion,
    );
    if (cambiada == true) await _recargar();
  }

  void _verHistorial(Subscription suscripcion) {
    context.push(
      '/platform/organizations/${suscripcion.organization}/subscriptions',
      extra: {
        'name': suscripcion.organizationName,
        'slug': suscripcion.organizationSlug,
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Suscripciones')),
      drawer: const PlatformDrawer(),
      body: FutureBuilder<List<Subscription>>(
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
                      : 'No se pudieron cargar las suscripciones.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          final suscripciones = snapshot.data ?? const [];
          final organizaciones =
              suscripciones.map((s) => s.organization).toSet().length;
          final planMasUsado = _planMasUsado(suscripciones);

          final filtro = _busqueda.trim().toLowerCase();
          final visibles = filtro.isEmpty
              ? suscripciones
              : suscripciones.where((s) {
                  return s.organizationName.toLowerCase().contains(filtro) ||
                      s.organizationSlug.toLowerCase().contains(filtro) ||
                      s.planName.toLowerCase().contains(filtro);
                }).toList();

          return RefreshIndicator(
            onRefresh: _recargar,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Row(
                  children: [
                    Expanded(
                      child: StatTile(
                        label: 'Suscripciones activas',
                        value: '${suscripciones.length}',
                        color: Marca.primary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: StatTile(
                        label: 'Organizaciones',
                        value: '$organizaciones',
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: StatTile(
                        label: 'Plan más usado',
                        value: planMasUsado ?? '—',
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                TextField(
                  decoration: const InputDecoration(
                    prefixIcon: Icon(Icons.search),
                    hintText: 'Buscar por organización o plan',
                  ),
                  onChanged: (valor) => setState(() => _busqueda = valor),
                ),
                const SizedBox(height: 16),
                for (final suscripcion in visibles)
                  _SubscriptionCard(
                    suscripcion: suscripcion,
                    onHistorial: () => _verHistorial(suscripcion),
                    onCambiarPlan: () => _cambiarPlan(suscripcion),
                  ),
              ],
            ),
          );
        },
      ),
    );
  }

  String? _planMasUsado(List<Subscription> suscripciones) {
    if (suscripciones.isEmpty) return null;
    final conteo = <String, int>{};
    for (final s in suscripciones) {
      conteo[s.planName] = (conteo[s.planName] ?? 0) + 1;
    }
    return conteo.entries.reduce((a, b) => a.value >= b.value ? a : b).key;
  }
}

class _SubscriptionCard extends StatelessWidget {
  const _SubscriptionCard({
    required this.suscripcion,
    required this.onHistorial,
    required this.onCambiarPlan,
  });

  final Subscription suscripcion;
  final VoidCallback onHistorial;
  final VoidCallback onCambiarPlan;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final activa = suscripcion.status == 'active';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(suscripcion.organizationName, style: theme.textTheme.titleMedium),
            Text(
              suscripcion.organizationSlug,
              style: theme.textTheme.bodySmall
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                Chip(label: Text(suscripcion.planName)),
                Chip(
                  label: Text(activa ? 'Activa' : 'Finalizada'),
                  backgroundColor:
                      (activa ? Marca.primary : Marca.ink500).withValues(alpha: 0.12),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Inicio: ${suscripcion.startsAt}',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(onPressed: onHistorial, child: const Text('Historial')),
                const SizedBox(width: 8),
                FilledButton(
                  // El tema global fuerza `minimumSize: Size.fromHeight(52)`
                  // -ancho infinito, pensado para el botón único de una
                  // columna a todo el ancho- y eso revienta el layout de un
                  // `Row`, que no puede darle ancho infinito a un hijo sin
                  // `Expanded`. Acá hace falta un tamaño acotado.
                  style: FilledButton.styleFrom(minimumSize: Size.zero),
                  onPressed: onCambiarPlan,
                  child: const Text('Cambiar plan'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
