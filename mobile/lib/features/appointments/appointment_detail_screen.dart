/// El detalle de una ficha y lo que el paciente puede hacer con ella.
///
/// - `pending_payment` → pagar (US-18). Se abre la página de cobro en el
///   navegador y, al volver, se **vuelve a leer la ficha** hasta que el backend
///   diga `confirmed`. El móvil nunca la marca como pagada por su cuenta: la
///   confirma el webhook de Stripe.
/// - `confirmed` → ver el comprobante con QR (US-19) y confirmar asistencia
///   (US-21).
/// - activa → reprogramar o cancelar (US-20); al cancelar, la política de
///   devolución queda a la vista.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/payments/payments_api.dart';

import 'appointments_api.dart';
import 'formato.dart';

/// Abre una URL fuera de la aplicación. Se inyecta en las pruebas.
typedef UrlOpener = Future<bool> Function(Uri url);

Future<bool> _abrirEnNavegador(Uri url) =>
    launchUrl(url, mode: LaunchMode.externalApplication);

class AppointmentDetailScreen extends StatefulWidget {
  const AppointmentDetailScreen({
    super.key,
    required this.appointmentId,
    this.client,
    this.openUrl,
    this.pollInterval = const Duration(seconds: 3),
    this.pollTimeout = const Duration(minutes: 2),
  });

  final String appointmentId;

  @visibleForTesting
  final ApiClient? client;

  @visibleForTesting
  final UrlOpener? openUrl;

  final Duration pollInterval;
  final Duration pollTimeout;

  @override
  State<AppointmentDetailScreen> createState() =>
      _AppointmentDetailScreenState();
}

