/// US-46 — Mis comprobantes, pedidos hablando o escribiendo, en el móvil.
///
///     flutter test test/my_receipts_voz_test.dart
///
/// El micrófono no se prueba: en el entorno de pruebas no hay reconocedor, así
/// que el dictado se inyecta ya transcrito con [_DictadoFalso]. Lo que se
/// prueba es lo que importa del lado del teléfono:
///
/// - que lo entendido se muestre **antes** de la lista, y que lo que el backend
///   no pudo resolver se vea y no traiga una lista;
/// - que cada comprobante dibuje el QR con el código que mandó el servidor;
/// - que viaje texto y no audio, y que el nombre de la especialidad no vaya al
///   listado;
/// - que sin reconocimiento disponible escribir siga alcanzando.
///
/// Qué se entiende de cada frase, y que nadie vea lo de otro, se prueba en el
/// backend (`tests/test_us46.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:qr_flutter/qr_flutter.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/files/archivos.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/receipts/my_receipts_api.dart';
import 'package:mobile/features/receipts/my_receipts_screen.dart';
import 'package:mobile/features/reporting/voice_input.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

const _propuesta = {
  'understood': true,
  'consulta': {
    'tipo': 'pagos',
    'cantidad': 2,
    'desde': null,
    'hasta': null,
    'especialidad': 'id-cardio',
    'especialidad_nombre': 'Cardiología',
  },
  'spoken_summary': 'Pagos con comprobante · últimos 2',
  'unresolved': <String>[],
  'generated_by': 'plantilla',
};

Map<String, dynamic> _propuestaAgrupada(String por) => {
  'understood': true,
  'consulta': {
    'tipo': 'pagos',
    'cantidad': null,
    'desde': '2026-08-16',
    'hasta': '2026-11-16',
    'especialidad': null,
    'especialidad_nombre': null,
    'agrupar': por,
  },
  'spoken_summary':
      'Pagos con comprobante · desde el 16/08/2026 hasta el 16/11/2026 · '
      'agrupados por $por',
  'unresolved': <String>[],
  'generated_by': 'plantilla',
};

Map<String, dynamic> _grupo(
  String etiqueta,
  List<Map<String, dynamic>> items, {
  String total = '0.00',
}) => {
  'key': etiqueta,
  'label': etiqueta,
  'count': items.length,
  'totals': [
    {'currency': 'BOB', 'amount': total},
  ],
  'items': items,
};

Map<String, dynamic> _item({
  String id = 'p1',
  String code = 'MC1.AAAA',
  String paciente = 'Ana Ríos',
  bool dependiente = false,
  String monto = '80.00',
}) => {
  'id': id,
  'appointment_id': 'ficha-$id',
  'code': code,
  'date': '2026-10-12T15:00:00Z',
  'starts_at': '2026-10-13T14:00:00Z',
  'patient_name': paciente,
  'is_dependent': dependiente,
  'practitioner_name': 'Laura Gómez',
  'specialties': ['Cardiología'],
  'branch_name': 'Sede Centro',
  'status': 'confirmed',
  'amount': monto,
  'currency': 'BOB',
  'provider': 'simulated',
  'paid_at': '2026-10-12T15:00:00Z',
};

Map<String, dynamic> _lista(
  List<Map<String, dynamic>> items, {
  List<Map<String, dynamic>> grupos = const [],
}) => {
  'tipo': 'pagos',
  'count': items.length,
  'limit': 20,
  'truncated': false,
  'summary': 'Pagos con comprobante',
  'groups': grupos,
  'items': items,
};

/// Un dictado que no toca el micrófono: entrega el texto que se le dio.
class _DictadoFalso implements DictadoDeVoz {
  _DictadoFalso({required this.texto, this.disponible = true});

  final String texto;
  final bool disponible;
  bool soltado = false;

  @override
  Future<bool> preparar() async => disponible;

  @override
  String get motivo => disponible ? '' : 'Este teléfono no puede dictar.';

  @override
  bool get escuchando => false;

  @override
  Future<void> empezar({
    required void Function(String texto) alCambiar,
    required void Function(String texto) alTerminar,
  }) async {
    alCambiar(texto.split(' ').first);
    alTerminar(texto);
  }

  @override
  Future<void> terminar() async {}

  @override
  void soltar() => soltado = true;
}

class _GuardadoFalso implements GuardadoDeArchivos {
  final guardados = <String, List<int>>{};

  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    guardados[nombre] = bytes;
    return '/descargas/$nombre';
  }
}

