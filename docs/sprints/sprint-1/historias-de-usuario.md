# Sprint 1 — Historias de Usuario (borrador para el documento)

Borrador para pegar en el apartado **Historias de Usuario** del Sprint 1
(CAPITULO 4). Sigue el mismo formato que el Sprint 0: título, caso de uso,
descripción, prioridad, horas, funcionalidades enumeradas, responsables y
prototipo.

**Objetivo del Sprint 1.** Dejar operativo el catálogo del centro médico
—sucursales, especialidades, profesionales y agendas— y completar la gestión
de pacientes y de la propia cuenta, de modo que el Sprint 2 pueda reservar
fichas sobre datos reales.

- **Fechas:** 25/08/26 – 07/09/26 · Revisión de Sprint: 08–10/09/26
- **Historias:** US-03, US-05, US-06, US-07 a US-16 (13 historias), más US-04 que se arrastra del Sprint 0
- **Compromiso:** 102 horas · 6 integrantes · 17 h por integrante

El reparto de historias, el alcance de cada integrante en web y en
móvil, la partición de paquetes y la ruta crítica están en
[`reparto.md`](reparto.md). Este archivo contiene sólo las historias
redactadas, para pegarlas en el CAPITULO 4 del documento.

---

## Casos de uso del Sprint

| ID | Caso de Uso | Plataforma | Descripción |
|---|---|---|---|
| CU2 | Gestión de Roles y Permisos | WEB | El administrador de la organización crea y edita los roles de su centro médico, les ajusta los permisos y se los asigna a los usuarios. Las cuatro plantillas del sistema se copian dentro de la organización al darla de alta, y lo que se edita es esa copia. |
| CU3 | Recuperación de Credenciales | WEB/MÓVIL | El usuario solicita restablecer su contraseña indicando su organización y su correo. El sistema envía un enlace de un solo uso con vencimiento; al usarlo, la contraseña se reemplaza y se invalidan las sesiones abiertas. La respuesta es idéntica exista o no la cuenta, para no revelar qué correos están registrados. |
| CU6 | Gestión de Perfil de Usuario | WEB/MÓVIL | El usuario consulta y edita sus datos de contacto y cambia su contraseña acreditando la actual. Los campos que definen su identidad dentro de la organización —documento, rol, organización— no son editables por él. |
| CU7 | Consulta de Bitácora de Auditoría | WEB | El administrador consulta el registro cronológico de acciones sensibles de su organización, con filtros por actor, tipo de acción y rango de fechas. La bitácora es de sólo lectura: no se edita ni se borra desde la aplicación. |
| CU8 | Gestión de Pacientes Dependientes | MÓVIL | El titular registra a los familiares a cargo, con su parentesco, y queda habilitado para agendarles fichas y ver su historial. Un dependiente no tiene cuenta de acceso propia mientras lo sea. |
| CU9 | Gestión de Antecedentes del Paciente | WEB/MÓVIL | El paciente o su titular registra alergias, condiciones crónicas y medicación habitual, que el profesional ve destacadas al abrir la consulta. |
| CU10 | Búsqueda y Consulta de Pacientes | WEB | El recepcionista busca pacientes por nombre o documento dentro de su organización y consulta su ficha demográfica y sus fichas próximas, sin acceso al contenido clínico. |
| CU11 | Administración de Pacientes | WEB | El administrador corrige datos demográficos, da de baja lógica registros duplicados y fusiona duplicados conservando el historial de ambos. |
| CU12 | Gestión de Sucursales | WEB | El administrador da de alta, edita y desactiva las sucursales de su organización con su dirección, teléfono y horario de atención. |
| CU13 | Gestión de Especialidades y Profesionales | WEB | El administrador define el catálogo de especialidades y da de alta a los profesionales, asociando cada uno a una o más especialidades y a una o más sucursales. |
| CU14 | Gestión de Agendas Médicas | WEB | El administrador define la agenda de cada profesional por sucursal: días de la semana, franjas horarias, duración de consulta y cupo por franja. De esa definición se derivan los espacios reservables. |
| CU15 | Bloqueo de Agenda Médica | WEB | El administrador bloquea rangos de fecha y hora de la agenda de un profesional por vacaciones, feriado o ausencia. Los espacios bloqueados dejan de ofrecerse. |
| CU16 | Consulta de Disponibilidad Médica | WEB/MÓVIL | El paciente consulta la disponibilidad de un profesional a lo largo de todas las sucursales donde atiende, en una sola vista y para un rango de fechas. |
| CU17 | Búsqueda de Profesionales | WEB/MÓVIL | El paciente busca profesionales por especialidad o por nombre y filtra por sucursal, viendo sólo a los activos de su organización. |

