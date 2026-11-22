/// US-51 — «Tu ficha, más que un comprobante».
///
/// Lo que el paciente necesita para ir, que el sistema ya sabe: agregarla al
/// calendario (el `.ics` del backend, con la hora de La Paz y un aviso un día
/// antes), cómo llegar (el mapa de la sede), cómo prepararse y cuánto falta.
/// Más la preconsulta, que el médico ve al abrir la atención. Sin cobro extra.
library;

import 'package:flutter/material.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/files/archivos.dart';
import 'package:url_launcher/url_launcher.dart';
import 'appointments_api.dart';

/// «Es hoy a las 10:00», «Es mañana a las 10:00», «Faltan 3 días»… o `null`
/// si el turno ya pasó.
String? cuentaRegresiva(DateTime inicio, DateTime ahora) {
  if (!inicio.isAfter(ahora)) return null;
  String dos(int n) => n.toString().padLeft(2, '0');
  final hora = '${dos(inicio.hour)}:${dos(inicio.minute)}';
  final dias = DateTime(inicio.year, inicio.month, inicio.day)
      .difference(DateTime(ahora.year, ahora.month, ahora.day))
      .inDays;
  if (dias == 0) return 'Es hoy a las $hora';
  if (dias == 1) return 'Es mañana a las $hora';
  return 'Faltan $dias días';
}

Future<bool> _abrirFuera(Uri url) =>
    launchUrl(url, mode: LaunchMode.externalApplication);

class PreconsultaPlusSheet extends StatefulWidget {
  const PreconsultaPlusSheet({
    super.key,
    required this.client,
    required this.ficha,
    this.openUrl,
    this.guardado,
    this.abridor,
    this.ahora,
  });
  final ApiClient client;
  final Appointment ficha;

  /// Se inyectan en las pruebas.
  final Future<bool> Function(Uri url)? openUrl;
  final GuardadoDeArchivos? guardado;
  final AbridorDeArchivos? abridor;
  final DateTime? ahora;

  @override
  State<PreconsultaPlusSheet> createState() => _PreconsultaPlusSheetState();
}

const _guardada = 'Preconsulta guardada: tu médico la verá al atenderte.';

class _PreconsultaPlusSheetState extends State<PreconsultaPlusSheet> {
  final _reason = TextEditingController();
  final _questions = TextEditingController();
  bool _loading = true;
  bool _saving = false;
  String? _message;

  bool _bajandoCalendario = false;

  String get _path => '/appointments/appointments/${widget.ficha.id}/preconsultation/';
  DateTime get _ahora => widget.ahora ?? DateTime.now();
  bool get _editable => widget.ficha.isConfirmed && widget.ficha.startsAt.isAfter(_ahora);

  /// El `.ics` se guarda en Descargas y se abre: el teléfono ofrece
  /// agregarlo a su calendario.
  Future<void> _calendario() async {
    setState(() => _bajandoCalendario = true);
    try {
      final archivo = await widget.client.download(
        'GET', '/appointments/appointments/${widget.ficha.id}/calendar.ics');
      final ruta = await (widget.guardado ?? GuardadoEnDescargas())
          .guardar(archivo.nombre ?? 'ficha.ics', archivo.bytes);
      final problema = await (widget.abridor ?? AbridorDelSistema()).abrir(ruta);
      if (mounted && problema != null) setState(() => _message = problema);
    } on ApiError catch (e) {
      if (mounted) setState(() => _message = e.message);
    } catch (_) {
      if (mounted) setState(() => _message = 'No se pudo guardar el archivo del calendario.');
    } finally {
      if (mounted) setState(() => _bajandoCalendario = false);
    }
  }

