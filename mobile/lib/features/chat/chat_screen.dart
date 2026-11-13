/// US-47 — "Chat con tu médico": las consultas sobre una atención ya firmada.
///
/// Se abre desde la atención en "Mi historia clínica" y desde el aviso que
/// llega cuando el médico responde. Arriba, siempre visible, que esto no es
/// para urgencias; debajo, la receta y las órdenes de esa atención, que es de
/// lo que se pregunta.
///
/// Si lo que escribe el paciente suena a urgencia, el backend lo marca y
/// devuelve la derivación a emergencias, que se muestra antes que nada.
///
/// Sin tiempo real: mientras la pantalla está abierta se vuelve a pedir la
/// conversación cada 10 segundos.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';

import 'chat_api.dart';

const _meses = [
  'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto',
  'septiembre', 'octubre', 'noviembre', 'diciembre',
];

String _fecha(DateTime? d) {
  if (d == null) return '';
  final l = d.toLocal();
  return '${l.day} de ${_meses[l.month - 1]}';
}

String _hora(DateTime? d) {
  if (d == null) return '';
  final l = d.toLocal();
  String dos(int n) => n.toString().padLeft(2, '0');
  return '${_fecha(l)}, ${dos(l.hour)}:${dos(l.minute)}';
}

class ChatScreen extends StatefulWidget {
  const ChatScreen({
    super.key,
    required this.encounterId,
    this.client,
    this.cadaCuanto = const Duration(seconds: 10),
  });

  final String encounterId;

  @visibleForTesting
  final ApiClient? client;

  @visibleForTesting
  final Duration cadaCuanto;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  ApiClient? _client;
  Conversacion? _datos;
  String? _error;
  String? _urgencia;
  bool _enviando = false;
  Timer? _sondeo;
  final _texto = TextEditingController();
  final _scroll = ScrollController();

  ApiClient get client =>
      _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_sondeo == null) {
      _cargar();
      _sondeo = Timer.periodic(widget.cadaCuanto, (_) => _cargar());
    }
  }

  @override
  void dispose() {
    _sondeo?.cancel();
    _texto.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    try {
      final datos = await verConversacion(client, encounterId: widget.encounterId);
      if (!mounted) return;
      final antes = _datos?.mensajes.length ?? 0;
      setState(() {
        _datos = datos;
        _error = null;
      });
      if (datos.mensajes.length != antes) _alFinal();
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    }
  }

  void _alFinal() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  Future<void> _enviar() async {
    final body = _texto.text.trim();
    if (body.isEmpty || _enviando) return;
    setState(() => _enviando = true);
    final avisos = ScaffoldMessenger.of(context);
    try {
      final urgencia = await escribirMensaje(client,
          encounterId: widget.encounterId, body: body);
      _texto.clear();
      setState(() => _urgencia = urgencia);
      await _cargar();
    } on ApiError catch (error) {
      avisos.showSnackBar(SnackBar(content: Text(error.message)));
      await _cargar();
    } finally {
      if (mounted) setState(() => _enviando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final datos = _datos;
    return Scaffold(
      appBar: AppBar(
        title: Text(datos == null ? 'Chat con tu médico' : datos.practitionerName),
      ),
      body: _error != null && datos == null
          ? _Problema(texto: _error!, onReintentar: _cargar)
          : datos == null
              ? const Center(child: CircularProgressIndicator())
              : Column(
                  children: [
                    Expanded(
                      child: ListView(
                        controller: _scroll,
                        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
                        children: [
                          _NoEsUrgencias(texto: datos.notice),
                          if (datos.receta.isNotEmpty || datos.ordenes.isNotEmpty)
                            _Receta(datos: datos),
                          if (_urgencia != null) _Urgencia(texto: _urgencia!),
                          const SizedBox(height: 8),
                          if (datos.mensajes.isEmpty)
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 24),
                              child: Text(
                                'Escribe tu duda sobre la medicación o las '
                                'indicaciones de la atención del '
                                '${_fecha(datos.encounterDate)}.',
                                textAlign: TextAlign.center,
                                style: theme.textTheme.bodyMedium?.copyWith(
                                    color: theme.colorScheme.onSurfaceVariant),
                              ),
                            ),
                          for (final m in datos.mensajes) _Burbuja(mensaje: m),
                        ],
                      ),
                    ),
                    datos.canWrite
                        ? _Caja(
                            controller: _texto,
                            enviando: _enviando,
                            hasta: datos.closesAt,
                            onEnviar: _enviar,
                          )
                        : _Cerrada(datos: datos),
                  ],
                ),
    );
  }
}

