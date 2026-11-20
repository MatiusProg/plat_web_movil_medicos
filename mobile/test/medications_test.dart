/// Pruebas de US-49 en el móvil — los recordatorios de la receta.
///
///     flutter test test/medications_test.dart
///
/// Los avisos no se programan de verdad: `Recordatorios` recibe un
/// programador falso que anota qué se programó y qué se canceló. Lo que se
/// prueba es lo que decide la app:
///
/// - «cada 8 horas por 5 días» son 15 avisos, y los que ya pasaron no se
///   programan;
/// - «Tomada» y «Posponer 15 min» desde el aviso;
/// - una toma marcada sin conexión queda pendiente y se manda después, y un
///   409 (ya estaba) cuenta como enviada;
/// - **al cerrar sesión se cancelan todos los avisos** y no queda nada;
/// - la pantalla *Mis medicamentos*.
///
/// Qué se entiende como horario («según dolor» no) y quién puede marcar qué
/// toma se prueba en el backend (`tests/test_us49.py`).
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/session/session.dart';
import 'package:mobile/features/medications/medications_api.dart';
import 'package:mobile/features/medications/medications_screen.dart';
import 'package:mobile/features/medications/recordatorios.dart';

import 'defectos_sesion_test.dart' show MemoryStorage, tokenQueVence;
import 'push_test.dart' show RegistradorFalso, usuario;

class ProgramadorFalso implements ProgramadorDeAvisos {
  final programados = <int, ({DateTime cuando, String titulo, String cuerpo, String payload})>{};
  final cancelados = <int>[];

  @override
  Future<void> programar({
    required int id,
    required DateTime cuando,
    required String titulo,
    required String cuerpo,
    required String payload,
  }) async {
    programados[id] = (cuando: cuando, titulo: titulo, cuerpo: cuerpo, payload: payload);
  }

  @override
  Future<void> cancelar(int id) async {
    cancelados.add(id);
    programados.remove(id);
  }
}

class AvisosFalsos implements AvisosLocales {
  int cancelaciones = 0;

  @override
  Future<void> cancelarTodo() async => cancelaciones++;
}

