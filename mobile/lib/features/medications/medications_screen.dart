/// US-49 — «Mis medicamentos»: los tratamientos en curso, la próxima toma y
/// el historial de tomadas y salteadas.
///
/// Con el selector de US-07 arriba, como en la historia clínica: el titular
/// maneja también los medicamentos de las personas a su cargo.
///
/// Al abrir, primero manda las tomas que quedaron pendientes en el teléfono
/// (marcadas desde el aviso sin conexión) y después pide la lista: así el
/// cumplimiento que se ve ya las incluye.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/features/dependents/dependents_api.dart';
import 'package:mobile/features/dependents/patient_selector.dart';

import 'medications_api.dart';
import 'recordarme.dart';
import 'recordatorios.dart';

class MedicationsScreen extends StatefulWidget {
  const MedicationsScreen({
    super.key,
    this.client,
    this.recordatorios,
    this.reloj,
  });

  @visibleForTesting
  final ApiClient? client;

  @visibleForTesting
  final Recordatorios? recordatorios;

  @visibleForTesting
  final DateTime Function()? reloj;

  @override
  State<MedicationsScreen> createState() => _MedicationsScreenState();
}

class _MedicationsScreenState extends State<MedicationsScreen> {
  ApiClient? _client;
  PatientOption? _deQuien;
  List<Tratamiento>? _tratamientos;
  String? _error;
  bool _sinPersona = false;
  final Set<String> _marcando = {};

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));
  Recordatorios get recordatorios =>
      widget.recordatorios ?? Recordatorios.instance;
  DateTime _ahora() => (widget.reloj ?? DateTime.now)();

  Future<void> _cargar() async {
    final paciente = _deQuien;
    if (paciente == null) return;
    await recordatorios.sincronizar(client);
    try {
      final lista = await verMisMedicamentos(client, patientId: paciente.id);
      if (!mounted || _deQuien?.id != paciente.id) return;
      setState(() {
        _tratamientos = lista;
        _error = null;
      });
    } on ApiError catch (error) {
      if (mounted) setState(() => _error = error.message);
    }
  }

  void _cambiarPersona(PatientOption opcion) {
    if (_deQuien?.id == opcion.id) return;
    setState(() {
      _deQuien = opcion;
      _tratamientos = null;
      _error = null;
    });
    _cargar();
  }

  Future<void> _marcar(Tratamiento t, int numero, {required bool tomada}) async {
    setState(() => _marcando.add(t.id));
    await recordatorios.marcar(t.id, numero, tomada: tomada);
    await _cargar();
    if (mounted) setState(() => _marcando.remove(t.id));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final lista = _tratamientos;

    return Scaffold(
      appBar: AppBar(title: const Text('Mis medicamentos')),
      body: RefreshIndicator(
        onRefresh: _cargar,
        child: ListenableBuilder(
          listenable: recordatorios,
          builder: (context, _) {
            final ahora = _ahora();
            final activos = recordatorios.activos;
            final enCurso = <Tratamiento>[];
            final otros = <Tratamiento>[];
            final sinHorario = <Tratamiento>[];
            for (final t in lista ?? const <Tratamiento>[]) {
              final activo = activos[t.id];
              if (t.horario == null) {
                sinHorario.add(t);
              } else if (activo != null && !activo.terminado(ahora)) {
                enCurso.add(t);
              } else {
                otros.add(t);
              }
            }
            return ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                PatientSelector(
                  label: '¿De quién son?',
                  onChanged: _cambiarPersona,
                  onSinSeleccion: () => setState(() => _sinPersona = true),
                  client: widget.client,
                ),
                const SizedBox(height: 12),
                Text(
                  'Activa «Recordarme» y la app te avisa a cada hora, aunque no '
                  'tengas conexión. Lo que marques como tomado lo ve tu médico.',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
                ),
                if (recordatorios.pendientes.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${recordatorios.pendientes.length} '
                    '${recordatorios.pendientes.length == 1 ? 'toma marcada espera' : 'tomas marcadas esperan'}'
                    ' conexión para enviarse.',
                    style: theme.textTheme.labelSmall
                        ?.copyWith(color: theme.colorScheme.tertiary),
                  ),
                ],
                const SizedBox(height: 16),
                if (_error != null)
                  Column(children: [
                    Text(_error!, textAlign: TextAlign.center),
                    TextButton(
                        onPressed: _cargar, child: const Text('Reintentar')),
                  ])
                else if (_sinPersona && _deQuien == null)
                  const SizedBox.shrink()
                else if (lista == null)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 32),
                    child: Center(child: CircularProgressIndicator()),
                  )
                else if (lista.isEmpty)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 32),
                    child: Text(
                      'No hay medicamentos recetados en los últimos meses. '
                      'Cuando un médico firme una receta, aparece acá.',
                      textAlign: TextAlign.center,
                      style: theme.textTheme.bodyMedium,
                    ),
                  )
                else ...[
                  if (enCurso.isNotEmpty) ...[
                    Text('En curso', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    for (final t in enCurso)
                      _TarjetaEnCurso(
                        tratamiento: t,
                        activo: activos[t.id]!,
                        pendientes: recordatorios.pendientes,
                        ahora: ahora,
                        ocupado: _marcando.contains(t.id),
                        onMarcar: (n, tomada) => _marcar(t, n, tomada: tomada),
                        interruptor: _interruptor(t),
                      ),
                    const SizedBox(height: 16),
                  ],
                  if (otros.isNotEmpty) ...[
                    Text('Recetados', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    for (final t in otros)
                      _TarjetaSimple(tratamiento: t, pie: _interruptor(t)),
                    const SizedBox(height: 16),
                  ],
                  if (sinHorario.isNotEmpty) ...[
                    Text('Sin horario fijo', style: theme.textTheme.titleMedium),
                    const SizedBox(height: 8),
                    for (final t in sinHorario)
                      _TarjetaSimple(tratamiento: t, pie: _interruptor(t)),
                  ],
                ],
              ],
            );
          },
        ),
      ),
    );
  }

  Widget _interruptor(Tratamiento t) => InterruptorRecordatorio(
        recordatorios: recordatorios,
        itemId: t.id,
        patientId: _deQuien?.id ?? '',
        medicamento: t.medicamento,
        dosis: t.dosis,
        horario: t.horario,
        motivoSinHorario: t.motivoSinHorario,
        reloj: widget.reloj,
      );
}