  Future<void> _comoLlegar() async {
    final url = widget.ficha.branchMapsUrl;
    if (url == null) return;
    final abierto = await (widget.openUrl ?? _abrirFuera)(Uri.parse(url));
    if (!abierto && mounted) {
      setState(() => _message = 'No se pudo abrir el mapa.');
    }
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = await widget.client.get(_path) as Map<String, dynamic>;
      if (!mounted) return;
      _reason.text = data['reason'] as String? ?? '';
      _questions.text = data['questions'] as String? ?? '';
    } on ApiError catch (e) {
      if (mounted) setState(() => _message = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _save() async {
    setState(() { _saving = true; _message = null; });
    try {
      await widget.client.put(_path, body: {
        'reason': _reason.text.trim(), 'questions': _questions.text.trim(),
      });
      if (mounted) setState(() => _message = _guardada);
    } on ApiError catch (e) {
      if (mounted) setState(() => _message = e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  void dispose() {
    _reason.dispose(); _questions.dispose(); super.dispose();
  }

  /// Por qué no se puede editar, o `null` si se puede.
  String? get _porQueNo {
    if (_editable) return null;
    if (!widget.ficha.isConfirmed) {
      return 'La preconsulta se completa antes del turno: esta ficha ya no está pendiente.';
    }
    return 'El turno ya empezó: la preconsulta se podía completar hasta ese momento.';
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final suave = theme.textTheme.bodyMedium
        ?.copyWith(color: theme.colorScheme.onSurfaceVariant);
    final porQueNo = _porQueNo;
    final falta = widget.ficha.isConfirmed
        ? cuentaRegresiva(widget.ficha.startsAt, _ahora)
        : null;
    final anotado = _reason.text.isNotEmpty || _questions.text.isNotEmpty;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
            24, 8, 24, MediaQuery.viewInsetsOf(context).bottom + 20),
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text('Tu ficha, más que un comprobante',
                  style: theme.textTheme.titleLarge),
              const SizedBox(height: 4),
              Text('${widget.ficha.practitionerName} · ${widget.ficha.branchName}',
                  style: suave),
              if (falta != null) ...[
                const SizedBox(height: 16),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Text(
                    '$falta para tu ficha con ${widget.ficha.practitionerName}',
                    textAlign: TextAlign.center,
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
              ],
              if (_editable) ...[
                const SizedBox(height: 12),
                _Tarjeta(
                  icono: Icons.event_available_outlined,
                  titulo: 'Agregar a mi calendario',
                  texto: 'Con un aviso un día antes.',
                  accion: _bajandoCalendario ? 'Guardando…' : 'Agregar',
                  onTap: _bajandoCalendario ? null : _calendario,
                ),
              ],
              if (widget.ficha.branchMapsUrl != null) ...[
                const SizedBox(height: 12),
                _Tarjeta(
                  icono: Icons.directions_outlined,
                  titulo: 'Cómo llegar',
                  texto: widget.ficha.branchAddress.isEmpty
                      ? widget.ficha.branchName
                      : widget.ficha.branchAddress,
                  accion: 'Abrir el mapa',
                  onTap: _comoLlegar,
                ),
              ],
              const SizedBox(height: 16),
              Text('Cómo prepararte', style: theme.textTheme.titleMedium),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: theme.colorScheme.primaryContainer.withValues(alpha: 0.35),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(Icons.badge_outlined, color: theme.colorScheme.primary),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'Llega 10 minutos antes con tu identificación y el '
                        'comprobante con QR. Trae tus recetas y estudios '
                        'anteriores. No suspendas medicamentos sin consejo médico.',
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              Text('Preconsulta opcional', style: theme.textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                porQueNo ??
                    'Cuéntale a tu médico el motivo y lo que quieres '
                        'preguntarle: lo ve al abrir tu atención.',
                style: suave,
              ),
              const SizedBox(height: 12),
              if (_loading)
                const Center(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: CircularProgressIndicator(),
                  ),
                )
              else if (porQueNo != null) ...[
                // Ya no se edita: se muestra lo anotado, sin campos vacíos.
                if (!anotado)
                  Text('No anotaste una preconsulta para esta ficha.', style: suave)
                else ...[
                  if (_reason.text.isNotEmpty) _Anotado('Motivo de consulta', _reason.text),
                  if (_questions.text.isNotEmpty)
                    _Anotado('Preguntas para el médico', _questions.text),
                ],
              ] else ...[
                TextField(
                  controller: _reason,
                  maxLength: 1200,
                  minLines: 2,
                  maxLines: 4,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: const InputDecoration(
                    labelText: 'Motivo de consulta',
                    hintText: 'Ej.: dolor de cabeza desde hace una semana',
                  ),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: _questions,
                  maxLength: 1200,
                  minLines: 2,
                  maxLines: 4,
                  textCapitalization: TextCapitalization.sentences,
                  decoration: const InputDecoration(
                    labelText: 'Preguntas para el médico',
                    hintText: 'Ej.: ¿puedo seguir tomando ibuprofeno?',
                  ),
                ),
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _saving ? null : _save,
                  icon: const Icon(Icons.save_outlined),
                  label: Text(_saving ? 'Guardando…' : 'Guardar preconsulta'),
                ),
              ],
              if (_message != null) ...[
                const SizedBox(height: 12),
                Text(
                  _message!,
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: _message == _guardada
                        ? theme.colorScheme.primary
                        : theme.colorScheme.error,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
              const SizedBox(height: 16),
              Text('Esta información no sustituye una evaluación médica.',
                  style: theme.textTheme.bodySmall
                      ?.copyWith(color: theme.colorScheme.onSurfaceVariant)),
            ],
          ),
        ),
      ),
    );
  }
}

class _Anotado extends StatelessWidget {
  const _Anotado(this.titulo, this.texto);
  final String titulo;
  final String texto;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(titulo, style: theme.textTheme.labelLarge),
          const SizedBox(height: 2),
          Text(texto, style: theme.textTheme.bodyLarge),
        ],
      ),
    );
  }
}

class _Tarjeta extends StatelessWidget {
  const _Tarjeta({
    required this.icono,
    required this.titulo,
    required this.texto,
    required this.accion,
    required this.onTap,
  });

  final IconData icono;
  final String titulo;
  final String texto;
  final String accion;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 12, 12),
        child: Row(
          children: [
            Icon(icono, color: theme.colorScheme.primary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(titulo, style: theme.textTheme.titleSmall),
                  Text(
                    texto,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            TextButton(onPressed: onTap, child: Text(accion)),
          ],
        ),
      ),
    );
  }
}
