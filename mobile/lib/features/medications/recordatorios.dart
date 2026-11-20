/// US-49 — Los avisos para tomar los medicamentos.
///
/// **Son notificaciones locales**: el teléfono las programa al activar el
/// recordatorio y suenan aunque no haya conexión ni servidor. Lo único que
/// viaja al backend son las tomas que el paciente marca, para que el médico
/// vea el cumplimiento.
///
/// Cómo funciona:
///
/// - **Activar** un medicamento programa una notificación por toma desde la
///   hora de la primera que elige el paciente: «cada 8 horas por 5 días» son
///   15 avisos. Las que ya pasaron no se programan.
/// - El aviso dice «Hora de tu Loratadina 10 mg: 1 comprimido» y trae
///   **«Tomada»** y **«Posponer 15 min»**. Tocarlo abre *Mis medicamentos*.
/// - Una toma marcada (desde el aviso o desde la app) queda **pendiente** en el
///   teléfono hasta que el backend la recibe. Si el servidor ya la tenía
///   (409), cuenta como enviada: no se duplica.
/// - **Al cerrar sesión se cancelan todos los avisos** y se borra lo guardado:
///   quien entra después en el mismo teléfono no recibe los de otro.
///
/// El aviso y el push de las fichas (US-28) comparten el mismo plugin. Los de
/// medicamentos se reconocen por el payload `med|<medicamento>|<toma>`.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:ui' show DartPluginRegistrant;

import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:timezone/data/latest_all.dart' as tzdata;
import 'package:timezone/timezone.dart' as tz;

import 'package:mobile/core/api/client.dart';

import 'medications_api.dart';

/// Cuánto se corre un aviso al tocar «Posponer».
const posponerPor = Duration(minutes: 15);

const accionTomada = 'tomada';
const accionPosponer = 'posponer';

// --------------------------------------------------------------------------
//  Lo que se guarda
// --------------------------------------------------------------------------

/// Un medicamento con los recordatorios activados.
class RecordatorioActivo {
  const RecordatorioActivo({
    required this.itemId,
    required this.patientId,
    required this.medicamento,
    required this.dosis,
    required this.horario,
    required this.primeraToma,
  });

  final String itemId;
  final String patientId;
  final String medicamento;
  final String dosis;
  final HorarioDeTomas horario;
  final DateTime primeraToma;

  /// Cuándo toca la toma `n` (de 1 a `totalTomas`).
  DateTime momentoDe(int n) =>
      primeraToma.add(Duration(hours: horario.intervaloHoras * (n - 1)));

  DateTime get ultimaToma => momentoDe(horario.totalTomas);

  bool terminado(DateTime ahora) =>
      ahora.isAfter(ultimaToma.add(Duration(hours: horario.intervaloHoras)));

  /// La próxima toma que todavía no llegó, o `null` si ya no quedan.
  int? proximaToma(DateTime ahora) {
    for (var n = 1; n <= horario.totalTomas; n++) {
      if (momentoDe(n).isAfter(ahora)) return n;
    }
    return null;
  }

  /// La toma que toca marcar ahora: la última cuya hora ya llegó (con una
  /// hora de margen hacia adelante, para quien la toma un poco antes).
  int? tomaQueToca(DateTime ahora) {
    int? ultima;
    for (var n = 1; n <= horario.totalTomas; n++) {
      if (!momentoDe(n).isAfter(ahora.add(const Duration(hours: 1)))) ultima = n;
    }
    return ultima;
  }

  /// «Día 3 de 10».
  int diaDelTratamiento(DateTime ahora) {
    final dia = ahora.difference(primeraToma).inHours ~/ 24 + 1;
    return dia.clamp(1, horario.dias < 1 ? 1 : horario.dias);
  }

  Map<String, dynamic> toJson() => {
        'item': itemId,
        'patient': patientId,
        'medication': medicamento,
        'dose': dosis,
        'schedule': horario.toJson(),
        'first': primeraToma.toUtc().toIso8601String(),
      };

