/// US-43 — Listado de organizaciones.
///
/// Espejo de `frontend/src/paginas/Organizaciones.tsx`: una fila por
/// organización, sin filtro ni acciones por fila -eso lo tiene la web
/// tampoco-, y un botón para registrar una nueva.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../../core/widgets/platform_drawer.dart';
import 'organizations_api.dart';

class OrganizationsScreen extends StatefulWidget {
  const OrganizationsScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<OrganizationsScreen> createState() => _OrganizationsScreenState();
}

class _OrganizationsScreenState extends State<OrganizationsScreen> {
  Future<List<Organization>>? _futuro;
  ApiClient? _client;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _futuro ??= listOrganizations(client);
  }

  Future<void> _recargar() async {
    final futuro = listOrganizations(client);
    setState(() {
      _futuro = futuro;
    });
    await futuro;
  }

  Future<void> _registrar() async {
    final registrada = await context.push<bool>('/platform/organizations/new');
    if (registrada == true) await _recargar();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Organizaciones'),
        actions: [
          IconButton(
            tooltip: 'Registrar organización',
            onPressed: _registrar,
            icon: const Icon(Icons.add),
          ),
        ],
      ),
      drawer: const PlatformDrawer(),
      body: FutureBuilder<List<Organization>>(
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
                      : 'No se pudieron cargar las organizaciones.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          final organizaciones = snapshot.data ?? const [];
          if (organizaciones.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.apartment_outlined,
                      size: 40,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Todavía no hay ninguna organización registrada.',
                      textAlign: TextAlign.center,
                    ),
                  ],
                ),
              ),
            );
          }
          return RefreshIndicator(
            onRefresh: _recargar,
            child: ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: organizaciones.length,
              itemBuilder: (context, indice) =>
                  _OrganizationCard(organizacion: organizaciones[indice]),
            ),
          );
        },
      ),
    );
  }
}

class _OrganizationCard extends StatelessWidget {
  const _OrganizationCard({required this.organizacion});

  final Organization organizacion;

  (Color, String) get _estado => switch (organizacion.status) {
        'active' => (Marca.primary, 'Activa'),
        'suspended' => (Marca.waiting, 'Suspendida'),
        _ => (Marca.ink500, 'Inactiva'),
      };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final (color, etiqueta) = _estado;
    final subtitulo = [
      organizacion.slug,
      'NIT ${organizacion.taxId}',
      if (organizacion.city.isNotEmpty) organizacion.city,
    ].join(' · ');

    return Card(
      child: ListTile(
        title: Text(organizacion.name),
        subtitle: Text(subtitulo),
        trailing: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              etiqueta,
              style: theme.textTheme.labelSmall
                  ?.copyWith(color: color, fontWeight: FontWeight.w700),
            ),
            Text(
              organizacion.currentPlan?.name ?? 'Sin plan',
              style: theme.textTheme.labelSmall
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}