---

## US-04 — Crear y asignar roles

**Gestión de roles y permisos** · *arrastre del Sprint 0 (T-06)*

| | |
|---|---|
| CU2 — Gestión de Roles y Permisos | El administrador de la organización crea y edita los roles de su centro médico, les ajusta los permisos y se los asigna a los usuarios. Lo que edita es la copia que su organización recibió al darse de alta, no la plantilla del sistema. |

**Prioridad: ALTA** · **Cant Horas: 10 hr**

**Funcionalidades:**

a) Alta, edición y baja de roles dentro de la organización, con código único
   por inquilino —no global: dos centros médicos pueden tener cada uno su rol
   `caja` sin pisarse—.
b) Edición del conjunto de permisos de un rol, tomados de un catálogo del
   sistema con el formato `modulo.recurso.accion`. El conjunto se reemplaza
   completo: lo que no viene, se revoca.
c) Asignación de roles a los usuarios y revocación. Una persona puede tener
   más de un rol, y sus permisos efectivos son la unión de los de todos.
d) Las cuatro plantillas del sistema —Administrador de Organización, Médico,
   Recepcionista y Paciente— se copian dentro del inquilino cuando US-43 da de
   alta la organización. La plantilla no se edita nunca; se edita la copia.
e) Un rol de una organización **no** puede llevar permisos del módulo
   `platform`: sin ese corte, el administrador de un centro médico podría
   concederse el alta de organizaciones.
f) Un rol asignado a algún usuario no se elimina; primero se reasignan esos
   usuarios. El rol de Administrador de Organización no se elimina ni se
   desactiva en ningún caso: es el único que puede administrar usuarios y
   roles, y sin él nadie podría volver a activarlo.
g) Nadie se revoca un rol a sí mismo, por el mismo motivo.
h) Toda alta, edición, baja, cambio de permisos, asignación y revocación queda
   en la bitácora de auditoría con el valor anterior y el nuevo (RNF-18).
i) La autorización se resuelve con `user.has_permission("modulo.recurso.accion")`
   contra `UserRole → RolePermission`, nunca con `user.has_perm()`: las tablas
   de `django.contrib.auth` no están aisladas por inquilino y responderían
   contra los permisos de todas las organizaciones.

> **Criterio de aceptación que no figura en el Product Backlog.** La plantilla
> del rol *Paciente* nacía sin ningún permiso. Se le agregan los cuatro de
> lectura del catálogo —`catalog.branch.read`, `catalog.specialty.read`,
> `catalog.professional.read` y `scheduling.slot.read`—; sin ellos la
> aplicación móvil no puede listar sucursales ni buscar profesionales, y el
> Sprint 2 no puede reservar.

**Nota sobre el catálogo de permisos.** La migración
`accounts/0003_seed_permissions_sprint_1` declara de una sola vez los 17
permisos que necesitan las historias del Sprint 1 —especialidades,
profesionales, agendas y bloqueos, baja lógica y fusión de pacientes, y baja
de roles—, y los propaga a las organizaciones **ya dadas de alta**: sus copias
de las plantillas existen desde antes y no se enteran solas de un permiso
nuevo. Se hizo en una migración y no en una por historia para que la base
compartida se toque una vez (regla 5 del reparto).

**Responsables:**
Web: Karen Ortega · Móvil: — *(historia de administrador; no va en móvil)*

**Prototipo** (capturas web)

---

## US-03 — Recuperación de contraseña

**Recuperación de credenciales**

| | |
|---|---|
| CU3 — Recuperación de Credenciales | El usuario solicita restablecer su contraseña indicando su organización y su correo; recibe un enlace de un solo uso con vencimiento, y al usarlo la contraseña se reemplaza y se cierran las sesiones abiertas. |

