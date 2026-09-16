# Las 8 características generales de la materia

Qué pide cada una, **qué hay hoy en el repositorio**, dónde está, y qué falta.

Este documento no es una declaración de intenciones: cada fila dice el archivo
y la prueba que la respaldan. Lo que no está hecho figura como no hecho.

**Corte:** 15/09/2026, Sprint 2 en curso. Estado general: **6 de 8 cumplidas,
2 parciales**.

| # | Característica | Estado | Dónde |
|---|---|---|---|
| 1 | Solución universal | ✅ Cumplida | `tenancy/`, RLS en toda tabla |
| 2 | Gestión de usuarios y privilegios | 🟡 **Parcial** | `accounts/` — falta granularidad de componente |
| 3 | Log / Bitácora | 🟡 **Parcial** | `audit/` — falta la confidencialidad por llave |
| 4 | Facilidad de uso y asistencia en línea | ✅ Cumplida | `assistant/` (US-31, US-32, US-34) |
| 5 | Reportes personalizables | ✅ Cumplida | `reporting/` |
| 6 | Backup / Restore | ✅ Cumplida | `backups/` |
| 7 | Web / Móvil | ✅ Cumplida | `frontend/`, `mobile/` |
| 8 | Modelo SaaS en la nube | ✅ Cumplida | `tenancy/`, Railway + Supabase |

---

## 1. Solución universal

> *El sistema debe poder ponerse en marcha en cualquier empresa donde se
> requiera la aplicación.*

**Es el eje del proyecto, no un agregado.** El sistema es multi-inquilino desde
el Sprint 0: una sola instalación atiende a varios centros médicos y ninguno ve
los datos de otro.

Lo que lo hace cierto, y no una promesa:

- **`tenancy.Organization`** es el inquilino. Se da de alta por la API (US-43) y
  al crearse se le clonan las plantillas de rol, así que su administrador ajusta
  sus permisos sin afectar a nadie.
- **Row Level Security en PostgreSQL**, con `ENABLE` **y** `FORCE`, en *toda*
  tabla con `organization_id`. No es un `WHERE` de la aplicación: lo hace
  cumplir la base, y Django se conecta como `app_user`, que es `NOSUPERUSER` y
  `NOBYPASSRLS`.
- **El fallo abre en cerrado.** Sin contexto de inquilino, toda consulta
  devuelve **cero filas**, no todas. Si el middleware falla, el sistema no
  devuelve nada.
- **Nada del negocio está cableado.** Sucursales, especialidades, profesionales,
  agendas, roles y permisos son datos que carga cada organización, no constantes
  del código.

**Cómo se comprueba:** `backend/tests/test_isolation.py` — 33 pruebas, incluida
una que **falla sola** si alguien crea una tabla con `organization_id` y se
olvida del RLS.

---

## 2. Gestión de usuarios y privilegios — 🟡 parcial

> *Crear usuarios, grupos de usuarios y asignar privilegios de manera flexible y
> abierta sobre todo tipo de componente (opciones de menú, formularios, botones,
> text, label, etc.). De entrada no se sabe cuántos usuarios ni qué grupos
> habrá.*

### Lo que sí está

- **Los roles son datos, no un `varchar` con una lista fija.** `accounts.Role`
  se crea, edita y borra por la API (US-04). Cada organización nace con cinco
  plantillas clonadas y puede cambiarlas enteras.
- **Los permisos también.** `accounts.Permission` es un catálogo con código
  `modulo.recurso.accion`; `RolePermission` los asigna a roles y `UserRole`
  asigna roles a personas. **Una persona puede tener más de un rol.**
- **Toda autorización pasa por `user.has_permission("...")`**, nunca por
  `django.contrib.auth`, cuyas tablas no están aisladas por inquilino.
- **Hay un administrador por organización** que hace ese trabajo, y un
  Superadministrador de Plataforma que da de alta organizaciones y **no accede a
  los datos internos de ninguna** — se hace cumplir en la base, no por
  convención.
- Hoy son **52 permisos** declarados en 9 módulos.

### Lo que falta, y es lo que la deja parcial

**La consigna pide privilegios sobre «opciones de menú, formularios, botones,
text, label».** Los permisos de hoy son por **acción de la API** —
`patients.patient.read`, `reporting.report.share`—, no por **componente de la
interfaz**. En la práctica el frontend esconde botones mirando esos permisos,
pero eso es una decisión del código del frontend, no algo que el administrador
pueda configurar desde el sistema.

Para cerrarla hace falta:

