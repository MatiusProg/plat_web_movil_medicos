/// US-28 — Las notificaciones push del teléfono.
///
/// El backend no le habla al teléfono: le pide a Firebase Cloud Messaging
/// (FCM) que entregue el aviso. Para eso FCM le da a cada instalación un
/// **token**, la «dirección» de este teléfono, que la app registra en
/// `/notifications/devices/` al iniciar sesión y borra al cerrarla.
///
/// **La configuración llega por `--dart-define`, no por archivo.** Igual que
/// `API_BASE_URL`: el `google-services.json` no entra al repositorio. Para
/// probar el push:
///
///     flutter run --dart-define=API_BASE_URL=http://192.168.0.15:8000/api \
///       --dart-define=FIREBASE_API_KEY=... \
///       --dart-define=FIREBASE_APP_ID=... \
///       --dart-define=FIREBASE_MESSAGING_SENDER_ID=... \
///       --dart-define=FIREBASE_PROJECT_ID=...
///
/// Sin esos cuatro valores la app arranca igual, sin push: nadie del equipo
/// queda bloqueado por no tener Firebase. Los avisos le siguen llegando por
/// correo.
///
/// Cómo se ve el aviso según dónde esté la app:
///
/// - **Cerrada o en segundo plano:** Android lo muestra solo en la barra.
/// - **Abierta:** Android no lo muestra; lo muestra esta clase con
///   `flutter_local_notifications`.
/// - **Al tocarlo**, en los tres casos, se abre la ficha (`/appointments/<id>`).
///
/// **Token de registro y no FID.** `firebase_messaging` 17 marca como
/// obsoletos `getToken`, `onTokenRefresh` y `deleteToken` en favor de
/// `register()`/`onRegistered`, que entregan el *Firebase Installation ID*
/// (FID). Se siguen usando los primeros a propósito: el backend manda con el
/// campo `token` de la API HTTP v1 (`backend/notifications/push.py`), que es
/// lo documentado y probado. Pasar a FID es cambiar las dos puntas juntas: acá
/// `register()`/`onRegistered`, y allá `token` por `fid`.
library;

import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import '../api/client.dart';

/// Los cuatro valores del proyecto de Firebase (consola > Configuración del
/// proyecto > tu app Android). No son secretos como la credencial del
/// backend, pero tampoco van al repositorio.
class FirebaseConfig {
  const FirebaseConfig._();

  static const String apiKey = String.fromEnvironment('FIREBASE_API_KEY');
  static const String appId = String.fromEnvironment('FIREBASE_APP_ID');
  static const String messagingSenderId =
      String.fromEnvironment('FIREBASE_MESSAGING_SENDER_ID');
  static const String projectId = String.fromEnvironment('FIREBASE_PROJECT_ID');

  static bool get completa =>
      apiKey.isNotEmpty &&
      appId.isNotEmpty &&
      messagingSenderId.isNotEmpty &&
      projectId.isNotEmpty;
}

/// Lo que la sesión necesita del push: registrar el teléfono al entrar y
/// olvidarlo al salir. Es una interfaz para que las pruebas no toquen
/// Firebase.
abstract class DeviceRegistrar {
  Future<void> registrar(ApiClient api);
  Future<void> olvidar(ApiClient api);
}

class Push implements DeviceRegistrar {
  Push._();

  /// Una instancia aparte de la de la app, para las pruebas.
  @visibleForTesting
  Push.paraPruebas();

  static final Push instance = Push._();

  /// El canal de Android de los avisos de fichas. El backend manda el mismo
  /// id (`notifications/push.py`, `ANDROID_CHANNEL`).
  static const AndroidNotificationChannel _canal = AndroidNotificationChannel(
    'fichas',
    'Fichas',
    description: 'Confirmación, recordatorio y cancelación de tus fichas.',
    importance: Importance.high,
  );

  final FlutterLocalNotificationsPlugin _locales =
      FlutterLocalNotificationsPlugin();

  Future<bool>? _iniciando;

  /// El token registrado, para poder borrarlo al cerrar sesión.
  String? _token;

  /// Con qué cliente se registró, para volver a registrar si FCM rota el
  /// token. Null = no hay nadie adentro.
  ApiClient? _api;
  StreamSubscription<String>? _renovaciones;

  void Function(String appointmentId)? _alAbrir;

  /// Una ficha tocada antes de que la app pudiera abrirla.
  String? _pendiente;

  /// Qué hacer cuando se toca un aviso. Lo fija la app, que es la que tiene
  /// el router; si el aviso llegó antes, se entrega ahora.
  set alAbrirFicha(void Function(String appointmentId) callback) {
    _alAbrir = callback;
    final pendiente = _pendiente;
    if (pendiente != null) {
      _pendiente = null;
      callback(pendiente);
    }
  }

  /// Prepara Firebase. Se puede llamar varias veces: inicia una sola.
  ///
  /// Devuelve si el push quedó disponible. Sin los `--dart-define`, fuera de
  /// Android o si Firebase falla, devuelve `false` y la app sigue sin push.
  Future<bool> iniciar() => _iniciando ??= _iniciar();

