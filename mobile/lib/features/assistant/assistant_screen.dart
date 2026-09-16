/// La conversación con el asistente de orientación (US-31 / US-34).
///
/// Tres reglas que la pantalla hace cumplir aunque el backend falle:
///
///   1. **Si no hay respuesta, no se inventa una.** Error, servidor caído o sin
///      red: se dice "no puedo responder ahora" y se ofrece reintentar.
///   2. **Una urgencia corta el camino a la reserva.** Con `emergency` no se
///      ofrece buscar profesionales: se deriva a emergencias (US-34).
///   3. **La sugerencia viaja con sus fragmentos.** Son los que muestran en qué
///      se basó el asistente.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';

import 'assistant_api.dart';

class AssistantScreen extends StatefulWidget {
  const AssistantScreen({
    super.key,
    this.client,
    this.demo = assistantDemoMode,
  });

  @visibleForTesting
  final ApiClient? client;

  final bool demo;

  @override
  State<AssistantScreen> createState() => _AssistantScreenState();
}

/// Un turno de la conversación: lo que escribió el paciente, o lo que contestó
/// el asistente, o el aviso de que no pudo contestar.
class _Turno {
  const _Turno.paciente(this.texto) : respuesta = null, error = null;
  const _Turno.asistente(AssistantReply this.respuesta)
    : texto = '',
      error = null;
  const _Turno.error(String this.error, this.texto) : respuesta = null;

  /// En un turno de error, el mensaje que hay que reintentar.
  final String texto;
  final AssistantReply? respuesta;
  final String? error;

  bool get esPaciente => respuesta == null && error == null;
}

class _AssistantScreenState extends State<AssistantScreen> {
  ApiClient? _client;
  final _entrada = TextEditingController();
  final _scroll = ScrollController();
  final List<_Turno> _turnos = [];
  bool _esperando = false;

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void dispose() {
    _entrada.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _enviar([String? reintento]) async {
    final mensaje = (reintento ?? _entrada.text).trim();
    if (mensaje.isEmpty || _esperando) return;

    setState(() {
      if (reintento == null) {
        _turnos.add(_Turno.paciente(mensaje));
        _entrada.clear();
      } else {
        _turnos.removeWhere((t) => t.error != null && t.texto == mensaje);
      }
      _esperando = true;
    });
    _bajar();

    _Turno turno;
    try {
      final respuesta = await consultarAsistente(
        client,
        mensaje,
        demo: widget.demo,
      );
      turno = _Turno.asistente(respuesta);
    } on ApiError catch (error) {
      turno = _Turno.error(_motivo(error), mensaje);
    } catch (_) {
      turno = _Turno.error(
        'El servidor respondió algo que no se pudo interpretar.',
        mensaje,
      );
    }

    if (!mounted) return;
    setState(() {
      _turnos.add(turno);
      _esperando = false;
    });
    _bajar();
  }

  String _motivo(ApiError error) {
    if (error.isOffline) return 'No hay conexión con el servidor.';
    if (error.status == 404) {
      return 'El asistente todavía no está disponible en este servidor.';
    }
    if (error.status >= 500) return 'El asistente no está disponible.';
    return error.message;
  }

  void _bajar() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scroll.hasClients) return;
      _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Asistente de orientación')),
      body: Column(
        children: [
          _Aviso(demo: widget.demo),
          Expanded(
            child: _turnos.isEmpty && !_esperando
                ? const _Bienvenida()
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(16),
                    itemCount: _turnos.length + (_esperando ? 1 : 0),
                    itemBuilder: (context, i) {
                      if (i == _turnos.length) return const _Pensando();
                      final turno = _turnos[i];
                      if (turno.esPaciente) {
                        return _BurbujaPaciente(texto: turno.texto);
                      }
                      if (turno.error != null) {
                        return _BurbujaError(
                          motivo: turno.error!,
                          onReintentar: _esperando
                              ? null
                              : () => _enviar(turno.texto),
                        );
                      }
                      return _BurbujaAsistente(respuesta: turno.respuesta!);
                    },
                  ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _entrada,
                      enabled: !_esperando,
                      minLines: 1,
                      maxLines: 4,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _enviar(),
                      decoration: const InputDecoration(
                        hintText: 'Contá qué síntomas tenés…',
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  IconButton.filled(
                    tooltip: 'Enviar',
                    onPressed: _esperando ? null : _enviar,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.demo});

  final bool demo;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      color: Marca.surfaceTint,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      child: Text(
        demo
            ? 'MODO EJEMPLO: las respuestas son fijas, no vienen del servidor.'
            : 'Te orienta sobre qué especialidad consultar. No reemplaza '
                  'la consulta médica.',
        style: TextStyle(
          color: demo ? Marca.waiting : Marca.ink500,
          fontWeight: demo ? FontWeight.w600 : FontWeight.normal,
          fontSize: 13,
        ),
      ),
    );
  }
}

class _Bienvenida extends StatelessWidget {
  const _Bienvenida();

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Padding(
        padding: EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.forum_outlined, size: 48, color: Marca.primary),
            SizedBox(height: 12),
            Text(
              'Describí tus síntomas y te sugiero con qué especialidad '
              'consultar.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _Burbuja extends StatelessWidget {
  const _Burbuja({
    required this.child,
    required this.color,
    this.derecha = false,
  });

  final Widget child;
  final Color color;
  final bool derecha;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: derecha ? Alignment.centerRight : Alignment.centerLeft,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.85,
        ),
        // `Material` y no un `Container` con color: la lista de fragmentos
        // usa `ListTile`, que pinta sobre el `Material` más cercano, y un
        // fondo intermedio le tapaba el efecto del toque.
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Material(
            color: color,
            borderRadius: BorderRadius.circular(14),
            child: Padding(padding: const EdgeInsets.all(12), child: child),
          ),
        ),
      ),
    );
  }
}

