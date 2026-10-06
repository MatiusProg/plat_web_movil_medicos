/// Característica general 6 — Copias de seguridad en el teléfono.
///
///     flutter test test/backups_test.dart
///
/// El disco no se prueba: el guardado se inyecta en memoria con
/// [_GuardadoFalso]. Lo que se prueba es lo que importa del lado del móvil:
///
/// - que la regla del plan y las copias automáticas se vean;
/// - que el historial distinga y filtre manuales y automáticas;
/// - que generar y descargar guarden el archivo con el nombre que corresponde;
/// - que restaurar pase por `inspect`, pida escribir el identificador de la
///   organización y recién entonces mande `confirm: true`;
/// - que sin el permiso de restaurar el botón no exista.
///
/// Qué se respalda y cómo se restaura se prueba en el backend
/// (`tests/test_caracteristica_6_*.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/features/backups/backups_api.dart';
import 'package:mobile/features/backups/backups_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Map<String, dynamic> _politica({bool permitida = true}) => {
  'plan_code': 'pro',
  'plan_name': 'Pro',
  'interval_hours': 24,
  'last_backup_at': null,
  'next_available_at': permitida ? null : '2026-10-07T10:00:00-04:00',
  'allowed_now': permitida,
  'description': 'Tu plan Pro permite una copia por día.',
  'automatic': {
    'enabled': true,
    'interval_hours': 24,
    'retention': 7,
    'last_at': '2026-10-06T03:00:00-04:00',
    'next_at': '2026-10-07T03:00:00-04:00',
    'description':
        'El sistema genera una por día sola y conserva las últimas 7.',
  },
};

const _historial = {
  'count': 2,
  'next': null,
  'previous': null,
  'results': [
    {
      'id': 'auto-1',
      'kind': 'backup',
      'kind_label': 'Copia de seguridad',
      'trigger': 'automatic',
      'trigger_label': 'Automática',
      'downloadable': true,
      'filename': 'respaldo-kolping-20261006-0300.json',
      'size_bytes': 20480,
      'total_rows': 120,
      'detail': [],
      'checksum': 'abc',
      'performed_by_email': null,
      'created_at': '2026-10-06T03:00:00-04:00',
    },
    {
      'id': 'manual-1',
      'kind': 'backup',
      'kind_label': 'Copia de seguridad',
      'trigger': 'manual',
      'trigger_label': 'Manual',
      'downloadable': false,
      'filename': 'respaldo-kolping-20261005-1800.json',
      'size_bytes': 19000,
      'total_rows': 118,
      'detail': [],
      'checksum': 'def',
      'performed_by_email': 'admin@kolping.test',
      'created_at': '2026-10-05T18:00:00-04:00',
    },
  ],
};

const _documento = {
  'format': 'plataforma-medica-backup',
  'version': 1,
  'generated_at': '2026-10-06T09:15:42.123456-04:00',
  'organization': {'id': 'org-1', 'slug': 'kolping', 'name': 'Kolping'},
  'counts': {'patients.Patient': 3},
  'checksum': 'zzz',
  'payload': {'patients.Patient': []},
};

const _inspeccion = {
  'organization': {'id': 'org-1', 'slug': 'kolping', 'name': 'Kolping'},
  'generated_at': '2026-10-06T03:00:00-04:00',
  'counts': {'patients.Patient': 3, 'encounters.Encounter': 0},
  'restorable': ['patients.Patient'],
  'skipped': [],
  'belongs_to_my_organization': true,
  'labels': {'patients.Patient': 'Pacientes', 'encounters.Encounter': 'Atenciones médicas'},
};

class _GuardadoFalso implements GuardadoDeArchivos {
  final Map<String, List<int>> archivos = {};

  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    archivos[nombre] = bytes;
    return '/Descargas/$nombre';
  }
}

/// Las peticiones que llegaron, para mirar qué se mandó.
class _Registro {
  final List<http.Request> pedidos = [];

  Iterable<http.Request> a(String sufijo) =>
      pedidos.where((r) => r.url.path.endsWith(sufijo));
}

MockClient _mock(_Registro registro, {bool permitida = true, int crear = 200}) {
  return MockClient((req) async {
    registro.pedidos.add(req);
    final ruta = req.url.path;
    if (ruta.endsWith('/backups/policy/')) {
      return _json(_politica(permitida: permitida), 200);
    }
    if (ruta.endsWith('/backups/records/')) return _json(_historial, 200);
    if (ruta.endsWith('/backups/create/')) {
      if (crear == 429) {
        return _json({
          'detail': 'Tu plan Pro permite una copia por día.',
          'code': 'backup_limit',
        }, 429);
      }
      return _json(_documento, 200);
    }
    if (ruta.endsWith('/download/')) return _json(_documento, 200);
    if (ruta.endsWith('/backups/inspect/')) return _json(_inspeccion, 200);
    if (ruta.endsWith('/backups/restore/')) {
      return _json({'written': {}, 'kept': {}, 'deleted': {}}, 200);
    }
    return _json({'detail': 'no'}, 404);
  });
}

