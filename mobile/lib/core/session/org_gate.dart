/// Protege las pantallas de administración de la organización.
///
/// Es el hermano de [SoloPacientes] (`patient_gate.dart`) para el otro lado
/// de la aplicación, y el equivalente móvil del `requiere:` de
/// `frontend/src/componentes/BarraPlataforma.tsx`: allá cada entrada del menú
/// declara el permiso que la habilita y `puede()` decide si se dibuja.
///
/// **Gatea por permiso y no por rol.** Los roles de una organización los
/// arma su propio administrador (US-04): puede haber un "Recepcionista" que
/// vea agendas pero no la bitácora, o un rol nuevo que nadie previó. Mirar el
/// permiso hace que eso funcione solo; mirar el rol obligaría a tocar la
/// aplicación cada vez que alguien inventa uno.
///
/// Como el resto de estas guardas, es cosmético: la puerta real la pone el
/// backend en cada endpoint. Acá sólo se evita ofrecer lo que va a dar 403.
library;

import 'package:flutter/material.dart';

import 'session_scope.dart';

class ConPermiso extends StatelessWidget {
  const ConPermiso({
    super.key,
    required this.permiso,
    required this.titulo,
    required this.child,
  });

  /// El código, tal como lo manda el backend: `scheduling.schedule.read`, …
  final String permiso;

  /// Para la barra de título cuando no se puede entrar: sin esto la pantalla
  /// de "no tenés permiso" saldría sin encabezado y sin forma de volver.
  final String titulo;

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final user = SessionScope.of(context).user;

    // Con el perfil todavía sin cargar no se bloquea: la pantalla de inicio ya
    // avisa que no se pudo confirmar quién es, y frenar acá además dejaría a
    // alguien con permiso afuera por un problema de red. Si de verdad no
    // correspondía, el backend contesta 403 y la pantalla lo muestra.
    if (user != null && !user.can(permiso)) {
      return Scaffold(
        appBar: AppBar(title: Text(titulo)),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Text(
              'Tu cuenta no tiene permiso para ver esta sección. '
              'Pedile al administrador de tu centro médico que te lo asigne.',
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    return child;
  }
}
