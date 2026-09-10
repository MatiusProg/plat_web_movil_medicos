/// US-11 — Sucursales del centro médico.
///
/// Equivale a `frontend/src/paginas/Sucursales.tsx`, sin el editor de horarios
/// de atención: ese es un formulario de siete filas que en un teléfono no
/// entra con dignidad, y la agenda de cada profesional (US-13) ya define
/// cuándo se atiende en cada sede. Se deja para la web.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'branches_api.dart';
import 'catalog_comun.dart';

class BranchesScreen extends StatefulWidget {
  const BranchesScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<BranchesScreen> createState() => _BranchesScreenState();
}

class _BranchesScreenState extends State<BranchesScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<Sucursal>? _sucursales;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_sucursales == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final sucursales = await listarSucursales(client);
      if (!mounted) return;
      setState(() => _sucursales = sucursales);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _abrirFormulario({Sucursal? existente}) async {
    final guardada = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _FormularioSucursal(client: client, existente: existente),
    );
    if (guardada == true) await _cargar();
  }

  Future<void> _darDeBaja(Sucursal sucursal) async {
    if (!await confirmarBaja(context, sucursal.name)) return;
    try {
      await desactivarSucursal(client, sucursal.id);
      await _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
    } catch (_) {
      _avisar('No se pudo dar de baja la sucursal.');
    }
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(mensaje)));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Sucursales')),
      drawer: const OrganizationDrawer(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _abrirFormulario(),
        icon: const Icon(Icons.add),
        label: const Text('Nueva sucursal'),
      ),
      body: CuerpoDeCatalogo<Sucursal>(
        items: _sucursales,
        error: _error,
        onReintentar: _cargar,
        vacio: 'Todavía no hay sucursales. Creá la primera para poder cargar '
            'profesionales y agendas.',
        encabezado: Text(
          'Las sedes del centro médico. Los profesionales y las agendas usan '
          'este catálogo.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        itemBuilder: (context, sucursal) => TarjetaDeCatalogo(
          titulo: sucursal.name,
          subtitulo: sucursal.address,
          activo: sucursal.isActive,
          detalle: Text(
            '${sucursal.phone} · ${sucursal.timezone}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          onEditar: () => _abrirFormulario(existente: sucursal),
          onDarDeBaja: () => _darDeBaja(sucursal),
        ),
      ),
    );
  }
}

class _FormularioSucursal extends StatefulWidget {
  const _FormularioSucursal({required this.client, this.existente});

  final ApiClient client;
  final Sucursal? existente;

  @override
  State<_FormularioSucursal> createState() => _FormularioSucursalState();
}

class _FormularioSucursalState extends State<_FormularioSucursal> {
  final _formulario = GlobalKey<FormState>();

  late final _nombre = TextEditingController(text: widget.existente?.name);
  late final _direccion =
      TextEditingController(text: widget.existente?.address);
  late final _telefono = TextEditingController(text: widget.existente?.phone);
  // La zona horaria por omisión es la del caso de estudio. Es un campo que se
  // completa una vez y no se vuelve a mirar.
  late final _zona = TextEditingController(
    text: widget.existente?.timezone ?? 'America/La_Paz',
  );

  bool _guardando = false;
  ApiError? _error;

  bool get _esEdicion => widget.existente != null;

  @override
  void dispose() {
    _nombre.dispose();
    _direccion.dispose();
    _telefono.dispose();
    _zona.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!(_formulario.currentState?.validate() ?? false)) return;

    setState(() {
      _guardando = true;
      _error = null;
    });

    var salio = false;
    try {
      if (_esEdicion) {
        await editarSucursal(
          widget.client,
          widget.existente!.id,
          name: _nombre.text.trim(),
          address: _direccion.text.trim(),
          phone: _telefono.text.trim(),
          timezone: _zona.text.trim(),
        );
      } else {
        await crearSucursal(
          widget.client,
          name: _nombre.text.trim(),
          address: _direccion.text.trim(),
          phone: _telefono.text.trim(),
          timezone: _zona.text.trim(),
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
      setState(() => _error = null);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('No se pudo guardar la sucursal.')),
      );
    } finally {
      if (mounted && !salio) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      // El teclado tapa el botón si no se le deja lugar.
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 28),
          child: Form(
            key: _formulario,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  _esEdicion ? 'Editar sucursal' : 'Nueva sucursal',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _nombre,
                  decoration: const InputDecoration(
                    labelText: 'Nombre',
                    border: OutlineInputBorder(),
                  ),
                  validator: _obligatorio,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _direccion,
                  decoration: const InputDecoration(
                    labelText: 'Dirección',
                    border: OutlineInputBorder(),
                  ),
                  validator: _obligatorio,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _telefono,
                  keyboardType: TextInputType.phone,
                  decoration: const InputDecoration(
                    labelText: 'Teléfono',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _zona,
                  decoration: const InputDecoration(
                    labelText: 'Zona horaria',
                    helperText: 'Con la que se calculan los turnos de esta sede',
                    border: OutlineInputBorder(),
                  ),
                  validator: _obligatorio,
                ),
                if (_error != null) ...[
                  const SizedBox(height: 12),
                  Text(
                    _error!.message,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
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
      ),
    );
  }

  static String? _obligatorio(String? valor) =>
      (valor ?? '').trim().isEmpty ? 'Este campo es obligatorio.' : null;
}
