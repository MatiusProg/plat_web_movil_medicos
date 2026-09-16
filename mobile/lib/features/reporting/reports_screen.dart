/// Característica general 5 — El constructor de reportes en el teléfono.
///
/// La consigna pide que el usuario arme el reporte: **qué datos, con qué
/// columnas, con qué criterios**. Eso es lo que hay acá, y todo sale del
/// catálogo que devuelve `datasets/`: esta pantalla no conoce ni un nombre de
/// campo.
///
/// Tres decisiones que explican cómo se ve:
///
/// 1. **La vista previa es del backend, no del teléfono.** Se piden 50 filas
///    con `format: json` y se muestran tal como vinieron, ya formateadas. El
///    móvil no ordena, no recorta ni convierte fechas: si lo hiciera, la
///    pantalla y el Excel dirían cosas distintas sobre los mismos datos.
/// 2. **Exportar es mandar un correo.** El archivo se arma en el servidor.
///    Bajarlo dentro de la aplicación obliga a permisos de almacenamiento y a
///    un selector de carpetas, y no agrega nada: el reporte se comparte.
/// 3. **La tabla scrollea sola en horizontal.** Un reporte de ocho columnas no
///    entra en un teléfono, y comprimirlas hasta que entren lo vuelve
///    ilegible. Se lee deslizando, como una planilla.
library;

import 'package:flutter/material.dart';

import '../../core/api/client.dart';
import '../../core/api/errors.dart';
import '../../core/session/session_scope.dart';
import '../../core/widgets/organization_drawer.dart';
import 'reporting_api.dart';

/// Cómo se lee cada operador. Los códigos son los del backend
/// (`reporting/datasets.py`, `OPERATORS`).
const _operadores = <String, String>{
  'eq': 'es',
  'contains': 'contiene',
  'starts': 'empieza con',
  'lt': 'menor que',
  'lte': 'menor o igual que',
  'gt': 'mayor que',
  'gte': 'mayor o igual que',
  'in': 'es alguno de',
};

