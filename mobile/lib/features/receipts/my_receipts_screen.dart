/// US-46 — Mis comprobantes, pedidos hablando o escribiendo.
///
/// «Mis últimas 2 facturas», «los pagos de octubre», «mis fichas de
/// cardiología»: la persona dice qué quiere y ve la lista con el **código QR**
/// de cada comprobante, que es el mismo de la ficha (US-19) y el que lee
/// recepción al llegar. También se baja en PDF con los QR.
///
/// Tres decisiones que explican cómo se ve:
///
/// 1. **La voz propone, no ejecuta sola.** Primero se muestra qué entendió el
///    sistema («Entendí: Pagos con comprobante · últimos 2») y recién después
///    aparece la lista. Si no entendió, dice qué no pudo y no muestra nada:
///    una lista de más se leería como si fuera lo que se pidió.
/// 2. **Escribir siempre alcanza.** El dictado depende del reconocedor del
///    teléfono; si no está o el micrófono está denegado, el botón no aparece y
///    la caja de texto sigue sirviendo.
/// 3. **Solo lo propio.** La pantalla nunca manda de quién son los datos: lo
///    decide el backend con la sesión, y son los de la persona y sus
///    dependientes. Por eso cada comprobante dice a quién pertenece.
library;

import 'dart:io' show FileSystemException;

import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/files/archivos.dart';
import '../../core/session/session_scope.dart';
import '../reporting/reporting_api.dart' show nombreDeReporte;
import '../reporting/voice_input.dart';
import 'my_receipts_api.dart';

class MyReceiptsScreen extends StatefulWidget {
  const MyReceiptsScreen({
    super.key,
    this.client,
    this.dictado,
    this.guardado,
    this.abridor,
    this.onAbrir,
    this.onVerGuardados,
  });

  /// Qué hacer al tocar un comprobante: abrirlo en grande, que además lo
  /// guarda para verlo sin conexión. La ruta lo resuelve; sin esto, la
  /// tarjeta no es tocable.
  final void Function(ComprobanteDeLista item)? onAbrir;

  /// Ir a los comprobantes guardados en el teléfono. Sin esto, no se muestra.
  final VoidCallback? onVerGuardados;

  @visibleForTesting
  final ApiClient? client;

  /// El dictado se inyecta para poder probar la pantalla sin micrófono.
  @visibleForTesting
  final DictadoDeVoz? dictado;

  /// Dónde se guarda el PDF y con qué se abre. Se inyectan para probar sin
  /// tocar el disco ni lanzar otra aplicación.
  @visibleForTesting
  final GuardadoDeArchivos? guardado;
  @visibleForTesting
  final AbridorDeArchivos? abridor;

  @override
  State<MyReceiptsScreen> createState() => _MyReceiptsScreenState();
}

