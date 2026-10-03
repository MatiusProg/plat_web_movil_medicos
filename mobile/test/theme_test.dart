/// Pruebas del selector de tema (claro, oscuro o como el sistema).
///
///     flutter test test/theme_test.dart
///
/// Lo que importa: que la elección sobreviva a reabrir la aplicación, que
/// sin nada guardado —o con el Keystore fallando— quede "como el sistema", y
/// que tocar el selector del perfil cambie el tema de verdad, no sólo el
/// botón marcado.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/theme/theme.dart';
import 'package:mobile/core/theme/theme_controller.dart';
import 'package:mobile/core/widgets/theme_selector.dart';
import 'package:mobile/features/profile/profile_screen.dart';

/// El almacenamiento en memoria: el Keystore no existe en las pruebas.
class MemoryThemeStorage extends ThemeStorage {
  MemoryThemeStorage([this.guardado]);

  String? guardado;
  int escrituras = 0;

  @override
  Future<String?> read() async => guardado;

  @override
  Future<void> write(String value) async {
    guardado = value;
    escrituras++;
  }
}

class _StorageQueFalla extends ThemeStorage {
  @override
  Future<String?> read() async => throw Exception('Keystore no disponible');

  @override
  Future<void> write(String value) async =>
      throw Exception('Keystore no disponible');
}

Map<String, dynamic> _perfil() => {
  'id': 'u1',
  'email': 'ana@kolping.test',
  'first_name': 'Ana',
  'last_name': 'Ríos',
  'full_name': 'Ana Ríos',
  'phone': '70000000',
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

void main() {
  group('ThemeController', () {
    test('por omisión es "como el sistema"', () async {
      final tema = ThemeController(storage: MemoryThemeStorage());
      expect(tema.value, ThemeMode.system);
      await tema.restore();
      expect(tema.value, ThemeMode.system);
    });

    test('guarda la elección y otro controlador la restaura', () async {
      final storage = MemoryThemeStorage();
      final tema = ThemeController(storage: storage);

      await tema.set(ThemeMode.dark);
      expect(tema.value, ThemeMode.dark);
      // Por nombre y no por índice (ver `_parse`).
      expect(storage.guardado, 'dark');

      // "Reabrir la aplicación": un controlador nuevo sobre lo guardado.
      final reabierto = ThemeController(storage: storage);
      await reabierto.restore();
      expect(reabierto.value, ThemeMode.dark);
    });

    test('un valor guardado desconocido cae en "como el sistema"', () async {
      final tema = ThemeController(storage: MemoryThemeStorage('violeta'));
      await tema.restore();
      expect(tema.value, ThemeMode.system);
    });

    test('si el Keystore falla, no rompe y el cambio vale igual', () async {
      final tema = ThemeController(storage: _StorageQueFalla());
      await tema.restore();
      expect(tema.value, ThemeMode.system);
      await tema.set(ThemeMode.light);
      expect(tema.value, ThemeMode.light);
    });
  });

  group('Selector en el perfil', () {
    Future<ThemeController> abrir(
      WidgetTester tester,
      MemoryThemeStorage storage,
    ) async {
      final tema = ThemeController(storage: storage);
      tester.view.physicalSize = const Size(800, 2800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.reset);
      // Igual que `app.dart`: el `MaterialApp` toma `themeMode` del
      // controlador, así se comprueba que el tema cambia de verdad.
      await tester.pumpWidget(
        ThemeScope(
          controller: tema,
          child: ValueListenableBuilder<ThemeMode>(
            valueListenable: tema,
            builder: (context, modo, _) => MaterialApp(
              theme: AppTheme.light,
              darkTheme: AppTheme.dark,
              themeMode: modo,
              home: ProfileScreen(
                client: ApiClient(
                  httpClient: MockClient(
                    (_) async => http.Response(
                      jsonEncode(_perfil()),
                      200,
                      headers: {
                        'content-type': 'application/json; charset=utf-8',
                      },
                    ),
                  ),
                ),
                onTokens: (_) async {},
                onSaved: () async {},
                onSignOut: () async {},
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      return tema;
    }

    Brightness brillo(WidgetTester tester) =>
        Theme.of(tester.element(find.byType(ProfileScreen))).brightness;

    testWidgets('muestra Apariencia con las tres opciones', (tester) async {
      await abrir(tester, MemoryThemeStorage());

      expect(find.text('APARIENCIA'), findsOneWidget);
      expect(find.byType(ThemeSelector), findsOneWidget);
      expect(find.text('Sistema'), findsOneWidget);
      expect(find.text('Claro'), findsOneWidget);
      expect(find.text('Oscuro'), findsOneWidget);
    });

    testWidgets('tocar "Oscuro" cambia el tema y lo guarda', (tester) async {
      final storage = MemoryThemeStorage();
      final tema = await abrir(tester, storage);
      expect(brillo(tester), Brightness.light); // el sistema de prueba es claro

      await tester.tap(find.text('Oscuro'));
      await tester.pumpAndSettle();

      expect(tema.value, ThemeMode.dark);
      expect(storage.guardado, 'dark');
      expect(brillo(tester), Brightness.dark);

      await tester.tap(find.text('Claro'));
      await tester.pumpAndSettle();
      expect(tema.value, ThemeMode.light);
      expect(storage.guardado, 'light');
      expect(brillo(tester), Brightness.light);
    });

    testWidgets('sin ThemeScope, el perfil no muestra la sección', (
      tester,
    ) async {
      await tester.pumpWidget(
        MaterialApp(
          home: ProfileScreen(
            client: ApiClient(
              httpClient: MockClient(
                (_) async => http.Response(
                  jsonEncode(_perfil()),
                  200,
                  headers: {'content-type': 'application/json; charset=utf-8'},
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(ThemeSelector), findsNothing);
    });
  });

  testWidgets('el acceso rápido del menú abre el selector', (tester) async {
    final tema = ThemeController(storage: MemoryThemeStorage());
    await tester.pumpWidget(
      ThemeScope(
        controller: tema,
        child: const MaterialApp(home: Scaffold(body: ThemeDrawerTile())),
      ),
    );

    expect(find.text('Tema: Sistema'), findsOneWidget);
    await tester.tap(find.text('Tema: Sistema'));
    await tester.pumpAndSettle();
    expect(find.byType(ThemeSelector), findsOneWidget);

    await tester.tap(find.text('Oscuro'));
    await tester.pumpAndSettle();
    expect(tema.value, ThemeMode.dark);
    expect(find.text('Tema: Oscuro'), findsOneWidget);
  });
}
