/// Cliente HTTP de la aplicación móvil.
///
/// Una sola puerta de salida hacia el backend, igual que `api/cliente.ts` en el
/// frontend web, para que tres cosas estén resueltas en un lugar y no repartidas
/// por cada pantalla:
///
///   1. el encabezado `Authorization` con el token vigente,
///   2. el encabezado `X-Organization`, que es como el backend resuelve el
///      inquilino en las peticiones sin autenticar,
///   3. la traducción de la respuesta de error a un [ApiError] con código.
///
/// **Por qué el encabezado de organización va en todas las peticiones y no sólo
/// en el login.** El backend fija el contexto de inquilino desde el claim del
/// token cuando la petición viene autenticada, así que ahí el encabezado sobra;
/// pero las que no lo están —ingresar, registrarse, recuperar la contraseña— lo
/// necesitan sí o sí: sin él, toda consulta protegida por RLS devuelve cero
/// filas. Mandarlo siempre evita tener que acordarse de cuál es cuál.
///
/// **La renovación es perezosa y no por temporizador.** Antes de cada petición
/// autenticada se mira si el token de acceso vence dentro del margen y, si es
/// así, se renueva. Un `Timer` cada 25 minutos parece más prolijo pero no
/// sobrevive a que el sistema operativo suspenda la aplicación —que es lo que
/// pasa cuando alguien deja el teléfono en el bolsillo—, y al volver la primera
/// petición falla igual.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'errors.dart';

/// Lo que el cliente necesita saber de la sesión, sin depender de ella.
///
/// La implementa `Session`. Está declarada acá y no allá para romper el ciclo:
/// el cliente no conoce a la sesión, sólo este contrato.
abstract class AuthContext {
  /// El token de acceso vigente, renovándolo si está por vencer.
  ///
  /// Con [forceRefresh] se renueva aunque todavía sirva: es lo que se hace
  /// cuando el backend contestó 401 pese a que el token parecía válido.
  Future<String?> accessToken({bool forceRefresh = false});

  /// El slug del inquilino, para el encabezado `X-Organization`.
  String? get organizationSlug;

  /// La sesión no se pudo renovar: hay que volver a la pantalla de ingreso.
  Future<void> onSessionExpired();
}

class ApiClient {
  ApiClient({http.Client? httpClient, this.auth})
      : _http = httpClient ?? http.Client();

  final http.Client _http;

  /// `null` en el cliente que usa la propia sesión para renovar: si ese
  /// tuviera contexto, renovar dispararía otra renovación.
  final AuthContext? auth;

  Future<dynamic> get(String path, {bool authenticated = true}) =>
      send('GET', path, authenticated: authenticated);

  Future<dynamic> post(
    String path, {
    Object? body,
    bool authenticated = true,
  }) =>
      send('POST', path, body: body, authenticated: authenticated);

  Future<dynamic> put(String path, {Object? body}) =>
      send('PUT', path, body: body);

  Future<dynamic> patch(String path, {Object? body}) =>
      send('PATCH', path, body: body);

  Future<dynamic> delete(String path) => send('DELETE', path);

  /// Manda la petición y devuelve el JSON ya decodificado.
  ///
  /// Lanza [ApiError] con el código del backend si la respuesta no es exitosa,
  /// y `ApiError.offline` si la petición no llegó a salir.
  Future<dynamic> send(
    String method,
    String path, {
    Object? body,
    bool authenticated = true,
    bool retrying = false,
  }) async {
    final request = http.Request(method, Uri.parse('${Config.apiBaseUrl}$path'))
      ..headers['Accept'] = 'application/json';

    if (body != null) {
      request.headers['Content-Type'] = 'application/json';
      request.body = jsonEncode(body);
    }

    final slug = auth?.organizationSlug;
    if (slug != null && slug.isNotEmpty) {
      request.headers['X-Organization'] = slug;
    }

    if (authenticated && auth != null) {
      final token = await auth!.accessToken(forceRefresh: retrying);
      if (token != null) {
        request.headers['Authorization'] = 'Bearer $token';
      }
    }

    http.Response response;
    try {
      final streamed = await _http.send(request).timeout(Config.timeout);
      response = await http.Response.fromStream(streamed);
    } on TimeoutException {
      throw ApiError.offline;
    } on SocketException {
      throw ApiError.offline;
    } on http.ClientException {
      throw ApiError.offline;
    }

    // 401 con un token que creíamos bueno: puede ser que el reloj del teléfono
    // esté corrido, o que el token se invalidara del otro lado —al cambiar la
    // contraseña, por ejemplo (US-03)—. Se renueva a la fuerza y se reintenta
    // UNA vez; si vuelve a fallar, la sesión se terminó de verdad.
    if (response.statusCode == 401 && authenticated && auth != null) {
      if (!retrying) {
        return send(
          method,
          path,
          body: body,
          authenticated: authenticated,
          retrying: true,
        );
      }
      await auth!.onSessionExpired();
    }

    if (response.statusCode == 204 || response.body.isEmpty) {
      if (response.statusCode >= 400) {
        throw ApiError.fromResponse(response.statusCode, null);
      }
      return null;
    }

    final decoded = _decode(response);

    if (response.statusCode >= 400) {
      throw ApiError.fromResponse(response.statusCode, decoded);
    }

    return decoded;
  }

  Object? _decode(http.Response response) {
    final type = response.headers['content-type'] ?? '';
    if (!type.contains('application/json')) return null;
    try {
      // `bodyBytes` y no `body`: `body` adivina la codificación por el
      // encabezado y cae en latin-1 si no lo encuentra, que es como aparecen
      // los acentos rotos en los mensajes del backend.
      return jsonDecode(utf8.decode(response.bodyBytes));
    } catch (_) {
      return null;
    }
  }

  void close() => _http.close();
}