class _MyReceiptsScreenState extends State<MyReceiptsScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  late final DictadoDeVoz _dictado = widget.dictado ?? DictadoDelSistema();
  late final GuardadoDeArchivos _guardado =
      widget.guardado ?? const GuardadoEnDescargas();
  late final AbridorDeArchivos _abridor =
      widget.abridor ?? const AbridorDelSistema();

  final _texto = TextEditingController();
  bool _puedeDictar = false;
  bool _escuchando = false;
  String _loQueOigo = '';

  PropuestaDeComprobantes? _propuesta;
  ListaDeComprobantes? _lista;
  ConsultaDeComprobantes? _consulta;
  bool _buscando = false;
  bool _descargando = false;
  String? _error;

  // Cada búsqueda lleva un número: si la persona pide otra mientras llega la
  // respuesta de la anterior, la vieja no pisa a la nueva.
  int _busqueda = 0;
  bool _dictadoPreparado = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_dictadoPreparado) {
      _dictadoPreparado = true;
      _prepararDictado();
    }
  }

  @override
  void dispose() {
    _dictado.soltar();
    _texto.dispose();
    super.dispose();
  }

  Future<void> _prepararDictado() async {
    final puede = await _dictado.preparar();
    if (!mounted) return;
    setState(() => _puedeDictar = puede);
  }

  Future<void> _hablar() async {
    if (_escuchando) {
      await _dictado.terminar();
      if (mounted) setState(() => _escuchando = false);
      return;
    }
    setState(() {
      _escuchando = true;
      _loQueOigo = '';
      _error = null;
    });
    await _dictado.empezar(
      alCambiar: (texto) {
        if (mounted) setState(() => _loQueOigo = texto);
      },
      alTerminar: (texto) {
        if (!mounted) return;
        setState(() {
          _escuchando = false;
          _loQueOigo = texto;
          _texto.text = texto;
        });
        _buscar(texto);
      },
    );
  }

  Future<void> _buscar(String texto) async {
    final limpio = texto.trim();
    if (limpio.isEmpty) return;
    final numero = ++_busqueda;
    setState(() {
      _buscando = true;
      _error = null;
      _lista = null;
      _consulta = null;
    });
    try {
      final propuesta = await interpretarComprobantes(client, limpio);
      if (!mounted || numero != _busqueda) return;
      setState(() => _propuesta = propuesta);
      final consulta = propuesta.consulta;
      if (!propuesta.entendio || consulta == null) return;

      final lista = await listarComprobantes(client, consulta);
      if (!mounted || numero != _busqueda) return;
      setState(() {
        _consulta = consulta;
        _lista = lista;
      });
    } on ApiError catch (error) {
      if (!mounted || numero != _busqueda) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted && numero == _busqueda) setState(() => _buscando = false);
    }
  }

  Future<void> _bajarPdf() async {
    final consulta = _consulta;
    if (consulta == null) return;
    setState(() {
      _descargando = true;
      _error = null;
    });
    try {
      final archivo = await descargarComprobantesPdf(client, consulta);
      final nombre = nombreDeReporte(
        archivo,
        dataset: 'mis-comprobantes',
        format: 'pdf',
      );
      final ruta = await _guardado.guardar(nombre, archivo.bytes);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Descargado en Descargas: ${ruta.split('/').last}'),
          action: SnackBarAction(label: 'Abrir', onPressed: () => _abrir(ruta)),
        ),
      );
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } on FileSystemException catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _descargando = false);
    }
  }

  Future<void> _abrir(String ruta) async {
    final problema = await _abridor.abrir(ruta);
    if (problema == null || !mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(problema)));
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final lista = _lista;
    final propuesta = _propuesta;

    return Scaffold(
      appBar: AppBar(title: const Text('Mis comprobantes')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Pídelos hablando o escribiendo y verás el código QR de cada '
              'uno. Salen los tuyos y los de las personas a tu cargo.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            _Pedido(
              controlador: _texto,
              puedeDictar: _puedeDictar,
              escuchando: _escuchando,
              loQueOigo: _loQueOigo,
              ocupado: _buscando,
              onBuscar: () => _buscar(_texto.text),
              onHablar: _hablar,
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Text(
                _error!,
                style: theme.textTheme.bodyMedium?.copyWith(
                  color: theme.colorScheme.error,
                ),
              ),
            ],
            if (propuesta != null && !_buscando && !_escuchando) ...[
              const SizedBox(height: 16),
              _LoQueEntendio(propuesta: propuesta),
            ],
            if (lista != null) ...[
              const SizedBox(height: 16),
              _Resultados(
                lista: lista,
                descargando: _descargando,
                onDescargar: _bajarPdf,
                onAbrir: widget.onAbrir,
              ),
            ],
            if (widget.onVerGuardados != null) ...[
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  style: TextButton.styleFrom(minimumSize: const Size(0, 44)),
                  onPressed: widget.onVerGuardados,
                  icon: const Icon(Icons.offline_pin_outlined),
                  label: const Text('Ver los guardados en este teléfono'),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------
//  El pedido: texto y voz
// --------------------------------------------------------------------------
class _Pedido extends StatelessWidget {
  const _Pedido({
    required this.controlador,
    required this.puedeDictar,
    required this.escuchando,
    required this.loQueOigo,
    required this.ocupado,
    required this.onBuscar,
    required this.onHablar,
  });

  final TextEditingController controlador;
  final bool puedeDictar;
  final bool escuchando;
  final String loQueOigo;
  final bool ocupado;
  final VoidCallback onBuscar;
  final VoidCallback onHablar;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: controlador,
              maxLength: 300,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => onBuscar(),
              decoration: const InputDecoration(
                labelText: '¿Qué quieres ver?',
                hintText: 'Mis últimas 2 facturas',
                counterText: '',
              ),
            ),
            const SizedBox(height: 12),
            // Los botones declaran su propio tamaño mínimo: el tema da a los
            // botones ancho completo (`Size.fromHeight`) y, dentro de una
            // fila, eso pide un ancho sin límite y deja la pantalla en
            // blanco (el defecto del Xiaomi del 05/10).
            Row(
              children: [
                FilledButton(
                  style: FilledButton.styleFrom(minimumSize: const Size(0, 44)),
                  onPressed: ocupado || escuchando ? null : onBuscar,
                  child: Text(ocupado ? 'Buscando…' : 'Buscar'),
                ),
                if (puedeDictar) ...[
                  const SizedBox(width: 8),
                  OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(0, 44),
                    ),
                    onPressed: ocupado ? null : onHablar,
                    icon: Icon(escuchando ? Icons.stop : Icons.mic),
                    label: Text(escuchando ? 'Listo' : 'Hablar'),
                  ),
                ],
              ],
            ),
            if (escuchando) ...[
              const SizedBox(height: 8),
              Text('Escuchando… $loQueOigo', style: theme.textTheme.bodySmall),
            ],
            const SizedBox(height: 12),
            Text(
              'Por ejemplo: «mis últimas 2 facturas», «los pagos de octubre» '
              'o «mis fichas de cardiología».',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}

