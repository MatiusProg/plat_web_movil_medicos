/// US-16 — Búsqueda de profesionales.
///
/// Nombre parcial (sin distinguir mayúsculas ni tildes lo resuelve el
/// backend), filtros por especialidad y por sucursal, y catálogo paginado
/// cuando la búsqueda va vacía.
library;

import 'package:mobile/core/api/client.dart';

class Especialidad {
  const Especialidad({required this.id, required this.name});

  final String id;
  final String name;

  factory Especialidad.fromJson(Map<String, dynamic> json) => Especialidad(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
      );
}

class ProfesionalTarjeta {
  const ProfesionalTarjeta({
    required this.id,
    required this.fullName,
    required this.specialties,
    required this.branches,
    this.nextAvailableSlot,
  });

  final String id;
  final String fullName;
  final List<String> specialties;
  final List<String> branches;

  /// ISO 8601 del próximo espacio reservable, o `null` si no hay agenda.
  final String? nextAvailableSlot;

  factory ProfesionalTarjeta.fromJson(Map<String, dynamic> json) {
    List<String> nombres(String clave) => (json[clave] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map((e) => e['name'] as String? ?? '')
        .where((n) => n.isNotEmpty)
        .toList();

    return ProfesionalTarjeta(
      id: json['id'] as String? ?? '',
      fullName: json['full_name'] as String? ?? '',
      specialties: nombres('specialties'),
      branches: nombres('branches'),
      nextAvailableSlot: json['next_available_slot'] as String?,
    );
  }
}

class PaginaProfesionales {
  const PaginaProfesionales({required this.results, required this.hayMas});

  final List<ProfesionalTarjeta> results;
  final bool hayMas;
}

Future<List<Especialidad>> listarEspecialidades(ApiClient client) async {
  final data = await client.get('/catalog/specialties/');
  return (data as List? ?? const [])
      .whereType<Map<String, dynamic>>()
      .map(Especialidad.fromJson)
      .toList();
}

Future<PaginaProfesionales> buscarProfesionales(
  ApiClient client, {
  String? q,
  String? specialtyId,
  String? branchId,
  int page = 1,
}) async {
  final params = <String, String>{
    if (q != null && q.trim().isNotEmpty) 'q': q.trim(),
    if (specialtyId != null && specialtyId.isNotEmpty) 'specialty': specialtyId,
    if (branchId != null && branchId.isNotEmpty) 'branch': branchId,
    if (page > 1) 'page': '$page',
  };
  final query = params.entries
      .map((e) => '${e.key}=${Uri.encodeQueryComponent(e.value)}')
      .join('&');
  final ruta =
      query.isEmpty ? '/catalog/professionals/' : '/catalog/professionals/?$query';

  final data = await client.get(ruta);
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  return PaginaProfesionales(
    results: (mapa['results'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ProfesionalTarjeta.fromJson)
        .toList(),
    hayMas: mapa['next'] != null,
  );
}
