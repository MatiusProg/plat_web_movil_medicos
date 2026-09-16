/// Característica general 5 — El constructor de reportes, del lado del móvil.
///
///     GET  /api/reporting/datasets/   qué se puede reportar y con qué filtros
///     POST /api/reporting/run/        ejecutar la definición que se armó
///
/// **El móvil no sabe nada del modelo de datos, y es a propósito.** Los
/// conjuntos, sus columnas, sus filtros y los operadores de cada tipo vienen
/// de `datasets/`: agregar un conjunto en el backend lo hace aparecer acá sin
/// tocar una línea de Dart. Por eso esta pantalla no tiene ninguna lista de
/// campos escrita a mano.
///
/// **Exportar en un teléfono es mandar un correo.** El backend genera xlsx,
/// pdf, html y csv, pero bajar un archivo dentro de la aplicación obliga a
/// pedir permisos de almacenamiento y a elegir dónde guardarlo. `recipients`
/// existe justo para esto: el archivo se arma en el servidor y llega al correo.
library;

import '../../core/api/client.dart';

/// Una columna que se puede pedir, o un campo por el que se puede filtrar.
class CampoDeReporte {
  const CampoDeReporte({
    required this.code,
    required this.label,
    required this.kind,
    this.choices = const [],
    this.operators = const [],
  });

  final String code;
  final String label;

  /// `text`, `number`, `date`, `datetime`, `boolean` o `choice`. No son los
  /// tipos de Django: son los del formulario, y deciden qué se dibuja.
  final String kind;

  /// Sólo en los campos `choice`. Llega como lista y no como objeto porque el
  /// orden importa: «Masculino, Femenino, Otro» no es alfabético.
  final List<OpcionDeCampo> choices;

  /// Sólo en los filtros: qué comparaciones tienen sentido para este tipo.
  final List<String> operators;