**Prioridad: MEDIA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Solicitud de restablecimiento indicando el identificador de la organización
   y el correo, porque el correo es único por inquilino y no de forma global:
   sin la organización, la búsqueda es ambigua.
b) Respuesta **idéntica** exista o no la cuenta, y con el mismo tiempo de
   respuesta, para que la pantalla no sirva como oráculo de qué correos están
   registrados en cada centro médico.
c) Generación de un token de un solo uso con vencimiento de 30 minutos,
   almacenado como hash y no en claro, de modo que leer la tabla no baste para
   secuestrar la cuenta.
d) Envío del enlace por correo, con la marca de la organización, y registro del
   envío en la bitácora de auditoría (US-06).
e) Reemplazo de la contraseña con el mismo cifrado Argon2 del alta (RNF-04) y
   con las mismas reglas de complejidad que el registro.
f) Invalidación de **todos** los tokens de refresco vigentes del usuario al
   completar el cambio: si alguien tenía la sesión abierta, deja de tenerla.
g) Consumo del token al primer uso y rechazo de cualquier reintento posterior,
   aunque no haya vencido.
h) Pantalla web y móvil de solicitud y de nueva contraseña, con mensajes
   distintos para enlace vencido, enlace ya usado y enlace inválido.

**Responsables:**
Web: Karen Ortega · Móvil: Karen Ortega

**Prototipo** (capturas, tanto web como móvil)

---

## US-05 — Edición de perfil

**Gestión del perfil de usuario**

| | |
|---|---|
| CU6 — Gestión de Perfil de Usuario | El usuario consulta y edita sus datos de contacto y cambia su contraseña acreditando la actual; los campos que definen su identidad dentro de la organización no son editables por él. |

**Prioridad: MEDIA** · **Cant Horas: 4 hr**

Es la **historia de referencia** de la escala de estimación descrita en el
apartado 1.2.6: cuatro horas entre el endpoint, el formulario y sus pruebas.
Las demás se estiman por comparación con ella.

**Funcionalidades:**

a) Consulta del propio perfil —nombres, correo, teléfono, organización y rol—,
   resuelto siempre a partir del token y **nunca** de un identificador enviado
   por el cliente.
b) Edición de los datos de contacto —nombres, teléfono, correo— con las mismas
   validaciones de formato del alta.
c) Cambio de contraseña acreditando la actual. Cambiarla no cierra la sesión en
   curso, a diferencia de la recuperación de US-03, porque aquí el usuario ya
   demostró conocerla.
d) Campos **no** editables por el propio usuario: documento, rol, organización
   y estado de la cuenta. Cambiarlos es potestad del administrador (US-10) y
   del superadministrador (US-43).
e) Rechazo del cambio de correo si el nuevo ya existe **en esa organización**,
   con la misma regla de unicidad por inquilino del registro.
f) Formulario web y pantalla móvil compartiendo el mismo endpoint, con guardado
   parcial: editar el teléfono no obliga a reenviar toda la ficha.

**Responsables:**
Web: Michael Mamani · Móvil: Michael Mamani

**Prototipo** (capturas, tanto web como móvil)

---

## US-06 — Bitácora de auditoría

**Consulta de la bitácora de acciones sensibles**

| | |
|---|---|
| CU7 — Consulta de Bitácora de Auditoría | El administrador consulta el registro cronológico de acciones sensibles de su organización, con filtros por actor, acción y fechas. La bitácora es de sólo lectura. |

**Prioridad: MEDIA** · **Cant Horas: 10 hr**

**Funcionalidades:**

a) Registro automático de las acciones sensibles que enumera el backlog —acceso
   a historia clínica, anulación de fichas y movimientos de pago— más el alta,
   la baja y el cambio de rol de usuarios, y el restablecimiento de contraseña.
b) Cada asiento guarda quién, qué, sobre qué recurso, cuándo, desde qué
   dirección IP y con qué agente, además de la organización a la que pertenece.
c) Escritura **fuera de la transacción de negocio**: que falle la auditoría no
   puede tumbar la operación auditada, y que la operación se deshaga no borra
   la constancia del intento.
