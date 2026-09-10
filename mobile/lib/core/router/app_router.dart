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

import '../../features/auth/register_screen.dart';
import '../../features/auth/sign_in_screen.dart';
import '../../features/availability/availability_screen.dart';
import '../../features/dependents/dependent_form_screen.dart';
import '../../features/dependents/dependents_screen.dart';
import '../../features/history/history_screen.dart';
import '../../features/metrics/metrics_screen.dart';
import '../../features/organizations/organizations_screen.dart';
import '../../features/organizations/register_organization_screen.dart';
import '../../features/plans/plan_form_screen.dart';
import '../../features/plans/plans_api.dart';
import '../../features/plans/plans_screen.dart';
import '../../features/search/search_screen.dart';
import '../../features/search/specialties_screen.dart';
import '../../features/subscriptions/change_plan_screen.dart';
import '../../features/subscriptions/subscription_history_screen.dart';
import '../../features/subscriptions/subscriptions_api.dart';
import '../../features/subscriptions/subscriptions_screen.dart';
import '../session/patient_gate.dart';
import '../session/session.dart';
import '../session/session_scope.dart';
import '../theme/theme.dart';

/// Los nombres se usan con `context.goNamed(Routes.signIn)`, para que cambiar
/// una ruta no obligue a buscar la cadena por todo el proyecto.
class Routes {
  const Routes._();

  static const String loading = 'loading';
  static const String signIn = 'sign-in';
  static const String register = 'register';
  static const String home = 'home';
  static const String specialties = 'specialties';
  static const String search = 'search';
  static const String availability = 'availability';
  static const String dependents = 'dependents';
  static const String dependentForm = 'dependent-form';
  static const String history = 'history';
  static const String platformDashboard = 'platform-dashboard';
  static const String platformOrganizations = 'platform-organizations';
  static const String platformOrganizationForm = 'platform-organization-form';
  static const String platformPlans = 'platform-plans';
  static const String platformPlanNew = 'platform-plan-new';
  static const String platformPlanEdit = 'platform-plan-edit';
  static const String platformSubscriptions = 'platform-subscriptions';
  static const String platformSubscriptionChange = 'platform-subscription-change';
  static const String platformSubscriptionHistory = 'platform-subscription-history';
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
      final publicRoute = path == '/sign-in' || path == '/register';

      if (!signedIn && !publicRoute) return '/sign-in';
      if (signedIn && (publicRoute || path == '/')) return '/home';

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

