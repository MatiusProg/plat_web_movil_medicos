# Sprint 0 — Revisión y Retrospectiva

**Proyecto:** Plataforma Web y Móvil multi-tenant para la Gestión de Atención
Médica Ambulatoria en Centros Médicos Multifuncionales
**Grupo 15 · INF 412 - SA · Semestre 2-2026**
**Sprint 0:** del 18 al 24 de agosto de 2026 (7 días)

| Rol | Integrante |
|---|---|
| Product Owner | Osinaga Blanco, Alexander |
| Scrum Master | Hurtado Castro, Luis Mateo |
| Equipo de Desarrollo | Aguayo Quiroz, Luis Miguel · Iporo Chulque, José Daniel · Mamani Samurio, Michael Alexander · Ortega Mancilla, Karen Paola |

---

# 4. Revisión del Sprint / Sprint Review

> Los miembros del equipo y los clientes se reúnen para mostrar el trabajo de
> desarrollo de software que se ha completado. Se hace una demostración de todos
> los requerimientos finalizados dentro del Sprint. La presentación está a cargo
> del **Scrum Master y el Product Owner**.

**Fecha:** 24 de agosto de 2026
**Presentan:** Luis Mateo Hurtado Castro (Scrum Master) y Alexander Osinaga
Blanco (Product Owner)
**Asisten:** el Equipo de Desarrollo en pleno

## 4.1 Objetivo del Sprint y grado de cumplimiento

> **Objetivo comprometido:** desarrollar las funcionalidades que permiten dar de
> alta a nuevas organizaciones y clientes, asignarles un plan de suscripción,
> permitir a cualquier usuario registrarse e iniciar sesión, y al administrador
> crear y asignar roles.

El objetivo se cumplió **parcialmente**. Las cuatro primeras capacidades quedaron
operativas y demostrables; la quinta —crear y asignar roles— no se completó.

## 4.2 Historias comprometidas y entregadas

| ID | Historia | SP | Responsable | Estado |
|---|---|---|---|---|
| US-43 | Registrar una nueva organización como inquilino independiente | 5 | Luis Mateo Hurtado | ✅ **Terminada** |
| US-44 | Definir y asignar planes de suscripción (Básico, Pro, Premium) | 5 | José Daniel Iporo | ✅ **Terminada** |
| US-45 | Panel de métricas globales de la plataforma | 5 | Luis Miguel Aguayo | ✅ **Terminada** |
| US-01 | Registro de paciente con documento y datos básicos | 5 | Alexander Osinaga | ✅ **Terminada** |
| US-02 | Inicio de sesión con credenciales, según el rol | 3 | Karen Ortega | ✅ **Terminada** |
| US-04 | Crear y asignar roles (Paciente, Médico, Recepcionista, Administrador) | 5 | Michael Mamani | ❌ **No completada** |

**Resultado: 5 de 6 historias terminadas — 23 de 28 story points (82 %).**

Las cinco historias terminadas cumplen los seis criterios de la Definición de
Terminado acordada en el Sprint Planning, incluido el criterio 4, que es el más
exigente del proyecto: toda tabla con discriminador de inquilino tiene
`ENABLE` y `FORCE ROW LEVEL SECURITY`, y existe una prueba que verifica que una
organización no ve los datos de otra.

## 4.3 Demostración del incremento

Todo lo que sigue se mostró **funcionando contra el entorno real** —backend en
`localhost:8000`, base PostgreSQL con las políticas de aislamiento activas— y no
sobre diapositivas ni prototipos. Las capturas de lo demostrado
están en [`evidencias/`](evidencias/).

**1. Alta de una organización (US-43).** Se registra un centro médico nuevo con
sus datos institucionales, y el sistema le clona las plantillas de rol para que
su administrador pueda ajustarlas sin afectar a los demás. El alta no se
completa si la organización queda sin rol de administrador.

**2. Planes de suscripción (US-44).** Se define y asigna un plan a la
organización recién creada, con sus límites de usuarios, sucursales, citas
mensuales y consultas de IA.

**3. Panel de métricas de plataforma (US-45).** El superadministrador consulta
el estado global: organizaciones activas, uso por plan y alertas de aislamiento.

