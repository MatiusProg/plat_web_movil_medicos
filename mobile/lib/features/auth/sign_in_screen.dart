/// US-02 — Pantalla de inicio de sesión.
///
/// Es el espejo móvil de `frontend/src/paginas/InicioSesion.tsx`, con el mismo
/// reparto de responsabilidades: casi todo el trabajo está en distinguir los
/// errores del backend, porque de eso depende que la persona sepa qué hacer.
///
///   401 credenciales_invalidas     → cartel rojo, foco de vuelta en la clave
///   423 cuenta_bloqueada           → cartel ámbar con cuenta regresiva en
///                                    vivo, formulario trabado hasta que venza
///   403 cuenta_inactiva            → cartel rojo, sin reintentar
///   400 organizacion_no_disponible → error debajo del campo del centro médico
///   0   sin_conexion               → el backend no está corriendo, o el
///                                    teléfono no llega a la IP de la red local
///
/// **Se compara contra `code`, nunca contra el texto del mensaje.** El texto lo
/// lee una persona y cambia; el código es el contrato.
///
/// La navegación al entrar no se hace acá: el router redirige solo cuando la
/// sesión cambia de estado (`refreshListenable` en `core/router/app_router.dart`).
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/brand_header.dart';
import 'auth_service.dart';

class SignInScreen extends StatefulWidget {
  const SignInScreen({super.key});

  @override
  State<SignInScreen> createState() => _SignInScreenState();
}

class _SignInScreenState extends State<SignInScreen> {
  final _formKey = GlobalKey<FormState>();
  final _organization = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _passwordFocus = FocusNode();

  bool _showPassword = false;
  bool _submitting = false;
  ApiError? _error;

  /// Lo que falta para que se libere la cuenta (RNF-07). `null` si no está
  /// bloqueada.
  Duration? _remaining;
  Timer? _countdown;

