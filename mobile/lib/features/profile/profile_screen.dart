/// US-05 — Mi perfil: datos de contacto, contraseña y cierre de sesión.
///
/// Los mismos tres bloques que la web (`frontend/src/paginas/Perfil.tsx`):
///
///   1. **Datos de contacto** —nombres, teléfono, correo—, lo único editable.
///      Se manda sólo lo que cambió (punto f).
///   2. **Tu cuenta** —documento, centro médico, rol, estado—, a la vista y
///      sin casillas: cambiarlos es del administrador (punto d).
///   3. **Contraseña**, acreditando la actual. No cierra esta sesión
///      (punto c): el backend devuelve un par de tokens nuevo y la sesión lo
///      guarda con `Session.replaceTokens`.
///
/// Más un cuarto que la web no tiene: **Apariencia**, el tema claro, oscuro
/// o "como el sistema". Es una preferencia del teléfono, no de la cuenta: se
/// guarda en el aparato y no viaja al backend.
///
/// **Y el cierre de sesión vive acá.** Hasta US-05 era un botón provisional
/// en la barra de la pantalla de inicio; el reparto del Sprint 1 lo ubicaba
/// en el perfil desde el principio.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/core/theme/theme_controller.dart';
import 'package:mobile/core/widgets/theme_selector.dart';

import 'profile_api.dart';

/// El verde de "se guardó". `primaryDark` sobre la tarjeta oscura apenas se
/// distingue del fondo, así que en modo oscuro se usa el tono claro.
Color _verdeDeExito(BuildContext context) =>
    Theme.of(context).brightness == Brightness.dark
        ? Marca.primaryLight
        : Marca.primaryDark;

const _nombreDocumento = {
  'CI': 'Cédula de identidad',
  'PAS': 'Pasaporte',
  'NIT': 'NIT',
  'OTRO': 'Otro',
};

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({
    super.key,
    this.client,
    this.onTokens,
    this.onSaved,
    this.onSignOut,
  });

  /// En las pruebas se inyectan el cliente y lo que hace la sesión; en la
  /// aplicación, todo sale de `SessionScope`.
  @visibleForTesting
  final ApiClient? client;
  @visibleForTesting
  final Future<void> Function(NewTokens tokens)? onTokens;
  @visibleForTesting
  final Future<void> Function()? onSaved;
  @visibleForTesting
  final Future<void> Function()? onSignOut;

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  ApiClient? _client;
  Profile? _perfil;
  String? _errorCarga;
  bool _cargando = true;
  bool _pedido = false;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Acá y no en `initState`: el cliente sale de `SessionScope`, que no se
    // puede leer antes de que el widget tenga dependencias.
    if (!_pedido) {
      _pedido = true;
      _cargar();
    }
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _errorCarga = null;
    });
    try {
      final perfil = await obtenerPerfil(client);
      if (!mounted) return;
      setState(() => _perfil = perfil);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _errorCarga = error.message);
    } catch (_) {
      if (!mounted) return;
      setState(
        () => _errorCarga =
            'El servidor respondió algo que no se pudo interpretar.',
      );
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _guardarTokens(NewTokens tokens) async {
    final propio = widget.onTokens;
    if (propio != null) return propio(tokens);
    await SessionScope.of(
      context,
    ).replaceTokens(access: tokens.access, refresh: tokens.refresh);
  }

  Future<void> _avisarGuardado() async {
    final propio = widget.onSaved;
    if (propio != null) return propio();
    // El nombre que muestra la pantalla de inicio sale de la sesión.
    await SessionScope.of(context).recargarUsuario();
  }

  Future<void> _salir() async {
    final propio = widget.onSignOut;
    if (propio != null) return propio();
    await SessionScope.of(context).signOut();
  }

  @override
  Widget build(BuildContext context) {
    final perfil = _perfil;

    return Scaffold(
      appBar: AppBar(title: const Text('Mi perfil')),
      body: _cargando && perfil == null
          ? const Center(child: CircularProgressIndicator())
          : perfil == null
          ? _ErrorDeCarga(motivo: _errorCarga ?? '', onReintentar: _cargar)
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _DatosDeContacto(
                  perfil: perfil,
                  client: client,
                  onGuardado: (nuevo) async {
                    setState(() => _perfil = nuevo);
                    await _avisarGuardado();
                  },
                ),
                const SizedBox(height: 16),
                _TuCuenta(perfil: perfil),
                const SizedBox(height: 16),
                _CambioDeContrasena(
                  client: client,
                  onTokens: _guardarTokens,
                ),
                if (ThemeScope.maybeOf(context) case final tema?) ...[
                  const SizedBox(height: 16),
                  _Apariencia(controller: tema),
                ],
                const SizedBox(height: 24),
                OutlinedButton.icon(
                  onPressed: _salir,
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Marca.danger,
                    side: const BorderSide(color: Marca.danger),
                    minimumSize: const Size.fromHeight(48),
                  ),
                  icon: const Icon(Icons.logout),
                  label: const Text('Cerrar sesión'),
                ),
                const SizedBox(height: 16),
              ],
            ),
    );
  }
}

