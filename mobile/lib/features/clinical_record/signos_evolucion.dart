/// US-53 — «Mis signos vitales»: la última medición y cómo vienen la presión y
/// el peso a lo largo de las atenciones firmadas.
///
/// Igual que en la web: se grafica lo que se firmó; si el médico lo corrigió
/// con una enmienda, el punto va hueco y la corrección se lee en la atención.
/// La franja es la de referencia de un adulto; el borde de arriba de la
/// presión es el mismo umbral que marca «Alta».
library;

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:mobile/core/theme/theme.dart';

import 'clinical_record_api.dart';

/// Una línea del gráfico: de dónde sale el valor y su franja normal.
class LineaSigno {
  const LineaSigno(this.etiqueta, this.valor, {this.franja});
  final String etiqueta;
  final double? Function(SignosVitales s) valor;
  final (double, double)? franja;
}

class SerieSigno {
  const SerieSigno(this.etiqueta, this.unidad, this.lineas);
  final String etiqueta;
  final String unidad;
  final List<LineaSigno> lineas;
}

final presion = SerieSigno('Presión arterial', 'mmHg', [
  LineaSigno('Sistólica', (s) => s.sistolica?.toDouble(), franja: (90, 140)),
  LineaSigno('Diastólica', (s) => s.diastolica?.toDouble(), franja: (60, 90)),
]);
final peso = SerieSigno('Peso', 'kg', [LineaSigno('Peso', (s) => s.peso)]);

class PuntoSigno {
  const PuntoSigno({
    required this.fecha,
    required this.valores,
    required this.enmendado,
  });
  final DateTime? fecha;

  /// Uno por línea de la serie; `null` si esa vez no se tomó.
  final List<double?> valores;

  /// El médico corrigió los signos de esa atención con una enmienda.
  final bool enmendado;
}

/// Las atenciones con algún valor de la serie, de la más vieja a la más nueva.
List<PuntoSigno> puntosDe(SerieSigno serie, List<Atencion> atenciones) {
  final con = [
    for (final a in atenciones)
      if (a.signos != null &&
          serie.lineas.any((l) => l.valor(a.signos!) != null))
        a,
  ]..sort((a, b) => (a.startsAt ?? DateTime(0)).compareTo(b.startsAt ?? DateTime(0)));
  return [
    for (final a in con)
      PuntoSigno(
        fecha: a.startsAt,
        valores: [for (final l in serie.lineas) l.valor(a.signos!)],
        enmendado: a.enmiendas.any((e) => e.section == 'vital_signs'),
      ),
  ];
}

/// La atención más nueva que tiene signos, o `null`.
Atencion? ultimaMedicion(List<Atencion> atenciones) {
  Atencion? ultima;
  for (final a in atenciones) {
    if (a.signos == null) continue;
    if (ultima == null ||
        (a.startsAt ?? DateTime(0)).isAfter(ultima.startsAt ?? DateTime(0))) {
      ultima = a;
    }
  }
  return ultima;
}

const _meses = [
  'ene', 'feb', 'mar', 'abr', 'may', 'jun',
  'jul', 'ago', 'sept', 'oct', 'nov', 'dic',
];
String _corta(DateTime? d) {
  if (d == null) return '';
  final l = d.toLocal();
  return '${l.day} ${_meses[l.month - 1]}';
}

String _num(double v) => v == v.roundToDouble()
    ? v.toInt().toString()
    : v.toStringAsFixed(1).replaceAll('.', ',');

/// La sección completa. Sin signos tomados, no se muestra nada.
class MisSignosVitales extends StatelessWidget {
  const MisSignosVitales({super.key, required this.atenciones});

  final List<Atencion> atenciones;

