/// Guardado de la sesión en el almacenamiento seguro del sistema.
///
/// **No es `SharedPreferences`.** Ahí los valores quedan en un archivo XML
/// legible en cualquier teléfono con root o con el respaldo activado, y lo que
/// se guarda acá son tokens que autentican a una persona contra su historia
/// clínica. `flutter_secure_storage` usa el Keystore de Android y el Keychain
/// de iOS, que es donde corresponde.
///
/// Se guardan tres cosas y ninguna más:
///
///   * el token de acceso, que dura 30 minutos,
///   * el de refresco, que dura 7 días y es el que sostiene la sesión,
///   * el slug de la organización, que el interceptor manda en cada petición
///     y que además sirve para prellenar el formulario de ingreso.
///
/// Los datos del usuario **no** se guardan: llegan en la respuesta del login y
/// viven en memoria. Si hicieran falta después de reabrir la aplicación, se
/// piden al backend; duplicarlos en el teléfono es una copia que se desactualiza
/// y que hay que acordarse de borrar al cerrar sesión.
library;

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class TokenStorage {
  TokenStorage({FlutterSecureStorage? storage})
      : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const _accessKey = 'access_token';
  static const _refreshKey = 'refresh_token';
  static const _organizationKey = 'organization';

  Future<String?> readAccess() => _storage.read(key: _accessKey);

  Future<String?> readRefresh() => _storage.read(key: _refreshKey);

  Future<String?> readOrganization() => _storage.read(key: _organizationKey);

  /// Guarda el par de tokens. Se llama al iniciar sesión y en cada renovación.
  ///
  /// El backend **rota** el token de refresco (`ROTATE_REFRESH_TOKENS`), así
  /// que en cada renovación llegan dos valores nuevos y hay que guardar los
  /// dos: quedarse con el refresco viejo deja la sesión muerta en la
  /// renovación siguiente, porque el anterior ya fue a la lista negra.
  Future<void> saveTokens({
    required String access,
    required String refresh,
  }) async {
    await _storage.write(key: _accessKey, value: access);
    await _storage.write(key: _refreshKey, value: refresh);
  }

  Future<void> saveOrganization(String slug) =>
      _storage.write(key: _organizationKey, value: slug);

  /// Borra los tokens y deja el slug.
  ///
  /// El slug se conserva a propósito: no es un secreto, y quien cierra sesión
  /// en un centro médico casi siempre vuelve a entrar al mismo. Borrarlo
  /// obliga a escribirlo de nuevo cada vez sin ganar nada.
  Future<void> clearTokens() async {
    await _storage.delete(key: _accessKey);
    await _storage.delete(key: _refreshKey);
  }
}
