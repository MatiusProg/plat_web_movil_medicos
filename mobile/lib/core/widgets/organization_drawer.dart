/// El menú lateral de quien administra un centro médico.
///
/// Es el equivalente móvil de las entradas de
/// `frontend/src/componentes/BarraPlataforma.tsx` que llevan un `requiere:`
/// con un código de permiso —todas menos las cuatro de plataforma, que tienen
/// su propio menú en `platform_drawer.dart`—.
///
/// **Cada entrada se dibuja sólo si el permiso está.** No hay una lista por
/// rol: los roles los arma cada organización (US-04), así que un
/// recepcionista con permiso de agendas pero no de bitácora ve exactamente
/// eso, sin que la aplicación sepa que existe el rol "recepcionista".
///
/// Termina en Inicio y Cerrar sesión por lo mismo que el de plataforma: entre
/// secciones se navega con `go`, que reemplaza la pila, y sin esas dos
/// salidas quien entra se queda sin botón atrás y sin forma de salir.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../session/session_scope.dart';
import '../theme/theme.dart';

/// Una sección del menú: qué permiso la habilita y a dónde lleva.
///
/// La lista vive acá y no repartida por las pantallas para que el orden y los
/// permisos se lean de un vistazo, igual que el array `items` de la web.
class SeccionDeOrganizacion {
  const SeccionDeOrganizacion({
    required this.icono,
    required this.etiqueta,
    required this.ruta,
    required this.permiso,
  });

  final IconData icono;
  final String etiqueta;
  final String ruta;
  final String permiso;
}

/// Las nueve secciones, en el mismo orden que la barra lateral de la web.
const seccionesDeOrganizacion = <SeccionDeOrganizacion>[
  // US-13 y US-14 — agendas y disponibilidad.
  SeccionDeOrganizacion(
    icono: Icons.event_note_outlined,
    etiqueta: 'Agendas',
    ruta: '/org/agendas',
    permiso: 'scheduling.schedule.read',
  ),
  SeccionDeOrganizacion(
    icono: Icons.schedule_outlined,
    etiqueta: 'Disponibilidad',
    ruta: '/org/disponibilidad',
    permiso: 'scheduling.slot.read',
  ),

  // US-11 y US-12 — catálogo del centro médico.
  SeccionDeOrganizacion(
    icono: Icons.apartment_outlined,
    etiqueta: 'Sucursales',
    ruta: '/org/sucursales',
    permiso: 'catalog.branch.read',
  ),
  SeccionDeOrganizacion(
    icono: Icons.local_hospital_outlined,
    etiqueta: 'Especialidades',
    ruta: '/org/especialidades',
    permiso: 'catalog.specialty.read',
  ),
  SeccionDeOrganizacion(
    icono: Icons.badge_outlined,
    etiqueta: 'Profesionales',
    ruta: '/org/profesionales',
    permiso: 'catalog.professional.read',
  ),

  // US-16 — la búsqueda que ya existe para el paciente, reutilizada tal cual.
  SeccionDeOrganizacion(
    icono: Icons.search,
    etiqueta: 'Buscar profesionales',
    ruta: '/specialties',
    permiso: 'catalog.professional.read',
  ),

  // US-06 — bitácora de auditoría.
  SeccionDeOrganizacion(
    icono: Icons.receipt_long_outlined,
    etiqueta: 'Bitácora',
    ruta: '/org/bitacora',
    permiso: 'audit.log.read',
  ),

  // US-04 — usuarios, roles y permisos.
  SeccionDeOrganizacion(
    icono: Icons.people_outline,
    etiqueta: 'Usuarios',
    ruta: '/org/usuarios',
    permiso: 'users.user.read',
  ),
  SeccionDeOrganizacion(
    icono: Icons.shield_outlined,
    etiqueta: 'Roles y permisos',
    ruta: '/org/roles',
    permiso: 'users.role.read',
  ),
];

class OrganizationDrawer extends StatelessWidget {
  const OrganizationDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final user = session.user;

    final visibles = seccionesDeOrganizacion
        .where((s) => user?.can(s.permiso) ?? false)
        .toList();

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 48, 20, 20),
            decoration: const BoxDecoration(
              gradient: RadialGradient(colors: Marca.gradient, radius: 1.4),
            ),
            child: Align(
              alignment: Alignment.bottomLeft,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text(
                    'Centro médico',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 20,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    session.organizationSlug ?? '',
                    style: const TextStyle(color: Colors.white70, fontSize: 13),
                  ),
                ],
              ),
            ),
          ),
          for (final seccion in visibles)
            ListTile(
              leading: Icon(seccion.icono),
              title: Text(seccion.etiqueta),
              onTap: () {
                Navigator.of(context).pop(); // cierra el cajón
                context.go(seccion.ruta); // navegación lateral: reemplaza
              },
            ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.home_outlined),
            title: const Text('Inicio'),
            onTap: () {
              Navigator.of(context).pop();
              context.go('/home');
            },
          ),
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Cerrar sesión'),
            onTap: () {
              Navigator.of(context).pop();
              session.signOut();
            },
          ),
        ],
      ),
    );
  }
}
