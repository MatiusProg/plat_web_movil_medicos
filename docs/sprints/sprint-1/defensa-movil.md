# Defensa del Sprint 1 — MÓVIL

Guía de estudio. **No es un guion para leer en la defensa**: es para aprenderlo
antes. Si estás leyendo esto delante de la ingeniera, ya salió mal.

Verificado sobre `main` el **10/09/2026**: 76 pruebas de Flutter en verde
(`flutter test` en `mobile/`).

---

## 1. El minuto que hay que saberse de memoria

> «La aplicación móvil está hecha en **Flutter** y consume exactamente la misma
> API REST que la web. No hay backend propio del móvil ni lógica de negocio
> duplicada: el teléfono pide, el backend decide.
>
> Tiene **tres caras**, y cuál ve cada persona lo deciden sus **permisos**, no
> una configuración ni el nombre de su rol:
>
> - la del **paciente** — buscar profesionales, ver disponibilidad, personas a
>   cargo, antecedentes;
> - la de quien **administra un centro médico** — agendas, sucursales,
>   especialidades, profesionales, bitácora, usuarios y roles;
> - la del **superadministrador de plataforma** — organizaciones, planes,
>   suscripciones y métricas.
>
> El Sprint 1 entregó el **shell** —el proyecto, el cliente HTTP, el
> almacenamiento seguro del token y la renovación automática— y las pantallas
> que cuelgan de él.»

---

## 2. La arquitectura del móvil, en una imagen mental

```
Pantallas          lib/features/<área>/…_screen.dart
     │
Servicios de API   lib/features/<área>/…_api.dart
     │
ApiClient          lib/core/api/client.dart      ← una sola puerta de salida
     │  pone Authorization: Bearer <JWT>
     │      y X-Organization: <slug>
     ▼
La misma API REST que consume la web
```

Al costado, transversal a todo:

```
Session          lib/core/session/session.dart        quién está dentro, renovación
TokenStorage     lib/core/session/token_storage.dart  Keystore de Android
GoRouter         lib/core/router/app_router.dart      rutas y redirección
ConPermiso       lib/core/session/org_gate.dart       guarda por permiso
SoloPacientes    lib/core/session/patient_gate.dart   guarda de la cara del paciente
```

**El menú se arma por permisos, no por rol.** Cada organización define sus
propios roles (US-04), así que la aplicación **no sabe** que existe "el
recepcionista": pregunta `user.can("scheduling.schedule.read")` y muestra
Agendas si la respuesta es sí. Un recepcionista con agendas pero sin bitácora ve
exactamente eso. Cada ruta va además detrás de `ConPermiso`, para que no alcance
con escribir la URL a mano.

**Las tres decisiones del shell que hay que poder defender:**

| Decisión | Por qué |
|---|---|
| El token va en **almacenamiento seguro**, no en `SharedPreferences` | `SharedPreferences` deja un XML legible con root o con el respaldo activado, y lo que se guarda son tokens que dan acceso a una historia clínica. `flutter_secure_storage` usa el **Keystore** de Android. |
| La renovación es **perezosa**, no por temporizador | Un `Timer` cada 25 minutos no sobrevive a que el sistema suspenda la aplicación —el teléfono en el bolsillo—, y al volver la primera petición falla igual. Se mira el vencimiento **antes de cada petición**. |
| La redirección la decide **el router**, no cada pantalla | Una pantalla que comprueba por su cuenta si hay sesión es una pantalla que alguien se va a olvidar de proteger. Es lo mismo que hace `RutaProtegida` en la web. |

---

## 3. Dónde vive cada cosa — `mobile/`

```
mobile/
├── lib/
│   ├── main.dart              punto de entrada; restaura la sesión
│   ├── app.dart               MaterialApp.router + tema
│   ├── core/
│   │   ├── config.dart              API_BASE_URL, márgenes y timeouts
│   │   ├── api/client.dart          el cliente HTTP: encabezados, errores, reintento
│   │   ├── api/errors.dart          ApiError con `code` estable
│   │   ├── session/session.dart     estado de sesión y renovación
│   │   ├── session/token_storage.dart  Keystore / Keychain
│   │   ├── session/jwt.dart         lee `exp` sin verificar la firma
│   │   ├── session/org_gate.dart    `ConPermiso`
│   │   ├── session/patient_gate.dart `SoloPacientes`
│   │   ├── router/app_router.dart   rutas y redirección
│   │   └── widgets/                 cajones laterales, cabecera, tarjetas
│   └── features/
│       ├── auth/           US-02 ingreso · US-01 registro de paciente
│       ├── dependents/     US-07 personas a cargo + selector compartido
│       ├── history/        US-08 antecedentes
│       ├── search/         US-16 especialidades y búsqueda
│       ├── availability/   US-15 disponibilidad consolidada
│       ├── schedules/      US-13/14 agendas y disponibilidad de la organización
│       ├── catalog/        US-11/12 sucursales, especialidades, profesionales
│       ├── audit/          US-06 bitácora
│       ├── users/          US-04 usuarios y roles
│       ├── organization/   panel de la organización
│       ├── organizations/  GES-43 organizaciones (plataforma)
│       ├── plans/          GES-44 planes
│       ├── subscriptions/  GES-44 suscripciones
│       └── metrics/        US-45 panel de plataforma
└── test/                   76 pruebas
```

