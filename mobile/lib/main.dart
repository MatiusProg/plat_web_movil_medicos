/// Punto de entrada de la aplicación móvil del Centro Médico.
///
/// Para correrla hay que decirle dónde está la API:
///
///     flutter run --dart-define=API_BASE_URL=http://192.168.0.15:8000/api
///
/// Esa IP es la de la máquina que corre Django, en la red local. El equipo
/// trabaja con el celular por USB y sin emulador, y para el teléfono
/// `localhost` es el propio teléfono. El porqué está en `lib/core/config.dart`
/// y en `docs/entorno/setup-movil.md`.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import 'app.dart';
import 'core/session/session.dart';

Future<void> main() async {
  // Hace falta antes de tocar el almacenamiento seguro: `restore()` usa un
  // canal de plataforma, y sin los bindings inicializados eso falla.
  WidgetsFlutterBinding.ensureInitialized();

  final session = Session();

  // Arranca sin esperar a que termine de leerse la sesión: mientras tanto el
  // router muestra la pantalla de carga, y en cuanto `restore()` avisa, la
  // redirección lleva a donde corresponda. Esperar acá deja la pantalla en
  // negro todo lo que tarde el Keystore del teléfono.
  unawaited(session.restore());

  runApp(CentroMedicoApp(session: session));
}
