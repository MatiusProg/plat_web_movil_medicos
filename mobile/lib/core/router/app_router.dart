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
import '../../features/audit/audit_screen.dart';
import '../../features/catalog/branches_screen.dart';
import '../../features/catalog/professionals_admin_screen.dart';
import '../../features/catalog/specialties_admin_screen.dart';
import '../../features/organization/organization_home_screen.dart';
import '../../features/users/roles_screen.dart';
import '../../features/users/users_screen.dart';
import '../../features/schedules/org_availability_screen.dart';
import '../../features/schedules/schedule_form_screen.dart';
import '../../features/schedules/schedules_api.dart';
import '../../features/schedules/schedules_screen.dart';
import '../session/org_gate.dart';
import '../session/patient_gate.dart';
import '../session/session.dart';
import '../session/session_scope.dart';
import '../theme/theme.dart';
import '../widgets/organization_drawer.dart';

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

  // La cara de la organización.
  static const String organizationHome = 'organization-home';
  static const String orgSchedules = 'org-schedules';
  static const String orgScheduleForm = 'org-schedule-form';
  static const String orgAvailability = 'org-availability';
  static const String orgBranches = 'org-branches';
  static const String orgSpecialties = 'org-specialties';
  static const String orgProfessionals = 'org-professionals';
  static const String orgAudit = 'org-audit';
  static const String orgUsers = 'org-users';
  static const String orgRoles = 'org-roles';
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

      // ---------- La cara de quien administra un centro médico -----------
      // Cada sección cuelga de `/org` y va gateada por su permiso, igual que
      // en la barra lateral de la web. El panel en sí no lleva guarda: es la
      // lista de lo que la persona **sí** puede, y si no puede nada lo dice.
      GoRoute(
        path: '/org',
        name: Routes.organizationHome,
        builder: (context, state) => const OrganizationHomeScreen(),
      ),

      // ---------- US-13 (Alexander): agendas médicas ---------------------
      GoRoute(
        path: '/org/agendas',
        name: Routes.orgSchedules,
        builder: (context, state) => const ConPermiso(
          permiso: 'scheduling.schedule.read',
          titulo: 'Agendas',
          child: SchedulesScreen(),
        ),
      ),
      GoRoute(
        path: '/org/agendas/form',
        name: Routes.orgScheduleForm,
        // El profesional y la regla viajan en `extra` porque el formulario se
        // abre siempre desde el listado, que ya los tiene. Si no vinieran, no
        // hay nada que editar: se vuelve al listado en vez de reventar.
        builder: (context, state) {
          final datos = state.extra;
          if (datos is! Map) return const _FaltaLaRegla();
          final practitioner = datos['practitioner'];
          if (practitioner is! String) return const _FaltaLaRegla();
          return ConPermiso(
            permiso: 'scheduling.schedule.create',
            titulo: 'Regla de agenda',
            child: ScheduleFormScreen(
              practitionerId: practitioner,
              existente: datos['agenda'] as Agenda?,
            ),
          );
        },
      ),

      // ---------- US-14 (Alexander): disponibilidad consolidada ----------
      // ---------- US-04 (Karen): usuarios, roles y permisos -------------
      GoRoute(
        path: '/org/usuarios',
        name: Routes.orgUsers,
        builder: (context, state) => const ConPermiso(
          permiso: 'users.user.read',
          titulo: 'Usuarios',
          child: UsersScreen(),
        ),
      ),
      GoRoute(
        path: '/org/roles',
        name: Routes.orgRoles,
        builder: (context, state) => const ConPermiso(
          permiso: 'users.role.read',
          titulo: 'Roles y permisos',
          child: RolesScreen(),
        ),
      ),

      // ---------- US-06 (SM): bitácora de auditoría ---------------------
      GoRoute(
        path: '/org/bitacora',
        name: Routes.orgAudit,
        builder: (context, state) => const ConPermiso(
          permiso: 'audit.log.read',
          titulo: 'Bitácora',
          child: AuditScreen(),
        ),
      ),

      // ---------- US-11 y US-12 (Matías): catálogo del centro médico ----
      GoRoute(
        path: '/org/sucursales',
        name: Routes.orgBranches,
        builder: (context, state) => const ConPermiso(
          permiso: 'catalog.branch.read',
          titulo: 'Sucursales',
          child: BranchesScreen(),
        ),
      ),
      GoRoute(
        path: '/org/especialidades',
        name: Routes.orgSpecialties,
        builder: (context, state) => const ConPermiso(
          permiso: 'catalog.specialty.read',
          titulo: 'Especialidades',
          child: SpecialtiesAdminScreen(),
        ),
      ),
      GoRoute(
        path: '/org/profesionales',
        name: Routes.orgProfessionals,
        builder: (context, state) => const ConPermiso(
          permiso: 'catalog.professional.read',
          titulo: 'Profesionales',
          child: ProfessionalsAdminScreen(),
        ),
      ),

      GoRoute(
        path: '/org/disponibilidad',
        name: Routes.orgAvailability,
        builder: (context, state) => const ConPermiso(
          permiso: 'scheduling.slot.read',
          titulo: 'Disponibilidad',
          child: OrgAvailabilityScreen(),
        ),
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
        // El id de la ruta es la fuente de verdad, no `state.extra`: si el
        // objeto no viaja -reinicio, restauración de estado, o entrar por la
        // ruta directamente- el formulario se creía un alta y **creaba un
        // plan duplicado**.
        builder: (context, state) => EditarPlanPorId(
          id: state.pathParameters['id']!,
          precargado: state.extra as Plan?,
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
        // El cast era `as Subscription`, sin `?`: con `extra` nulo lanzaba un
        // `TypeError` **al construir la ruta**, o sea la pantalla roja de
        // Flutter, sin barra de título y sin más salida que el botón atrás
        // del sistema. A diferencia de la edición de plan, acá el id no viaja
        // en la ruta y no hay nada que resolver, así que se explica y se
        // ofrece volver al listado, que es de donde hay que entrar.
        builder: (context, state) {
          final suscripcion = state.extra;
          if (suscripcion is! Subscription) {
            return const _FaltaLaSuscripcion();
          }
          return ChangePlanScreen(suscripcionActual: suscripcion);
        },
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
    // Sin `?? true`: no saber quién es NO es lo mismo que ser paciente. Ese
    // valor por omisión le mostraba a un administrador -y al propio
    // superadministrador, que perdía el acceso a su panel- las tres tarjetas
    // de auto-servicio, que al tocarlas dan 403 o, peor, una lista vacía que
    // parece decir "no tenés nada a cargo". Cuando no se sabe, se dice.
    final esPaciente = user?.isPatient ?? false;
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
            child: session.cargandoUsuario
                ? const _CargandoPerfil()
                : session.perfilNoDisponible
                    ? _PerfilNoDisponible(onReintentar: session.recargarUsuario)
                    : esPaciente
                        ? Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: _accesosDePaciente(context),
                          )
                        : esSuperadmin
                            // ------ US-45 (Luis Miguel): panel del superadmin
                            ? _accesoTarjeta(
                                context,
                                icono: Icons.dashboard_outlined,
                                titulo: 'Panel de la plataforma',
                                subtitulo:
                                    'Organizaciones, planes y alertas de aislamiento',
                                onTap: () => context.push('/platform/dashboard'),
                              )
                            // ------ La cara de quien administra un centro
                            // médico. El cartel de "esto es para pacientes"
                            // queda sólo para quien de verdad no tiene ni una
                            // sección habilitada.
                            : _tieneSeccionesDeOrganizacion(user)
                                ? _accesoTarjeta(
                                    context,
                                    icono: Icons.medical_services_outlined,
                                    titulo: 'Panel del centro médico',
                                    subtitulo:
                                        'Agendas, catálogo, usuarios y bitácora',
                                    onTap: () => context.push('/org'),
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
  /// Si sus permisos le abren al menos una de las nueve secciones.
  ///
  /// Se pregunta por permisos y no por rol a propósito: los roles los arma
  /// cada organización (US-04), y un rol nuevo con permiso de agendas tiene
  /// que funcionar sin tocar la aplicación.
  static bool _tieneSeccionesDeOrganizacion(CurrentUser? user) =>
      user != null &&
      seccionesDeOrganizacion.any((seccion) => user.can(seccion.permiso));

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


/// Se entró al formulario de agenda sin saber de qué profesional es.
///
/// Mismo criterio que [_FaltaLaSuscripcion]: en vez de un cast que revienta,
/// se explica y se ofrece la puerta de vuelta.
class _FaltaLaRegla extends StatelessWidget {
  const _FaltaLaRegla();

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Regla de agenda')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'No sabemos de qué profesional es esta regla. Entrá desde '
                  'Agendas y elegí uno.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.tonalIcon(
                  onPressed: () => context.go('/org/agendas'),
                  icon: const Icon(Icons.event_note_outlined),
                  label: const Text('Ir a Agendas'),
                ),
              ],
            ),
          ),
        ),
      );
}