### Mapa por cara

**Paciente**

| Historia | Pantalla | Ruta |
|---|---|---|
| US-02 Ingreso | `auth/sign_in_screen.dart` | `/sign-in` |
| US-01 Registro | `auth/register_screen.dart` | `/register` |
| US-16 Especialidades / búsqueda | `search/` | `/specialties`, `/search` |
| US-15 Disponibilidad | `availability/availability_screen.dart` | `/professionals/:id/availability` |
| US-07 Personas a cargo | `dependents/` | `/dependents`, `/dependents/new` |
| US-08 Antecedentes | `history/history_screen.dart` | `/history` |

**Organización** — todas cuelgan de `/org` y van detrás de su permiso

| Sección | Permiso que la habilita |
|---|---|
| Agendas | `scheduling.schedule.read` |
| Disponibilidad | `scheduling.slot.read` |
| Sucursales | `catalog.branch.read` |
| Especialidades | `catalog.specialty.read` |
| Profesionales | `catalog.professional.read` |
| Buscar profesionales | `catalog.professional.read` |
| Bitácora | `audit.log.read` |
| Usuarios | `users.user.read` |
| Roles y permisos | `users.role.read` |

**Plataforma** — organizaciones, planes, suscripciones y métricas (`/platform/…`).

---

## 4. Recorrido de la demo

**Se prueba en un celular real conectado por USB, sin emulador.** Para el
teléfono, `localhost` es el propio teléfono, así que hay que pasarle la IP de la
máquina en la red local:

```bash
python manage.py runserver 0.0.0.0:8000
flutter run --dart-define=API_BASE_URL=http://192.168.0.15:8000/api
```

Plan B si la red del aula no coopera: apuntar al backend desplegado
(`https://web-production-872fa.up.railway.app/api`). **Probarlo antes.**

1. **Ingreso** — slug, correo y contraseña. El slug queda prellenado de la
   última sesión.
2. **Un error a propósito** — contraseña mal: cartel rojo, la contraseña se
   limpia y el foco vuelve ahí. Insistiendo, **cuenta bloqueada (RNF-07)** con
   cuenta regresiva en vivo y el formulario trabado.
3. **Entrar como paciente** — buscar por especialidad, ver el **próximo espacio
   disponible** de cada profesional, abrir uno y mostrar sus huecos en **todas**
   sus sucursales. *Ese es el caso que da nombre al proyecto.*
4. **Personas a cargo** (US-07) — alta de un familiar. *Decir:* se le crea
   **ficha demográfica sin cuenta de acceso**.
5. **Antecedentes** (US-08) — registrar una alergia con severidad y, con el
   selector, cambiar a la persona a cargo.
6. **Salir y entrar como administrador de la organización** — el panel muestra
   sólo las secciones que sus permisos habilitan. Entrar a Agendas y cargar una
   regla; entrar a Roles y mostrar los permisos agrupados por módulo.
   *Ese contraste entre las dos sesiones es la mejor demostración de US-04.*
7. **Bitácora** — cerrar mostrando que todo lo anterior dejó asiento.
8. **Cerrar sesión** — el refresco va a la lista negra: esa sesión no se puede
   renovar aunque alguien tuviera el token.

---

## 5. Las preguntas que van a caer

**Si el móvil es del paciente, ¿por qué tiene pantallas de administración?**
Ésta es la pregunta que hay que tener afilada, porque el documento del proyecto
dice *web para el personal, móvil para el paciente*. La respuesta: quien
administra una organización tiene 32 permisos y, hasta la semana pasada,
ninguna pantalla móvil donde usarlos — entraba y leía «esta sección es para
pacientes». Se le dieron **las mismas nueve secciones que ya tiene en la web**,
sin reimplementar nada: Disponibilidad y Buscar profesionales son las pantallas
que ya existían para el paciente, colgadas del menú. La web sigue siendo la
herramienta de trabajo del personal; el móvil ya no lo deja afuera.

**¿Cómo sabe la aplicación qué mostrarle a cada uno?**
Por **permisos**, no por rol. Los roles los define cada organización (US-04), así
que la aplicación no puede tener una lista de roles conocidos. Pregunta
`user.can("modulo.recurso.accion")` y cada ruta va detrás de `ConPermiso`.

**¿El móvil valida los permisos, entonces?**
No, y no debe. Esconder un botón no autoriza nada: sólo evita ofrecer lo que va
a dar 403. La autorización real la hace el backend con `user.has_permission`, y
el aislamiento entre organizaciones lo hace PostgreSQL con RLS.

