/// Lectura del contenido de un JWT, sin verificar la firma.
///
/// **Acá no se valida nada y no se pretende validar.** Quien decide si un token
/// sirve es el backend, que tiene la clave; el cliente sólo necesita mirar el
/// `exp` para saber si conviene renovar antes de mandar la petición siguiente.
/// Leer un JWT sin verificar la firma es correcto exactamente para esto y para
/// nada más: ninguna decisión de permisos puede salir de estos claims.
///
/// El proyecto emite los tokens con `accounts.tokens.tokens_for_user`, que
/// agrega `organization_id` e `is_platform_admin`. Se leen sólo para depurar y
/// para el caso raro del token viejo sin contexto, que el backend rechaza con
/// `token_sin_organizacion`.
library;

import 'dart:convert';

class Jwt {
  const Jwt._();

  /// El payload del token, o `null` si no tiene forma de JWT.
  static Map<String, dynamic>? payload(String token) {
    final parts = token.split('.');
    if (parts.length != 3) return null;

    try {
      // El payload va en base64url y sin relleno; `base64Url.decode` lo exige,
      // así que hay que reponerlo antes de decodificar.
      final normalized = base64Url.normalize(parts[1]);
      final decoded = utf8.decode(base64Url.decode(normalized));
      final data = jsonDecode(decoded);
      return data is Map<String, dynamic> ? data : null;
    } catch (_) {
      return null;
    }
  }

  /// Cuándo vence el token, en hora local. `null` si no se puede leer.
  static DateTime? expiry(String token) {
    final exp = payload(token)?['exp'];
    if (exp is! int) return null;
    return DateTime.fromMillisecondsSinceEpoch(exp * 1000);
  }

  /// Si el token vence dentro de [margin] —o ya venció—.
  ///
  /// Un token ilegible cuenta como vencido: es preferible intentar una
  /// renovación de más que mandar una petición que va a fallar con 401.
  static bool expiresWithin(String token, Duration margin) {
    final expiry = Jwt.expiry(token);
    if (expiry == null) return true;
    return expiry.isBefore(DateTime.now().add(margin));
  }
}