  /// El slug se prellena una sola vez, con lo que quedó guardado de la última
  /// sesión: `TokenStorage` lo conserva a propósito al cerrar sesión, porque
  /// quien sale de un centro médico casi siempre vuelve a entrar al mismo.
  bool _prefilled = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_prefilled) return;
    _prefilled = true;
    _organization.text = SessionScope.of(context).organizationSlug ?? '';
  }

  @override
  void dispose() {
    _countdown?.cancel();
    _organization.dispose();
    _email.dispose();
    _password.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  bool get _locked => _remaining != null;
  bool get _inactive => _error?.code == 'cuenta_inactiva';

  /// El formulario no acepta nada mientras se verifica, mientras la cuenta esté
  /// bloqueada, o si fue dada de baja: en esos dos casos reintentar no cambia
  /// el resultado y sólo suma intentos fallidos.
  bool get _frozen => _submitting || _locked || _inactive;

  Future<void> _submit() async {
    if (_frozen) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;

    // Cierra el teclado: en un teléfono tapa medio formulario y el cartel de
    // error aparecería detrás.
    FocusScope.of(context).unfocus();

    setState(() {
      _submitting = true;
      _error = null;
    });

    final session = SessionScope.of(context);

    try {
      await AuthService(session: session).signIn(
        organization: _organization.text.trim(),
        email: _email.text.trim(),
        password: _password.text,
      );
      // No se navega: el router lo hace cuando la sesión pasa a iniciada. Y no
      // se toca el estado, porque para entonces esta pantalla ya no está.
      return;
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        // La contraseña se limpia siempre: la que se escribió no sirvió, y
        // dejarla puesta invita a mandarla otra vez igual.
        _password.clear();
      });
      if (error.code == 'cuenta_bloqueada') _startCountdown(error.lockedUntil);
      if (error.code == 'credenciales_invalidas') _passwordFocus.requestFocus();
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  /// Arranca la cuenta regresiva del bloqueo temporal.
  ///
  /// Sin `locked_until` —un backend viejo, o un reloj que no se pudo leer— se
  /// deja el cartel sin contador y el formulario habilitado: es preferible que
  /// la persona pueda reintentar a trabarle la pantalla sin decirle hasta
  /// cuándo.
  void _startCountdown(DateTime? until) {
    _countdown?.cancel();
    if (until == null) return;

    void tick() {
      final left = until.difference(DateTime.now());
      if (left.isNegative || left.inSeconds == 0) {
        _countdown?.cancel();
        if (mounted) {
          setState(() {
            _remaining = null;
            _error = null;
          });
        }
        return;
      }
      if (mounted) setState(() => _remaining = left);
    }

    tick();
    _countdown = Timer.periodic(const Duration(seconds: 1), (_) => tick());
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    // El error del slug se pinta debajo de su campo y no en el cartel: es un
    // dato mal escrito, no un problema de credenciales.
    final organizationError = _error?.code == 'organizacion_no_disponible'
        ? (_error?.forField('organization') ?? _error?.message)
        : null;

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const BrandHeader(),
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(24, 32, 24, 32),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Text(
                            'Iniciá sesión',
                            style: theme.textTheme.headlineSmall
                                ?.copyWith(fontWeight: FontWeight.w600),
                          ),
                          const SizedBox(height: 6),
                          Text(
                            'Ingresá con tus credenciales para acceder según tu rol.',
                            style: theme.textTheme.bodyMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                          const SizedBox(height: 28),

                          TextFormField(
                      controller: _organization,
                      enabled: !_frozen,
                      autocorrect: false,
                      textInputAction: TextInputAction.next,
                      decoration: InputDecoration(
                        labelText: 'Centro médico',
                        hintText: 'kolping',
                        helperText:
                            'Dejalo vacío sólo si administrás la plataforma.',
                        errorText: organizationError,
                        prefixIcon: const Icon(Icons.apartment_outlined),
                      ),
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _email,
                      enabled: !_frozen,
                      autocorrect: false,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      decoration: const InputDecoration(
                        labelText: 'Correo electrónico',
                        hintText: 'nombre@centromedico.com',
                        prefixIcon: Icon(Icons.mail_outline),
                      ),
                      validator: _validateEmail,
                    ),
                    const SizedBox(height: 16),

                    TextFormField(
                      controller: _password,
                      focusNode: _passwordFocus,
                      enabled: !_frozen,
                      obscureText: !_showPassword,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      decoration: InputDecoration(
                        labelText: 'Contraseña',
                        prefixIcon: const Icon(Icons.lock_outline),
                        suffixIcon: IconButton(
                          onPressed: _frozen
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
                      validator: (value) => (value ?? '').isEmpty
                          ? 'Escribí tu contraseña.'
                          : null,
                    ),

                    if (_error != null && organizationError == null) ...[
                      const SizedBox(height: 20),
                      _Notice(error: _error!, remaining: _remaining),
                    ],

                    const SizedBox(height: 24),
                    FilledButton(
                      onPressed: _frozen ? null : _submit,
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(48),
                      ),
                      child: _submitting
                          ? const _ButtonProgress(label: 'Verificando…')
                          : const Text('Entrar'),
                    ),

                    const SizedBox(height: 16),
                    TextButton(
                      onPressed: _frozen ? null : () => context.push('/register'),
                      child: const Text('¿No tenés cuenta? Registrate'),
                    ),

                    const SizedBox(height: 8),
                    Text(
                      'Tu contraseña se guarda cifrada y nunca viaja en texto '
                      'plano.',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
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

  /// Validación de forma, no de existencia.
  ///
  /// Comprueba que haya algo con pinta de correo para no gastar una ida al
  /// servidor —y un intento fallido de los cinco del RNF-07— en un campo vacío
  /// o con un tipeo evidente.
  static String? _validateEmail(String? value) {
    final email = (value ?? '').trim();
    if (email.isEmpty) return 'Escribí tu correo electrónico.';
    if (!email.contains('@') || !email.contains('.')) {
      return 'Ese correo no parece válido.';
    }
    return null;
  }
}

/// El cartel de error, con el color que corresponde a lo que pasó.
///
/// El bloqueo va en ámbar y no en rojo: no es un error de quien está mirando la
/// pantalla, es una espera. Y lleva el tiempo que falta, porque un bloqueo sin
/// plazo se lee como una cuenta perdida.
class _Notice extends StatelessWidget {
  const _Notice({required this.error, this.remaining});

  final ApiError error;
  final Duration? remaining;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final locked = error.code == 'cuenta_bloqueada';

    final color = locked
        ? const Color(0xFFB26A00)
        : theme.colorScheme.error;

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
            locked
                ? Icons.timer_outlined
                : error.isOffline
                    ? Icons.wifi_off_outlined
                    : Icons.error_outline,
            color: color,
            size: 20,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  error.message,
                  style: theme.textTheme.bodyMedium?.copyWith(color: color),
                ),
                if (remaining != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    'Podés volver a intentar en ${_format(remaining!)}.',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: color,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }

  static String _format(Duration left) {
    final minutes = left.inMinutes;
    final seconds = left.inSeconds % 60;
    if (minutes == 0) return '$seconds s';
    return '$minutes:${seconds.toString().padLeft(2, '0')} min';
  }
}

/// El botón mientras espera la respuesta.
///
/// Se muestra el texto además del indicador: un botón que sólo gira no dice si
/// está verificando o si se colgó.
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