  static RecordatorioActivo? fromJson(Map<String, dynamic> json) {
    final horario = HorarioDeTomas.fromJson(json['schedule']);
    final primera = DateTime.tryParse(json['first'] as String? ?? '');
    final item = json['item'] as String? ?? '';
    if (horario == null || primera == null || item.isEmpty) return null;
    return RecordatorioActivo(
      itemId: item,
      patientId: json['patient'] as String? ?? '',
      medicamento: json['medication'] as String? ?? '',
      dosis: json['dose'] as String? ?? '',
      horario: horario,
      primeraToma: primera.toLocal(),
    );
  }
}

/// Una toma marcada en el teléfono que el backend todavía no recibió.
class TomaPendiente {
  const TomaPendiente({
    required this.itemId,
    required this.numero,
    required this.tomada,
    this.programadaPara,
  });

  final String itemId;
  final int numero;
  final bool tomada;
  final DateTime? programadaPara;

  Map<String, dynamic> toJson() => {
        'item': itemId,
        'n': numero,
        'taken': tomada,
        if (programadaPara != null)
          'at': programadaPara!.toUtc().toIso8601String(),
      };

  static TomaPendiente? fromJson(Map<String, dynamic> json) {
    final item = json['item'] as String? ?? '';
    final n = (json['n'] as num?)?.toInt() ?? 0;
    if (item.isEmpty || n < 1) return null;
    return TomaPendiente(
      itemId: item,
      numero: n,
      tomada: json['taken'] as bool? ?? true,
      programadaPara: DateTime.tryParse(json['at'] as String? ?? '')?.toLocal(),
    );
  }
}

/// Dónde se guardan los recordatorios. Una interfaz para que las pruebas no
/// toquen el Keystore.
abstract class AlmacenRecordatorios {
  Future<String?> leer();
  Future<void> guardar(String datos);
  Future<void> borrar();
}

class AlmacenSeguro implements AlmacenRecordatorios {
  const AlmacenSeguro();

  static const _clave = 'medicamentos.recordatorios.v1';
  static const _storage = FlutterSecureStorage();

  @override
  Future<String?> leer() => _storage.read(key: _clave);

  @override
  Future<void> guardar(String datos) =>
      _storage.write(key: _clave, value: datos);

  @override
  Future<void> borrar() => _storage.delete(key: _clave);
}

class AlmacenEnMemoria implements AlmacenRecordatorios {
  String? datos;

  @override
  Future<String?> leer() async => datos;

  @override
  Future<void> guardar(String datos) async => this.datos = datos;

  @override
  Future<void> borrar() async => datos = null;
}

// --------------------------------------------------------------------------
//  Los avisos del sistema
// --------------------------------------------------------------------------

/// Programar y cancelar avisos. Interfaz para las pruebas.
abstract class ProgramadorDeAvisos {
  Future<void> programar({
    required int id,
    required DateTime cuando,
    required String titulo,
    required String cuerpo,
    required String payload,
  });

  Future<void> cancelar(int id);
}

/// El de verdad, con `flutter_local_notifications`.
class ProgramadorLocal implements ProgramadorDeAvisos {
  ProgramadorLocal({this.alResponder});

  /// Qué hacer al tocar un aviso con la app viva. Lo fija `Recordatorios`.
  final void Function(NotificationResponse respuesta)? alResponder;

  static const AndroidNotificationChannel canal = AndroidNotificationChannel(
    'medicamentos',
    'Medicamentos',
    description: 'Avisos para tomar los medicamentos de tu receta.',
    importance: Importance.high,
  );

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  Future<void>? _listo;

  Future<void> iniciar() => _listo ??= _iniciar();