  factory CampoDeReporte.fromJson(Map<String, dynamic> json) => CampoDeReporte(
    code: json['code'] as String? ?? '',
    label: json['label'] as String? ?? '',
    kind: json['kind'] as String? ?? 'text',
    choices: (json['choices'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(OpcionDeCampo.fromJson)
        .toList(),
    operators: (json['operators'] as List? ?? const [])
        .whereType<String>()
        .toList(),
  );
}

class OpcionDeCampo {
  const OpcionDeCampo({required this.value, required this.label});

  final String value;
  final String label;

  factory OpcionDeCampo.fromJson(Map<String, dynamic> json) => OpcionDeCampo(
    value: '${json['value'] ?? ''}',
    label: json['label'] as String? ?? '',
  );
}

/// Un origen de datos reportable, con todo lo que hace falta para dibujar el
/// formulario entero.
class ConjuntoDeDatos {
  const ConjuntoDeDatos({
    required this.code,
    required this.label,
    required this.description,
    required this.columns,
    required this.filters,
    required this.defaultColumns,
  });

  final String code;
  final String label;
  final String description;
  final List<CampoDeReporte> columns;
  final List<CampoDeReporte> filters;

  /// Con qué columnas se abre el constructor. Un reporte sin columnas elegidas
  /// no se puede ejecutar, así que empezar en blanco sería empezar en error.
  final List<String> defaultColumns;

  factory ConjuntoDeDatos.fromJson(Map<String, dynamic> json) =>
      ConjuntoDeDatos(
        code: json['code'] as String? ?? '',
        label: json['label'] as String? ?? '',
        description: json['description'] as String? ?? '',
        columns: (json['columns'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(CampoDeReporte.fromJson)
            .toList(),
        filters: (json['filters'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(CampoDeReporte.fromJson)
            .toList(),
        defaultColumns: (json['default_columns'] as List? ?? const [])
            .whereType<String>()
            .toList(),
      );
}

/// Lo que devuelve `datasets/`: los conjuntos y las reglas del constructor.
class CatalogoDeReportes {
  const CatalogoDeReportes({
    required this.datasets,
    required this.formats,
    required this.maxRows,
  });

  final List<ConjuntoDeDatos> datasets;
  final List<String> formats;

  /// El tope de filas que exporta el backend. Se muestra al pie del resultado
  /// cuando la consulta se truncó, para que nadie crea que ésas son todas.
  final int maxRows;
}

/// Un criterio ya armado por la persona: campo, comparación y valor.
class CriterioDeFiltro {
  const CriterioDeFiltro({
    required this.field,
    required this.operator,
    required this.value,
    required this.etiqueta,
  });

  final String field;
  final String operator;
  final Object value;

  /// Cómo se lee el criterio en la lista: «Sexo es Femenino». Se arma al
  /// crearlo, con las etiquetas del catálogo, y no se recalcula.
  final String etiqueta;

  Map<String, dynamic> toJson() => {
    'field': field,
    'operator': operator,
    'value': value,
  };
}

/// El resultado de ejecutar una definición con `format: json`.
class ResultadoDeReporte {
  const ResultadoDeReporte({
    required this.title,
    required this.columns,
    required this.rows,
    required this.truncated,
  });

  final String title;
  final List<CampoDeReporte> columns;

  /// Las filas ya formateadas por el backend, alineadas con `columns`. Vienen
  /// como listas y no como objetos: son una tabla, no entidades.
  final List<List<String>> rows;

  /// Hubo más filas de las que entraron en la vista previa.
  final bool truncated;

  factory ResultadoDeReporte.fromJson(Map<String, dynamic> json) =>
      ResultadoDeReporte(
        title: json['title'] as String? ?? '',
        columns: (json['columns'] as List? ?? const [])
            .whereType<Map<String, dynamic>>()
            .map(CampoDeReporte.fromJson)
            .toList(),
        rows: (json['rows'] as List? ?? const [])
            .whereType<List>()
            .map((fila) => fila.map((v) => v == null ? '' : '$v').toList())
            .toList(),
        truncated: json['truncated'] == true,
      );
}

/// Qué puede reportar quien pregunta. Es lo primero que pide la pantalla.
Future<CatalogoDeReportes> listarConjuntos(ApiClient client) async {
  final data = await client.get('/reporting/datasets/');
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  return CatalogoDeReportes(
    datasets: (mapa['datasets'] as List? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ConjuntoDeDatos.fromJson)
        .toList(),
    formats: (mapa['formats'] as List? ?? const [])
        .whereType<String>()
        .toList(),
    maxRows: mapa['max_rows'] as int? ?? 0,
  );
}

/// La vista previa: pocas filas, sin generar ningún archivo.
Future<ResultadoDeReporte> ejecutarReporte(
  ApiClient client, {
  required String dataset,
  required List<String> columns,
  List<CriterioDeFiltro> filters = const [],
  List<String> orderBy = const [],
  int previewRows = 50,
}) async {
  final data = await client.post(
    '/reporting/run/',
    body: {
      'dataset': dataset,
      'columns': columns,
      'filters': [for (final f in filters) f.toJson()],
      'order_by': orderBy,
      'format': 'json',
      'preview_rows': previewRows,
    },
  );
  if (data is! Map<String, dynamic>) {
    throw const FormatException('El reporte volvió sin formato.');
  }
  return ResultadoDeReporte.fromJson(data);
}

/// Lo que contesta el backend cuando el reporte se manda por correo.
class EnvioDeReporte {
  const EnvioDeReporte({
    required this.recipients,
    required this.filename,
    required this.rows,
    required this.truncated,
  });

  /// Las direcciones a las que efectivamente salió.
  final List<String> recipients;
  final String filename;
  final int rows;
  final bool truncated;
}

/// Genera el archivo en el servidor y lo manda por correo.
///
/// **No descarga nada**: ver el encabezado del módulo.
Future<EnvioDeReporte> enviarReportePorCorreo(
  ApiClient client, {
  required String dataset,
  required List<String> columns,
  required String format,
  required List<String> recipients,
  List<CriterioDeFiltro> filters = const [],
  List<String> orderBy = const [],
  String title = '',
}) async {
  final data = await client.post(
    '/reporting/run/',
    body: {
      'dataset': dataset,
      'columns': columns,
      'filters': [for (final f in filters) f.toJson()],
      'order_by': orderBy,
      'format': format,
      'recipients': recipients,
      if (title.isNotEmpty) 'title': title,
    },
  );
  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  return EnvioDeReporte(
    recipients: (mapa['recipients'] as List? ?? recipients)
        .whereType<String>()
        .toList(),
    filename: mapa['filename'] as String? ?? '',
    rows: mapa['rows'] as int? ?? 0,
    truncated: mapa['truncated'] == true,
  );
}
