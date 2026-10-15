/// US-28 — El teléfono se registra para los avisos al entrar y se olvida al
/// salir.
///
/// Firebase no se toca: la sesión recibe un registrador falso. Lo que se
/// prueba es el enganche —cuándo se registra y cuándo se olvida— y que sin la
/// configuración de Firebase la app sigue funcionando.
library;

import 'package:flutter_test/flutter_test.dart';
import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/notifications/push.dart';
import 'package:mobile/core/session/session.dart';

import 'defectos_sesion_test.dart' show MemoryStorage, tokenQueVence;

class RegistradorFalso implements DeviceRegistrar {
  final List<String> llamadas = [];

  @override
  Future<void> registrar(ApiClient api) async => llamadas.add('registrar');

  @override
  Future<void> olvidar(ApiClient api) async => llamadas.add('olvidar');
}

CurrentUser usuario({bool superadmin = false}) => CurrentUser(
      id: 'u1',
      email: 'ana@centro.test',
      fullName: 'Ana Ríos',
      organization: superadmin ? null : 'centro',
      isPlatformAdmin: superadmin,
      roles: superadmin ? const [] : const ['patient'],
      permissions: const [],
    );

Future<Session> entrar(RegistradorFalso registrador, {bool superadmin = false}) async {
  final session = Session(storage: MemoryStorage(), devices: registrador);
  await session.saveSession(
    access: tokenQueVence(const Duration(minutes: 30)),
    refresh: tokenQueVence(const Duration(days: 7)),
    organization: superadmin ? '' : 'centro',
    user: usuario(superadmin: superadmin),
  );
  return session;
}

void main() {
  test('al iniciar sesión se registra el teléfono', () async {
    final registrador = RegistradorFalso();
    await entrar(registrador);
    expect(registrador.llamadas, ['registrar']);
  });

  test('el superadministrador no registra el teléfono: no tiene fichas', () async {
    final registrador = RegistradorFalso();
    await entrar(registrador, superadmin: true);
    expect(registrador.llamadas, isEmpty);
  });

  test('al cerrar sesión se olvida el teléfono', () async {
    final registrador = RegistradorFalso();
    final session = await entrar(registrador);

    await session.signOut();

    expect(registrador.llamadas, ['registrar', 'olvidar']);
    expect(session.isSignedIn, isFalse);
  });

  test('sin la configuración de Firebase el push no arranca y nada falla',
      () async {
    // Las pruebas corren sin los --dart-define de Firebase.
    expect(FirebaseConfig.completa, isFalse);
    expect(await Push.instance.iniciar(), isFalse);
    await Push.instance.registrar(ApiClient());
    await Push.instance.olvidar(ApiClient());
  });

  test('un aviso tocado antes de que la app esté lista se abre al estarlo', () {
    // Con la app cerrada, el toque llega antes de que exista el router.
    final push = Push.paraPruebas()..tocarAviso('ficha-1');
    final abiertas = <String>[];

    push.alAbrirFicha = abiertas.add;
    expect(abiertas, ['ficha-1']);

    push.tocarAviso('ficha-2');
    expect(abiertas, ['ficha-1', 'ficha-2']);
  });

  test('un aviso sin ficha no abre nada', () {
    final abiertas = <String>[];
    Push.paraPruebas()
      ..alAbrirFicha = abiertas.add
      ..tocarAviso(null)
      ..tocarAviso('');
    expect(abiertas, isEmpty);
  });
}
