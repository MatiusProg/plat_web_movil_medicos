/// El tema de la aplicación.
///
/// Los colores son **los mismos** que los del frontend web
/// (`frontend/src/index.css`): `marca` para lo de la aplicación y `tinta` para
/// los grises. No se eligieron acá de nuevo — el paciente que entra por la web
/// y por el teléfono tiene que ver el mismo producto, y dos paletas parecidas
/// pero distintas es peor que una sola.
///
/// La marca por organización todavía no se aplica. `Organization` ya guarda
/// `primary_color` y `secondary_color` (US-43), así que cuando haga falta se
/// construye el `ColorScheme` con esos valores en vez de con la constante; el
/// lugar donde tocarlo es [Marca.primary] y nada más.
library;

import 'package:flutter/material.dart';

/// La paleta compartida con el frontend web.
class Marca {
  const Marca._();

  static const Color primary = Color(0xFF0D8F88); // marca-600
  static const Color primaryDark = Color(0xFF10726E); // marca-700
  static const Color primaryLight = Color(0xFF38CEC0); // marca-400
  static const Color surfaceTint = Color(0xFFEEFDFA); // marca-50

  static const Color ink900 = Color(0xFF0F172A); // tinta-900
  static const Color ink800 = Color(0xFF1E293B);
  static const Color ink500 = Color(0xFF64748B);
  static const Color ink300 = Color(0xFFCBD5E1);
  static const Color ink100 = Color(0xFFF1F5F9);
  static const Color ink50 = Color(0xFFF8FAFC);
  static const Color ink950 = Color(0xFF020617);

  /// Rojo de error. En el web es `alerta`.
  static const Color danger = Color(0xFFDC2626);

  /// Ámbar de espera: el bloqueo temporal del RNF-07 no es un error, es una
  /// espera, y se pinta distinto a propósito.
  static const Color waiting = Color(0xFFD97706);
}

class AppTheme {
  const AppTheme._();

  static ThemeData get light => _build(Brightness.light);
  static ThemeData get dark => _build(Brightness.dark);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;

    final scheme = ColorScheme.fromSeed(
      seedColor: Marca.primary,
      brightness: brightness,
      primary: Marca.primary,
      error: Marca.danger,
      surface: isDark ? Marca.ink950 : Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: isDark ? Marca.ink950 : Marca.ink50,

      appBarTheme: AppBarTheme(
        backgroundColor: isDark ? Marca.ink950 : Colors.white,
        foregroundColor: isDark ? Marca.ink50 : Marca.ink900,
        elevation: 0,
        scrolledUnderElevation: 1,
        centerTitle: false,
      ),

      // Los mismos radios que el web, que usa `rounded-xl` en todo.
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          textStyle: const TextStyle(
            fontSize: 15,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? Marca.ink900 : Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: isDark ? Marca.ink800 : Marca.ink300),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: isDark ? Marca.ink800 : Marca.ink300),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Marca.primary, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: Marca.danger),
        ),
      ),

      cardTheme: CardThemeData(
        elevation: 0,
        color: isDark ? Marca.ink900 : Colors.white,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: BorderSide(color: isDark ? Marca.ink800 : Marca.ink300),
        ),
      ),

      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
      ),
    );
  }
}