      // ---------- US-01: registro de paciente ------------------------------
      GoRoute(
        path: '/register',
        name: Routes.register,
        builder: (context, state) => const RegisterScreen(),
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
      // vuelva al listado y no a la pantalla de inicio. `SoloPacientes`
      // -no seguridad, el backend ya la pone- evita que alguien que llegue
      // acá por un enlace directo dispare una petición que no le corresponde.
      GoRoute(
        path: '/dependents',
        name: Routes.dependents,
        builder: (context, state) => const SoloPacientes(
          titulo: 'Personas a cargo',
          child: DependentsScreen(),
        ),
        routes: [
          GoRoute(
            path: 'new',
            name: Routes.dependentForm,
            builder: (context, state) => const SoloPacientes(
              titulo: 'Agregar persona a cargo',
              child: DependentFormScreen(),
            ),
          ),
        ],
      ),

      // ---------- US-08 (SM): antecedentes -------------------------------
      GoRoute(
        path: '/history',
        name: Routes.history,
        builder: (context, state) => const SoloPacientes(
          titulo: 'Antecedentes',
          child: HistoryScreen(),
        ),
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

      // ---------- US-45 (Luis Miguel): panel del superadministrador -----
      // Sin `SoloPacientes` ni gate propio: `IsPlatformAdmin` en el backend
      // ya responde 403 limpio a cualquiera que no sea superadmin -a
      // diferencia de `/patients/history/`, acá no hay un caso de 200 con
      // datos vacíos y engañosos que evitar-, así que el manejo de
      // `ApiError` que ya tiene la pantalla alcanza.
      GoRoute(
        path: '/platform/dashboard',
        name: Routes.platformDashboard,
        builder: (context, state) => const PlatformDashboardScreen(),
      ),

      // ---------- US-43 (Luis Mateo): organizaciones ---------------------
      GoRoute(
        path: '/platform/organizations',
        name: Routes.platformOrganizations,
        builder: (context, state) => const OrganizationsScreen(),
      ),
      GoRoute(
        path: '/platform/organizations/new',
        name: Routes.platformOrganizationForm,
        builder: (context, state) => const RegisterOrganizationScreen(),
      ),

      // ---------- US-44 (Daniel): planes y suscripciones ------------------
      GoRoute(
        path: '/platform/plans',
        name: Routes.platformPlans,
        builder: (context, state) => const PlansScreen(),
      ),
      GoRoute(
        path: '/platform/plans/new',
        name: Routes.platformPlanNew,
        builder: (context, state) => const PlanFormScreen(),
      ),
      GoRoute(
        path: '/platform/plans/:id/edit',
        name: Routes.platformPlanEdit,
        builder: (context, state) => PlanFormScreen(
          planExistente: state.extra as Plan?,
        ),
      ),
      GoRoute(
        path: '/platform/subscriptions',
        name: Routes.platformSubscriptions,
        builder: (context, state) => const SubscriptionsScreen(),
      ),
      GoRoute(
        path: '/platform/subscriptions/change',
        name: Routes.platformSubscriptionChange,
        builder: (context, state) => ChangePlanScreen(
          suscripcionActual: state.extra as Subscription,
        ),
      ),
      // Cuelga de `/platform/organizations/...` -no de `/subscriptions`-
      // porque así resuelve el backend (`organizations/{id}/subscriptions/`).
      GoRoute(
        path: '/platform/organizations/:id/subscriptions',
        name: Routes.platformSubscriptionHistory,
        builder: (context, state) {
          final extra = state.extra as Map<String, String>?;
          return SubscriptionHistoryScreen(
            organizationId: state.pathParameters['id']!,
            organizationName: extra?['name'] ?? '',
          );
        },
      ),
    ],
  );
}

class _LoadingScreen extends StatelessWidget {
  const _LoadingScreen();

  @override
  Widget build(BuildContext context) {
    // Degradé estático -sin animar-: es una pantalla transitoria, dura lo
    // que tarda en leerse el almacenamiento seguro, no vale la pena el
    // `AnimationController` que sí tiene `BrandHeader`.
    return const DecoratedBox(
      decoration: BoxDecoration(
        gradient: RadialGradient(colors: Marca.gradient, radius: 1.2),
      ),
      child: Center(child: CircularProgressIndicator(color: Colors.white)),
    );
  }
}

/// Lo que se ve al entrar, hasta que una historia ponga algo real.
///
/// Muestra el estado del shell —quién entró, de qué organización— porque es lo
/// que hay que poder comprobar de un vistazo cuando algo del contexto de
/// inquilino no anda.
///
/// **Los accesos de acá abajo son sólo para pacientes.** El router no
/// redirige por rol -sigue siendo sólo por autenticación, igual que
/// `RutaProtegida` en el frontend web-, así que la diferenciación va acá
/// adentro, igual que hace `Panel.tsx` en la web según
/// `usuario.is_platform_admin`. `user?.isPatient ?? true`: sin datos del
/// usuario todavía -sesión reabierta sin red-, no hay que esconder de más;
/// la pantalla de destino, si no correspondía, falla sola.
class _HomeScreen extends StatelessWidget {
  const _HomeScreen();

