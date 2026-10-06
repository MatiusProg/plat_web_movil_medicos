/// Guardar en el teléfono lo que se baja de la plataforma, y abrirlo.
///
/// Lo usan las copias de seguridad y los reportes. Las dos cosas pasan por
/// contratos ([GuardadoDeArchivos] y [AbridorDeArchivos]) para que las
/// pruebas no toquen el disco ni lancen otra aplicación.
library;

import 'dart:io';

import 'package:open_filex/open_filex.dart';

/// Dónde termina un archivo bajado. Se inyecta para probar sin disco.
abstract class GuardadoDeArchivos {
  /// Guarda y devuelve la ruta donde quedó.
  Future<String> guardar(String nombre, List<int> bytes);
}

/// La carpeta pública de Descargas, donde la persona lo encuentra con el
/// administrador de archivos y lo puede mandar a donde quiera.
///
/// Sin permisos: desde Android 11 una aplicación puede crear sus propios
/// archivos en `Download/` sin pedir nada. Si el nombre ya existe se agrega un
/// número en vez de pisar el anterior: `pacientes (2).xlsx`.
class GuardadoEnDescargas implements GuardadoDeArchivos {
  const GuardadoEnDescargas({this.carpeta = '/storage/emulated/0/Download'});

  final String carpeta;

  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    final punto = nombre.lastIndexOf('.');
    final base = punto > 0 ? nombre.substring(0, punto) : nombre;
    final extension = punto > 0 ? nombre.substring(punto) : '';

    var archivo = File('$carpeta/$base$extension');
    for (var n = 2; await archivo.exists(); n++) {
      archivo = File('$carpeta/$base ($n)$extension');
    }
    try {
      await archivo.writeAsBytes(bytes, flush: true);
    } on FileSystemException {
      throw const FileSystemException(
        'El teléfono no dejó guardar el archivo en Descargas. Bajalo desde la '
        'plataforma web.',
      );
    }
    return archivo.path;
  }
}

/// Abre un archivo guardado con la aplicación que corresponda.
abstract class AbridorDeArchivos {
  /// `null` si se abrió; si no, el motivo para mostrarle a la persona.
  Future<String?> abrir(String ruta);
}

/// Le pide a Android que lo abra: Excel o Sheets para un `.xlsx`, el visor de
/// PDF para un `.pdf`, el navegador para un `.html`.
///
/// `open_filex` y no `url_launcher`: desde Android 7 una aplicación no puede
/// pasarle a otra la ruta de un archivo (`file://`), tiene que compartirlo
/// por un `FileProvider` con permiso de lectura, y eso es lo que resuelve.
class AbridorDelSistema implements AbridorDeArchivos {
  const AbridorDelSistema();

  @override
  Future<String?> abrir(String ruta) async {
    final resultado = await OpenFilex.open(ruta);
    switch (resultado.type) {
      case ResultType.done:
        return null;
      case ResultType.noAppToOpen:
        return 'No hay ninguna aplicación instalada que abra este tipo de '
            'archivo. Está en Descargas.';
      case ResultType.fileNotFound:
        return 'El archivo ya no está en Descargas: puede que lo hayan movido '
            'o borrado.';
      case ResultType.permissionDenied:
        return 'El teléfono no dejó abrir el archivo. Está en Descargas.';
      case ResultType.error:
        return 'No se pudo abrir el archivo: ${resultado.message}';
    }
  }
}