// ---------------------------------------------------------------------------
//  1. Datos de contacto
// ---------------------------------------------------------------------------

class _DatosDeContacto extends StatefulWidget {
  const _DatosDeContacto({
    required this.perfil,
    required this.client,
    required this.onGuardado,
  });

  final Profile perfil;
  final ApiClient client;
  final Future<void> Function(Profile nuevo) onGuardado;

  @override
  State<_DatosDeContacto> createState() => _DatosDeContactoState();
}

class _DatosDeContactoState extends State<_DatosDeContacto> {
  late final _nombres = TextEditingController(text: widget.perfil.firstName);
  late final _apellidos = TextEditingController(text: widget.perfil.lastName);
  late final _telefono = TextEditingController(text: widget.perfil.phone);
  late final _correo = TextEditingController(text: widget.perfil.email);

  bool _guardando = false;
  ApiError? _error;
  bool _guardado = false;

  @override
  void initState() {
    super.initState();
    for (final c in [_nombres, _apellidos, _telefono, _correo]) {
      c.addListener(_alEscribir);
    }
  }

  @override
  void dispose() {
    for (final c in [_nombres, _apellidos, _telefono, _correo]) {
      c.dispose();
    }
    super.dispose();
  }

  // Redibuja para habilitar "Guardar" y borra el "se guardaron" anterior.
  void _alEscribir() => setState(() => _guardado = false);

  /// Sólo lo que cambió respecto del perfil guardado (punto f).
  Map<String, String> get _cambios {
    final p = widget.perfil;
    return {
      if (_nombres.text != p.firstName) 'first_name': _nombres.text,
      if (_apellidos.text != p.lastName) 'last_name': _apellidos.text,
      if (_telefono.text != p.phone) 'phone': _telefono.text,
      if (_correo.text.trim() != p.email) 'email': _correo.text.trim(),
    };
  }

