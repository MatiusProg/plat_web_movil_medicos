/// Pruebas de US-16 — búsqueda de profesionales (móvil).
///
///     flutter test test/search_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/search/search_api.dart';
import 'package:mobile/features/search/search_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

Map<String, dynamic> _pagina(List<Map<String, dynamic>> results,
        {String? next}) =>
    {'count': results.length, 'next': next, 'previous': null, 'results': results};

Map<String, dynamic> _tarjeta(String id, String nombre, {String? slot}) => {
      'id': id,
      'full_name': nombre,
      'specialties': [
        {'id': 's1', 'name': 'Cardiología'},
      ],
      'branches': [
        {'id': 'b1', 'name': 'Sede Centro'},
      ],
      'next_available_slot': slot,
    };

void main() {
  group('buscarProfesionales', () {
    test('sin filtros pega al catálogo completo', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_pagina([_tarjeta('p1', 'Marta González')]), 200);
      });

      final pagina = await buscarProfesionales(ApiClient(httpClient: mock));

      expect(capturada!.url.path, '/api/catalog/professionals/');
      expect(capturada!.url.hasQuery, isFalse);
      expect(pagina.results.single.fullName, 'Marta González');
      expect(pagina.hayMas, isFalse);
    });

    test('incluye q, specialty y page cuando vienen', () async {
      http.Request? capturada;
      final mock = MockClient((req) async {
        capturada = req;
        return _json(_pagina([], next: null), 200);
      });

      await buscarProfesionales(
        ApiClient(httpClient: mock),
        q: 'gonzalez',
        specialtyId: 's1',
        page: 2,
      );

      expect(capturada!.url.queryParameters, {
        'q': 'gonzalez',
        'specialty': 's1',
        'page': '2',
      });
    });

    test('next no nulo marca que hay más páginas', () async {
      final mock = MockClient(
        (req) async => _json(
          _pagina([_tarjeta('p1', 'A')], next: 'http://x/?page=2'),
          200,
        ),
      );
      final pagina = await buscarProfesionales(ApiClient(httpClient: mock));
      expect(pagina.hayMas, isTrue);
    });
  });

  testWidgets('la pantalla lista resultados y su próximo espacio',
      (tester) async {
    tester.view.physicalSize = const Size(1200, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final mock = MockClient(
      (req) async => _json(
        _pagina([
          _tarjeta('p1', 'Marta González',
              slot: '2026-09-10T09:00:00-04:00'),
          _tarjeta('p2', 'Juan Pérez'),
        ]),
        200,
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: SearchScreen(client: ApiClient(httpClient: mock)),
      ),
    );
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Marta González'), findsOneWidget);
    expect(find.text('Juan Pérez'), findsOneWidget);
    expect(find.textContaining('Próximo: 10/09 09:00'), findsOneWidget);
    expect(find.text('Sin agenda cargada'), findsOneWidget);
  });
}
