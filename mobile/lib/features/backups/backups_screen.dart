/// Característica general 6 — Copias de seguridad en el teléfono.
///
/// Lo mismo que la pantalla `/respaldos` de la web, con una diferencia: acá
/// se restaura **desde el historial** (las copias automáticas que guarda el
/// servidor) y no desde un archivo. Ver el encabezado de `backups_api.dart`.
///
/// Tres bloques, de arriba hacia abajo:
///
/// 1. **Copia manual**: la regla del plan, cuándo es la próxima, y el botón.
///    La copia se guarda en Descargas.
/// 2. **Copias automáticas**: las que hace el sistema solo, cada cuánto y
///    cuántas conserva.
/// 3. **Historial**, con filtro Todas / Automáticas / Manuales. Las
///    automáticas que todavía se conservan se pueden descargar y restaurar.
///
/// Restaurar pide lo mismo que la web: ver primero qué trae la copia y
/// escribir el identificador de la organización. Reemplaza todos los datos.
library;

import 'dart:io';

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/theme/theme.dart';
import '../../core/widgets/organization_drawer.dart';
import 'backups_api.dart';

const _meses = [
  'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'sep', 'oct', 'nov', 'dic',
];

String _fechaHora(DateTime? d) {
  if (d == null) return '—';
  final l = d.toLocal();
  String dos(int n) => n.toString().padLeft(2, '0');
  return '${l.day} ${_meses[l.month - 1]} ${l.year}, ${dos(l.hour)}:${dos(l.minute)}';
}

String _tamano(int bytes) {
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  return '${(bytes / 1024 / 1024).toStringAsFixed(1)} MB';
}

enum _Filtro { todas, automaticas, manuales }

class BackupsScreen extends StatefulWidget {
  const BackupsScreen({super.key, this.client, this.guardado, this.puedeRestaurar});

  @visibleForTesting
  final ApiClient? client;

  /// Dónde se guardan las copias. En las pruebas, en memoria.
  @visibleForTesting
  final GuardadoDeArchivos? guardado;

  /// En las pruebas, sin sesión: si se muestra Restaurar.
  @visibleForTesting
  final bool? puedeRestaurar;

  @override
  State<BackupsScreen> createState() => _BackupsScreenState();
}