/// Se entró a "cambiar plan" sin saber qué suscripción se cambia.
///
/// Reemplaza a la pantalla roja de Flutter que salía antes: mismo callejón,
/// pero explicado y con una puerta.
class _FaltaLaSuscripcion extends StatelessWidget {
  const _FaltaLaSuscripcion();

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Cambiar plan')),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Text(
                  'No sabemos qué suscripción querés cambiar. Entrá desde el '
                  'listado y elegí la organización.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                FilledButton.tonalIcon(
                  onPressed: () => context.go('/platform/subscriptions'),
                  icon: const Icon(Icons.list_alt),
                  label: const Text('Ir a Suscripciones'),
                ),
              ],
            ),
          ),
        ),
      );
}


/// Mientras se pide el perfil a `/accounts/me/`.
///
/// Ocupa el lugar de los accesos y no toda la pantalla: arriba ya se ve el
/// nombre y la organización, así que la aplicación se siente abierta aunque
/// falte saber el rol.
class _CargandoPerfil extends StatelessWidget {
  const _CargandoPerfil();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.symmetric(vertical: 32),
        child: Column(
          children: [
            SizedBox(
              width: 28,
              height: 28,
              child: CircularProgressIndicator(strokeWidth: 3),
            ),
            SizedBox(height: 16),
            Text('Cargando tu perfil…'),
          ],
        ),
      );
}


/// Hay sesión pero no se pudo traer el perfil.
///
/// Antes este caso no existía: se asumía "paciente" y se mostraban las tres
/// tarjetas de auto-servicio a cualquiera, incluido el superadministrador,
/// que además perdía el acceso a su panel. Decir que no se sabe y ofrecer
/// reintentar es más honesto y deja una salida que no es cerrar sesión.
class _PerfilNoDisponible extends StatelessWidget {
  const _PerfilNoDisponible({required this.onReintentar});

  final Future<void> Function() onReintentar;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      color: theme.colorScheme.surfaceContainerHighest,
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  Icons.cloud_off_outlined,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'No pudimos confirmar tu perfil, así que todavía no '
                    'sabemos qué mostrarte. Revisá tu conexión y volvé a '
                    'intentar.',
                    style: theme.textTheme.bodyMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: FilledButton.tonalIcon(
                onPressed: onReintentar,
                icon: const Icon(Icons.refresh),
                label: const Text('Reintentar'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
