# Sprint 1 — Reparto de historias y alcance por integrante

**Fechas:** 25/08/26 – 07/09/26 · **Revisión de Sprint:** 08–10/09/26

**Objetivo:** dejar operativo el catálogo del centro médico —sucursales,
especialidades, profesionales y agendas— y completar la gestión de pacientes y
de la propia cuenta, de modo que el Sprint 2 pueda reservar fichas sobre datos
reales.

Este documento es el contrato de trabajo del sprint. Dice quién hace qué, en
qué archivos, de quién depende y para cuándo. Si vas a escribir código —o si le
vas a pedir a una IA que lo escriba por vos— leé primero la sección de tu
nombre y después la sección 5, que son las reglas que rompen el aislamiento
multi-inquilino si se ignoran.

Las historias de usuario detalladas están en `historias-de-usuario.md`. Las
convenciones de código, en `../../convenciones-de-codigo.md`.

---

## 1. Reparto

| Integrante | Historias | Web | Móvil | Horas |
|---|---|---|---|---|
| Ortega Mancilla, Karen Paola | US-04, US-03 | US-04, US-03 | US-02 (deuda S0), US-03 | **20** |
| Mamani Samurio, Michael Alexander | US-05, US-09, US-10 | US-05, US-09, US-10 | US-05 | **16** |
| Hurtado Castro, Luis Mateo *(SM)* | US-06, US-07, US-08 | US-06, endpoint de US-08 | US-07, US-08 | **26** |
| Iporo Chulque, José Daniel | US-11, US-12 | US-11, US-12 | — | **16** |
| Aguayo Quiroz, Luis Miguel | US-13, US-14 | US-13, US-14 | — | **22** |
| Osinaga Blanco, Alexander *(PO)* | Shell Flutter, US-15, US-16 | US-15, US-16 | US-01 (deuda S0), US-15, US-16 | **26** |

**Total comprometido: 126 horas** · 6 integrantes · 21 h por integrante.
La sección 7 explica de dónde salen esas horas si ninguna historia cambió.

**14 historias:** las 13 del Sprint 1 más US-04, que se arrastra del Sprint 0.
US-04 no se redacta como historia todavía; se trabaja con lo que dice el
Product Backlog y se documenta al terminarla.

---

## 2. Qué le toca a cada uno

### Karen Ortega — *identidad* — 20 h

Queda dueña de la identidad completa: quién sos, cómo entrás, cómo recuperás el
acceso y qué podés hacer. Es la continuación directa de US-02, que ella escribió
en el Sprint 0.

**US-04 — Crear y asignar roles · 10 h · WEB · arrastre del Sprint 0 (T-06)**

ABM de roles dentro de la organización, edición de sus permisos y asignación de
rol a los usuarios. Las cuatro plantillas del sistema —Administrador de
Organización, Médico, Recepcionista y Paciente— ya se copian dentro del
inquilino cuando US-43 da de alta la organización; acá se las hace editables.

> **Criterio de aceptación que no está en el Product Backlog y hay que cumplir
> igual:** la plantilla del rol *Paciente* debe incluir los permisos de lectura
> del catálogo —`catalog.branch.read`, `catalog.specialty.read`,
> `catalog.professional.read` y `scheduling.slot.read`—. Sin ellos la aplicación
> móvil no puede listar sucursales ni buscar profesionales, y el Sprint 2 no
> puede reservar. Se descubre tarde y obliga a reabrir tres historias ya
> cerradas.

**US-03 — Recuperación de contraseña · 6 h · WEB + MÓVIL**

Reutiliza la lista negra de tokens de refresco que ella misma construyó en
US-02: el punto (f) de la historia —invalidar todas las sesiones abiertas al
cambiar la contraseña— es esa lista. Token de un solo uso, guardado como hash,
30 minutos de vigencia, y respuesta idéntica en contenido y en tiempo exista o
no la cuenta.

**US-02 móvil — Inicio y cierre de sesión · 4 h · deuda del Sprint 0**

La pantalla de ingreso en Flutter: campo de organización, correo y contraseña,
mensajes distintos por tipo de error, aviso del bloqueo temporal, y cierre de
sesión que invalida el refresco. Se monta sobre el shell de Alexander, así que
no arranca antes del 30/08.

