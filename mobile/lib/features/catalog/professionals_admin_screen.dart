/// US-12 — Profesionales del centro médico.
///
/// Equivale a `frontend/src/paginas/Profesionales.tsx`. Es la más grande de
/// las tres del catálogo porque un profesional tiene dos relaciones: sus
/// especialidades y las sedes donde atiende, y las dos son de selección
/// múltiple.
///
/// Se eligen con chips y no con una lista de casillas: en un teléfono ocho
/// casillas ocupan la pantalla entera, y los chips dejan ver de un vistazo qué
/// hay elegido y qué no.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'branches_api.dart';
import 'catalog_comun.dart';
import 'professionals_api.dart';
import 'specialties_api.dart';

class ProfessionalsAdminScreen extends StatefulWidget {
  const ProfessionalsAdminScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<ProfessionalsAdminScreen> createState() =>
      _ProfessionalsAdminScreenState();
}

class _ProfessionalsAdminScreenState extends State<ProfessionalsAdminScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<Profesional>? _profesionales;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_profesionales == null && _error == null) _cargar();
  }

  Future<void> _cargar() async {
    setState(() => _error = null);
    try {
      final profesionales = await listarProfesionalesAdmin(client);
      if (!mounted) return;
      setState(() => _profesionales = profesionales);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  Future<void> _abrirFormulario({Profesional? existente}) async {
    final guardado = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) =>
          _FormularioProfesional(client: client, existente: existente),
    );
    if (guardado == true) await _cargar();
  }

  Future<void> _darDeBaja(Profesional profesional) async {
    if (!await confirmarBaja(context, profesional.fullName)) return;
    try {
      await desactivarProfesional(client, profesional.id);
      await _cargar();
    } on ApiError catch (error) {
      _avisar(error.message);
    } catch (_) {
      _avisar('No se pudo dar de baja al profesional.');
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
      appBar: AppBar(title: const Text('Profesionales')),
      drawer: const OrganizationDrawer(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _abrirFormulario(),
        icon: const Icon(Icons.add),
        label: const Text('Nuevo profesional'),
      ),
      body: CuerpoDeCatalogo<Profesional>(
        items: _profesionales,
        error: _error,
        onReintentar: _cargar,
        vacio: 'Todavía no hay profesionales. Creá el primero para poder '
            'cargarle una agenda.',
        encabezado: Text(
          'Quiénes atienden, con qué matrícula, en qué especialidades y en qué '
          'sedes.',
          style: theme.textTheme.bodySmall,
        ),
        itemBuilder: (context, profesional) => TarjetaDeCatalogo(
          titulo: profesional.fullName,
          subtitulo: profesional.licenseNumber.isEmpty
              ? null
              : 'Matrícula ${profesional.licenseNumber}',
          activo: profesional.isActive,
          detalle: Wrap(
            spacing: 6,
            runSpacing: 4,
            children: [
              for (final e in profesional.specialties)
                Chip(
                  label: Text(e.name),
                  visualDensity: VisualDensity.compact,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
              for (final b in profesional.branches)
                Chip(
                  avatar: const Icon(Icons.apartment_outlined, size: 16),
                  label: Text(b.name),
                  visualDensity: VisualDensity.compact,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                ),
            ],
          ),
          onEditar: () => _abrirFormulario(existente: profesional),
          onDarDeBaja: () => _darDeBaja(profesional),
        ),
      ),
    );
  }
}

class _FormularioProfesional extends StatefulWidget {
  const _FormularioProfesional({required this.client, this.existente});

  final ApiClient client;
  final Profesional? existente;

  @override
  State<_FormularioProfesional> createState() => _FormularioProfesionalState();
}

class _FormularioProfesionalState extends State<_FormularioProfesional> {
  final _formulario = GlobalKey<FormState>();

  late final _nombre = TextEditingController(text: widget.existente?.firstName);
  late final _apellido =
      TextEditingController(text: widget.existente?.lastName);
  late final _matricula =
      TextEditingController(text: widget.existente?.licenseNumber);

  late final Set<String> _especialidadesElegidas = {
    for (final e in widget.existente?.specialties ?? const <Etiqueta>[]) e.id,
  };
  late final Set<String> _sedesElegidas = {
    for (final b in widget.existente?.branches ?? const <Etiqueta>[]) b.id,
  };

  List<Especialidad>? _especialidades;
  List<Sucursal>? _sucursales;
  String? _errorCatalogo;

  bool _guardando = false;
  ApiError? _error;

  bool get _esEdicion => widget.existente != null;

  @override
  void initState() {
    super.initState();
    _cargarCatalogo();
  }

