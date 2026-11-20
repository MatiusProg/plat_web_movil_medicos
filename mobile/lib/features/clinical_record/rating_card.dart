/// US-48 — «¿Cómo te atendieron?»: las estrellas debajo de cada atención
/// firmada en *Mi historia clínica*.
///
/// Sin calificar: cinco estrellas grandes que se tocan y un comentario
/// opcional. Ya calificada: «Calificaste con ★★★★☆» y «Cambiar» mientras
/// queden días. Las reglas (1 a 5, 500 caracteres, 7 días) las vuelve a
/// revisar el backend.
library;

import 'package:flutter/material.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';

import 'clinical_record_api.dart';

const _etiquetas = ['Muy mala', 'Mala', 'Regular', 'Buena', 'Muy buena'];
const _ambar = Color(0xFFF59E0B);

const _meses = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre',
];

/// ★★★★☆, para leer de un vistazo.
String estrellasEnTexto(int n) => '★' * n + '☆' * (5 - n);

class TarjetaCalificacion extends StatefulWidget {
  const TarjetaCalificacion({
    super.key,
    required this.client,
    required this.encounterId,
    required this.inicial,
  });

  final ApiClient client;
  final String encounterId;
  final Calificacion? inicial;

  @override
  State<TarjetaCalificacion> createState() => _TarjetaCalificacionState();
}

class _TarjetaCalificacionState extends State<TarjetaCalificacion> {
  late Calificacion? _guardada = widget.inicial;
  late bool _editando = widget.inicial == null;
  late int _estrellas = widget.inicial?.estrellas ?? 0;
  late final _comentario =
      TextEditingController(text: widget.inicial?.comentario ?? '');
  bool _enviando = false;
  String? _error;

  @override
  void dispose() {
    _comentario.dispose();
    super.dispose();
  }

  Future<void> _enviar() async {
    if (_estrellas == 0) return;
    setState(() {
      _enviando = true;
      _error = null;
    });
    try {
      final guardada = await calificarAtencion(
        widget.client,
        encounterId: widget.encounterId,
        primera: _guardada == null,
        estrellas: _estrellas,
        comentario: _comentario.text.trim(),
      );
      if (!mounted) return;
      setState(() {
        _guardada = guardada;
        _editando = false;
      });
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final suave = theme.colorScheme.onSurfaceVariant;
    final guardada = _guardada;

    if (guardada != null && !_editando) {
      final hasta = guardada.editableHasta?.toLocal();
      return Container(
        width: double.infinity,
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text.rich(
              TextSpan(children: [
                const TextSpan(text: 'Calificaste con '),
                TextSpan(
                  text: estrellasEnTexto(guardada.estrellas),
                  style: const TextStyle(color: _ambar),
                ),
              ]),
              semanticsLabel:
                  'Calificaste con ${guardada.estrellas} de 5 estrellas',
              style: theme.textTheme.bodyMedium,
            ),
            if (guardada.comentario.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text('«${guardada.comentario}»',
                  style: theme.textTheme.bodySmall?.copyWith(color: suave)),
            ],
            if (guardada.editable)
              TextButton(
                style: TextButton.styleFrom(padding: EdgeInsets.zero),
                onPressed: () => setState(() {
                  _estrellas = guardada.estrellas;
                  _comentario.text = guardada.comentario;
                  _editando = true;
                }),
                child: Text(hasta == null
                    ? 'Cambiar'
                    : 'Cambiar (hasta el ${hasta.day} de '
                        '${_meses[hasta.month - 1]})'),
              )
            else
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text('Ya no se puede cambiar.',
                    style: theme.textTheme.labelSmall?.copyWith(color: suave)),
              ),
          ],
        ),
      );
    }

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('¿Cómo te atendieron?', style: theme.textTheme.titleSmall),
          const SizedBox(height: 4),
          Row(
            children: [
              for (var n = 1; n <= 5; n++)
                Semantics(
                  label: '$n ${n == 1 ? 'estrella' : 'estrellas'}: '
                      '${_etiquetas[n - 1]}',
                  selected: _estrellas == n,
                  button: true,
                  child: InkResponse(
                    radius: 24,
                    onTap: _enviando
                        ? null
                        : () => setState(() => _estrellas = n),
                    child: Padding(
                      padding: const EdgeInsets.all(4),
                      child: Icon(
                        n <= _estrellas
                            ? Icons.star_rounded
                            : Icons.star_outline_rounded,
                        size: 40,
                        color: n <= _estrellas ? _ambar : suave,
                      ),
                    ),
                  ),
                ),
            ],
          ),
          if (_estrellas > 0) ...[
            Text(_etiquetas[_estrellas - 1],
                style: theme.textTheme.bodySmall?.copyWith(color: suave)),
            const SizedBox(height: 8),
            TextField(
              controller: _comentario,
              maxLength: maxComentarioCalificacion,
              maxLines: 3,
              minLines: 2,
              decoration: const InputDecoration(
                labelText: 'Comentario (opcional)',
                hintText: '¿Qué te gustó o qué se puede mejorar?',
              ),
            ),
            Text(
              'Tu médico ve su promedio, pero no quién lo calificó. '
              'Puedes cambiarla durante 7 días.',
              style: theme.textTheme.labelSmall?.copyWith(color: suave),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 8),
            Text(_error!,
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.error)),
          ],
          const SizedBox(height: 8),
          Row(
            children: [
              FilledButton(
                onPressed: _estrellas == 0 || _enviando ? null : _enviar,
                child: Text(_enviando
                    ? 'Guardando…'
                    : guardada == null
                        ? 'Enviar calificación'
                        : 'Guardar cambio'),
              ),
              if (guardada != null) ...[
                const SizedBox(width: 8),
                TextButton(
                  onPressed: _enviando
                      ? null
                      : () => setState(() => _editando = false),
                  child: const Text('Cancelar'),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}
