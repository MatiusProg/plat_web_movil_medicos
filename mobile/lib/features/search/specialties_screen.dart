/// US-16 — Pantalla de entrada por especialidad.
///
/// Para el paciente que no sabe a quién buscar pero sí qué necesita. Al elegir
/// una especialidad, abre la búsqueda ya filtrada.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';

import 'search_api.dart';

class SpecialtiesScreen extends StatefulWidget {
  const SpecialtiesScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<SpecialtiesScreen> createState() => _SpecialtiesScreenState();
}

class _SpecialtiesScreenState extends State<SpecialtiesScreen> {
  Future<List<Especialidad>>? _futuro;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _futuro ??= listarEspecialidades(
      widget.client ?? ApiClient(auth: SessionScope.of(context)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Buscar profesionales'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            tooltip: 'Buscar por nombre',
            onPressed: () => context.go('/search'),
          ),
        ],
      ),
      body: FutureBuilder<List<Especialidad>>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            final error = snapshot.error;
            return Center(
              child: Text(
                error is ApiError
                    ? error.message
                    : 'No se pudo cargar el catálogo.',
              ),
            );
          }
          final especialidades = snapshot.data ?? const [];
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
            children: [
              const Padding(
                padding: EdgeInsets.only(bottom: 12),
                child: Text('Elegí una especialidad'),
              ),
              for (final e in especialidades)
                Card(
                  child: ListTile(
                    title: Text(e.name),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.go('/search?specialty=${e.id}'),
                  ),
                ),
              const SizedBox(height: 12),
              OutlinedButton(
                onPressed: () => context.go('/search'),
                child: const Text('Ver todos los profesionales'),
              ),
            ],
          );
        },
      ),
    );
  }
}