  Future<void> _cargarCatalogo() async {
    try {
      // En paralelo: son dos listas chicas e independientes, y encadenarlas
      // duplicaría la espera del formulario.
      final resultados = await Future.wait([
        listarEspecialidadesAdmin(widget.client),
        listarSucursales(widget.client),
      ]);
      if (!mounted) return;
      setState(() {
        _especialidades = resultados[0] as List<Especialidad>;
        _sucursales = resultados[1] as List<Sucursal>;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      // Se avisa en vez de dejar los chips vacíos sin explicación: la
      // auditoría encontró justo eso en el alta de organización, donde el
      // desplegable quedaba vacío y el error recién aparecía al enviar.
      setState(() => _errorCatalogo = error.message);
    }
  }

  @override
  void dispose() {
    _nombre.dispose();
    _apellido.dispose();
    _matricula.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    if (!(_formulario.currentState?.validate() ?? false)) return;
    if (_especialidadesElegidas.isEmpty) {
      _avisar('Elegí al menos una especialidad.');
      return;
    }
    if (_sedesElegidas.isEmpty) {
      _avisar('Elegí al menos una sede donde atiende.');
      return;
    }

    setState(() {
      _guardando = true;
      _error = null;
    });

    var salio = false;
    try {
      if (_esEdicion) {
        await editarProfesional(
          widget.client,
          widget.existente!.id,
          firstName: _nombre.text.trim(),
          lastName: _apellido.text.trim(),
          licenseNumber: _matricula.text.trim(),
          specialtyIds: _especialidadesElegidas.toList(),
          branchIds: _sedesElegidas.toList(),
        );
      } else {
        await crearProfesional(
          widget.client,
          firstName: _nombre.text.trim(),
          lastName: _apellido.text.trim(),
          licenseNumber: _matricula.text.trim(),
          specialtyIds: _especialidadesElegidas.toList(),
          branchIds: _sedesElegidas.toList(),
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
      _avisar('No se pudo guardar el profesional.');
    } finally {
      if (mounted && !salio) setState(() => _guardando = false);
    }
  }

  void _avisar(String mensaje) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(mensaje)));

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

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
                  _esEdicion ? 'Editar profesional' : 'Nuevo profesional',
                  style: theme.textTheme.titleLarge,
                ),
                const SizedBox(height: 16),

                TextFormField(
                  controller: _nombre,
                  decoration: const InputDecoration(
                    labelText: 'Nombres',
                    border: OutlineInputBorder(),
                  ),
                  validator: _obligatorio,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _apellido,
                  decoration: const InputDecoration(
                    labelText: 'Apellidos',
                    border: OutlineInputBorder(),
                  ),
                  validator: _obligatorio,
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _matricula,
                  decoration: const InputDecoration(
                    labelText: 'Matrícula',
                    border: OutlineInputBorder(),
                  ),
                  validator: _obligatorio,
                ),

                if (_errorCatalogo != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    _errorCatalogo!,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                ],

                const SizedBox(height: 20),
                _Seleccion(
                  titulo: 'Especialidades',
                  cargando: _especialidades == null && _errorCatalogo == null,
                  opciones: [
                    for (final e in _especialidades ?? const <Especialidad>[])
                      (id: e.id, nombre: e.name),
                  ],
                  elegidas: _especialidadesElegidas,
                  onAlternar: (id) => setState(() {
                    _especialidadesElegidas.contains(id)
                        ? _especialidadesElegidas.remove(id)
                        : _especialidadesElegidas.add(id);
                  }),
                ),

                const SizedBox(height: 16),
                _Seleccion(
                  titulo: 'Sedes donde atiende',
                  cargando: _sucursales == null && _errorCatalogo == null,
                  opciones: [
                    for (final s in _sucursales ?? const <Sucursal>[])
                      (id: s.id, nombre: s.name),
                  ],
                  elegidas: _sedesElegidas,
                  onAlternar: (id) => setState(() {
                    _sedesElegidas.contains(id)
                        ? _sedesElegidas.remove(id)
                        : _sedesElegidas.add(id);
                  }),
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
      ),
    );
  }

  static String? _obligatorio(String? valor) =>
      (valor ?? '').trim().isEmpty ? 'Este campo es obligatorio.' : null;
}

/// Un grupo de chips de selección múltiple.
class _Seleccion extends StatelessWidget {
  const _Seleccion({
    required this.titulo,
    required this.cargando,
    required this.opciones,
    required this.elegidas,
    required this.onAlternar,
  });

  final String titulo;
  final bool cargando;
  final List<({String id, String nombre})> opciones;
  final Set<String> elegidas;
  final void Function(String id) onAlternar;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(titulo, style: theme.textTheme.titleSmall),
        const SizedBox(height: 8),
        if (cargando)
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 8),
            child: LinearProgressIndicator(),
          )
        else if (opciones.isEmpty)
          Text(
            'No hay opciones cargadas todavía.',
            style: theme.textTheme.bodySmall,
          )
        else
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final opcion in opciones)
                FilterChip(
                  label: Text(opcion.nombre),
                  selected: elegidas.contains(opcion.id),
                  onSelected: (_) => onAlternar(opcion.id),
                ),
            ],
          ),
      ],
    );
  }
}
