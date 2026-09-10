/// US-44 — Historial de suscripciones de una organización.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import 'subscriptions_api.dart';

class SubscriptionHistoryScreen extends StatefulWidget {
  const SubscriptionHistoryScreen({
    super.key,
    required this.organizationId,
    required this.organizationName,
    this.client,
  });

  final String organizationId;
  final String organizationName;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<SubscriptionHistoryScreen> createState() =>
      _SubscriptionHistoryScreenState();
}

class _SubscriptionHistoryScreenState
    extends State<SubscriptionHistoryScreen> {
  Future<List<Subscription>>? _futuro;
  ApiClient? _client;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _futuro ??= organizationSubscriptionHistory(client, widget.organizationId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Historial · ${widget.organizationName}')),
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
                      : 'No se pudo cargar el historial.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          final suscripciones = List.of(snapshot.data ?? const <Subscription>[])
            ..sort((a, b) => b.startsAt.compareTo(a.startsAt));

          if (suscripciones.isEmpty) {
            return const Center(child: Text('Todavía no hay suscripciones.'));
          }

          return ListView.builder(
            padding: const EdgeInsets.all(16),
            itemCount: suscripciones.length,
            itemBuilder: (context, indice) =>
                _HistoryCard(suscripcion: suscripciones[indice]),
          );
        },
      ),
    );
  }
}

class _HistoryCard extends StatelessWidget {
  const _HistoryCard({required this.suscripcion});

  final Subscription suscripcion;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final vigente = suscripcion.status == 'active' && suscripcion.endsAt == null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Chip(label: Text(suscripcion.planName)),
                if (vigente) ...[
                  const SizedBox(width: 8),
                  Chip(
                    label: const Text('PLAN VIGENTE'),
                    backgroundColor: Marca.surfaceTint,
                    labelStyle: const TextStyle(
                      color: Marca.primary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ],
            ),
            const SizedBox(height: 8),
            Text(
              '${suscripcion.startsAt} → ${suscripcion.endsAt ?? "Vigente"}',
              style: theme.textTheme.bodyMedium,
            ),
            Text(
              suscripcion.status == 'active' ? 'Estado: Activa' : 'Estado: Finalizada',
              style: theme.textTheme.bodySmall,
            ),
            Text(
              'Asignado por: ${suscripcion.assignedByEmail ?? "—"}',
              style: theme.textTheme.bodySmall,
            ),
            Text(
              'Registrado: ${suscripcion.createdAt}',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 4),
            Text(
              suscripcion.changeReason.isEmpty
                  ? 'Sin motivo registrado'
                  : suscripcion.changeReason,
              style: theme.textTheme.bodySmall
                  ?.copyWith(fontStyle: FontStyle.italic),
            ),
          ],
        ),
      ),
    );
  }
}
