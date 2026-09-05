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

class CentroMedicoApp extends StatefulWidget {
  const CentroMedicoApp({super.key, required this.session});

  final Session session;

  @override
  State<CentroMedicoApp> createState() => _CentroMedicoAppState();
}

class _CentroMedicoAppState extends State<CentroMedicoApp> {
  late final GoRouter _router = buildRouter(widget.session);

  @override
  Widget build(BuildContext context) {
    return SessionScope(
      session: widget.session,
      child: MaterialApp.router(
        title: 'Centro médico',
        debugShowCheckedModeBanner: false,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        // Sigue el ajuste del teléfono, igual que el frontend web sigue el del
        // sistema con `prefers-color-scheme`.
        themeMode: ThemeMode.system,
        routerConfig: _router,
      ),
    );
  }
}
