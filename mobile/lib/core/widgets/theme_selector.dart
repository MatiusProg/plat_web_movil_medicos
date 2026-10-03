/// El selector de tema: el mismo control en el perfil y en el acceso rápido.
///
/// Un `SegmentedButton` porque son tres opciones excluyentes y cortas, y se
/// ven las tres a la vez; un `RadioListTile` por opción ocupaba tres renglones
/// para lo mismo. Usar el mismo widget en los dos lugares evita que el perfil
/// diga "Sistema" y el menú "Automático".
library;

import 'package:flutter/material.dart';

import '../theme/theme_controller.dart';

class ThemeSelector extends StatelessWidget {
  const ThemeSelector({super.key, required this.controller});

  final ThemeController controller;

  @override
  Widget build(BuildContext context) {
    // Escucha al controlador y no depende del `ThemeScope`: así funciona
    // también dentro de una hoja modal, que tiene otro contexto.
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: controller,
      builder: (context, actual, _) => SegmentedButton<ThemeMode>(
        segments: const [
          ButtonSegment(
            value: ThemeMode.system,
            icon: Icon(Icons.brightness_auto_outlined),
            label: Text('Sistema'),
            tooltip: 'Como el sistema',
          ),
          ButtonSegment(
            value: ThemeMode.light,
            icon: Icon(Icons.light_mode_outlined),
            label: Text('Claro'),
          ),
          ButtonSegment(
            value: ThemeMode.dark,
            icon: Icon(Icons.dark_mode_outlined),
            label: Text('Oscuro'),
          ),
        ],
        selected: {actual},
        showSelectedIcon: false,
        onSelectionChanged: (elegido) => controller.set(elegido.first),
      ),
    );
  }
}

/// El ícono que corresponde a la elección actual.
IconData iconoDeTema(ThemeMode mode) => switch (mode) {
  ThemeMode.system => Icons.brightness_auto_outlined,
  ThemeMode.light => Icons.light_mode_outlined,
  ThemeMode.dark => Icons.dark_mode_outlined,
};

/// Abre una hoja chica con el selector. Es el acceso rápido de los menús y de
/// la pantalla de inicio: el cambio se ve al instante detrás de la hoja.
Future<void> mostrarSelectorDeTema(
  BuildContext context,
  ThemeController controller,
) {
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Tema', style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 16),
            ThemeSelector(controller: controller),
          ],
        ),
      ),
    ),
  );
}

/// El renglón de los menús laterales: "Tema: Claro", y al tocarlo, la hoja.
///
/// No se dibuja si no hay `ThemeScope` arriba (pantallas sueltas en pruebas).
class ThemeDrawerTile extends StatelessWidget {
  const ThemeDrawerTile({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = ThemeScope.maybeOf(context);
    if (controller == null) return const SizedBox.shrink();
    final actual = controller.value;
    return ListTile(
      leading: Icon(iconoDeTema(actual)),
      title: Text(
        'Tema: ${actual == ThemeMode.system ? 'Sistema' : etiquetaDeTema(actual)}',
      ),
      // El cajón queda abierto a propósito: la hoja sale encima y, al
      // cerrarla, se sigue en el menú, que ya muestra el tema nuevo.
      onTap: () => mostrarSelectorDeTema(context, controller),
    );
  }
}
