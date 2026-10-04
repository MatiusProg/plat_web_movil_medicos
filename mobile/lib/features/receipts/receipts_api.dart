/// US-19 — Comprobante digital de la ficha.
///
/// `code` es el texto firmado por el servidor que va dentro del QR. El móvil
/// no lo genera ni lo valida: lo muestra. Quien lo valida es recepción, en el
/// check-in de US-22, y por eso un comprobante copiado o inventado no sirve.
library;

import 'package:mobile/core/api/client.dart';

class Receipt {
  const Receipt({
    required this.appointmentId,
    required this.code,
    required this.raw,
    this.issuedAt,
    this.organizationName = '',
    this.patientName = '',
    this.documentNumber = '',
    this.practitionerName = '',
    this.branchName = '',
    this.branchAddress = '',
    this.startsAt,
    this.endsAt,
    this.status = '',
  });

  final String appointmentId;
  final String code;
  final DateTime? issuedAt;
  final String organizationName;
  final String patientName;
  final String documentNumber;
  final String practitionerName;
  final String branchName;
  final String branchAddress;
  final DateTime? startsAt;
  final DateTime? endsAt;
  final String status;

  /// El JSON tal como vino: es lo que se guarda para mostrarlo sin conexión.
  final Map<String, dynamic> raw;

  static DateTime? _fecha(Object? valor) =>
      valor is String ? DateTime.tryParse(valor)?.toLocal() : null;

  factory Receipt.fromJson(Map<String, dynamic> json) => Receipt(
    appointmentId: '${json['appointment_id'] ?? ''}',
    code: json['code'] as String? ?? '',
    issuedAt: _fecha(json['issued_at']),
    organizationName: json['organization_name'] as String? ?? '',
    patientName: json['patient_name'] as String? ?? '',
    documentNumber: json['document_number'] as String? ?? '',
    practitionerName: json['practitioner_name'] as String? ?? '',
    branchName: json['branch_name'] as String? ?? '',
    branchAddress: json['branch_address'] as String? ?? '',
    startsAt: _fecha(json['starts_at']),
    endsAt: _fecha(json['ends_at']),
    status: json['status'] as String? ?? '',
    raw: json,
  );
}

Future<Receipt> pedirComprobante(ApiClient client, String appointmentId) async {
  final data = await client.get(
    '/appointments/appointments/$appointmentId/receipt/',
  );
  return Receipt.fromJson(
    data is Map<String, dynamic> ? data : const <String, dynamic>{},
  );
}