// --------------------------------------------------------------------------
//  Lo que entendió el sistema
// --------------------------------------------------------------------------
class _LoQueEntendio extends StatelessWidget {
  const _LoQueEntendio({required this.propuesta});

  final PropuestaDeComprobantes propuesta;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          propuesta.entendio
              ? 'Entendí: ${propuesta.resumen}'
              : 'No pude entender tu pedido.',
          style: theme.textTheme.bodyMedium?.copyWith(
            fontWeight: propuesta.entendio ? null : FontWeight.w600,
          ),
        ),
        for (final motivo in propuesta.sinResolver)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text('· $motivo', style: theme.textTheme.bodySmall),
          ),
      ],
    );
  }
}

// --------------------------------------------------------------------------
//  La lista
// --------------------------------------------------------------------------
class _Resultados extends StatelessWidget {
  const _Resultados({
    required this.lista,
    required this.descargando,
    required this.onDescargar,
    required this.onAbrir,
  });

  final ListaDeComprobantes lista;
  final bool descargando;
  final VoidCallback onDescargar;
  final void Function(ComprobanteDeLista item)? onAbrir;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    if (lista.cantidad == 0) {
      return Text(
        'No encontré comprobantes con ese pedido.',
        style: theme.textTheme.bodyMedium,
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                lista.cantidad == 1
                    ? '1 comprobante'
                    : '${lista.cantidad} comprobantes',
                style: theme.textTheme.titleMedium,
              ),
            ),
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(minimumSize: const Size(0, 44)),
              onPressed: descargando ? null : onDescargar,
              icon: const Icon(Icons.picture_as_pdf_outlined),
              label: Text(descargando ? 'Descargando…' : 'Descargar PDF'),
            ),
          ],
        ),
        if (lista.truncada)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Hay más de los que se muestran. Pide menos, por ejemplo «mis '
              'últimas 5 facturas» o un mes.',
              style: theme.textTheme.bodySmall,
            ),
          ),
        const SizedBox(height: 8),
        for (final item in lista.items)
          _TarjetaDeComprobante(item: item, tipo: lista.tipo, onAbrir: onAbrir),
      ],
    );
  }
}

String _dos(int n) => n.toString().padLeft(2, '0');

String _fecha(DateTime? fecha) => fecha == null
    ? ''
    : '${_dos(fecha.day)}/${_dos(fecha.month)}/${fecha.year} '
          '${_dos(fecha.hour)}:${_dos(fecha.minute)}';

const _estados = {'confirmed': 'Confirmada', 'attended': 'Atendida'};

class _TarjetaDeComprobante extends StatelessWidget {
  const _TarjetaDeComprobante({
    required this.item,
    required this.tipo,
    required this.onAbrir,
  });

  final ComprobanteDeLista item;
  final String tipo;
  final void Function(ComprobanteDeLista item)? onAbrir;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final esPago = tipo == 'pagos';
    final detalle = esPago
        ? '${item.moneda == 'BOB' ? 'Bs' : item.moneda ?? ''} '
              '${double.tryParse(item.monto ?? '')?.toStringAsFixed(2) ?? item.monto ?? ''}'
        : _estados[item.estado] ?? item.estado;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onAbrir == null ? null : () => onAbrir!(item),
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      esPago
                          ? 'Pagado el ${_fecha(item.fecha)}'
                          : 'Ficha del ${_fecha(item.fecha)}',
                      style: theme.textTheme.titleSmall,
                    ),
                    if (esPago)
                      Text(
                        'Ficha del ${_fecha(item.inicio)}',
                        style: theme.textTheme.bodySmall,
                      ),
                    const SizedBox(height: 6),
                    Text(
                      item.esDependiente
                          ? '${item.paciente} (dependiente)'
                          : item.paciente,
                      style: theme.textTheme.bodyMedium,
                    ),
                    Text(
                      [
                        item.profesional,
                        ...item.especialidades,
                      ].where((e) => e.isNotEmpty).join(' · '),
                      style: theme.textTheme.bodySmall,
                    ),
                    Text(item.sucursal, style: theme.textTheme.bodySmall),
                    const SizedBox(height: 6),
                    Text(
                      detalle,
                      style: theme.textTheme.bodyMedium?.copyWith(
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              // Fondo blanco fijo: un QR sobre el fondo oscuro del tema no se
              // lee.
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: QrImageView(
                  // La clave lleva el código: es lo que permite comprobar en las
                  // pruebas que se dibuja el que mandó el servidor.
                  key: ValueKey('qr-${item.code}'),
                  data: item.code,
                  size: 110,
                  backgroundColor: Colors.white,
                  semanticsLabel:
                      'Código QR del comprobante de ${item.paciente}, '
                      '${_fecha(item.inicio)}',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