class _AbridorFalso implements AbridorDeArchivos {
  String? abierto;

  @override
  Future<String?> abrir(String ruta) async {
    abierto = ruta;
    return null;
  }
}

/// El backend simulado: lo que se pidió queda registrado para inspeccionarlo.
class _Servidor {
  _Servidor({
    this.interpretacion = _propuesta,
    List<Map<String, dynamic>>? items,
    this.errorAlInterpretar,
    this.grupos = const [],
  }) : items = items ?? [_item(), _item(id: 'p2', code: 'MC1.BBBB')];

  final List<Map<String, dynamic>> grupos;

  final Map<String, dynamic> interpretacion;
  final List<Map<String, dynamic>> items;
  final http.Response? errorAlInterpretar;

  final textos = <String>[];
  final listados = <Uri>[];

  MockClient get cliente => MockClient((req) async {
    if (req.url.path.endsWith('/mine/receipts/interpret/')) {
      textos.add(
        (jsonDecode(req.body) as Map<String, dynamic>)['text'] as String,
      );
      return errorAlInterpretar ?? _json(interpretacion, 200);
    }
    listados.add(req.url);
    if (req.url.queryParameters['formato'] == 'pdf') {
      return http.Response.bytes(
        [0x25, 0x50, 0x44, 0x46],
        200,
        headers: {
          'content-type': 'application/pdf',
          'content-disposition':
              'attachment; filename="mis-comprobantes-de-pagos.pdf"',
        },
      );
    }
    return _json(_lista(items, grupos: grupos), 200);
  });
}