d) Clave primaria UUID generada en Python y no `bigserial`, por la misma razón
   que `login_attempts` e `isolation_alerts`: una tabla de sólo inserción bajo
   RLS con `INSERT ... RETURNING` exigiría abrir también la política de
   lectura.
e) Consulta paginada con filtros por actor, tipo de acción y rango de fechas,
   ordenada de lo más reciente a lo más antiguo.
f) Sin edición ni borrado desde la aplicación: la bitácora no expone verbos de
   escritura, ni siquiera al administrador.
g) Aislamiento verificado: un administrador de la organización A no ve un solo
   asiento de la organización B, comprobado en la capa ORM y en RLS (RNF-08).
h) Autorización por `user.has_permission("audit.log.read")`, **nunca** por
   `has_perm()`, que consulta tablas no aisladas.

**Responsables:**
Web: Luis Mateo Hurtado · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-07 — Pacientes dependientes

**Registro de familiares a cargo**

| | |
|---|---|
| CU8 — Gestión de Pacientes Dependientes | El titular registra a los familiares a cargo con su parentesco y queda habilitado para agendarles fichas y ver su historial. Un dependiente no tiene cuenta de acceso propia mientras lo sea. |

**Prioridad: ALTA** · **Cant Horas: 10 hr**

**Funcionalidades:**

a) Alta de un dependiente desde la aplicación móvil del titular: nombres,
   documento, fecha de nacimiento, sexo y parentesco.
b) Creación de la **ficha demográfica sin cuenta de acceso**: el dependiente es
   un paciente del catálogo, no un usuario que inicia sesión. La distinción
   entre persona atendida y credencial es la que hace posible el caso.
c) Unicidad del documento por organización, igual que en el alta de paciente:
   si ese documento ya existe en el centro médico, se ofrece **vincularlo** en
   lugar de crear un duplicado.
d) Habilitación del titular para reservar fichas y consultar el historial de
   sus dependientes, con el mismo alcance que sobre sí mismo.
e) Baja del vínculo sin borrar la ficha del dependiente: la historia clínica es
   longitudinal y sobrevive al vínculo.
f) Promoción de un dependiente a titular al alcanzar la mayoría de edad,
   creándole su cuenta de acceso y conservando su historial.
g) Límite configurable de dependientes por titular, para que el caso no sea una
   puerta abierta a inflar el padrón de pacientes.
h) Listado de dependientes en la aplicación móvil, con un selector de "para
   quién es esta ficha" reutilizable por la reserva del Sprint 2.

**Responsables:**
Web: — · Móvil: Luis Mateo Hurtado

**Prototipo** (capturas móvil)

---

## US-08 — Antecedentes del paciente

**Registro de antecedentes relevantes**

| | |
|---|---|
| CU9 — Gestión de Antecedentes del Paciente | El paciente o su titular registra alergias, condiciones crónicas y medicación habitual, que el profesional ve destacadas al abrir la consulta. |

**Prioridad: MEDIA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Registro de tres tipos de antecedente —alergia, condición crónica y
   medicación habitual—, cada uno con descripción y fecha de registro.
b) Marca de severidad en las alergias, para que el profesional distinga una
   intolerancia leve de una reacción anafiláctica.
c) Registro sobre sí mismo o sobre un dependiente a cargo (US-07), con la misma
   pantalla y el mismo selector de paciente.
d) Los antecedentes son **declarados por el paciente**, no diagnosticados: se
   guardan marcados como tales y no se confunden con el diagnóstico clínico que
   el médico registra en el Sprint 3.
e) Edición y baja lógica por el propio paciente; el histórico de lo declarado no
   se pierde, sólo deja de estar vigente.
f) Exposición del conjunto vigente en el endpoint que el módulo de atención
   consumirá para mostrarlo destacado al abrir la consulta.
g) Acceso limitado al propio paciente, a su titular y a los profesionales de su
   organización; toda lectura por parte de un profesional queda en la bitácora
   (US-06).

**Responsables:**
Web: Luis Mateo Hurtado · Móvil: Luis Mateo Hurtado

