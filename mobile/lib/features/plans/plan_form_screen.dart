/// US-44 — Alta y edición de un plan de suscripción.
///
/// Un solo widget para las dos cosas: `planExistente == null` es alta,
/// `!= null` es edición -mismo criterio que otros formularios del proyecto-.
/// El `code` sólo se puede escribir al crear: el backend no lo deja cambiar
/// después (es la clave que usan las organizaciones para referenciar el
/// plan), así que al editar queda deshabilitado en vez de mandarlo y que el
/// backend lo ignore silenciosamente.
///
/// No incluye los "features" (chatbot, resúmenes por IA, etc. en la web):
/// el backend los guarda en un JSON libre y no se confirmó el nombre exacto
/// de cada clave. Editar acá no los toca ni los pierde -no viajan en el
/// body-, sólo no se pueden prender/apagar desde mobile todavía.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import 'plans_api.dart';

class PlanFormScreen extends StatefulWidget {
  const PlanFormScreen({super.key, this.planExistente, this.client});

  final Plan? planExistente;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<PlanFormScreen> createState() => _PlanFormScreenState();
}

class _PlanFormScreenState extends State<PlanFormScreen> {
  final _formKey = GlobalKey<FormState>();
  late final _code = TextEditingController(text: widget.planExistente?.code);
  late final _name = TextEditingController(text: widget.planExistente?.name);
  late final _description =
      TextEditingController(text: widget.planExistente?.description);
  late final _price =
      TextEditingController(text: widget.planExistente?.monthlyPrice);
  late final _currency = TextEditingController(
    text: widget.planExistente?.currency ?? 'BOB',
  );
  late final _maxUsers =
      TextEditingController(text: widget.planExistente?.maxUsers?.toString());
  late final _maxBranches = TextEditingController(
    text: widget.planExistente?.maxBranches?.toString(),
  );
  late final _maxPractitioners = TextEditingController(
    text: widget.planExistente?.maxPractitioners?.toString(),
  );
  late final _maxAppointments = TextEditingController(
    text: widget.planExistente?.maxAppointmentsMonth?.toString(),
  );
  late final _maxAiQueries = TextEditingController(
    text: widget.planExistente?.maxAiQueriesMonth?.toString(),
  );
  late final _storageMb = TextEditingController(
    text: widget.planExistente?.storageMb?.toString(),
  );
  late bool _activo = widget.planExistente?.isActive ?? true;

  bool _guardando = false;
  ApiError? _error;
  ApiClient? _client;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  bool get _esEdicion => widget.planExistente != null;

  @override
  void dispose() {
    _code.dispose();
    _name.dispose();
    _description.dispose();
    _price.dispose();
    _currency.dispose();
    _maxUsers.dispose();
    _maxBranches.dispose();
    _maxPractitioners.dispose();
    _maxAppointments.dispose();
    _maxAiQueries.dispose();
    _storageMb.dispose();
    super.dispose();
  }

  int? _limite(TextEditingController controlador) {
    final texto = controlador.text.trim();
    return texto.isEmpty ? null : int.tryParse(texto);
  }

  Future<void> _guardar() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    try {
      if (_esEdicion) {
        await updatePlan(
          client,
          widget.planExistente!.id,
          name: _name.text.trim(),
          description: _description.text.trim(),
          monthlyPrice: _price.text.trim(),
          currency: _currency.text.trim(),
          maxBranches: _limite(_maxBranches),
          maxUsers: _limite(_maxUsers),
          maxPractitioners: _limite(_maxPractitioners),
          maxAppointmentsMonth: _limite(_maxAppointments),
          maxAiQueriesMonth: _limite(_maxAiQueries),
          storageMb: _limite(_storageMb),
          isActive: _activo,
        );
      } else {
        await createPlan(
          client,
          code: _code.text.trim(),
          name: _name.text.trim(),
          description: _description.text.trim(),
          monthlyPrice: _price.text.trim(),
          currency: _currency.text.trim(),
          maxBranches: _limite(_maxBranches),
          maxUsers: _limite(_maxUsers),
          maxPractitioners: _limite(_maxPractitioners),
          maxAppointmentsMonth: _limite(_maxAppointments),
          maxAiQueriesMonth: _limite(_maxAiQueries),
          storageMb: _limite(_storageMb),
          isActive: _activo,
        );
      }
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  Widget _campoLimite(
    String etiqueta,
    TextEditingController controlador,
    String campoBackend,
  ) {
    return TextFormField(
      controller: controlador,
      enabled: !_guardando,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(
        labelText: etiqueta,
        hintText: 'Vacío = ilimitado',
        errorText: _error?.forField(campoBackend),
      ),
      validator: (valor) {
        if (valor == null || valor.trim().isEmpty) return null;
        return int.tryParse(valor.trim()) == null ? 'Tiene que ser un número.' : null;
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_esEdicion ? 'Editar plan' : 'Nuevo plan'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _code,
                enabled: !_esEdicion && !_guardando,
                decoration: InputDecoration(
                  labelText: 'Código',
                  helperText: _esEdicion
                      ? 'No se puede cambiar después de creado.'
                      : 'Minúsculas, sin espacios (ej. "pro").',
                  errorText: _error?.forField('code'),
                ),
                validator: (valor) => (valor ?? '').trim().isEmpty
                    ? 'Escribí un código.'
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _name,
                enabled: !_guardando,
                decoration: InputDecoration(
                  labelText: 'Nombre',
                  errorText: _error?.forField('name'),
                ),
                validator: (valor) =>
                    (valor ?? '').trim().isEmpty ? 'Escribí un nombre.' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _description,
                enabled: !_guardando,
                maxLines: 2,
                decoration: const InputDecoration(labelText: 'Descripción'),
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    flex: 2,
                    child: TextFormField(
                      controller: _price,
                      enabled: !_guardando,
                      keyboardType:
                          const TextInputType.numberWithOptions(decimal: true),
                      decoration: InputDecoration(
                        labelText: 'Precio mensual',
                        errorText: _error?.forField('monthly_price'),
                      ),
                      validator: (valor) => (valor ?? '').trim().isEmpty
                          ? 'Escribí un precio.'
                          : null,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: TextFormField(
                      controller: _currency,
                      enabled: !_guardando,
                      decoration: const InputDecoration(labelText: 'Moneda'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 20),
              Text('Límites', style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _campoLimite('Usuarios', _maxUsers, 'max_users'),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _campoLimite(
                      'Sucursales',
                      _maxBranches,
                      'max_branches',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _campoLimite(
                      'Profesionales',
                      _maxPractitioners,
                      'max_practitioners',
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _campoLimite(
                      'Citas/mes',
                      _maxAppointments,
                      'max_appointments_month',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: _campoLimite(
                      'Consultas IA/mes',
                      _maxAiQueries,
                      'max_ai_queries_month',
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _campoLimite(
                      'Almacenamiento (MB)',
                      _storageMb,
                      'storage_mb',
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              SwitchListTile(
                contentPadding: EdgeInsets.zero,
                title: const Text('Plan activo'),
                value: _activo,
                onChanged:
                    _guardando ? null : (valor) => setState(() => _activo = valor),
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
                onPressed: _guardando ? null : _guardar,
                child: Text(_guardando ? 'Guardando…' : 'Guardar'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
