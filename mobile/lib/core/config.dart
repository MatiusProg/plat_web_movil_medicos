/// Configuración del entorno.
///
/// La URL de la API llega por `--dart-define` y no por un archivo: el valor
/// cambia entre la máquina de cada integrante, el teléfono y el despliegue, y
/// un archivo con la URL adentro termina siempre commiteado con la de alguien.
///
/// **En el celular, la API no está en `localhost`.** El equipo trabaja con un
/// teléfono conectado por USB y sin emulador (ver `docs/entorno/setup-movil.md`),
/// y para el teléfono `localhost` es el propio teléfono: el backend no está
/// ahí. Hay que pasarle la IP de la máquina en la red local, con Django
/// levantado como `runserver 0.0.0.0:8000`:
///
///     flutter run --dart-define=API_BASE_URL=http://192.168.0.15:8000/api
///
/// El valor por omisión sirve sólo para correr la aplicación en el navegador
/// de la propia máquina —`flutter run -d chrome`—, que es como se comprueba el
/// shell sin depender del teléfono.
library;

class Config {
  const Config._();

  /// Base de la API, sin barra final.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api',
  );

  /// Margen para renovar el token de acceso antes de que venza.
  ///
  /// El de acceso dura 30 minutos (`ACCESS_TOKEN_LIFETIME`). Renovar un minuto
  /// antes evita el caso en que el token era válido al armar la petición y ya
  /// no lo es cuando llega al servidor.
  static const Duration refreshMargin = Duration(minutes: 1);

  /// Cuánto se espera a la API antes de darla por caída.
  ///
  /// Con el teléfono por USB contra el backend de la red local, una respuesta
  /// que tarda más que esto es un problema de red, no del servidor.
  static const Duration timeout = Duration(seconds: 20);
}
