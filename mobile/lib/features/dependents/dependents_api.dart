/// US-07 — Pacientes dependientes: los familiares a cargo del titular.
///
/// Un dependiente es una ficha de paciente **sin cuenta de acceso**: no tiene
/// correo ni contraseña y no inicia sesión. Quien lo administra es el titular
/// desde su teléfono, que es esta pantalla.
///
/// `PatientOption` es el modelo del selector de *"¿para quién es esta ficha?"*,
/// que también usa US-08 y volverá a usar la reserva del Sprint 2. Está acá y
/// no dentro de una pantalla a propósito.
library;

import 'package:mobile/core/api/client.dart';

/// Los parentescos que acepta el backend, con su etiqueta.
///
/// La lista está duplicada del modelo de Django, y es deliberado: el
/// desplegable tiene que poder dibujarse sin una llamada de red, y son ocho
/// valores que no cambian. Si algún día se vuelven configurables, esto pasa a
/// venir del backend.
const Map<String, String> parentescos = {
  'child': 'Hijo/a',
  'spouse': 'Cónyuge',
  'parent': 'Padre/Madre',
  'sibling': 'Hermano/a',
  'grandparent': 'Abuelo/a',
  'grandchild': 'Nieto/a',
  'ward': 'Bajo tutela',
  'other': 'Otro',
};

class Dependiente {
  const Dependiente({
    required this.id,
    required this.firstName,
    required this.lastName,
    required this.fullName,
    required this.relationship,
    required this.relationshipLabel,
    this.documentType,
    this.documentNumber,
    this.birthDate,
    this.sex,
    this.age,
  });

  final String id;
  final String firstName;
  final String lastName;
  final String fullName;
  final String relationship;
  final String relationshipLabel;
  final String? documentType;
  final String? documentNumber;
  final String? birthDate;
  final String? sex;
  final int? age;

  factory Dependiente.fromJson(Map<String, dynamic> json) => Dependiente(
        id: json['id'] as String? ?? '',
        firstName: json['first_name'] as String? ?? '',
        lastName: json['last_name'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        relationship: json['relationship'] as String? ?? '',
        relationshipLabel: json['relationship_label'] as String? ?? '',
        documentType: json['document_type'] as String?,
        documentNumber: json['document_number'] as String?,
        birthDate: json['birth_date'] as String?,
        sex: json['sex'] as String?,
        age: json['age'] as int?,
      );
}

/// Una opción del selector de *"¿para quién es esta ficha?"*. Punto (h).
class PatientOption {
  const PatientOption({
    required this.id,
    required this.fullName,
    required this.relationshipLabel,
    required this.isSelf,
    this.birthDate,
  });

  final String id;
  final String fullName;

  /// `'Yo'` para el titular; el parentesco para los demás.
  final String relationshipLabel;
  final bool isSelf;
  final String? birthDate;

  factory PatientOption.fromJson(Map<String, dynamic> json) => PatientOption(
        id: json['id'] as String? ?? '',
        fullName: json['full_name'] as String? ?? '',
        relationshipLabel: json['relationship_label'] as String? ?? '',
        isSelf: json['is_self'] as bool? ?? false,
        birthDate: json['birth_date'] as String?,
      );
}

/// Lo que se manda al dar de alta o editar un dependiente.
class DependienteNuevo {
  const DependienteNuevo({
    required this.firstName,
    required this.lastName,
    required this.relationship,
    this.documentType,
    this.documentNumber,
    this.birthDate,
    this.sex,
    this.phone,
  });

  final String firstName;
  final String lastName;
  final String relationship;
  final String? documentType;
  final String? documentNumber;
  final String? birthDate;
  final String? sex;
  final String? phone;

  Map<String, dynamic> toJson({bool confirmLink = false}) => {
        'first_name': firstName,
        'last_name': lastName,
        'relationship': relationship,
        if (documentNumber != null && documentNumber!.trim().isNotEmpty) ...{
          'document_type': documentType ?? 'CI',
          'document_number': documentNumber!.trim(),
        },
        if (birthDate != null && birthDate!.isNotEmpty) 'birth_date': birthDate,
        if (sex != null && sex!.isNotEmpty) 'sex': sex,
        if (phone != null && phone!.trim().isNotEmpty) 'phone': phone!.trim(),
        if (confirmLink) 'confirm_link': true,
      };
}

Future<List<Dependiente>> listarDependientes(ApiClient client) async {
  final data = await client.get('/patients/dependents/');
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  return (mapa['results'] as List? ?? const [])
      .whereType<Map<String, dynamic>>()
      .map(Dependiente.fromJson)
      .toList();
}

/// Da de alta al dependiente.
///
/// Con [confirmLink] en `true` confirma vincular una ficha que ya existe en el
/// centro médico en lugar de crear un duplicado (punto c). El backend sólo la
/// vincula si el nombre, el apellido y la fecha de nacimiento coinciden con lo
/// que la ficha ya tenía.
Future<Dependiente> crearDependiente(
  ApiClient client,
  DependienteNuevo datos, {
  bool confirmLink = false,
}) async {
  final data = await client.post(
    '/patients/dependents/',
    body: datos.toJson(confirmLink: confirmLink),
  );
  return Dependiente.fromJson(data as Map<String, dynamic>);
}

Future<Dependiente> editarDependiente(
  ApiClient client,
  String id,
  Map<String, dynamic> cambios,
) async {
  final data = await client.patch('/patients/dependents/$id/', body: cambios);
  return Dependiente.fromJson(data as Map<String, dynamic>);
}

/// Corta el vínculo. **No borra la ficha**: la historia clínica es longitudinal
/// y sobrevive al vínculo (punto e).
Future<void> desvincularDependiente(ApiClient client, String id) =>
    client.delete('/patients/dependents/$id/');

/// Punto (f): le crea la cuenta de acceso al que ya es mayor de edad.
Future<void> promoverATitular(
  ApiClient client,
  String id, {
  required String email,
  required String password,
}) =>
    client.post(
      '/patients/dependents/$id/promote/',
      body: {
        'email': email,
        'password': password,
        'password_confirmation': password,
      },
    );

/// El titular y sus dependientes, para el selector de "¿para quién es?".
Future<List<PatientOption>> listarOpcionesDePaciente(ApiClient client) async {
  final data = await client.get('/patients/dependents/patient-options/');
  return (data as List? ?? const [])
      .whereType<Map<String, dynamic>>()
      .map(PatientOption.fromJson)
      .toList();
}
