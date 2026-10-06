/// Característica general 6 — Copias de seguridad, del lado del móvil.
///
///     GET  /api/backups/policy/                  regla del plan y copias automáticas
///     POST /api/backups/create/                  genera la copia (la devuelve entera)
///     GET  /api/backups/records/                 historial
///     GET  /api/backups/records/<id>/download/   baja una copia automática guardada
///     POST /api/backups/inspect/                 qué trae una copia, sin escribir nada
///     POST /api/backups/restore/                 reemplaza los datos (con confirmación)
///
/// **El teléfono restaura desde el historial, no desde un archivo.** Las copias
/// automáticas quedan guardadas —cifradas— en el servidor, así que restaurar
/// es mandar su `record`: no hace falta bajar a la memoria del teléfono todos
/// los datos de la organización en claro para volver a subirlos, ni un
/// selector de archivos. Restaurar desde un archivo propio sigue en la web.
library;

import 'dart:convert';
import 'dart:io';

import '../../core/api/client.dart';
import '../../core/api/paginacion.dart';

DateTime? _fecha(Object? valor) =>
    valor is String ? DateTime.tryParse(valor)?.toLocal() : null;

/// Las copias automáticas que hace el sistema solo, según el plan.
class CopiasAutomaticas {
  const CopiasAutomaticas({
    required this.enabled,
    required this.intervalHours,
    required this.retention,
    required this.lastAt,
    required this.nextAt,
    required this.description,
  });

  final bool enabled;
  final int? intervalHours;

  /// Cuántas conserva el plan. Las más viejas se borran; el registro queda.
  final int retention;
  final DateTime? lastAt;
  final DateTime? nextAt;
  final String description;

  factory CopiasAutomaticas.fromJson(Map<String, dynamic> json) =>
      CopiasAutomaticas(
        enabled: json['enabled'] == true,
        intervalHours: json['interval_hours'] as int?,
        retention: json['retention'] as int? ?? 0,
        lastAt: _fecha(json['last_at']),
        nextAt: _fecha(json['next_at']),
        description: json['description'] as String? ?? '',
      );
}

/// Qué permite el plan y cuándo se puede generar la próxima copia manual.
class PoliticaDeRespaldo {
  const PoliticaDeRespaldo({
    required this.planCode,
    required this.planName,
    required this.description,
    required this.allowedNow,
    required this.lastBackupAt,
    required this.nextAvailableAt,
    required this.automaticas,
  });

  final String? planCode;
  final String? planName;
  final String description;
  final bool allowedNow;
  final DateTime? lastBackupAt;
  final DateTime? nextAvailableAt;
  final CopiasAutomaticas? automaticas;

  factory PoliticaDeRespaldo.fromJson(Map<String, dynamic> json) =>
      PoliticaDeRespaldo(
        planCode: json['plan_code'] as String?,
        planName: json['plan_name'] as String?,
        description: json['description'] as String? ?? '',
        allowedNow: json['allowed_now'] == true,
        lastBackupAt: _fecha(json['last_backup_at']),
        nextAvailableAt: _fecha(json['next_available_at']),
        automaticas: json['automatic'] is Map<String, dynamic>
            ? CopiasAutomaticas.fromJson(
                json['automatic'] as Map<String, dynamic>,
              )
            : null,
      );
}

/// Una fila del historial: una copia (manual o automática) o una restauración.
class RegistroDeRespaldo {
  const RegistroDeRespaldo({
    required this.id,
    required this.kind,
    required this.kindLabel,
    required this.trigger,
    required this.triggerLabel,
    required this.downloadable,
    required this.filename,
    required this.sizeBytes,
    required this.totalRows,
    required this.performedBy,
    required this.createdAt,
  });

  final String id;

  /// `backup` o `restore`.
  final String kind;
  final String kindLabel;

  /// `manual` o `automatic`.
  final String trigger;
  final String triggerLabel;

  /// Si todavía se conserva en el servidor: sólo las automáticas dentro de la
  /// retención del plan. Es lo que habilita Descargar y Restaurar.
  final bool downloadable;
  final String filename;
  final int sizeBytes;
  final int totalRows;
  final String? performedBy;
  final DateTime? createdAt;

  bool get esCopia => kind == 'backup';
  bool get esAutomatica => trigger == 'automatic';

  factory RegistroDeRespaldo.fromJson(Map<String, dynamic> json) =>
      RegistroDeRespaldo(
        id: '${json['id'] ?? ''}',
        kind: json['kind'] as String? ?? '',
        kindLabel: json['kind_label'] as String? ?? '',
        trigger: json['trigger'] as String? ?? 'manual',
        triggerLabel: json['trigger_label'] as String? ?? '',
        downloadable: json['downloadable'] == true,
        filename: json['filename'] as String? ?? '',
        sizeBytes: json['size_bytes'] as int? ?? 0,
        totalRows: json['total_rows'] as int? ?? 0,
        performedBy: json['performed_by_email'] as String?,
        createdAt: _fecha(json['created_at']),
      );
}

/// Lo que trae una copia, antes de restaurarla.
class InspeccionDeRespaldo {
  const InspeccionDeRespaldo({
    required this.organizationName,
    required this.organizationSlug,
    required this.generatedAt,
    required this.counts,
    required this.labels,
    required this.belongsToMyOrganization,
  });

  final String organizationName;

  /// Lo que hay que escribir para confirmar, igual que en la web.
  final String organizationSlug;
  final DateTime? generatedAt;
  final Map<String, int> counts;
  final Map<String, String> labels;
  final bool belongsToMyOrganization;

  /// Las tablas con filas, con su nombre legible.
  List<MapEntry<String, int>> get conFilas => [
    for (final e in counts.entries)
      if (e.value > 0) MapEntry(labels[e.key] ?? e.key, e.value),
  ];

