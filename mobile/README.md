# Aplicación móvil — Flutter

La cara del paciente. **Web para el personal, móvil para el paciente**: esa
división es la que sostiene la arquitectura del proyecto (Capítulo 2 del
documento), y por eso acá no hay pantallas de administración.

La instalación del entorno está en
[`docs/entorno/setup-movil.md`](../docs/entorno/setup-movil.md).

---

## Correrla

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://192.168.0.15:8000/api
```

**El equipo trabaja con el celular por USB, sin emulador** (decisión registrada
en [`docs/entorno/setup-movil.md`](../docs/entorno/setup-movil.md)). Eso tiene
una consecuencia que hay que tener presente: para el teléfono, `localhost` es
el propio teléfono, así que la API va por la **IP de tu máquina en la red
local** (`ipconfig` en Windows), y Django tiene que escuchar fuera de
localhost:

```bash
python manage.py runserver 0.0.0.0:8000
```

El teléfono y la computadora tienen que estar en la misma red. Si el firewall
de Windows pregunta, hay que permitir Python en redes privadas.

Para comprobar el shell sin depender del teléfono alcanza con el navegador de
la propia máquina, y ahí sí vale `localhost`:

```bash
flutter run -d chrome
```

### Pruebas

```bash
flutter test        # no necesita emulador ni dispositivo
flutter analyze
```

---

## Qué hay y qué falta

El shell es el andamiaje, no una pantalla. Lo que resuelve, resuelto una sola
vez para las ocho superficies móviles del sprint:

| Pieza | Dónde | Qué hace |
|---|---|---|
| Cliente HTTP | `core/api/client.dart` | Encabezados `Authorization` y `X-Organization`, errores con código, reintento tras renovar |
| Errores | `core/api/errors.dart` | `ApiError`, espejo del `ErrorApi` del frontend web |
| Sesión | `core/session/session.dart` | Estado, renovación automática, cierre |
| Almacenamiento | `core/session/token_storage.dart` | Tokens en el Keystore / Keychain, no en `SharedPreferences` |
| Lectura del JWT | `core/session/jwt.dart` | El `exp`, para renovar antes de que venza |
| Rutas | `core/router/app_router.dart` | Redirección según la sesión |
| Tema | `core/theme/theme.dart` | La paleta del frontend web |

**Las pantallas todavía no existen.** Cada historia agrega la suya:

| Historia | Carpeta | Responsable |
|---|---|---|
| US-02 — Inicio y cierre de sesión | `lib/features/auth/` | Karen |
| US-01 — Registro de paciente | `lib/features/signup/` | Alexander |
| US-03 — Recuperación de contraseña | `lib/features/auth/` | Karen |
| US-05 — Perfil y cambio de contraseña | `lib/features/profile/` | Michael |
| US-07 — Pacientes dependientes | `lib/features/dependents/` | SM |
| US-08 — Antecedentes | `lib/features/history/` | SM |
| US-15 — Disponibilidad consolidada | `lib/features/availability/` | Alexander |
| US-16 — Búsqueda de profesionales | `lib/features/search/` | Alexander |

Las carpetas son las que fija
[`docs/sprints/sprint-1/reparto.md`](../docs/sprints/sprint-1/reparto.md).

---

## Cómo se agrega una pantalla

**1. La ruta**, en su propio bloque de `core/router/app_router.dart` — la misma
regla del archivo compartido que el backend aplica en `accounts/urls.py`: tocá
tu bloque y no la línea de al lado.

**2. La pantalla**, en `lib/features/<lo tuyo>/`.

**3. Las llamadas a la API**, con el cliente del shell:

```dart
final client = ApiClient(auth: SessionScope.of(context));
final data = await client.get('/catalog/branches/');
```

No armes tu propio `http.Client`: el del shell es el que pone el token, el que
manda el encabezado de organización y el que renueva antes de que venza.

**4. Los errores**, comparando contra el código y nunca contra el texto:

```dart
try {
  await client.post('/accounts/login/', body: {...}, authenticated: false);
} on ApiError catch (e) {
  if (e.code == 'cuenta_bloqueada') { /* RNF-07: mostrá hasta cuándo */ }
}
```

---

## Tres cosas que no son obvias

**El encabezado de organización va en todas las peticiones.** Cuando la
petición está autenticada, el backend saca el inquilino del claim del token y
el encabezado sobra. Pero las que no lo están —ingresar, registrarse, recuperar
la contraseña— lo necesitan sí o sí: sin él, toda consulta protegida por RLS
devuelve **cero filas**. Mandarlo siempre evita tener que acordarse de cuál
es cuál.

**El refresco se rota.** El backend tiene `ROTATE_REFRESH_TOKENS`, así que cada
renovación devuelve un refresco nuevo y manda el anterior a la lista negra.
`TokenStorage.saveTokens` guarda los dos; quedarse con el viejo deja la sesión
muerta en la renovación siguiente.

**La renovación es perezosa, no por temporizador.** Se mira el `exp` antes de
cada petición. Un `Timer` cada 25 minutos parece más prolijo, pero no sobrevive
a que el sistema operativo suspenda la aplicación —que es lo que pasa cuando el
teléfono queda en el bolsillo—, y al volver la primera petición falla igual.

---

## Lo que el shell **no** decide

**La gestión de estado.** `SessionScope` es un `InheritedNotifier` de Flutter,
sin ningún paquete. Elegir entre Provider, Riverpod o Bloc es una decisión del
equipo, no algo que deba quedar decidido de hecho por el andamiaje. Cuando se
acuerde una, se cambia `core/session/session_scope.dart` y nada más.

**La marca por organización.** `Organization` ya guarda `primary_color` y
`secondary_color` (US-43), pero el tema usa la paleta fija. Cuando haga falta,
se construye el `ColorScheme` con esos valores; el único lugar donde tocarlo es
`Marca.primary`.
