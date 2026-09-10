# Defensa del Sprint 1 — WEB

Guía de estudio. **No es un guion para leer en la defensa**: es para aprenderlo
antes. Si estás leyendo esto delante de la ingeniera, ya salió mal.

Verificado sobre `main` el **10/09/2026**: 268 pruebas de backend en verde,
backend y frontend desplegados y respondiendo.

---

## 1. El minuto que hay que saberse de memoria

> «Es una plataforma **multi-inquilino** para centros médicos: un solo
> despliegue atiende a varias organizaciones, y los datos de una **no pueden**
> verse desde otra. La web es la herramienta de trabajo del **personal**
> —administrador, recepcionista, médico—; el paciente entra por la aplicación
> móvil.
>
> El Sprint 1 dejó operativo el **catálogo** —sucursales, especialidades,
> profesionales y agendas— y la **identidad** —roles, permisos y recuperación
> de contraseña—, más la **bitácora de auditoría**. Sobre eso el Sprint 2 puede
> reservar fichas.
>
> El aislamiento no se programa en cada consulta: lo hace cumplir **PostgreSQL
> con Row Level Security**. Aunque alguien se olvide de filtrar, la base
> devuelve cero filas.»

Eso responde el 80 % de "de qué se trata su proyecto".

---

## 2. La arquitectura, en una imagen mental

```
React + TypeScript (Vite)        frontend/src/
        │  fetch con Authorization: Bearer <JWT>
        │       y X-Organization: <slug>
        ▼
Django REST Framework            backend/<app>/
        │  el JWT trae organization_id → se fija app.tenant_id
        ▼
PostgreSQL con RLS               las políticas leen app.tenant_id
```

**Las tres capas de defensa del aislamiento** (esto es lo que distingue al
proyecto; hay que poder decirlo sin dudar):

| # | Capa | Archivo |
|---|---|---|
| 1 | El **token** lleva `organization_id`; sin ese claim no autentica | `backend/accounts/tokens.py` |
| 2 | La **autenticación** fija `app.tenant_id` antes de tocar la base | `backend/accounts/authentication.py` |
| 3 | La **base** filtra con RLS: sin contexto, cero filas | migraciones `*_rls_policies.py` |

**La pregunta trampa:** *¿por qué el contexto no lo pone un middleware?*
→ Porque un middleware corre **antes** de la vista, y la autenticación de DRF
ocurre **dentro** de la vista: ahí `request.user` todavía es anónimo. El
middleware (`backend/tenancy/middleware.py`) sólo resuelve el inquilino por el
encabezado `X-Organization` para las peticiones **sin autenticar** (el login).

---

## 3. Dónde vive cada cosa

### Backend — `backend/`

| App | Qué resuelve | Historias |
|---|---|---|
| `tenancy/` | Organizaciones, planes, suscripciones, contexto de inquilino | GES-43, GES-44, US-45 |
| `accounts/` | Usuarios, login, roles, permisos, contraseñas | US-01, US-02, US-03, US-04 |
| `catalog/` | Sucursales, especialidades, profesionales, búsqueda | US-11, US-12, US-16 |
| `scheduling/` | Agendas, bloqueos, disponibilidad | US-13, US-14, US-15 |
| `patients/` | Dependientes y antecedentes | US-07, US-08 |
| `audit/` | Bitácora de auditoría (sólo lectura) | US-06 |

Archivos que hay que poder nombrar de memoria:

- `backend/config/settings.py` — configuración; `config/urls.py` — el mapa de la API.
- `backend/tenancy/context.py` — `tenant_context()`, `set_context()`. **El corazón del aislamiento.**
- `backend/accounts/authentication.py` — la clase que fija el contexto desde el token.
- `backend/accounts/permissions.py` — `user.has_permission("modulo.recurso.accion")`.
- `backend/tests/` — 268 pruebas, una carpeta por historia (`test_us04.py`, …) más `test_isolation.py`.

### Frontend — `frontend/src/`

| Carpeta | Qué hay |
|---|---|
| `api/` | Una puerta de salida por dominio + `cliente.ts`, que pone `Authorization` y `X-Organization` |
| `paginas/` | Una pantalla por historia |
| `componentes/` | `ArmazonPlataforma` (layout con barra lateral), `Boton`, `Campo`, `Aviso` |
| `sesion/` | `ContextoSesion.tsx` — sesión, token y renovación |
| `rutas/` | `RutaProtegida.tsx` — puerta de las pantallas con sesión |
| `App.tsx` | El mapa de rutas, comentado historia por historia |

### Mapa historia → pantalla → archivos