class _AppointmentDetailScreenState extends State<AppointmentDetailScreen>
    with WidgetsBindingObserver {
  ApiClient? _client;
  Appointment? _ficha;
  String? _error;
  bool _cargando = true;
  bool _ocupado = false;

  /// Se abrió la página de cobro y todavía no se vio la ficha confirmada.
  bool _esperandoPago = false;
  Timer? _poll;
  DateTime? _pollHasta;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_client == null) {
      _client = widget.client ?? ApiClient(auth: SessionScope.maybeOf(context));
      _recargar();
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _poll?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Vuelve del navegador: se pregunta enseguida, sin esperar al temporizador.
    if (state == AppLifecycleState.resumed && _esperandoPago) {
      _empezarAEsperar();
    }
  }

  Future<void> _recargar({bool silencioso = false}) async {
    if (!silencioso) setState(() => _cargando = _ficha == null);
    try {
      final ficha = await verFicha(_client!, widget.appointmentId);
      if (!mounted) return;
      setState(() {
        _ficha = ficha;
        _error = null;
        _cargando = false;
      });
      if (_esperandoPago && !ficha.isPendingPayment) _dejarDeEsperar();
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        // Un fallo durante la espera no borra lo que ya se ve.
        if (!silencioso) _error = error.message;
        _cargando = false;
      });
    }
  }

  void _empezarAEsperar() {
    _poll?.cancel();
    _pollHasta = DateTime.now().add(widget.pollTimeout);
    setState(() => _esperandoPago = true);
    _recargar(silencioso: true);
    _poll = Timer.periodic(widget.pollInterval, (_) {
      if (DateTime.now().isAfter(_pollHasta!)) {
        _poll?.cancel();
        _poll = null;
        if (mounted) setState(() {});
        return;
      }
      _recargar(silencioso: true);
    });
  }

  void _dejarDeEsperar() {
    _poll?.cancel();
    _poll = null;
    setState(() => _esperandoPago = false);
    final ficha = _ficha;
    if (ficha != null && ficha.isConfirmed) {
      _avisar('¡Pago recibido! Tu ficha está confirmada.');
    }
  }

  void _avisar(String mensaje) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(mensaje)));
  }

  Future<void> _pagar() async {
    final ficha = _ficha!;
    final importe = ficha.fee?.texto;
    final seguir = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Pagar la ficha'),
        content: Text(
          '${importe == null ? 'Vas a pagar la ficha' : 'Vas a pagar $importe'} '
          'con ${ficha.practitionerName}, el ${fechaHora(ficha.startsAt)}.\n\n'
          'Se abre la página de pago segura en el navegador. Cuando termines, '
          'volvé a la aplicación: la ficha se confirma sola en cuanto el pago '
          'se acredita.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Volver'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Ir a pagar'),
          ),
        ],
      ),
    );
    if (seguir != true) return;

    setState(() => _ocupado = true);
    try {
      final sesion = await iniciarPago(_client!, ficha.id);
      final url = Uri.tryParse(sesion.checkoutUrl);
      if (url == null || sesion.checkoutUrl.isEmpty) {
        _avisar('El servidor no devolvió la página de pago.');
        return;
      }
      final abrir = widget.openUrl ?? _abrirEnNavegador;
      final abierto = await abrir(url);
      if (!abierto) {
        _avisar('No se pudo abrir el navegador para pagar.');
        return;
      }
      if (!mounted) return;
      _empezarAEsperar();
    } on ApiError catch (error) {
      _avisar(error.message);
      // `ficha_vencida` o `ficha_no_pendiente`: la ficha cambió, mostrarla.
      await _recargar(silencioso: true);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  Future<void> _confirmarAsistencia() async {
    setState(() => _ocupado = true);
    try {
      final ficha = await confirmarAsistencia(_client!, widget.appointmentId);
      if (!mounted) return;
      setState(() => _ficha = ficha);
      _avisar('Listo: avisaste que vas a asistir.');
    } on ApiError catch (error) {
      _avisar(error.message);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  /// US-20 — Abre la pantalla de horarios. Si se reprogramó, la ficha de
  /// esta pantalla ya no es la vigente: se pasa a la nueva.
  Future<void> _reprogramar() async {
    final nueva = await context.push<Appointment>(
      '/appointments/${widget.appointmentId}/reschedule',
    );
    if (nueva == null || !mounted) return;
    context.pushReplacement('/appointments/${nueva.id}');
  }

  Future<void> _cancelar() async {
    final ficha = _ficha!;
    final pagada = ficha.isConfirmed;
    final seguir = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('¿Cancelar la ficha?'),
        content: Text(
          pagada
              ? 'El turno queda libre para otra persona.\n\n'
                    'Política de devolución: si cancelás con la anticipación '
                    'que pide el centro médico, se te devuelve el pago completo. '
                    'Si cancelás con menos anticipación, no hay devolución.'
              : 'El turno queda libre para otra persona. Como todavía no '
                    'pagaste, no hay nada que devolver.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No, mantenerla'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(context).colorScheme.error,
            ),
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Sí, cancelar'),
          ),
        ],
      ),
    );
    if (seguir != true) return;

    setState(() => _ocupado = true);
    try {
      final cancelada = await cancelarFicha(_client!, ficha.id);
      if (!mounted) return;
      setState(() => _ficha = cancelada);
      if (!pagada) {
        _avisar('Ficha cancelada.');
      } else if (cancelada.refundEligible == true) {
        _avisar(
          cancelada.paymentStatus == 'refunded'
              ? 'Ficha cancelada. El pago se devolvió.'
              : 'Ficha cancelada. Corresponde la devolución del pago.',
        );
      } else {
        _avisar('Ficha cancelada. Por la anticipación, no hay devolución.');
      }
    } on ApiError catch (error) {
      _avisar(error.message);
    } finally {
      if (mounted) setState(() => _ocupado = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mi ficha'),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            onPressed: _cargando ? null : () => _recargar(),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _cuerpo(context),
    );
  }

  Widget _cuerpo(BuildContext context) {
    final ficha = _ficha;
    if (ficha == null) {
      if (_cargando) return const Center(child: CircularProgressIndicator());
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _error ?? 'No se pudo cargar la ficha.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _recargar,
                child: const Text('Reintentar'),
              ),
            ],
          ),
        ),
      );
    }

    final theme = Theme.of(context);
    final ahora = DateTime.now();

    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                ficha.practitionerName,
                style: theme.textTheme.titleLarge,
              ),
            ),
            StatusChip(status: ficha.status),
          ],
        ),
        const SizedBox(height: 8),
        _dato(Icons.event, fechaHora(ficha.startsAt)),
        _dato(Icons.place_outlined, ficha.branchName),
        _dato(Icons.person_outline, ficha.patientName),
        if (ficha.fee != null) _dato(Icons.payments_outlined, ficha.fee!.texto),
        if (ficha.attendanceConfirmedAt != null)
          _dato(
            Icons.how_to_reg,
            'Asistencia confirmada el '
            '${fechaHora(ficha.attendanceConfirmedAt!)}',
          ),
        if (ficha.checkedInAt != null)
          _dato(
            Icons.login,
            'Ingreso registrado el ${fechaHora(ficha.checkedInAt!)}',
          ),
        if (ficha.paymentStatus == 'refunded')
          _dato(Icons.undo, 'El pago se devolvió.'),
        const SizedBox(height: 20),
        ..._acciones(context, ficha, ahora),
      ],
    );
  }

  List<Widget> _acciones(
    BuildContext context,
    Appointment ficha,
    DateTime ahora,
  ) {
    final acciones = <Widget>[];

    if (ficha.isPendingPayment) {
      if (_esperandoPago) {
        final sigue = _poll != null;
        acciones.addAll([
          Card(
            child: ListTile(
              leading: sigue
                  ? const SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.hourglass_empty),
              title: Text(
                sigue
                    ? 'Esperando la confirmación del pago…'
                    : 'Todavía no llegó la confirmación del pago.',
              ),
              subtitle: const Text(
                'La ficha se confirma cuando el pago se acredita, no antes.',
              ),
            ),
          ),
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _empezarAEsperar,
            icon: const Icon(Icons.refresh),
            label: const Text('Ya pagué — actualizar'),
          ),
          const SizedBox(height: 8),
        ]);
      }
      final importe = ficha.fee?.texto;
      final pagoEnLinea =
          SessionScope.maybeOf(context)?.incluyePagoEnLinea ?? true;
      if (!pagoEnLinea) {
        acciones.add(
          const Card(
            child: ListTile(
              leading: Icon(Icons.storefront_outlined),
              title: Text('Esta ficha se paga en recepción'),
              subtitle: Text(
                'El plan de tu centro médico no incluye el pago en línea.',
              ),
            ),
          ),
        );
      } else {
        acciones.add(
          FilledButton.icon(
            onPressed: _ocupado ? null : _pagar,
            icon: const Icon(Icons.credit_card),
            label: Text(importe == null ? 'Pagar' : 'Pagar $importe'),
          ),
        );
      }
      if (ficha.expiresAt != null) {
        acciones.add(
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Si no pagás antes de las ${hora(ficha.expiresAt!)}, el turno se '
              'libera para otra persona.',
              style: const TextStyle(color: Marca.waiting),
            ),
          ),
        );
      }
    }

    if (ficha.isConfirmed) {
      acciones.add(
        FilledButton.icon(
          onPressed: () => context.push('/appointments/${ficha.id}/receipt'),
          icon: const Icon(Icons.qr_code_2),
          label: const Text('Ver comprobante'),
        ),
      );
      if (ficha.canConfirmAttendance(ahora)) {
        acciones.addAll([
          const SizedBox(height: 8),
          OutlinedButton.icon(
            onPressed: _ocupado ? null : _confirmarAsistencia,
            icon: const Icon(Icons.how_to_reg),
            label: const Text('Confirmar que voy a asistir'),
          ),
        ]);
      }
    }

    if (ficha.isActive && !ficha.isPast(ahora)) {
      acciones.addAll([
        const SizedBox(height: 8),
        OutlinedButton.icon(
          onPressed: _ocupado ? null : _reprogramar,
          icon: const Icon(Icons.edit_calendar),
          label: const Text('Reprogramar ficha'),
        ),
        const SizedBox(height: 8),
        TextButton.icon(
          onPressed: _ocupado ? null : _cancelar,
          icon: const Icon(Icons.event_busy),
          label: const Text('Cancelar ficha'),
          style: TextButton.styleFrom(
            foregroundColor: Theme.of(context).colorScheme.error,
          ),
        ),
      ]);
    }

    return acciones;
  }

  Widget _dato(IconData icono, String texto) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(
      children: [
        Icon(icono, size: 20, color: Marca.ink500),
        const SizedBox(width: 10),
        Expanded(child: Text(texto)),
      ],
    ),
  );
}

/// El estado de la ficha con su color, en español.
class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final (fondo, texto) = switch (status) {
      AppointmentStatus.confirmed => (
        Colors.green.shade50,
        Colors.green.shade800,
      ),
      AppointmentStatus.pendingPayment => (
        Colors.orange.shade50,
        Colors.orange.shade900,
      ),
      AppointmentStatus.attended => (Marca.surfaceTint, Marca.primaryDark),
      _ => (Marca.ink100, Marca.ink500),
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: fondo,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        AppointmentStatus.etiqueta(status),
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: texto,
        ),
      ),
    );
  }
}
