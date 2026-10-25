/// Pruebas de US-25 en el móvil — la historia clínica vista por el paciente.
///
///     flutter test test/clinical_record_test.dart
///
/// Lo que se prueba acá es la pantalla: que muestre la línea de tiempo con
/// sus enmiendas, que el filtro por sucursal funcione y que cambiar de
/// persona traiga la historia de esa persona. US-27: que muestre la receta
/// y las órdenes y que la receta se baje a Descargas. Quién puede leer la historia de
/// quién se prueba en el backend (`tests/test_us25.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/files/archivos.dart';
import 'package:mobile/features/clinical_record/clinical_record_screen.dart';

http.Response _json(Object cuerpo) => http.Response(
      jsonEncode(cuerpo),
      200,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

const _opciones = [
  {
    'id': 't1',
    'full_name': 'Ana Ríos',
    'relationship': '',
    'relationship_label': 'Yo',
    'is_self': true,
    'birth_date': '1990-05-20',
  },
  {
    'id': 'd1',
    'full_name': 'Mateo Ríos',
    'relationship': 'child',
    'relationship_label': 'Hijo/a',
    'is_self': false,
    'birth_date': '2020-03-15',
  },
];

Map<String, dynamic> _atencion(
  String id,
  String sucursal,
  String diagnostico, {
  List<Map<String, dynamic>> enmiendas = const [],
  List<Map<String, dynamic>> medicamentos = const [],
  List<Map<String, dynamic>> ordenes = const [],
}) =>
    {
      'id': id,
      'status': 'signed',
      'appointment_starts_at': '2026-09-20T14:00:00Z',
      'practitioner_name': 'Dra. Paz',
      'branch_name': sucursal,
      'reason': 'Dolor de cabeza.',
      'evolution': '',
      'diagnosis': diagnostico,
      'indications': '',
      'treatment': '',
      'signed_by_name': 'Dra. Paz',
      'signed_at': '2026-09-20T15:00:00Z',
      'amendments': enmiendas,
      'prescription_items': medicamentos,
      'orders': ordenes,
    };

class _GuardadoFalso implements GuardadoDeArchivos {
  final guardados = <String, List<int>>{};

  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    guardados[nombre] = bytes;
    return '/storage/emulated/0/Download/$nombre';
  }
}

class _AbridorFalso implements AbridorDeArchivos {
  final abiertos = <String>[];

  @override
  Future<String?> abrir(String ruta) async {
    abiertos.add(ruta);
    return null;
  }
}

Map<String, dynamic> _historia(String nombre, List<Map<String, dynamic>> atenciones) {
  final porSucursal = <String, int>{};
  for (final a in atenciones) {
    porSucursal.update(a['branch_name'] as String, (n) => n + 1, ifAbsent: () => 1);
  }
  return {
    'patient': {'id': 'x', 'full_name': nombre, 'appointments': []},
    'scope': 'own',
    'branches': [
      for (final e in porSucursal.entries) {'name': e.key, 'encounters': e.value},
    ],
    'encounters': atenciones,
  };
}

