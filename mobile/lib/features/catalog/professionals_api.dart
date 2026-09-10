/// US-12 — Profesionales del centro médico, del lado de quien administra.
///
/// El endpoint es `professionals/manage/` y no `professionals/`: el segundo es
/// la **búsqueda** que usa el paciente —pagina, ordena por disponibilidad y
/// trae el próximo espacio libre—, y este es el catálogo administrativo, sin
/// paginar y con lo que hace falta para editar.
///
/// Especialidades y sedes viajan como listas de ids al escribir y vuelven como
/// objetos `{id, name}` al leer, que es como lo resuelve el serializer del
/// backend (`PractitionerWriteSerializer` / `PractitionerAdminSerializer`).
library;

import '../../core/api/client.dart';

/// Una especialidad o una sede, tal como vienen anidadas en el profesional.
class Etiqueta {
  const Etiqueta({required this.id, required this.name});

  final String id;
  final String name;

  factory Etiqueta.fromJson(Map<String, dynamic> json) => Etiqueta(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
      );
}

class Profesional {
  const Profesional({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.fullName,
    required this.licenseNumber,
    required this.isActive,
    required this.specialties,
    required this.branches,
  });

  final String id;
  final String firstName;
  final String lastName;
  final String fullName;

  /// La matrícula profesional.
  final String licenseNumber;

  final bool isActive;
  final List<Etiqueta> specialties;
  final List<Etiqueta> branches;

  factory Profesional.fromJson(Map<String, dynamic> json) => Profesional(
        id: json['id'] as String? ?? '',
        firstName: json['first_name'] as String? ?? '',
        lastName: json['last_name'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        licenseNumber: json['license_number'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? false,
        specialties: (json['specialties'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Etiqueta.fromJson)
            .toList(),
        branches: (json['branches'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(Etiqueta.fromJson)
            .toList(),
      );
}

Future<List<Profesional>> listarProfesionalesAdmin(ApiClient client) async {
  final data = await client.get('/catalog/professionals/manage/');
  return (data as List? ?? const [])
      .map((e) => Profesional.fromJson(e as Map<String, dynamic>))
      .toList();
}

Map<String, dynamic> _cuerpo({
  required String firstName,
  required String lastName,
  required String licenseNumber,
  required List<String> specialtyIds,
  required List<String> branchIds,
}) => {
      'first_name': firstName,
      'last_name': lastName,
      'license_number': licenseNumber,
      'specialties': specialtyIds,
      'branches': branchIds,
    };

Future<Profesional> crearProfesional(
  ApiClient client, {
  required String firstName,
  required String lastName,
  required String licenseNumber,
  required List<String> specialtyIds,
  required List<String> branchIds,
}) async {
  final data = await client.post(
    '/catalog/professionals/manage/',
    body: _cuerpo(
      firstName: firstName,
      lastName: lastName,
      licenseNumber: licenseNumber,
      specialtyIds: specialtyIds,
      branchIds: branchIds,
    ),
  );
  return Profesional.fromJson(data as Map<String, dynamic>);
}

Future<Profesional> editarProfesional(
  ApiClient client,
  String id, {
  required String firstName,
  required String lastName,
  required String licenseNumber,
  required List<String> specialtyIds,
  required List<String> branchIds,
}) async {
  final data = await client.patch(
    '/catalog/professionals/$id/',
    body: _cuerpo(
      firstName: firstName,
      lastName: lastName,
      licenseNumber: licenseNumber,
      specialtyIds: specialtyIds,
      branchIds: branchIds,
    ),
  );
  return Profesional.fromJson(data as Map<String, dynamic>);
}

Future<void> desactivarProfesional(ApiClient client, String id) =>
    client.post('/catalog/professionals/$id/deactivate/');
