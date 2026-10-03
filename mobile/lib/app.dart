/// La aplicación.
///
/// Arma el router una sola vez y lo cuelga de la sesión. Reconstruir el
/// `GoRouter` en cada `build` reinicia la pila de navegación, y el síntoma es
/// que la aplicación vuelve sola a la pantalla inicial cada vez que algo
/// notifica — por ejemplo, cada renovación de token.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'core/router/app_router.dart';
import 'core/session/session.dart';
import 'core/session/session_scope.dart';
import 'core/theme/theme.dart';
import 'core/theme/theme_controller.dart';

class CentroMedicoApp extends StatefulWidget {
  const CentroMedicoApp({super.key, required this.session, required this.tema});

  final Session session;

  /// La elección de claro, oscuro o "como el sistema" (ver
  /// `core/theme/theme_controller.dart`).
  final ThemeController tema;

  @override
  State<CentroMedicoApp> createState() => _CentroMedicoAppState();
}

class _CentroMedicoAppState extends State<CentroMedicoApp> {
  late final GoRouter _router = buildRouter(widget.session);

  @override
  Widget build(BuildContext context) {
    return SessionScope(
      session: widget.session,
      child: ThemeScope(
        controller: widget.tema,
        // Sólo `MaterialApp` se reconstruye al cambiar el tema; el router es
        // el mismo objeto, así que la pila de navegación no se pierde.
        child: ValueListenableBuilder<ThemeMode>(
          valueListenable: widget.tema,
          builder: (context, modo, _) => MaterialApp.router(
            title: 'Centro médico',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light,
            darkTheme: AppTheme.dark,
            // Por omisión sigue el ajuste del teléfono, igual que el frontend
            // web con `prefers-color-scheme`; la persona puede fijarlo en su
            // perfil o desde el menú.
            themeMode: modo,
            routerConfig: _router,
          ),
        ),
      ),
    );
  }
}