**Prototipo** (capturas, tanto web como móvil)

---

## US-09 — Búsqueda de pacientes

**Búsqueda y filtrado de pacientes en ventanilla**

| | |
|---|---|
| CU10 — Búsqueda y Consulta de Pacientes | El recepcionista busca pacientes por nombre o documento dentro de su organización y consulta su ficha demográfica y sus fichas próximas, sin acceso al contenido clínico. |

**Prioridad: ALTA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Búsqueda por número de documento —coincidencia exacta— y por nombre o
   apellido —coincidencia parcial, sin distinguir mayúsculas ni tildes—.
b) Respuesta en **menos de 2 segundos con 10.000 registros** (RNF-01), lo que
   obliga a un índice de texto sobre el nombre normalizado: sin él, la búsqueda
   parcial degrada linealmente y el requisito no se cumple.
c) Resultados paginados con los datos que la ventanilla necesita para
   identificar a la persona: nombres, documento, fecha de nacimiento y teléfono.
d) Consulta de la ficha del paciente seleccionado con sus fichas próximas y su
   estado, **sin ninguna información clínica**: el recepcionista agenda y cobra,
   no lee diagnósticos.
e) Filtro por sucursal y por estado —activo o dado de baja— para separar el
   padrón vigente del histórico.
f) Alcance limitado a la organización del recepcionista, verificado en ORM y en
   RLS (RNF-08); una búsqueda ancha nunca alcanza a otro centro médico.
g) Prueba de carga con un conjunto de 10.000 registros **sintéticos** —el
   repositorio es público y no admite datos de personas reales— como criterio de
   verificación del RNF-01.

**Responsables:**
Web: Michael Mamani · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-10 — ABM de pacientes

**Administración completa de pacientes**

| | |
|---|---|
| CU11 — Administración de Pacientes | El administrador corrige datos demográficos, da de baja lógica registros duplicados y fusiona duplicados conservando el historial de ambos. |

**Prioridad: MEDIA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Corrección de los datos demográficos de cualquier paciente de la
   organización, incluidos los que el propio paciente no puede editar (US-05):
   documento y estado de la cuenta.
b) Alta manual de un paciente desde la web, para quien llega a ventanilla sin
   haberse registrado en la aplicación; genera ficha y, opcionalmente, cuenta de
   acceso con contraseña temporal.
c) **Baja lógica y nunca física.** Un paciente con historia clínica no se borra:
   se marca inactivo y deja de aparecer en las búsquedas y en la reserva.
d) Fusión de duplicados: se elige el registro que sobrevive, y las fichas,
   antecedentes y atenciones del otro se reasignan antes de inactivarlo. La
   operación es transaccional y reversible durante la misma sesión.
e) Cada corrección, baja y fusión queda en la bitácora de auditoría (US-06) con
   el valor anterior y el nuevo.
f) Autorización por `user.has_permission("patients.patient.write")`; el
   recepcionista, que comparte las pantallas de búsqueda, no alcanza estos
   verbos.

**Responsables:**
Web: Michael Mamani · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-11 — Gestión de sucursales

**Registro de las sucursales del centro médico**

| | |
|---|---|
| CU12 — Gestión de Sucursales | El administrador da de alta, edita y desactiva las sucursales de su organización con su dirección, teléfono y horario de atención. |

**Prioridad: ALTA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Alta de sucursal con nombre, dirección, teléfono y horario de atención por
   día de la semana, incluyendo el corte de mediodía cuando lo haya.
b) Edición y desactivación; una sucursal desactivada deja de ofrecerse en la
   reserva pero conserva su historial de atenciones.
c) Rechazo de la desactivación si la sucursal tiene fichas futuras
   confirmadas, con el detalle de cuáles, para que el administrador las
   reprograme antes en lugar de descubrirlo cuando el paciente llegue.
d) Nombre único por organización; dos centros médicos distintos sí pueden tener
   una sucursal llamada igual, porque la unicidad es por inquilino.
e) Coordenadas geográficas opcionales, que la aplicación móvil usará para
   ordenar las sucursales por cercanía en la búsqueda del Sprint 2.
f) Semilla de las tres sucursales del caso de estudio como datos de
   demostración **ficticios**, cargados por migración de datos y no a mano.

