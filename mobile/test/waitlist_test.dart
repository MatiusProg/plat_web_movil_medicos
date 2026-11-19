/// Pruebas de US-52 en el móvil: lista de espera con aviso de cupo liberado.
///
/// El móvil muestra y el backend decide: acá se comprueba qué se pide, qué se
/// le dice a la persona según lo que respondió el backend y que un fallo de la
/// lista de espera no rompa "Mis fichas".
///
///     flutter test test/waitlist_test.dart
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/appointments/appointment_detail_screen.dart';
import 'package:mobile/features/appointments/my_appointments_screen.dart';
import 'package:mobile/features/availability/availability_screen.dart';
import 'package:mobile/features/waitlist/waitlist_api.dart';

http.Response _json(Object? cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

String _iso(DateTime d) =>
    '${d.year.toString().padLeft(4, '0')}-'
    '${d.month.toString().padLeft(2, '0')}-'
    '${d.day.toString().padLeft(2, '0')}';

const _opciones = [
  {
    'id': 'p1',
    'full_name': 'Ana Pérez',
    'relationship_label': 'Yo',
    'is_self': true,
  },
];

Map<String, dynamic> _entrada({
  String id = 'w1',
  int? position = 2,
  String status = 'waiting',
}) => {
  'id': id,
  'patient': 'p1',
  'patient_name': 'Ana Pérez',
  'practitioner': 'pr1',
  'practitioner_name': 'Laura Gómez',
  'specialty': null,
  'specialty_name': null,
  'branch': null,
  'branch_name': null,
  'date_from': '2026-11-20',
  'date_to': '2026-12-04',
  'status': status,
  'position': position,
  'offered_appointment': null,
  'offered_expires_at': null,
  'created_at': '2026-11-18T10:00:00Z',
};

Map<String, dynamic> _sinEspacios({bool activo = true}) => {
  'practitioner': {'full_name': 'Laura Gómez', 'is_active': activo},
  'days': <Object>[],
};

void _vistaGrande(WidgetTester tester) {
  tester.view.physicalSize = const Size(1200, 2400);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.resetPhysicalSize);
  addTearDown(tester.view.resetDevicePixelRatio);
}