void _pantallaGrande(WidgetTester tester) {
  tester.view.physicalSize = const Size(1200, 4000);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

Future<List<String>> _abrir(
  WidgetTester tester,
  Map<String, Map<String, dynamic>> historias, {
  GuardadoDeArchivos? guardado,
  AbridorDeArchivos? abridor,
}) async {
  final pedidos = <String>[];
  final client = ApiClient(
    httpClient: MockClient((request) async {
      pedidos.add(request.url.path);
      if (request.url.path.endsWith('/patient-options/')) return _json(_opciones);
      if (request.url.path.endsWith('/prescription.pdf')) {
        return http.Response.bytes(
          utf8.encode('%PDF-1.4 receta'),
          200,
          headers: {
            'content-type': 'application/pdf',
            'content-disposition': 'attachment; filename="receta-2026-09-20-rios.pdf"',
          },
        );
      }
      final id = request.url.pathSegments.where((s) => s.isNotEmpty).last;
      return _json(historias[id]!);
    }),
  );
  await tester.pumpWidget(
    MaterialApp(
      home: ClinicalRecordScreen(
        client: client,
        guardado: guardado,
        abridor: abridor,
      ),
    ),
  );
  await tester.pumpAndSettle();
  return pedidos;
}

void main() {
  testWidgets('muestra la línea de tiempo con la enmienda debajo de lo firmado',
      (tester) async {
    _pantallaGrande(tester);
    await _abrir(tester, {
      't1': _historia('Ana Ríos', [
        _atencion('e1', 'Sede Central', 'Migraña.', enmiendas: [
          {
            'id': 'm1',
            'section': 'diagnosis',
            'section_display': 'Diagnóstico',
            'text': 'Migraña con aura.',
            'author_name': 'Dra. Paz',
            'created_at': '2026-09-21T10:00:00Z',
          },
        ]),
      ]),
    });

    expect(find.text('1 atención firmada en 1 sucursal'), findsOneWidget);
    // Lo firmado sigue a la vista; la enmienda se agrega, no lo reemplaza.
    expect(find.text('Migraña.'), findsOneWidget);
    expect(find.text('Migraña con aura.'), findsOneWidget);
    expect(find.textContaining('Enmienda de Dra. Paz'), findsOneWidget);
    // Una sucursal sola no necesita filtro.
    expect(find.byType(ChoiceChip), findsNothing);
  });

  testWidgets('el filtro por sucursal deja sólo las de esa sede',
      (tester) async {
    _pantallaGrande(tester);
    await _abrir(tester, {
      't1': _historia('Ana Ríos', [
        _atencion('e1', 'Sede Central', 'Migraña.'),
        _atencion('e2', 'Sede Norte', 'Gastritis.'),
      ]),
    });

    expect(find.text('2 atenciones firmadas en 2 sucursales'), findsOneWidget);
    expect(find.text('Gastritis.'), findsOneWidget);

    await tester.tap(find.text('Sede Central · 1'));
    await tester.pumpAndSettle();

    expect(find.text('Migraña.'), findsOneWidget);
    expect(find.text('Gastritis.'), findsNothing);
  });

  testWidgets('cambiar de persona trae la historia de esa persona',
      (tester) async {
    _pantallaGrande(tester);
    final pedidos = await _abrir(tester, {
      't1': _historia('Ana Ríos', [_atencion('e1', 'Sede Central', 'Migraña.')]),
      'd1': _historia('Mateo Ríos', []),
    });
    expect(pedidos.last, endsWith('/encounters/history/t1/'));

    await tester.tap(find.byType(DropdownButtonFormField<String>));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mateo Ríos · Hijo/a').last);
    await tester.pumpAndSettle();

    expect(pedidos.last, endsWith('/encounters/history/d1/'));
    expect(find.text('Todavía no hay atenciones firmadas.'), findsOneWidget);
    expect(find.text('Migraña.'), findsNothing);
  });

  testWidgets('US-27: muestra la receta y las órdenes y baja el PDF a Descargas',
      (tester) async {
    _pantallaGrande(tester);
    final guardado = _GuardadoFalso();
    final abridor = _AbridorFalso();
    final pedidos = await _abrir(
      tester,
      {
        't1': _historia('Ana Ríos', [
          _atencion('e1', 'Sede Central', 'Faringitis.', medicamentos: [
            {
              'id': 'p1',
              'medication': 'Amoxicilina 500 mg',
              'dose': '1 cápsula',
              'frequency': 'cada 8 horas',
              'duration': '7 días',
              'instructions': 'Después de comer',
            },
          ], ordenes: [
            {
              'id': 'o1',
              'kind': 'laboratory',
              'kind_display': 'Laboratorio',
              'description': 'Hemograma completo',
              'notes': '',
            },
          ]),
        ]),
      },
      guardado: guardado,
      abridor: abridor,
    );

    expect(find.text('Receta y órdenes'), findsOneWidget);
    expect(find.text('Amoxicilina 500 mg'), findsOneWidget);
    expect(find.text('1 cápsula · cada 8 horas · 7 días'), findsOneWidget);
    expect(find.text('Laboratorio: Hemograma completo'), findsOneWidget);

    await tester.tap(find.text('Descargar receta (PDF)'));
    await tester.pumpAndSettle();

    expect(pedidos.last, endsWith('/encounters/e1/prescription.pdf'));
    expect(guardado.guardados.keys, ['receta-2026-09-20-rios.pdf']);
    expect(find.textContaining('Receta guardada en Descargas'), findsOneWidget);

    await tester.tap(find.text('Abrir'));
    await tester.pumpAndSettle();
    expect(abridor.abiertos,
        ['/storage/emulated/0/Download/receta-2026-09-20-rios.pdf']);
  });

  testWidgets('US-27: una atención sin receta no muestra el botón',
      (tester) async {
    _pantallaGrande(tester);
    await _abrir(tester, {
      't1': _historia('Ana Ríos', [_atencion('e1', 'Sede Central', 'Migraña.')]),
    });
    expect(find.text('Receta y órdenes'), findsNothing);
    expect(find.text('Descargar receta (PDF)'), findsNothing);
  });
}