class _NoEsUrgencias extends StatelessWidget {
  const _NoEsUrgencias({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: esquema.tertiaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.info_outline, size: 20, color: esquema.onTertiaryContainer),
          const SizedBox(width: 8),
          Expanded(
            child: Text(texto,
                style: TextStyle(color: esquema.onTertiaryContainer)),
          ),
        ],
      ),
    );
  }
}

class _Receta extends StatelessWidget {
  const _Receta({required this.datos});

  final Conversacion datos;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(top: 12),
      child: ExpansionTile(
        title: const Text('Receta y órdenes de esta atención'),
        initiallyExpanded: true,
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
        expandedCrossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final r in datos.receta) Text('• $r'),
          for (final o in datos.ordenes) Text('• $o'),
        ],
      ),
    );
  }
}

class _Urgencia extends StatelessWidget {
  const _Urgencia({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Container(
      key: const Key('urgencia'),
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: esquema.errorContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(texto,
              style: TextStyle(
                  color: esquema.onErrorContainer, fontWeight: FontWeight.w600)),
          const SizedBox(height: 4),
          Text(
            'Tu mensaje le llegó a tu médico igual, pero no esperes su '
            'respuesta para ir.',
            style: TextStyle(color: esquema.onErrorContainer),
          ),
        ],
      ),
    );
  }
}

class _Burbuja extends StatelessWidget {
  const _Burbuja({required this.mensaje});

  final MensajeChat mensaje;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final esquema = theme.colorScheme;
    final mio = mensaje.mine;
    return Align(
      alignment: mio ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
            maxWidth: MediaQuery.of(context).size.width * 0.8),
        decoration: BoxDecoration(
          color: mio ? esquema.primary : esquema.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(16),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(mensaje.body,
                style: TextStyle(color: mio ? esquema.onPrimary : esquema.onSurface)),
            const SizedBox(height: 4),
            Text(
              '${mio ? 'Tú' : mensaje.authorName} · ${_hora(mensaje.createdAt)}',
              style: theme.textTheme.labelSmall?.copyWith(
                  color: mio
                      ? esquema.onPrimary.withValues(alpha: 0.8)
                      : esquema.onSurfaceVariant),
            ),
          ],
        ),
      ),
    );
  }
}

class _Caja extends StatelessWidget {
  const _Caja({
    required this.controller,
    required this.enviando,
    required this.hasta,
    required this.onEnviar,
  });

  final TextEditingController controller;
  final bool enviando;
  final DateTime? hasta;
  final VoidCallback onEnviar;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      top: false,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 8, 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: TextField(
                controller: controller,
                minLines: 1,
                maxLines: 5,
                maxLength: maxCaracteresMensaje,
                textCapitalization: TextCapitalization.sentences,
                decoration: InputDecoration(
                  hintText: 'Escribe tu consulta…',
                  helperText: hasta == null
                      ? null
                      : 'Puedes escribir hasta el ${_fecha(hasta)}.',
                  counterText: '',
                ),
              ),
            ),
            const SizedBox(width: 4),
            IconButton.filled(
              tooltip: 'Enviar',
              onPressed: enviando ? null : onEnviar,
              icon: enviando
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : const Icon(Icons.send),
            ),
          ],
        ),
      ),
    );
  }
}

class _Cerrada extends StatelessWidget {
  const _Cerrada({required this.datos});

  final Conversacion datos;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      top: false,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(16),
        color: theme.colorScheme.surfaceContainerHigh,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              datos.closedReason == 'closed'
                  ? 'El médico cerró esta conversación.'
                  : 'La conversación se cerró: pasaron ${datos.windowDays} '
                      'días desde la atención.',
            ),
            const SizedBox(height: 8),
            OutlinedButton(
              onPressed: () => context.push('/search'),
              child: const Text('Reservar una ficha nueva'),
            ),
          ],
        ),
      ),
    );
  }
}

class _Problema extends StatelessWidget {
  const _Problema({required this.texto, required this.onReintentar});

  final String texto;
  final Future<void> Function() onReintentar;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(texto, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onReintentar, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }
}
