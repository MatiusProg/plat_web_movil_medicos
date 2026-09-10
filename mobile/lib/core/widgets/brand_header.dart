/// La cabecera de marca de las pantallas de sesión.
///
/// Un degradé radial que respira lentamente -un `AnimationController` en
/// loop que corre el punto focal del gradiente- para que el login y el
/// registro no se sientan un formulario gris más. Es la misma pieza que
/// tenía la versión anterior de la app (antes de adoptar esta arquitectura),
/// portada tal cual: sólo cambian los nombres a inglés, para no romper la
/// convención de `core/`.
library;

import 'package:flutter/material.dart';

import '../theme/theme.dart';

class BrandHeader extends StatefulWidget {
  const BrandHeader({super.key, this.organization, this.compact = false});

  /// El centro médico al que se está por entrar, si ya se escribió. `null`
  /// o vacío muestra el texto genérico.
  final String? organization;

  /// Sin la frase larga ni tanto espaciado -para pantallas como el registro,
  /// donde el formulario ya es largo y la cabecera no puede comerse media
  /// pantalla-.
  final bool compact;

  @override
  State<BrandHeader> createState() => _BrandHeaderState();
}

class _BrandHeaderState extends State<BrandHeader>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final t = _controller.value;
        return Container(
          decoration: BoxDecoration(
            gradient: RadialGradient(
              center: Alignment(-0.6 + t * 1.2, -0.8 + t * 0.6),
              radius: 1.4,
              colors: Marca.gradient,
            ),
          ),
          // SafeArea propio: esta cabecera puede ser el primer widget de la
          // pantalla, así que no depende de que el padre ya haya reservado la
          // barra de estado.
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: EdgeInsets.fromLTRB(
                24,
                widget.compact ? 12 : 24,
                24,
                24,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.25),
                          ),
                        ),
                        child: const Icon(
                          Icons.favorite_rounded,
                          color: Colors.white,
                          size: 20,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Centro Médico',
                            style: TextStyle(
                              color: Colors.white,
                              fontWeight: FontWeight.w600,
                              fontSize: 15,
                            ),
                          ),
                          Text(
                            'Plataforma de atención ambulatoria',
                            style: TextStyle(color: Colors.white70, fontSize: 12),
                          ),
                        ],
                      ),
                    ],
                  ),
                  if (!widget.compact) ...[
                    const SizedBox(height: 28),
                    Text(
                      'La historia clínica de cada paciente,\nen un solo lugar.',
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(color: Colors.white, fontSize: 24),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Text(
                    widget.organization != null && widget.organization!.isNotEmpty
                        ? 'Ingresando a ${widget.organization}'
                        : 'Cada centro médico administra su propia información.',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.75),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