**4. Registro de paciente (US-01).** Un paciente se da de alta y el sistema le
crea, en una sola transacción, la cuenta de acceso, la asignación del rol
Paciente y la ficha demográfica.

**5. Inicio de sesión (US-02).** Se demostró el ciclo completo y sus caminos de
error, que es donde está el trabajo real de la historia:

- Ingreso correcto: el sistema devuelve el token junto con **los roles y
  permisos** del usuario, que es lo que permite que cada quien vea sólo sus
  funciones.
- Contraseña incorrecta y correo inexistente devuelven **exactamente la misma
  respuesta**: desde el formulario no se puede averiguar qué correos están
  registrados.
- **RNF-07 en vivo:** cinco intentos fallidos bloquean la cuenta quince minutos,
  y no entra ni con la contraseña correcta.
- Cierre de sesión: el token de refresco queda invalidado y la sesión no se
  puede renovar.

Se mostró además la **pantalla web** de inicio de sesión, primer entregable
visual del proyecto: es la primera vez que el sistema se ve como un producto y
no como una API.

**6. El aislamiento entre organizaciones (RNF-08).** Se demostró que un usuario
válido de un centro médico **no puede entrar** usando el identificador de otro, y
que dos centros médicos pueden tener al mismo correo registrado sin interferirse.
Esto no se ve en una pantalla: se verifica con la suite de pruebas.

## 4.4 Estado técnico del incremento

