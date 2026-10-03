/// La elección de tema claro, oscuro o "como el sistema", y dónde se guarda.
///
/// Sigue el mismo patrón que la sesión: un objeto que notifica
/// ([ThemeController], un `ValueNotifier`) colgado de un `InheritedNotifier`
/// ([ThemeScope]), y el guardado aparte ([ThemeStorage]) para poder
/// reemplazarlo en las pruebas. Sin paquete de gestión de estado por lo mismo
/// que explica `session_scope.dart`: esa decisión es del equipo.
///
/// **Por qué en `flutter_secure_storage` y no en `SharedPreferences`.** La
/// preferencia no es un secreto, pero la aplicación ya depende del
/// almacenamiento seguro y `SharedPreferences` sería una dependencia nueva
/// sólo para guardar una palabra. Se paga con una lectura un poco más lenta
/// al abrir (el Keystore), y por eso la aplicación arranca con "como el
/// sistema" y cambia en cuanto [ThemeController.restore] termina.
library;

import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Lee y escribe la elección. Una sola clave, aparte de las de la sesión.
class ThemeStorage {
  ThemeStorage({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _key = 'theme_mode';

  Future<String?> read() => _storage.read(key: _key);

  Future<void> write(String value) => _storage.write(key: _key, value: value);
}

class ThemeController extends ValueNotifier<ThemeMode> {
  ThemeController({ThemeStorage? storage})
    : _storage = storage ?? ThemeStorage(),
      super(ThemeMode.system);

  final ThemeStorage _storage;

  /// Se guarda el nombre (`system`, `light`, `dark`) y no el índice del enum:
  /// si Flutter reordena `ThemeMode`, un índice guardado pasaría a significar
  /// otra cosa sin que nada avise.
  static ThemeMode _parse(String? guardado) => ThemeMode.values.firstWhere(
    (m) => m.name == guardado,
    orElse: () => ThemeMode.system,
  );

  /// Aplica lo guardado. Si no hay nada, o el Keystore falla, queda "como el
  /// sistema": un tema que no se pudo leer no es motivo para que la
  /// aplicación no abra.
  Future<void> restore() async {
    try {
      value = _parse(await _storage.read());
    } catch (_) {
      value = ThemeMode.system;
    }
  }

  /// Cambia el tema en el momento y después lo guarda. Primero se aplica:
  /// quien toca "Oscuro" espera verlo ya, no cuando termine el Keystore.
  Future<void> set(ThemeMode mode) async {
    value = mode;
    try {
      await _storage.write(mode.name);
    } catch (_) {
      // Si no se pudo guardar, el cambio vale igual para esta vez; al
      // reabrir vuelve lo anterior, que es un mal menor que un error en
      // pantalla por una preferencia visual.
    }
  }
}

/// El nombre corto de cada opción, el mismo en el perfil y en los menús.
String etiquetaDeTema(ThemeMode mode) => switch (mode) {
  ThemeMode.system => 'Como el sistema',
  ThemeMode.light => 'Claro',
  ThemeMode.dark => 'Oscuro',
};

/// Acceso al controlador desde cualquier widget.
class ThemeScope extends InheritedNotifier<ThemeController> {
  const ThemeScope({
    super.key,
    required ThemeController controller,
    required super.child,
  }) : super(notifier: controller);

  /// `null` si no hay [ThemeScope] arriba. Las pantallas lo toleran y
  /// esconden el selector: así las pruebas que arman una pantalla suelta no
  /// tienen que montar también el tema.
  static ThemeController? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<ThemeScope>()?.notifier;
}