  Future<void> _guardar() async {
    final cambios = _cambios;
    if (cambios.isEmpty) return;
    setState(() {
      _guardando = true;
      _error = null;
    });
    try {
      final nuevo = await actualizarPerfil(widget.client, cambios);
      // El backend recorta espacios: se muestra lo que quedó guardado.
      _nombres.text = nuevo.firstName;
      _apellidos.text = nuevo.lastName;
      _telefono.text = nuevo.phone;
      _correo.text = nuevo.email;
      await widget.onGuardado(nuevo);
      if (mounted) setState(() => _guardado = true);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final error = _error;
    final sinCampo = error != null && error.fieldErrors == null;

    return _Tarjeta(
      titulo: 'Datos de contacto',
      children: [
        TextField(
          controller: _nombres,
          enabled: !_guardando,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(
            labelText: 'Nombres',
            errorText: error?.forField('first_name'),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _apellidos,
          enabled: !_guardando,
          textCapitalization: TextCapitalization.words,
          decoration: InputDecoration(
            labelText: 'Apellidos',
            errorText: error?.forField('last_name'),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _telefono,
          enabled: !_guardando,
          keyboardType: TextInputType.phone,
          decoration: InputDecoration(
            labelText: 'Teléfono',
            errorText: error?.forField('phone'),
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _correo,
          enabled: !_guardando,
          keyboardType: TextInputType.emailAddress,
          autocorrect: false,
          decoration: InputDecoration(
            labelText: 'Correo',
            helperText: 'Es el correo con el que inicias sesión.',
            errorText: error?.forField('email'),
          ),
        ),
        if (sinCampo) ...[
          const SizedBox(height: 12),
          Text(error.message, style: const TextStyle(color: Marca.danger)),
        ],
        if (_guardado) ...[
          const SizedBox(height: 12),
          Text(
            'Tus datos se guardaron.',
            style: TextStyle(color: _verdeDeExito(context)),
          ),
        ],
        const SizedBox(height: 16),
        FilledButton(
          onPressed: _guardando || _cambios.isEmpty ? null : _guardar,
          child: Text(_guardando ? 'Guardando…' : 'Guardar cambios'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
//  2. Tu cuenta — lo que no se edita acá
// ---------------------------------------------------------------------------

class _TuCuenta extends StatelessWidget {
  const _TuCuenta({required this.perfil});

  final Profile perfil;

  @override
  Widget build(BuildContext context) {
    final documento =
        '${_nombreDocumento[perfil.documentType] ?? perfil.documentType} '
        '${perfil.documentNumber}';
    final rol = perfil.isPlatformAdmin
        ? 'Superadministrador de plataforma'
        : perfil.roles.isEmpty
        ? 'Sin rol asignado'
        : perfil.roles.join(', ');

    return _Tarjeta(
      titulo: 'Tu cuenta',
      children: [
        _Dato(termino: 'Documento', valor: documento),
        _Dato(
          termino: 'Centro médico',
          valor: perfil.organizationName ?? 'Plataforma',
        ),
        _Dato(termino: 'Rol', valor: rol),
        _Dato(termino: 'Estado', valor: perfil.isActive ? 'Activa' : 'Inactiva'),
        const SizedBox(height: 8),
        const Text(
          'Estos datos sólo los puede cambiar el administrador de tu centro '
          'médico.',
          style: TextStyle(color: Marca.ink500, fontSize: 13),
        ),
      ],
    );
  }
}

class _Dato extends StatelessWidget {
  const _Dato({required this.termino, required this.valor});

  final String termino;
  final String valor;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(termino, style: const TextStyle(color: Marca.ink500, fontSize: 12)),
          const SizedBox(height: 2),
          Text(valor, style: const TextStyle(fontWeight: FontWeight.w500)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
//  3. Contraseña
// ---------------------------------------------------------------------------

class _CambioDeContrasena extends StatefulWidget {
  const _CambioDeContrasena({required this.client, required this.onTokens});

  final ApiClient client;
  final Future<void> Function(NewTokens tokens) onTokens;

  @override
  State<_CambioDeContrasena> createState() => _CambioDeContrasenaState();
}

class _CambioDeContrasenaState extends State<_CambioDeContrasena> {
  final _actual = TextEditingController();
  final _nueva = TextEditingController();
  final _repetida = TextEditingController();

  bool _ver = false;
  bool _enviando = false;
  ApiError? _error;
  String? _cambiada;

  @override
  void initState() {
    super.initState();
    for (final c in [_actual, _nueva, _repetida]) {
      c.addListener(() => setState(() {}));
    }
  }

  @override
  void dispose() {
    for (final c in [_actual, _nueva, _repetida]) {
      c.dispose();
    }
    super.dispose();
  }

  bool get _completo =>
      _actual.text.isNotEmpty &&
      _nueva.text.isNotEmpty &&
      _repetida.text.isNotEmpty;

  Future<void> _cambiar() async {
    setState(() {
      _enviando = true;
      _error = null;
      _cambiada = null;
    });
    try {
      final tokens = await cambiarContrasena(
        widget.client,
        actual: _actual.text,
        nueva: _nueva.text,
        repetida: _repetida.text,
      );
      // Antes que nada: los refrescos anteriores ya están en la lista negra.
      await widget.onTokens(tokens);
      _actual.clear();
      _nueva.clear();
      _repetida.clear();
      if (mounted) setState(() => _cambiada = tokens.message);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final error = _error;
    final sinCampo = error != null && error.fieldErrors == null;

    InputDecoration decoracion(String etiqueta, String campo, {String? ayuda}) =>
        InputDecoration(
          labelText: etiqueta,
          helperText: ayuda,
          helperMaxLines: 2,
          errorText: error?.forField(campo),
          errorMaxLines: 3,
        );

    return _Tarjeta(
      titulo: 'Contraseña',
      children: [
        TextField(
          controller: _actual,
          enabled: !_enviando,
          obscureText: !_ver,
          autocorrect: false,
          enableSuggestions: false,
          decoration: decoracion('Contraseña actual', 'current_password'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _nueva,
          enabled: !_enviando,
          obscureText: !_ver,
          autocorrect: false,
          enableSuggestions: false,
          decoration: decoracion(
            'Contraseña nueva',
            'password',
            ayuda:
                'Al menos 8 caracteres, que no sea sólo números ni se parezca '
                'a tu correo.',
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _repetida,
          enabled: !_enviando,
          obscureText: !_ver,
          autocorrect: false,
          enableSuggestions: false,
          decoration: decoracion(
            'Repite la contraseña nueva',
            'password_confirmation',
          ),
        ),
        CheckboxListTile(
          value: _ver,
          onChanged: _enviando ? null : (v) => setState(() => _ver = v ?? false),
          title: const Text('Mostrar las contraseñas'),
          contentPadding: EdgeInsets.zero,
          controlAffinity: ListTileControlAffinity.leading,
          dense: true,
        ),
        if (sinCampo)
          Text(error.message, style: const TextStyle(color: Marca.danger)),
        if (_cambiada != null)
          Text(_cambiada!, style: TextStyle(color: _verdeDeExito(context))),
        const SizedBox(height: 12),
        FilledButton(
          onPressed: _enviando || !_completo ? null : _cambiar,
          child: Text(_enviando ? 'Cambiando…' : 'Cambiar contraseña'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
//  4. Apariencia
// ---------------------------------------------------------------------------

class _Apariencia extends StatelessWidget {
  const _Apariencia({required this.controller});

  final ThemeController controller;

  @override
  Widget build(BuildContext context) {
    return _Tarjeta(
      titulo: 'Apariencia',
      children: [
        ThemeSelector(controller: controller),
        const SizedBox(height: 8),
        const Text(
          '"Sistema" sigue el modo claro u oscuro del teléfono. Se guarda en '
          'este teléfono.',
          style: TextStyle(color: Marca.ink500, fontSize: 13),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------

class _Tarjeta extends StatelessWidget {
  const _Tarjeta({required this.titulo, required this.children});

  final String titulo;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              titulo.toUpperCase(),
              style: const TextStyle(
                color: Marca.ink500,
                fontSize: 12,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.8,
              ),
            ),
            const SizedBox(height: 12),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _ErrorDeCarga extends StatelessWidget {
  const _ErrorDeCarga({required this.motivo, required this.onReintentar});

  final String motivo;
  final VoidCallback onReintentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text(
              'No se pudo cargar tu perfil.',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            Text(motivo, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton(onPressed: onReintentar, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }
}