**Archivos:** `accounts/roles.py`, `accounts/permissions.py`,
`accounts/password_reset.py`, `accounts/passwords.py`, bloque propio en
`accounts/urls.py`. En móvil, `mobile/lib/features/auth/`.

**Depende de:** el shell de Flutter (Alexander) para la parte móvil.

**Dependen de ella:** las trece historias restantes. US-04 libera
`has_permission`; hasta que exista, todos autorizan contra permisos que nadie
puede administrar.

---

### Michael Mamani — *perfil y padrón de pacientes* — 16 h

Carga deliberadamente contenida y **sin nada que bloquee a nadie más**: US-09 es
*Must have*, pero quien la consume es la recepcionista en el Sprint 2, no una
historia de este sprint.

**US-05 — Edición de perfil · 4 h · WEB + MÓVIL**

Consulta y edición del propio perfil, resuelto siempre desde el token y nunca
desde un identificador que mande el cliente. Cambio de contraseña acreditando la
actual —y sin cerrar la sesión en curso, a diferencia de US-03—. Documento, rol,
organización y estado de la cuenta **no** son editables por el usuario. Es la
historia de referencia de la escala de estimación (apartado 1.2.6).

**US-09 — Búsqueda de pacientes · 6 h · WEB**

Búsqueda por documento (exacta) y por nombre o apellido (parcial, sin distinguir
mayúsculas ni tildes), en menos de 2 segundos con 10.000 registros (RNF-01). Eso
obliga a un índice de texto sobre el nombre normalizado: sin él la búsqueda
parcial degrada linealmente y el requisito no se cumple. El conjunto de prueba
es **sintético**; el repositorio es público y no admite datos de personas
reales.

**US-10 — ABM de pacientes · 6 h · WEB**

Corrección de datos demográficos, alta manual desde ventanilla, baja **lógica y
nunca física**, y fusión de duplicados reasignando fichas, antecedentes y
atenciones antes de inactivar el registro absorbido. Cada corrección, baja y
fusión va a la bitácora con el valor anterior y el nuevo.

**Archivos:** `accounts/profile.py`, `patients/search.py`,
`patients/admin_ops.py`, bloques propios en los `urls.py` de cada app. En móvil,
`mobile/lib/features/profile/`.

**Depende de:** US-04 (permisos), `accounts/passwords.py` de Karen para la
política de contraseñas, US-06 (bitácora) para el punto (e) de US-10.

**Dependen de él:** nadie, dentro de este sprint.

**Corte por fecha.** Si US-05 no está mergeada el 02/09, no se le suma trabajo
nuevo y US-09 y US-10 se replanifican con el equipo. Acordado en el planning.

---

### Luis Mateo Hurtado *(Scrum Master)* — *auditoría y pacientes a cargo* — 26 h

**US-06 — Bitácora de auditoría · 10 h · WEB**

App nueva `audit`, bajo `/api/audit/`. Registro automático de accesos a historia
clínica, anulaciones de fichas, movimientos de pago, alta/baja/cambio de rol de
usuarios y restablecimientos de contraseña. Cada asiento guarda quién, qué,
sobre qué recurso, cuándo, desde qué IP y con qué agente. Tres decisiones que no
son negociables: escritura **fuera de la transacción de negocio** —que falle la
auditoría no puede tumbar la operación auditada—, clave primaria UUID generada
en Python y no `bigserial`, y **sin verbos de escritura expuestos**, ni siquiera
al administrador.

Es transversal: US-03 (d), US-08 (g) y US-10 (e) escriben en ella. Tiene que
estar recibiendo asientos el **01/09** o los otros tres la stubbean y hay que
rehacer.

**US-07 — Pacientes dependientes · 10 h · SÓLO MÓVIL**

Alta de familiares a cargo con su parentesco, creando **ficha demográfica sin
cuenta de acceso**: el dependiente es un paciente del catálogo, no un usuario
que inicia sesión. Esa distinción es la que hace posible el caso. Incluye el
selector *"¿para quién es esta ficha?"*, que es un **widget compartido**: lo
consume US-08 en este sprint y la reserva en el Sprint 2. Publicarlo con esa
intención, no como parte privada de la pantalla.

**US-08 — Antecedentes del paciente · 6 h · MÓVIL + endpoint web**

Alergias con severidad, condiciones crónicas y medicación habitual, declarados
por el paciente y marcados como tales —no son diagnóstico clínico—. Se registran
sobre uno mismo o sobre un dependiente, con el selector de US-07.