  @override
  Widget build(BuildContext context) {
    final session = SessionScope.of(context);
    final user = session.user;
    final theme = Theme.of(context);
    final esPaciente = user?.isPatient ?? true;
    final esSuperadmin = user?.isPlatformAdmin ?? false;

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
      body: ListView(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(24, 20, 24, 28),
            decoration: BoxDecoration(color: Marca.surfaceTint),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(
                  radius: 24,
                  backgroundColor: Marca.primary,
                  child: Text(
                    (user?.fullName.isNotEmpty ?? false)
                        ? user!.fullName[0].toUpperCase()
                        : '?',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.w700,
                      fontSize: 18,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                // Colores fijos, no los del tema: `Marca.surfaceTint` es un
                // fondo claro sin importar el brillo de la app, y el texto
                // del tema en modo oscuro quedaría casi invisible encima.
                Text(
                  user?.fullName ?? 'Sesión iniciada',
                  style: theme.textTheme.titleLarge?.copyWith(
                    color: Marca.ink900,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Centro médico: ${session.organizationSlug ?? "—"}',
                  style: theme.textTheme.bodyMedium
                      ?.copyWith(color: Marca.ink500),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 20),
            child: esPaciente
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: _accesosDePaciente(context),
                  )
                : esSuperadmin
                    // ---------- US-45 (Luis Miguel): panel del superadmin --
                    ? _accesoTarjeta(
                        context,
                        icono: Icons.dashboard_outlined,
                        titulo: 'Panel de la plataforma',
                        subtitulo:
                            'Organizaciones, planes y alertas de aislamiento',
                        onTap: () => context.push('/platform/dashboard'),
                      )
                    : _avisoNoPaciente(theme),
          ),
        ],
      ),
    );
  }

  /// Los tres accesos de auto-servicio del paciente, como tarjetas con
  /// ícono en vez de botones en columna -más jerarquía visual, menos "es un
  /// formulario más".
  List<Widget> _accesosDePaciente(BuildContext context) => [
        _accesoTarjeta(
          context,
          icono: Icons.search,
          titulo: 'Buscar profesionales',
          subtitulo: 'Especialidades, sedes y disponibilidad',
          // `push`, no `go`: así el botón atrás del teléfono vuelve acá en
          // lugar de cerrar la aplicación.
          onTap: () => context.push('/specialties'),
        ),
        const SizedBox(height: 12),
        // ---------- US-07 (SM): personas a cargo -----------------------
        _accesoTarjeta(
          context,
          icono: Icons.family_restroom,
          titulo: 'Personas a mi cargo',
          subtitulo: 'Dependientes y su información',
          onTap: () => context.push('/dependents'),
        ),
        const SizedBox(height: 12),
        // ---------- US-08 (SM): antecedentes -----------------------------
        _accesoTarjeta(
          context,
          icono: Icons.medical_information_outlined,
          titulo: 'Mis antecedentes',
          subtitulo: 'Alergias, condiciones y medicación declaradas',
          onTap: () => context.push('/history'),
        ),
      ];

  Widget _accesoTarjeta(
    BuildContext context, {
    required IconData icono,
    required String titulo,
    required String subtitulo,
    required VoidCallback onTap,
  }) {
    final theme = Theme.of(context);
    return Card(
      margin: EdgeInsets.zero,
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: CircleAvatar(
          radius: 20,
          backgroundColor: Marca.surfaceTint,
          child: Icon(icono, color: Marca.primary),
        ),
        title: Text(titulo, style: theme.textTheme.titleMedium),
        subtitle: Text(subtitulo, style: theme.textTheme.bodySmall),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }

  /// Lo que ve quien no es paciente -superadministrador, administrador de
  /// organización, profesional-: ninguno de los accesos de arriba tiene
  /// sentido para ellos hoy. Mensaje de paso, igual que la web todavía no
  /// tiene una pantalla propia por rol (eso es US-45, aparte).
  Widget _avisoNoPaciente(ThemeData theme) => Card(
        color: theme.colorScheme.surfaceContainerHighest,
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(Icons.info_outline, color: theme.colorScheme.onSurfaceVariant),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  'Esta sección de la aplicación es para pacientes. '
                  'Iniciá sesión desde la plataforma web para administrar '
                  'tu organización.',
                  style: theme.textTheme.bodyMedium,
                ),
              ),
            ],
          ),
        ),
      );
}
