/// US-43 — Alta de una organización.
///
/// Espejo de `frontend/src/paginas/AltaOrganizacion.tsx`, con la misma
/// decisión de fondo: **no es una ruta separada la pantalla de éxito**. El
/// mismo widget cambia qué dibuja según tenga o no una `OrganizationCreated`
/// -igual que la web reemplaza el propio componente-, porque la contraseña
/// temporal del administrador **sólo viaja en la respuesta de este POST** y
/// no hay que arriesgarse a perderla navegando a otro lado.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show Clipboard, ClipboardData;

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../plans/plans_api.dart';
import 'organizations_api.dart';

class RegisterOrganizationScreen extends StatefulWidget {
  const RegisterOrganizationScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<RegisterOrganizationScreen> createState() =>
      _RegisterOrganizationScreenState();
}

class _RegisterOrganizationScreenState
    extends State<RegisterOrganizationScreen> {
  final _formKey = GlobalKey<FormState>();
  final _slug = TextEditingController();
  final _name = TextEditingController();
  final _legalName = TextEditingController();
  final _taxId = TextEditingController();
  final _contactEmail = TextEditingController();
  final _contactPhone = TextEditingController();
  final _address = TextEditingController();
  final _city = TextEditingController();
  final _adminEmail = TextEditingController();
  final _adminFirstName = TextEditingController();
  final _adminLastName = TextEditingController();
  final _adminDocumentNumber = TextEditingController();
  final _adminPhone = TextEditingController();

  static final _patronSlug =
      RegExp(r'^[a-z0-9]([a-z0-9-]{1,38}[a-z0-9])$');

  Future<List<Plan>>? _planesFuturo;
  String? _planCode;
  bool _enviando = false;
  ApiError? _error;
  OrganizationCreated? _creada;
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
    _slug.dispose();
    _name.dispose();
    _legalName.dispose();
    _taxId.dispose();
    _contactEmail.dispose();
    _contactPhone.dispose();
    _address.dispose();
    _city.dispose();
    _adminEmail.dispose();
    _adminFirstName.dispose();
    _adminLastName.dispose();
    _adminDocumentNumber.dispose();
    _adminPhone.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    if (_planCode == null) {
      setState(() => _error = const ApiError(
            'Elegí un plan de suscripción.',
            'validacion',
            400,
            fieldErrors: {
              'plan_code': ['Elegí un plan de suscripción.'],
            },
          ));
      return;
    }

    setState(() {
      _enviando = true;
      _error = null;
    });

    try {
      final creada = await registerOrganization(
        client,
        slug: _slug.text.trim(),
        name: _name.text.trim(),
        legalName: _legalName.text.trim(),
        taxId: _taxId.text.trim(),
        contactEmail: _contactEmail.text.trim(),
        contactPhone: _contactPhone.text.trim(),
        address: _address.text.trim(),
        city: _city.text.trim(),
        planCode: _planCode!,
        adminEmail: _adminEmail.text.trim(),
        adminFirstName: _adminFirstName.text.trim(),
        adminLastName: _adminLastName.text.trim(),
        adminDocumentNumber: _adminDocumentNumber.text.trim(),
        adminPhone: _adminPhone.text.trim(),
      );
      if (!mounted) return;
      setState(() => _creada = creada);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final creada = _creada;
    return PopScope(
      // Mientras no se confirme que la contraseña ya se copió, no se puede
      // volver atrás sin querer y perderla -no hay forma de volver a pedirla-.
      canPop: creada == null,
      child: Scaffold(
        appBar: AppBar(
          title: Text(creada == null ? 'Registrar organización' : 'Organización registrada'),
        ),
        body: creada == null ? _formulario() : _CredencialesView(creada: creada),
      ),
    );
  }

  Widget _formulario() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('El centro médico',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _name,
                      enabled: !_enviando,
                      decoration: InputDecoration(
                        labelText: 'Nombre comercial',
                        errorText: _error?.forField('name'),
                      ),
                      validator: (v) =>
                          (v ?? '').trim().isEmpty ? 'Escribí un nombre.' : null,
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _legalName,
                      enabled: !_enviando,
                      decoration: InputDecoration(
                        labelText: 'Razón social',
                        errorText: _error?.forField('legal_name'),
                      ),
                      validator: (v) => (v ?? '').trim().isEmpty
                          ? 'Escribí la razón social.'
                          : null,
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _slug,
                            enabled: !_enviando,
                            autocorrect: false,
                            decoration: InputDecoration(
                              labelText: 'Identificador',
                              hintText: 'kolping',
                              helperText:
                                  'Lo que se escribe al iniciar sesión.',
                              errorText: _error?.forField('slug'),
                            ),
                            validator: (v) {
                              final valor = (v ?? '').trim();
                              if (valor.isEmpty) return 'Escribí un identificador.';
                              if (!_patronSlug.hasMatch(valor)) {
                                return 'Minúsculas, números y guiones.';
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _taxId,
                            enabled: !_enviando,
                            decoration: InputDecoration(
                              labelText: 'NIT',
                              errorText: _error?.forField('tax_id'),
                            ),
                            validator: (v) =>
                                (v ?? '').trim().isEmpty ? 'Escribí el NIT.' : null,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _contactEmail,
                            enabled: !_enviando,
                            keyboardType: TextInputType.emailAddress,
                            decoration: InputDecoration(
                              labelText: 'Correo de contacto',
                              errorText: _error?.forField('contact_email'),
                            ),
                            validator: (v) => (v ?? '').trim().isEmpty
                                ? 'Escribí un correo.'
                                : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _contactPhone,
                            enabled: !_enviando,
                            decoration: const InputDecoration(
                              labelText: 'Teléfono',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _address,
                            enabled: !_enviando,
                            decoration: const InputDecoration(
                              labelText: 'Dirección',
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _city,
                            enabled: !_enviando,
                            decoration: const InputDecoration(
                              labelText: 'Ciudad',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    FutureBuilder<List<Plan>>(
                      future: _planesFuturo,
                      builder: (context, snapshot) {
                        final planes = snapshot.data ?? const [];
                        return DropdownButtonFormField<String>(
                          initialValue: _planCode,
                          decoration: InputDecoration(
                            labelText: 'Plan de suscripción',
                            errorText: _error?.forField('plan_code'),
                          ),
                          items: [
                            for (final plan in planes)
                              DropdownMenuItem(
                                value: plan.code,
                                child: Text(
                                  '${plan.name} — ${plan.monthlyPrice} ${plan.currency}/mes',
                                ),
                              ),
                          ],
                          onChanged: _enviando
                              ? null
                              : (valor) => setState(() => _planCode = valor),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Su administrador',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 4),
                    Text(
                      'Recibe una contraseña temporal que se muestra una sola vez.',
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          color: Theme.of(context).colorScheme.onSurfaceVariant),
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _adminFirstName,
                            enabled: !_enviando,
                            decoration: InputDecoration(
                              labelText: 'Nombres',
                              errorText: _error?.forField('admin'),
                            ),
                            validator: (v) =>
                                (v ?? '').trim().isEmpty ? 'Escribí el nombre.' : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _adminLastName,
                            enabled: !_enviando,
                            decoration: const InputDecoration(
                              labelText: 'Apellidos',
                            ),
                            validator: (v) => (v ?? '').trim().isEmpty
                                ? 'Escribí el apellido.'
                                : null,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _adminEmail,
                            enabled: !_enviando,
                            keyboardType: TextInputType.emailAddress,
                            decoration: const InputDecoration(
                              labelText: 'Correo',
                            ),
                            validator: (v) =>
                                (v ?? '').trim().isEmpty ? 'Escribí un correo.' : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _adminDocumentNumber,
                            enabled: !_enviando,
                            decoration: const InputDecoration(
                              labelText: 'Documento',
                            ),
                            validator: (v) => (v ?? '').trim().isEmpty
                                ? 'Escribí el documento.'
                                : null,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    TextFormField(
                      controller: _adminPhone,
                      enabled: !_enviando,
                      decoration: const InputDecoration(labelText: 'Teléfono'),
                    ),
                  ],
                ),
              ),
            ),
            if (_error != null && _error!.fieldErrors == null) ...[
              const SizedBox(height: 16),
              Text(
                _error!.message,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 20),
            FilledButton(
              onPressed: _enviando ? null : _enviar,
              child: Text(_enviando ? 'Registrando…' : 'Registrar organización'),
            ),
          ],
        ),
      ),
    );
  }
}

class _CredencialesView extends StatefulWidget {
  const _CredencialesView({required this.creada});

  final OrganizationCreated creada;

  @override
  State<_CredencialesView> createState() => _CredencialesViewState();
}

class _CredencialesViewState extends State<_CredencialesView> {
  bool _copiado = false;

  Future<void> _copiar() async {
    final admin = widget.creada.admin;
    final org = widget.creada.organization;
    await Clipboard.setData(ClipboardData(
      text: 'Organización: ${org.slug}\n'
          'Correo: ${admin.email}\n'
          'Contraseña temporal: ${admin.temporaryPassword}',
    ));
    if (!mounted) return;
    setState(() => _copiado = true);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copiado')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final org = widget.creada.organization;
    final admin = widget.creada.admin;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(org.name, style: theme.textTheme.titleLarge),
          const SizedBox(height: 4),
          Text(
            'Ya tiene su plan ${org.currentPlan?.name ?? ""}, sus roles y su '
            'administrador.',
            style: theme.textTheme.bodyMedium
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 20),
          Card(
            color: Marca.waiting.withValues(alpha: 0.10),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const Icon(Icons.warning_amber_rounded, color: Marca.waiting),
                      const SizedBox(width: 8),
                      Text(
                        'Copiá la contraseña ahora',
                        style: theme.textTheme.titleSmall
                            ?.copyWith(color: Marca.waiting, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'Se muestra una sola vez. No queda guardada en ningún lado '
                    'y no hay forma de volver a consultarla: si se pierde, hay '
                    'que restablecerla.',
                  ),
                  const SizedBox(height: 16),
                  _dato('Organización', org.slug),
                  _dato('Correo', admin.email),
                  _dato('Contraseña temporal', admin.temporaryPassword),
                  const SizedBox(height: 16),
                  OutlinedButton.icon(
                    onPressed: _copiar,
                    icon: Icon(_copiado ? Icons.check : Icons.copy),
                    label: Text(_copiado ? 'Copiado' : 'Copiar los tres datos'),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Ya la copié, volver al listado'),
          ),
        ],
      ),
    );
  }

  Widget _dato(String etiqueta, String valor) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 130,
            child: Text(etiqueta, style: const TextStyle(color: Marca.ink500)),
          ),
          Expanded(
            child: SelectableText(
              valor,
              style: const TextStyle(fontFamily: 'monospace'),
            ),
          ),
        ],
      ),
    );
  }
}