> **Cambio de alcance respecto del documento.** El documento marca US-08 como
> WEB/MÓVIL, pero el actor es el paciente o su titular, y el paciente no usa la
> aplicación web. La mitad web se reduce al **endpoint de lectura** que el
> módulo de atención consumirá en el Sprint 3 para mostrar los antecedentes
> destacados al abrir la consulta. No se construye pantalla web.

**Además, como SM:** abrir `config/urls.py` **una sola vez**, en un commit, al
inicio del sprint, para incluir `audit` y `scheduling`. El archivo está cerrado
para todos los demás.

**Archivos:** app `audit` completa, `patients/dependents.py`,
`patients/history.py`. En móvil, `mobile/lib/features/dependents/` y
`mobile/lib/features/history/`.

**Depende de:** el shell de Flutter (Alexander) para US-07 y US-08.

**Dependen de él:** Karen (US-03 d), Michael (US-10 e) y él mismo (US-08 g).

**Si el sprint se atrasa, US-08 es lo primero que cae al Sprint 2.** Es *Should
have* y es lo más barato de soltar. Daniel queda declarado como reserva para
tomarla si el SM se satura.

---

### José Daniel Iporo — *catálogo del centro médico* — 16 h

Dueño único de `catalog`. Nadie más escribe en esa app este sprint.

**US-11 — Gestión de sucursales · 6 h · WEB**

Alta, edición y desactivación con dirección, teléfono y horario de atención por
día —incluido el corte de mediodía—. La desactivación se **rechaza** si hay
fichas futuras confirmadas, con el detalle de cuáles: el administrador las
reprograma antes, en vez de descubrirlo cuando el paciente llegue. Nombre único
por organización, no global. Coordenadas geográficas opcionales, que el móvil
usará para ordenar por cercanía en el Sprint 2. Las tres sucursales del caso de
estudio se cargan por **migración de datos** y como datos ficticios, no a mano.

**US-12 — Especialidades y profesionales · 10 h · WEB**

ABM de especialidades y alta del profesional con su matrícula y su cuenta de
acceso con rol *Médico*, en una sola transacción. Asociación **muchos a muchos**
con especialidades y con sucursales: sin esa segunda, un profesional que atiende
en tres sedes serían tres registros distintos y la disponibilidad consolidada de
US-15 no existiría.

> La **descripción de la especialidad no es decorativa**: es el texto que el
> chatbot del Sprint 4 recuperará por RAG para sugerir la especialidad adecuada.
> Escribirla bien ahora evita reescribir el catálogo después.

> **Recordatorio de permisos:** los endpoints de lectura de sucursales,
> especialidades y profesionales tienen que ser accesibles al rol *Paciente*
> (`catalog.*.read`), no sólo a quien tiene permiso de escritura. El móvil los
> consume en US-16 y en todo el Sprint 2.

**Archivos:** `catalog/branches.py`, `catalog/specialties.py`,
`catalog/professionals.py`, bloque propio en `catalog/urls.py`.

**Depende de:** US-04 (permisos).

**Dependen de él:** Luis Aguayo (US-13 valida contra el horario de la sucursal)
y Alexander (US-16 filtra por especialidad y por sucursal).

**Reserva declarada:** si alguien se atrasa, toma US-08.

---

### Luis Miguel Aguayo — *agendas* — 22 h

Dueño único de la escritura en `scheduling`, app nueva bajo `/api/scheduling/`.
Lleva la historia más grande del sprint y la que sostiene todo el Sprint 2: sin
espacios reservables no hay reserva, ni pago, ni comprobante.

**US-13 — Agendas médicas · 16 h · WEB**

La agenda se guarda como **regla y no como lista**: profesional, sucursal, días
de la semana, hora de inicio y fin, duración de consulta y cupo por franja. Los
espacios reservables se **derivan** de la regla para un horizonte configurable.
Guardar cada espacio suelto haría inmanejable el cambio de horario.

Tres validaciones que definen la historia: solapamiento —un profesional no puede
tener dos agendas que se pisen, **ni siquiera en sucursales distintas**, porque
no puede estar en dos sedes a la vez—; respeto del horario de atención de la
sucursal (US-11); y vigencia con fecha de inicio y fin, para que cambiar el
horario no altere las fichas ya reservadas bajo la regla anterior.

