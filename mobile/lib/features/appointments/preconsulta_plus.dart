/// US-51: experiencia posterior a la compra. Sin cobro adicional.
library;

import 'package:flutter/material.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'appointments_api.dart';

class PreconsultaPlusSheet extends StatefulWidget {
  const PreconsultaPlusSheet({super.key, required this.client, required this.ficha});
  final ApiClient client;
  final Appointment ficha;

  @override
  State<PreconsultaPlusSheet> createState() => _PreconsultaPlusSheetState();
}

class _PreconsultaPlusSheetState extends State<PreconsultaPlusSheet> {
  final _reason = TextEditingController();
  final _questions = TextEditingController();
  bool _loading = true;
  bool _saving = false;
  String? _message;

  String get _path => '/appointments/appointments/${widget.ficha.id}/preconsultation/';
  bool get _editable => widget.ficha.isConfirmed && widget.ficha.startsAt.isAfter(DateTime.now());

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
      if (mounted) setState(() => _message = 'Preconsulta guardada.');
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
              const SizedBox(height: 16),
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
                        'Antes de asistir lleva tu identificación y revisa las '
                        'indicaciones de tu centro. No suspendas medicamentos '
                        'sin consejo médico.',
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
                    'Cuéntale a tu médico el motivo y lo que quieres preguntarle. '
                        'Lo lee antes de atenderte.',
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
                    color: _message == 'Preconsulta guardada.'
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
