/// Protege las pantallas de auto-servicio del paciente en el router.
///
/// Es el equivalente de `if (!usuario.is_platform_admin) return <mensaje/>`
/// en `Organizaciones.tsx` del frontend web: cosmético, no seguridad -la
/// puerta real la sigue poniendo el backend con sus permisos-. Va en el
/// `builder` de la ruta, no adentro de la pantalla: así, si no corresponde,
/// la pantalla ni se monta y no llega a pedir nada -evita a la vez el 403
/// que le daría a un `org_admin` y la lista vacía y engañosa que hoy
/// devuelve `practitioner` en `/patients/history/` sin `?patient=`.
library;

import 'package:flutter/material.dart';

import 'session_scope.dart';

class SoloPacientes extends StatelessWidget {
  const SoloPacientes({super.key, required this.titulo, required this.child});

  final String titulo;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    final user = SessionScope.of(context).user;

    // Sin datos del usuario todavía -sesión reabierta sin red, por
    // ejemplo-, se deja pasar: la pantalla que sigue va a fallar sola con su
    // propio error si de verdad no correspondía, y no hay que arriesgarse a
    // bloquear a un paciente real por no haber podido confirmar el rol.
    if (user != null && !user.isPatient) {
      return Scaffold(
        appBar: AppBar(title: Text(titulo)),
        body: const Padding(
          padding: EdgeInsets.all(24),
          child: Text('Esta sección es para pacientes.'),
        ),
      );
    }

    return child;
  }
}
