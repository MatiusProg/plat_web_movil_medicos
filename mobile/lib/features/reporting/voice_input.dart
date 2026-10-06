/// Dictado en el teléfono, para pedir un reporte hablando.
///
/// **El audio no sale del dispositivo por nuestra cuenta.** Quien transcribe es
/// el reconocedor del sistema —el de Google, en la práctica—; esta aplicación
/// no graba, no guarda y no sube ningún audio. Lo único que viaja al backend es
/// el texto.
///
/// Dos cosas que conviene saber:
///
/// 1. **Puede no estar disponible.** Hay teléfonos sin reconocedor instalado, y
///    algunos fabricantes lo recortan. Por eso [disponible] se consulta antes
///    de mostrar el botón: ofrecer un micrófono que no funciona es peor que no
///    ofrecerlo, y el formulario se arma igual a mano.
/// 2. **El permiso lo pide el paquete** la primera vez que se inicializa. Si la
///    persona lo niega, [motivo] lo explica en vez de dejar el botón mudo.
///
/// La interfaz está detrás de [DictadoDeVoz] para que la pantalla no dependa
/// del paquete: las pruebas inyectan el texto ya transcrito y no necesitan
/// micrófono, que en un entorno de pruebas no existe.
library;

import 'package:speech_to_text/speech_to_text.dart';

/// Lo que la pantalla necesita de un dictado, sin saber quién lo hace.
abstract class DictadoDeVoz {
  /// Prepara el reconocedor y dice si se puede dictar en este teléfono.
  Future<bool> preparar();

  /// Por qué no se puede dictar, para mostrárselo a la persona.
  String get motivo;

  bool get escuchando;

  /// Empieza a escuchar. [alCambiar] recibe el texto parcial mientras habla y
  /// [alTerminar] el texto final cuando la frase se cierra.
  Future<void> empezar({
    required void Function(String texto) alCambiar,
    required void Function(String texto) alTerminar,
  });

  Future<void> terminar();

  void soltar();
}

class DictadoDelSistema implements DictadoDeVoz {
  DictadoDelSistema({SpeechToText? motor}) : _motor = motor ?? SpeechToText();

  final SpeechToText _motor;
  bool _listo = false;
  String _motivo = '';

  @override
  String get motivo => _motivo;

  @override
  bool get escuchando => _motor.isListening;

  @override
  Future<bool> preparar() async {
    if (_listo) return true;
    try {
      _listo = await _motor.initialize(
        // Los errores y los cambios de estado llegan acá. No se registran en
        // pantalla: lo que importa es si quedó listo, y eso lo dice el retorno.
        onError: (error) => _motivo = _mensajeDeError(error.errorMsg),
        onStatus: (_) {},
      );
    } catch (_) {
      _listo = false;
    }
    if (!_listo && _motivo.isEmpty) {
      _motivo =
          'Este teléfono no puede dictar. Armá el reporte tocando las '
          'opciones.';
    }
    return _listo;
  }

  @override
  Future<void> empezar({
    required void Function(String texto) alCambiar,
    required void Function(String texto) alTerminar,
  }) async {
    if (!await preparar()) return;
    await _motor.listen(
      // `dictation` mantiene la escucha durante las pausas cortas: una frase
      // como "pacientes… mujeres… de septiembre" se dice con pausas y con el
      // modo por omisión se cortaría en la primera.
      listenOptions: SpeechListenOptions(
        localeId: 'es_BO',
        partialResults: true,
        listenMode: ListenMode.dictation,
      ),
      onResult: (resultado) {
        final texto = resultado.recognizedWords.trim();
        if (resultado.finalResult) {
          if (texto.isNotEmpty) alTerminar(texto);
        } else {
          alCambiar(texto);
        }
      },
    );
  }

  @override
  Future<void> terminar() => _motor.stop();

  @override
  void soltar() {
    // Cancelar y no parar: salir de la pantalla no tiene que entregar un
    // resultado tardío a una pantalla que ya no está.
    _motor.cancel();
  }

  String _mensajeDeError(String codigo) {
    if (codigo.contains('permission') || codigo.contains('denied')) {
      return 'No diste permiso para usar el micrófono.';
    }
    if (codigo.contains('no_match') || codigo.contains('speech_timeout')) {
      return 'No escuché nada. Probá de nuevo.';
    }
    return 'No se pudo usar el micrófono.';
  }
}