| Historia | Ruta web | Pantalla | Backend |
|---|---|---|---|
| US-02 Inicio de sesión | `/ingresar` | `paginas/InicioSesion.tsx` | `accounts/views/auth.py` |
| — Reanudar sesión | *(la usa el móvil)* | — | `GET /api/accounts/me/` |
| US-01 Registro paciente | `/registro` | `paginas/RegistroPaciente.tsx` | `accounts/views/registration.py` |
| US-03 Recuperar contraseña | `/recuperar`, `/restablecer` | `RecuperarAcceso.tsx`, `RestablecerContrasena.tsx` | `accounts/services/password_reset.py` |
| US-04 Roles y permisos | `/roles`, `/usuarios` | `Roles.tsx`, `Usuarios.tsx` | `accounts/views/roles.py`, `services/roles.py` |
| US-06 Bitácora | `/bitacora` | `Bitacora.tsx` | `audit/views.py`, `audit/services.py` |
| US-11 Sucursales | `/sucursales` | `Sucursales.tsx` | `catalog/branches.py`, `branch_services.py` |
| US-12 Especialidades / profesionales | `/especialidades`, `/profesionales` | `Especialidades.tsx`, `Profesionales.tsx` | `catalog/us12_views.py`, `us12_services.py` |
| US-13 Agendas | `/agendas` | `Agendas.tsx` | `scheduling/schedules.py` |
| US-14 Bloqueos | `/agendas/bloqueos` | `BloqueosAgenda.tsx` | `scheduling/blocks.py` |
| US-15 Disponibilidad | `/disponibilidad` | `Disponibilidad.tsx` | `scheduling/availability.py` |
| US-16 Búsqueda profesionales | `/buscar-profesionales` | `BuscarProfesionales.tsx` | `catalog/search.py` |
| GES-43 / 44 / 45 | `/organizaciones`, `/planes`, `/suscripciones`, `/panel` | ídem | `tenancy/views/` |

---

## 4. Recorrido de la demo — el orden importa

Cada paso deja armado el siguiente. **Ensayarlo entero al menos una vez.**

1. **`/ingresar`** — entrar con el slug del centro médico, correo y contraseña.
   *Decir:* el correo es único **por organización**, no global; por eso hace
   falta el slug antes de autenticar.
2. **`/roles`** (US-04) — mostrar los cuatro roles plantilla, abrir uno y
   marcar/desmarcar un permiso. Luego **`/usuarios`**: asignar rol a alguien.
   *Decir:* todo el sistema autoriza con `user.has_permission("...")`.
3. **`/sucursales`** (US-11) — alta con horario por día. Intentar desactivar
   una sucursal con fichas futuras: **se rechaza y dice cuáles**.
4. **`/especialidades`** y **`/profesionales`** (US-12) — dar de alta un
   profesional: se crea su cuenta con rol *Médico* **en una sola transacción**,
   y se lo asocia a varias especialidades y varias sucursales.
5. **`/agendas`** (US-13) — cargar una agenda y mostrar el calendario semanal.
   Intentar solapar dos agendas del mismo profesional: **se rechaza**.
6. **`/agendas/bloqueos`** (US-14) — bloquear un rango y ver que los espacios
   dejan de ofrecerse. Levantar el bloqueo: **la agenda vuelve sola**.
7. **`/disponibilidad`** (US-15) — el mismo profesional, sus huecos libres en
   **todas** sus sucursales, etiquetados con la sede.
8. **`/buscar-profesionales`** (US-16) — buscar por nombre sin tildes y filtrar
   por especialidad; cada resultado trae su **próximo espacio disponible**.
9. **`/bitacora`** (US-06) — cerrar mostrando que todo lo anterior dejó asiento:
   quién, qué, sobre qué, cuándo, desde qué IP.

**Antes de la defensa:** entrar a Supabase el día anterior (el plan gratuito se
pausa a los 7 días sin actividad) y comprobar que hay catálogo cargado. Si no,
`python manage.py seed_catalog --organization <slug> --with-schedules`.

- Backend: <https://web-production-872fa.up.railway.app>
- Frontend: <https://platwebmovilmedicos-production-ae19.up.railway.app>

---

## 5. Las preguntas que van a caer

**¿Cómo garantizan que una organización no vea los datos de otra?**
Tres capas: el claim `organization_id` en el JWT, `set_context()` en la
autenticación, y políticas RLS en PostgreSQL con `FORCE ROW LEVEL SECURITY`.
Si el contexto no se fija, la comparación es contra NULL y la consulta devuelve
**cero filas** — falla cerrando, no abriendo. Hay 29 pruebas sólo de eso en
`backend/tests/test_isolation.py`, y corren conectadas como `app_user`, no como
`postgres` (que es superusuario y omitiría las políticas).

**¿Y el móvil no hace también administración?**
Sí, desde hace pocos días: quien administra una organización tiene ahora en el
teléfono las mismas nueve secciones que en la web, porque tenía 32 permisos y
ninguna pantalla móvil donde usarlos. No cambia el argumento: la web sigue
siendo la herramienta de trabajo del personal —es donde se gestiona con teclado
y pantalla grande—, y el móvil no reimplementa nada, consume la misma API. Si
te toca defender web, con esto alcanza; el detalle está en la guía móvil.