Future<void> _abrir(
  WidgetTester tester,
  MockClient mock, {
  _GuardadoFalso? guardado,
  bool puedeRestaurar = true,
}) async {
  tester.view.physicalSize = const Size(1200, 3200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);

  await tester.pumpWidget(
    MaterialApp(
      // Con el tema de la aplicación: ver `reporting_voz_test.dart`.
      theme: AppTheme.light,
      home: BackupsScreen(
        client: ApiClient(httpClient: mock),
        guardado: guardado ?? _GuardadoFalso(),
        puedeRestaurar: puedeRestaurar,
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('se ve la regla del plan, las automáticas y el historial', (
    tester,
  ) async {
    await _abrir(tester, _mock(_Registro()));

    expect(find.text('Tu plan Pro permite una copia por día.'), findsOneWidget);
    expect(find.text('Copias automáticas'), findsOneWidget);
    expect(find.textContaining('conserva las últimas 7'), findsOneWidget);
    expect(find.text('Copia automática'), findsOneWidget);
    expect(find.text('Copia manual'), findsOneWidget);
  });

  testWidgets('el filtro separa automáticas de manuales', (tester) async {
    await _abrir(tester, _mock(_Registro()));

    await tester.tap(find.text('Automáticas'));
    await tester.pumpAndSettle();
    expect(find.text('Copia automática'), findsOneWidget);
    expect(find.text('Copia manual'), findsNothing);

    await tester.tap(find.text('Manuales'));
    await tester.pumpAndSettle();
    expect(find.text('Copia automática'), findsNothing);
    expect(find.text('Copia manual'), findsOneWidget);
  });

  testWidgets('generar guarda el archivo con el nombre del backend', (
    tester,
  ) async {
    final guardado = _GuardadoFalso();
    final registro = _Registro();
    await _abrir(tester, _mock(registro), guardado: guardado);

    await tester.tap(find.text('Generar y guardar'));
    await tester.pumpAndSettle();

    expect(registro.a('/backups/create/'), hasLength(1));
    final bytes = guardado.archivos['respaldo-kolping-20261006-0915.json'];
    expect(bytes, isNotNull);
    final guardadoComoJson =
        jsonDecode(utf8.decode(bytes!)) as Map<String, dynamic>;
    expect(guardadoComoJson['checksum'], 'zzz');
    expect(find.textContaining('Copia guardada en'), findsOneWidget);
  });

  testWidgets('sin cuota el botón se apaga y dice desde cuándo', (
    tester,
  ) async {
    await _abrir(tester, _mock(_Registro(), permitida: false));

    final boton = tester.widget<FilledButton>(
      find.ancestor(
        of: find.text('Generar y guardar'),
        matching: find.byWidgetPredicate((w) => w is FilledButton),
      ),
    );
    expect(boton.onPressed, isNull);
    expect(find.textContaining('La próxima se puede generar'), findsOneWidget);
  });

  testWidgets('si el backend rechaza la copia se muestra su motivo', (
    tester,
  ) async {
    await _abrir(tester, _mock(_Registro(), crear: 429));
    await tester.tap(find.text('Generar y guardar'));
    await tester.pumpAndSettle();
    expect(find.text('Tu plan Pro permite una copia por día.'), findsWidgets);
  });

  testWidgets('descargar una automática la guarda con su nombre', (
    tester,
  ) async {
    final guardado = _GuardadoFalso();
    final registro = _Registro();
    await _abrir(tester, _mock(registro), guardado: guardado);

    await tester.tap(find.text('Descargar'));
    await tester.pumpAndSettle();

    expect(registro.a('/backups/records/auto-1/download/'), hasLength(1));
    expect(
      guardado.archivos.keys,
      contains('respaldo-kolping-20261006-0300.json'),
    );
  });

  testWidgets('sin el permiso de restaurar no aparece el botón', (
    tester,
  ) async {
    await _abrir(tester, _mock(_Registro()), puedeRestaurar: false);
    expect(find.text('Descargar'), findsOneWidget);
    expect(find.text('Restaurar'), findsNothing);
  });

  testWidgets(
    'restaurar inspecciona, pide el identificador y recién ahí confirma',
    (tester) async {
      final registro = _Registro();
      await _abrir(tester, _mock(registro));

      await tester.tap(find.text('Restaurar'));
      await tester.pumpAndSettle();

      final inspeccion = registro.a('/backups/inspect/').single;
      expect(jsonDecode(inspeccion.body), {'record': 'auto-1'});
      expect(find.text('Pacientes: 3'), findsOneWidget);
      // Las tablas vacías no se listan.
      expect(find.textContaining('Atenciones médicas'), findsNothing);

      final boton = find.text('Restaurar y reemplazar los datos');
      await tester.tap(boton);
      await tester.pumpAndSettle();
      expect(registro.a('/backups/restore/'), isEmpty);

      await tester.enterText(
        find.byKey(const Key('confirmacion-restauracion')),
        'kolpin',
      );
      await tester.pump();
      await tester.tap(boton);
      await tester.pumpAndSettle();
      expect(registro.a('/backups/restore/'), isEmpty);

      await tester.enterText(
        find.byKey(const Key('confirmacion-restauracion')),
        'kolping',
      );
      await tester.pump();
      await tester.tap(boton);
      await tester.pumpAndSettle();

      final restauracion = registro.a('/backups/restore/').single;
      expect(jsonDecode(restauracion.body), {
        'record': 'auto-1',
        'confirm': true,
      });
      expect(find.textContaining('Datos restaurados'), findsOneWidget);
    },
  );

  test('el nombre se arma con el slug y la hora local del servidor', () {
    expect(nombreDeCopia(_documento), 'respaldo-kolping-20261006-0915.json');
    expect(
      nombreDeCopia(const {'organization': {}}),
      'respaldo-organizacion-copia.json',
    );
  });
}
