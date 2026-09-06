/// Las rutas de la aplicación.
///
/// **La redirección la decide la sesión, no cada pantalla.** Es lo mismo que
/// hace `RutaProtegida` en el frontend web: una pantalla que comprueba por su
/// cuenta si hay sesión es una pantalla que alguien va a olvidarse de proteger.
///
/// Cada historia agrega su ruta en la lista de abajo, en su propio bloque, y no
/// toca las de al lado — la misma regla del archivo compartido que el backend
/// aplica en `accounts/urls.py`.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/sign_in_screen.dart';
import '../../features/availability/availability_screen.dart';
import '../../features/dependents/dependent_form_screen.dart';
import '../../features/dependents/dependents_screen.dart';
import '../../features/search/search_screen.dart';
import '../../features/search/specialties_screen.dart';
import '../session/session.dart';
import '../session/session_scope.dart';

/// Los nombres se usan con `context.goNamed(Routes.signIn)`, para que cambiar
/// una ruta no obligue a buscar la cadena por todo el proyecto.
class Routes {
  const Routes._();

  static const String loading = 'loading';
  static const String signIn = 'sign-in';
  static const String home = 'home';
  static const String specialties = 'specialties';
  static const String search = 'search';
  static const String availability = 'availability';
  static const String dependents = 'dependents';
  static const String dependentForm = 'dependent-form';
}

GoRouter buildRouter(Session session) {
  return GoRouter(
    initialLocation: '/',
    // El router se vuelve a evaluar cada vez que la sesión cambia: al entrar,
    // al cerrar sesión y cuando una renovación falla.
    refreshListenable: session,
    redirect: (context, state) {
      final path = state.matchedLocation;

      // Todavía no se leyó el almacenamiento seguro. Sin este caso, quien
      // tenía sesión ve un parpadeo de la pantalla de ingreso antes de entrar.
      if (session.status == SessionStatus.unknown) {
        return path == '/' ? null : '/';
      }

      final signedIn = session.isSignedIn;
      final goingToSignIn = path == '/sign-in';

      if (!signedIn && !goingToSignIn) return '/sign-in';
      if (signedIn && (goingToSignIn || path == '/')) return '/home';

      return null;
    },
    routes: [
      GoRoute(
        path: '/',
        name: Routes.loading,
        builder: (context, state) => const _LoadingScreen(),
      ),

      // ---------- US-02 (Karen): inicio y cierre de sesión ----------------
      // El cierre no tiene ruta propia: lo dispara `Session.signOut` desde
      // donde esté el botón —hoy la pantalla de después de entrar, mañana el
      // perfil de US-05— y la redirección de arriba se encarga del resto.
      GoRoute(
        path: '/sign-in',
        name: Routes.signIn,
        builder: (context, state) => const SignInScreen(),
      ),

      // ---------- Pantalla de después de entrar ---------------------------
      // La reemplaza la primera historia que traiga la cara del paciente.
      GoRoute(
        path: '/home',
        name: Routes.home,
        builder: (context, state) => const _HomeScreen(),
      ),

      // ---------- US-16 (Alexander): búsqueda de profesionales -----------
      GoRoute(
        path: '/specialties',
        name: Routes.specialties,
        builder: (context, state) => const SpecialtiesScreen(),
      ),
      GoRoute(
        path: '/search',
        name: Routes.search,
        builder: (context, state) => SearchScreen(
          specialtyId: state.uri.queryParameters['specialty'],
        ),
      ),

      // ---------- US-07 (SM): personas a cargo ---------------------------
      // `/dependents/new` es hija de `/dependents` para que el botón atrás
      // vuelva al listado y no a la pantalla de inicio.
      GoRoute(
        path: '/dependents',
        name: Routes.dependents,
        builder: (context, state) => const DependentsScreen(),
        routes: [
          GoRoute(
            path: 'new',
            name: Routes.dependentForm,
            builder: (context, state) => const DependentFormScreen(),
          ),
        ],
      ),

      // ---------- US-15 (Alexander): disponibilidad consolidada ---------
      GoRoute(
        path: '/professionals/:id/availability',
        name: Routes.availability,
        builder: (context, state) => AvailabilityScreen(
          practitionerId: state.pathParameters['id']!,
          practitionerName: state.uri.queryParameters['name'],
        ),
      ),
    ],
  );
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    return const Scaffold(
      body: Center(child: CircularProgressIndicator()),
    );
  }
}

/// Lo que se ve al entrar, hasta que una historia ponga algo real.
///
/// Muestra el estado del shell —quién entró, de qué organización— porque es lo
/// que hay que poder comprobar de un vistazo cuando algo del contexto de
/// inquilino no anda.
class _HomeScreen extends StatelessWidget {
  const _HomeScreen();

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final user = session.user;
    final theme = Theme.of(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Centro médico'),
        actions: [
          IconButton(
            tooltip: 'Cerrar sesión',
            onPressed: session.signOut,
            icon: const Icon(Icons.logout),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              user?.fullName ?? 'Sesión iniciada',
              style: theme.textTheme.titleLarge,
            ),
            const SizedBox(height: 4),
            Text(
              'Centro médico: ${session.organizationSlug ?? "—"}',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              // `push`, no `go`: así el botón atrás del teléfono vuelve acá en
              // lugar de cerrar la aplicación.
              onPressed: () => context.push('/specialties'),
              icon: const Icon(Icons.search),
              label: const Text('Buscar profesionales'),
            ),
            const SizedBox(height: 12),
            // ---------- US-07 (SM): personas a cargo ---------------------
            OutlinedButton.icon(
              onPressed: () => context.push('/dependents'),
              icon: const Icon(Icons.family_restroom),
              label: const Text('Personas a mi cargo'),
            ),
            const SizedBox(height: 12),
            Text(
              'El shell está listo. Cada historia agrega su pantalla en '
              'lib/features/ y su ruta en core/router/app_router.dart.',
              style: theme.textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
