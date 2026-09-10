/// El menú lateral del superadministrador de plataforma.
///
/// Es el equivalente móvil de `frontend/src/componentes/BarraPlataforma.tsx`
/// para las cuatro secciones que sólo ve el superadmin (`requiere:
/// 'plataforma'` en ese archivo): Panel, Organizaciones, Planes,
/// Suscripciones. Con `drawer:` puesto en el `Scaffold`, el `AppBar` agrega
/// solo el ícono de hamburguesa que lo abre -no hace falta dibujarlo a mano-.
///
/// Cada pantalla de estas cuatro secciones agrega `drawer: const
/// PlatformDrawer()` a su propio `Scaffold`.
///
/// **Por qué el menú termina en Inicio y Cerrar sesión.** Entre secciones se
/// navega con `go`, que reemplaza la pila en vez de apilarla: es lo correcto
/// para navegación lateral -no tiene sentido acumular Panel sobre Planes
/// sobre Panel-, pero deja al superadministrador sin historial al que
/// volver, y el botón atrás del teléfono se queda sin destino. Como el
/// cierre de sesión vive en la pantalla de inicio y ninguna de estas cuatro
/// lo tiene, sin estas dos salidas la única forma de salir del panel era
/// matar la aplicación.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../session/session_scope.dart';
import '../theme/theme.dart';

class PlatformDrawer extends StatelessWidget {
  const PlatformDrawer({super.key});

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);

    Widget item(IconData icono, String texto, String ruta) => ListTile(
          leading: Icon(icono),
          title: Text(texto),
          onTap: () {
            Navigator.of(context).pop(); // cierra el drawer
            context.go(ruta); // reemplaza, no apila: es navegación lateral
          },
        );

    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 48, 20, 20),
            decoration: const BoxDecoration(
              gradient: RadialGradient(colors: Marca.gradient, radius: 1.4),
            ),
            child: const Align(
              alignment: Alignment.bottomLeft,
              child: Text(
                'Plataforma',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          item(Icons.dashboard_outlined, 'Panel', '/platform/dashboard'),
          item(
            Icons.apartment_outlined,
            'Organizaciones',
            '/platform/organizations',
          ),
          item(
            Icons.workspace_premium_outlined,
            'Planes',
            '/platform/plans',
          ),
          item(
            Icons.receipt_long_outlined,
            'Suscripciones',
            '/platform/subscriptions',
          ),
          const Divider(),
          item(Icons.home_outlined, 'Inicio', '/home'),
          ListTile(
            leading: const Icon(Icons.logout),
            title: const Text('Cerrar sesión'),
            onTap: () {
              Navigator.of(context).pop(); // cierra el drawer
              session.signOut();
            },
          ),
        ],
      ),
    );
  }
}
