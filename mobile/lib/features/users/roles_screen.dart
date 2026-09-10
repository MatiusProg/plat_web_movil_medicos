/// US-04 — Roles y permisos de la organización.
///
/// Equivale a `frontend/src/paginas/Roles.tsx`, la pantalla más grande de la
/// web (555 líneas) por la matriz de permisos.
///
/// **Los permisos se agrupan por módulo y cada grupo arranca plegado.** Son
/// más de treinta: una lista plana de casillas en un teléfono es scroll puro y
/// nadie encuentra lo que busca. Agrupados por `catalog`, `scheduling`,
/// `users`… se lee de un vistazo cuántos hay elegidos en cada área.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'users_api.dart';

class RolesScreen extends StatefulWidget {
  const RolesScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<RolesScreen> createState() => _RolesScreenState();
}

class _RolesScreenState extends State<RolesScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<Rol>? _roles;
  List<Permiso> _permisos = const [];
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_roles == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final resultados = await Future.wait([
        listarRoles(client),
        listarPermisos(client),
      ]);
      if (!mounted) return;
      setState(() {
        _roles = resultados[0] as List<Rol>;
        _permisos = resultados[1] as List<Permiso>;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _abrirFormulario({Rol? existente}) async {
    if (_permisos.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('No se pudo cargar el catálogo de permisos.'),
        ),
      );
      return;
    }
    final guardado = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _FormularioRol(
        client: client,
        permisos: _permisos,
        existente: existente,
      ),
    );
    if (guardado == true) await _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final roles = _roles;

    return Scaffold(
      appBar: AppBar(title: const Text('Roles y permisos')),
      drawer: const OrganizationDrawer(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _abrirFormulario(),
        icon: const Icon(Icons.add),
        label: const Text('Nuevo rol'),
      ),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
          children: [
            Text(
              'Qué puede hacer cada rol. Esconder un permiso no autoriza nada: '
              'la puerta real la pone el servidor.',
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
            else if (roles == null)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (roles.isEmpty)
              const Text('Todavía no hay roles definidos.')
            else
              for (final rol in roles)
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
                                rol.name,
                                style: theme.textTheme.titleMedium,
                              ),
                            ),
                            if (rol.isSystem)
                              Chip(
                                label: const Text('Del sistema'),
                                visualDensity: VisualDensity.compact,
                                backgroundColor:
                                    theme.colorScheme.surfaceContainerHighest,
                              ),
                          ],
                        ),
                        if (rol.description.isNotEmpty) ...[
                          const SizedBox(height: 4),
                          Text(
                            rol.description,
                            style: theme.textTheme.bodySmall,
                          ),
                        ],
                        const SizedBox(height: 6),
                        Text(
                          '${rol.permissions.length} permisos · '
                          '${rol.assignedUsers} '
                          '${rol.assignedUsers == 1 ? "usuario" : "usuarios"}',
                          style: theme.textTheme.bodySmall,
                        ),
                        Row(
                          mainAxisAlignment: MainAxisAlignment.end,
                          children: [
                            TextButton(
                              onPressed: () => _abrirFormulario(existente: rol),
                              child: const Text('Editar permisos'),
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

class _FormularioRol extends StatefulWidget {
  const _FormularioRol({
    required this.client,
    required this.permisos,
    this.existente,
  });

  final ApiClient client;
  final List<Permiso> permisos;
  final Rol? existente;

  @override
  State<_FormularioRol> createState() => _FormularioRolState();
}

class _FormularioRolState extends State<_FormularioRol> {
  final _formulario = GlobalKey<FormState>();

  late final _codigo = TextEditingController(text: widget.existente?.code);
  late final _nombre = TextEditingController(text: widget.existente?.name);
  late final _descripcion =
      TextEditingController(text: widget.existente?.description);
  late final Set<String> _elegidos = {
    ...(widget.existente?.permissions ?? const <String>[]),
  };

  bool _guardando = false;
  ApiError? _error;

  bool get _esEdicion => widget.existente != null;

  /// La misma regla que aplica el backend, comprobada antes de mandar.
  ///
  /// Sin esto el formulario aceptaba "Rol De Prueba", lo enviaba, y el 400
  /// volvía con el motivo escrito al pie de una pantalla larga. Quien lo usa
  /// intenta tres o cuatro veces sin entender qué está mal: la regla no está
  /// escrita en ningún lado que se lea antes de escribir.
  static final _formatoDelCodigo = RegExp(r'^[a-z][a-z0-9_]{2,39}$');

  static String? _validarCodigo(String? valor) {
    final codigo = (valor ?? '').trim();
    if (codigo.isEmpty) return 'Poné un código.';
    if (!_formatoDelCodigo.hasMatch(codigo)) {
      return 'En minúsculas, empezando con letra. Se admiten números y '
          'guión bajo, entre 3 y 40 caracteres.';
    }
    return null;
  }

  /// Los permisos agrupados por módulo, en orden.
  Map<String, List<Permiso>> get _porModulo {
    final mapa = <String, List<Permiso>>{};
    for (final permiso in widget.permisos) {
      mapa.putIfAbsent(permiso.module, () => []).add(permiso);
    }
    return mapa;
  }

  @override
  void dispose() {
    _codigo.dispose();
    _nombre.dispose();
    _descripcion.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!(_formulario.currentState?.validate() ?? false)) return;
    if (_elegidos.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Elegí al menos un permiso.')),
      );
      return;
    }

    setState(() {
      _guardando = true;
      _error = null;
    });

    var salio = false;
    try {
      if (_esEdicion) {
        await editarRol(
          widget.client,
          widget.existente!.id,
          name: _nombre.text.trim(),
          description: _descripcion.text.trim(),
          permissions: _elegidos.toList(),
        );
      } else {
        await crearRol(
          widget.client,
          code: _codigo.text.trim(),
          name: _nombre.text.trim(),
          description: _descripcion.text.trim(),
          permissions: _elegidos.toList(),
        );
      }
      if (!mounted) return;
      salio = true;
      Navigator.of(context).pop(true);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo guardar el rol.')),
      );
    } finally {
      if (mounted && !salio) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.85,
        maxChildSize: 0.95,
        builder: (context, scroll) => Form(
          key: _formulario,
          child: ListView(
            controller: scroll,
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
            children: [
              Text(
                _esEdicion ? 'Editar rol' : 'Nuevo rol',
                style: theme.textTheme.titleLarge,
              ),
              const SizedBox(height: 16),

              TextFormField(
                controller: _codigo,
                // El código es la clave con la que se referencia al rol: el
                // backend no lo deja cambiar después de crearlo.
                enabled: !_esEdicion,
                decoration: InputDecoration(
                  labelText: 'Código',
                  helperText: _esEdicion
                      ? 'No se puede cambiar después de crear el rol'
                      : 'En minúsculas, sin espacios: recepcion, enfermeria_2',
                  border: const OutlineInputBorder(),
                  // El error del backend se pinta acá y no al pie: cuando el
                  // código ya existe, el mensaje tiene que estar donde está
                  // el campo que hay que cambiar.
                  errorText: _error?.forField('code'),
                ),
                validator: _validarCodigo,
                // Sin esto, el error del servidor queda pegado al campo aunque
                // ya se haya corregido: `errorText` gana sobre el validador.
                onChanged: (_) {
                  if (_error != null) setState(() => _error = null);
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _nombre,
                decoration: const InputDecoration(
                  labelText: 'Nombre',
                  border: OutlineInputBorder(),
                ),
                validator: (v) =>
                    (v ?? '').trim().isEmpty ? 'Poné un nombre.' : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _descripcion,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Descripción (opcional)',
                  border: OutlineInputBorder(),
                  alignLabelWithHint: true,
                ),
              ),

              const SizedBox(height: 20),
              Text('Permisos', style: theme.textTheme.titleSmall),
              Text(
                '${_elegidos.length} de ${widget.permisos.length} elegidos',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),

              for (final grupo in _porModulo.entries)
                ExpansionTile(
                  tilePadding: EdgeInsets.zero,
                  title: Text(grupo.key),
                  subtitle: Text(
                    '${grupo.value.where((p) => _elegidos.contains(p.code)).length}'
                    ' de ${grupo.value.length}',
                    style: theme.textTheme.bodySmall,
                  ),
                  children: [
                    for (final permiso in grupo.value)
                      CheckboxListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(permiso.code),
                        subtitle: permiso.description.isEmpty
                            ? null
                            : Text(permiso.description),
                        value: _elegidos.contains(permiso.code),
                        onChanged: (marcado) => setState(() {
                          if (marcado ?? false) {
                            _elegidos.add(permiso.code);
                          } else {
                            _elegidos.remove(permiso.code);
                          }
                        }),
                      ),
                  ],
                ),

              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!.message,
                  style: TextStyle(color: theme.colorScheme.error),
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
