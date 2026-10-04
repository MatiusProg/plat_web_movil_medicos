/// Pruebas de los ayudantes de paginación (`core/api/paginacion.dart`).
///
///     flutter test test/paginacion_test.dart
library;

import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/paginacion.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

/// Simula el `PageNumberPagination` del backend sobre [filas], de a [tamano].
MockClient _backendPaginado(
  List<Map<String, dynamic>> filas, {
  int tamano = 25,
  List<Uri>? pedidas,
}) => MockClient((req) async {
  pedidas?.add(req.url);
  final pagina = int.parse(req.url.queryParameters['page'] ?? '1');
  final desde = (pagina - 1) * tamano;
  final hasta = (desde + tamano).clamp(0, filas.length);
  return _json({
    'count': filas.length,
    // URL absoluta y con otro host, como la arma el backend detrás del
    // proxy: el ayudante no debe seguirla.
    'next': hasta < filas.length
        ? 'http://interno:8000${req.url.path}?page=${pagina + 1}'
        : null,
    'previous': null,
    'results': filas.sublist(desde, hasta),
  }, 200);
});

List<Map<String, dynamic>> _filas(int n) => [
  for (var i = 1; i <= n; i++) {'id': i},
];

int _id(Map<String, dynamic> json) => json['id'] as int;

void main() {
  group('rutaDePagina', () {
    test('la primera página no lleva el parámetro', () {
      expect(rutaDePagina('/x/', 1), '/x/');
    });

    test('respeta los parámetros que ya tiene la ruta', () {
      expect(rutaDePagina('/x/', 3), '/x/?page=3');
      expect(rutaDePagina('/x/?user=u1', 2), '/x/?user=u1&page=2');
    });
  });

  group('todasLasPaginas', () {
    test('junta las 80 filas de 4 páginas, en orden', () async {
      final pedidas = <Uri>[];
      final client = ApiClient(
        httpClient: _backendPaginado(_filas(80), pedidas: pedidas),
      );

      final ids = await todasLasPaginas(client, '/accounts/users/', _id);

      expect(ids, [for (var i = 1; i <= 80; i++) i]);
      expect(pedidas, hasLength(4));
      // Siempre contra la base del cliente, nunca contra el host de `next`.
      expect(pedidas.every((u) => u.host != 'interno'), isTrue);
      expect(pedidas.last.queryParameters['page'], '4');
    });

    test('conserva los filtros de la ruta en cada página', () async {
      final pedidas = <Uri>[];
      final client = ApiClient(
        httpClient: _backendPaginado(_filas(30), pedidas: pedidas),
      );

      await todasLasPaginas(client, '/accounts/user-roles/?user=u1', _id);

      expect(pedidas.map((u) => u.queryParameters['user']), ['u1', 'u1']);
    });

    test('acepta un endpoint sin paginar, que contesta una lista', () async {
      final client = ApiClient(
        httpClient: MockClient((_) async => _json(_filas(3), 200)),
      );

      expect(await todasLasPaginas(client, '/x/', _id), [1, 2, 3]);
    });

    test('no se queda pidiendo para siempre si `next` nunca es nulo', () async {
      var llamadas = 0;
      final client = ApiClient(
        httpClient: MockClient((_) async {
          llamadas++;
          return _json({
            'count': 1,
            'next': 'otra',
            'previous': null,
            'results': [
              {'id': 1},
            ],
          }, 200);
        }),
      );

      await todasLasPaginas(client, '/x/', _id);

      expect(llamadas, maximoDePaginas);
    });
  });

  group('unaPagina', () {
    test('devuelve las filas, si hay más y el total', () async {
      final client = ApiClient(httpClient: _backendPaginado(_filas(60)));

      final segunda = await unaPagina(client, '/x/', _id, page: 2);
      final tercera = await unaPagina(client, '/x/', _id, page: 3);

      expect(segunda.results.first, 26);
      expect(segunda.hayMas, isTrue);
      expect(segunda.total, 60);
      expect(tercera.results, hasLength(10));
      expect(tercera.hayMas, isFalse);
    });
  });
}