String _operador(String code) => _operadores[code] ?? code;

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key, this.client});

  @visibleForTesting
  final ApiClient? client;

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends State<ReportsScreen> {
  ApiClient? _cliente;
  ApiClient get client =>
      _cliente ??= widget.client ?? ApiClient(auth: SessionScope.of(context));

  CatalogoDeReportes? _catalogo;
  ConjuntoDeDatos? _conjunto;
  final List<String> _columnas = [];
  final List<CriterioDeFiltro> _criterios = [];

  ResultadoDeReporte? _resultado;
  bool _cargando = false;
  bool _ejecutando = false;
  String? _error;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_catalogo == null && _error == null) _cargarCatalogo();
  }

  Future<void> _cargarCatalogo() async {
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final catalogo = await listarConjuntos(client);
      if (!mounted) return;
      setState(() {
        _catalogo = catalogo;
        if (catalogo.datasets.isNotEmpty) {
          _elegirConjunto(catalogo.datasets.first);
        }
      });
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() => _error = error.message);
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  /// Cambiar de conjunto **descarta las columnas y los criterios**: son de otro
  /// conjunto y el backend los rechazaría uno por uno. Es menos molesto perder
  /// la selección que ir corrigiendo errores de campos que ya no existen.
  void _elegirConjunto(ConjuntoDeDatos conjunto) {
    _conjunto = conjunto;
    _columnas
      ..clear()
      ..addAll(
        conjunto.defaultColumns.isNotEmpty
            ? conjunto.defaultColumns
            : conjunto.columns.take(4).map((c) => c.code),
      );
    _criterios.clear();
    _resultado = null;
  }

  Future<void> _ejecutar() async {
    final conjunto = _conjunto;
    if (conjunto == null || _columnas.isEmpty) return;

    setState(() {
      _ejecutando = true;
      _error = null;
    });
    try {
      final resultado = await ejecutarReporte(
        client,
        dataset: conjunto.code,
        columns: _columnasEnOrden(conjunto),
        filters: _criterios,
      );
      if (!mounted) return;
      setState(() => _resultado = resultado);
    } on ApiError catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error.message;
        _resultado = null;
      });
    } finally {
      if (mounted) setState(() => _ejecutando = false);
    }
  }

  /// Las columnas en el orden del catálogo y no en el que se fueron tocando:
  /// así dos personas que eligen lo mismo obtienen la misma tabla.
  List<String> _columnasEnOrden(ConjuntoDeDatos conjunto) => [
    for (final columna in conjunto.columns)
      if (_columnas.contains(columna.code)) columna.code,
  ];

  Future<void> _agregarCriterio() async {
    final conjunto = _conjunto;
    if (conjunto == null || conjunto.filters.isEmpty) return;

    final criterio = await showModalBottomSheet<CriterioDeFiltro>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _FormularioDeCriterio(filtros: conjunto.filters),
    );
    if (criterio == null || !mounted) return;
    setState(() {
      _criterios.add(criterio);
      _resultado = null;
    });
  }

  Future<void> _enviarPorCorreo() async {
    final conjunto = _conjunto;
    final catalogo = _catalogo;
    if (conjunto == null || catalogo == null || _columnas.isEmpty) return;

    final envio = await showModalBottomSheet<_PedidoDeEnvio>(
      context: context,
      isScrollControlled: true,
      builder: (_) => _FormularioDeEnvio(formatos: catalogo.formats),
    );
    if (envio == null || !mounted) return;

    setState(() => _ejecutando = true);
    try {
      final resultado = await enviarReportePorCorreo(
        client,
        dataset: conjunto.code,
        columns: _columnasEnOrden(conjunto),
        filters: _criterios,
        format: envio.formato,
        recipients: envio.destinatarios,
        title: conjunto.label,
      );
      if (!mounted) return;
      final cuantos = resultado.recipients.length;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Enviado a $cuantos ${cuantos == 1 ? "dirección" : "direcciones"} '
            '· ${resultado.rows} filas',
          ),
        ),
      );
    } on ApiError catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(error.message)));
    } finally {
      if (mounted) setState(() => _ejecutando = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final catalogo = _catalogo;
    final conjunto = _conjunto;

    return Scaffold(
      appBar: AppBar(title: const Text('Reportes')),
      drawer: const OrganizationDrawer(),
      body: _cargando && catalogo == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
              children: [
                Text(
                  'Armá el reporte con las columnas y los criterios que '
                  'necesites. La vista previa muestra las primeras filas; el '
                  'archivo completo se manda por correo.',
                  style: theme.textTheme.bodySmall,
                ),
                const SizedBox(height: 16),

                if (_error != null) ...[
                  _Aviso(mensaje: _error!, onReintentar: _cargarCatalogo),
                  const SizedBox(height: 16),
                ],

                if (catalogo != null && catalogo.datasets.isEmpty)
                  Text(
                    'Tu cuenta no tiene permiso para consultar ningún conjunto '
                    'de datos.',
                    style: theme.textTheme.bodyMedium,
                  ),

                if (conjunto != null) ...[
                  DropdownButtonFormField<String>(
                    initialValue: conjunto.code,
                    decoration: const InputDecoration(
                      labelText: 'Qué reportar',
                      border: OutlineInputBorder(),
                    ),
                    items: [
                      for (final d in catalogo!.datasets)
                        DropdownMenuItem(value: d.code, child: Text(d.label)),
                    ],
                    onChanged: (codigo) {
                      final elegido = catalogo.datasets.firstWhere(
                        (d) => d.code == codigo,
                        orElse: () => conjunto,
                      );
                      setState(() => _elegirConjunto(elegido));
                    },
                  ),
                  if (conjunto.description.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      conjunto.description,
                      style: theme.textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 20),

                  _Titulo('Columnas (${_columnas.length})'),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    children: [
                      for (final columna in conjunto.columns)
                        FilterChip(
                          label: Text(columna.label),
                          selected: _columnas.contains(columna.code),
                          onSelected: (elegida) => setState(() {
                            if (elegida) {
                              _columnas.add(columna.code);
                            } else {
                              _columnas.remove(columna.code);
                            }
                            _resultado = null;
                          }),
                        ),
                    ],
                  ),
                  if (_columnas.isEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Elegí al menos una columna.',
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.error,
                      ),
                    ),
                  ],
                  const SizedBox(height: 20),

                  Row(
                    children: [
                      Expanded(
                        child: _Titulo('Criterios (${_criterios.length})'),
                      ),
                      if (conjunto.filters.isNotEmpty)
                        TextButton.icon(
                          onPressed: _agregarCriterio,
                          icon: const Icon(Icons.add, size: 18),
                          label: const Text('Agregar'),
                        ),
                    ],
                  ),
                  if (_criterios.isEmpty)
                    Text(
                      'Sin criterios: entran todas las filas.',
                      style: theme.textTheme.bodySmall,
                    ),
                  for (final criterio in _criterios)
                    Padding(
                      padding: const EdgeInsets.only(top: 4),
                      child: InputChip(
                        label: Text(criterio.etiqueta),
                        onDeleted: () => setState(() {
                          _criterios.remove(criterio);
                          _resultado = null;
                        }),
                      ),
                    ),
                  const SizedBox(height: 24),

                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          onPressed: _columnas.isEmpty || _ejecutando
                              ? null
                              : _ejecutar,
                          icon: const Icon(Icons.play_arrow),
                          label: const Text('Ejecutar'),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: _columnas.isEmpty || _ejecutando
                              ? null
                              : _enviarPorCorreo,
                          icon: const Icon(Icons.mail_outline),
                          label: const Text('Enviar'),
                        ),
                      ),
                    ],
                  ),
                  if (_ejecutando) ...[
                    const SizedBox(height: 16),
                    const Center(child: CircularProgressIndicator()),
                  ],
                ],

                if (_resultado != null) ...[
                  const SizedBox(height: 24),
                  _Tabla(
                    resultado: _resultado!,
                    maxRows: catalogo?.maxRows ?? 0,
                  ),
                ],
              ],
            ),
    );
  }
}