**Responsables:**
Web: José Daniel Iporo · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-12 — Especialidades y profesionales

**Catálogo médico: especialidades y profesionales**

| | |
|---|---|
| CU13 — Gestión de Especialidades y Profesionales | El administrador define el catálogo de especialidades y da de alta a los profesionales, asociando cada uno a una o más especialidades y a una o más sucursales. |

**Prioridad: ALTA** · **Cant Horas: 10 hr**

**Funcionalidades:**

a) ABM de especialidades con nombre y descripción. La descripción no es
   decorativa: es el texto que el chatbot del Sprint 4 recuperará por RAG para
   sugerir la especialidad adecuada, de modo que escribirla bien ahora evita
   reescribir el catálogo después.
b) Alta del profesional con sus datos, su matrícula y su cuenta de acceso con
   rol *Médico*, en una sola transacción.
c) Asociación **muchos a muchos** con especialidades: un profesional puede ser
   internista y gastroenterólogo a la vez.
d) Asociación **muchos a muchos** con sucursales, que es la que hace posible la
   disponibilidad consolidada de US-15: sin ella, un profesional que atiende en
   tres sedes serían tres registros distintos.
e) Desactivación del profesional sin borrarlo; sus atenciones pasadas siguen
   siendo consultables y firmadas por él.
f) Rechazo de la desactivación si tiene agenda con fichas futuras, con el mismo
   criterio que la sucursal.
g) Listado web con filtro por especialidad y por sucursal, base del buscador
   móvil de US-16.

**Responsables:**
Web: José Daniel Iporo · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-13 — Agendas médicas

**Definición de la agenda de cada profesional**

| | |
|---|---|
| CU14 — Gestión de Agendas Médicas | El administrador define la agenda de cada profesional por sucursal: días, franjas horarias, duración de consulta y cupo por franja. De esa definición se derivan los espacios reservables. |

**Prioridad: ALTA** · **Cant Horas: 16 hr**

Es la historia más grande del sprint y la que sostiene todo el Sprint 2: sin
espacios reservables no hay reserva, ni pago, ni comprobante.

**Funcionalidades:**

a) Definición de la agenda como **regla y no como lista**: profesional,
   sucursal, días de la semana, hora de inicio y fin, duración de consulta y
   cupo por franja. Guardar cada espacio suelto haría inmanejable el cambio de
   horario.
b) Derivación de los espacios reservables a partir de la regla, para un
   horizonte configurable de semanas hacia adelante.
c) Validación de solapamiento: un profesional no puede tener dos agendas que se
   pisen en el mismo día y hora, **ni siquiera en sucursales distintas**, porque
   no puede estar en dos sedes a la vez. Ésta es la validación que da sentido a
   la asociación muchos a muchos de US-12.
d) Respeto del horario de atención de la sucursal (US-11): una agenda no puede
   extenderse fuera del horario en que la sede está abierta.
e) Vigencia con fecha de inicio y de fin, de modo que cambiar el horario a
   partir de una fecha no altere las fichas ya reservadas bajo la regla
   anterior.
f) Cupo por franja mayor a uno para las especialidades que atienden por orden de
   llegada dentro de un bloque.
g) Vista de calendario semanal por profesional y por sucursal, que es donde el
   administrador realmente detecta un error de configuración.
h) Endpoint de espacios disponibles por profesional, sucursal y rango de fechas,
   que consumen US-15, US-16 y la reserva del Sprint 2. Es el contrato que hay
   que dejar cerrado antes de terminar el sprint.

**Responsables:**
Web: Luis Miguel Aguayo · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-14 — Bloqueo de agenda

**Bloqueo por vacaciones, feriado o ausencia**

| | |
|---|---|
| CU15 — Bloqueo de Agenda Médica | El administrador bloquea rangos de fecha y hora de la agenda de un profesional por vacaciones, feriado o ausencia. Los espacios bloqueados dejan de ofrecerse. |

**Prioridad: MEDIA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Bloqueo por rango de fechas completo —vacaciones— o por franja horaria de un
   día concreto —una ausencia de media mañana—.
