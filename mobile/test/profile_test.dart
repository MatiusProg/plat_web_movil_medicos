/// Pruebas de la pantalla de perfil (US-05, móvil).
///
///     flutter test test/profile_test.dart
///
/// Lo que se prueba es lo del móvil: que se mande sólo lo que cambió, que el
/// par de tokens nuevo llegue a la sesión, que los errores caigan debajo de
/// su casilla y que el cierre de sesión esté acá. Las reglas —qué es
/// editable, la unicidad del correo, la política de contraseñas— se prueban
/// en el backend, en `tests/test_us05.py`.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/features/profile/profile_api.dart';
import 'package:mobile/features/profile/profile_screen.dart';

http.Response _json(Object cuerpo, int estado) => http.Response(
  jsonEncode(cuerpo),
  estado,
  headers: {'content-type': 'application/json; charset=utf-8'},
);

Map<String, dynamic> _perfil({String phone = '70000000'}) => {
  'id': 'u1',
  'email': 'ana@kolping.test',
  'first_name': 'Ana',
  'last_name': 'Ríos',
  'full_name': 'Ana Ríos',
  'phone': phone,
  'birth_date': null,
  'document_type': 'CI',
  'document_number': '5001',
  'organization': {'slug': 'kolping', 'name': 'Kolping'},
  'roles': [
    {'code': 'patient', 'name': 'Paciente'},
  ],
  'is_platform_admin': false,
  'is_active': true,
};

/// Lo que la pantalla le pidió a la sesión, para poder afirmarlo.
class _Sesion {
  NewTokens? tokens;
  int guardados = 0;
  int salidas = 0;
}

Future<_Sesion> _abrir(WidgetTester tester, MockClient mock) async {
  final sesion = _Sesion();
  // Alta a propósito: la pantalla es un `ListView`, que no construye lo que
  // queda fuera de la vista, y el cierre de sesión está al final.
  tester.view.physicalSize = const Size(800, 2400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      home: ProfileScreen(
        client: ApiClient(httpClient: mock),
        onTokens: (t) async => sesion.tokens = t,
        onSaved: () async => sesion.guardados++,
        onSignOut: () async => sesion.salidas++,
      ),
    ),
  );
  await tester.pumpAndSettle();
  return sesion;
}

Finder _campo(String etiqueta) =>
    find.widgetWithText(TextField, etiqueta);

