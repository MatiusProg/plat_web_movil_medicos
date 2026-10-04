/// US-44 — Listado de planes de suscripción.
///
/// Espejo de `frontend/src/paginas/Planes.tsx`: una tarjeta por plan, del
/// más barato al más caro, con su precio, los topes que hace cumplir
/// `tenancy/plans.py` y las funciones que incluye o no. El filtro por estado
/// sólo aparece si hay planes inactivos.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../../core/widgets/platform_drawer.dart';
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
          // Del más barato al más caro, como se leen.
          final planes = [...?snapshot.data]..sort((a, b) =>
              (double.tryParse(a.monthlyPrice) ?? 0)
                  .compareTo(double.tryParse(b.monthlyPrice) ?? 0));
          final inactivos = planes.where((p) => !p.isActive).length;
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
                Text(
                  'Lo que cada plan permite. Los topes se hacen cumplir en '
                  'todo el sistema: un centro no puede pasarse de ellos.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
                const SizedBox(height: 16),
                // El filtro sólo aparece si hay algo que filtrar.
                if (inactivos > 0) ...[
                  Wrap(
                    spacing: 8,
                    children: [
                      for (final (filtro, etiqueta) in const [
                        (_Filtro.todos, 'Todos'),
                        (_Filtro.activos, 'Activos'),
                        (_Filtro.inactivos, 'Inactivos'),
                      ])
                        ChoiceChip(
                          label: Text(etiqueta),
                          selected: _filtro == filtro,
                          onSelected: (_) => setState(() => _filtro = filtro),
                        ),
                    ],
                  ),
                  const SizedBox(height: 16),
                ],
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

  /// Las funciones que un plan puede incluir, con las mismas palabras que la
  /// web (`Planes.tsx`).
  static const _funciones = [
    ('ai_chatbot', 'Asistente de orientación'),
    ('noshow_prediction', 'Predicción de inasistencia'),
    ('ai_summaries', 'Resúmenes con IA'),
    ('report_export', 'Exportar reportes'),
    ('online_payment', 'Pago en línea'),
  ];

  static String _tope(int? valor) => valor == null ? 'Sin límite' : '$valor';

  static String _sinCeros(double n) =>
      n == n.roundToDouble() ? n.toStringAsFixed(0) : n.toStringAsFixed(1);

  static String _almacenamiento(int? mb) {
    if (mb == null) return 'Sin límite';
    return mb < 1024 ? '$mb MB' : '${_sinCeros(mb / 1024)} GB';
  }

  String get _precio {
    final moneda = plan.currency == 'BOB' ? 'Bs' : plan.currency;
    final monto = double.tryParse(plan.monthlyPrice) ?? 0;
    final texto = monto == monto.roundToDouble()
        ? monto.toStringAsFixed(0)
        : monto.toStringAsFixed(2);
    return '$moneda $texto';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final suave = theme.colorScheme.onSurfaceVariant;
    final topes = [
      ('Personal', _tope(plan.maxUsers)),
      ('Sucursales', _tope(plan.maxBranches)),
      ('Profesionales', _tope(plan.maxPractitioners)),
      ('Fichas al mes', _tope(plan.maxAppointmentsMonth)),
      (
        'Consultas al asistente al mes',
        plan.incluye('ai_chatbot')
            ? _tope(plan.maxAiQueriesMonth)
            : 'No incluye',
      ),
      ('Almacenamiento', _almacenamiento(plan.storageMb)),
    ];

    return Opacity(
      opacity: plan.isActive ? 1 : 0.75,
      child: Card(
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
                      color: theme.colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(999),
                    ),
                    child: Text(
                      plan.isActive ? 'Activo' : 'Inactivo',
                      style: theme.textTheme.labelSmall?.copyWith(color: suave),
                    ),
                  ),
                ],
              ),
              if (plan.description.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  plan.description,
                  style: theme.textTheme.bodySmall?.copyWith(color: suave),
                ),
              ],
              const SizedBox(height: 12),
              Row(
                crossAxisAlignment: CrossAxisAlignment.baseline,
                textBaseline: TextBaseline.alphabetic,
                children: [
                  Text(
                    _precio,
                    style: theme.textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w600,
                      fontFeatures: const [FontFeature.tabularFigures()],
                    ),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'al mes',
                    style: theme.textTheme.bodySmall?.copyWith(color: suave),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              const Divider(height: 1),
              for (final (etiqueta, valor) in topes) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          etiqueta,
                          style:
                              theme.textTheme.bodySmall?.copyWith(color: suave),
                        ),
                      ),
                      Text(
                        valor,
                        style: theme.textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: valor == 'No incluye' ? suave : null,
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1),
              ],
              const SizedBox(height: 12),
              for (final (clave, etiqueta) in _funciones)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Semantics(
                    label: '$etiqueta: '
                        '${plan.incluye(clave) ? 'incluido' : 'no incluido'}',
                    excludeSemantics: true,
                    child: Row(
                      children: [
                        Icon(
                          plan.incluye(clave) ? Icons.check : Icons.close,
                          size: 18,
                          color: plan.incluye(clave) ? Marca.primary : suave,
                        ),
                        const SizedBox(width: 10),
                        Text(
                          etiqueta,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: plan.incluye(clave) ? null : suave,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: onEditar,
                  icon: const Icon(Icons.edit_outlined, size: 18),
                  label: const Text('Editar plan'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
