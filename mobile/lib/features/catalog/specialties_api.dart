/// US-12 — Especialidades del centro médico, del lado de quien administra.
///
/// **No se pisa con `features/search/search_api.dart`.** Aquel lee el mismo
/// endpoint pero para el paciente, que sólo necesita id y nombre para elegir
/// a quién buscar; acá hacen falta la descripción y el estado, y además crear,
/// editar y dar de baja. Son dos usos distintos del mismo recurso.
///
/// Como el resto del catálogo de una organización, el listado **no pagina**:
/// son unas pocas por centro médico.
library;

import '../../core/api/client.dart';

class Especialidad {
  const Especialidad({
    required this.id,
    required this.name,
    required this.description,
    required this.isActive,
  });

  final String id;
  final String name;
  final String description;
  final bool isActive;

  factory Especialidad.fromJson(Map<String, dynamic> json) => Especialidad(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        description: json['description'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? false,
      );
}

Future<List<Especialidad>> listarEspecialidadesAdmin(ApiClient client) async {
  final data = await client.get('/catalog/specialties/');
  return (data as List? ?? const [])
      .map((e) => Especialidad.fromJson(e as Map<String, dynamic>))
      .toList();
}

Future<Especialidad> crearEspecialidad(
  ApiClient client, {
  required String name,
  required String description,
}) async {
  final data = await client.post(
    '/catalog/specialties/',
    body: {'name': name, 'description': description},
  );
  return Especialidad.fromJson(data as Map<String, dynamic>);
}

Future<Especialidad> editarEspecialidad(
  ApiClient client,
  String id, {
  required String name,
  required String description,
}) async {
  final data = await client.patch(
    '/catalog/specialties/$id/',
    body: {'name': name, 'description': description},
  );
  return Especialidad.fromJson(data as Map<String, dynamic>);
}

Future<void> desactivarEspecialidad(ApiClient client, String id) =>
    client.post('/catalog/specialties/$id/deactivate/');