class _Titulo extends StatelessWidget {
  const _Titulo(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) => Text(
    texto,
    style: Theme.of(context).textTheme.titleSmall
        ?.copyWith(fontWeight: FontWeight.w600),
  );
}

class _Aviso extends StatelessWidget {
  const _Aviso({required this.mensaje, this.onReintentar});

  final String mensaje;
  final VoidCallback? onReintentar;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              mensaje,
              style: TextStyle(color: theme.colorScheme.onErrorContainer),
            ),
          ),
          if (onReintentar != null)
            TextButton(
              onPressed: onReintentar,
              child: const Text('Reintentar'),
            ),
        ],
      ),
    );
  }
}

/// La tabla del resultado. Scrollea en horizontal: ver el encabezado.
class _Tabla extends StatelessWidget {
  const _Tabla({required this.resultado, required this.maxRows});

  final ResultadoDeReporte resultado;
  final int maxRows;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (resultado.rows.isEmpty) {
      return Text(
        'Ninguna fila cumple los criterios.',
        style: theme.textTheme.bodyMedium,
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(resultado.title, style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            columns: [
              for (final columna in resultado.columns)
                DataColumn(label: Text(columna.label)),
            ],
            rows: [
              for (final fila in resultado.rows)
                DataRow(
                  cells: [
                    for (var i = 0; i < resultado.columns.length; i++)
                      DataCell(Text(i < fila.length ? fila[i] : '')),
                  ],
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        Text(
          resultado.truncated
              ? '${resultado.rows.length} filas en la vista previa; hay más. '
                    'El archivo exporta hasta $maxRows.'
              : '${resultado.rows.length} '
                    '${resultado.rows.length == 1 ? "fila" : "filas"}.',
          style: theme.textTheme.bodySmall,
        ),
      ],
    );
  }
}

// --------------------------------------------------------------------------
//  Armar un criterio
// --------------------------------------------------------------------------
class _FormularioDeCriterio extends StatefulWidget {
  const _FormularioDeCriterio({required this.filtros});

  final List<CampoDeReporte> filtros;

  @override
  State<_FormularioDeCriterio> createState() => _FormularioDeCriterioState();
}

class _FormularioDeCriterioState extends State<_FormularioDeCriterio> {
  late CampoDeReporte _campo = widget.filtros.first;
  late String _comparacion = _campo.operators.isEmpty
      ? 'eq'
      : _campo.operators.first;
  final _texto = TextEditingController();
  String? _opcion;
  bool _booleano = true;
  DateTime? _fecha;

  @override
  void initState() {
    super.initState();
    // El desplegable de un campo `choice` se dibuja con la primera opción
    // marcada, así que el criterio ya tiene valor. Sin esto, el botón de
    // agregar nace deshabilitado y hay que volver a elegir lo que ya se ve
    // elegido, que es de las cosas más desconcertantes de un formulario.
    if (_campo.kind == 'choice' && _campo.choices.isNotEmpty) {
      _opcion = _campo.choices.first.value;
    }
  }

  @override
  void dispose() {
    _texto.dispose();
    super.dispose();
  }

  void _cambiarCampo(CampoDeReporte campo) {
    setState(() {
      _campo = campo;
      _comparacion = campo.operators.isEmpty ? 'eq' : campo.operators.first;
      _texto.clear();
      _opcion = campo.kind == 'choice' && campo.choices.isNotEmpty
          ? campo.choices.first.value
          : null;
      _fecha = null;
    });
  }

  /// El valor y cómo se lee, juntos: la etiqueta se arma acá porque es acá
  /// donde se conocen las opciones del desplegable. Después sólo queda el
  /// código, que no le dice nada a nadie.
  (Object, String)? _valor() {
    switch (_campo.kind) {
      case 'boolean':
        return (_booleano, _booleano ? 'Sí' : 'No');
      case 'choice':
        final opcion = _opcion;
        if (opcion == null) return null;
        final etiqueta = _campo.choices
            .firstWhere(
              (o) => o.value == opcion,
              orElse: () => OpcionDeCampo(value: opcion, label: opcion),
            )
            .label;
        return (opcion, etiqueta);
      case 'date':
      case 'datetime':
        final fecha = _fecha;
        if (fecha == null) return null;
        String dos(int n) => n.toString().padLeft(2, '0');
        return (
          '${fecha.year}-${dos(fecha.month)}-${dos(fecha.day)}',
          '${dos(fecha.day)}/${dos(fecha.month)}/${fecha.year}',
        );
      case 'number':
        final numero = num.tryParse(_texto.text.trim());
        if (numero == null) return null;
        return (numero, '$numero');
      default:
        final texto = _texto.text.trim();
        if (texto.isEmpty) return null;
        return (texto, texto);
    }
  }

  Future<void> _elegirFecha() async {
    final hoy = DateTime.now();
    final elegida = await showDatePicker(
      context: context,
      initialDate: _fecha ?? hoy,
      firstDate: DateTime(hoy.year - 10),
      lastDate: DateTime(hoy.year + 2),
    );
    if (elegida != null) setState(() => _fecha = elegida);
  }

  @override
  Widget build(BuildContext context) {
    final valor = _valor();

    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Nuevo criterio',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 16),

          DropdownButtonFormField<String>(
            initialValue: _campo.code,
            decoration: const InputDecoration(
              labelText: 'Campo',
              border: OutlineInputBorder(),
            ),
            items: [
              for (final filtro in widget.filtros)
                DropdownMenuItem(value: filtro.code, child: Text(filtro.label)),
            ],
            onChanged: (codigo) => _cambiarCampo(
              widget.filtros.firstWhere((f) => f.code == codigo),
            ),
          ),
          const SizedBox(height: 12),

          if (_campo.operators.length > 1) ...[
            DropdownButtonFormField<String>(
              initialValue: _comparacion,
              decoration: const InputDecoration(
                labelText: 'Comparación',
                border: OutlineInputBorder(),
              ),
              items: [
                for (final op in _campo.operators)
                  DropdownMenuItem(value: op, child: Text(_operador(op))),
              ],
              onChanged: (op) => setState(() => _comparacion = op ?? 'eq'),
            ),
            const SizedBox(height: 12),
          ],

          _campoDeValor(),
          const SizedBox(height: 20),

          FilledButton(
            onPressed: valor == null
                ? null
                : () => Navigator.of(context).pop(
                    CriterioDeFiltro(
                      field: _campo.code,
                      operator: _comparacion,
                      value: valor.$1,
                      etiqueta:
                          '${_campo.label} ${_operador(_comparacion)} ${valor.$2}',
                    ),
                  ),
            child: const Text('Agregar criterio'),
          ),
        ],
      ),
    );
  }

  Widget _campoDeValor() {
    switch (_campo.kind) {
      case 'boolean':
        return SwitchListTile(
          contentPadding: EdgeInsets.zero,
          title: Text(_campo.label),
          subtitle: Text(_booleano ? 'Sí' : 'No'),
          value: _booleano,
          onChanged: (v) => setState(() => _booleano = v),
        );
      case 'choice':
        return DropdownButtonFormField<String>(
          initialValue:
              _opcion ??
              (_campo.choices.isNotEmpty ? _campo.choices.first.value : null),
          decoration: const InputDecoration(
            labelText: 'Valor',
            border: OutlineInputBorder(),
          ),
          items: [
            for (final opcion in _campo.choices)
              DropdownMenuItem(value: opcion.value, child: Text(opcion.label)),
          ],
          onChanged: (v) => setState(() => _opcion = v),
        );
      case 'date':
      case 'datetime':
        final fecha = _fecha;
        String dos(int n) => n.toString().padLeft(2, '0');
        return OutlinedButton.icon(
          onPressed: _elegirFecha,
          icon: const Icon(Icons.calendar_today, size: 18),
          label: Text(
            fecha == null
                ? 'Elegir fecha'
                : '${dos(fecha.day)}/${dos(fecha.month)}/${fecha.year}',
          ),
        );
      default:
        return TextField(
          controller: _texto,
          keyboardType: _campo.kind == 'number'
              ? TextInputType.number
              : TextInputType.text,
          decoration: const InputDecoration(
            labelText: 'Valor',
            border: OutlineInputBorder(),
          ),
          onChanged: (_) => setState(() {}),
        );
    }
  }
}