  @override
  Widget build(BuildContext context) {
    final ultima = ultimaMedicion(atenciones);
    if (ultima == null) return const SizedBox.shrink();
    final theme = Theme.of(context);
    final suave = theme.colorScheme.onSurfaceVariant;
    final l = ultima.startsAt?.toLocal();
    return Card(
      margin: const EdgeInsets.only(top: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Mis signos vitales', style: theme.textTheme.titleMedium),
            const SizedBox(height: 2),
            Text(
              'Última medición: '
              '${l == null ? '—' : '${l.day}/${l.month}/${l.year}'}, '
              '${ultima.practitionerName}',
              style: theme.textTheme.bodySmall?.copyWith(color: suave),
            ),
            for (final fila in ultima.signos!.filas)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        fila.etiqueta,
                        style: theme.textTheme.bodyMedium?.copyWith(color: suave),
                      ),
                    ),
                    Text(fila.valor, style: theme.textTheme.bodyMedium),
                    if (fila.alerta != null) ...[
                      const SizedBox(width: 6),
                      Text(
                        fila.alerta!,
                        style: theme.textTheme.labelSmall?.copyWith(
                          color: theme.colorScheme.error,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            if (ultima.enmiendas.any((e) => e.section == 'vital_signs'))
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  'Tu médico agregó una corrección: la ves en esa atención, más abajo.',
                  style: theme.textTheme.bodySmall?.copyWith(color: suave),
                ),
              ),
            for (final serie in [presion, peso])
              if (puntosDe(serie, atenciones).isNotEmpty) ...[
                const SizedBox(height: 16),
                Text(
                  '${serie.etiqueta} (${serie.unidad})',
                  style: theme.textTheme.labelLarge,
                ),
                const SizedBox(height: 8),
                GraficoSigno(serie: serie, puntos: puntosDe(serie, atenciones)),
              ],
          ],
        ),
      ),
    );
  }
}

/// Un gráfico de línea con la franja normal sombreada.
class GraficoSigno extends StatelessWidget {
  const GraficoSigno({super.key, required this.serie, required this.puntos});