**¿Dónde guardan el token y por qué ahí?**
En el almacenamiento seguro del sistema —Keystore en Android, Keychain en iOS—
con `flutter_secure_storage`. No en `SharedPreferences`, porque ahí queda en un
XML legible en cualquier teléfono con root. Se guardan tres cosas: el acceso (30
min), el refresco (7 días) y el slug. **Los datos del usuario no se guardan**:
viven en memoria y se piden de nuevo, porque una copia se desactualiza cuando el
administrador cambia un rol.

**¿Cómo maneja la app que el token venza mientras se usa?**
Antes de cada petición autenticada se mira si vence dentro del margen y, si es
así, se renueva. Como el backend **rota** el refresco, hay una sola renovación a
la vez: sin eso, varias peticiones simultáneas lanzarían renovaciones en
paralelo, la primera mandaría el refresco a la lista negra y las demás
fallarían. Si aun así llega un 401, se fuerza una renovación y se reintenta
**una vez**.

**¿Qué cierra la sesión y qué no?**
Sólo un 401 o un refresco rechazado. **No** la cierra la falta de red ni un 500
del servidor: el token sigue siendo válido, lo que falló es otra cosa. Cerrarla
ahí echaría a la gente cada vez que entra a un ascensor.

**¿Por qué el móvil manda `X-Organization` en todas las peticiones?**
Las autenticadas no lo necesitan —el backend resuelve el inquilino desde el
claim del token—, pero las que **no** lo están —ingresar, registrarse— sí: sin
ese encabezado, toda consulta protegida por RLS devuelve cero filas.

**¿Leen el JWT en el cliente? ¿No es inseguro?**
Se lee el `exp` **sin verificar la firma**, y sólo para decidir si conviene
renovar. Ninguna decisión de permisos sale de esos claims: quien decide si un
token sirve es el backend, que tiene la clave.

**¿Por qué distinguen tantos errores en el login?**
Porque de eso depende que la persona sepa qué hacer: credenciales inválidas,
cuenta bloqueada (RNF-07), cuenta inactiva, organización inexistente y sin
conexión son cinco acciones distintas. Se compara contra el **código** del
backend, nunca contra el texto: el texto lo lee una persona y cambia, el código
es el contrato. Los mismos códigos que usa la web.

**¿Qué probaron?**
76 pruebas con `flutter test`: los servicios de API de cada área y las pantallas
con `WidgetTester`, más `shell_test.dart` (lectura del token, decisión de
renovar, traducción de errores) y `defectos_sesion_test.dart`, que cubre
justamente qué cierra la sesión y qué no.

**¿Por qué Flutter?**
Un solo código para Android e iOS. La versión está fijada para los seis
—Flutter 3.47.2— en `docs/entorno/setup-movil.md`: la deriva de versiones
produce errores que parecen de código y no lo son.

---

## 6. Lo que no se entregó — decirlo así, y sin rodeos

| Superficie | Estado |
|---|---|
| US-03 móvil — recuperación de contraseña | **No entregada** |
| US-05 móvil — perfil y cambio de contraseña | Historia sin responsable; pasa al Sprint 2 |

US-03 **sí tiene su mitad web funcionando y desplegada**: el backend está
terminado y probado, falta la pantalla Flutter. Eso acota el faltante y es
cierto.

Cómo decirlo: *«La recuperación de contraseña en el teléfono quedó pendiente: el
backend y la pantalla web están terminados y en producción, falta la pantalla
del móvil. Va al Sprint 2 junto con el perfil, que quedó sin responsable
asignado y se replanificó en el corte del 02/09.»*

**Dónde vive el cierre de sesión.** Según el reparto iba en la pantalla de
perfil (US-05). Como US-05 no se entregó, el botón vive en el menú lateral y en
la pantalla de inicio. Quien tome US-05 lo mueve al perfil. Está anotado en
`docs/sprints/sprint-1/reparto.md`, sección 3.

---

## 7. Errores que no hay que cometer

1. **No decir que el móvil es sólo la cara del paciente.** Era cierto hasta hace
   unos días y ya no lo es: tiene tres caras. La respuesta buena está en la
   primera pregunta de la sección 5.
2. **No decir que el móvil "tiene su propia lógica".** Consume la misma API que
   la web. Toda decisión de negocio y de permisos está del lado del servidor.
3. **No prometer la recuperación de contraseña en el teléfono.** Es la sección 6.
4. **No demostrar sobre `localhost`.** Para el celular, `localhost` es el
   celular. Es el error clásico y se nota en el acto.
5. **Probar la red del aula antes.** Si el teléfono no llega a la máquina sale
   «No se pudo conectar con el servidor» y no hay demo. Tener listo el plan B.
6. **Llevar dos sesiones preparadas** —un paciente y un administrador— con sus
   contraseñas a mano. El contraste entre las dos es media defensa.
7. **Teléfono cargado, pantalla desbloqueada y APK ya instalada.** No compilar
   en vivo.
