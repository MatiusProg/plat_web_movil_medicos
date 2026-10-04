/// US-19 — Los comprobantes guardados en el teléfono.
///
/// El paciente llega al centro médico y puede no tener señal: el comprobante
/// tiene que poder mostrarse sin red. Se guarda el JSON entero que devolvió el
/// servidor, con el código firmado adentro, y se vuelve a pedir cada vez que
/// hay conexión para tenerlo al día.
///
/// En `flutter_secure_storage`, como los tokens: el comprobante es un código
/// que da acceso a la consulta y no tiene por qué quedar en texto plano.
library;

import 'dart:convert';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'receipts_api.dart';

class ReceiptStore {
  ReceiptStore({FlutterSecureStorage? storage})
    : _storage = storage ?? const FlutterSecureStorage();

  final FlutterSecureStorage _storage;

  static const String _prefijo = 'receipt.';

  Future<void> save(Receipt receipt) async {
    if (receipt.appointmentId.isEmpty) return;
    await _storage.write(
      key: '$_prefijo${receipt.appointmentId}',
      value: jsonEncode(receipt.raw),
    );
  }

  Future<Receipt?> read(String appointmentId) async {
    final valor = await _storage.read(key: '$_prefijo$appointmentId');
    return _decode(valor);
  }

  Future<void> remove(String appointmentId) =>
      _storage.delete(key: '$_prefijo$appointmentId');

  /// Todos los guardados, la próxima ficha primero.
  Future<List<Receipt>> all() async {
    final todo = await _storage.readAll();
    final comprobantes = <Receipt>[
      for (final entrada in todo.entries)
        if (entrada.key.startsWith(_prefijo)) ?_decode(entrada.value),
    ];
    comprobantes.sort((a, b) {
      final ia = a.startsAt ?? DateTime.fromMillisecondsSinceEpoch(0);
      final ib = b.startsAt ?? DateTime.fromMillisecondsSinceEpoch(0);
      return ia.compareTo(ib);
    });
    return comprobantes;
  }

  Receipt? _decode(String? valor) {
    if (valor == null || valor.isEmpty) return null;
    try {
      final json = jsonDecode(valor);
      return json is Map<String, dynamic> ? Receipt.fromJson(json) : null;
    } catch (_) {
      return null;
    }
  }
}