  final SerieSigno serie;
  final List<PuntoSigno> puntos;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final oscuro = theme.brightness == Brightness.dark;
    final colores = [
      oscuro ? Marca.primaryLight : Marca.primary,
      oscuro ? const Color(0xFFCBD5E1) : Marca.ink500,
    ];
    final ultimo = puntos.last;
    final resumen = [
      for (final (i, l) in serie.lineas.indexed)
        if (ultimo.valores[i] != null)
          '${l.etiqueta} ${_num(ultimo.valores[i]!)}',
    ].join(', ');
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Semantics(
          label: '${serie.etiqueta}: ${puntos.length} '
              '${puntos.length == 1 ? 'medición' : 'mediciones'}. '
              'La última, $resumen ${serie.unidad}.',
          child: ExcludeSemantics(
            child: SizedBox(
              height: 180,
              width: double.infinity,
              child: CustomPaint(
                painter: _Pintor(
                  serie: serie,
                  puntos: puntos,
                  colores: colores,
                  fondo: theme.colorScheme.surface,
                  texto: theme.colorScheme.onSurfaceVariant,
                  guia: theme.colorScheme.outlineVariant,
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Wrap(
          spacing: 12,
          runSpacing: 4,
          children: [
            for (final (i, l) in serie.lineas.indexed)
              Text(
                '— ${serie.lineas.length > 1 ? l.etiqueta : 'Medido'}'
                '${l.franja == null ? '' : ' · normal ${_num(l.franja!.$1)}–${_num(l.franja!.$2)}'}',
                style: theme.textTheme.bodySmall?.copyWith(color: colores[i]),
              ),
            if (puntos.any((p) => p.enmendado))
              Text(
                '○ con corrección del médico',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
            if (puntos.length == 1)
              Text(
                'Con una sola medición todavía no hay evolución.',
                style: theme.textTheme.bodySmall
                    ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
              ),
          ],
        ),
      ],
    );
  }
}

class _Pintor extends CustomPainter {
  _Pintor({
    required this.serie,
    required this.puntos,
    required this.colores,
    required this.fondo,
    required this.texto,
    required this.guia,
  });

  final SerieSigno serie;
  final List<PuntoSigno> puntos;
  final List<Color> colores;
  final Color fondo;
  final Color texto;
  final Color guia;

  static const izq = 36.0, der = 10.0, arriba = 8.0, abajo = 22.0;

  void _etiqueta(Canvas c, String s, Offset o, {TextAlign al = TextAlign.left}) {
    final tp = TextPainter(
      text: TextSpan(text: s, style: TextStyle(color: texto, fontSize: 10)),
      textDirection: TextDirection.ltr,
    )..layout();
    final dx = switch (al) {
      TextAlign.right => o.dx - tp.width,
      TextAlign.center => o.dx - tp.width / 2,
      _ => o.dx,
    };
    tp.paint(c, Offset(dx, o.dy - tp.height / 2));
  }

  @override
  void paint(Canvas canvas, Size size) {
    final valores = [for (final p in puntos) ...p.valores.whereType<double>()];
    final bordes = [
      for (final l in serie.lineas)
        if (l.franja != null) ...[l.franja!.$1, l.franja!.$2],
    ];
    var min = [...valores, ...bordes].reduce(math.min);
    var max = [...valores, ...bordes].reduce(math.max);
    final margen = (max - min == 0 ? (max.abs() == 0 ? 1 : max.abs()) : max - min) * 0.08;
    min -= margen;
    max += margen;
    final alto = size.height - arriba - abajo;
    double y(double v) => arriba + (max - v) / (max - min) * alto;
    double x(int i) => puntos.length == 1
        ? (izq + size.width - der) / 2
        : izq + i * (size.width - izq - der) / (puntos.length - 1);

    for (final (i, l) in serie.lineas.indexed) {
      final f = l.franja;
      if (f == null) continue;
      canvas.drawRect(
        Rect.fromLTRB(izq, y(f.$2), size.width - der, y(f.$1)),
        Paint()..color = colores[i].withValues(alpha: 0.12),
      );
    }

    // Marcas del eje: primero los bordes de la franja, después lo medido.
    final marcas = <double>[];
    for (final v in [...bordes, valores.reduce(math.min), valores.reduce(math.max)]) {
      if (marcas.every((m) => (y(m) - y(v)).abs() >= 12)) marcas.add(v);
    }
    for (final m in marcas) {
      canvas.drawLine(
        Offset(izq, y(m)),
        Offset(size.width - der, y(m)),
        Paint()
          ..color = guia
          ..strokeWidth = 1,
      );
      _etiqueta(canvas, _num(m), Offset(izq - 4, y(m)), al: TextAlign.right);
    }

    final cada = (puntos.length / 4).ceil();
    for (final (i, p) in puntos.indexed) {
      if (i % cada != 0 && i != puntos.length - 1) continue;
      final al = puntos.length == 1
          ? TextAlign.center
          : i == 0
              ? TextAlign.left
              : i == puntos.length - 1
                  ? TextAlign.right
                  : TextAlign.center;
      _etiqueta(canvas, _corta(p.fecha), Offset(x(i), size.height - 8), al: al);
    }

    for (var j = 0; j < serie.lineas.length; j++) {
      final linea = Paint()
        ..color = colores[j]
        ..strokeWidth = 2.5
        ..style = PaintingStyle.stroke;
      final camino = Path();
      var primero = true;
      for (final (i, p) in puntos.indexed) {
        final v = p.valores[j];
        if (v == null) continue;
        primero ? camino.moveTo(x(i), y(v)) : camino.lineTo(x(i), y(v));
        primero = false;
      }
      canvas.drawPath(camino, linea);
      for (final (i, p) in puntos.indexed) {
        final v = p.valores[j];
        if (v == null) continue;
        final c = Offset(x(i), y(v));
        if (p.enmendado) {
          canvas.drawCircle(c, 4.5, Paint()..color = fondo);
          canvas.drawCircle(c, 4.5, linea..strokeWidth = 2);
          linea.strokeWidth = 2.5;
        } else {
          canvas.drawCircle(c, 4.5, Paint()..color = colores[j]);
        }
      }
    }
  }

  @override
  bool shouldRepaint(_Pintor old) =>
      old.puntos != puntos || old.colores != colores || old.fondo != fondo;
}
