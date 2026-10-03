/// Ayudantes para las listas paginadas del backend.
///
/// El backend pagina por defecto con `PageNumberPagination` de 25 filas
/// (`REST_FRAMEWORK` en `backend/config/settings.py`): la respuesta es
/// `{count, next, previous, results}` y la página se pide con `?page=N`. Leer
/// sólo `results` de la primera respuesta —que es lo que hacía casi toda la
/// aplicación— funciona con los datos de prueba y pierde información en
/// cuanto una organización real pasa de 25 usuarios, roles o asignaciones.
///
/// Hay dos maneras de resolverlo, y cada pantalla elige la suya:
///
///   * [todasLasPaginas] para lo que tiene que estar **completo** —un
///     desplegable de profesionales, los roles para asignar, el mapa de
///     asignaciones—: un selector al que le faltan opciones no avisa, la
///     opción simplemente no está.
///   * [unaPagina] para las listas que pueden crecer sin techo, que se
///     muestran con un botón "Cargar más" igual que la bitácora.
library;

import 'client.dart';

/// Una página de resultados, ya desenvuelta.
class Pagina<T> {
  const Pagina({
    required this.results,
    required this.hayMas,
    required this.total,
  });

  final List<T> results;

  /// `next` no nulo: hay otra página después de esta.
  final bool hayMas;

  /// `count` del backend: el total de filas, no las de esta página. Sirve
  /// para mostrar "12 de 80" sin tener que traerlas todas.
  final int total;
}

/// Agrega `page=N` a la ruta, respetando los parámetros que ya traiga.
///
/// La primera página va sin el parámetro: es la misma respuesta y deja las
/// rutas iguales a como eran antes, que es lo que esperan las pruebas.
String rutaDePagina(String path, int page) {
  if (page <= 1) return path;
  final separador = path.contains('?') ? '&' : '?';
  return '$path${separador}page=$page';
}

/// Pide la página [page] de [path] y la convierte con [desdeJson].
///
/// Tolera también un endpoint sin paginar (`pagination_class = None`), que
/// contesta una lista pelada: se toma como una única página completa.
Future<Pagina<T>> unaPagina<T>(
  ApiClient client,
  String path,
  T Function(Map<String, dynamic>) desdeJson, {
  int page = 1,
}) async {
  final data = await client.get(rutaDePagina(path, page));

  if (data is List) {
    final filas = data.whereType<Map<String, dynamic>>().map(desdeJson).toList();
    return Pagina(results: filas, hayMas: false, total: filas.length);
  }

  final mapa = data is Map<String, dynamic> ? data : const <String, dynamic>{};
  final filas = (mapa['results'] as List? ?? const [])
      .whereType<Map<String, dynamic>>()
      .map(desdeJson)
      .toList();
  return Pagina(
    results: filas,
    hayMas: mapa['next'] != null,
    total: mapa['count'] as int? ?? filas.length,
  );
}

/// Tope de páginas de [todasLasPaginas]: 200 × 25 son 5000 filas.
///
/// No es un límite de negocio sino un seguro: si un backend mal configurado
/// devolviera siempre `next`, la pantalla se quedaría pidiendo para siempre.
const int maximoDePaginas = 200;

/// Recorre todas las páginas de [path] y devuelve las filas juntas.
///
/// Se avanza con `page=N` y no siguiendo la URL de `next`: esa URL la arma el
/// backend con el host que ve él, y detrás del proxy de Railway sale con
/// `http://` y el dominio interno. El número de página, en cambio, siempre
/// sirve con la base que ya usa el cliente.
///
/// Las páginas se piden en orden y no en paralelo: hasta no ver la primera no
/// se sabe cuántas hay, y para las listas de una organización son pocas.
Future<List<T>> todasLasPaginas<T>(
  ApiClient client,
  String path,
  T Function(Map<String, dynamic>) desdeJson,
) async {
  final todas = <T>[];
  for (var page = 1; page <= maximoDePaginas; page++) {
    final pagina = await unaPagina(client, path, desdeJson, page: page);
    todas.addAll(pagina.results);
    if (!pagina.hayMas) break;
  }
  return todas;
}
