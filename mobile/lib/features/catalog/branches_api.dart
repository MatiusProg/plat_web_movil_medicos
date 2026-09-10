/// US-11 — Sucursales del centro médico.
///
/// El listado **no pagina**: son las sedes de una organización, un puñado, y
/// el backend las devuelve como lista pelada y no como página. Es el mismo
/// criterio que `catalog/specialties/`.
///
/// Lo consumen dos lugares: la sección Sucursales del menú, y el selector de
/// sede del formulario de agendas (US-13), que necesita saber a qué sedes se
/// puede asignar una regla.
library;

import '../../core/api/client.dart';

class Sucursal {
  const Sucursal({
    required this.id,
    required this.name,
    required this.address,
    required this.phone,
    required this.timezone,
    required this.isActive,
  });

  final String id;
  final String name;
  final String address;
  final String phone;

  /// La zona horaria de la sede, no la del teléfono: es la que usa el backend
  /// para expandir los espacios de la agenda.
  final String timezone;

  final bool isActive;

  factory Sucursal.fromJson(Map<String, dynamic> json) => Sucursal(
        id: json['id'] as String? ?? '',
        name: json['name'] as String? ?? '',
        address: json['address'] as String? ?? '',
        phone: json['phone'] as String? ?? '',
        timezone: json['timezone'] as String? ?? '',
        isActive: json['is_active'] as bool? ?? false,
      );
}

Future<List<Sucursal>> listarSucursales(ApiClient client) async {
  final data = await client.get('/catalog/branches/');
  return (data as List? ?? const [])
      .map((e) => Sucursal.fromJson(e as Map<String, dynamic>))
      .toList();
}

Map<String, dynamic> _cuerpo({
  required String name,
  required String address,
  required String phone,
  required String timezone,
}) => {
      'name': name,
      'address': address,
      'phone': phone,
      'timezone': timezone,
    };

Future<Sucursal> crearSucursal(
  ApiClient client, {
  required String name,
  required String address,
  required String phone,
  required String timezone,
}) async {
  final data = await client.post(
    '/catalog/branches/',
    body: _cuerpo(
      name: name,
      address: address,
      phone: phone,
      timezone: timezone,
    ),
  );
  return Sucursal.fromJson(data as Map<String, dynamic>);
}

Future<Sucursal> editarSucursal(
  ApiClient client,
  String id, {
  required String name,
  required String address,
  required String phone,
  required String timezone,
}) async {
  final data = await client.patch(
    '/catalog/branches/$id/',
    body: _cuerpo(
      name: name,
      address: address,
      phone: phone,
      timezone: timezone,
    ),
  );
  return Sucursal.fromJson(data as Map<String, dynamic>);
}

/// Baja lógica, con endpoint propio.
///
/// No es un `DELETE` como en agendas: acá el backend expone
/// `branches/<id>/deactivate/`, porque una sede con agendas o fichas colgando
/// no se puede borrar y la operación real es marcarla inactiva.
Future<void> desactivarSucursal(ApiClient client, String id) =>
    client.post('/catalog/branches/$id/deactivate/');
