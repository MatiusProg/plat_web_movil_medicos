/// La conversación con el asistente de orientación (US-31 / US-34) y la
/// reserva conversacional (US-33).
///
/// Reglas que la pantalla hace cumplir aunque el backend falle:
///
///   1. **Si no hay respuesta, no se inventa una.** Error, servidor caído o sin
///      red: se dice "no puedo responder ahora" y se ofrece reintentar.
///   2. **Una urgencia corta el camino a la reserva.** Con `emergency` no se
///      ofrecen profesionales ni horarios: se deriva a emergencias (US-34).
///   3. **La sugerencia viaja con sus fragmentos.** Son los que muestran en qué
///      se basó el asistente.
///   4. **US-33: los horarios salen de `slots/`, nunca del texto**, y nada se
///      reserva sin que el paciente toque *Reservar* en la hoja de
///      confirmación. Tocar un horario sólo abre la hoja.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/appointments/confirmar_reserva_sheet.dart';
import 'package:mobile/features/appointments/formato.dart' as formato;
import 'package:mobile/features/dependents/dependents_api.dart';

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

/// US-33 — Con qué se pidieron unos horarios, para volver a pedirlos igual.
class _Pedido {
  const _Pedido(this.specialtyId, this.preferencia);

  final String specialtyId;
  final String preferencia;
}

/// Un turno de la conversación: lo que escribió el paciente, lo que contestó
/// el asistente, los horarios que ofreció, la ficha reservada, un aviso, o que
/// no pudo contestar.
class _Turno {
  const _Turno.paciente(this.texto)
    : respuesta = null,
      turnos = null,
      pedido = null,
      ficha = null,
      error = null,
      reintentar = null;
  const _Turno.asistente(AssistantReply this.respuesta)
    : texto = '',
      turnos = null,
      pedido = null,
      ficha = null,
      error = null,
      reintentar = null;
  const _Turno.turnos(SlotsReply this.turnos, _Pedido this.pedido)
    : texto = '',
      respuesta = null,
      ficha = null,
      error = null,
      reintentar = null;
  const _Turno.reservada(Appointment this.ficha)
    : texto = '',
      respuesta = null,
      turnos = null,
      pedido = null,
      error = null,
      reintentar = null;
  const _Turno.aviso(this.texto)
    : respuesta = null,
      turnos = null,
      pedido = null,
      ficha = null,
      error = '',
      reintentar = null;
  const _Turno.error(String this.error, Future<void> Function() this.reintentar)
    : texto = '',
      respuesta = null,
      turnos = null,
      pedido = null,
      ficha = null;

  final String texto;
  final AssistantReply? respuesta;
  final SlotsReply? turnos;
  final _Pedido? pedido;
  final Appointment? ficha;
  final String? error;

  /// En un turno de error, lo que hay que volver a pedir.
  final Future<void> Function()? reintentar;

