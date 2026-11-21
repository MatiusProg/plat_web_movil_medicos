import 'package:flutter/material.dart';

/// El logo del Centro Médico: corazón con pulso. Es el mismo trazo del ícono
/// de la app, de las notificaciones y del favicon de la web.
class LogoMarca extends StatelessWidget {
  const LogoMarca({super.key, this.size = 20, this.color = Colors.white});

  final double size;
  final Color color;

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'Centro Médico',
        child: CustomPaint(
          size: Size.square(size),
          painter: _Logo(color),
        ),
      );
}

class _Logo extends CustomPainter {
  _Logo(this.color);
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    // Dibujado en una grilla de 24 × 24, como el ícono de la web.
    canvas.scale(size.width / 24, size.height / 24);
    final trazo = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 2.2
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    final corazon = Path()
      ..moveTo(12, 21.3)
      ..cubicTo(5.3, 16.7, 1.3, 12.7, 1.3, 8)
      ..cubicTo(1.3, 4.7, 4, 2.3, 7, 2.3)
      ..cubicTo(9.3, 2.3, 11, 3.7, 12, 5.3)
      ..cubicTo(13, 3.7, 14.7, 2.3, 17, 2.3)
      ..cubicTo(20, 2.3, 22.7, 4.7, 22.7, 8)
      ..cubicTo(22.7, 12.7, 18.7, 16.7, 12, 21.3)
      ..close();
    final pulso = Path()
      ..moveTo(3.3, 11.3)
      ..lineTo(8, 11.3)
      ..lineTo(10, 7.7)
      ..lineTo(12.7, 15)
      ..lineTo(14.7, 10.3)
      ..lineTo(20.7, 11.3);
    canvas
      ..drawPath(corazon, trazo)
      ..drawPath(pulso, trazo);
  }

  @override
  bool shouldRepaint(_Logo old) => old.color != color;
}
