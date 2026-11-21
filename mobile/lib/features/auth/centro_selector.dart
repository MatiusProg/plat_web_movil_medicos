/// El centro médico del login y del registro: se elige de una lista en vez de
/// escribir el slug.
///
/// La lista viene de `GET /accounts/centers/` (pública: sólo nombre y slug de
/// las organizaciones activas), así que se actualiza sola con las altas y las
/// bajas. En el login se suma «Administración de la plataforma» para el
/// superadministrador, que entra sin organización (slug vacío).
///
/// El valor es `null` si todavía no eligió, `''` para la plataforma o el slug.
/// Si la lista no se puede traer (sin conexión, backend caído) vuelve el campo
/// de texto de siempre: el login nunca queda trabado por esto.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';

class Centro {
  const Centro({required this.slug, required this.name});

  factory Centro.fromJson(Map<String, dynamic> json) => Centro(
        slug: json['slug'] as String? ?? '',
        name: json['name'] as String? ?? '',
      );

  final String slug;
  final String name;
}

/// `GET /accounts/centers/`, sin sesión.
Future<List<Centro>> listarCentros(ApiClient client) async {
  final data = await client.get('/accounts/centers/', authenticated: false);
  return [
    for (final c in (data as List? ?? const []))
      if (c is Map<String, dynamic>) Centro.fromJson(c),
  ];
}

class SelectorCentro extends StatefulWidget {
  const SelectorCentro({
    super.key,
    required this.cargar,
    required this.valor,
    required this.onCambio,
    this.conPlataforma = false,
    this.habilitado = true,
    this.errorText,
    this.ayuda,
  });

  final Future<List<Centro>> Function() cargar;
  final String? valor;
  final ValueChanged<String?> onCambio;
  final bool conPlataforma;
  final bool habilitado;
  final String? errorText;
  final String? ayuda;

  static const plataforma = 'Administración de la plataforma';

  @override
  State<SelectorCentro> createState() => _SelectorCentroState();
}

class _SelectorCentroState extends State<SelectorCentro> {
  List<Centro>? _centros;
  bool _sinLista = false;
  final _texto = TextEditingController();

  @override
  void initState() {
    super.initState();
    _texto.text = widget.valor ?? '';
    _traer();
  }

  @override
  void dispose() {
    _texto.dispose();
    super.dispose();
  }

  Future<void> _traer() async {
    try {
      final centros = await widget.cargar();
      if (!mounted) return;
      setState(() => _centros = centros);
      // El último centro usado puede haberse dado de baja: no queda elegido.
      final v = widget.valor;
      if (v != null && v.isNotEmpty && !centros.any((c) => c.slug == v)) {
        widget.onCambio(null);
      }
    } catch (_) {
      if (mounted) setState(() => _sinLista = true);
    }
  }

  String? get _nombre {
    final v = widget.valor;
    if (v == null) return null;
    if (v.isEmpty) return widget.conPlataforma ? SelectorCentro.plataforma : null;
    for (final c in _centros ?? const <Centro>[]) {
      if (c.slug == v) return c.name;
    }
    return null;
  }

  Future<void> _abrir() async {
    final centros = _centros;
    if (centros == null) return;
    FocusScope.of(context).unfocus();
    final elegido = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      showDragHandle: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      // Con el teclado abierto (el buscador), la hoja sube por encima de él
      // en vez de quedar tapada.
      builder: (hoja) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(hoja).bottom),
        child: _ListaCentros(
          centros: centros,
          actual: widget.valor,
          conPlataforma: widget.conPlataforma,
        ),
      ),
    );
    if (elegido != null) widget.onCambio(elegido);
  }

  @override
  Widget build(BuildContext context) {
    if (_sinLista) {
      return TextFormField(
        controller: _texto,
        enabled: widget.habilitado,
        autocorrect: false,
        textInputAction: TextInputAction.next,
        onChanged: widget.onCambio,
        decoration: InputDecoration(
          labelText: 'Centro médico',
          hintText: 'kolping',
          helperText: widget.conPlataforma
              ? 'No pudimos cargar la lista: escribe el código del centro. '
                  'Vacío solo si administras la plataforma.'
              : 'No pudimos cargar la lista: escribe el código del centro.',
          helperMaxLines: 2,
          errorText: widget.errorText,
          prefixIcon: const Icon(Icons.apartment_outlined),
        ),
      );
    }

    final theme = Theme.of(context);
    final cargando = _centros == null;
    final nombre = _nombre;
    return Semantics(
      button: true,
      label: 'Centro médico',
      value: nombre ?? 'Sin elegir',
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: widget.habilitado && !cargando ? _abrir : null,
        child: InputDecorator(
          isEmpty: nombre == null,
          isFocused: false,
          decoration: InputDecoration(
            labelText: 'Centro médico',
            hintText: cargando ? 'Cargando centros…' : 'Elige tu centro médico',
            helperText: widget.ayuda,
            errorText: widget.errorText,
            enabled: widget.habilitado,
            prefixIcon: Icon(
              nombre == SelectorCentro.plataforma
                  ? Icons.admin_panel_settings_outlined
                  : Icons.apartment_outlined,
            ),
            suffixIcon: cargando
                ? const Padding(
                    padding: EdgeInsets.all(14),
                    child: SizedBox.square(
                      dimension: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : const Icon(Icons.expand_more_rounded),
          ),
          child: nombre == null
              ? null
              : Text(
                  nombre,
                  style: theme.textTheme.bodyLarge,
                  overflow: TextOverflow.ellipsis,
                ),
        ),
      ),
    );
  }
}

/// La hoja que sube desde abajo: buscador (si hay muchos), los centros con su
/// inicial y, al final y aparte, la administración de la plataforma.
class _ListaCentros extends StatefulWidget {
  const _ListaCentros({
    required this.centros,
    required this.actual,
    required this.conPlataforma,
  });

