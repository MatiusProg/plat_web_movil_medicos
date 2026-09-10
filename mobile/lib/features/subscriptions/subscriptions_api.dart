/// US-44 — Suscripciones vigentes de cada organización y su historial.
library;

import '../../core/api/client.dart';

class Subscription {
  const Subscription({
    required this.id,
    required this.organization,
    required this.organizationName,
    required this.organizationSlug,
    required this.plan,
    required this.planCode,
    required this.planName,
    required this.startsAt,
    required this.endsAt,
    required this.status,
    required this.changeReason,
    required this.assignedByEmail,
    required this.createdAt,
  });

  final String id;
  final String organization;
  final String organizationName;
  final String organizationSlug;
  final String plan;
  final String planCode;
  final String planName;
  final String startsAt;

  /// `null` = vigente, sin fecha de fin todavía.
  final String? endsAt;

  /// `active` | `cancelled` | `expired`.
  final String status;
  final String changeReason;
  final String? assignedByEmail;
  final String createdAt;

  factory Subscription.fromJson(Map<String, dynamic> json) => Subscription(
        id: json['id'] as String? ?? '',
        organization: json['organization'] as String? ?? '',
        organizationName: json['organization_name'] as String? ?? '',
        organizationSlug: json['organization_slug'] as String? ?? '',
        plan: json['plan'] as String? ?? '',
        planCode: json['plan_code'] as String? ?? '',
        planName: json['plan_name'] as String? ?? '',
        startsAt: json['starts_at'] as String? ?? '',
        endsAt: json['ends_at'] as String?,
        status: json['status'] as String? ?? 'active',
        changeReason: json['change_reason'] as String? ?? '',
        assignedByEmail: json['assigned_by_email'] as String?,
        createdAt: json['created_at'] as String? ?? '',
      );
}

Future<List<Subscription>> listSubscriptions(
  ApiClient client, {
  bool current = true,
}) async {
  final data = await client.get('/platform/subscriptions/?current=$current');
  final mapa = data as Map<String, dynamic>;
  return (mapa['results'] as List? ?? const [])
      .map((e) => Subscription.fromJson(e as Map<String, dynamic>))
      .toList();
}

Future<Subscription> assignPlan(
  ApiClient client, {
  required String organizationId,
  required String planId,
  required String startsAt,
  String changeReason = '',
}) async {
  final data = await client.post(
    '/platform/subscriptions/assign/',
    body: {
      'organization_id': organizationId,
      'plan_id': planId,
      'starts_at': startsAt,
      'change_reason': changeReason,
    },
  );
  return Subscription.fromJson(data as Map<String, dynamic>);
}

Future<List<Subscription>> organizationSubscriptionHistory(
  ApiClient client,
  String organizationId,
) async {
  final data =
      await client.get('/platform/organizations/$organizationId/subscriptions/');
  final mapa = data as Map<String, dynamic>;
  return (mapa['results'] as List? ?? const [])
      .map((e) => Subscription.fromJson(e as Map<String, dynamic>))
      .toList();
}