> **Entregable con fecha propia: el contrato del endpoint de espacios
> disponibles** (punto h de la historia). Lo consumen US-15, US-16 y toda la
> reserva del Sprint 2. Se publica **el 01/09**, documentado, aunque la
> implementación siga en curso — Alexander programa contra el contrato, no
> contra el código.

**US-14 — Bloqueo de agenda · 6 h · WEB**

Bloqueo por rango de fechas o por franja de un día, con motivo tipificado, y
feriado a nivel de organización que se aplica a todos los profesionales de una
vez. Los espacios bloqueados dejan de ofrecerse pero **la regla de agenda no se
toca**: al levantar el bloqueo, la agenda vuelve sola. Las fichas ya reservadas
que caen dentro del bloqueo se **avisan con su listado**; el sistema no las
cancela por su cuenta.

**Archivos:** `scheduling/schedules.py`, `scheduling/blocks.py`, bloque propio en
`scheduling/urls.py`.

**Depende de:** US-04 (permisos) y US-11 (horario de sucursal).

**Dependen de él:** Alexander (US-15 y US-16) y el Sprint 2 completo.

---

### Alexander Osinaga *(Product Owner)* — *shell móvil y cara del paciente* — 26 h

Toma el shell de Flutter porque es el único con la ventana libre al inicio del
sprint: sus dos historias están bloqueadas hasta que Luis publique el contrato
de US-13 el 01/09. Esos primeros días son exactamente los que necesita el shell.

**Shell de Flutter · 6 h · tarea técnica, nunca estimada antes**

La carpeta `mobile/` está vacía: no existe proyecto Flutter. Antes de cualquier
pantalla hace falta el proyecto, el cliente HTTP con **interceptor de
organización y JWT**, el almacenamiento seguro del token, la renovación
automática antes del vencimiento, el router y el tema. Bloquea **ocho**
superficies móviles, así que tiene la fecha más temprana del sprint: **30/08**.

Antes de arrancar, completar la tabla de versiones de
`../../entorno/setup-movil.md`, que sigue en `_(completar)_`, y cerrar la tarea
6 del Sprint 0: `flutter doctor -v` limpio en las seis máquinas.

**US-01 móvil — Registro de paciente · 4 h · deuda del Sprint 0**

La pantalla de alta pública en Flutter, sobre el endpoint que él mismo escribió
en el Sprint 0. Es la primera pantalla que estrena el shell después del login.

**US-15 — Disponibilidad consolidada · 10 h · WEB + MÓVIL**

Vista única con los espacios libres del profesional en **todas** las sucursales
donde atiende, etiquetados con la sede. Es el caso que da nombre al proyecto: el
paciente elige por conveniencia, no por sucursal. El espacio libre se calcula
restando, a lo derivado de la agenda (US-13), los bloqueos (US-14) y las fichas
ya reservadas. Menos de 3 segundos (RNF-02), lo que exige resolverlo en **una
sola consulta por rango** y no una por día: con tres sucursales y catorce días,
el bucle ingenuo son cuarenta y dos idas a la base. La hora de corte se calcula
en la zona horaria de la sucursal, no en la del servidor.

**US-16 — Búsqueda de profesionales · 6 h · WEB + MÓVIL**

Búsqueda por nombre (parcial, sin distinguir mayúsculas ni tildes) y navegación
por especialidad como pantalla de entrada, para el paciente que no sabe a quién
buscar pero sí qué necesita. Cada resultado muestra el dato que decide la
elección: nombre, especialidades, sucursales y **próximo espacio disponible**,
tomado del endpoint de US-15. Búsqueda vacía devuelve el catálogo paginado, no
una pantalla en blanco.

**Archivos:** `mobile/` completo (shell), `scheduling/availability.py`, módulo
propio de búsqueda dentro de `catalog` —acordar el nombre con Daniel antes de
crearlo—. En móvil, `mobile/lib/features/signup/`,
`mobile/lib/features/availability/`, `mobile/lib/features/search/`.

**Depende de:** Luis Aguayo (contrato de US-13, 01/09) y Daniel (US-12) para
US-16.

**Dependen de él:** Karen, el SM y Michael, todos por el shell.

---

## 3. Qué va en móvil y qué no

Ocho superficies móviles este sprint, sobre cuatro personas.