  Future<bool> _iniciar() async {
    if (kIsWeb ||
        defaultTargetPlatform != TargetPlatform.android ||
        !FirebaseConfig.completa) {
      return false;
    }
    try {
      await Firebase.initializeApp(
        options: const FirebaseOptions(
          apiKey: FirebaseConfig.apiKey,
          appId: FirebaseConfig.appId,
          messagingSenderId: FirebaseConfig.messagingSenderId,
          projectId: FirebaseConfig.projectId,
        ),
      );

      await _locales.initialize(
        settings: const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        ),
        onDidReceiveNotificationResponse: (respuesta) =>
            _abrir(respuesta.payload),
      );
      await _locales
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(_canal);

      FirebaseMessaging.onMessage.listen(_mostrarConLaAppAbierta);
      FirebaseMessaging.onMessageOpenedApp
          .listen((mensaje) => _abrir(mensaje.data['appointment_id']));

      // La app estaba cerrada y se abrió tocando el aviso: el de FCM, o uno
      // que mostró esta misma clase antes de que la cerraran.
      final inicial = await FirebaseMessaging.instance.getInitialMessage();
      if (inicial != null) _abrir(inicial.data['appointment_id']);
      final lanzada = await _locales.getNotificationAppLaunchDetails();
      if (lanzada?.didNotificationLaunchApp ?? false) {
        _abrir(lanzada!.notificationResponse?.payload);
      }
      return true;
    } catch (error) {
      debugPrint('Push desactivado: $error');
      return false;
    }
  }

  /// Registra este teléfono para los avisos de quien acaba de entrar.
  ///
  /// Pide el permiso de notificaciones (Android 13 en adelante). Si la
  /// persona lo niega no se registra nada: el aviso no se vería, y el correo
  /// le sigue llegando igual. Nunca lanza: sin push la app funciona.
  @override
  Future<void> registrar(ApiClient api) async {
    if (!await iniciar()) return;
    try {
      final permiso = await FirebaseMessaging.instance.requestPermission();
      if (permiso.authorizationStatus == AuthorizationStatus.denied) return;

      // ignore: deprecated_member_use — token y no FID, ver arriba.
      final token = await FirebaseMessaging.instance.getToken();
      if (token == null) return;
      // En depuración se imprime, para mandar un mensaje de prueba desde la
      // consola de Firebase (Messaging > Enviar mensaje de prueba). Nunca en
      // la APK de release: el token es la dirección de este teléfono.
      if (kDebugMode) debugPrint('Token de FCM de este teléfono: $token');
      _api = api;
      await _enviar(token);

      // FCM puede cambiar el token (al restaurar la app, por ejemplo): el
      // nuevo se registra solo.
      _renovaciones ??= FirebaseMessaging.instance
          // ignore: deprecated_member_use — token y no FID, ver arriba.
          .onTokenRefresh
          .listen((nuevo) => unawaited(_enviar(nuevo)));
    } catch (error) {
      debugPrint('No se pudo registrar el teléfono para los avisos: $error');
    }
  }

  Future<void> _enviar(String token) async {
    final api = _api;
    if (api == null) return;
    _token = token;
    try {
      await api.post(
        '/notifications/devices/',
        body: {'token': token, 'platform': 'android'},
      );
    } catch (error) {
      debugPrint('El backend no registró el teléfono: $error');
    }
  }

  /// Olvida este teléfono: quien sale no tiene que seguir recibiendo avisos.
  ///
  /// Borra el token en el backend y además lo invalida en FCM. Lo segundo
  /// cubre el caso en que lo primero falla —sin red, o con la sesión ya
  /// vencida—: un token invalidado hace que FCM conteste «ya no existe» y el
  /// backend borra la fila en el próximo aviso.
  @override
  Future<void> olvidar(ApiClient api) async {
    _api = null;
    if (!await iniciar()) return;
    try {
      final token = _token ??
          // ignore: deprecated_member_use — token y no FID, ver arriba.
          await FirebaseMessaging.instance.getToken();
      _token = null;
      if (token != null) {
        await api.send('DELETE', '/notifications/devices/',
            body: {'token': token});
      }
    } catch (error) {
      debugPrint('El backend no olvidó el teléfono: $error');
    }
    try {
      // ignore: deprecated_member_use — token y no FID, ver arriba.
      await FirebaseMessaging.instance.deleteToken();
    } catch (error) {
      debugPrint('FCM no invalidó el token: $error');
    }
  }

  /// Con la app abierta Android no muestra el aviso de FCM: se muestra acá.
  void _mostrarConLaAppAbierta(RemoteMessage mensaje) {
    final aviso = mensaje.notification;
    if (aviso == null) return;
    unawaited(_locales.show(
      id: (mensaje.messageId ?? '${DateTime.now()}').hashCode & 0x7fffffff,
      title: aviso.title,
      body: aviso.body,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          _canal.id,
          _canal.name,
          channelDescription: _canal.description,
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
      payload: mensaje.data['appointment_id'],
    ));
  }

  /// Lo mismo que pasa al tocar un aviso, para las pruebas.
  @visibleForTesting
  void tocarAviso(String? appointmentId) => _abrir(appointmentId);

  void _abrir(String? appointmentId) {
    if (appointmentId == null || appointmentId.isEmpty) return;
    final alAbrir = _alAbrir;
    if (alAbrir == null) {
      _pendiente = appointmentId;
      return;
    }
    alAbrir(appointmentId);
  }
}
