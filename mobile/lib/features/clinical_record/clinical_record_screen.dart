/// US-25 — "Mi historia clínica": lo que escribieron los médicos, en una sola
/// línea de tiempo y de todas las sucursales.
///
/// No confundir con "Mis antecedentes" (US-08), que es lo que el paciente
/// **declara**. Esto es lo que el médico registró y firmó, y el paciente sólo
/// lo lee: no hay nada que editar acá.
///
/// Con el selector de US-07 arriba, igual que en antecedentes: el titular ve
/// también la historia de las personas a su cargo.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

import 'clinical_record_api.dart';

const _meses = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre',
];

String _fecha(DateTime? d) {
  if (d == null) return '—';
  final l = d.toLocal();
  return '${l.day} de ${_meses[l.month - 1]} de ${l.year}';
}

String _fechaHora(DateTime? d) {
  if (d == null) return '';
  final l = d.toLocal();
  String dos(int n) => n.toString().padLeft(2, '0');
  return '${_fecha(l)}, ${dos(l.hour)}:${dos(l.minute)}';
}

class ClinicalRecordScreen extends StatefulWidget {
  const ClinicalRecordScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<ClinicalRecordScreen> createState() => _ClinicalRecordScreenState();
}

class _ClinicalRecordScreenState extends State<ClinicalRecordScreen> {
  ApiClient? _client;
  PatientOption? _deQuien;
  HistoriaClinica? _historia;
  String? _error;
  bool _sinPersona = false;

  /// `null` = todas las sucursales.
  String? _sucursal;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  Future<void> _cargar() async {
    final paciente = _deQuien;
    if (paciente == null) return;
    try {
      final historia = await verHistoriaClinica(client, patientId: paciente.id);
      if (!mounted || _deQuien?.id != paciente.id) return;
      setState(() {
        _historia = historia;
        _error = null;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  void _cambiarPersona(PatientOption opcion) {
    if (_deQuien?.id == opcion.id) return;
    setState(() {
      _deQuien = opcion;
      _historia = null;
      _error = null;
      _sucursal = null;
    });
    _cargar();
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final historia = _historia;
    final atenciones = historia == null
        ? const <Atencion>[]
        : historia.atenciones
            .where((a) => _sucursal == null || a.branchName == _sucursal)
            .toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Mi historia clínica')),
      body: RefreshIndicator(
      onRefresh: _cargar,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
        children: [
          PatientSelector(
            label: '¿De quién es?',
            onChanged: _cambiarPersona,
            onSinSeleccion: () => setState(() => _sinPersona = true),
            client: widget.client,
          ),
          const SizedBox(height: 12),
          Text(
            'Lo que registraron y firmaron los médicos que te atendieron, de '
            'todas las sucursales. Para cambiar algo, habla con tu médico.',
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 16),
          if (_error != null)
            _Aviso(texto: _error!, onReintentar: _cargar)
          else if (_sinPersona && _deQuien == null)
            const SizedBox.shrink()
          else if (historia == null)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 32),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (historia.atenciones.isEmpty)
            const _Vacio()
          else ...[
            Text(
              '${historia.atenciones.length} '
              '${historia.atenciones.length == 1 ? 'atención firmada' : 'atenciones firmadas'}'
              ' en ${historia.sucursales.length} '
              '${historia.sucursales.length == 1 ? 'sucursal' : 'sucursales'}',
              style: theme.textTheme.titleSmall,
            ),
            // El filtro sólo tiene sentido si hay más de una sucursal.
            if (historia.sucursales.length > 1) ...[
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  ChoiceChip(
                    label: Text('Todas · ${historia.atenciones.length}'),
                    selected: _sucursal == null,
                    onSelected: (_) => setState(() => _sucursal = null),
                  ),
                  for (final MapEntry(key: nombre, value: n)
                      in historia.sucursales.entries)
                    ChoiceChip(
                      label: Text('$nombre · $n'),
                      selected: _sucursal == nombre,
                      onSelected: (_) => setState(() => _sucursal = nombre),
                    ),
                ],
              ),
            ],
            const SizedBox(height: 16),
            for (final (i, atencion) in atenciones.indexed)
              _EnLaLinea(
                ultima: i == atenciones.length - 1,
                child: _TarjetaAtencion(atencion: atencion),
              ),
          ],
        ],
      ),
      ),
    );
  }
}