  factory InspeccionDeRespaldo.fromJson(Map<String, dynamic> json) {
    final org = json['organization'] is Map
        ? json['organization'] as Map
        : const {};
    return InspeccionDeRespaldo(
      organizationName: '${org['name'] ?? ''}',
      organizationSlug: '${org['slug'] ?? ''}',
      generatedAt: _fecha(json['generated_at']),
      counts: {
        for (final e in (json['counts'] as Map? ?? const {}).entries)
          '${e.key}': e.value is int ? e.value as int : 0,
      },
      labels: {
        for (final e in (json['labels'] as Map? ?? const {}).entries)
          '${e.key}': '${e.value}',
      },
      belongsToMyOrganization: json['belongs_to_my_organization'] == true,
    );
  }
}

/// Una copia ya bajada: el documento y con qué nombre guardarlo.
class CopiaDescargada {
  const CopiaDescargada({required this.nombre, required this.contenido});

  final String nombre;
  final Map<String, dynamic> contenido;

  /// El archivo como lo baja la web: JSON con sangría y acentos de verdad. La
  /// suma de verificación es del contenido, no del formato, así que el archivo
  /// se puede restaurar después desde la web igual.
  List<int> get bytes =>
      utf8.encode(const JsonEncoder.withIndent('  ').convert(contenido));
}

Future<PoliticaDeRespaldo> verPolitica(ApiClient client) async {
  final data = await client.get('/backups/policy/');
  return PoliticaDeRespaldo.fromJson(
    data is Map<String, dynamic> ? data : const {},
  );
}

Future<Pagina<RegistroDeRespaldo>> verHistorial(
  ApiClient client, {
  int page = 1,
}) => unaPagina(
  client,
  '/backups/records/',
  RegistroDeRespaldo.fromJson,
  page: page,
);

/// Genera la copia manual. El backend la devuelve entera en el cuerpo.
Future<CopiaDescargada> generarCopia(ApiClient client) async {
  final data = await client.post('/backups/create/');
  if (data is! Map<String, dynamic>) {
    throw const FormatException('La copia volvió sin formato.');
  }
  return CopiaDescargada(nombre: nombreDeCopia(data), contenido: data);
}

/// Baja una copia automática guardada en el servidor.
Future<CopiaDescargada> descargarCopia(
  ApiClient client,
  RegistroDeRespaldo registro,
) async {
  final data = await client.get('/backups/records/${registro.id}/download/');
  if (data is! Map<String, dynamic>) {
    throw const FormatException('La copia volvió sin formato.');
  }
  return CopiaDescargada(
    nombre: registro.filename.isNotEmpty
        ? registro.filename
        : nombreDeCopia(data),
    contenido: data,
  );
}

Future<InspeccionDeRespaldo> inspeccionarCopia(
  ApiClient client,
  String recordId,
) async {
  final data = await client.post(
    '/backups/inspect/',
    body: {'record': recordId},
  );
  return InspeccionDeRespaldo.fromJson(
    data is Map<String, dynamic> ? data : const {},
  );
}

/// Reemplaza los datos de la organización. `confirm: true` va siempre: la
/// confirmación de la persona ya se pidió en la pantalla.
Future<void> restaurarCopia(ApiClient client, String recordId) async {
  await client.post(
    '/backups/restore/',
    body: {'record': recordId, 'confirm': true},
  );
}

/// `respaldo-kolping-20261006-0300.json`, el mismo nombre que arma el backend
/// (`services.filename`). Se toma la hora tal como la escribió el servidor,
/// que ya es la local del centro médico, sin convertirla.
String nombreDeCopia(Map<String, dynamic> documento) {
  final org = documento['organization'];
  final slug = org is Map && org['slug'] is String && org['slug'] != ''
      ? org['slug'] as String
      : 'organizacion';
  final generado = documento['generated_at'] is String
      ? documento['generated_at'] as String
      : '';
  final m = RegExp(
    r'^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})',
  ).firstMatch(generado);
  final momento = m == null
      ? 'copia'
      : '${m[1]}${m[2]}${m[3]}-${m[4]}${m[5]}';
  return 'respaldo-$slug-$momento.json';
}

// --------------------------------------------------------------------------
//  Guardar el archivo en el teléfono
// --------------------------------------------------------------------------

/// Dónde termina una copia bajada. Se inyecta para probar sin disco.
abstract class GuardadoDeArchivos {
  /// Guarda y devuelve la ruta donde quedó.
  Future<String> guardar(String nombre, List<int> bytes);
}

/// La carpeta pública de Descargas, donde la persona la encuentra con el
/// administrador de archivos y la puede mandar a donde quiera.
///
/// Sin dependencias ni permisos: desde Android 11 una aplicación puede crear
/// sus propios archivos en `Download/` sin pedir nada. Si el nombre ya existe
/// —una copia del mismo minuto, o de una instalación anterior— se agrega un
/// número en vez de pisarla.
class GuardadoEnDescargas implements GuardadoDeArchivos {
  const GuardadoEnDescargas({this.carpeta = '/storage/emulated/0/Download'});

  final String carpeta;

  @override
  Future<String> guardar(String nombre, List<int> bytes) async {
    final base = nombre.endsWith('.json')
        ? nombre.substring(0, nombre.length - 5)
        : nombre;
    var archivo = File('$carpeta/$base.json');
    for (var n = 2; await archivo.exists(); n++) {
      archivo = File('$carpeta/$base ($n).json');
    }
    try {
      await archivo.writeAsBytes(bytes, flush: true);
    } on FileSystemException {
      throw const FileSystemException(
        'El teléfono no dejó guardar la copia en Descargas. Bajala desde la '
        'plataforma web.',
      );
    }
    return archivo.path;
  }
}