  Future<void> _iniciar() async {
    tzdata.initializeTimeZones();
    await _plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
      onDidReceiveNotificationResponse: alResponder,
      onDidReceiveBackgroundNotificationResponse: alResponderEnSegundoPlano,
    );
    await _plugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(canal);
  }

  /// Si la app se abrió tocando un aviso de medicamento, su respuesta.
  Future<NotificationResponse?> respuestaDeArranque() async {
    await iniciar();
    final detalles = await _plugin.getNotificationAppLaunchDetails();
    return detalles?.didNotificationLaunchApp ?? false
        ? detalles!.notificationResponse
        : null;
  }

  /// Android 13+: el permiso para mostrar notificaciones.
  Future<bool> pedirPermiso() async {
    await iniciar();
    final android = _plugin.resolvePlatformSpecificImplementation<
        AndroidFlutterLocalNotificationsPlugin>();
    return await android?.requestNotificationsPermission() ?? true;
  }

  @override
  Future<void> programar({
    required int id,
    required DateTime cuando,
    required String titulo,
    required String cuerpo,
    required String payload,
  }) async {
    await iniciar();
    await _plugin.zonedSchedule(
      id: id,
      // Un instante absoluto: la zona sólo cambia cómo se escribe.
      scheduledDate: tz.TZDateTime.from(cuando, tz.UTC),
      title: titulo,
      body: cuerpo,
      payload: payload,
      // Inexacto: no pide el permiso de alarmas exactas, y unos minutos de
      // diferencia no cambian una toma.
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      notificationDetails: NotificationDetails(
        android: AndroidNotificationDetails(
          canal.id,
          canal.name,
          channelDescription: canal.description,
          importance: Importance.high,
          priority: Priority.high,
          category: AndroidNotificationCategory.reminder,
          actions: const [
            AndroidNotificationAction(accionTomada, 'Tomada',
                cancelNotification: true),
            AndroidNotificationAction(accionPosponer, 'Posponer 15 min',
                cancelNotification: true),
          ],
        ),
      ),
    );
  }

  @override
  Future<void> cancelar(int id) async {
    await iniciar();
    await _plugin.cancel(id: id);
  }
}

/// Un botón del aviso tocado con la app cerrada. Corre en otro isolate, sin
/// sesión: la toma se anota en el almacén y se manda al abrir la app; el
/// «Posponer» programa el aviso nuevo desde acá.
@pragma('vm:entry-point')
Future<void> alResponderEnSegundoPlano(NotificationResponse respuesta) async {
  DartPluginRegistrant.ensureInitialized();
  final recordatorios = Recordatorios(programador: ProgramadorLocal());
  await recordatorios.responder(respuesta.payload, respuesta.actionId);
}

// --------------------------------------------------------------------------
//  Recordatorios
// --------------------------------------------------------------------------

/// Lo que la sesión necesita: cancelar todo al salir.
abstract class AvisosLocales {
  Future<void> cancelarTodo();
}

class Recordatorios extends ChangeNotifier implements AvisosLocales {
  Recordatorios({
    AlmacenRecordatorios? almacen,
    ProgramadorDeAvisos? programador,
    DateTime Function()? reloj,
  })  : _almacen = almacen ?? const AlmacenSeguro(),
        _reloj = reloj ?? DateTime.now {
    _programador = programador ??
        ProgramadorLocal(alResponder: (r) => unawaited(responder(r.payload, r.actionId)));
  }

  static final Recordatorios instance = Recordatorios();

  final AlmacenRecordatorios _almacen;
  late final ProgramadorDeAvisos _programador;
  final DateTime Function() _reloj;

  final Map<String, RecordatorioActivo> _activos = {};
  final List<TomaPendiente> _pendientes = [];
  Future<void>? _cargando;

  /// Tocar el cuerpo del aviso: lo fija la app, que tiene el router.
  void Function()? alTocarAviso;

  /// Tocar un aviso que no es de medicamento (el push de una ficha o del
  /// chat). El plugin de avisos locales es uno solo y el último `initialize`
  /// define a quién llama: si los recordatorios se inician después que el
  /// push, los toques llegan acá y hay que devolvérselos. Lo fija la app.
  /// Sin esto, tocar «Tu médico te respondió» no abría el chat (20/11/26).
  void Function(String? payload)? alTocarOtroAviso;

  /// Con qué cliente mandar las tomas en cuanto se marcan. Lo fija la app;
  /// `null` si no hay sesión, y quedan pendientes.
  ApiClient? Function()? clienteParaEnviar;

