/// El error de la API, con su código estable.
///
/// Es el espejo de `ErrorApi` del frontend web (`frontend/src/api/tipos.ts`), y
/// a propósito: el backend responde los mismos códigos a los dos clientes, y
/// tener dos vocabularios distintos para lo mismo obliga a traducir en cada
/// pantalla.
///
/// **Se compara contra `code`, nunca contra el texto del mensaje.** El texto
/// puede cambiar —de hecho cambia, es lo que lee una persona—; el código es el
/// contrato.
library;

class ApiError implements Exception {
  const ApiError(
    this.message,
    this.code,
    this.status, {
    this.fieldErrors,
    this.lockedUntil,
  });

  /// Lo que se le muestra a la persona.
  final String message;

  /// `credenciales_invalidas`, `cuenta_bloqueada`, `enlace_vencido`, …
  final String code;

  /// El HTTP. `0` cuando la petición no llegó a salir.
  final int status;

  /// Validaciones de forma, tal como las devuelve DRF: `{campo: [mensaje]}`.
  final Map<String, List<String>>? fieldErrors;

  /// Sólo en `cuenta_bloqueada` (RNF-07): cuándo se libera la cuenta.
  final DateTime? lockedUntil;

  /// El primer mensaje del campo, para pintarlo debajo del input.
  String? forField(String field) => fieldErrors?[field]?.first;

  /// La petición no llegó a salir: no hay red, o el backend no está corriendo.
  bool get isOffline => code == 'sin_conexion';

  /// La sesión no sirve más y hay que volver a entrar.
  bool get isSessionExpired =>
      code == 'refresh_invalido' || code == 'token_sin_organizacion';

  @override
  String toString() => 'ApiError($status, $code): $message';

  /// Construye el error a partir del cuerpo que devolvió el backend.
  ///
  /// DRF mezcla dos formas en la misma respuesta: `detail` con el mensaje
  /// general y `campo: [...]` con las validaciones. Acá se separan las dos para
  /// que la pantalla no tenga que hurgar en el mapa.
  factory ApiError.fromResponse(int status, Object? body) {
    final map = body is Map<String, dynamic> ? body : const <String, dynamic>{};

    final code = map['code'] is String ? map['code'] as String : 'desconocido';

    final fields = <String, List<String>>{};
    map.forEach((key, value) {
      if (key == 'code' || key == 'detail') return;
      if (value is List && value.every((item) => item is String)) {
        fields[key] = value.cast<String>();
      }
    });

    final detail = map['detail'] is String ? map['detail'] as String : null;
    final firstField = fields.values.isEmpty ? null : fields.values.first.first;

    DateTime? lockedUntil;
    if (map['locked_until'] is String) {
      lockedUntil = DateTime.tryParse(map['locked_until'] as String);
    }

    return ApiError(
      detail ?? firstField ?? _defaultMessage(status),
      code,
      status,
      fieldErrors: fields.isEmpty ? null : fields,
      lockedUntil: lockedUntil,
    );
  }

  static const ApiError offline = ApiError(
    'No se pudo conectar con el servidor. Revisá tu conexión.',
    'sin_conexion',
    0,
  );

  static String _defaultMessage(int status) {
    if (status >= 500) {
      return 'El servidor tuvo un problema. Intentá de nuevo en un momento.';
    }
    if (status == 404) return 'No se encontró lo que buscabas.';
    if (status == 403) return 'No tenés permiso para hacer esto.';
    return 'La petición no se pudo completar.';
  }
}