void main() {
  group('waitlist_api', () {
    test('lee la lista, la posición y si la función está habilitada', () async {
      final client = ApiClient(
        httpClient: MockClient(
          (_) async => _json({
            'enabled': true,
            'results': [_entrada(), _entrada(id: 'w2', position: null)],
          }, 200),
        ),
      );
      final lista = await miListaDeEspera(client);
      expect(lista.enabled, isTrue);
      expect(lista.entries, hasLength(2));
      expect(lista.entries.first.position, 2);
      expect(lista.entries.first.destino, 'Laura Gómez');
      expect(lista.entries.first.rango, '20/11/2026 al 04/12/2026');
      expect(lista.entries.last.position, isNull);
    });

    test('tolera una respuesta vacía', () async {
      final client = ApiClient(
        httpClient: MockClient((_) async => _json({}, 200)),
      );
      final lista = await miListaDeEspera(client);
      expect(lista.enabled, isFalse);
      expect(lista.entries, isEmpty);
    });
  });

  group('disponibilidad sin espacios', () {
    late List<http.Request> pedidos;

    Future<void> abrir(
      WidgetTester tester, {
      http.Response Function(http.Request)? alAnotarse,
      bool activo = true,
    }) async {
      _vistaGrande(tester);
      pedidos = [];
      final client = ApiClient(
        httpClient: MockClient((request) async {
          pedidos.add(request);
          final ruta = request.url.path;
          if (ruta.endsWith('/patient-options/')) return _json(_opciones, 200);
          if (ruta.endsWith('/appointments/waitlist/')) {
            return alAnotarse!(request);
          }
          return _json(_sinEspacios(activo: activo), 200);
        }),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: AvailabilityScreen(
            practitionerId: 'pr1',
            practitionerName: 'Laura Gómez',
            client: client,
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('ofrece la lista de espera y manda el cuerpo correcto', (
      tester,
    ) async {
      await abrir(
        tester,
        alAnotarse: (_) => _json(_entrada(position: 3), 201),
      );

      expect(
        find.text('No hay espacios libres en las próximas dos semanas.'),
        findsOneWidget,
      );
      expect(find.text('¿Quieres que te avisemos?'), findsOneWidget);

      await tester.tap(find.text('Anotarme en lista de espera'));
      await tester.pumpAndSettle();

      final post = pedidos.firstWhere((r) => r.method == 'POST');
      final hoy = DateTime.now();
      final desde = DateTime(hoy.year, hoy.month, hoy.day);
      expect(jsonDecode(post.body), {
        'patient': 'p1',
        'practitioner': 'pr1',
        'date_from': _iso(desde),
        'date_to': _iso(desde.add(const Duration(days: 14))),
      });
      expect(
        find.text('Quedaste anotado. Eres el N.º 3 de la fila.'),
        findsOneWidget,
      );
    });

    testWidgets('hay_turnos dice que reserve y vuelve a mirar la grilla', (
      tester,
    ) async {
      await abrir(
        tester,
        alAnotarse: (_) => _json({
          'code': 'hay_turnos',
          'detail': 'Ya hay turnos libres.',
        }, 400),
      );
      final antes = pedidos
          .where((r) => r.url.path.contains('availability'))
          .length;

      await tester.tap(find.text('Anotarme en lista de espera'));
      await tester.pumpAndSettle();

      expect(
        find.text('Ya hay turnos libres en esas fechas: reserva uno.'),
        findsOneWidget,
      );
      final despues = pedidos
          .where((r) => r.url.path.contains('availability'))
          .length;
      expect(despues, greaterThan(antes));
    });

    testWidgets('plan_limit muestra el detalle del backend y no insiste', (
      tester,
    ) async {
      await abrir(
        tester,
        alAnotarse: (_) => _json({
          'code': 'plan_limit',
          'detail': 'La lista de espera es de los planes Pro y Premium.',
        }, 403),
      );

      await tester.tap(find.text('Anotarme en lista de espera'));
      await tester.pumpAndSettle();

      expect(
        find.text('La lista de espera es de los planes Pro y Premium.'),
        findsOneWidget,
      );
      expect(find.text('Anotarme en lista de espera'), findsNothing);
    });

    testWidgets('ya_anotado tiene su propio mensaje', (tester) async {
      await abrir(
        tester,
        alAnotarse: (_) =>
            _json({'code': 'ya_anotado', 'detail': 'Ya estás anotado.'}, 400),
      );

      await tester.tap(find.text('Anotarme en lista de espera'));
      await tester.pumpAndSettle();

      expect(
        find.text(
          'Ya estás en la lista de espera de este profesional en esas fechas.',
        ),
        findsOneWidget,
      );
    });

    testWidgets('con el profesional inactivo no se ofrece anotarse', (
      tester,
    ) async {
      await abrir(tester, activo: false);
      expect(
        find.text('No hay espacios libres en las próximas dos semanas.'),
        findsOneWidget,
      );
      expect(find.text('Anotarme en lista de espera'), findsNothing);
    });
  });

  group('Mis fichas', () {
    Future<List<http.Request>> abrir(
      WidgetTester tester, {
      required bool enabled,
      bool falla = false,
    }) async {
      final pedidos = <http.Request>[];
      var salio = false;
      final client = ApiClient(
        httpClient: MockClient((request) async {
          pedidos.add(request);
          final ruta = request.url.path;
          if (ruta.contains('/appointments/waitlist/')) {
            if (request.method == 'DELETE') {
              salio = true;
              return http.Response('', 204);
            }
            if (falla) return _json({'detail': 'Boom'}, 500);
            return _json({
              'enabled': enabled,
              'results': enabled && !salio ? [_entrada()] : <Object>[],
            }, 200);
          }
          return _json(<Object>[], 200);
        }),
      );
      await tester.pumpWidget(
        MaterialApp(home: MyAppointmentsScreen(client: client)),
      );
      await tester.pumpAndSettle();
      return pedidos;
    }

    testWidgets('muestra la sección y «Salir de la lista» hace DELETE', (
      tester,
    ) async {
      _vistaGrande(tester);
      final pedidos = await abrir(tester, enabled: true);

      expect(find.text('En lista de espera'), findsOneWidget);
      expect(find.text('Laura Gómez'), findsOneWidget);
      expect(find.text('Eres el 2.º'), findsOneWidget);
      expect(find.text('Fechas: 20/11/2026 al 04/12/2026'), findsOneWidget);

      await tester.tap(find.text('Salir de la lista'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Sí, salir'));
      await tester.pumpAndSettle();

      final borrado = pedidos.firstWhere((r) => r.method == 'DELETE');
      expect(borrado.url.path, endsWith('/appointments/waitlist/w1/'));
      expect(find.text('En lista de espera'), findsNothing);
    });

    testWidgets('con enabled:false no aparece la sección', (tester) async {
      _vistaGrande(tester);
      await abrir(tester, enabled: false);
      expect(find.text('En lista de espera'), findsNothing);
      expect(find.text('Buscar profesionales'), findsOneWidget);
    });

    testWidgets('si la lista de espera falla, las fichas siguen', (
      tester,
    ) async {
      _vistaGrande(tester);
      await abrir(tester, enabled: true, falla: true);
      expect(find.text('En lista de espera'), findsNothing);
      expect(find.text('Buscar profesionales'), findsOneWidget);
    });
  });

  group('cuenta regresiva del detalle', () {
    Map<String, dynamic> pendiente(DateTime? vence) => {
      'id': 'f1',
      'patient': 'p1',
      'patient_name': 'Ana Pérez',
      'practitioner': 'pr1',
      'practitioner_name': 'Laura Gómez',
      'branch': 'b1',
      'branch_name': 'Sede Centro',
      'starts_at': DateTime.utc(2099, 1, 1, 13).toIso8601String(),
      'ends_at': DateTime.utc(2099, 1, 1, 13, 30).toIso8601String(),
      'status': 'pending_payment',
      'expires_at': vence?.toUtc().toIso8601String(),
      'fee': {'amount': '120.00', 'currency': 'BOB'},
    };

    Future<int Function()> abrir(WidgetTester tester, DateTime vence) async {
      var lecturas = 0;
      final client = ApiClient(
        httpClient: MockClient((_) async {
          lecturas++;
          return _json(pendiente(vence), 200);
        }),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: AppointmentDetailScreen(appointmentId: 'f1', client: client),
        ),
      );
      await tester.pump();
      await tester.pump();
      return () => lecturas;
    }

    testWidgets('muestra mm:ss y avanza cada segundo', (tester) async {
      await abrir(tester, DateTime.now().add(const Duration(seconds: 90)));

      expect(find.text('Tiempo para pagar'), findsOneWidget);
      expect(find.textContaining(RegExp(r'^01:[23]\d$')), findsOneWidget);

      // El reloj de la prueba es el real: se espera de verdad un segundo.
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 1100)),
      );
      await tester.pump(const Duration(seconds: 1));
      expect(find.textContaining(RegExp(r'^01:[12]\d$')), findsOneWidget);

      // Se desmonta la pantalla: el temporizador se cancela en dispose.
      await tester.pumpWidget(const SizedBox());
    });

    testWidgets('al llegar a cero recarga la ficha', (tester) async {
      final lecturas = await abrir(
        tester,
        DateTime.now().add(const Duration(milliseconds: 1500)),
      );
      expect(find.text('Tiempo para pagar'), findsOneWidget);
      expect(lecturas(), 1);

      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 1700)),
      );
      await tester.pump(const Duration(seconds: 1));
      await tester.pump();

      expect(find.text('Tiempo para pagar'), findsNothing);
      expect(lecturas(), 2);
    });

    testWidgets('sin vencimiento no hay cuenta regresiva', (tester) async {
      final client = ApiClient(
        httpClient: MockClient((_) async => _json(pendiente(null), 200)),
      );
      await tester.pumpWidget(
        MaterialApp(
          home: AppointmentDetailScreen(appointmentId: 'f1', client: client),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Tiempo para pagar'), findsNothing);
      expect(find.textContaining('Pagar'), findsWidgets);
    });
  });
}
