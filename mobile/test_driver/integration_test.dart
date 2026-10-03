/// Lado de la PC de `flutter drive`: guarda las capturas del recorrido.
library;

import 'dart:io';

import 'package:integration_test/integration_test_driver_extended.dart';

Future<void> main() => integrationDriver(
      onScreenshot: (nombre, bytes, [args]) async {
        final archivo = File('build/capturas/$nombre.png');
        await archivo.create(recursive: true);
        await archivo.writeAsBytes(bytes);
        return true;
      },
    );
