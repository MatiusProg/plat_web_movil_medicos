/// US-06 — Bitácora de auditoría.
///
/// Equivale a `frontend/src/paginas/Bitacora.tsx`, con el filtro por acción y
/// sin los de actor y fechas: en un teléfono tres filtros ocupan media
/// pantalla, y el de acción es el que responde la pregunta habitual —"quién
/// tocó los pacientes"—. Los otros dos quedan en la web.
///
/// La lista se pagina con el botón del final y no con scroll infinito: acá
/// interesa un rango acotado y saber cuántos asientos hay en total, no
/// deslizar sin fin.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'audit_api.dart';

class AuditScreen extends StatefulWidget {
  const AuditScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<AuditScreen> createState() => _AuditScreenState();
}

class _AuditScreenState extends State<AuditScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  List<AccionAuditable> _acciones = const [];
  String? _filtro;

  List<Asiento>? _asientos;
  int _total = 0;
  int _pagina = 1;
  bool _cargando = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_asientos == null && _error == null) _cargarTodo();
  }

  Future<void> _cargarTodo() async {
    await _cargarAcciones();
    await _cargar(reiniciar: true);
  }

  Future<void> _cargarAcciones() async {
    try {
      final acciones = await listarAcciones(client);
      if (!mounted) return;
      setState(() => _acciones = acciones);
    } on ApiError {
      // El filtro es una comodidad: si el catálogo no carga, la bitácora se
      // ve igual sin él. No vale la pena romper la pantalla por esto.
    }
  }

  Future<void> _cargar({required bool reiniciar}) async {
    if (reiniciar) {
      setState(() {
        _pagina = 1;
        _asientos = null;
        _error = null;
      });
    }
    setState(() => _cargando = true);

    try {
      final pagina = await listarBitacora(
        client,
        action: _filtro,
        page: _pagina,
      );
      if (!mounted) return;
      setState(() {
        _total = pagina.total;
        _asientos = [...(reiniciar ? const <Asiento>[] : _asientos ?? const []),
          ...pagina.asientos];
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _masAsientos() async {
    setState(() => _pagina += 1);
    await _cargar(reiniciar: false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final asientos = _asientos;
    final hayMas = asientos != null && asientos.length < _total;

    return Scaffold(
      appBar: AppBar(title: const Text('Bitácora')),
      drawer: const OrganizationDrawer(),
      body: RefreshIndicator(
        onRefresh: () => _cargar(reiniciar: true),
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          children: [
            Text(
              'Registro cronológico de las acciones sensibles de tu '
              'organización. Es de sólo lectura: no se edita ni se borra desde '
              'la aplicación.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 16),

            if (_acciones.isNotEmpty)
              DropdownButtonFormField<String?>(
                initialValue: _filtro,
                decoration: const InputDecoration(
                  labelText: 'Acción',
                  border: OutlineInputBorder(),
                ),
                items: [
                  const DropdownMenuItem<String?>(
                    value: null,
                    child: Text('Todas'),
                  ),
                  for (final accion in _acciones)
                    DropdownMenuItem<String?>(
                      value: accion.code,
                      child: Text(accion.label),
                    ),
                ],
                onChanged: (valor) {
                  setState(() => _filtro = valor);
                  _cargar(reiniciar: true);
                },
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
                    onPressed: () => _cargar(reiniciar: true),
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reintentar'),
                  ),
                ],
              )
            else if (asientos == null)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 48),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (asientos.isEmpty)
              const Padding(
                padding: EdgeInsets.symmetric(vertical: 32),
                child: Text(
                  'Todavía no hay asientos registrados con este filtro.',
                  textAlign: TextAlign.center,
                ),
              )
            else ...[
              Text(
                '$_total ${_total == 1 ? "asiento" : "asientos"}',
                style: theme.textTheme.labelLarge,
              ),
              const SizedBox(height: 8),
              for (final asiento in asientos) _TarjetaDeAsiento(asiento: asiento),
              if (hayMas)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: OutlinedButton(
                    onPressed: _cargando ? null : _masAsientos,
                    child: Text(_cargando ? 'Cargando…' : 'Ver más'),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _TarjetaDeAsiento extends StatelessWidget {
  const _TarjetaDeAsiento({required this.asiento});

  final Asiento asiento;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    asiento.actionLabel.isEmpty
                        ? asiento.action
                        : asiento.actionLabel,
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                Text(asiento.cuando, style: theme.textTheme.bodySmall),
              ],
            ),
            if (asiento.actor != null) ...[
              const SizedBox(height: 4),
              Text(
                '${asiento.actor!.fullName} · ${asiento.actor!.email}',
                style: theme.textTheme.bodySmall,
              ),
            ],
            if (asiento.detail.isNotEmpty) ...[
              const SizedBox(height: 8),
              for (final entrada in asiento.detail.entries)
                Text(
                  '${entrada.key}: ${entrada.value}',
                  style: theme.textTheme.bodySmall,
                ),
            ],
            const SizedBox(height: 8),
            Text(
              [
                asiento.entity,
                if (asiento.ipAddress.isNotEmpty) asiento.ipAddress,
                if (asiento.userAgent.isNotEmpty) asiento.userAgent,
              ].join(' · '),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
