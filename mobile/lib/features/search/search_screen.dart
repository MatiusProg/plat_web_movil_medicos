/// US-16 — Búsqueda de profesionales por nombre.
///
/// Coincidencia parcial sin distinguir mayúsculas ni tildes (lo resuelve el
/// backend). Búsqueda vacía = catálogo completo, paginado al llegar al final
/// de la lista. Cada tarjeta lleva a la disponibilidad del profesional
/// (US-15).
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'package:mobile/core/api/client.dart';
import 'package:mobile/core/api/errors.dart';
import 'package:mobile/core/session/session_scope.dart';
import 'package:mobile/core/theme/theme.dart';

import 'search_api.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key, this.specialtyId, this.client});

  final String? specialtyId;

  @visibleForTesting
  final ApiClient? client;

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  ApiClient? _client;
  final _scroll = ScrollController();
  final _campo = TextEditingController();

  final List<ProfesionalTarjeta> _resultados = [];
  bool _cargando = false;
  bool _hayMas = false;
  bool _primeraCarga = true;
  int _pagina = 1;
  String? _error;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_alHacerScroll);
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _client ??= widget.client ?? ApiClient(auth: SessionScope.of(context));
    if (_primeraCarga) {
      _primeraCarga = false;
      _buscar(reiniciar: true);
    }
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _scroll.dispose();
    _campo.dispose();
    if (widget.client == null) _client?.close();
    super.dispose();
  }

  void _alTeclear(String _) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 350), () {
      _buscar(reiniciar: true);
    });
  }

  void _alHacerScroll() {
    if (_scroll.position.pixels >= _scroll.position.maxScrollExtent - 200 &&
        _hayMas &&
        !_cargando) {
      _buscar(reiniciar: false);
    }
  }

  Future<void> _buscar({required bool reiniciar}) async {
    if (_cargando) return;
    setState(() {
      _cargando = true;
      _error = null;
      if (reiniciar) {
        _pagina = 1;
        _resultados.clear();
      }
    });

    try {
      final pagina = await buscarProfesionales(
        _client!,
        q: _campo.text,
        specialtyId: widget.specialtyId,
        page: _pagina,
      );
      if (!mounted) return;
      setState(() {
        _resultados.addAll(pagina.results);
        _hayMas = pagina.hayMas;
        _pagina += 1;
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Profesionales')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: TextField(
              key: const Key('search-campo'),
              controller: _campo,
              onChanged: _alTeclear,
              decoration: const InputDecoration(
                hintText: 'Buscar por nombre…',
                prefixIcon: Icon(Icons.search),
              ),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(_error!, style: const TextStyle(color: Marca.danger)),
            ),
          Expanded(
            child: _resultados.isEmpty && !_cargando
                ? const Center(child: Text('No hay profesionales que coincidan.'))
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
                    itemCount: _resultados.length + (_cargando ? 1 : 0),
                    itemBuilder: (context, i) {
                      if (i >= _resultados.length) {
                        return const Padding(
                          padding: EdgeInsets.all(16),
                          child: Center(child: CircularProgressIndicator()),
                        );
                      }
                      return _TarjetaProfesional(
                        profesional: _resultados[i],
                        onVerDisponibilidad: () => context.go(
                          '/professionals/${_resultados[i].id}/availability',
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

class _TarjetaProfesional extends StatelessWidget {
  const _TarjetaProfesional({
    required this.profesional,
    required this.onVerDisponibilidad,
  });

  final ProfesionalTarjeta profesional;
  final VoidCallback onVerDisponibilidad;

  String get _proximo {
    final iso = profesional.nextAvailableSlot;
    if (iso == null || iso.length < 16) return 'Sin agenda cargada';
    return 'Próximo: ${iso.substring(8, 10)}/${iso.substring(5, 7)} '
        '${iso.substring(11, 16)}';
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onVerDisponibilidad,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                profesional.fullName,
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 2),
              Text(
                profesional.specialties.join(' · '),
                style: const TextStyle(color: Marca.ink500, fontSize: 13),
              ),
              const SizedBox(height: 2),
              Text(
                profesional.branches.join(' · '),
                style: const TextStyle(color: Marca.ink500, fontSize: 12),
              ),
              const SizedBox(height: 6),
              Text(
                _proximo,
                style: const TextStyle(
                  color: Marca.primaryDark,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
