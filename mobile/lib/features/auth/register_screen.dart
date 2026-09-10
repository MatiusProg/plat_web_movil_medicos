/// US-01 — Pantalla de registro de paciente.
///
/// Es el espejo móvil de `frontend/src/paginas/RegistroPaciente.tsx`. El
/// backend (`accounts/views/registration.py`) no deja tokens en la
/// respuesta del alta, así que después de crear la cuenta se entra con las
/// mismas credenciales (`AuthService.registerPatient`) en vez de mandar a la
/// persona a escribir de nuevo lo que ya escribió.
///
/// La navegación al entrar tampoco se hace acá: como en el ingreso, el
/// router redirige solo cuando la sesión pasa a iniciada
/// (`refreshListenable` en `core/router/app_router.dart`).
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/brand_header.dart';
import 'auth_service.dart';

class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _organization = TextEditingController();
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _documentNumber = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _passwordConfirmation = TextEditingController();

  bool _showPassword = false;
  bool _submitting = false;
  ApiError? _error;

  @override
  void dispose() {
    _organization.dispose();
    _firstName.dispose();
    _lastName.dispose();
    _documentNumber.dispose();
    _email.dispose();
    _password.dispose();
    _passwordConfirmation.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_submitting) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;

    FocusScope.of(context).unfocus();

    setState(() {
      _submitting = true;
      _error = null;
    });

    final session = SessionScope.of(context);

    try {
      await AuthService(session: session).registerPatient(
        organization: _organization.text.trim(),
        email: _email.text.trim(),
        password: _password.text,
        passwordConfirmation: _passwordConfirmation.text,
        documentNumber: _documentNumber.text.trim(),
        firstName: _firstName.text.trim(),
        lastName: _lastName.text.trim(),
      );
      // No se navega: el router lo hace cuando la sesión pasa a iniciada.
      return;
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const BrandHeader(compact: true),
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Row(
                            children: [
                              IconButton(
                                onPressed: () => context.pop(),
                                icon: const Icon(Icons.arrow_back_rounded),
                                padding: EdgeInsets.zero,
                              ),
                              const SizedBox(width: 4),
                              Text(
                                'Registrate como paciente',
                                style: theme.textTheme.headlineSmall
                                    ?.copyWith(fontWeight: FontWeight.w600),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Creá tu cuenta en tu centro médico.',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                          const SizedBox(height: 28),

                          TextFormField(
                      controller: _organization,
                      enabled: !_submitting,
                      autocorrect: false,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Centro médico',
                        hintText: 'kolping',
                        helperText: 'El identificador que te dio tu centro médico.',
                        errorText: _error?.forField('organization'),
                        prefixIcon: const Icon(Icons.apartment_outlined),
                      ),
                      validator: (value) => (value ?? '').trim().isEmpty
                          ? 'Escribí tu centro médico.'
                          : null,
                    ),
                    const SizedBox(height: 16),

                    Row(
                      children: [
                        Expanded(
                          child: TextFormField(
                            controller: _firstName,
                            enabled: !_submitting,
                            textCapitalization: TextCapitalization.words,
                            textInputAction: TextInputAction.next,
                            decoration: InputDecoration(
                              labelText: 'Nombres',
                              errorText: _error?.forField('first_name'),
                            ),
                            validator: (value) => (value ?? '').trim().isEmpty
                                ? 'Poné tu nombre.'
                                : null,
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: TextFormField(
                            controller: _lastName,
                            enabled: !_submitting,
                            textCapitalization: TextCapitalization.words,
                            textInputAction: TextInputAction.next,
                            decoration: InputDecoration(
                              labelText: 'Apellidos',
                              errorText: _error?.forField('last_name'),
                            ),
                            validator: (value) => (value ?? '').trim().isEmpty
                                ? 'Poné tu apellido.'
                                : null,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _documentNumber,
                      enabled: !_submitting,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Número de documento',
                        errorText: _error?.forField('document_number'),
                        prefixIcon: const Icon(Icons.badge_outlined),
                      ),
                      validator: (value) => (value ?? '').trim().isEmpty
                          ? 'Escribí tu número de documento.'
                          : null,
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _email,
                      enabled: !_submitting,
                      autocorrect: false,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Correo electrónico',
                        hintText: 'nombre@correo.com',
                        errorText: _error?.forField('email'),
                        prefixIcon: const Icon(Icons.mail_outline),
                      ),
                      validator: _validateEmail,
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _password,
                      enabled: !_submitting,
                      obscureText: !_showPassword,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        errorText: _error?.forField('password'),
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          onPressed: _submitting
                              ? null
                              : () => setState(
                                    () => _showPassword = !_showPassword,
                                  ),
                          tooltip: _showPassword
                              ? 'Ocultar la contraseña'
                              : 'Mostrar la contraseña',
                          icon: Icon(
                            _showPassword
                                ? Icons.visibility_off_outlined
                                : Icons.visibility_outlined,
                          ),
                        ),
                      ),
                      validator: (value) {
                        final password = value ?? '';
                        if (password.isEmpty) return 'Escribí una contraseña.';
                        if (password.length < 8) {
                          return 'Tiene que tener al menos 8 caracteres.';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _passwordConfirmation,
                      enabled: !_submitting,
                      obscureText: !_showPassword,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: 'Confirmá la contraseña',
                        errorText: _error?.forField('password_confirmation'),
                        prefixIcon: const Icon(Icons.lock_outline),
                      ),
                      validator: (value) => value != _password.text
                          ? 'Las contraseñas no coinciden.'
                          : null,
                    ),

                    if (_error != null && _error!.fieldErrors == null) ...[
                      const SizedBox(height: 20),
                      _Notice(error: _error!),
                    ],

                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _submitting ? null : _submit,
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(48),
                      ),
                      child: _submitting
                          ? const _ButtonProgress(label: 'Creando cuenta…')
                          : const Text('Crear cuenta'),
                    ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Validación de forma, no de existencia — igual que en el ingreso.
  static String? _validateEmail(String? value) {
    final email = (value ?? '').trim();
    if (email.isEmpty) return 'Escribí tu correo electrónico.';
    if (!email.contains('@') || !email.contains('.')) {
      return 'Ese correo no parece válido.';
    }
    return null;
  }
}

/// El cartel de error sin campo asociado (organización inactiva sin campo
/// específico, sin conexión, etc.), igual que en `sign_in_screen.dart`.
class _Notice extends StatelessWidget {
  const _Notice({required this.error});

  final ApiError error;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = theme.colorScheme.error;

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.10),
        border: Border.all(color: color.withValues(alpha: 0.40)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            error.isOffline ? Icons.wifi_off_outlined : Icons.error_outline,
            color: color,
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              error.message,
              style: theme.textTheme.bodyMedium?.copyWith(color: color),
            ),
          ),
        ],
      ),
    );
  }
}

/// El botón mientras espera la respuesta, igual que en `sign_in_screen.dart`.
class _ButtonProgress extends StatelessWidget {
  const _ButtonProgress({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const SizedBox(
          width: 16,
          height: 16,
          child: CircularProgressIndicator(strokeWidth: 2),
        ),
        const SizedBox(width: 10),
        Text(label),
      ],
    );
  }
}
