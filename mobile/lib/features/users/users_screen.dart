/// US-04 — Usuarios de la organización y sus roles.
///
/// Equivale a `frontend/src/paginas/Usuarios.tsx`. **No se dan de alta desde
/// acá**: el endpoint es de sólo lectura y las cuentas nacen del registro
/// (US-01) o del alta de organización (US-43). Lo que sí se hace es asignar y
/// quitar roles, que es la operación del día a día.
library;

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

  List<UsuarioDeOrganizacion>? _usuarios;
  List<Rol> _roles = const [];
  Map<String, int> _asignaciones = const {};
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_usuarios == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      // Las tres juntas: los roles y las asignaciones hacen falta para poder
      // asignar y quitar, y encadenarlas triplicaría la espera.
      final resultados = await Future.wait([
        listarUsuarios(client),
        listarRoles(client),
        mapaDeAsignaciones(client),
      ]);
      if (!mounted) return;
      setState(() {
        _usuarios = resultados[0] as List<UsuarioDeOrganizacion>;
        _roles = resultados[1] as List<Rol>;
        _asignaciones = resultados[2] as Map<String, int>;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _gestionarRoles(UsuarioDeOrganizacion usuario) async {
    final cambiado = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _RolesDelUsuario(
        client: client,
        usuario: usuario,
        roles: _roles,
        asignaciones: _asignaciones,
      ),
    );
    if (cambiado == true) await _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final usuarios = _usuarios;

    return Scaffold(
      appBar: AppBar(title: const Text('Usuarios')),
      drawer: const OrganizationDrawer(),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            Text(
              'Las cuentas de tu organización. Desde acá se les asignan y '
              'quitan roles; las altas se hacen por el registro.',
              style: theme.textTheme.bodySmall,
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
                    onPressed: _cargar,
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
              const Text('Todavía no hay usuarios en tu organización.')
            else
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
    required this.asignaciones,
  });

  final ApiClient client;
  final UsuarioDeOrganizacion usuario;
  final List<Rol> roles;
  final Map<String, int> asignaciones;

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
        final clave = '${widget.usuario.id}|${rol.id}';
        final asignacionId = widget.asignaciones[clave];
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