  final List<Centro> centros;
  final String? actual;
  final bool conPlataforma;

  @override
  State<_ListaCentros> createState() => _ListaCentrosState();
}

class _ListaCentrosState extends State<_ListaCentros> {
  String _filtro = '';

  static String _sinTildes(String s) => s
      .toLowerCase()
      .replaceAll(RegExp('[áà]'), 'a')
      .replaceAll(RegExp('[éè]'), 'e')
      .replaceAll(RegExp('[íì]'), 'i')
      .replaceAll(RegExp('[óò]'), 'o')
      .replaceAll(RegExp('[úùü]'), 'u');

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final f = _sinTildes(_filtro.trim());
    final visibles = [
      for (final c in widget.centros)
        if (f.isEmpty || _sinTildes(c.name).contains(f) || c.slug.contains(f)) c,
    ];
    final buscador = widget.centros.length > 6;

    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: buscador ? 0.75 : 0.55,
      minChildSize: 0.35,
      maxChildSize: 0.92,
      builder: (context, scroll) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 4),
            child: Text('Elige tu centro médico', style: theme.textTheme.titleLarge),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 0, 24, 12),
            child: Text(
              'Cada centro tiene sus propias cuentas: entra al que te atiende.',
              style: theme.textTheme.bodyMedium
                  ?.copyWith(color: theme.colorScheme.onSurfaceVariant),
            ),
          ),
          if (buscador)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: TextField(
                autofocus: false,
                onChanged: (v) => setState(() => _filtro = v),
                decoration: const InputDecoration(
                  hintText: 'Buscar por nombre',
                  prefixIcon: Icon(Icons.search),
                ),
              ),
            ),
          Expanded(
            child: ListView(
              controller: scroll,
              padding: const EdgeInsets.only(bottom: 16),
              children: [
                if (widget.centros.isEmpty)
                  const _Vacio('Todavía no hay centros médicos activos.')
                else if (visibles.isEmpty)
                  const _Vacio('Ningún centro coincide con la búsqueda.'),
                for (final c in visibles)
                  _Fila(
                    titulo: c.name,
                    inicial: c.name.isEmpty ? '?' : c.name.characters.first.toUpperCase(),
                    elegido: widget.actual == c.slug,
                    onTap: () => Navigator.of(context).pop(c.slug),
                  ),
                if (widget.conPlataforma) ...[
                  const Divider(height: 24, indent: 24, endIndent: 24),
                  _Fila(
                    titulo: SelectorCentro.plataforma,
                    subtitulo: 'Solo para el superadministrador',
                    icono: Icons.admin_panel_settings_outlined,
                    elegido: widget.actual == '',
                    onTap: () => Navigator.of(context).pop(''),
                  ),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Fila extends StatelessWidget {
  const _Fila({
    required this.titulo,
    required this.elegido,
    required this.onTap,
    this.subtitulo,
    this.inicial,
    this.icono,
  });

  final String titulo;
  final String? subtitulo;
  final String? inicial;
  final IconData? icono;
  final bool elegido;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return ListTile(
      contentPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 2),
      selected: elegido,
      selectedTileColor: scheme.primaryContainer.withValues(alpha: 0.35),
      leading: CircleAvatar(
        radius: 20,
        backgroundColor: icono == null ? scheme.primary : scheme.surfaceContainerHighest,
        foregroundColor: icono == null ? scheme.onPrimary : scheme.onSurfaceVariant,
        child: icono == null
            ? Text(inicial ?? '', style: const TextStyle(fontWeight: FontWeight.w600))
            : Icon(icono, size: 20),
      ),
      title: Text(titulo),
      subtitle: subtitulo == null ? null : Text(subtitulo!),
      trailing: elegido ? Icon(Icons.check_circle, color: scheme.primary) : null,
      onTap: onTap,
    );
  }
}

class _Vacio extends StatelessWidget {
  const _Vacio(this.texto);
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        child: Text(
          texto,
          textAlign: TextAlign.center,
          style: TextStyle(color: Theme.of(context).colorScheme.onSurfaceVariant),
        ),
      );
}

/// «Centro médico: Clínica San Gabriel» en el inicio, con el nombre en lugar
/// del slug. Mientras llega la lista, o si no llega, queda el slug.
class NombreDelCentro extends StatefulWidget {
  const NombreDelCentro({super.key, required this.slug, this.style, this.cargar});

  final String? slug;
  final TextStyle? style;

  /// Para las pruebas; por defecto, la lista pública del backend.
  final Future<List<Centro>> Function()? cargar;

  @override
  State<NombreDelCentro> createState() => _NombreDelCentroState();
}

class _NombreDelCentroState extends State<NombreDelCentro> {
  String? _nombre;

  @override
  void initState() {
    super.initState();
    _buscar();
  }

  // Otra sesión, otro centro: el nombre anterior ya no vale.
  @override
  void didUpdateWidget(NombreDelCentro viejo) {
    super.didUpdateWidget(viejo);
    if (viejo.slug != widget.slug) {
      _nombre = null;
      _buscar();
    }
  }

  void _buscar() {
    final slug = widget.slug;
    if (slug == null || slug.isEmpty) return;
    (widget.cargar ?? () => listarCentros(ApiClient()))().then((centros) {
      for (final c in centros) {
        if (c.slug == slug && widget.slug == slug && mounted) {
          setState(() => _nombre = c.name);
        }
      }
    }).catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    final slug = widget.slug;
    final texto = slug == null || slug.isEmpty
        ? SelectorCentro.plataforma
        : _nombre ?? slug;
    return Text('Centro médico: $texto', style: widget.style);
  }
}