  bool get esAviso => error == '' && reintentar == null && texto.isNotEmpty;
  bool get esError => reintentar != null;
  bool get esPaciente =>
      respuesta == null && turnos == null && ficha == null && error == null;
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
      }
      _esperando = true;
    });
    _bajar();

    _Turno turno;
    AssistantReply? respuesta;
    try {
      respuesta = await consultarAsistente(
        client,
        mensaje,
        demo: widget.demo,
      );
      turno = _Turno.asistente(respuesta);
    } on ApiError catch (error) {
      turno = _Turno.error(_motivo(error), () => _enviar(mensaje));
    } catch (_) {
      turno = _Turno.error(
        'El servidor respondió algo que no se pudo interpretar.',
        () => _enviar(mensaje),
      );
    }

    if (!mounted) return;
    setState(() {
      _turnos.add(turno);
      _esperando = false;
    });
    _bajar();

    // US-33: si el mensaje ya pedía un turno, los horarios se buscan solos,
    // con el mismo mensaje como preferencia ("el jueves por la tarde").
    final pista = respuesta?.booking;
    if (respuesta != null &&
        !respuesta.emergency &&
        pista != null &&
        pista.puedeReservar &&
        pista.bookingIntent) {
      await _buscarTurnos(_Pedido(pista.specialtyId!, mensaje));
    }
  }

  /// US-33 — Pide horarios reales. Con `escrito`, primero agrega lo que el
  /// paciente tocó o escribió ("Por la tarde") como un turno suyo.
  Future<void> _buscarTurnos(_Pedido pedido, {String? escrito}) async {
    if (_esperando) return;
    setState(() {
      if (escrito != null) _turnos.add(_Turno.paciente(escrito));
      _esperando = true;
    });
    _bajar();

    _Turno turno;
    try {
      final turnos = await pedirTurnos(
        client,
        pedido.specialtyId,
        pedido.preferencia,
        demo: widget.demo,
      );
      turno = _Turno.turnos(turnos, pedido);
    } on ApiError catch (error) {
      turno = _Turno.error(_motivo(error), () => _buscarTurnos(pedido));
    } catch (_) {
      turno = _Turno.error(
        'El servidor respondió algo que no se pudo interpretar.',
        () => _buscarTurnos(pedido),
      );
    }

    if (!mounted) return;
    setState(() {
      _turnos.add(turno);
      _esperando = false;
    });
    _bajar();
  }

  /// US-33 — Tocar un horario abre la hoja; sólo *Reservar* reserva.
  Future<void> _elegir(OfferedSlot oferta, _Pedido pedido) async {
    if (_esperando) return;
    final inicio = oferta.inicio;
    final paraQuien = await showModalBottomSheet<PatientOption>(
      context: context,
      isScrollControlled: true,
      builder: (context) => ConfirmarReservaSheet(
        profesional: oferta.practitionerName,
        sede: oferta.branchName,
        cuando: inicio == null
            ? oferta.start
            : '${formato.fecha(inicio)} a las ${formato.hora(inicio)}',
        client: client,
      ),
    );
    if (paraQuien == null || !mounted) return;

    final avisos = ScaffoldMessenger.of(context);
    setState(() => _esperando = true);
    _bajar();
    try {
      final ficha = await reservarDesdeAsistente(
        client,
        patientId: paraQuien.id,
        turno: oferta,
        demo: widget.demo,
      );
      if (!mounted) return;
      setState(() {
        _turnos.add(_Turno.reservada(ficha));
        _esperando = false;
      });
      _bajar();
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _esperando = false);
      if (error.code == 'turno_ocupado') {
        // Otro lo tomó entre que se mostró y se confirmó: se vuelve a pedir
        // igual, y el horario ocupado ya no aparece.
        setState(() => _turnos.add(const _Turno.aviso(
              'Ese horario se acaba de ocupar. Estos son los que quedan.',
            )));
        await _buscarTurnos(pedido);
      } else {
        avisos.showSnackBar(SnackBar(content: Text(error.message)));
      }
    }
  }

  Future<void> _reintentar(_Turno turno) async {
    setState(() => _turnos.remove(turno));
    await turno.reintentar!();
  }

  String _motivo(ApiError error) {
    if (error.isOffline) return 'No hay conexión con el servidor.';
    if (error.status == 404 && error.code != 'especialidad_invalida') {
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
      appBar: AppBar(title: const Text('Asistente')),
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
                      if (turno.esAviso) {
                        return _BurbujaAviso(texto: turno.texto);
                      }
                      if (turno.esError) {
                        return _BurbujaError(
                          motivo: turno.error!,
                          onReintentar: _esperando
                              ? null
                              : () => _reintentar(turno),
                        );
                      }
                      if (turno.turnos != null) {
                        final pedido = turno.pedido!;
                        return _BurbujaTurnos(
                          turnos: turno.turnos!,
                          habilitada: !_esperando,
                          onElegir: (oferta) => _elegir(oferta, pedido),
                          onBuscar: (texto) => _buscarTurnos(
                            _Pedido(pedido.specialtyId, texto),
                            escrito: texto,
                          ),
                        );
                      }
                      if (turno.ficha != null) {
                        return _BurbujaReservada(ficha: turno.ficha!);
                      }
                      final pista = turno.respuesta!.booking;
                      return _BurbujaAsistente(
                        respuesta: turno.respuesta!,
                        // Sin intención de reservar, el paciente pide ver
                        // horarios con un botón.
                        onVerHorarios: pista != null &&
                                pista.puedeReservar &&
                                !pista.bookingIntent &&
                                !_esperando
                            ? () => _buscarTurnos(_Pedido(pista.specialtyId!, ''))
                            : null,
                      );
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
                        hintText: 'Tus síntomas, o un horario o precio…',
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
              'Describe tus síntomas y te sugiero con qué especialidad '
              'consultar.\n\nTambién puedes preguntarme horarios y '
              'direcciones de las sucursales, precios de consultas y '
              'estudios, cómo prepararte o cómo cancelar una ficha.',
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
  const _BurbujaAsistente({required this.respuesta, this.onVerHorarios});

  final AssistantReply respuesta;

  /// US-33: `null` si no se puede reservar, o si los horarios ya se buscaron
  /// solos.
  final VoidCallback? onVerHorarios;

  @override
  Widget build(BuildContext context) {
    // La burbuja es un fondo claro fijo (`ink100`) también en modo oscuro.
    // Con el tema oscuro, lo que no lleva color propio —el subtítulo de cada
    // fragmento, la flecha del desplegable, el ícono de la cita— salía en
    // gris claro sobre gris claro. Se le da el tema claro a todo el contenido.
    final theme = AppTheme.light;
    final especialidad = respuesta.specialtyName;

    return Theme(
      data: theme,
      child: _Burbuja(
        color: Marca.ink100,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (respuesta.emergency) const _AlertaEmergencia(),
            if (respuesta.answer.isNotEmpty)
              Text(
                respuesta.answer,
                style: const TextStyle(color: Marca.ink900),
              ),
            // Con una urgencia no se ofrece reservar: se deriva (US-34).
            if (!respuesta.emergency && especialidad != null) ...[
              const SizedBox(height: 8),
              Text(
                'Especialidad sugerida: $especialidad',
                style: theme.textTheme.titleSmall?.copyWith(
                  color: Marca.ink900,
                ),
              ),
              Wrap(
                spacing: 4,
                children: [
                  if (respuesta.specialtyId != null)
                    TextButton.icon(
                      onPressed: () => context.push(
                        '/search?specialty=${respuesta.specialtyId}',
                      ),
                      icon: const Icon(Icons.search),
                      label: const Text('Ver profesionales'),
                    ),
                  if (onVerHorarios != null)
                    TextButton.icon(
                      onPressed: onVerHorarios,
                      icon: const Icon(Icons.event_available),
                      label: const Text('Ver horarios'),
                    ),
                ],
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
              'Esto puede ser una urgencia. No esperes una ficha: acude ya '
              'a un servicio de emergencias o llama a una ambulancia.',
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

/// US-33 — Los horarios que ofreció `slots/`, para elegir uno, o pedir otros.
class _BurbujaTurnos extends StatefulWidget {
  const _BurbujaTurnos({
    required this.turnos,
    required this.habilitada,
    required this.onElegir,
    required this.onBuscar,
  });

  final SlotsReply turnos;
  final bool habilitada;
  final void Function(OfferedSlot oferta) onElegir;
  final void Function(String texto) onBuscar;

  @override
  State<_BurbujaTurnos> createState() => _BurbujaTurnosState();
}

class _BurbujaTurnosState extends State<_BurbujaTurnos> {
  final _otro = TextEditingController();

  static const _rapidos = [
    'Mañana',
    'Por la mañana',
    'Por la tarde',
    'La semana que viene',
  ];

  @override
  void dispose() {
    _otro.dispose();
    super.dispose();
  }

  void _buscarOtro() {
    final texto = _otro.text.trim();
    if (texto.isEmpty || !widget.habilitada) return;
    _otro.clear();
    widget.onBuscar(texto);
  }

  @override
  Widget build(BuildContext context) {
    final turnos = widget.turnos;
    return Theme(
      data: AppTheme.light,
      child: _Burbuja(
        color: Marca.ink100,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Una urgencia en la preferencia: se deriva, sin horarios.
            if (turnos.emergency) const _AlertaEmergencia(),
            if (turnos.answer.isNotEmpty)
              Text(turnos.answer, style: const TextStyle(color: Marca.ink900)),
            if (!turnos.emergency) ...[
              for (final oferta in turnos.offers)
                Card(
                  margin: const EdgeInsets.only(top: 8),
                  child: ListTile(
                    enabled: widget.habilitada,
                    onTap: () => widget.onElegir(oferta),
                    leading: const Icon(Icons.event, color: Marca.primary),
                    title: Text(
                      oferta.inicio == null
                          ? oferta.start
                          : formato.fechaHora(oferta.inicio!),
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      '${oferta.practitionerName} · ${oferta.branchName}',
                    ),
                    trailing: const Icon(Icons.chevron_right),
                  ),
                ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                children: [
                  for (final rapido in _rapidos)
                    ActionChip(
                      label: Text(rapido),
                      onPressed:
                          widget.habilitada ? () => widget.onBuscar(rapido) : null,
                    ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const ValueKey('otro-horario'),
                      controller: _otro,
                      enabled: widget.habilitada,
                      maxLength: 200,
                      textInputAction: TextInputAction.search,
                      onSubmitted: (_) => _buscarOtro(),
                      decoration: const InputDecoration(
                        hintText: '¿Otro día u horario?',
                        counterText: '',
                        isDense: true,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: widget.habilitada ? _buscarOtro : null,
                    child: const Text('Buscar'),
                  ),
                ],
              ),
            ],
            if (turnos.isExample)
              const Padding(
                padding: EdgeInsets.only(top: 6),
                child: Text(
                  'Horarios de ejemplo',
                  style: TextStyle(fontSize: 11, color: Marca.waiting),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// US-33 — La ficha quedó reservada, pendiente de pago.
class _BurbujaReservada extends StatelessWidget {
  const _BurbujaReservada({required this.ficha});

  final Appointment ficha;

  @override
  Widget build(BuildContext context) {
    return Theme(
      data: AppTheme.light,
      child: _Burbuja(
        color: Marca.surfaceTint,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.check_circle, color: Marca.primary),
                SizedBox(width: 6),
                Text(
                  'Ficha reservada',
                  style: TextStyle(
                    color: Marca.ink900,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              '${formato.fechaHora(ficha.startsAt.toLocal())} · '
              '${ficha.practitionerName} · ${ficha.branchName}',
              style: const TextStyle(color: Marca.ink800),
            ),
            const SizedBox(height: 4),
            const Text(
              'Queda pendiente de pago. Págala desde tus fichas para '
              'confirmarla.',
              style: TextStyle(color: Marca.ink500),
            ),
            TextButton.icon(
              onPressed: () => context.push('/appointments/${ficha.id}'),
              icon: const Icon(Icons.receipt_long),
              label: const Text('Ir a la ficha'),
            ),
          ],
        ),
      ),
    );
  }
}

class _BurbujaAviso extends StatelessWidget {
  const _BurbujaAviso({required this.texto});

  final String texto;

  @override
  Widget build(BuildContext context) {
    return _Burbuja(
      color: Marca.ink50,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.info_outline, size: 18, color: Marca.waiting),
          const SizedBox(width: 6),
          Flexible(
            child: Text(texto, style: const TextStyle(color: Marca.ink800)),
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