Future<void> _abrir(
  WidgetTester tester,
  _Servidor servidor, {
  DictadoDeVoz? dictado,
  GuardadoDeArchivos? guardado,
  AbridorDeArchivos? abridor,
  void Function(ComprobanteDeLista item)? onAbrir,
}) async {
  tester.view.physicalSize = const Size(1200, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      // Con el tema de la aplicación y no con el de Material por omisión: el
      // tema propio da a los botones ancho completo (`Size.fromHeight`) y un
      // botón así dentro de una fila deja la pantalla en blanco. Con el tema
      // por omisión la prueba pasaba y el teléfono no mostraba nada.
      theme: AppTheme.light,
      home: MyReceiptsScreen(
        client: ApiClient(httpClient: servidor.cliente),
        dictado: dictado ?? _DictadoFalso(texto: '', disponible: false),
        guardado: guardado,
        abridor: abridor,
        onAbrir: onAbrir,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

Future<void> _escribirYBuscar(WidgetTester tester, String frase) async {
  await tester.enterText(find.byType(TextField), frase);
  await tester.tap(find.widgetWithText(FilledButton, 'Buscar'));
  await tester.pumpAndSettle();
}

/// Los códigos de los QR dibujados, en orden. `QrImageView` no expone su dato:
/// la pantalla le pone una clave `qr-<código>` justamente para esto.
List<String> _codigosDeQr(WidgetTester tester) => [
  for (final qr in tester.widgetList<QrImageView>(find.byType(QrImageView)))
    (qr.key! as ValueKey<String>).value.substring('qr-'.length),
];

void main() {
  testWidgets('escribir una frase muestra lo entendido y el QR de cada uno', (
    tester,
  ) async {
    await _abrir(tester, _Servidor());

    await _escribirYBuscar(tester, 'mis últimas 2 facturas');

    expect(
      find.text('Entendí: Pagos con comprobante · últimos 2'),
      findsOneWidget,
    );
    expect(find.text('2 comprobantes'), findsOneWidget);
    // Un QR por comprobante, con el código exacto que mandó el servidor.
    expect(_codigosDeQr(tester), ['MC1.AAAA', 'MC1.BBBB']);
    expect(find.text('Bs 80.00'), findsNWidgets(2));
    expect(find.textContaining('Pagado el'), findsNWidgets(2));
    expect(find.text('Laura Gómez · Cardiología'), findsNWidgets(2));
  });

  testWidgets(
    'viaja el texto y la consulta, sin el nombre de la especialidad',
    (tester) async {
      final servidor = _Servidor();
      await _abrir(tester, servidor);

      await _escribirYBuscar(tester, 'mis últimas 2 facturas de cardiología');

      expect(servidor.textos, ['mis últimas 2 facturas de cardiología']);
      final pedido = servidor.listados.single.queryParameters;
      expect(pedido, {
        'tipo': 'pagos',
        'cantidad': '2',
        'especialidad': 'id-cardio',
        'formato': 'json',
      });
      expect(pedido.containsKey('especialidad_nombre'), isFalse);
    },
  );

  testWidgets('dictar dispara la consulta sin tocar «Buscar»', (tester) async {
    final servidor = _Servidor();
    final dictado = _DictadoFalso(texto: 'los pagos de octubre');
    await _abrir(tester, servidor, dictado: dictado);

    await tester.tap(find.widgetWithText(OutlinedButton, 'Hablar'));
    await tester.pumpAndSettle();

    // Viajó el texto, no audio, y quedó en la caja para poder corregirlo.
    expect(servidor.textos, ['los pagos de octubre']);
    expect(find.text('los pagos de octubre'), findsOneWidget);
    expect(_codigosDeQr(tester), hasLength(2));
  });

  testWidgets('si no entendió, dice por qué y no pide la lista', (
    tester,
  ) async {
    final servidor = _Servidor(
      interpretacion: const {
        'understood': false,
        'consulta': null,
        'spoken_summary': '',
        'unresolved': [
          'Solo se muestran los pagos y las fichas con comprobante.',
        ],
        'generated_by': 'plantilla',
      },
    );
    await _abrir(tester, servidor);

    await _escribirYBuscar(tester, 'mis pagos devueltos');

    expect(find.text('No pude entender tu pedido.'), findsOneWidget);
    expect(
      find.textContaining('Solo se muestran los pagos y las fichas'),
      findsOneWidget,
    );
    // No hubo segunda petición ni nada que se pueda leer como resultado.
    expect(servidor.listados, isEmpty);
    expect(find.byType(QrImageView), findsNothing);
  });

  testWidgets('sin comprobantes lo dice en vez de dejar la pantalla vacía', (
    tester,
  ) async {
    await _abrir(tester, _Servidor(items: const []));

    await _escribirYBuscar(tester, 'mis últimas 2 facturas');

    expect(
      find.text('No encontré comprobantes con ese pedido.'),
      findsOneWidget,
    );
    expect(find.byType(QrImageView), findsNothing);
  });

  testWidgets('un dependiente se ve como tal', (tester) async {
    await _abrir(
      tester,
      _Servidor(
        items: [
          _item(),
          _item(
            id: 'p2',
            code: 'MC1.BBBB',
            paciente: 'Tito Ríos',
            dependiente: true,
          ),
        ],
      ),
    );

    await _escribirYBuscar(tester, 'mis últimas 2 facturas');

    expect(find.text('Ana Ríos'), findsOneWidget);
    expect(find.text('Tito Ríos (dependiente)'), findsOneWidget);
  });

  testWidgets(
    'sin reconocimiento no aparece «Hablar» y escribir sigue sirviendo',
    (tester) async {
      await _abrir(tester, _Servidor());

      expect(find.widgetWithText(OutlinedButton, 'Hablar'), findsNothing);

      await _escribirYBuscar(tester, 'mis últimas 2 facturas');
      expect(_codigosDeQr(tester), hasLength(2));
    },
  );

  testWidgets(
    'el error del backend se muestra y no deja la pantalla en blanco',
    (tester) async {
      await _abrir(
        tester,
        _Servidor(
          errorAlInterpretar: _json({
            'code': 'sin_perfil_de_paciente',
            'detail': 'Esta consulta es para pacientes con perfil activo.',
          }, 403),
        ),
      );

      await _escribirYBuscar(tester, 'mis últimas 2 facturas');

      expect(
        find.text('Esta consulta es para pacientes con perfil activo.'),
        findsOneWidget,
      );
      expect(find.widgetWithText(FilledButton, 'Buscar'), findsOneWidget);
    },
  );

  testWidgets('descargar el PDF baja el mismo pedido y lo guarda', (
    tester,
  ) async {
    final servidor = _Servidor();
    final guardado = _GuardadoFalso();
    final abridor = _AbridorFalso();
    await _abrir(tester, servidor, guardado: guardado, abridor: abridor);
    await _escribirYBuscar(tester, 'mis últimas 2 facturas');

    await tester.tap(find.widgetWithText(OutlinedButton, 'Descargar PDF'));
    await tester.pumpAndSettle();

    final pedido = servidor.listados.last.queryParameters;
    expect(pedido['formato'], 'pdf');
    expect(pedido['tipo'], 'pagos');
    expect(pedido['cantidad'], '2');
    // Se guarda con fecha en el nombre, para no confundir una descarga con otra.
    final nombre = guardado.guardados.keys.single;
    expect(nombre, startsWith('mis-comprobantes-de-pagos-'));
    expect(nombre, endsWith('.pdf'));
    expect(guardado.guardados[nombre], [0x25, 0x50, 0x44, 0x46]);
    expect(find.textContaining('Descargado en Descargas'), findsOneWidget);

    await tester.tap(find.text('Abrir'));
    await tester.pumpAndSettle();
    expect(abridor.abierto, '/descargas/$nombre');
  });

  testWidgets('tocar un comprobante lo abre en grande', (tester) async {
    ComprobanteDeLista? abierto;
    await _abrir(tester, _Servidor(), onAbrir: (item) => abierto = item);
    await _escribirYBuscar(tester, 'mis últimas 2 facturas');

    // Sin fijar la hora: `toLocal` depende de la zona de la máquina.
    await tester.tap(find.textContaining('Pagado el').first);
    await tester.pumpAndSettle();

    expect(abierto?.appointmentId, 'ficha-p1');
    expect(abierto?.code, 'MC1.AAAA');
  });

  testWidgets('la consulta se arma con los parámetros que el backend espera', (
    tester,
  ) async {
    const consulta = ConsultaDeComprobantes(
      tipo: 'fichas',
      cantidad: 3,
      desde: '2026-10-01',
      hasta: '2026-10-31',
      especialidad: 'id-cardio',
      especialidadNombre: 'Cardiología',
      agrupar: 'sucursal',
    );

    final partes = Uri.splitQueryString(consulta.parametros('pdf'));

    expect(partes, {
      'tipo': 'fichas',
      'formato': 'pdf',
      'cantidad': '3',
      'desde': '2026-10-01',
      'hasta': '2026-10-31',
      'especialidad': 'id-cardio',
      'agrupar': 'sucursal',
    });
  });

  testWidgets('agrupada, cada sección dice cuántos tiene y cuánto suma', (
    tester,
  ) async {
    final a = _item(id: 'a', code: 'MC1.AAAA', monto: '100.00');
    final b = _item(id: 'b', code: 'MC1.BBBB', monto: '50.00');
    final c = _item(id: 'c', code: 'MC1.CCCC', monto: '80.00');
    final servidor = _Servidor(
      interpretacion: _propuestaAgrupada('sucursal'),
      items: [a, b, c],
      grupos: [
        _grupo('Sede Centro', [a, c], total: '180.00'),
        _grupo('Sede Norte', [b], total: '50.00'),
      ],
    );
    await _abrir(tester, servidor);

    await _escribirYBuscar(
      tester,
      'mis facturas de los últimos 3 meses agrupadas por sucursal',
    );

    // Lo entendido incluye cómo se agrupa, y la consulta viaja con ello.
    expect(find.textContaining('agrupados por sucursal'), findsOneWidget);
    expect(servidor.listados.single.queryParameters['agrupar'], 'sucursal');
    expect(servidor.listados.single.queryParameters['desde'], '2026-08-16');
    // Una sección por sucursal, con su cuenta y su total. El nombre también
    // sale en cada tarjeta, así que lo que identifica a la sección es su
    // resumen, que es único.
    expect(find.text('2 comprobantes · Bs 180.00'), findsOneWidget);
    expect(find.text('1 comprobante · Bs 50.00'), findsOneWidget);
    expect(find.byType(Divider), findsNWidgets(2));
    // Las secciones van en el orden que mandó el backend.
    expect(
      tester.getTopLeft(find.text('2 comprobantes · Bs 180.00')).dy,
      lessThan(tester.getTopLeft(find.text('1 comprobante · Bs 50.00')).dy),
    );
    // Y los QR de todos, en el orden de los grupos.
    expect(_codigosDeQr(tester), ['MC1.AAAA', 'MC1.CCCC', 'MC1.BBBB']);
  });

  testWidgets('sin pedir agrupar no hay secciones', (tester) async {
    await _abrir(tester, _Servidor());

    await _escribirYBuscar(tester, 'mis últimas 2 facturas');

    // Ni encabezados con totales ni separadores entre secciones.
    expect(find.byType(Divider), findsNothing);
    expect(find.textContaining('Bs 180'), findsNothing);
    expect(_codigosDeQr(tester), hasLength(2));
  });
}
