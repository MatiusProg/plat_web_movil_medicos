/// US-46 — Mis comprobantes, pedidos hablando o escribiendo.
///
///     POST /api/payments/mine/receipts/interpret/   de la frase a la consulta
///     GET  /api/payments/mine/receipts/             la lista, o el PDF con los QR
///
/// Dos pasos, como el reporte por voz: [interpretarComprobantes] **propone**
/// una consulta y no devuelve datos; la persona la ve y recién ahí se pide la
/// lista con [listarComprobantes]. La consulta no dice de quién son los datos:
/// eso lo decide la sesión en el backend (el paciente y sus dependientes), así
/// que no hay un campo para pedir los de otra persona.
///
/// El QR de cada ítem es el [ComprobanteDeLista.code] firmado por el servidor,
/// el mismo de la ficha (US-19). El móvil lo dibuja; no lo genera ni lo valida.
library;

import 'package:mobile/core/api/client.dart';

/// Lo que entendió el sistema. Se manda tal cual al listado.
class ConsultaDeComprobantes {
  const ConsultaDeComprobantes({
    required this.tipo,
    this.cantidad,
    this.desde,
    this.hasta,
    this.especialidad,
    this.especialidadNombre,
  });

  /// `pagos` o `fichas`.
  final String tipo;
  final int? cantidad;

  /// `AAAA-MM-DD`.
  final String? desde;
  final String? hasta;

  /// El id de la especialidad del centro.
  final String? especialidad;

  /// Solo para mostrarla; no viaja al listado.
  final String? especialidadNombre;

  factory ConsultaDeComprobantes.fromJson(Map<String, dynamic> json) =>
      ConsultaDeComprobantes(
        tipo: json['tipo'] as String? ?? 'pagos',
        cantidad: json['cantidad'] as int?,
        desde: json['desde'] as String?,
        hasta: json['hasta'] as String?,
        especialidad: json['especialidad'] as String?,
        especialidadNombre: json['especialidad_nombre'] as String?,
      );

  /// Los parámetros de la URL. El nombre es `formato` y no `format`: DRF
  /// reserva `?format=` para elegir el renderizador y respondería 404.
  String parametros(String formato) {
    final partes = <String, String>{'tipo': tipo, 'formato': formato};
    if (cantidad != null) partes['cantidad'] = '$cantidad';
    if (desde != null) partes['desde'] = desde!;
    if (hasta != null) partes['hasta'] = hasta!;
    if (especialidad != null) partes['especialidad'] = especialidad!;
    return Uri(queryParameters: partes).query;
  }
}

class PropuestaDeComprobantes {
  const PropuestaDeComprobantes({
    required this.entendio,
    required this.consulta,
    required this.resumen,
    required this.sinResolver,
    required this.generadoPor,
  });

  final bool entendio;
  final ConsultaDeComprobantes? consulta;

  /// La consulta en palabras, armada por el backend.
  final String resumen;

  /// Lo que se pidió y no se pudo resolver, o avisos.
  final List<String> sinResolver;
  final String generadoPor;

  factory PropuestaDeComprobantes.fromJson(Map<String, dynamic> json) {
    final consulta = json['consulta'];
    return PropuestaDeComprobantes(
      entendio: json['understood'] == true,
      consulta: consulta is Map<String, dynamic>
          ? ConsultaDeComprobantes.fromJson(consulta)
          : null,
      resumen: json['spoken_summary'] as String? ?? '',
      sinResolver: [
        for (final item in (json['unresolved'] as List<dynamic>? ?? const []))
          '$item',
      ],
      generadoPor: json['generated_by'] as String? ?? 'plantilla',
    );
  }
}

class ComprobanteDeLista {
  const ComprobanteDeLista({
    required this.id,
    required this.appointmentId,
    required this.code,
    required this.fecha,
    required this.inicio,
    required this.paciente,
    required this.esDependiente,
    required this.profesional,
    required this.especialidades,
    required this.sucursal,
    required this.estado,
    this.monto,
    this.moneda,
  });

  /// El id del pago o de la ficha, según el tipo.
  final String id;
  final String appointmentId;

  /// El contenido del QR.
  final String code;

  /// Cuándo se pagó (pagos) o cuándo es la ficha (fichas).
  final DateTime? fecha;
  final DateTime? inicio;
  final String paciente;
  final bool esDependiente;
  final String profesional;
  final List<String> especialidades;
  final String sucursal;
  final String estado;

  /// Solo en los pagos.
  final String? monto;
  final String? moneda;

  static DateTime? _fecha(Object? valor) =>
      valor is String ? DateTime.tryParse(valor)?.toLocal() : null;

  factory ComprobanteDeLista.fromJson(Map<String, dynamic> json) =>
      ComprobanteDeLista(
        id: '${json['id'] ?? ''}',
        appointmentId: '${json['appointment_id'] ?? ''}',
        code: json['code'] as String? ?? '',
        fecha: _fecha(json['date']),
        inicio: _fecha(json['starts_at']),
        paciente: json['patient_name'] as String? ?? '',
        esDependiente: json['is_dependent'] == true,
        profesional: json['practitioner_name'] as String? ?? '',
        especialidades: [
          for (final e in (json['specialties'] as List<dynamic>? ?? const []))
            '$e',
        ],
        sucursal: json['branch_name'] as String? ?? '',
        estado: json['status'] as String? ?? '',
        monto: json['amount'] as String?,
        moneda: json['currency'] as String?,
      );
}

class ListaDeComprobantes {
  const ListaDeComprobantes({
    required this.tipo,
    required this.cantidad,
    required this.truncada,
    required this.items,
  });

  final String tipo;
  final int cantidad;

  /// Había más de lo pedido.
  final bool truncada;
  final List<ComprobanteDeLista> items;

  factory ListaDeComprobantes.fromJson(Map<String, dynamic> json) =>
      ListaDeComprobantes(
        tipo: json['tipo'] as String? ?? 'pagos',
        cantidad: json['count'] as int? ?? 0,
        truncada: json['truncated'] == true,
        items: [
          for (final item in (json['items'] as List<dynamic>? ?? const []))
            if (item is Map<String, dynamic>) ComprobanteDeLista.fromJson(item),
        ],
      );
}

const _ruta = '/payments/mine/receipts/';

Map<String, dynamic> _mapa(Object? datos) =>
    datos is Map<String, dynamic> ? datos : const <String, dynamic>{};

Future<PropuestaDeComprobantes> interpretarComprobantes(
  ApiClient client,
  String texto,
) async => PropuestaDeComprobantes.fromJson(
  _mapa(await client.post('${_ruta}interpret/', body: {'text': texto})),
);

Future<ListaDeComprobantes> listarComprobantes(
  ApiClient client,
  ConsultaDeComprobantes consulta,
) async => ListaDeComprobantes.fromJson(
  _mapa(await client.get('$_ruta?${consulta.parametros('json')}')),
);

/// El PDF con los QR, tal como lo armó el servidor.
Future<ArchivoRecibido> descargarComprobantesPdf(
  ApiClient client,
  ConsultaDeComprobantes consulta,
) => client.download('GET', '$_ruta?${consulta.parametros('pdf')}');