http.Response _json(Object cuerpo, [int estado = 200]) => http.Response(
      jsonEncode(cuerpo),
      estado,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

const _cada8por5 =
    HorarioDeTomas(intervaloHoras: 8, dias: 5, totalTomas: 15);

/// Hoy 10:00. La primera toma fue a las 08:00: la 1 ya pasó.
final _ahora = DateTime(2026, 11, 20, 10, 0);

RecordatorioActivo _loratadina({DateTime? primera}) => RecordatorioActivo(
      itemId: 'item-1',
      patientId: 't1',
      medicamento: 'Loratadina 10 mg',
      dosis: '1 comprimido',
      horario: _cada8por5,
      primeraToma: primera ?? DateTime(2026, 11, 20, 8, 0),
    );

({Recordatorios r, ProgramadorFalso programador, AlmacenEnMemoria almacen}) _armar() {
  final programador = ProgramadorFalso();
  final almacen = AlmacenEnMemoria();
  final r = Recordatorios(
    almacen: almacen,
    programador: programador,
    reloj: () => _ahora,
  );
  return (r: r, programador: programador, almacen: almacen);
}

ApiClient _api(List<http.Request> pedidos, {int estado = 201}) => ApiClient(
      httpClient: MockClient((request) async {
        pedidos.add(request);
        return _json({'dose_number': 1, 'status': 'taken'}, estado);
      }),
    );

void main() {
  group('el horario', () {
    test('cada 8 horas por 5 días son 15 avisos, sin los que ya pasaron',
        () async {
      final a = _armar();
      await a.r.activar(_loratadina());

      // La 1 (08:00) ya pasó: quedan 14, desde las 16:00.
      expect(a.programador.programados, hasLength(14));
      final horas = a.programador.programados.values.map((p) => p.cuando).toList()
        ..sort();
      expect(horas.first, DateTime(2026, 11, 20, 16, 0));
      expect(horas.last, DateTime(2026, 11, 25, 0, 0));

      final aviso = a.programador.programados[Recordatorios.idDeAviso('item-1', 2)]!;
      expect(aviso.titulo, 'Hora de tu Loratadina 10 mg');
      expect(aviso.cuerpo, '1 comprimido · toma 2 de 15');
      expect(aviso.payload, 'med|item-1|2');
    });

    test('la próxima toma, la que toca y el día del tratamiento', () {
      final r = _loratadina();
      expect(r.proximaToma(_ahora), 2);
      expect(r.tomaQueToca(_ahora), 1);
      expect(r.diaDelTratamiento(_ahora), 1);
      expect(r.diaDelTratamiento(DateTime(2026, 11, 22, 9, 0)), 3);
      expect(r.terminado(DateTime(2026, 11, 26, 0, 0)), isTrue);
    });

    test('los ids de los avisos son estables y no chocan entre tomas', () {
      final ids = {
        for (var n = 1; n <= 15; n++) Recordatorios.idDeAviso('item-1', n),
        for (var n = 1; n <= 15; n++)
          Recordatorios.idDeAviso('item-1', n, pospuesto: true),
      };
      expect(ids, hasLength(30));
      expect(Recordatorios.idDeAviso('item-1', 3),
          Recordatorios.idDeAviso('item-1', 3));
      expect(ids.every((id) => id > 0 && id < 0x7fffffff), isTrue);
    });

    test('reactivar con otra hora cancela los avisos anteriores', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.activar(_loratadina(primera: DateTime(2026, 11, 20, 12, 0)));
      expect(a.programador.programados.values.map((p) => p.cuando),
          contains(DateTime(2026, 11, 20, 12, 0)));
      expect(a.programador.programados.values.map((p) => p.cuando),
          isNot(contains(DateTime(2026, 11, 20, 16, 0))));
    });

    test('desactivar cancela todos sus avisos', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.desactivar('item-1');
      expect(a.programador.programados, isEmpty);
      expect(a.r.activos, isEmpty);
    });

    test('lo activado sobrevive a cerrar y abrir la app', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.marcar('item-1', 1, tomada: true);

      final otra = Recordatorios(
          almacen: a.almacen, programador: ProgramadorFalso(), reloj: () => _ahora);
      await otra.cargar();
      expect(otra.activos.keys, ['item-1']);
      expect(otra.activos['item-1']!.primeraToma, DateTime(2026, 11, 20, 8, 0));
      expect(otra.pendientes.single.numero, 1);
    });
  });

  group('desde el aviso', () {
    test('«Tomada» la deja pendiente y cancela su aviso', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.responder('med|item-1|2', accionTomada);

      expect(a.r.pendientes.single.numero, 2);
      expect(a.r.pendientes.single.tomada, isTrue);
      expect(a.r.pendientes.single.programadaPara, DateTime(2026, 11, 20, 16, 0));
      expect(a.programador.programados
          .containsKey(Recordatorios.idDeAviso('item-1', 2)), isFalse);
    });

    test('«Posponer 15 min» programa el mismo aviso un rato después', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.responder('med|item-1|2', accionPosponer);

      final pospuesto = a.programador
          .programados[Recordatorios.idDeAviso('item-1', 2, pospuesto: true)]!;
      expect(pospuesto.cuando, _ahora.add(const Duration(minutes: 15)));
      expect(pospuesto.payload, 'med|item-1|2');
      expect(a.r.pendientes, isEmpty);
    });

    test('tocar el aviso abre Mis medicamentos', () async {
      final a = _armar();
      var abierto = false;
      a.r.alTocarAviso = () => abierto = true;
      await a.r.responder('med|item-1|2', null);
      expect(abierto, isTrue);
    });

    test('un aviso que no es de medicamentos no se toca', () async {
      final a = _armar();
      var abierto = false;
      a.r.alTocarAviso = () => abierto = true;
      await a.r.responder('a1b2c3', accionTomada);
      await a.r.responder('chat:e1', null);
      await a.r.responder('med|roto', accionTomada);
      expect(abierto, isFalse);
      expect(a.r.pendientes, isEmpty);
      expect(Recordatorios.esDeMedicamento('med|item-1|2'), isTrue);
      expect(Recordatorios.esDeMedicamento('appointment-id'), isFalse);
    });

    test('marcar dos veces la misma toma no la duplica', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.marcar('item-1', 2, tomada: true);
      await a.r.marcar('item-1', 2, tomada: false);
      expect(a.r.pendientes, hasLength(1));
      expect(a.r.pendientes.single.tomada, isTrue);
    });
  });

  group('al servidor', () {
    test('las pendientes se mandan y se borran del teléfono', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.marcar('item-1', 1, tomada: true);
      await a.r.marcar('item-1', 2, tomada: false);

      final pedidos = <http.Request>[];
      expect(await a.r.sincronizar(_api(pedidos)), 0);
      expect(a.r.pendientes, isEmpty);
      expect(pedidos.map((p) => p.url.path).toSet(),
          {'/api/encounters/prescription/item-1/intakes/'});
      expect(pedidos.map((p) => (jsonDecode(p.body) as Map)['status']),
          ['taken', 'skipped']);
    });

    test('si ya estaba marcada (409) cuenta como enviada', () async {
      final a = _armar();
      await a.r.marcar('item-1', 1, tomada: true);
      expect(await a.r.sincronizar(_api([], estado: 409)), 0);
      expect(a.r.pendientes, isEmpty);
    });

    test('sin conexión quedan pendientes para la próxima', () async {
      final a = _armar();
      await a.r.marcar('item-1', 1, tomada: true);
      final sinRed = ApiClient(
        httpClient: MockClient((_) async => throw http.ClientException('sin red')),
      );
      expect(await a.r.sincronizar(sinRed), 1);
      expect(a.r.pendientes, hasLength(1));
    });

    test('con sesión, la toma marcada se manda en seguida', () async {
      final a = _armar();
      final pedidos = <http.Request>[];
      a.r.clienteParaEnviar = () => _api(pedidos);
      await a.r.marcar('item-1', 1, tomada: true);
      expect(pedidos, hasLength(1));
      expect(a.r.pendientes, isEmpty);
    });
  });

  group('al cerrar sesión', () {
    test('se cancelan todos los avisos y no queda nada guardado', () async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await a.r.activar(RecordatorioActivo(
        itemId: 'item-2',
        patientId: 'd1',
        medicamento: 'Amoxicilina',
        dosis: '5 ml',
        horario: const HorarioDeTomas(intervaloHoras: 12, dias: 3, totalTomas: 6),
        primeraToma: DateTime(2026, 11, 20, 20, 0),
      ));
      await a.r.marcar('item-1', 1, tomada: true);
      expect(a.programador.programados, isNotEmpty);

      await a.r.cancelarTodo();

      expect(a.programador.programados, isEmpty);
      expect(a.r.activos, isEmpty);
      expect(a.r.pendientes, isEmpty);
      expect(a.almacen.datos, isNull);
    });

    test('la sesión los cancela al salir', () async {
      final avisos = AvisosFalsos();
      final session = Session(
          storage: MemoryStorage(), devices: RegistradorFalso(), avisos: avisos);
      await session.saveSession(
        access: tokenQueVence(const Duration(minutes: 30)),
        refresh: tokenQueVence(const Duration(days: 7)),
        organization: 'centro',
        user: usuario(),
      );
      await session.signOut();
      expect(avisos.cancelaciones, 1);
    });
  });

  group('Mis medicamentos', () {
    Map<String, dynamic> tratamiento(String id, String nombre, {
      Map<String, dynamic>? horario,
      String? motivo,
      List<Map<String, dynamic>> tomas = const [],
    }) =>
        {
          'id': id,
          'encounter': 'e1',
          'prescribed_at': '2026-11-20T11:00:00Z',
          'practitioner_name': 'Laura Gómez',
          'medication': nombre,
          'dose': '1 comprimido',
          'frequency': horario == null ? 'según dolor' : 'cada 8 horas',
          'duration': '5 días',
          'instructions': '',
          'schedule': horario,
          'schedule_reason': motivo,
          'adherence': {'taken': 0, 'skipped': 0, 'total': null, 'rate': null},
          'intakes': tomas,
        };

    Future<List<http.Request>> abrir(WidgetTester tester, Recordatorios r) async {
      tester.view.physicalSize = const Size(1200, 3000);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      final pedidos = <http.Request>[];
      final client = ApiClient(
        httpClient: MockClient((request) async {
          pedidos.add(request);
          if (request.url.path.endsWith('/patient-options/')) {
            return _json([
              {
                'id': 't1',
                'full_name': 'Ana Ríos',
                'relationship': '',
                'relationship_label': 'Yo',
                'is_self': true,
                'birth_date': '1990-05-20',
              },
            ]);
          }
          if (request.url.path.endsWith('/intakes/')) {
            return _json({'dose_number': 1, 'status': 'taken'}, 201);
          }
          return _json({
            'patient': 't1',
            'medications': [
              tratamiento('item-1', 'Loratadina 10 mg',
                  horario: {'interval_hours': 8, 'days': 5, 'total_doses': 15},
                  tomas: [
                    {'dose_number': 1, 'status': 'taken',
                     'scheduled_at': null, 'recorded_at': '2026-11-20T12:00:00Z'},
                  ]),
              tratamiento('item-2', 'Paracetamol 500 mg',
                  horario: {'interval_hours': 6, 'days': 3, 'total_doses': 12}),
              tratamiento('item-3', 'Ibuprofeno 400 mg',
                  motivo: 'Esta indicación no tiene horario fijo.'),
            ],
          });
        }),
      );
      await tester.pumpWidget(MaterialApp(
        home: MedicationsScreen(client: client, recordatorios: r, reloj: () => _ahora),
      ));
      await tester.pumpAndSettle();
      return pedidos;
    }

    testWidgets('separa en curso, recetados y sin horario fijo', (tester) async {
      final a = _armar();
      await a.r.activar(_loratadina());
      await abrir(tester, a.r);

      expect(find.text('En curso'), findsOneWidget);
      expect(find.text('Día 1 de 5'), findsOneWidget);
      expect(find.text('Próxima toma: hoy 16:00'), findsWidgets);
      expect(find.text('1 de 15 tomas'), findsOneWidget);

      expect(find.text('Recetados'), findsOneWidget);
      expect(find.text('Paracetamol 500 mg'), findsOneWidget);
      expect(find.text('cada 6 horas por 3 días · 12 tomas'), findsOneWidget);

      expect(find.text('Sin horario fijo'), findsOneWidget);
      expect(find.text('Esta indicación no tiene horario fijo.'), findsOneWidget);
      // Sin horario fijo no se ofrece el recordatorio.
      expect(find.byType(SwitchListTile), findsNWidgets(2));
    });

    testWidgets('marca desde la app la toma que toca', (tester) async {
      final a = _armar();
      // Primera toma a las 02:00: la 1 ya está marcada en el servidor y la 2
      // es justo a las 10:00, así que es la que toca marcar.
      await a.r.activar(_loratadina(primera: DateTime(2026, 11, 20, 2, 0)));
      final pedidos = await abrir(tester, a.r);

      expect(find.text('Toma de las hoy 10:00'), findsOneWidget);
      await tester.tap(find.text('Tomada'));
      await tester.pumpAndSettle();

      final marcada = pedidos.where((p) => p.url.path.endsWith('/intakes/'));
      expect(marcada, hasLength(1));
      expect((jsonDecode(marcada.single.body) as Map)['dose_number'], 2);
    });
  });
}
