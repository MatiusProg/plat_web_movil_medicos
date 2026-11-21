/// US-51: experiencia posterior a la compra. Sin cobro adicional.
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

  @override
  Widget build(BuildContext context) => SafeArea(child: Padding(
    padding: EdgeInsets.fromLTRB(20, 12, 20, MediaQuery.of(context).viewInsets.bottom + 20),
    child: SingleChildScrollView(child: Column(
      mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Tu ficha, más que un comprobante', style: Theme.of(context).textTheme.titleLarge),
        const SizedBox(height: 8),
        Text('${widget.ficha.practitionerName} · ${widget.ficha.branchName}'),
        const SizedBox(height: 12),
        const Text('Antes de asistir lleva tu identificación y revisa las indicaciones oficiales de tu centro. No suspendas medicamentos sin consejo médico.'),
        const SizedBox(height: 16),
        const Text('Preconsulta opcional', style: TextStyle(fontWeight: FontWeight.bold)),
        if (_loading) const CircularProgressIndicator() else ...[
          TextField(controller: _reason, enabled: _editable, maxLength: 1200,
            maxLines: 3, decoration: const InputDecoration(labelText: 'Motivo de consulta')),
          TextField(controller: _questions, enabled: _editable, maxLength: 1200,
            maxLines: 3, decoration: const InputDecoration(labelText: 'Preguntas para el médico')),
          if (_editable) FilledButton(onPressed: _saving ? null : _save,
            child: Text(_saving ? 'Guardando…' : 'Guardar preconsulta')),
        ],
        if (_message != null) Text(_message!),
        const SizedBox(height: 8),
        const Text('Esta información no sustituye una evaluación médica.', style: TextStyle(fontSize: 12)),
      ],
    )),
  ));
}