1. Un catálogo de **componentes de interfaz** por pantalla (menú, formulario,
   botón, campo), con su código.
2. Una tabla que asocie rol → componente → visible / editable / oculto.
3. Que el frontend pregunte por ese mapa en vez de tener la regla escrita.

No está hecho y no está estimado. Es lo primero que hay que llevar al Planning.

---

## 3. Log / Bitácora — 🟡 parcial

> *Registrar en un archivo log todas las acciones de los usuarios: IP, usuario,
> fecha, hora, acción. Es confidencial: ni el administrador de BD debe verlo, y
> la única forma de verlo es vía una llave del desarrollador y sólo desde el
> sistema.*

### Lo que sí está

`accounts.AuditLog`, consultable en `/api/audit/logs/` (US-06):

| Lo que pide | Columna |
|---|---|
| IP de la máquina | `ip_address` — mirando `X-Forwarded-For` primero, porque en Railway hay un proxy delante |
| Usuario | `user` |
| Fecha y hora | `occurred_at` |
| Acción realizada | `action`, con un catálogo de **26 acciones** con etiqueta legible |

Y tres cosas que la consigna no pide y que la hacen confiable:

- **Es inalterable.** `app_user` no tiene `UPDATE` ni `DELETE` sobre `audit_log`.
  No es una regla de la aplicación: es un `REVOKE` en la base. Tan real es que
  **impide borrar un usuario que dejó un asiento**, y por eso la restauración de
  una copia de seguridad desactiva usuarios en vez de borrarlos.
- **El asiento se escribe fuera de la transacción de negocio.** Un intento
  rechazado —lo que más interesa auditar— dejaría de registrarse si se escribiera
  dentro, porque DRF deshace la transacción al manejar el rechazo.
- **La bitácora no se puede reponer desde un respaldo.** Si se pudiera,
  restaurar sería la forma de borrar el rastro de lo que uno hizo.

Se audita todo lo sensible, incluida **la exportación de reportes** y **la
consulta al asistente** — y en los dos casos se registra *qué* se hizo y nunca
*el contenido*: ni las filas del reporte ni los síntomas que escribió el
paciente.

### Lo que falta, y es lo que la deja parcial

**La confidencialidad.** Hoy la bitácora está en claro en una tabla de
PostgreSQL. RLS impide que una organización lea la de otra, y el permiso
`audit.log.read` impide que la lea cualquiera **desde la aplicación** — pero
quien tenga acceso a la base la lee entera. La consigna pide explícitamente que
ni el administrador de BD pueda, y que sólo se abra con una llave del
desarrollador desde el sistema.

Para cerrarla hace falta cifrar el contenido del asiento —`detail`, `entity_id`,
y probablemente `ip_address` y el usuario— con una clave que **no viva en la
base**, y descifrarlo únicamente en el proceso de la aplicación al servir
`/api/audit/logs/`. Las decisiones abiertas son dónde vive esa clave (variable
de entorno, igual que `OPENAI_API_KEY`) y qué pasa si se pierde: los asientos
viejos quedan ilegibles para siempre, que es justamente el punto.

No está hecho. Es la segunda cosa que hay que llevar al Planning.

---

## 4. Facilidad de uso y asistencia en línea — ✅

> *Interface donde el usuario no invierta tiempo en aprender a usar el sistema,
> componentes que faciliten la entrada de datos, y mecanismos de asistencia en
> línea en caso de dudas.*

**La asistencia en línea es el asistente de orientación** (US-31, US-32, US-34),
entregado en este sprint. No es un manual ni un tooltip: es un chatbot RAG que
responde sobre el catálogo real de cada organización.

- **Responde sólo sobre lo que está en el catálogo de esa organización**, y la
  respuesta **viaja con los fragmentos que la sustentan**. Sin esa lista no hay
  cómo demostrar que no inventó.
- Si el catálogo no contesta la pregunta, dice **«no tengo esa información»**.
  No completa con conocimiento general.
- **Deriva a emergencia** ante una descripción compatible con una urgencia, y
  esa evaluación corre **antes** de todo lo demás: sale aunque no haya red, ni
  clave del proveedor, ni nada indexado.
- Sugiere la especialidad **con su identificador real**, para que la pantalla
  pueda ofrecer reservar sin que el usuario tenga que buscarla.

Lo demás de la facilidad de uso está repartido: búsqueda de profesionales sin
distinguir mayúsculas ni tildes (US-16), disponibilidad consolidada entre sedes
(US-15), y el arreglo de los diez defectos de usabilidad del móvil del Sprint 1.

