/// El panel de quien administra un centro médico.
///
/// Muestra como tarjetas las secciones que los permisos de la persona
/// habilitan. Es la misma lista que el cajón lateral
/// (`core/widgets/organization_drawer.dart`) y sale del mismo lugar: acá se
/// dibuja para que sea **descubrible** —en un teléfono nadie encuentra un
/// cajón que no sabe que existe— y allá para saltar entre secciones sin
/// volver.
///
/// **Por qué existía un agujero acá.** Hasta ahora el móvil sólo tenía dos
/// caras, la del paciente y la del superadministrador de plataforma. Quien
/// administra una organización —el rol que en la web maneja agendas,
/// sucursales, usuarios y bitácora— entraba y leía "Esta sección es para
/// pacientes": 32 permisos y ninguna pantalla donde usarlos.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';

class OrganizationHomeScreen extends StatelessWidget {
  const OrganizationHomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final session = SessionScope.of(context);
    final user = session.user;

    final visibles = seccionesDeOrganizacion
        .where((s) => user?.can(s.permiso) ?? false)
        .toList();

    return Scaffold(
      appBar: AppBar(title: const Text('Centro médico')),
      drawer: const OrganizationDrawer(),
      body: visibles.isEmpty
          ? const _SinSecciones()
          : ListView.separated(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 32),
              itemCount: visibles.length,
              separatorBuilder: (_, _) => const SizedBox(height: 12),
              itemBuilder: (context, i) {
                final seccion = visibles[i];
                return Card(
                  margin: EdgeInsets.zero,
                  child: ListTile(
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    leading: CircleAvatar(
                      backgroundColor: theme.colorScheme.secondaryContainer,
                      child: Icon(
                        seccion.icono,
                        color: theme.colorScheme.onSecondaryContainer,
                      ),
                    ),
                    title: Text(
                      seccion.etiqueta,
                      style: theme.textTheme.titleMedium,
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    // `push` y no `go`: desde el panel se entra y se vuelve,
                    // así el botón atrás del teléfono trae de vuelta acá. El
                    // `go` queda para el cajón, que es navegación lateral.
                    onTap: () => context.push(seccion.ruta),
                  ),
                );
              },
            ),
    );
  }
}

/// Hay sesión de alguien de la organización, pero sin ningún permiso de los
/// que abren una sección.
///
/// Pasa con un rol recortado, o mientras el perfil todavía no se pudo cargar.
class _SinSecciones extends StatelessWidget {
  const _SinSecciones();

  @override
  Widget build(BuildContext context) => const Center(
        child: Padding(
          padding: EdgeInsets.all(24),
          child: Text(
            'Tu cuenta todavía no tiene permisos de administración. '
            'Pedile al administrador de tu centro médico que te asigne un rol.',
            textAlign: TextAlign.center,
          ),
        ),
      );
}
