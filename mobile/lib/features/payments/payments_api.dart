/// US-18 — Pago en línea de la ficha.
///
/// El móvil **pide** el pago y abre la página de cobro (Stripe Checkout, o la
/// simulada cuando el servidor no tiene claves de Stripe); **no** lo da por
/// hecho. La ficha la confirma el webhook firmado de Stripe del lado del
/// servidor, y la aplicación se entera volviendo a leer la ficha. Si la
/// pantalla decidiera "pagué" al volver del navegador, una aplicación cerrada a
/// destiempo dejaría fichas cobradas sin confirmar o confirmadas sin cobrar.
library;

import 'package:mobile/core/api/client.dart';

class CheckoutSession {
  const CheckoutSession({
    required this.paymentId,
    required this.provider,
    required this.checkoutUrl,
    required this.amount,
    required this.currency,
    required this.status,
  });

  final String paymentId;

  /// `stripe` | `simulated`.
  final String provider;
  final String checkoutUrl;
  final String amount;
  final String currency;
  final String status;

  bool get isSimulated => provider == 'simulated';

  factory CheckoutSession.fromJson(Map<String, dynamic> json) =>
      CheckoutSession(
        paymentId: '${json['payment_id'] ?? ''}',
        provider: json['provider'] as String? ?? '',
        checkoutUrl: json['checkout_url'] as String? ?? '',
        amount: '${json['amount'] ?? ''}',
        currency: json['currency'] as String? ?? 'BOB',
        status: json['status'] as String? ?? '',
      );
}

/// Crea (o reutiliza, si el backend así lo decide) la sesión de cobro.
Future<CheckoutSession> iniciarPago(
  ApiClient client,
  String appointmentId,
) async {
  final data = await client.post(
    '/payments/appointments/$appointmentId/checkout/',
  );
  return CheckoutSession.fromJson(
    data is Map<String, dynamic> ? data : const <String, dynamic>{},
  );
}