**Sigue faltando** la ayuda contextual por pantalla — un «¿qué es esto?» en cada
formulario. El asistente cubre la duda del paciente, no la del recepcionista
sobre un campo concreto.

---

## 5. Reportes personalizables — ✅

> *Mecanismos que permitan al usuario construir sus propios reportes, indicando
> qué columnas, qué criterios de selección y qué orden. Todo reporte, antes de
> generarse, debe tener una interfaz para filtrar. Y debe poder exportarse a
> Excel, HTML, eMail y PDF.*

App `reporting`, bajo `/api/reporting/`.

| Lo que pide | Cómo está resuelto |
|---|---|
| Elegir **columnas** | `POST /run/` con `columns: [...]` |
| Elegir **criterios de selección** | `filters: [{field, operator, value}]` — con operadores por tipo: contiene, empieza con, mayor, menor… |
| Elegir **orden** | `order_by: ["last_name", "-created_at"]` |
| **Interfaz previa para filtrar** | `GET /datasets/` devuelve columnas, filtros, tipos y operadores. El formulario se dibuja solo con eso |
| **Excel** | `.xlsx` con encabezado congelado, autofiltro y ancho por contenido |
| **HTML** | una sola pieza, con los estilos adentro |
| **PDF** | apaisado, con el texto envuelto y el ancho repartido por contenido |
| **eMail** | el mismo archivo, adjunto |
| *(además)* CSV | con BOM y punto y coma, para que Excel en español lo abra bien |

Seis conjuntos reportables: pacientes, profesionales, especialidades,
sucursales, agendas y bitácora. Agregar uno es un bloque declarativo en
`reporting/datasets.py`.

**Y el usuario guarda sus reportes** (`SavedReport`) y puede compartirlos con la
organización. Al correr uno guardado se le pueden cambiar los filtros, que es el
caso normal: el mismo reporte, otro período.

**Tres decisiones que no salen del enunciado y que sostienen lo demás:**

1. **Lista blanca declarativa, no reflexión sobre los modelos.** `password` es un
   campo de `User` y `guardian__user__password` es una ruta válida del ORM. Sólo
   se puede pedir lo que el catálogo declara — y eso incluye el orden: ordenar
   por un campo que no se muestra sigue filtrando por él, y con eso se adivina
   un valor letra por letra.
2. **Dos cerraduras.** Una autoriza *usar el constructor*; la otra, *ver ese
   dato*, y es la misma que ya exige la pantalla correspondiente. Sin la
   segunda, un reporte es la puerta lateral para leer lo que la pantalla niega.
3. **Un criterio que no se pudo aplicar falla.** El defecto clásico de un filtro
   dinámico es no filtrar nada en silencio: el reporte sale con la tabla entera y
   quien lo lee concluye que ése es el dato.

**Cómo se comprueba:** `backend/tests/test_caracteristica_5_reportes.py` —
31 pruebas, incluidas las que abren el Excel generado y comprueban que trae los
datos filtrados.

---

## 6. Backup / Restore — ✅

> *Funciones para posibilitar las copias de seguridad y restauración de todo el
> sistema.*

**En un sistema multi-inquilino esto son dos cosas, y confundirlas era el error
a evitar.**

### La copia de toda la instalación

`manage.py dump_database` — `pg_dump` de la base entera, en formato comprimido o
en SQL. Es trabajo de quien administra la base, no de la aplicación: el caso de
uso de un respaldo completo es el de un sistema al que no se puede entrar.

### La copia de una organización

Lo que un cliente de un SaaS necesita y no puede pedirle al proveedor: llevarse
*sus* datos, poder restaurarlos, y poder irse.

| Endpoint | Qué hace |
|---|---|
| `POST /api/backups/create/` | genera la copia en JSON y la descarga |
| `POST /api/backups/inspect/` | dice qué trae un archivo, **sin escribir nada** |
| `POST /api/backups/restore/` | reemplaza los datos, con confirmación explícita |
| `GET /api/backups/records/` | el historial: qué se respaldó y qué se restauró |

También por consola: `backup_organization` (con `--all`, para una tarea
nocturna) y `restore_organization`.

**Decisiones que valen más que el código:**

- **El archivo no se guarda en la base.** Lleva en claro todo lo que el sistema
  protege; guardarlo dentro sería poner una copia sin RLS al lado de la
  original. Queda registrado *que* se hizo, quién y de cuánto.