b) Motivo tipificado: vacaciones, feriado, licencia o ausencia imprevista, que
   después alimenta el reporte de ocupación del Sprint 4.
c) Feriado a nivel de organización que se aplica a **todos** los profesionales
   de una vez, sin cargarlo profesional por profesional.
d) Los espacios bloqueados dejan de ofrecerse en la disponibilidad (US-15) y en
   la reserva, pero la regla de agenda no se toca: al levantar el bloqueo, la
   agenda vuelve sola.
e) Aviso explícito de las fichas ya reservadas que caen dentro del bloqueo, con
   su listado, para que el administrador decida reprogramarlas o cancelarlas.
   El sistema **no** las cancela por su cuenta.
f) Levantamiento del bloqueo antes de tiempo, que devuelve a la oferta los
   espacios no ocupados.

**Responsables:**
Web: Luis Miguel Aguayo · Móvil: — (caso de uso sólo web)

**Prototipo** (capturas web)

---

## US-15 — Disponibilidad consolidada

**Disponibilidad de un profesional entre las tres sucursales**

| | |
|---|---|
| CU16 — Consulta de Disponibilidad Médica | El paciente consulta la disponibilidad de un profesional a lo largo de todas las sucursales donde atiende, en una sola vista y para un rango de fechas. |

**Prioridad: ALTA** · **Cant Horas: 10 hr**

**Funcionalidades:**

a) Vista única con los espacios libres del profesional en **todas** las
   sucursales donde atiende, ordenados por fecha y hora y etiquetados con la
   sede. Es el caso que da nombre al proyecto: el paciente elige por
   conveniencia, no por sucursal.
b) Cálculo del espacio libre restando, a lo derivado de la agenda (US-13), los
   bloqueos (US-14) y las fichas ya reservadas.
c) Respuesta en **menos de 3 segundos** (RNF-02), lo que exige resolver el
   cálculo en una sola consulta por rango y no una por día: con tres sucursales
   y catorce días, el bucle ingenuo son cuarenta y dos idas a la base.
d) Filtro por sucursal y por rango de fechas, con un horizonte máximo
   configurable para que nadie pida un año de disponibilidad de una vez.
e) Exclusión de los espacios cuya hora de inicio ya pasó, calculada en la zona
   horaria de la sucursal y no en la del servidor.
f) Mismo endpoint para web y móvil, con la respuesta agrupada por día, que es
   como la dibuja la interfaz.
g) Espacios marcados como no reservables cuando el profesional o la sucursal
   están desactivados, sin que desaparezcan del cálculo, para que el paciente
   entienda por qué no puede reservar.

**Responsables:**
Web: Alexander Osinaga · Móvil: Alexander Osinaga

**Prototipo** (capturas, tanto web como móvil)

---

## US-16 — Búsqueda de profesionales

**Búsqueda de profesionales desde la aplicación móvil**

| | |
|---|---|
| CU17 — Búsqueda de Profesionales | El paciente busca profesionales por especialidad o por nombre y filtra por sucursal, viendo sólo a los activos de su organización. |

**Prioridad: ALTA** · **Cant Horas: 6 hr**

**Funcionalidades:**

a) Búsqueda por nombre del profesional —coincidencia parcial, sin distinguir
   mayúsculas ni tildes— y navegación por especialidad.
b) Filtro por sucursal, que se apoya en la asociación de US-12.
c) Resultados con el dato que decide la elección: nombre, especialidades,
   sucursales donde atiende y **próximo espacio disponible**, tomado del
   endpoint de US-15.
d) Sólo profesionales activos y de la organización del paciente; el catálogo de
   un centro médico no es visible desde otro (RNF-08).
e) Listado por especialidad como pantalla de entrada, para el paciente que no
   sabe a quién buscar pero sí qué necesita.
f) Paso directo desde el resultado a la disponibilidad del profesional (US-15),
   que en el Sprint 2 continúa en la reserva.
g) Búsqueda vacía que devuelve el catálogo completo paginado, en lugar de una
   pantalla en blanco.

**Responsables:**
Web: Alexander Osinaga · Móvil: Alexander Osinaga

**Prototipo** (capturas, tanto web como móvil)

---
