/// US-44 — Listado de planes de suscripción.
///
/// Espejo de `frontend/src/paginas/Planes.tsx`: resumen de conteos arriba,
/// filtro por estado, una tarjeta por plan con lo que incluye derivado de
/// sus límites -no hay una lista de "features" separada que traer, los
/// límites `null` ya dicen "ilimitado" solos-.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../../core/widgets/platform_drawer.dart';
import '../../core/widgets/stat_tile.dart';
import 'plans_api.dart';

enum _Filtro { todos, activos, inactivos }

class PlansScreen extends StatefulWidget {
  const PlansScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<PlansScreen> createState() => _PlansScreenState();
}

class _PlansScreenState extends State<PlansScreen> {
  Future<List<Plan>>? _futuro;
  ApiClient? _client;
  _Filtro _filtro = _Filtro.todos;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _futuro ??= listPlans(client);
  }

  Future<void> _recargar() async {
    final futuro = listPlans(client);
    setState(() {
      _futuro = futuro;
    });
    await futuro;
  }

  Future<void> _nuevoPlan() async {
    final creado = await context.push<bool>('/platform/plans/new');
    if (creado == true) await _recargar();
  }

  Future<void> _editarPlan(Plan plan) async {
    final editado = await context.push<bool>(
      '/platform/plans/${plan.id}/edit',
      extra: plan,
    );
    if (editado == true) await _recargar();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Planes'),
        actions: [
          IconButton(
            tooltip: 'Nuevo plan',
            onPressed: _nuevoPlan,
            icon: const Icon(Icons.add),
          ),
        ],
      ),
      drawer: const PlatformDrawer(),
      body: FutureBuilder<List<Plan>>(
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
                      : 'No se pudieron cargar los planes.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          final planes = snapshot.data ?? const [];
          final activos = planes.where((p) => p.isActive).length;
          final inactivos = planes.length - activos;
          final visibles = switch (_filtro) {
            _Filtro.todos => planes,
            _Filtro.activos => planes.where((p) => p.isActive).toList(),
            _Filtro.inactivos => planes.where((p) => !p.isActive).toList(),
          };

          return RefreshIndicator(
            onRefresh: _recargar,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Row(
                  children: [
                    Expanded(
                      child: StatTile(
                        label: 'Disponibles',
                        value: '${planes.length}',
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: StatTile(
                        label: 'Activos',
                        value: '$activos',
                        color: Marca.primary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: StatTile(label: 'Inactivos', value: '$inactivos'),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                Wrap(
                  spacing: 8,
                  children: [
                    ChoiceChip(
                      label: Text('Todos (${planes.length})'),
                      selected: _filtro == _Filtro.todos,
                      onSelected: (_) => setState(() => _filtro = _Filtro.todos),
                    ),
                    ChoiceChip(
                      label: Text('Activos ($activos)'),
                      selected: _filtro == _Filtro.activos,
                      onSelected: (_) =>
                          setState(() => _filtro = _Filtro.activos),
                    ),
                    ChoiceChip(
                      label: Text('Inactivos ($inactivos)'),
                      selected: _filtro == _Filtro.inactivos,
                      onSelected: (_) =>
                          setState(() => _filtro = _Filtro.inactivos),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                for (final plan in visibles) _PlanCard(
                  plan: plan,
                  onEditar: () => _editarPlan(plan),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.plan, required this.onEditar});

  final Plan plan;
  final VoidCallback onEditar;

  List<String> get _incluye {
    String linea(int? valor, String singular, String plural) => valor == null
        ? '$plural ilimitados'
        : 'Hasta $valor $plural';
    return [
      linea(plan.maxUsers, 'usuario', 'usuarios'),
      linea(plan.maxBranches, 'sucursal', 'sucursales'),
      linea(plan.maxPractitioners, 'profesional', 'profesionales'),
      linea(plan.maxAppointmentsMonth, 'cita/mes', 'citas/mes'),
      linea(plan.maxAiQueriesMonth, 'consulta IA/mes', 'consultas IA/mes'),
      plan.storageMb == null
          ? 'Almacenamiento ilimitado'
          : 'Hasta ${plan.storageMb} MB de almacenamiento',
    ];
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(plan.name, style: theme.textTheme.titleMedium),
                ),
                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                  decoration: BoxDecoration(
                    color: plan.isActive
                        ? Marca.surfaceTint
                        : theme.colorScheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    plan.isActive ? 'ACTIVO' : 'INACTIVO',
                    style: theme.textTheme.labelSmall?.copyWith(
                      color: plan.isActive ? Marca.primary : Marca.ink500,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            if (plan.description.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(plan.description, style: theme.textTheme.bodyMedium),
            ],
            const SizedBox(height: 8),
            Text(
              '${plan.monthlyPrice} ${plan.currency}/mes',
              style: theme.textTheme.titleMedium
                  ?.copyWith(color: Marca.primaryDark),
            ),
            const SizedBox(height: 12),
            Text('Incluye', style: theme.textTheme.labelLarge),
            const SizedBox(height: 4),
            for (final linea in _incluye)
              Text('• $linea', style: theme.textTheme.bodySmall),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: onEditar,
                child: const Text('Editar plan'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