| US | Superficie móvil | Dueño |
|---|---|---|
| US-01 *(deuda S0)* | Registro de paciente | Alexander |
| US-02 *(deuda S0)* | Inicio y cierre de sesión | Karen |
| US-03 | Solicitud de restablecimiento y nueva contraseña | Karen |
| US-05 | Perfil y cambio de contraseña | Michael |
| US-07 | **Sólo móvil** — alta y listado de dependientes | SM |
| US-08 | Antecedentes propios y de dependientes | SM |
| US-15 | Disponibilidad consolidada entre sucursales | Alexander |
| US-16 | Búsqueda de profesionales por especialidad y nombre | Alexander |

**Qué no va en móvil, y por qué.** US-04, US-06, US-09, US-10, US-11, US-12,
US-13 y US-14 son de administrador, recepcionista o médico. El Capítulo 2 del
documento sostiene la arquitectura sobre esa división —**web para el personal,
móvil para el paciente**— y agregarles pantalla móvil duplica interfaces que
nadie va a abrir y contradice el propio argumento de diseño del proyecto.

**Dónde queda el cierre de sesión.** CU4 es WEB/MÓVIL y lo cubre la deuda de
US-02 (Karen), pero el botón vive en la pantalla de perfil (Michael). Karen
expone el método en el shell, Michael lo invoca. Que quede acordado ahora o
aparece dos veces, o ninguna.

---

## 4. Reparto de paquetes

`convenciones-de-codigo.md` exige partir el paquete **antes** de empezar, no
después del primer conflicto. Esto es esa partición.

| App | Módulo | Dueño |
|---|---|---|
| `accounts` | `roles.py`, `permissions.py` | Karen (US-04) |
| `accounts` | `password_reset.py` | Karen (US-03) |
| `accounts` | `passwords.py` *(compartido)* | **Escribe Karen, consume Michael** |
| `accounts` | `profile.py` | Michael (US-05) |
| `patients` | `dependents.py`, `history.py` | SM (US-07, US-08) |
| `patients` | `search.py`, `admin_ops.py` | Michael (US-09, US-10) |
| `catalog` | `branches.py`, `specialties.py`, `professionals.py` | Daniel (US-11, US-12) |
| `catalog` | módulo de búsqueda *(nombre a acordar con Daniel)* | Alexander (US-16) |
| `audit` *(nueva)* | app completa, `/api/audit/` | SM (US-06) |
| `scheduling` *(nueva)* | `schedules.py`, `blocks.py` | Luis Aguayo (US-13, US-14) |
| `scheduling` | `availability.py` | Alexander (US-15) |

**`accounts/passwords.py`** es el único archivo compartido del sprint: contiene
la política de complejidad y el cifrado Argon2 que usan US-03, US-05 y el alta.
Lo escribe Karen los días 1–2 y Michael lo consume; no se duplica la validación.

**`config/urls.py` sigue cerrado.** El SM lo abre una sola vez, en un commit, al
inicio del sprint, para incluir `audit` y `scheduling`. Después nadie lo toca.
Cada app lleva su propio `urls.py` con un bloque de rutas por historia.

**Ramas:** una por historia, `feature/US-13-agendas-medicas`.

---

## 5. Reglas que no se negocian

Valen también para cualquier IA que trabaje sobre este repositorio.

1. **Autorización con `user.has_permission("modulo.recurso.accion")`, nunca con
   `user.has_perm()`.** Las tablas de `django.contrib.auth` no están aisladas
   por inquilino; `has_perm()` responde contra datos de todas las
   organizaciones.
2. **Tokens siempre con `accounts.tokens.tokens_for_user()`.** Un token sin los
   claims `organization_id` / `is_platform_admin` no puede autenticar: la
   búsqueda del usuario devuelve cero filas por RLS.
3. **El contexto lo fija `accounts/authentication.py`, no un middleware.** Un
   middleware corre antes de la vista, y ahí `request.user` todavía es anónimo.
4. **Fuera del ciclo HTTP, envolver con `tenant_context(org.id)`.** Comandos de
   gestión, tareas, migraciones de datos y semillas incluidas.
5. **Nadie corre `makemigrations` sin avisar al SM.** El modelo de datos del
   Sprint 0 está aplicado en local y en Supabase; una migración descoordinada
   deja las dos bases distintas.
6. **Código en inglés; comentarios, docstrings y nombres de pruebas en
   español.**