  Map<String, RecordatorioActivo> get activos => Map.unmodifiable(_activos);
  List<TomaPendiente> get pendientes => List.unmodifiable(_pendientes);

  static bool esDeMedicamento(String? payload) =>
      payload != null && payload.startsWith('med|');

  /// El id del aviso de la toma `n`. Estable entre arranques: no usa
  /// `hashCode`, que Dart no garantiza.
  static int idDeAviso(String itemId, int n, {bool pospuesto = false}) {
    var h = 0x811c9dc5;
    for (final c in itemId.codeUnits) {
      h = ((h ^ c) * 0x01000193) & 0xffffffff;
    }
    return (h % 1000000) * 1000 + (pospuesto ? 500 : 0) + n;
  }

  /// Prepara el plugin, lee lo guardado y atiende el aviso con el que se
  /// abrió la app, si lo hubo. Se puede llamar varias veces.
  Future<void> iniciar() async {
    await cargar();
    final programador = _programador;
    if (programador is ProgramadorLocal) {
      try {
        final arranque = await programador.respuestaDeArranque();
        if (arranque != null && esDeMedicamento(arranque.payload)) {
          await responder(arranque.payload, arranque.actionId);
        }
      } catch (error) {
        debugPrint('Recordatorios sin avisos: $error');
      }
    }
  }

  Future<void> cargar() => _cargando ??= _cargar();