void main() {
  testWidgets('muestra lo editable en casillas y lo demás como texto', (
    tester,
  ) async {
    await _abrir(tester, MockClient((_) async => _json(_perfil(), 200)));

    expect(_campo('Nombres'), findsOneWidget);
    expect(_campo('Correo'), findsOneWidget);
    // Punto (d): el documento y el rol se ven, pero no hay dónde cambiarlos.
    expect(find.text('Cédula de identidad 5001'), findsOneWidget);
    expect(find.text('Paciente'), findsOneWidget);
    expect(find.text('Kolping'), findsOneWidget);
    expect(_campo('Documento'), findsNothing);
  });

  testWidgets('guardar manda sólo el campo que cambió', (tester) async {
    Map<String, dynamic>? enviado;
    final sesion = await _abrir(
      tester,
      MockClient((request) async {
        if (request.method == 'PATCH') {
          expect(request.url.path, endsWith('/accounts/users/me/'));
          enviado = jsonDecode(request.body) as Map<String, dynamic>;
          return _json(_perfil(phone: '71234567'), 200);
        }
        return _json(_perfil(), 200);
      }),
    );

    await tester.enterText(_campo('Teléfono'), '71234567');
    await tester.pump();
    await tester.tap(find.text('Guardar cambios'));
    await tester.pumpAndSettle();

    expect(enviado, {'phone': '71234567'});
    expect(sesion.guardados, 1);
    expect(find.text('Tus datos se guardaron.'), findsOneWidget);
  });

  testWidgets('sin cambios, guardar está deshabilitado', (tester) async {
    await _abrir(tester, MockClient((_) async => _json(_perfil(), 200)));

    final boton = tester.widget<FilledButton>(
      find.widgetWithText(FilledButton, 'Guardar cambios'),
    );
    expect(boton.onPressed, isNull);
  });

  testWidgets('el correo repetido se muestra debajo del correo', (
    tester,
  ) async {
    await _abrir(
      tester,
      MockClient((request) async {
        if (request.method == 'PATCH') {
          return _json({
            'email': ['Ya hay otra cuenta con este correo en tu centro médico.'],
          }, 400);
        }
        return _json(_perfil(), 200);
      }),
    );

    await tester.enterText(_campo('Correo'), 'carla@kolping.test');
    await tester.pump();
    await tester.tap(find.text('Guardar cambios'));
    await tester.pumpAndSettle();

    expect(
      find.text('Ya hay otra cuenta con este correo en tu centro médico.'),
      findsOneWidget,
    );
  });

  testWidgets('cambiar la contraseña le pasa el par nuevo a la sesión', (
    tester,
  ) async {
    Map<String, dynamic>? enviado;
    final sesion = await _abrir(
      tester,
      MockClient((request) async {
        if (request.method == 'POST') {
          expect(request.url.path, endsWith('/accounts/users/me/password/'));
          enviado = jsonDecode(request.body) as Map<String, dynamic>;
          return _json({
            'detail': 'Tu contraseña se cambió.',
            'access': 'acceso-nuevo',
            'refresh': 'refresco-nuevo',
          }, 200);
        }
        return _json(_perfil(), 200);
      }),
    );

    await tester.enterText(_campo('Contraseña actual'), 'clave-actual-1');
    await tester.enterText(_campo('Contraseña nueva'), 'Otra-clave-42');
    await tester.enterText(
      _campo('Repite la contraseña nueva'),
      'Otra-clave-42',
    );
    await tester.pump();
    await tester.ensureVisible(find.text('Cambiar contraseña'));
    await tester.tap(find.text('Cambiar contraseña'));
    await tester.pumpAndSettle();

    expect(enviado, {
      'current_password': 'clave-actual-1',
      'password': 'Otra-clave-42',
      'password_confirmation': 'Otra-clave-42',
    });
    expect(sesion.tokens?.access, 'acceso-nuevo');
    expect(sesion.tokens?.refresh, 'refresco-nuevo');
    // No cierra la sesión (punto c).
    expect(sesion.salidas, 0);
    expect(find.text('Tu contraseña se cambió.'), findsOneWidget);
  });

  testWidgets('la contraseña actual equivocada cae debajo de su casilla', (
    tester,
  ) async {
    final sesion = await _abrir(
      tester,
      MockClient((request) async {
        if (request.method == 'POST') {
          return _json({
            'code': 'contrasena_actual_incorrecta',
            'current_password': ['La contraseña actual no es correcta.'],
          }, 400);
        }
        return _json(_perfil(), 200);
      }),
    );

    await tester.enterText(_campo('Contraseña actual'), 'no-es-esta');
    await tester.enterText(_campo('Contraseña nueva'), 'Otra-clave-42');
    await tester.enterText(
      _campo('Repite la contraseña nueva'),
      'Otra-clave-42',
    );
    await tester.pump();
    await tester.ensureVisible(find.text('Cambiar contraseña'));
    await tester.tap(find.text('Cambiar contraseña'));
    await tester.pumpAndSettle();

    expect(find.text('La contraseña actual no es correcta.'), findsOneWidget);
    expect(sesion.tokens, isNull);
  });

  testWidgets('el cierre de sesión está en el perfil', (tester) async {
    final sesion = await _abrir(
      tester,
      MockClient((_) async => _json(_perfil(), 200)),
    );

    await tester.ensureVisible(find.text('Cerrar sesión'));
    await tester.tap(find.text('Cerrar sesión'));
    await tester.pump();

    expect(sesion.salidas, 1);
  });

  testWidgets('si no carga, lo dice y deja reintentar', (tester) async {
    var intentos = 0;
    await _abrir(
      tester,
      MockClient((_) async {
        intentos++;
        return intentos == 1
            ? _json({'detail': 'Se cayó.'}, 500)
            : _json(_perfil(), 200);
      }),
    );

    expect(find.text('No se pudo cargar tu perfil.'), findsOneWidget);

    await tester.tap(find.text('Reintentar'));
    await tester.pumpAndSettle();

    expect(_campo('Nombres'), findsOneWidget);
  });
}
