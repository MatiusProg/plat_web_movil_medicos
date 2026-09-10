/// US-12 — Especialidades del centro médico.
///
/// Equivale a `frontend/src/paginas/Especialidades.tsx`, la más chica de las
/// tres del catálogo: nombre y descripción.
///
/// El archivo se llama `_admin` para no confundirse con
/// `features/search/specialties_screen.dart`, que es la pantalla del paciente
/// —"elegí una especialidad para buscar"— sobre el mismo recurso.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'catalog_comun.dart';
import 'specialties_api.dart';

class SpecialtiesAdminScreen extends StatefulWidget {
  const SpecialtiesAdminScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<SpecialtiesAdminScreen> createState() => _SpecialtiesAdminScreenState();
}

class _SpecialtiesAdminScreenState extends State<SpecialtiesAdminScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<Especialidad>? _especialidades;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_especialidades == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final especialidades = await listarEspecialidadesAdmin(client);
      if (!mounted) return;
      setState(() => _especialidades = especialidades);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _abrirFormulario({Especialidad? existente}) async {
    final guardada = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) =>
          _FormularioEspecialidad(client: client, existente: existente),
    );
    if (guardada == true) await _cargar();
  }

  Future<void> _darDeBaja(Especialidad especialidad) async {
    if (!await confirmarBaja(context, especialidad.name)) return;
    try {
      await desactivarEspecialidad(client, especialidad.id);
      await _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
    } catch (_) {
      _avisar('No se pudo dar de baja la especialidad.');
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
      appBar: AppBar(title: const Text('Especialidades')),
      drawer: const OrganizationDrawer(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _abrirFormulario(),
        icon: const Icon(Icons.add),
        label: const Text('Nueva especialidad'),
      ),
      body: CuerpoDeCatalogo<Especialidad>(
        items: _especialidades,
        error: _error,
        onReintentar: _cargar,
        vacio: 'Todavía no hay especialidades. Creá la primera para poder '
            'asignárselas a los profesionales.',
        encabezado: Text(
          'Con estas especialidades los pacientes filtran la búsqueda de '
          'profesionales.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        itemBuilder: (context, especialidad) => TarjetaDeCatalogo(
          titulo: especialidad.name,
          subtitulo: especialidad.description,
          activo: especialidad.isActive,
          onEditar: () => _abrirFormulario(existente: especialidad),
          onDarDeBaja: () => _darDeBaja(especialidad),
        ),
      ),
    );
  }
}

class _FormularioEspecialidad extends StatefulWidget {
  const _FormularioEspecialidad({required this.client, this.existente});

  final ApiClient client;
  final Especialidad? existente;

  @override
  State<_FormularioEspecialidad> createState() =>
      _FormularioEspecialidadState();
}

class _FormularioEspecialidadState extends State<_FormularioEspecialidad> {
  final _formulario = GlobalKey<FormState>();

  late final _nombre = TextEditingController(text: widget.existente?.name);
  late final _descripcion =
      TextEditingController(text: widget.existente?.description);

  bool _guardando = false;
  ApiError? _error;

  bool get _esEdicion => widget.existente != null;

  @override
  void dispose() {
    _nombre.dispose();
    _descripcion.dispose();
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
        await editarEspecialidad(
          widget.client,
          widget.existente!.id,
          name: _nombre.text.trim(),
          description: _descripcion.text.trim(),
        );
      } else {
        await crearEspecialidad(
          widget.client,
          name: _nombre.text.trim(),
          description: _descripcion.text.trim(),
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
        const SnackBar(content: Text('No se pudo guardar la especialidad.')),
      );
    } finally {
      if (mounted && !salio) setState(() => _guardando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
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
                  _esEdicion ? 'Editar especialidad' : 'Nueva especialidad',
                  style: Theme.of(context).textTheme.titleLarge,
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _nombre,
                  decoration: const InputDecoration(
                    labelText: 'Nombre',
                    border: OutlineInputBorder(),
                  ),
                  validator: (v) => (v ?? '').trim().isEmpty
                      ? 'Poné un nombre.'
                      : null,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _descripcion,
                  maxLines: 3,
                  decoration: const InputDecoration(
                    labelText: 'Descripción (opcional)',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
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
}
