/// Recorrido de humo en un teléfono real: cada rol entra y abre sus pantallas.
///
/// No reemplaza a las pruebas de widget de `test/`, que usan respuestas
/// falsas. Ésta habla con un backend de verdad, así que encuentra lo que
/// ellas no pueden: un endpoint que cambió, un permiso que no se sembró, una
/// pantalla que revienta con datos reales.
///
/// Se corre con el celular por USB, el backend local en el 8000 y el puerto
/// redirigido (`adb reverse tcp:8000 tcp:8000`):
///
///     flutter drive --driver=test_driver/integration_test.dart \
///       --target=integration_test/recorrido_test.dart \
///       --dart-define=DEMO_PASSWORD=<la de los datos de prueba>
///
/// Las cuentas son las del dataset local (`seed_dataset`). La contraseña no
/// se escribe acá a propósito: no va al repositorio.
library;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:integration_test/integration_test.dart';
import 'package:mobile/app.dart';
import 'package:mobile/core/session/session.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme_controller.dart';
import 'package:mobile/core/widgets/organization_drawer.dart';

const _clave = String.fromEnvironment('DEMO_PASSWORD');
const _org = String.fromEnvironment('DEMO_ORG', defaultValue: 'chuquisaca');

/// Textos que delatan que una pantalla no cargó (ver `core/api/errors.dart`).
final _errores = RegExp(
  r'No se pudo conectar|tuvo un problema|No tenés permiso|no se pudo interpretar|'
  r'No se encontró|La petición no se pudo|sesión venció|no es válida',
);

late IntegrationTestWidgetsFlutterBinding _binding;
final _problemas = <String>[];

void main() {
  _binding = IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  setUpAll(() {
    if (_clave.isEmpty) {
      fail('Falta --dart-define=DEMO_PASSWORD=...');
    }
  });

  tearDownAll(() {
    // ignore: avoid_print
    print(_problemas.isEmpty
        ? 'RECORRIDO: todas las pantallas cargaron'
        : 'RECORRIDO: ${_problemas.length} problema(s)\n${_problemas.join('\n')}');
  });

  testWidgets('paciente', (tester) async {
    await _entrar(tester, 'paciente1@$_org.test', org: _org);
    for (final ruta in ['/specialties', '/clinical-record', '/dependents', '/history', '/assistant', '/profile']) {
      await _visitar(tester, 'paciente', ruta);
    }
  });

  for (final cuenta in ['recepcion1', 'medico1', 'admin']) {
    testWidgets(cuenta, (tester) async {
      await _entrar(tester, '$cuenta@$_org.test', org: _org);
      await _visitar(tester, cuenta, '/org');
      final user = _session(tester).user!;
      for (final seccion in seccionesDeOrganizacion.where((s) => user.can(s.permiso))) {
        await _visitar(tester, cuenta, seccion.ruta);
      }
      await _visitar(tester, cuenta, '/profile');
    });
  }

  testWidgets('superadministrador', (tester) async {
    await _entrar(tester, 'super@plataforma.local');
    for (final ruta in [
      '/platform/dashboard',
      '/platform/organizations',
      '/platform/plans',
      '/platform/subscriptions',
    ]) {
      await _visitar(tester, 'super', ruta);
    }
  });
}

Session _session(WidgetTester tester) =>
    SessionScope.of(tester.element(find.byType(Scaffold).first));

/// Bombea hasta que aparezca [finder]. No usa `pumpAndSettle`: la cabecera de
/// marca tiene una animación que no termina nunca.
Future<void> _esperar(WidgetTester tester, Finder finder,
    {Duration limite = const Duration(seconds: 20)}) async {
  final fin = DateTime.now().add(limite);
  while (DateTime.now().isBefore(fin)) {
    await tester.pump(const Duration(milliseconds: 200));
    if (finder.evaluate().isNotEmpty) return;
  }
  fail('No apareció: $finder');
}

Future<void> _quieto(WidgetTester tester, [int segundos = 3]) async {
  for (var i = 0; i < segundos * 5; i++) {
    await tester.pump(const Duration(milliseconds: 200));
  }
}

Future<void> _entrar(WidgetTester tester, String correo, {String org = ''}) async {
  // Cada rol empieza sin sesión guardada.
  await const FlutterSecureStorage().deleteAll();
  final session = Session();
  await session.restore();
  await tester.pumpWidget(CentroMedicoApp(session: session, tema: ThemeController()));
  // En Android hay que pasar la superficie a imagen antes de capturar, y la
  // conversión no sobrevive de un caso al siguiente.
  await _binding.convertFlutterSurfaceToImage();

  await _esperar(tester, find.text('Entrar'));
  await tester.enterText(find.widgetWithText(TextFormField, 'Centro médico'), org);
  await tester.enterText(find.widgetWithText(TextFormField, 'Correo electrónico'), correo);
  await tester.enterText(find.widgetWithText(TextFormField, 'Contraseña'), _clave);
  await tester.tap(find.text('Entrar'));

  await _esperar(tester, find.byIcon(Icons.account_circle_outlined));
  await _quieto(tester);
  await _captura(tester, '${correo.split('@').first}-inicio');
  expect(_session(tester).user, isNotNull, reason: 'No llegó el perfil de $correo');
}

Future<void> _visitar(WidgetTester tester, String rol, String ruta) async {
  final router = GoRouter.of(tester.element(find.byType(Scaffold).first));
  router.push(ruta);
  await _quieto(tester);

  final excepcion = tester.takeException();
  if (excepcion != null) _problemas.add('$rol $ruta: excepción $excepcion');

  final error = find.textContaining(_errores);
  if (error.evaluate().isNotEmpty) {
    final texto = (error.evaluate().first.widget as Text).data ?? '';
    _problemas.add('$rol $ruta: "$texto"');
  }

  await _captura(tester, '$rol${ruta.replaceAll('/', '-')}');
  if (router.canPop()) router.pop();
  await _quieto(tester, 1);
}

Future<void> _captura(WidgetTester tester, String nombre) async {
  await tester.pump();
  await _binding.takeScreenshot(nombre);
}
