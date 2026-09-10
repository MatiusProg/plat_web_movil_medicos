/// Lo que comparten las tres pantallas del catálogo del centro médico.
///
/// Sucursales, Especialidades y Profesionales tienen la misma forma —listar,
/// dar de alta, editar, dar de baja— y sólo cambian los campos. Es el
/// equivalente móvil de `frontend/src/paginas/catalogo_comun.tsx`.
///
/// Sin esto, el estado de carga, el de error con reintento y el vacío
/// quedarían escritos tres veces, y en la práctica eso significa que uno de
/// los tres se olvida: es exactamente lo que la auditoría encontró en las
/// pantallas de plataforma, donde un corte de red de dos segundos dejaba la
/// pantalla inservible porque no había forma de reintentar.
library;

import 'package:flutter/material.dart';

/// El cuerpo de una pantalla de catálogo, con sus cuatro estados resueltos.
class CuerpoDeCatalogo<T> extends StatelessWidget {
  const CuerpoDeCatalogo({
    super.key,
    required this.items,
    required this.error,
    required this.onReintentar,
    required this.vacio,
    required this.itemBuilder,
    this.encabezado,
  });

  /// `null` = todavía cargando.
  final List<T>? items;

  final String? error;
  final Future<void> Function() onReintentar;

  /// Qué decir cuando no hay nada. Que explique, no un "sin datos" pelado.
  final String vacio;

  final Widget Function(BuildContext, T) itemBuilder;
  final Widget? encabezado;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return RefreshIndicator(
      onRefresh: onReintentar,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 96),
        children: [
          if (encabezado != null) ...[encabezado!, const SizedBox(height: 16)],

          if (error != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 24),
              child: Column(
                children: [
                  Text(
                    error!,
                    textAlign: TextAlign.center,
                    style: TextStyle(color: theme.colorScheme.error),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.tonalIcon(
                    onPressed: onReintentar,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reintentar'),
                  ),
                ],
              ),
            )
          else if (items == null)
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 48),
              child: Center(child: CircularProgressIndicator()),
            )
          else if (items!.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 32),
              child: Text(vacio, textAlign: TextAlign.center),
            )
          else
            for (final item in items!) itemBuilder(context, item),
        ],
      ),
    );
  }
}

/// La tarjeta de una fila del catálogo, con su estado y sus dos acciones.
class TarjetaDeCatalogo extends StatelessWidget {
  const TarjetaDeCatalogo({
    super.key,
    required this.titulo,
    required this.activo,
    required this.onEditar,
    required this.onDarDeBaja,
    this.subtitulo,
    this.detalle,
  });

  final String titulo;
  final String? subtitulo;

  /// Una línea más chica: sedes, especialidades, lo que distinga a la fila.
  final Widget? detalle;

  final bool activo;
  final VoidCallback onEditar;
  final VoidCallback onDarDeBaja;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 8, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(titulo, style: theme.textTheme.titleMedium),
                ),
                if (!activo)
                  Chip(
                    label: const Text('Inactiva'),
                    visualDensity: VisualDensity.compact,
                    backgroundColor: theme.colorScheme.surfaceContainerHighest,
                  ),
              ],
            ),
            if (subtitulo != null && subtitulo!.isNotEmpty) ...[
              const SizedBox(height: 4),
              Text(subtitulo!, style: theme.textTheme.bodySmall),
            ],
            if (detalle != null) ...[const SizedBox(height: 8), detalle!],
            Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                TextButton(onPressed: onEditar, child: const Text('Editar')),
                if (activo)
                  TextButton(
                    onPressed: onDarDeBaja,
                    child: const Text('Dar de baja'),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

/// Confirmación antes de una baja.
///
/// Las bajas del catálogo son lógicas y reversibles desde la web, pero igual
/// se pregunta: en un teléfono el dedo roza botones que no quería tocar.
Future<bool> confirmarBaja(BuildContext context, String queCosa) async {
  final respuesta = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: const Text('¿Dar de baja?'),
      content: Text(
        '$queCosa va a dejar de estar disponible para nuevas asignaciones. '
        'Lo que ya existe no se borra.',
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: const Text('Dar de baja'),
        ),
      ],
    ),
  );
  return respuesta ?? false;
}