**¿Por qué no usan el admin de Django?**
Porque el admin no conoce el contexto de inquilino: un administrador de una
organización vería y editaría los datos de todas. Está explicado en
`backend/config/urls.py`.

**¿Por qué no usan `user.has_perm()` de Django?**
Las tablas de `django.contrib.auth` no llevan `organization_id` ni están
protegidas por RLS: responderían contra los permisos de todas las
organizaciones. Se usa `user.has_permission("modulo.recurso.accion")`, que
consulta `UserRole → RolePermission`.

**¿Cómo manejan las sesiones?**
JWT con `djangorestframework-simplejwt`. Acceso de 30 minutos, refresco de 7
días, con **rotación** y lista negra: al cerrar sesión o cambiar la contraseña,
el refresco se invalida y todas las sesiones abiertas caen.

**¿Por qué la bitácora no tiene POST ni DELETE?**
Es el punto (f) de US-06: no expone verbos de escritura **ni siquiera al
administrador**. Es un `ReadOnlyModelViewSet` y además declara
`http_method_names = ["get", "head", "options"]`. Se escribe **fuera de la
transacción de negocio**: que falle la auditoría no puede tumbar la operación
auditada, y que la operación se deshaga no borra la constancia del intento.

**¿Cómo evitan que el "olvidé mi contraseña" revele qué correos existen?**
La respuesta es **idéntica** exista o no la cuenta, y hace el mismo trabajo
costoso en los dos casos para que el tiempo tampoco lo delate. El token se
guarda **como hash**, dura 30 minutos y se consume al primer uso.

**¿Cómo cumplen el requisito de menos de 3 segundos de US-15?**
Resolviendo el rango en **una consulta de agendas y una de bloqueos**, no una
por día: con tres sucursales y catorce días, el bucle ingenuo serían 42 idas a
la base. La hora de corte se calcula en la zona horaria de **la sucursal**, no
la del servidor.

**¿Por qué la agenda se guarda como regla y no como lista de turnos?**
Porque los espacios se **derivan** de la regla. Guardar cada espacio suelto
haría inmanejable cambiar un horario. Y por eso un bloqueo (US-14) **no toca la
regla**: al levantarlo, la agenda vuelve sola.

**¿Qué probaron?**
268 pruebas automáticas en el backend, todas en verde. Una carpeta por historia
más `test_isolation.py`. Toda historia cierra con pruebas de aislamiento
(RNF-08): un usuario de la organización A no ve ni una fila de la B, comprobado
en ORM **y** en RLS.

**¿Dónde está desplegado?**
Backend y frontend en Railway, base en Supabase. Se desplegó temprano y a
propósito: el primer despliegue siempre falla por cosas del entorno que no se
ven leyendo código.

---

## 6. Lo que no se entregó — decirlo así, y sin rodeos

**US-05 (perfil), US-09 (búsqueda de pacientes) y US-10 (ABM de pacientes)
quedaron sin responsable y pasan al Sprint 2, con su estimación intacta: 16
horas.** Está documentado en el repositorio (`docs/sprints/sprint-1/reparto.md`,
sección 1) y decidido **antes** del cierre del sprint, no después.

Cómo decirlo: *«Tres historias quedaron sin responsable asignado. Se detectó en
el corte del 02/09 que fijamos en el planning, se replanificaron al Sprint 2 y
quedó registrado en el repositorio. No bloquearon a ninguna otra historia del
sprint, que es por lo que el resto pudo cerrar.»*

**US-08 no tiene pantalla web, y es deliberado.** El actor es el paciente o su
titular, y el paciente no usa la web. La mitad web se reduce al endpoint de
lectura (`patients/history/highlights/`) que el módulo de atención consumirá en
el Sprint 3.

---

## 7. Errores que no hay que cometer

1. **No decir "multi-tenant" sin poder explicar RLS.** Es la pregunta que sigue,
   siempre.
2. **No decir que el frontend "protege" las rutas.** `RutaProtegida.tsx` es
   comodidad, no seguridad: cualquiera lo saltea desde la consola. La
   autorización real la hace el backend en cada petición. Decirlo así suma.
3. **No prometer lo que no está.** Si preguntan por perfil de usuario o
   búsqueda de pacientes, es la respuesta de la sección 6.
4. **No improvisar sobre código ajeno.** Si te toca defender algo que no
   escribiste, ubicá el archivo (sección 3), decí qué resuelve y por qué está
   así. La ubicación y el porqué valen más que la línea exacta.
5. **No abrir el admin de Django.** No existe en este proyecto, y hay una razón.
6. **Si algo falla en vivo, no insistir.** Explicar qué debía pasar y seguir con
   el punto siguiente del recorrido.
