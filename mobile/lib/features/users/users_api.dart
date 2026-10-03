/// US-04 — Usuarios, roles y permisos de la organización.
///
/// Espejo móvil de `frontend/src/paginas/Usuarios.tsx` y `Roles.tsx`.
///
/// **Los usuarios son de sólo lectura.** `AssignableUserViewSet` es un
/// `ReadOnlyModelViewSet` (`backend/accounts/views/roles.py:233`): desde acá
/// no se dan de alta, se listan y se les asignan o quitan roles, que se hace
/// por `/accounts/user-roles/` — el único endpoint con escritura de esta
/// sección, y sólo `POST` y `DELETE`, sin `PATCH`.
///
/// Los roles sí se crean y editan, con sus permisos elegidos de un catálogo
/// global de sólo lectura.
library;

import '../../core/api/client.dart';
import '../../core/api/paginacion.dart';

class RolAsignado {
  const RolAsignado({required this.id, required this.code, required this.name});

  final String id;
  final String code;
  final String name;

  factory RolAsignado.fromJson(Map<String, dynamic> json) => RolAsignado(
        id: json['id'] as String? ?? '',
        code: json['code'] as String? ?? '',
        name: json['name'] as String? ?? '',
      );
}

class UsuarioDeOrganizacion {
  const UsuarioDeOrganizacion({
    required this.id,
    required this.email,
    required this.fullName,
    required this.isActive,
    required this.roles,
  });

  final String id;
  final String email;
  final String fullName;
  final bool isActive;
  final List<RolAsignado> roles;

  factory UsuarioDeOrganizacion.fromJson(Map<String, dynamic> json) =>
      UsuarioDeOrganizacion(
        id: json['id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? false,
        roles: (json['roles'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(RolAsignado.fromJson)
            .toList(),
      );
}

class Rol {
  const Rol({
    required this.id,
    required this.code,
    required this.name,
    required this.description,
    required this.isSystem,
    required this.isActive,
    required this.assignedUsers,
    required this.permissions,
  });

  final String id;
  final String code;
  final String name;
  final String description;

  /// Los roles de sistema los clona el alta de organización y no se borran.
  final bool isSystem;

  final bool isActive;
  final int assignedUsers;

  /// Códigos de permiso, no objetos.
  final List<String> permissions;

  factory Rol.fromJson(Map<String, dynamic> json) => Rol(
        id: json['id'] as String? ?? '',
        code: json['code'] as String? ?? '',
        name: json['name'] as String? ?? '',
        description: json['description'] as String? ?? '',
        isSystem: json['is_system'] as bool? ?? false,
        isActive: json['is_active'] as bool? ?? false,
        assignedUsers: json['assigned_users'] as int? ?? 0,
        permissions:
            (json['permissions'] as List? ?? const []).cast<String>(),
      );
}

class Permiso {
  const Permiso({
    required this.code,
    required this.module,
    required this.description,
  });

  final String code;

  /// La primera parte del código (`catalog`, `scheduling`, …). Sirve para
  /// agrupar: cuarenta casillas sueltas no se leen.
  final String module;

  final String description;

  factory Permiso.fromJson(Map<String, dynamic> json) => Permiso(
        code: json['code'] as String? ?? '',
        module: json['module'] as String? ?? '',
        description: json['description'] as String? ?? '',
      );
}

/// Una página de usuarios, opcionalmente filtrada por correo.
///
/// Paginada y no completa: una organización real tiene decenas de cuentas
/// (unas 80 en las de prueba con datos reales) y la pantalla las muestra con
/// "Cargar más". El filtro [search] lo resuelve el backend
/// (`AssignableUserViewSet.get_queryset`) y busca **sólo en el correo**
/// (`email__icontains`), no en el nombre.
Future<Pagina<UsuarioDeOrganizacion>> listarUsuarios(
  ApiClient client, {
  String? search,
  int page = 1,
}) {
  final buscado = search?.trim() ?? '';
  final ruta = buscado.isEmpty
      ? '/accounts/users/'
      : '/accounts/users/?search=${Uri.encodeQueryComponent(buscado)}';
  return unaPagina(client, ruta, UsuarioDeOrganizacion.fromJson, page: page);
}

/// Todos los roles de la organización.
///
/// Completos: alimentan los interruptores de "Gestionar roles", y un rol que
/// quedara en la página 2 no se podría asignar desde el teléfono.
Future<List<Rol>> listarRoles(ApiClient client) =>
    todasLasPaginas(client, '/accounts/roles/', Rol.fromJson);

Future<List<Permiso>> listarPermisos(ApiClient client) async {
  final data = await client.get('/accounts/permissions/');
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  final crudos = mapa['results'] as List? ?? (data is List ? data : const []);
  return crudos
      .whereType<Map<String, dynamic>>()
      .map(Permiso.fromJson)
      .toList();
}

Future<Rol> crearRol(
  ApiClient client, {
  required String code,
  required String name,
  required String description,
  required List<String> permissions,
}) async {
  final data = await client.post('/accounts/roles/', body: {
    'code': code,
    'name': name,
    'description': description,
    'permissions': permissions,
  });
  return Rol.fromJson(data as Map<String, dynamic>);
}

Future<Rol> editarRol(
  ApiClient client,
  String id, {
  required String name,
  required String description,
  required List<String> permissions,
}) async {
  // Sin `code`: el backend no lo deja cambiar después de crear el rol, es la
  // clave con la que se lo referencia.
  final data = await client.patch('/accounts/roles/$id/', body: {
    'name': name,
    'description': description,
    'permissions': permissions,
  });
  return Rol.fromJson(data as Map<String, dynamic>);
}

/// Le da un rol a alguien.
Future<void> asignarRol(
  ApiClient client, {
  required String userId,
  required String roleId,
}) =>
    client.post('/accounts/user-roles/', body: {
      'user': userId,
      'role': roleId,
    });

/// Le quita un rol. Hace falta el id **de la asignación**, no el del rol.
Future<void> quitarAsignacion(ApiClient client, int asignacionId) =>
    client.delete('/accounts/user-roles/$asignacionId/');

/// Las asignaciones vigentes **de un usuario**, para poder quitar una.
///
/// El listado de usuarios trae los roles de cada uno, pero no el id de la
/// asignación, que es lo que `DELETE` necesita.
///
/// Antes se pedía `/accounts/user-roles/` entero y se tomaba sólo la primera
/// página: con 80 personas y sus roles eran más de 25 asignaciones, y al
/// quitarle un rol a alguien que había caído en otra página la app contestaba
/// "No se encontró la asignación". Ahora se filtra por `?user=<id>`
/// (`UserRoleViewSet.get_queryset` lo admite) y se recorren igual todas sus
/// páginas, por si alguien acumula más de 25 roles.
///
/// La clave sigue siendo `usuario|rol` para no cambiar a quien la consulta.
Future<Map<String, int>> mapaDeAsignaciones(
  ApiClient client, {
  required String userId,
}) async {
  final filas = await todasLasPaginas(
    client,
    '/accounts/user-roles/?user=${Uri.encodeQueryComponent(userId)}',
    (fila) => fila,
  );
  final resultado = <String, int>{};
  for (final fila in filas) {
    final usuario = fila['user'] as String? ?? '';
    final rol = fila['role'] as String? ?? '';
    final id = fila['id'] as int?;
    if (id != null) resultado['$usuario|$rol'] = id;
  }
  return resultado;
}