class _BackupsScreenState extends State<BackupsScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  late final GuardadoDeArchivos _guardado =
      widget.guardado ?? const GuardadoEnDescargas();

  PoliticaDeRespaldo? _politica;
  final List<RegistroDeRespaldo> _historial = [];
  bool _hayMas = false;
  int _pagina = 1;
  _Filtro _filtro = _Filtro.todas;

  bool _cargando = false;
  bool _trabajando = false;
  bool _iniciado = false;
  String? _error;

  bool get _puedeRestaurar =>
      widget.puedeRestaurar ??
      (SessionScope.of(context).user?.can('backups.backup.restore') ?? false);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_iniciado) {
      _iniciado = true;
      _cargar();
    }
  }

  Future<void> _cargar() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final regla = await verPolitica(client);
      final pagina = await verHistorial(client);
      if (!mounted) return;
      setState(() {
        _politica = regla;
        _historial
          ..clear()
          ..addAll(pagina.results);
        _hayMas = pagina.hayMas;
        _pagina = 1;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _cargarMas() async {
    setState(() => _cargando = true);
    try {
      final pagina = await verHistorial(client, page: _pagina + 1);
      if (!mounted) return;
      setState(() {
        _historial.addAll(pagina.results);
        _hayMas = pagina.hayMas;
        _pagina++;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _avisar(String texto) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(texto)));
  }

  Future<void> _guardar(Future<CopiaDescargada> Function() bajar) async {
    setState(() {
      _trabajando = true;
      _error = null;
    });
    try {
      final copia = await bajar();
      final ruta = await _guardado.guardar(copia.nombre, copia.bytes);
      if (!mounted) return;
      _avisar(
        'Copia guardada en $ruta. Guardala en un lugar seguro: trae todos '
        'los datos de la organización.',
      );
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } on FileSystemException catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _trabajando = false);
    }
    // La política y el historial cambian al generar: se vuelven a pedir.
    if (mounted) await _cargar();
  }

  Future<void> _generar() => _guardar(() => generarCopia(client));

  Future<void> _descargar(RegistroDeRespaldo registro) =>
      _guardar(() => descargarCopia(client, registro));

  Future<void> _restaurar(RegistroDeRespaldo registro) async {
    setState(() {
      _trabajando = true;
      _error = null;
    });
    InspeccionDeRespaldo? inspeccion;
    try {
      inspeccion = await inspeccionarCopia(client, registro.id);
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _trabajando = false);
    }
    if (inspeccion == null || !mounted) return;

    final confirmado = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _ConfirmarRestauracion(inspeccion: inspeccion!),
    );
    if (confirmado != true || !mounted) return;

    setState(() => _trabajando = true);
    try {
      await restaurarCopia(client, registro.id);
      if (!mounted) return;
      _avisar(
        'Datos restaurados al ${_fechaHora(inspeccion.generatedAt)}.',
      );
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _trabajando = false);
    }
    if (mounted) await _cargar();
  }

  List<RegistroDeRespaldo> get _filtrado => switch (_filtro) {
    _Filtro.todas => _historial,
    _Filtro.automaticas => _historial.where((r) => r.esAutomatica).toList(),
    _Filtro.manuales => _historial.where((r) => !r.esAutomatica).toList(),
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final politica = _politica;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Copias de seguridad'),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            icon: const Icon(Icons.refresh),
            onPressed: _cargando || _trabajando ? null : _cargar,
          ),
        ],
      ),
      drawer: const OrganizationDrawer(),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Una copia con todos los datos de tu organización, para '
              'guardarla fuera del sistema y poder restaurarla si algo sale mal.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 12),
            if (_trabajando || (_cargando && politica == null))
              const LinearProgressIndicator(),
            if (_error != null) ...[
              const SizedBox(height: 8),
              _Error(mensaje: _error!),
            ],
            if (politica != null) ...[
              const SizedBox(height: 8),
              _bloqueManual(theme, politica),
              const SizedBox(height: 12),
              _bloqueAutomaticas(theme, politica.automaticas),
            ],
            const SizedBox(height: 20),
            Text('Historial', style: theme.textTheme.titleMedium),
            const SizedBox(height: 8),
            SegmentedButton<_Filtro>(
              segments: const [
                ButtonSegment(value: _Filtro.todas, label: Text('Todas')),
                ButtonSegment(
                  value: _Filtro.automaticas,
                  label: Text('Automáticas'),
                ),
                ButtonSegment(value: _Filtro.manuales, label: Text('Manuales')),
              ],
              selected: {_filtro},
              onSelectionChanged: (s) => setState(() => _filtro = s.first),
            ),
            const SizedBox(height: 8),
            if (!_cargando && _filtrado.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16),
                child: Text(
                  'Todavía no hay copias en esta lista.',
                  style: theme.textTheme.bodyMedium,
                ),
              ),
            for (final registro in _filtrado) _fila(theme, registro),
            if (_hayMas)
              TextButton(
                onPressed: _cargando ? null : _cargarMas,
                child: const Text('Cargar más'),
              ),
          ],
        ),
      ),
    );
  }

  Widget _bloqueManual(ThemeData theme, PoliticaDeRespaldo politica) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Generar una copia', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(politica.description, style: theme.textTheme.bodyMedium),
            if (politica.lastBackupAt != null)
              Text(
                'Última copia manual: ${_fechaHora(politica.lastBackupAt)}.',
                style: theme.textTheme.bodySmall,
              ),
            if (!politica.allowedNow && politica.nextAvailableAt != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  'La próxima se puede generar desde el '
                  '${_fechaHora(politica.nextAvailableAt)}.',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: Marca.waiting,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: politica.allowedNow && !_trabajando ? _generar : null,
              icon: const Icon(Icons.download_outlined),
              label: const Text('Generar y guardar'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _bloqueAutomaticas(ThemeData theme, CopiasAutomaticas? auto) {
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.autorenew, color: Marca.primary),
                const SizedBox(width: 8),
                Text('Copias automáticas', style: theme.textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              auto?.description ??
                  'El sistema genera copias solo, según tu plan.',
              style: theme.textTheme.bodyMedium,
            ),
            if (auto != null && auto.enabled) ...[
              const SizedBox(height: 4),
              Text(
                auto.lastAt == null
                    ? 'Todavía no se generó ninguna: la primera sale en la '
                          'próxima hora.'
                    : 'Última: ${_fechaHora(auto.lastAt)}. '
                          'Próxima: ${_fechaHora(auto.nextAt)}.',
                style: theme.textTheme.bodySmall,
              ),
            ],
            if (_puedeRestaurar) ...[
              const SizedBox(height: 4),
              Text(
                'Para restaurar, elegí una copia automática del historial.',
                style: theme.textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _fila(ThemeData theme, RegistroDeRespaldo r) {
    final icono = !r.esCopia
        ? Icons.settings_backup_restore
        : r.esAutomatica
        ? Icons.autorenew
        : Icons.person_outline;
    final etiqueta = r.esCopia
        ? (r.esAutomatica ? 'Copia automática' : 'Copia manual')
        : r.kindLabel;
    final detalle = [
      _fechaHora(r.createdAt),
      if (r.totalRows > 0) '${r.totalRows} filas',
      if (r.esCopia && r.sizeBytes > 0) _tamano(r.sizeBytes),
      if (r.performedBy != null) r.performedBy!,
      if (r.esAutomatica && r.esCopia && !r.downloadable) 'ya no se conserva',
    ].join(' · ');

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ListTile(
            leading: CircleAvatar(
              backgroundColor: Marca.surfaceTint,
              child: Icon(icono, color: Marca.primary),
            ),
            title: Text(etiqueta),
            subtitle: Text(detalle),
          ),
          if (r.downloadable)
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
              child: Wrap(
                spacing: 8,
                children: [
                  TextButton.icon(
                    onPressed: _trabajando ? null : () => _descargar(r),
                    icon: const Icon(Icons.download_outlined),
                    label: const Text('Descargar'),
                  ),
                  if (_puedeRestaurar)
                    TextButton.icon(
                      onPressed: _trabajando ? null : () => _restaurar(r),
                      icon: const Icon(Icons.settings_backup_restore),
                      label: const Text('Restaurar'),
                      style: TextButton.styleFrom(
                        foregroundColor: Marca.danger,
                      ),
                    ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// El resumen de lo que trae la copia y la confirmación escribiendo el
/// identificador de la organización, como en la web.
class _ConfirmarRestauracion extends StatefulWidget {
  const _ConfirmarRestauracion({required this.inspeccion});

  final InspeccionDeRespaldo inspeccion;

  @override
  State<_ConfirmarRestauracion> createState() => _ConfirmarRestauracionState();
}

class _ConfirmarRestauracionState extends State<_ConfirmarRestauracion> {
  final _confirmacion = TextEditingController();

  @override
  void dispose() {
    _confirmacion.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final i = widget.inspeccion;
    final palabra = i.organizationSlug;
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Restaurar desde esta copia', style: theme.textTheme.titleLarge),
            const SizedBox(height: 4),
            Text(
              '${i.organizationName} · copia del ${_fechaHora(i.generatedAt)}',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 8),
            if (!i.belongsToMyOrganization)
              const _Error(
                mensaje: 'Esta copia es de otra organización: no se puede '
                    'restaurar acá.',
              )
            else ...[
              Text(
                'Reemplaza todos los datos de la organización por los de la '
                'copia. La historia clínica y los pagos no se borran: se '
                'agregan los que falten. La bitácora no se toca.',
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: 8),
              for (final e in i.conFilas)
                Text('${e.key}: ${e.value}', style: theme.textTheme.bodySmall),
              const SizedBox(height: 12),
              Text('Para confirmar, escribí «$palabra»'),
              const SizedBox(height: 4),
              TextField(
                key: const Key('confirmacion-restauracion'),
                controller: _confirmacion,
                autocorrect: false,
                onChanged: (_) => setState(() {}),
              ),
              const SizedBox(height: 12),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: Marca.danger),
                  onPressed: _confirmacion.text.trim() == palabra
                      ? () => Navigator.of(context).pop(true)
                      : null,
                  child: const Text('Restaurar y reemplazar los datos'),
                ),
              ),
            ],
            TextButton(
              onPressed: () => Navigator.of(context).pop(false),
              child: const Text('Cancelar'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Error extends StatelessWidget {
  const _Error({required this.mensaje});

  final String mensaje;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      color: theme.colorScheme.errorContainer,
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Text(
          mensaje,
          style: TextStyle(color: theme.colorScheme.onErrorContainer),
        ),
      ),
    );
  }
}
