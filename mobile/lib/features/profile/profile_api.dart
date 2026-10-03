/// US-05 — El perfil propio y el cambio de contraseña (móvil).
///
///     GET   /api/accounts/users/me/            el perfil de quien tiene la sesión
///     PATCH /api/accounts/users/me/            sólo los campos que cambiaron
///     POST  /api/accounts/users/me/password/   actual + nueva -> par nuevo
///
/// Es el mismo endpoint que usa la web (`frontend/src/api/perfil.ts`), que es
/// el punto (f) de la historia. La ruta no lleva identificador: el backend saca
/// al usuario del token.
library;

import 'package:mobile/core/api/client.dart';

class Profile {
  const Profile({
    required this.id,
    required this.email,
    required this.firstName,
    required this.lastName,
    required this.fullName,
    required this.phone,
    required this.documentType,
    required this.documentNumber,
    required this.organizationName,
    required this.roles,
    required this.isPlatformAdmin,
    required this.isActive,
  });

  final String id;
  final String email;
  final String firstName;
  final String lastName;
  final String fullName;
  final String phone;
  final String documentType;
  final String documentNumber;

  /// `null` sólo para el Superadministrador de Plataforma.
  final String? organizationName;

  /// Los nombres de los roles, para mostrar.
  final List<String> roles;
  final bool isPlatformAdmin;
  final bool isActive;

  factory Profile.fromJson(Map<String, dynamic> json) {
    final organization = json['organization'];
    final roles = json['roles'];
    return Profile(
      id: json['id'] as String? ?? '',
      email: json['email'] as String? ?? '',
      firstName: json['first_name'] as String? ?? '',
      lastName: json['last_name'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      phone: json['phone'] as String? ?? '',
      documentType: json['document_type'] as String? ?? '',
      documentNumber: json['document_number'] as String? ?? '',
      organizationName: organization is Map<String, dynamic>
          ? organization['name'] as String?
          : null,
      roles: roles is List
          ? roles
                .whereType<Map<String, dynamic>>()
                .map((rol) => rol['name'] as String? ?? '')
                .where((nombre) => nombre.isNotEmpty)
                .toList()
          : const [],
      isPlatformAdmin: json['is_platform_admin'] == true,
      isActive: json['is_active'] != false,
    );
  }
}

/// El par que devuelve el cambio de contraseña. Los refrescos anteriores
/// quedaron en la lista negra: hay que guardar éste.
class NewTokens {
  const NewTokens({
    required this.access,
    required this.refresh,
    required this.message,
  });

  final String access;
  final String refresh;
  final String message;
}

Future<Profile> obtenerPerfil(ApiClient client) async {
  final data = await client.get('/accounts/users/me/');
  if (data is! Map<String, dynamic>) {
    throw const FormatException('Perfil sin formato.');
  }
  return Profile.fromJson(data);
}

/// Guardado parcial (punto f): se manda sólo lo que cambió.
Future<Profile> actualizarPerfil(
  ApiClient client,
  Map<String, String> cambios,
) async {
  final data = await client.patch('/accounts/users/me/', body: cambios);
  if (data is! Map<String, dynamic>) {
    throw const FormatException('Perfil sin formato.');
  }
  return Profile.fromJson(data);
}

Future<NewTokens> cambiarContrasena(
  ApiClient client, {
  required String actual,
  required String nueva,
  required String repetida,
}) async {
  final data = await client.post(
    '/accounts/users/me/password/',
    body: {
      'current_password': actual,
      'password': nueva,
      'password_confirmation': repetida,
    },
  );
  if (data is! Map<String, dynamic> ||
      data['access'] is! String ||
      data['refresh'] is! String) {
    throw const FormatException('Respuesta sin tokens.');
  }
  return NewTokens(
    access: data['access'] as String,
    refresh: data['refresh'] as String,
    message: data['detail'] as String? ?? 'Tu contraseña se cambió.',
  );
}
