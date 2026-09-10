/// US-44 — Planes de suscripción, vistos y editados por el superadministrador.
///
/// Sin scroll infinito: se pide sólo la primera página (25, el default del
/// backend) — es un catálogo de escala administrativa, no de cientos de
/// filas como la búsqueda de profesionales.
library;

import '../../core/api/client.dart';

class Plan {
  const Plan({
    required this.id,
    required this.code,
    required this.name,
    required this.description,
    required this.monthlyPrice,
    required this.currency,
    required this.maxBranches,
    required this.maxUsers,
    required this.maxPractitioners,
    required this.maxAppointmentsMonth,
    required this.maxAiQueriesMonth,
    required this.storageMb,
    required this.isActive,
  });

  final String id;
  final String code;
  final String name;
  final String description;

  /// String, no `double`: es lo que manda el backend (decimal serializado) y
  /// no hace falta operar con este número en el cliente, sólo mostrarlo.
  final String monthlyPrice;
  final String currency;

  // `null` = ilimitado, en los seis.
  final int? maxBranches;
  final int? maxUsers;
  final int? maxPractitioners;
  final int? maxAppointmentsMonth;
  final int? maxAiQueriesMonth;
  final int? storageMb;

  final bool isActive;

  factory Plan.fromJson(Map<String, dynamic> json) => Plan(
        id: json['id'] as String? ?? '',
        code: json['code'] as String? ?? '',
        name: json['name'] as String? ?? '',
        description: json['description'] as String? ?? '',
        monthlyPrice: json['monthly_price'] as String? ?? '0',
        currency: json['currency'] as String? ?? '',
        maxBranches: json['max_branches'] as int?,
        maxUsers: json['max_users'] as int?,
        maxPractitioners: json['max_practitioners'] as int?,
        maxAppointmentsMonth: json['max_appointments_month'] as int?,
        maxAiQueriesMonth: json['max_ai_queries_month'] as int?,
        storageMb: json['storage_mb'] as int?,
        isActive: json['is_active'] as bool? ?? false,
      );
}

Future<List<Plan>> listPlans(ApiClient client, {bool? isActive}) async {
  final query = isActive == null ? '' : '?is_active=$isActive';
  final data = await client.get('/platform/plans/$query');
  final mapa = data as Map<String, dynamic>;
  return (mapa['results'] as List? ?? const [])
      .map((e) => Plan.fromJson(e as Map<String, dynamic>))
      .toList();
}

/// Los seis límites en `int?`: `null` viaja como ausente en el body -no como
/// `"null"` ni como `0`, que significaría "cero permitidos"-.
Map<String, dynamic> _cuerpoDelPlan({
  required String name,
  required String description,
  required String monthlyPrice,
  required String currency,
  required int? maxBranches,
  required int? maxUsers,
  required int? maxPractitioners,
  required int? maxAppointmentsMonth,
  required int? maxAiQueriesMonth,
  required int? storageMb,
  required bool isActive,
}) => {
      'name': name,
      'description': description,
      'monthly_price': monthlyPrice,
      'currency': currency,
      'max_branches': maxBranches,
      'max_users': maxUsers,
      'max_practitioners': maxPractitioners,
      'max_appointments_month': maxAppointmentsMonth,
      'max_ai_queries_month': maxAiQueriesMonth,
      'storage_mb': storageMb,
      'is_active': isActive,
    };

Future<Plan> createPlan(
  ApiClient client, {
  required String code,
  required String name,
  required String description,
  required String monthlyPrice,
  required String currency,
  required int? maxBranches,
  required int? maxUsers,
  required int? maxPractitioners,
  required int? maxAppointmentsMonth,
  required int? maxAiQueriesMonth,
  required int? storageMb,
  required bool isActive,
}) async {
  final data = await client.post(
    '/platform/plans/',
    body: {
      'code': code,
      ..._cuerpoDelPlan(
        name: name,
        description: description,
        monthlyPrice: monthlyPrice,
        currency: currency,
        maxBranches: maxBranches,
        maxUsers: maxUsers,
        maxPractitioners: maxPractitioners,
        maxAppointmentsMonth: maxAppointmentsMonth,
        maxAiQueriesMonth: maxAiQueriesMonth,
        storageMb: storageMb,
        isActive: isActive,
      ),
    },
  );
  return Plan.fromJson(data as Map<String, dynamic>);
}

Future<Plan> updatePlan(
  ApiClient client,
  String id, {
  required String name,
  required String description,
  required String monthlyPrice,
  required String currency,
  required int? maxBranches,
  required int? maxUsers,
  required int? maxPractitioners,
  required int? maxAppointmentsMonth,
  required int? maxAiQueriesMonth,
  required int? storageMb,
  required bool isActive,
}) async {
  final data = await client.patch(
    '/platform/plans/$id/',
    body: _cuerpoDelPlan(
      name: name,
      description: description,
      monthlyPrice: monthlyPrice,
      currency: currency,
      maxBranches: maxBranches,
      maxUsers: maxUsers,
      maxPractitioners: maxPractitioners,
      maxAppointmentsMonth: maxAppointmentsMonth,
      maxAiQueriesMonth: maxAiQueriesMonth,
      storageMb: storageMb,
      isActive: isActive,
    ),
  );
  return Plan.fromJson(data as Map<String, dynamic>);
}
