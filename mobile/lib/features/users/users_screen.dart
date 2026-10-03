/// US-04 — Usuarios de la organización y sus roles.
///
/// Equivale a `frontend/src/paginas/Usuarios.tsx`. **No se dan de alta desde
/// acá**: el endpoint es de sólo lectura y las cuentas nacen del registro
/// (US-01) o del alta de organización (US-43). Lo que sí se hace es asignar y
/// quitar roles, que es la operación del día a día.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'users_api.dart';

class UsersScreen extends StatefulWidget {
  const UsersScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<UsersScreen> createState() => _UsersScreenState();
}

class _UsersScreenState extends State<UsersScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  final _campo = TextEditingController();
  Timer? _debounce;

  List<UsuarioDeOrganizacion>? _usuarios;
  List<Rol> _roles = const [];
  int _total = 0;
  int _pagina = 1;
  bool _hayMas = false;
  bool _cargando = false;
  String? _error;

  /// Número de la última carga pedida. Si alguien teclea mientras una
  /// respuesta viene en camino, la vieja llega después y pisaría la lista
  /// filtrada con resultados que ya no corresponden: se descarta.
  int _pedido = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_usuarios == null && _error == null && !_cargando) _cargarTodo();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _campo.dispose();
    super.dispose();
  }

  Future<void> _cargarTodo() async {
    // Los roles en paralelo con la primera página: hacen falta para poder
    // asignar, y encadenarlos duplicaría la espera. Ya no se pide el mapa de
    // asignaciones de toda la organización: se pide el de cada persona en el
    // momento de quitarle un rol (ver `_RolesDelUsuario`).
    await Future.wait([_cargarRoles(), _cargar(reiniciar: true)]);
  }

  Future<void> _cargarRoles() async {
    try {
      final roles = await listarRoles(client);
      if (!mounted) return;
      setState(() => _roles = roles);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _cargar({required bool reiniciar}) async {
    final pedido = ++_pedido;
    final pagina = reiniciar ? 1 : _pagina + 1;
    setState(() {
      _cargando = true;
      if (reiniciar) {
        _usuarios = null;
        _error = null;
      }
    });

    try {
      final resultado = await listarUsuarios(
        client,
        search: _campo.text,
        page: pagina,
      );
      if (!mounted || pedido != _pedido) return;
      setState(() {
        _pagina = pagina;
        _total = resultado.total;
        _hayMas = resultado.hayMas;
        _usuarios = [
          ...(reiniciar
              ? const <UsuarioDeOrganizacion>[]
              : _usuarios ?? const []),
          ...resultado.results,
        ];
      });
    } on ApiError catch (error) {
      if (!mounted || pedido != _pedido) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted && pedido == _pedido) setState(() => _cargando = false);
    }
  }

  void _alTeclear(String _) {
    // La misma espera que la búsqueda de profesionales: sin ella cada letra
    // es una petición al backend.
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      _cargar(reiniciar: true);
    });
  }

  Future<void> _gestionarRoles(UsuarioDeOrganizacion usuario) async {
    final cambiado = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _RolesDelUsuario(
        client: client,
        usuario: usuario,
        roles: _roles,
      ),
    );
    if (cambiado == true) await _cargar(reiniciar: true);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final usuarios = _usuarios;

    return Scaffold(
      appBar: AppBar(title: const Text('Usuarios')),
      drawer: const OrganizationDrawer(),
      body: RefreshIndicator(
        onRefresh: _cargarTodo,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            Text(
              'Las cuentas de tu organización. Desde acá se les asignan y '
              'quitan roles; las altas se hacen por el registro.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('usuarios-buscar'),
              controller: _campo,
              onChanged: _alTeclear,
              decoration: const InputDecoration(
                // "por correo" y no "por nombre": el backend filtra sólo con
                // `email__icontains`, y prometer otra cosa confunde.
                hintText: 'Buscar por correo…',
                prefixIcon: Icon(Icons.search),
              ),
            ),
            const SizedBox(height: 16),

            if (_error != null)
              Column(
                children: [
                  Text(
                    _error!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: _cargarTodo,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reintentar'),
                  ),
                ],
              )
            else if (usuarios == null)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (usuarios.isEmpty)
              Text(
                _campo.text.trim().isEmpty
                    ? 'Todavía no hay usuarios en tu organización.'
                    : 'Ningún correo coincide con la búsqueda.',
              )
            else ...[
              Text(
                // Cuántos se ven de cuántos hay: sin esto, con 25 en pantalla
                // nada indica que faltan otros 55.
                'Mostrando ${usuarios.length} de $_total '
                '${_total == 1 ? "usuario" : "usuarios"}',
                style: theme.textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              for (final usuario in usuarios)
                Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: Padding(
                    padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Expanded(
                              child: Text(
                                usuario.fullName,
                                style: theme.textTheme.titleMedium,
                              ),
                            ),
                            if (!usuario.isActive)
                              Chip(
                                label: const Text('Inactivo'),
                                visualDensity: VisualDensity.compact,
                                backgroundColor:
                                    theme.colorScheme.surfaceContainerHighest,
                              ),
                          ],
                        ),
                        Text(usuario.email, style: theme.textTheme.bodySmall),
                        const SizedBox(height: 8),
                        if (usuario.roles.isEmpty)
                          Text(
                            'Sin roles asignados',
                            style: theme.textTheme.bodySmall,
                          )
                        else
                          Wrap(
                            spacing: 6,
                            runSpacing: 4,
                            children: [
                              for (final rol in usuario.roles)
                                Chip(
                                  label: Text(rol.name),
                                  visualDensity: VisualDensity.compact,
                                  materialTapTargetSize:
                                      MaterialTapTargetSize.shrinkWrap,
                                ),
                            ],
                          ),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton(
                              onPressed: () => _gestionarRoles(usuario),
                              child: const Text('Gestionar roles'),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              if (_hayMas)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: OutlinedButton(
                    onPressed:
                        _cargando ? null : () => _cargar(reiniciar: false),
                    child: Text(_cargando ? 'Cargando…' : 'Cargar más'),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Asignar y quitar roles de una persona.
class _RolesDelUsuario extends StatefulWidget {
  const _RolesDelUsuario({
    required this.client,
    required this.usuario,
    required this.roles,
  });

  final ApiClient client;
  final UsuarioDeOrganizacion usuario;
  final List<Rol> roles;

  @override
  State<_RolesDelUsuario> createState() => _RolesDelUsuarioState();
}

class _RolesDelUsuarioState extends State<_RolesDelUsuario> {
  late final Set<String> _actuales = {
    for (final r in widget.usuario.roles) r.id,
  };

  bool _trabajando = false;
  bool _huboCambios = false;

  Future<void> _alternar(Rol rol) async {
    if (_trabajando) return;
    setState(() => _trabajando = true);

    try {
      if (_actuales.contains(rol.id)) {
        // Las asignaciones de esta persona se piden recién ahora, y frescas:
        // así aparece también la de un rol que se le acaba de dar en esta
        // misma hoja, que no estaba en ningún mapa cargado antes.
        final asignaciones = await mapaDeAsignaciones(
          widget.client,
          userId: widget.usuario.id,
        );
        final clave = '${widget.usuario.id}|${rol.id}';
        final asignacionId = asignaciones[clave];
        if (asignacionId == null) {
          _avisar('No se encontró la asignación. Actualizá y probá de nuevo.');
          return;
        }
        await quitarAsignacion(widget.client, asignacionId);
        setState(() => _actuales.remove(rol.id));
      } else {
        await asignarRol(
          widget.client,
          userId: widget.usuario.id,
          roleId: rol.id,
        );
        setState(() => _actuales.add(rol.id));
      }
      _huboCambios = true;
    } on ApiError catch (error) {
      _avisar(error.message);
    } catch (_) {
      _avisar('No se pudo cambiar el rol. Intentá de nuevo.');
    } finally {
      if (mounted) setState(() => _trabajando = false);
    }
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(mensaje)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Roles de ${widget.usuario.fullName}',
                style: theme.textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              'Los cambios se guardan al tocar cada rol.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),

            if (widget.roles.isEmpty)
              const Text('No hay roles definidos todavía.')
            else
              ...widget.roles.map(
                (rol) => SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: Text(rol.name),
                  subtitle: rol.description.isEmpty ? null : Text(
                    rol.description,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  value: _actuales.contains(rol.id),
                  onChanged: _trabajando ? null : (_) => _alternar(rol),
                ),
              ),

            const SizedBox(height: 16),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton(
                onPressed: () => Navigator.of(context).pop(_huboCambios),
                child: const Text('Listo'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