/// Un punto de la línea de tiempo: la raya a la izquierda une las atenciones.
class _EnLaLinea extends StatelessWidget {
  const _EnLaLinea({required this.child, required this.ultima});

  final Widget child;
  final bool ultima;

  @override
  Widget build(BuildContext context) {
    final linea = Theme.of(context).colorScheme.outlineVariant;
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 20,
            child: Column(
              children: [
                const SizedBox(height: 20),
                Container(
                  width: 12,
                  height: 12,
                  decoration: const BoxDecoration(
                    color: Marca.primary,
                    shape: BoxShape.circle,
                  ),
                ),
                Expanded(
                  child: ultima
                      ? const SizedBox.shrink()
                      : Container(width: 2, color: linea),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}

class _TarjetaAtencion extends StatelessWidget {
  const _TarjetaAtencion({required this.atencion});

  final Atencion atencion;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final suave = theme.colorScheme.onSurfaceVariant;
    final secciones = [
      for (final (campo, etiqueta) in seccionesDeAtencion)
        if (atencion.secciones.containsKey(campo) ||
            atencion.enmiendas.any((e) => e.section == campo))
          (campo, etiqueta),
    ];

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(_fecha(atencion.startsAt), style: theme.textTheme.titleMedium),
            const SizedBox(height: 2),
            Text(
              '${atencion.practitionerName} · ${atencion.branchName}',
              style: theme.textTheme.bodySmall?.copyWith(color: suave),
            ),
            const SizedBox(height: 8),
            const Divider(height: 1),
            for (final (campo, etiqueta) in secciones) ...[
              const SizedBox(height: 12),
              Text(etiqueta, style: theme.textTheme.labelLarge),
              const SizedBox(height: 2),
              Text(atencion.secciones[campo] ?? '—',
                  style: theme.textTheme.bodyMedium),
              // Una enmienda no reemplaza lo firmado: se agrega debajo, con
              // quién y cuándo, y lo original sigue a la vista.
              for (final enmienda
                  in atencion.enmiendas.where((e) => e.section == campo))
                Container(
                  margin: const EdgeInsets.only(top: 8, left: 4),
                  padding: const EdgeInsets.only(left: 10),
                  decoration: const BoxDecoration(
                    border: Border(
                      left: BorderSide(color: Marca.primaryLight, width: 2),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Enmienda de ${enmienda.authorName} · '
                        '${_fechaHora(enmienda.createdAt)}',
                        style:
                            theme.textTheme.labelSmall?.copyWith(color: suave),
                      ),
                      Text(enmienda.text, style: theme.textTheme.bodyMedium),
                    ],
                  ),
                ),
            ],
            const SizedBox(height: 12),
            Text(
              'Firmada por ${atencion.signedByName} · '
              '${_fechaHora(atencion.signedAt)}',
              style: theme.textTheme.labelSmall?.copyWith(color: suave),
            ),
          ],
        ),
      ),
    );
  }
}

class _Vacio extends StatelessWidget {
  const _Vacio();

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        children: [
          Icon(Icons.history_edu_outlined,
              size: 40, color: theme.colorScheme.onSurfaceVariant),
          const SizedBox(height: 12),
          Text('Todavía no hay atenciones firmadas.',
              style: theme.textTheme.titleSmall, textAlign: TextAlign.center),
          const SizedBox(height: 4),
          Text(
            'Cuando un médico te atienda y firme la consulta, aparece acá.',
            style: theme.textTheme.bodySmall
                ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.texto, required this.onReintentar});

  final String texto;
  final Future<void> Function() onReintentar;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(texto, textAlign: TextAlign.center),
        const SizedBox(height: 8),
        TextButton(onPressed: onReintentar, child: const Text('Reintentar')),
      ],
    );
  }
}