// --------------------------------------------------------------------------
//  Mandar el reporte por correo
// --------------------------------------------------------------------------
class _PedidoDeEnvio {
  const _PedidoDeEnvio({required this.formato, required this.destinatarios});

  final String formato;
  final List<String> destinatarios;
}

class _FormularioDeEnvio extends StatefulWidget {
  const _FormularioDeEnvio({required this.formatos});

  final List<String> formatos;

  @override
  State<_FormularioDeEnvio> createState() => _FormularioDeEnvioState();
}

class _FormularioDeEnvioState extends State<_FormularioDeEnvio> {
  late String _formato = widget.formatos.isEmpty
      ? 'xlsx'
      : widget.formatos.first;
  final _correos = TextEditingController();

  @override
  void dispose() {
    _correos.dispose();
    super.dispose();
  }

  List<String> get _destinatarios => _correos.text
      .split(RegExp(r'[,;\s]+'))
      .map((e) => e.trim())
      .where((e) => e.contains('@'))
      .toList();

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(
        20,
        20,
        20,
        20 + MediaQuery.of(context).viewInsets.bottom,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Enviar el reporte',
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'El archivo se genera en el servidor con todas las filas, no sólo '
            'las de la vista previa.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
          const SizedBox(height: 16),

          Wrap(
            spacing: 8,
            children: [
              for (final formato in widget.formatos)
                ChoiceChip(
                  label: Text(formato.toUpperCase()),
                  selected: _formato == formato,
                  onSelected: (_) => setState(() => _formato = formato),
                ),
            ],
          ),
          const SizedBox(height: 16),

          TextField(
            controller: _correos,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Destinatarios',
              helperText: 'Separados por coma',
              border: OutlineInputBorder(),
            ),
            onChanged: (_) => setState(() {}),
          ),
          const SizedBox(height: 20),

          FilledButton(
            onPressed: _destinatarios.isEmpty
                ? null
                : () => Navigator.of(context).pop(
                    _PedidoDeEnvio(
                      formato: _formato,
                      destinatarios: _destinatarios,
                    ),
                  ),
            child: const Text('Enviar'),
          ),
        ],
      ),
    );
  }
}
