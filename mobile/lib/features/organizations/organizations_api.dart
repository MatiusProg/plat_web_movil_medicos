/// US-43 — Alta y listado de organizaciones (centros médicos clientes).
///
/// Sin scroll infinito, mismo criterio que `plans_api.dart`: sólo la primera
/// página.
library;

import '../../core/api/client.dart';

class CurrentPlan {
  const CurrentPlan({
    required this.code,
    required this.name,
    required this.startsAt,
  });

  final String code;
  final String name;
  final String startsAt;

  factory CurrentPlan.fromJson(Map<String, dynamic> json) => CurrentPlan(
        code: json['code'] as String? ?? '',
        name: json['name'] as String? ?? '',
        startsAt: json['starts_at'] as String? ?? '',
      );
}

class Organization {
  const Organization({
    required this.id,
    required this.slug,
    required this.name,
    required this.legalName,
    required this.taxId,
    required this.contactEmail,
    required this.city,
    required this.status,
    required this.currentPlan,
  });

  final String id;
  final String slug;
  final String name;
  final String legalName;
  final String taxId;
  final String contactEmail;
  final String city;

  /// `active` | `suspended` | `inactive` — se compara contra el código, no
  /// contra ningún texto traducido, mismo criterio que `ApiError.code`.
  final String status;
  final CurrentPlan? currentPlan;

  factory Organization.fromJson(Map<String, dynamic> json) => Organization(
        id: json['id'] as String? ?? '',
        slug: json['slug'] as String? ?? '',
        name: json['name'] as String? ?? '',
        legalName: json['legal_name'] as String? ?? '',
        taxId: json['tax_id'] as String? ?? '',
        contactEmail: json['contact_email'] as String? ?? '',
        city: json['city'] as String? ?? '',
        status: json['status'] as String? ?? 'active',
        currentPlan: json['current_plan'] == null
            ? null
            : CurrentPlan.fromJson(json['current_plan'] as Map<String, dynamic>),
      );
}

/// El administrador que acaba de crearse. `temporaryPassword` sólo llega acá
/// -esta única respuesta-, nunca en una lectura posterior.
class NewOrganizationAdmin {
  const NewOrganizationAdmin({
    required this.id,
    required this.email,
    required this.role,
    required this.temporaryPassword,
  });

  final String id;
  final String email;
  final String role;
  final String temporaryPassword;

  factory NewOrganizationAdmin.fromJson(Map<String, dynamic> json) =>
      NewOrganizationAdmin(
        id: json['id'] as String? ?? '',
        email: json['email'] as String? ?? '',
        role: json['role'] as String? ?? '',
        temporaryPassword: json['temporary_password'] as String? ?? '',
      );
}

class OrganizationCreated {
  const OrganizationCreated({required this.organization, required this.admin});

  final Organization organization;
  final NewOrganizationAdmin admin;

  factory OrganizationCreated.fromJson(Map<String, dynamic> json) =>
      OrganizationCreated(
        organization: Organization.fromJson(json),
        admin: NewOrganizationAdmin.fromJson(
          json['admin'] as Map<String, dynamic>,
        ),
      );
}

Future<List<Organization>> listOrganizations(ApiClient client) async {
  final data = await client.get('/platform/organizations/');
  final mapa = data as Map<String, dynamic>;
  return (mapa['results'] as List? ?? const [])
      .map((e) => Organization.fromJson(e as Map<String, dynamic>))
      .toList();
}

Future<OrganizationCreated> registerOrganization(
  ApiClient client, {
  required String slug,
  required String name,
  required String legalName,
  required String taxId,
  required String contactEmail,
  required String contactPhone,
  required String address,
  required String city,
  required String planCode,
  required String adminEmail,
  required String adminFirstName,
  required String adminLastName,
  required String adminDocumentNumber,
  required String adminPhone,
}) async {
  final data = await client.post(
    '/platform/organizations/',
    body: {
      'slug': slug,
      'name': name,
      'legal_name': legalName,
      'tax_id': taxId,
      'contact_email': contactEmail,
      'contact_phone': contactPhone,
      'address': address,
      'city': city,
      'plan_code': planCode,
      'admin': {
        'email': adminEmail,
        'first_name': adminFirstName,
        'last_name': adminLastName,
        'document_number': adminDocumentNumber,
        'phone': adminPhone,
      },
    },
  );
  return OrganizationCreated.fromJson(data as Map<String, dynamic>);
}