| Indicador | Valor |
|---|---|
| Pruebas automatizadas en verde | **101** |
| Migraciones de base de datos aplicadas | 6 |
| Pull requests revisados y fusionados | 3 (#3, #4 y #5) |
| Defectos detectados y corregidos | 13 |
| Motores verificados | PostgreSQL 16, 17 y 18, y Supabase |

Ninguna historia se dio por terminada sin revisión de una persona distinta de
quien escribió el código, según el punto 4 de la Definición de Terminado.

## 4.5 Decisión sobre el trabajo no completado

**US-04 (crear y asignar roles, 5 SP) no se completó y no se demostró.** El
lugar donde va su código está reservado y documentado en las convenciones
—`accounts/views/roles.py`, `accounts/serializers/roles.py`— pero los archivos no
existen, y tampoco su archivo de pruebas.

**Impacto acotado.** El modelo de datos que la historia necesita ya está
construido y probado por las otras historias: las tablas `roles`,
`role_permissions` y `user_roles` existen, tienen sus políticas de aislamiento
y las plantillas de rol se siembran automáticamente. US-01 ya asigna el rol
Paciente y US-02 ya lee roles y permisos para devolverlos al iniciar sesión. Lo
que falta es la interfaz de administración, no los cimientos.

**Decisión del Product Owner:** US-04 vuelve al Product Backlog y se replanifica
como primer elemento del Sprint 1, antes que las historias nuevas. La razón es
de dependencia, no de castigo: US-06 (bitácora de auditoría) audita justamente la
asignación de roles, y el resto de la Épica 1 asume que los roles se pueden
administrar.

## 4.6 Métrica para planificar el Sprint 1

La **velocidad demostrada del Sprint 0 es de 23 story points** en siete días.

Conviene mirar ese número contra el Sprint 1, que hoy tiene **51 SP**
comprometidos (US-03, US-05, US-06 y US-07 a US-16) más los 5 SP que arrastra
US-04: **56 SP en total, más del doble de lo que el equipo demostró poder
entregar.**

Es la primera vez que existe un dato de velocidad real, y el Sprint Planning
debería usarlo para ajustar el compromiso o confirmar que el Sprint 1 dispone de
bastante más tiempo de calendario. Comprometerse otra vez con el doble de la
capacidad demostrada es la forma más segura de repetir una historia sin terminar.

---

# 5. Retrospectiva del Sprint / Retrospective

> En este evento el **Product Owner se reúne con todo su equipo de trabajo y su
> Scrum Master** para hablar sobre lo ocurrido durante el Sprint.

**Fecha:** 24 de agosto de 2026 · **Participan:** los seis integrantes

## 5.1 Qué se hizo bien

*Para seguir en la misma senda del éxito.*

**1. El aislamiento entre organizaciones se construyó primero, y en dos capas.**
Fue la decisión más importante del sprint. El discriminador de inquilino existe
desde la primera tabla, y la protección está tanto en la aplicación como en la
base de datos con Row Level Security. Incorporarlo después habría obligado a
migrar el modelo entero. Hoy, si alguien olvida un filtro, la base no entrega
las filas igual.

**2. Se acordaron convenciones de código antes de abrir las ramas.** Se definió
qué va en cada módulo, cómo se nombra cada cosa y —clave— la **regla del archivo
compartido**: si dos personas van a tocar el mismo archivo en el mismo sprint, se
parte en un paquete *antes* de empezar. Tres personas trabajaron sobre la misma
app `accounts` durante todo el sprint y **no hubo un solo conflicto de merge**.

**3. La revisión cruzada encontró defectos que las pruebas no veían.** La
revisión del backend destapó que las 21 pruebas existentes pasaban con un
backend que **ni siquiera arrancaba**, porque ninguna entraba por el ciclo HTTP.
De ahí salieron seis defectos encadenados, uno de los cuales cambió el diseño de
la autenticación. Es la mejor evidencia de que el punto 4 de la Definición de
Terminado —revisar el código de otra persona— no es un trámite.

**4. Cada defecto quedó documentado con su causa y su corrección.** Los trece
defectos están en `docs/registro-de-defectos.md` con síntoma, causa, corrección
y la prueba que fallaba antes. De ahí salieron seis reglas técnicas que ya
evitaron que los mismos errores se repitieran.

**5. Nadie dio una historia por terminada sin pruebas.** Las 101 pruebas
automatizadas no son un adorno: cada una de las cinco historias terminadas suma
pruebas que entran por HTTP, como lo haría un cliente real.

**6. El equipo se destrabó solo cuando una máquina no podía correr Docker.** En
vez de frenar, se documentó y verificó una alternativa completa con PostgreSQL
instalado directamente. Nadie perdió días esperando.

## 5.2 Qué se hizo mal

*Para poder mejorar el próximo Sprint.*

**1. El trabajo se concentró en los dos últimos días de siete.** El historial del
repositorio lo muestra sin lugar a dudas: en todo el Sprint hubo commits **sólo
tres días —el 19, el 23 y el 24—**, y el del 19 fue apenas la estructura inicial
del repositorio. Cuatro de los siete días no registran una sola línea. Un sprint
que se ejecuta en el último 30 % de su duración no tiene margen para absorber
ningún imprevisto, y es la causa de fondo de casi todo lo demás en esta lista.

**2. Una historia comprometida no se entregó, y el equipo se enteró tarde.** El
problema no es sólo que US-04 no esté: es que **nadie lo supo hasta el final**.
Con un tablero al día o un Daily efectivo, una historia en riesgo se detecta el
tercer día, cuando todavía se puede pedir ayuda, repartir el trabajo o negociar
el alcance con el Product Owner. Detectarlo el último día no deja ninguna
alternativa. En Scrum el compromiso del Sprint es del equipo completo, así que
esto es una falla del equipo en hacer visible el avance, no de una persona.

**3. El Daily Scrum no se sostuvo.** El registro del Daily está completo para
algunos integrantes y prácticamente vacío para otros, y varios días quedaron sin
llenar. El Daily es exactamente el mecanismo que debía haber detectado el punto
anterior; sin él, el equipo trabajó a ciegas respecto del avance de los demás.

**4. El tablero de tareas no se usó.** El Sprint Backlog quedó sin desglosar en
tareas con responsable, estimación y estado. Sin tablero no hay columnas "Por
hacer / Haciendo / Terminado", y sin esas columnas nadie puede ver que algo
lleva cinco días en la primera.

**5. El modelo se validó con el usuario equivocado.** Todo el SQL inicial se
probó como `postgres`, que es superusuario y **omite las políticas de
aislamiento aunque estén activas**. Las pruebas pasaban sin verificar nada.
Repetir exactamente las mismas pruebas como el usuario real de la aplicación
destapó cinco defectos, cuatro de los cuales bloqueaban una historia. Fue un
error de método, no de código.

**6. La documentación quedó por detrás del código.** Cuatro guías del proyecto
tenían instrucciones equivocadas o incompletas. Una guía errónea cuesta lo mismo
que un defecto: hace perder horas a quien la sigue.

## 5.3 Qué inconvenientes se encontraron

*Y no permitieron avanzar como se tenía planificado.*

**1. Desconocimiento inicial del modelo multi-inquilino.** Ninguna persona del
equipo había construido antes una aplicación multi-tenant con aislamiento a
nivel de base de datos. Los primeros días se fueron en estudiar el concepto
antes de poder escribir una línea, y eso explica buena parte del arranque lento.

**2. El aislamiento por Row Level Security falla en silencio.** Es la
característica más difícil de este proyecto: cuando algo está mal configurado, la
base **no da error** — devuelve cero filas, o las devuelve todas. Seis de los
trece defectos fueron de este tipo. Se necesitaron tres rondas de pruebas con
enfoques distintos para encontrarlos.

**3. Limitaciones de hardware en el equipo.** No todas las máquinas del equipo
pueden correr Docker con comodidad, que era el entorno previsto. Se resolvió con
una guía alternativa verificada, pero consumió tiempo de un sprint corto.

**4. Un choque de tecnologías que obligó a fijar versiones.** La librería de
autenticación por tokens sólo declara soporte hasta Django 5.2, y esa versión no
cubre Python 3.14. Hubo que fijar Python 3.13 para los seis integrantes y
documentar el porqué, porque la falla aparecería justo en la pieza que autentica
a todo el sistema.

**5. Las fechas de los sprints vienen impuestas por el calendario académico.**
Su duración no es uniforme y el equipo no puede negociarla. El Sprint 0 tuvo
siete días para 28 story points. Es una restricción real que hay que compensar
ajustando el compromiso, no el esfuerzo del último día.

## 5.4 Acciones concretas para el Sprint 1

Una retrospectiva sin acciones es una conversación. Estos son los compromisos
que el equipo asume, con responsable y forma de verificarlos:

| # | Acción | Responsable | Cómo se verifica |
|---|---|---|---|
| 1 | **US-04 entra primero** en el Sprint 1, antes que cualquier historia nueva | Product Owner | Está al tope del Sprint Backlog |
| 2 | **Desglosar el Sprint Backlog en tareas** con responsable, estimación y estado, en el Sprint Planning y no después | Scrum Master | El tablero tiene tarjetas el día 1 |
| 3 | **Daily de 15 minutos, mismo horario**, con las tres preguntas y registro escrito | Todo el equipo | El acta del Daily no tiene días vacíos |
| 4 | **Regla del tercer día:** quien no haya abierto su rama al tercer día lo declara en el Daily, y el equipo redistribuye | Todo el equipo | Todas las ramas abiertas al día 3 |
| 5 | **Ajustar el compromiso del Sprint 1** a la velocidad demostrada (23 SP) o confirmar que hay más días de calendario | Scrum Master y PO | Acta del Sprint Planning |
| 6 | **Toda prueba de aislamiento se corre como el usuario de la aplicación**, nunca como superusuario | Todo el equipo | Ya está en las convenciones |
| 7 | **Acordar el idioma del código del frontend**, que hoy difiere del backend, mientras el cambio siga siendo barato | Todo el equipo | Queda escrito en las convenciones |
| 8 | **Resolver pgvector antes del Sprint 3**, no el día que haga falta | Scrum Master | Verificado antes de que empiece |

---

## Conclusión del Sprint 0

El Sprint 0 entregó **82 % de lo comprometido** y, sobre todo, entregó lo más
difícil de incorporar después: el aislamiento entre organizaciones, verificado en
dos capas y respaldado por 101 pruebas automatizadas. La plataforma hoy puede dar
de alta un centro médico, asignarle un plan, registrar pacientes y autenticarlos
según su rol.

Lo que falló no fue técnico sino de **visibilidad**: el equipo no supo a tiempo
que una historia estaba en riesgo. Las acciones 2, 3 y 4 de la tabla anterior
atacan exactamente ese punto, y son las que hay que sostener en el Sprint 1.