  Future<void> _cargar() async {
    try {
      final crudo = await _almacen.leer();
      if (crudo == null || crudo.isEmpty) return;
      final datos = jsonDecode(crudo) as Map<String, dynamic>;
      for (final r in (datos['active'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(RecordatorioActivo.fromJson)
          .whereType<RecordatorioActivo>()) {
        _activos[r.itemId] = r;
      }
      _pendientes.addAll((datos['pending'] as List? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(TomaPendiente.fromJson)
          .whereType<TomaPendiente>());
    } catch (error) {
      debugPrint('No se leyeron los recordatorios: $error');
    }
  }

  Future<void> _guardar() async {
    try {
      await _almacen.guardar(jsonEncode({
        'active': [for (final r in _activos.values) r.toJson()],
        'pending': [for (final p in _pendientes) p.toJson()],
      }));
    } catch (error) {
      debugPrint('No se guardaron los recordatorios: $error');
    }
    notifyListeners();
  }

  String _titulo(RecordatorioActivo r) => 'Hora de tu ${r.medicamento}';
  String _cuerpo(RecordatorioActivo r, int n) =>
      '${r.dosis.isEmpty ? 'Toma ${r.medicamento}' : r.dosis}'
      ' · toma $n de ${r.horario.totalTomas}';

  /// Activa los avisos de un medicamento desde `primeraToma`. Si ya estaba
  /// activo, se reprograma con la hora nueva.
  Future<void> activar(RecordatorioActivo recordatorio) async {
    await cargar();
    final anterior = _activos[recordatorio.itemId];
    if (anterior != null) await _cancelarAvisos(anterior);
    _activos[recordatorio.itemId] = recordatorio;
    final ahora = _reloj();
    for (var n = 1; n <= recordatorio.horario.totalTomas; n++) {
      final cuando = recordatorio.momentoDe(n);
      if (!cuando.isAfter(ahora)) continue;
      await _programarSeguro(
        id: idDeAviso(recordatorio.itemId, n),
        cuando: cuando,
        titulo: _titulo(recordatorio),
        cuerpo: _cuerpo(recordatorio, n),
        payload: 'med|${recordatorio.itemId}|$n',
      );
    }
    await _guardar();
  }

  Future<void> desactivar(String itemId) async {
    await cargar();
    final r = _activos.remove(itemId);
    if (r != null) await _cancelarAvisos(r);
    await _guardar();
  }

  Future<void> _cancelarAvisos(RecordatorioActivo r) async {
    for (var n = 1; n <= r.horario.totalTomas; n++) {
      await _cancelarSeguro(idDeAviso(r.itemId, n));
      await _cancelarSeguro(idDeAviso(r.itemId, n, pospuesto: true));
    }
  }

  /// Al cerrar sesión: ni un aviso más, y nada guardado.
  @override
  Future<void> cancelarTodo() async {
    await cargar();
    for (final r in _activos.values.toList()) {
      await _cancelarAvisos(r);
    }
    _activos.clear();
    _pendientes.clear();
    try {
      await _almacen.borrar();
    } catch (error) {
      debugPrint('No se borraron los recordatorios: $error');
    }
    notifyListeners();
  }

  /// Marca una toma y cancela su aviso si todavía no sonó.
  Future<void> marcar(String itemId, int numero, {required bool tomada}) async {
    await cargar();
    if (_pendientes.any((p) => p.itemId == itemId && p.numero == numero)) {
      return;
    }
    final r = _activos[itemId];
    _pendientes.add(TomaPendiente(
      itemId: itemId,
      numero: numero,
      tomada: tomada,
      programadaPara: r?.momentoDe(numero),
    ));
    await _cancelarSeguro(idDeAviso(itemId, numero));
    await _cancelarSeguro(idDeAviso(itemId, numero, pospuesto: true));
    await _guardar();
    final api = clienteParaEnviar?.call();
    if (api != null) await sincronizar(api);
  }

  /// «Posponer 15 min»: el mismo aviso, un rato más tarde.
  Future<void> posponer(String itemId, int numero) async {
    await cargar();
    final r = _activos[itemId];
    if (r == null) return;
    await _programarSeguro(
      id: idDeAviso(itemId, numero, pospuesto: true),
      cuando: _reloj().add(posponerPor),
      titulo: _titulo(r),
      cuerpo: _cuerpo(r, numero),
      payload: 'med|$itemId|$numero',
    );
  }

  /// Manda al backend las tomas pendientes. Devuelve cuántas quedaron sin
  /// mandar (sin conexión, por ejemplo); se reintentan la próxima vez.
  Future<int> sincronizar(ApiClient api) async {
    await cargar();
    final enviadas = <TomaPendiente>[];
    for (final p in List<TomaPendiente>.of(_pendientes)) {
      try {
        await marcarToma(api,
            itemId: p.itemId,
            numero: p.numero,
            tomada: p.tomada,
            programadaPara: p.programadaPara);
        enviadas.add(p);
      } catch (error) {
        debugPrint('Toma sin enviar: $error');
      }
    }
    if (enviadas.isNotEmpty) {
      _pendientes.removeWhere(enviadas.contains);
      await _guardar();
    }
    return _pendientes.length;
  }

  /// Lo que pasa al tocar un aviso de medicamento o uno de sus botones.
  Future<void> responder(String? payload, String? accion) async {
    if (!esDeMedicamento(payload)) {
      alTocarOtroAviso?.call(payload);
      return;
    }
    final partes = payload!.split('|');
    if (partes.length != 3) return;
    final itemId = partes[1];
    final numero = int.tryParse(partes[2]) ?? 0;
    if (itemId.isEmpty || numero < 1) return;
    switch (accion) {
      case accionTomada:
        await marcar(itemId, numero, tomada: true);
      case accionPosponer:
        await posponer(itemId, numero);
      default:
        alTocarAviso?.call();
    }
  }

  Future<void> _programarSeguro({
    required int id,
    required DateTime cuando,
    required String titulo,
    required String cuerpo,
    required String payload,
  }) async {
    try {
      await _programador.programar(
          id: id, cuando: cuando, titulo: titulo, cuerpo: cuerpo, payload: payload);
    } catch (error) {
      debugPrint('No se programó el aviso $id: $error');
    }
  }

  Future<void> _cancelarSeguro(int id) async {
    try {
      await _programador.cancelar(id);
    } catch (error) {
      debugPrint('No se canceló el aviso $id: $error');
    }
  }

  /// Pide el permiso de notificaciones (Android 13+). Sin él, los avisos no
  /// aparecen; la app lo dice.
  Future<bool> pedirPermiso() async {
    final programador = _programador;
    if (programador is! ProgramadorLocal) return true;
    try {
      return await programador.pedirPermiso();
    } catch (_) {
      return true;
    }
  }
}
