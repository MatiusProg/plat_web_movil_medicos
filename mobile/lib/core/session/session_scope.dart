/// Acceso a la sesión desde cualquier widget, sin pasarla por parámetro.
///
/// Es un `InheritedNotifier` y no un paquete de gestión de estado. El shell
/// necesita exactamente esto —un objeto que notifica cuando cambia— y elegir
/// entre Provider, Riverpod o Bloc es una decisión del equipo, no algo que deba
/// quedar decidido de hecho por el andamiaje. Cuando se acuerde una, se cambia
/// este archivo y nada más.
///
/// Uso:
///
///     final session = SessionScope.of(context);
///     if (session.user?.can('scheduling.slot.read') ?? false) { … }
library;

import 'package:flutter/widgets.dart';

import 'session.dart';

class SessionScope extends InheritedNotifier<Session> {
  const SessionScope({
    super.key,
    required Session session,
    required super.child,
  }) : super(notifier: session);

  static Session of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<SessionScope>();
    assert(scope != null, 'SessionScope no está sobre este widget.');
    return scope!.notifier!;
  }
}
