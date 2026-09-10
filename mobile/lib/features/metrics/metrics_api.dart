/// US-45 — Datos del panel del superadministrador de plataforma.
///
/// Sólo el resumen (`fetchDashboard`): el backend también expone
/// `/platform/alerts/` con el detalle de cada alerta, pero esta primera
/// vuelta de mobile se queda en los conteos. Ver
/// `backend/tenancy/views/metrics.py`.
library;

import '../../core/api/client.dart';

class OrganizationCounts {
  const OrganizationCounts({
    required this.total,
    required this.active,
    required this.suspended,
    required this.inactive,
  });

  final int total;
  final int active;
  final int suspended;
  final int inactive;

  factory OrganizationCounts.fromJson(Map<String, dynamic> json) =>
      OrganizationCounts(
        total: json['total'] as int? ?? 0,
        active: json['active'] as int? ?? 0,
        suspended: json['suspended'] as int? ?? 0,
        inactive: json['inactive'] as int? ?? 0,
      );
}

class PlanCount {
  const PlanCount({
    required this.planCode,
    required this.planName,
    required this.count,
  });

  final String planCode;
  final String planName;
  final int count;

  factory PlanCount.fromJson(Map<String, dynamic> json) => PlanCount(
        planCode: json['plan_code'] as String? ?? '',
        planName: json['plan_name'] as String? ?? '',
        count: json['count'] as int? ?? 0,
      );
}

class AlertCounts {
  const AlertCounts({required this.pending, required this.criticalPending});

  final int pending;
  final int criticalPending;

  factory AlertCounts.fromJson(Map<String, dynamic> json) => AlertCounts(
        pending: json['pending'] as int? ?? 0,
        criticalPending: json['critical_pending'] as int? ?? 0,
      );
}

class PlatformDashboard {
  const PlatformDashboard({
    required this.organizations,
    required this.byPlan,
    required this.alerts,
  });

  final OrganizationCounts organizations;
  final List<PlanCount> byPlan;
  final AlertCounts alerts;

  factory PlatformDashboard.fromJson(Map<String, dynamic> json) =>
      PlatformDashboard(
        organizations: OrganizationCounts.fromJson(
          json['organizations'] as Map<String, dynamic>,
        ),
        byPlan: (json['by_plan'] as List? ?? const [])
            .map((e) => PlanCount.fromJson(e as Map<String, dynamic>))
            .toList(),
        alerts: AlertCounts.fromJson(json['alerts'] as Map<String, dynamic>),
      );
}

Future<PlatformDashboard> fetchDashboard(ApiClient client) async {
  final data = await client.get('/platform/dashboard/');
  return PlatformDashboard.fromJson(data as Map<String, dynamic>);
}
