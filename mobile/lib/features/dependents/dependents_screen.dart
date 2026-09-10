/// US-07 — Las personas que el titular tiene a cargo.
///
/// Listado, alta, edición, baja del vínculo y paso a titular. Es una pantalla
/// **sólo móvil**: el caso de uso es el titular administrando a su familia
/// desde el teléfono, no el personal del centro médico.
///
/// La baja dice "Ya no está a mi cargo" y no "Eliminar", porque eso es lo que
/// hace: la ficha y su historial siguen existiendo (punto e). Un botón que
/// dijera "Eliminar" prometería algo que el sistema no hace —ni debe hacer— y
/// dejaría a la persona creyendo que borró datos clínicos.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';

import 'dependents_api.dart';

class DependentsScreen extends StatefulWidget {
  const DependentsScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<DependentsScreen> createState() => _DependentsScreenState();
}

class _DependentsScreenState extends State<DependentsScreen> {
  ApiClient? _client;
  List<Dependiente>? _dependientes;
  String? _error;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_dependientes == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    try {
      final lista = await listarDependientes(client);
      if (!mounted) return;
      setState(() {
        _dependientes = lista;
        _error = null;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _abrirAlta() async {
    final creado = await context.push<bool>('/dependents/new');
    if (creado == true) _cargar();
  }

  Future<void> _desvincular(Dependiente dependiente) async {
    final confirmado = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text('¿${dependiente.fullName} ya no está a tu cargo?'),
        content: const Text(
          'Su ficha y su historial no se borran: dejás de poder reservarle '
          'fichas y de ver sus antecedentes.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: const Text('Cancelar'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(true),
            child: const Text('Quitar de mi cargo'),
          ),
        ],
      ),
    );
    if (confirmado != true) return;

    try {
      await desvincularDependiente(client, dependiente.id);
      if (!mounted) return;
      _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
    }
  }

  Future<void> _promover(Dependiente dependiente) async {
    final datos = await showDialog<({String email, String password})>(
      context: context,
      builder: (context) => _DialogoPromocion(nombre: dependiente.fullName),
    );
    if (datos == null) return;

    try {
      await promoverATitular(
        client,
        dependiente.id,
        email: datos.email,
        password: datos.password,
      );
      if (!mounted) return;
      _avisar('${dependiente.fullName} ya tiene su propia cuenta.');
      _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
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

    return Scaffold(
      appBar: AppBar(title: const Text('Personas a cargo')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _abrirAlta,
        icon: const Icon(Icons.person_add_alt),
        label: const Text('Agregar'),
      ),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: _cuerpo(theme),
      ),
    );
  }

  Widget _cuerpo(ThemeData theme) {
    if (_error != null) {
      return ListView(
        padding: const EdgeInsets.all(24),
        children: [Text(_error!, style: TextStyle(color: theme.colorScheme.error))],
      );
    }

    final dependientes = _dependientes;
    if (dependientes == null) {
      return const Center(child: CircularProgressIndicator());
    }

    if (dependientes.isEmpty) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(24, 48, 24, 24),
        children: [
          Icon(Icons.family_restroom,
              size: 48, color: theme.colorScheme.outline),
          const SizedBox(height: 16),
          Text('Todavía no agregaste a nadie',
              textAlign: TextAlign.center, style: theme.textTheme.titleMedium),
          const SizedBox(height: 8),
          Text(
            'Acá se agregan los familiares que están a tu cargo para poder '
            'reservarles fichas y registrar sus antecedentes. No necesitan '
            'tener cuenta propia.',
            textAlign: TextAlign.center,
            style: theme.textTheme.bodyMedium,
          ),
        ],
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 96),
      itemCount: dependientes.length,
      separatorBuilder: (_, _) => const SizedBox(height: 8),
      itemBuilder: (context, indice) {
        final dependiente = dependientes[indice];
        return Card(
          child: ListTile(
            leading: CircleAvatar(
              radius: 18,
              backgroundColor: Marca.surfaceTint,
              child: const Icon(Icons.person_outline, color: Marca.primary, size: 18),
            ),
            title: Text(dependiente.fullName),
            subtitle: Text(
              [
                dependiente.relationshipLabel,
                if (dependiente.age != null) '${dependiente.age} años',
                if (dependiente.documentNumber != null &&
                    dependiente.documentNumber!.isNotEmpty)
                  'CI ${dependiente.documentNumber}',
              ].join(' · '),
            ),
            trailing: PopupMenuButton<String>(
              onSelected: (opcion) {
                if (opcion == 'promover') _promover(dependiente);
                if (opcion == 'desvincular') _desvincular(dependiente);
              },
              itemBuilder: (context) => const [
                PopupMenuItem(
                  value: 'promover',
                  child: Text('Pasar a cuenta propia'),
                ),
                PopupMenuItem(
                  value: 'desvincular',
                  child: Text('Ya no está a mi cargo'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// El paso a titular del punto (f): lo único que falta es la cuenta de acceso.
class _DialogoPromocion extends StatefulWidget {
  const _DialogoPromocion({required this.nombre});

  final String nombre;

  @override
  State<_DialogoPromocion> createState() => _DialogoPromocionState();
}

class _DialogoPromocionState extends State<_DialogoPromocion> {
  final _correo = TextEditingController();
  final _clave = TextEditingController();

  @override
  void dispose() {
    _correo.dispose();
    _clave.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text('Cuenta propia para ${widget.nombre}'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Text(
            'Conserva su ficha y todo su historial; sólo suma con qué entrar. '
            'A partir de ahí deja de estar a tu cargo.',
          ),
          const SizedBox(height: 16),
          TextField(
            controller: _correo,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Correo',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _clave,
            obscureText: true,
            decoration: const InputDecoration(
              labelText: 'Contraseña',
              border: OutlineInputBorder(),
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop((
            email: _correo.text.trim(),
            password: _clave.text,
          )),
          child: const Text('Crear cuenta'),
        ),
      ],
    );
  }
}
