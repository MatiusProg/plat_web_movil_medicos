/// US-44 — Cambiar el plan de una organización.
///
/// Espejo de `ModalCambiarPlan.tsx`, como pantalla propia en vez de diálogo
/// -mismo criterio que `dependent_form_screen.dart`-. Cierra sola la
/// suscripción vigente y abre la nueva; no hay nada que confirmar aparte del
/// propio envío del formulario (la web tampoco pide una confirmación extra).
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../plans/plans_api.dart';
import 'subscriptions_api.dart';

class ChangePlanScreen extends StatefulWidget {
  const ChangePlanScreen({super.key, required this.suscripcionActual, this.client});

  final Subscription suscripcionActual;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<ChangePlanScreen> createState() => _ChangePlanScreenState();
}

class _ChangePlanScreenState extends State<ChangePlanScreen> {
  Future<List<Plan>>? _planesFuturo;
  Plan? _planElegido;
  DateTime _fechaInicio = DateTime.now();
  final _motivo = TextEditingController();

  bool _guardando = false;
  ApiError? _error;
  ApiClient? _client;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _planesFuturo ??= listPlans(client, isActive: true);
  }

  @override
  void dispose() {
    _motivo.dispose();
    super.dispose();
  }

  Future<void> _elegirFecha() async {
    final elegida = await showDatePicker(
      context: context,
      initialDate: _fechaInicio,
      firstDate: DateTime(2020),
      lastDate: DateTime(2100),
      helpText: 'Fecha de inicio',
    );
    if (elegida != null) setState(() => _fechaInicio = elegida);
  }

  Future<void> _confirmar() async {
    final plan = _planElegido;
    if (plan == null) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    try {
      await assignPlan(
        client,
        organizationId: widget.suscripcionActual.organization,
        planId: plan.id,
        startsAt: _fechaInicio.toIso8601String().substring(0, 10),
        changeReason: _motivo.text.trim(),
      );
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final actual = widget.suscripcionActual;
    return Scaffold(
      appBar: AppBar(title: const Text('Cambiar plan')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Organización', style: Theme.of(context).textTheme.labelLarge),
            const SizedBox(height: 4),
            Text(actual.organizationName),
            Text(
              'Plan actual: ${actual.planName}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 20),
            FutureBuilder<List<Plan>>(
              future: _planesFuturo,
              builder: (context, snapshot) {
                final planes = (snapshot.data ?? const [])
                    .where((p) => p.code != actual.planCode)
                    .toList();
                return DropdownButtonFormField<Plan>(
                  initialValue: _planElegido,
                  decoration: InputDecoration(
                    labelText: 'Nuevo plan',
                    errorText: _error?.forField('plan_id'),
                  ),
                  items: [
                    for (final plan in planes)
                      DropdownMenuItem(
                        value: plan,
                        child: Text('${plan.name} — ${plan.monthlyPrice} ${plan.currency}/mes'),
                      ),
                  ],
                  onChanged: _guardando
                      ? null
                      : (valor) => setState(() => _planElegido = valor),
                );
              },
            ),
            const SizedBox(height: 16),
            OutlinedButton.icon(
              onPressed: _guardando ? null : _elegirFecha,
              icon: const Icon(Icons.calendar_today_outlined),
              label: Text(
                'Fecha de inicio: ${_fechaInicio.toIso8601String().substring(0, 10)}',
              ),
            ),
            if (_error?.forField('starts_at') != null) ...[
              const SizedBox(height: 4),
              Text(
                _error!.forField('starts_at')!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 16),
            TextField(
              controller: _motivo,
              enabled: !_guardando,
              maxLines: 3,
              maxLength: 200,
              decoration: const InputDecoration(
                labelText: 'Motivo del cambio (opcional)',
                helperText: 'Este motivo queda registrado en el historial.',
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Al confirmar, la suscripción vigente se cierra y se abre la '
              'nueva. La organización conserva su historial completo de cambios.',
              style: Theme.of(context).textTheme.bodySmall,
            ),
            if (_error != null && _error!.fieldErrors == null) ...[
              const SizedBox(height: 12),
              Text(
                _error!.message,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: (_guardando || _planElegido == null) ? null : _confirmar,
              child: Text(_guardando ? 'Cambiando…' : 'Confirmar cambio'),
            ),
          ],
        ),
      ),
    );
  }
}
