/// US-19 — El comprobante con QR, presentable sin conexión.
///
/// Primero se muestra lo que hay guardado en el teléfono —abre al instante y
/// sin red— y después se pide al servidor para tenerlo al día. Si no hay red
/// y hay copia, se muestra la copia con un aviso; si no hay ninguna de las
/// dos, se explica que hay que abrirlo una vez con conexión.
library;

import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/appointments/appointments_api.dart';
import 'package:mobile/features/appointments/formato.dart';

import 'receipt_store.dart';
import 'receipts_api.dart';

class ReceiptScreen extends StatefulWidget {
  const ReceiptScreen({
    super.key,
    required this.appointmentId,
    this.client,
    this.store,
  });

  final String appointmentId;

  @visibleForTesting
  final ApiClient? client;

  @visibleForTesting
  final ReceiptStore? store;

  @override
  State<ReceiptScreen> createState() => _ReceiptScreenState();
}

class _ReceiptScreenState extends State<ReceiptScreen> {
  late final ReceiptStore _store = widget.store ?? ReceiptStore();
  ApiClient? _client;

  Receipt? _receipt;
  bool _cargando = true;

  /// La copia que se ve es la guardada: no se pudo confirmar con el servidor.
  bool _sinConexion = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_client == null) {
      _client = widget.client ?? ApiClient(auth: SessionScope.maybeOf(context));
      _cargar();
    }
  }

  Future<void> _cargar() async {
    final guardado = await _store.read(widget.appointmentId);
    if (!mounted) return;
    setState(() {
      _receipt = guardado;
      _cargando = guardado == null;
      _error = null;
    });

    try {
      final nuevo = await pedirComprobante(_client!, widget.appointmentId);
      await _store.save(nuevo);
      if (!mounted) return;
      setState(() {
        _receipt = nuevo;
        _sinConexion = false;
        _cargando = false;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      // Sin red: alcanza con la copia. Con un rechazo del servidor —la ficha
      // se canceló, por ejemplo— la copia ya no vale y se borra.
      if (!error.isOffline && error.status >= 400 && error.status < 500) {
        await _store.remove(widget.appointmentId);
        if (!mounted) return;
        setState(() {
          _receipt = null;
          _error = error.message;
          _cargando = false;
        });
        return;
      }
      setState(() {
        _sinConexion = _receipt != null;
        _error = _receipt == null
            ? (error.isOffline
                  ? 'No hay conexión y este comprobante todavía no se guardó en '
                        'el teléfono. Abrilo una vez con conexión.'
                  : error.message)
            : null;
        _cargando = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Comprobante'),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            onPressed: _cargando ? null : _cargar,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _cuerpo(context),
    );
  }

  Widget _cuerpo(BuildContext context) {
    final receipt = _receipt;
    if (receipt == null) {
      if (_cargando) return const Center(child: CircularProgressIndicator());
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                _error ?? 'No hay comprobante.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 16),
              FilledButton(onPressed: _cargar, child: const Text('Reintentar')),
            ],
          ),
        ),
      );
    }

    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 32),
      children: [
        if (_sinConexion)
          Card(
            color: theme.colorScheme.surfaceContainerHighest,
            margin: const EdgeInsets.only(bottom: 16),
            child: const ListTile(
              leading: Icon(Icons.cloud_off),
              title: Text('Sin conexión — copia guardada'),
              subtitle: Text(
                'Es el comprobante que guardaste en el teléfono. Recepción lo '
                'valida igual.',
              ),
            ),
          ),
        if (receipt.organizationName.isNotEmpty)
          Text(
            receipt.organizationName,
            textAlign: TextAlign.center,
            style: theme.textTheme.titleMedium,
          ),
        const SizedBox(height: 12),
        Center(
          // Fondo blanco fijo: un QR sobre el fondo oscuro del tema no lo lee
          // ningún lector.
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Marca.ink300),
            ),
            child: QrImageView(
              data: receipt.code,
              size: 260,
              backgroundColor: Colors.white,
              semanticsLabel: 'Código QR del comprobante',
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Mostrá este código en recepción al llegar.',
          textAlign: TextAlign.center,
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 20),
        _dato('Paciente', receipt.patientName),
        if (receipt.documentNumber.isNotEmpty)
          _dato('Documento', receipt.documentNumber),
        _dato('Profesional', receipt.practitionerName),
        _dato(
          'Sucursal',
          receipt.branchAddress.isEmpty
              ? receipt.branchName
              : '${receipt.branchName} · ${receipt.branchAddress}',
        ),
        if (receipt.startsAt != null)
          _dato('Fecha y hora', fechaHora(receipt.startsAt!)),
        if (receipt.status.isNotEmpty)
          _dato('Estado', AppointmentStatus.etiqueta(receipt.status)),
        if (receipt.issuedAt != null)
          _dato('Emitido', fechaHora(receipt.issuedAt!)),
      ],
    );
  }

  Widget _dato(String etiqueta, String valor) => ListTile(
    dense: true,
    contentPadding: EdgeInsets.zero,
    title: Text(etiqueta),
    subtitle: Text(valor.isEmpty ? '—' : valor),
  );
}

/// "Mis comprobantes": los guardados en el teléfono, sin pedir nada a la red.
///
/// Es la salida cuando la lista de fichas no carga porque no hay señal.
class SavedReceiptsScreen extends StatefulWidget {
  const SavedReceiptsScreen({super.key, this.store, this.onOpen});

  @visibleForTesting
  final ReceiptStore? store;

  /// Qué hacer al tocar uno; por omisión, abrir [ReceiptScreen].
  final void Function(BuildContext context, Receipt receipt)? onOpen;

  @override
  State<SavedReceiptsScreen> createState() => _SavedReceiptsScreenState();
}

class _SavedReceiptsScreenState extends State<SavedReceiptsScreen> {
  late final Future<List<Receipt>> _futuro = (widget.store ?? ReceiptStore())
      .all();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mis comprobantes')),
      body: FutureBuilder<List<Receipt>>(
        future: _futuro,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final lista = snapshot.data ?? const <Receipt>[];
          if (lista.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Text(
                  'Todavía no hay comprobantes guardados en este teléfono. Se '
                  'guardan solos la primera vez que abrís uno con conexión.',
                  textAlign: TextAlign.center,
                ),
              ),
            );
          }
          return ListView.separated(
            padding: const EdgeInsets.symmetric(vertical: 8),
            itemCount: lista.length,
            separatorBuilder: (_, _) => const Divider(height: 1),
            itemBuilder: (context, i) {
              final r = lista[i];
              return ListTile(
                leading: const Icon(Icons.qr_code_2),
                title: Text(r.practitionerName),
                subtitle: Text(
                  [
                    if (r.startsAt != null) fechaHora(r.startsAt!),
                    r.branchName,
                  ].where((t) => t.isNotEmpty).join(' · '),
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () {
                  final abrir = widget.onOpen;
                  if (abrir != null) {
                    abrir(context, r);
                  } else {
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) =>
                            ReceiptScreen(appointmentId: r.appointmentId),
                      ),
                    );
                  }
                },
              );
            },
          );
        },
      ),
    );
  }
}
