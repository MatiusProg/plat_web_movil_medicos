// El centro médico del login y del registro, elegido de una lista (21/11/26).
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/auth/centro_selector.dart';

const _tres = [
  Centro(slug: 'andina', name: 'Andina'),
  Centro(slug: 'sangabriel', name: 'Clínica San Gabriel'),
  Centro(slug: 'sur', name: 'Policlínico Sur'),
];

class _Prueba extends StatefulWidget {
  const _Prueba({required this.cargar, this.inicial, this.conPlataforma = false});
  final Future<List<Centro>> Function() cargar;
  final String? inicial;
  final bool conPlataforma;
  @override
  State<_Prueba> createState() => _PruebaState();
}

class _PruebaState extends State<_Prueba> {
  late String? valor = widget.inicial;
  final cambios = <String?>[];
  @override
  Widget build(BuildContext context) => MaterialApp(
        home: Scaffold(
          body: Padding(
            padding: const EdgeInsets.all(16),
            child: SelectorCentro(
              cargar: widget.cargar,
              valor: valor,
              conPlataforma: widget.conPlataforma,
              onCambio: (v) => setState(() {
                cambios.add(v);
                valor = v;
              }),
            ),
          ),
        ),
      );
}

Future<_PruebaState> _abrir(WidgetTester tester, Widget w) async {
  await tester.pumpWidget(w);
  await tester.pumpAndSettle();
  return tester.state<_PruebaState>(find.byType(_Prueba));
}

void main() {
  testWidgets('se elige de la lista y queda el nombre a la vista', (tester) async {
    final s = await _abrir(tester, _Prueba(cargar: () async => _tres));
    expect(find.text('Elige tu centro médico'), findsOneWidget);

    await tester.tap(find.byType(SelectorCentro));
    await tester.pumpAndSettle();
    expect(find.text('Andina'), findsOneWidget);
    expect(find.text('Policlínico Sur'), findsOneWidget);
    // Sin la opción de la plataforma fuera del login.
    expect(find.text(SelectorCentro.plataforma), findsNothing);

    await tester.tap(find.text('Clínica San Gabriel'));
    await tester.pumpAndSettle();
    expect(s.valor, 'sangabriel');
    expect(find.text('Clínica San Gabriel'), findsOneWidget);
  });

  testWidgets('en el login, la plataforma es el slug vacío', (tester) async {
    final s = await _abrir(
        tester, _Prueba(cargar: () async => _tres, conPlataforma: true));
    await tester.tap(find.byType(SelectorCentro));
    await tester.pumpAndSettle();
    // En una pantalla chica queda al final de la hoja: hay que bajar.
    await tester.ensureVisible(find.text(SelectorCentro.plataforma));
    await tester.pumpAndSettle();
    await tester.tap(find.text(SelectorCentro.plataforma));
    await tester.pumpAndSettle();
    expect(s.valor, '');
    expect(find.text(SelectorCentro.plataforma), findsOneWidget);
  });

  testWidgets('el último centro usado aparece elegido', (tester) async {
    final s = await _abrir(
        tester, _Prueba(cargar: () async => _tres, inicial: 'sur'));
    expect(find.text('Policlínico Sur'), findsOneWidget);
    expect(s.cambios, isEmpty);
  });

  testWidgets('si el último centro se dio de baja, no queda elegido',
      (tester) async {
    final s = await _abrir(
        tester, _Prueba(cargar: () async => _tres, inicial: 'cerrada'));
    expect(s.cambios, [null]);
    expect(find.text('Elige tu centro médico'), findsOneWidget);
  });

  testWidgets('sin la lista vuelve el campo para escribir el código',
      (tester) async {
    final s = await _abrir(tester,
        _Prueba(cargar: () async => throw Exception('sin red'), conPlataforma: true));
    expect(find.byType(TextFormField), findsOneWidget);
    await tester.enterText(find.byType(TextFormField), 'kolping');
    expect(s.valor, 'kolping');
  });

  testWidgets('con muchos centros hay buscador, y no distingue tildes',
      (tester) async {
    final muchos = [
      for (final n in ['Uno', 'Dos', 'Tres', 'Cuatro', 'Cinco', 'Seis'])
        Centro(slug: n.toLowerCase(), name: 'Centro $n'),
      const Centro(slug: 'sanjose', name: 'Clínica San José'),
    ];
    await _abrir(tester, _Prueba(cargar: () async => muchos));
    await tester.tap(find.byType(SelectorCentro));
    await tester.pumpAndSettle();
    await tester.enterText(find.widgetWithText(TextField, 'Buscar por nombre'), 'clinica jose');
    await tester.pumpAndSettle();
    expect(find.text('Ningún centro coincide con la búsqueda.'), findsOneWidget);
    await tester.enterText(find.widgetWithText(TextField, 'Buscar por nombre'), 'josé');
    await tester.pumpAndSettle();
    expect(find.text('Clínica San José'), findsOneWidget);
    expect(find.text('Centro Uno'), findsNothing);
  });

  test('lee la lista del backend, sin sesión', () async {
    late http.Request pedido;
    final client = ApiClient(
      httpClient: MockClient((r) async {
        pedido = r;
        return http.Response(
          jsonEncode([
            {'slug': 'andina', 'name': 'Andina'},
          ]),
          200,
          headers: {'content-type': 'application/json'},
        );
      }),
    );
    final centros = await listarCentros(client);
    expect(pedido.url.path, endsWith('/accounts/centers/'));
    expect(pedido.headers.containsKey('Authorization'), isFalse);
    expect([for (final c in centros) c.name], ['Andina']);
  });
}