7. **Datos de prueba sintéticos.** El repositorio es público: ni un dato de una
   persona real, tampoco en las capturas del prototipo.
8. **Toda historia cierra con pruebas de aislamiento**: un usuario de la
   organización A no ve ni una fila de la B, comprobado en ORM y en RLS
   (RNF-08).

---

## 6. Ruta crítica

El sprint arrancó el 25/08. Estas son las fechas que, si se corren, corren todo
lo demás.

| Fecha | Qué tiene que estar | Quién |
|---|---|---|
| **30/08** | US-04 mergeada — libera `has_permission` para las trece historias restantes | Karen |
| **30/08** | Shell de Flutter usable — desbloquea ocho superficies móviles | Alexander |
| **01/09** | Contrato del endpoint de espacios disponibles publicado, aunque la implementación siga | Luis Aguayo |
| **01/09** | Bitácora recibiendo asientos — la escriben US-03, US-08 y US-10 | SM |
| **02/09** | US-05 mergeada; si no, se replanifican US-09 y US-10 | Michael |
| **04/09** | Backend completo y congelado; sólo pantallas, prototipos y pruebas | Todos |
| **07/09** | Cierre del sprint | — |

---

## 7. De dónde salen las 126 horas

El documento comprometía **102 h**. Ninguna historia cambió de alcance ni de
estimación. Las 24 h de diferencia son deuda del Sprint 0 y una tarea técnica
que nunca estuvo en ninguna lista.

| Concepto | Horas |
|---|---|
| Las 13 historias del Sprint 1, tal como están estimadas en el documento | 102 |
| US-04 — arrastre del Sprint 0 (T-06, estado *faltante*) | +10 |
| US-01 móvil — arrastre del Sprint 0 | +4 |
| US-02 móvil — arrastre del Sprint 0 | +4 |
| Shell de Flutter — tarea técnica nunca estimada | +6 |
| **Total** | **126** |

**De esas 24 h, 18 ya estaban estimadas y cobradas en el Sprint 0.** US-04 valía
10 h en el Product Backlog y figura como no entregada. US-01 y US-02 se
estimaron en 10 h y 6 h con responsable web **y móvil** en ambas, y sólo se
entregó la mitad web. No es trabajo nuevo: es trabajo que el Sprint 0 declaró
terminado sin estarlo.

**Sólo 6 h son estimación nueva**, el shell de Flutter, y aparecen porque la
tarea 6 del Sprint 0 pedía *instalar el entorno* —`flutter doctor` limpio—, no
crear el proyecto. Nadie estimó nunca el proyecto en sí, y sin él las ocho
pantallas móviles del sprint no tienen dónde vivir.

**Efecto sobre el ritmo.** 126 h entre 6 son 21 h por integrante. El sprint dura
14 días, pero arrancó el 25/08: contando desde el 27 quedan 11 días útiles, o
sea ~1,9 h por día y por persona. Es ajustado. Si hay que soltar algo, se suelta
US-08 (6 h, *Should have*) al Sprint 2, y quedan 20 h por integrante.

---

## 8. Tareas nuevas para el Sprint Backlog del documento

La numeración del Sprint 1 va de T-09 a T-21. Se agregan:

| ID | Tarea | Tipo | Estimación | Responsable | Prioridad |
|---|---|---|---|---|---|
| T-06 *(arrastre)* | Crear y asignar roles | Historia | 10 horas | Ortega Mancilla, K.P. | Must have |
| T-22 | Shell de la aplicación Flutter | Técnica | 6 horas | Osinaga Blanco, A. | Must have |
| T-23 | Registro de paciente — pantalla móvil | Historia | 4 horas | Osinaga Blanco, A. | Must have |
| T-24 | Inicio y cierre de sesión — pantalla móvil | Historia | 4 horas | Ortega Mancilla, K.P. | Must have |

T-06 conserva su identificador original: es la misma tarea del Sprint 0, no una
nueva. Su estimación pasa de 5 h a 10 h para alinearse con el Product Backlog,
donde US-04 siempre valió 10 h.

También hay que corregir el estado de **T-08** (pruebas de acceso cruzado entre
inquilinos), que figura como *incompleto* en el Sprint Backlog del Sprint 0 pero
está cubierto por las 33 pruebas en verde del cierre. O se corrige el estado o
se completa lo que falte, pero no puede quedar en rojo en el documento.