- **El respaldo de un centro médico no se restaura dentro de otro.** RLS no
  alcanzaría: las filas se insertarían bajo el `organization_id` correcto. Lo que
  estaría mal es el contenido.
- **La restauración reemplaza, no fusiona**, y es todo o nada. Restaurar es
  volver a un momento; si el archivo no tiene una fila, es porque en ese momento
  no existía.
- **Tres tablas no vuelven nunca**: la bitácora, los intentos de acceso y los
  tokens de restablecimiento. Y **dos más tampoco**: la suscripción y las
  métricas de uso, que son la relación comercial y las escribe la plataforma, no
  el inquilino — restaurarlas sería reasignarse el propio plan volviendo a un
  archivo viejo.
- **Los usuarios se desactivan, no se borran.** Porque la bitácora es
  inalterable y los apunta: borrar un usuario que dejó un asiento es imposible
  en esta base, y está bien que lo sea.

**Cómo se comprueba:** `backend/tests/test_caracteristica_6_respaldos.py` —
18 pruebas, incluida el ciclo completo respaldo → desastre → restauración.

---

## 7. Web / Móvil — ✅

> *Identificar qué funcionalidades conviene implementar como app Web y cuáles
> como App Móvil.*

El reparto no es arbitrario: **la web es para quien trabaja en el centro médico,
el móvil para el paciente.**

| | Web (React) | Móvil (Flutter) |
|---|---|---|
| **Quién** | administrador, médico, recepción, superadministrador | paciente y titular de dependientes |
| **Qué** | ABM de sucursales, especialidades, profesionales y agendas; padrón de pacientes; historia clínica; check-in de mostrador; cobro y comprobante; bitácora; reportes; respaldos; panel de plataforma y planes | registro e inicio de sesión; búsqueda de profesionales; disponibilidad; reserva y pago de la ficha; comprobante; pacientes a cargo; antecedentes; **asistente de orientación** |
| **Por qué** | trabajo de escritorio, sesiones largas, tablas y formularios extensos | de a ratos, en la calle, con el teléfono en la mano |

Los dos consumen la **misma API**, con los mismos permisos. Un reporte no se
hace desde el móvil no porque no se pueda, sino porque un Excel de veinte
columnas en una pantalla de cinco pulgadas no le sirve a nadie.

Web desplegada; la APK se compila en local siguiendo
[`docs/entorno/setup-movil.md`](entorno/setup-movil.md).

---

## 8. Modelo SaaS en la nube — ✅

> *Desarrollado bajo el enfoque de software como servicio, donde lo que se vende
> son suscripciones, desplegado en la nube.*

### Lo que se vende

- **`SubscriptionPlan`** — los planes, con sus límites: sucursales, usuarios,
  profesionales, consultas de IA por mes, almacenamiento.
- **`Subscription`** — el historial de planes de cada organización, con fechas.
  Es una tabla y no un campo porque hay que poder reconstruir «uso por plan».
  Una sola vigente por organización, garantizado por la base.
- **`UsageMetric`** — el consumo de cada inquilino, precalculado. El panel del
  superadministrador se alimenta de acá y **no cuenta filas en vivo sobre las
  tablas de los inquilinos**: no puede —RLS se lo impide— y no escalaría.
- **`IsolationAlert`** — las alertas de acceso cruzado. Cualquiera las inserta,
  sólo el superadministrador las lee.

Y el detalle que hace que sea un SaaS de verdad: **el superadministrador vende y
administra suscripciones, pero no accede a los datos clínicos de ningún
cliente**, y eso se hace cumplir en la base.

### Dónde está desplegado

| Qué | Servicio |
|---|---|
| Aplicación web y API | **Railway** (dos servicios del mismo proyecto) |
| Base de datos | **Supabase** (PostgreSQL 16 gestionado, con pgvector y RLS) |

Los detalles del despliegue, con las trampas que costaron una tarde, están en
[`docs/entorno/despliegue.md`](entorno/despliegue.md).

> **Antes de cualquier defensa, entrar al panel de Supabase el día anterior y
> comprobar que el proyecto está activo.** El plan gratuito se pausa a los
> 7 días sin actividad y el despliegue queda caído sin aviso.

---

## Qué falta, en orden

1. **Característica 2** — privilegios sobre componentes de interfaz. Sin
   estimar.
2. **Característica 3** — cifrado de la bitácora con llave del desarrollador.
   Sin estimar.
3. **Característica 4** — ayuda contextual por pantalla, además del asistente.

Las tres van al Planning. Ninguna está empezada.