class _TarjetaSimple extends StatelessWidget {
  const _TarjetaSimple({required this.tratamiento, required this.pie});

  final Tratamiento tratamiento;
  final Widget pie;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final t = tratamiento;
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(t.medicamento, style: theme.textTheme.titleSmall),
            Text('${t.dosis} · ${t.frecuencia} · ${t.duracion}',
                style: theme.textTheme.bodySmall),
            if (t.indicaciones.isNotEmpty)
              Text(t.indicaciones, style: theme.textTheme.bodySmall),
            Text('Recetado por ${t.medico}',
                style: theme.textTheme.labelSmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            pie,
          ],
        ),
      ),
    );
  }
}

class _TarjetaEnCurso extends StatelessWidget {
  const _TarjetaEnCurso({
    required this.tratamiento,
    required this.activo,
    required this.pendientes,
    required this.ahora,
    required this.ocupado,
    required this.onMarcar,
    required this.interruptor,
  });

  final Tratamiento tratamiento;
  final RecordatorioActivo activo;
  final List<TomaPendiente> pendientes;
  final DateTime ahora;
  final bool ocupado;
  final void Function(int numero, bool tomada) onMarcar;
  final Widget interruptor;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final suave = theme.colorScheme.onSurfaceVariant;
    final t = tratamiento;
    final horario = activo.horario;

    // Lo que dijo el servidor, más lo marcado acá que todavía no llegó.
    final marcadas = <int, bool>{
      for (final toma in t.tomas) toma.numero: toma.tomada,
      for (final p in pendientes.where((p) => p.itemId == t.id))
        p.numero: p.tomada,
    };
    final tomadas = marcadas.values.where((v) => v).length;
    final salteadas = marcadas.length - tomadas;
    final dia = activo.diaDelTratamiento(ahora);
    final proxima = activo.proximaToma(ahora);
    final toca = activo.tomaQueToca(ahora);
    final porMarcar = toca != null && !marcadas.containsKey(toca) ? toca : null;

    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(t.medicamento, style: theme.textTheme.titleSmall),
            Text(t.dosis, style: theme.textTheme.bodySmall),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(
                child: LinearProgressIndicator(
                  value: dia / (horario.dias < 1 ? 1 : horario.dias),
                  minHeight: 6,
                  borderRadius: BorderRadius.circular(3),
                  semanticsLabel: 'Día $dia de ${horario.dias}',
                ),
              ),
              const SizedBox(width: 8),
              Text('Día $dia de ${horario.dias}',
                  style: theme.textTheme.labelSmall),
            ]),
            const SizedBox(height: 6),
            Text(
              proxima == null
                  ? 'No quedan tomas por avisar.'
                  : 'Próxima toma: ${cuandoEnTexto(activo.momentoDe(proxima), ahora)}',
              style: theme.textTheme.bodyMedium,
            ),
            Text(
              '$tomadas de ${horario.totalTomas} tomas'
              '${salteadas > 0 ? ' · $salteadas salteadas' : ''}',
              style: theme.textTheme.labelSmall?.copyWith(color: suave),
            ),
            if (porMarcar != null) ...[
              const SizedBox(height: 8),
              Text(
                'Toma de las ${cuandoEnTexto(activo.momentoDe(porMarcar), ahora)}',
                style: theme.textTheme.labelLarge,
              ),
              const SizedBox(height: 4),
              Wrap(spacing: 8, children: [
                FilledButton.icon(
                  onPressed: ocupado ? null : () => onMarcar(porMarcar, true),
                  icon: const Icon(Icons.check, size: 18),
                  label: const Text('Tomada'),
                ),
                OutlinedButton(
                  onPressed: ocupado ? null : () => onMarcar(porMarcar, false),
                  child: const Text('No la tomé'),
                ),
              ]),
            ],
            if (marcadas.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text('Historial', style: theme.textTheme.labelLarge),
              const SizedBox(height: 4),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final MapEntry(key: n, value: tomada)
                      in (marcadas.entries.toList()
                        ..sort((a, b) => b.key.compareTo(a.key))))
                    Chip(
                      visualDensity: VisualDensity.compact,
                      avatar: Icon(tomada ? Icons.check_circle : Icons.cancel,
                          size: 16,
                          color: tomada
                              ? theme.colorScheme.primary
                              : theme.colorScheme.error),
                      label: Text(
                          '${cuandoEnTexto(activo.momentoDe(n), ahora)} · '
                          '${tomada ? 'tomada' : 'salteada'}'),
                    ),
                ],
              ),
            ],
            interruptor,
          ],
        ),
      ),
    );
  }
}