class _BurbujaPaciente extends StatelessWidget {
  const _BurbujaPaciente({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return _Burbuja(
      derecha: true,
      color: Marca.primary,
      child: Text(texto, style: const TextStyle(color: Colors.white)),
    );
  }
}

class _BurbujaAsistente extends StatelessWidget {
  const _BurbujaAsistente({required this.respuesta});

  final AssistantReply respuesta;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final especialidad = respuesta.specialtyName;

    return _Burbuja(
      color: Marca.ink100,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (respuesta.emergency) const _AlertaEmergencia(),
          if (respuesta.answer.isNotEmpty)
            Text(respuesta.answer, style: const TextStyle(color: Marca.ink900)),
          // Con una urgencia no se ofrece reservar: se deriva (US-34).
          if (!respuesta.emergency && especialidad != null) ...[
            const SizedBox(height: 8),
            Text(
              'Especialidad sugerida: $especialidad',
              style: theme.textTheme.titleSmall?.copyWith(color: Marca.ink900),
            ),
            if (respuesta.specialtyId != null)
              TextButton.icon(
                onPressed: () =>
                    context.push('/search?specialty=${respuesta.specialtyId}'),
                icon: const Icon(Icons.search),
                label: const Text('Ver profesionales'),
              ),
          ],
          if (respuesta.fragments.isNotEmpty)
            Theme(
              data: theme.copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                tilePadding: EdgeInsets.zero,
                childrenPadding: EdgeInsets.zero,
                title: Text(
                  'En qué se basa (${respuesta.fragments.length})',
                  style: const TextStyle(fontSize: 13, color: Marca.ink500),
                ),
                children: [
                  for (final fragmento in respuesta.fragments)
                    ListTile(
                      dense: true,
                      contentPadding: EdgeInsets.zero,
                      leading: const Icon(Icons.format_quote, size: 18),
                      title: Text(
                        fragmento.text,
                        style: const TextStyle(color: Marca.ink800),
                      ),
                      subtitle: fragmento.source == null
                          ? null
                          : Text(fragmento.source!),
                    ),
                ],
              ),
            ),
          if (respuesta.isExample)
            const Padding(
              padding: EdgeInsets.only(top: 6),
              child: Text(
                'Respuesta de ejemplo',
                style: TextStyle(fontSize: 11, color: Marca.waiting),
              ),
            ),
        ],
      ),
    );
  }
}

class _AlertaEmergencia extends StatelessWidget {
  const _AlertaEmergencia();

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Marca.danger,
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.warning_amber_rounded, color: Colors.white),
          SizedBox(width: 8),
          Expanded(
            child: Text(
              'Esto puede ser una urgencia. No esperes una ficha: acudí ya '
              'a un servicio de emergencias o llamá a una ambulancia.',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _BurbujaError extends StatelessWidget {
  const _BurbujaError({required this.motivo, required this.onReintentar});

  final String motivo;
  final VoidCallback? onReintentar;

  @override
  Widget build(BuildContext context) {
    return _Burbuja(
      color: Marca.ink50,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'No puedo responder ahora.',
            style: TextStyle(color: Marca.ink900, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 2),
          Text(motivo, style: const TextStyle(color: Marca.ink500)),
          TextButton(onPressed: onReintentar, child: const Text('Reintentar')),
        ],
      ),
    );
  }
}

class _Pensando extends StatelessWidget {
  const _Pensando();

  @override
  Widget build(BuildContext context) {
    return const _Burbuja(
      color: Marca.ink100,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          SizedBox(width: 8),
          Text('Pensando…', style: TextStyle(color: Marca.ink500)),
        ],
      ),
    );
  }
}
