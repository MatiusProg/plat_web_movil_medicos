# De puntos de historia a horas — cambios para el documento

> **Para qué es este archivo.** La docente pidió que la estimación deje de
> expresarse en puntos de historia y pase a horas. Los puntos aparecen en
> **seis lugares** del documento, no sólo en las tablas del backlog, y dos de
> ellos son párrafos que hoy argumentan justamente lo contrario de lo que se
> va a hacer.
>
> Cada cambio va con el texto actual y el texto propuesto, para que puedas
> pegarlo directo en Word y ajustar lo que quieras. Nada de esto está aplicado
> todavía en el `.docx`.

---

## 0. La regla de conversión

**1 punto de historia = 3 horas-persona.**

No es un factor elegido al azar: sale de la capacidad real del Sprint 0.
Seis integrantes, siete días (18 al 24 de agosto) y 28 puntos comprometidos.
Con el factor 3 eso da 84 horas, es decir **2 horas por persona y por día**,
que es la dedicación realista de seis estudiantes que cursan otras materias.
Con factor 2 daría 1,3 h/día —por debajo de lo que realmente se trabajó— y con
factor 4, 2,7 h/día.

El backlog usa sólo cuatro valores de la escala, así que la conversión entera
son cuatro reglas:

| Puntos | Horas | Cuántas historias |
|---|---|---|
| 2 | 6 h | 1 |
| 3 | 9 h | 14 |
| 5 | 15 h | 22 |
| 8 | 24 h | 8 |

---

## 1. §1.2.6 — Historias de usuario y estimación

Es el cambio más importante: el párrafo actual **defiende** estimar en puntos
y no en horas. Si se cambian las tablas y se deja este texto, el documento se
contradice a sí mismo.

### Texto actual

> La estimación se realiza en story points, una medida relativa de esfuerzo
> que combina complejidad, volumen de trabajo e incertidumbre, en lugar de
> horas absolutas. Se emplea la escala de Fibonacci (1, 2, 3, 5, 8, 13), cuyos
> saltos crecientes reflejan que la precisión disminuye conforme aumenta el
> tamaño: distinguir entre 1 y 2 puntos es posible, entre 20 y 21 no lo es. La
> suma de puntos completados por Sprint constituye la velocidad del equipo,
> dato empírico que permite proyectar cuánto trabajo puede comprometerse en
> los siguientes.

### Texto propuesto

> La estimación se expresa en **horas-persona**: las horas de trabajo que un
> integrante dedica a completar la historia, incluyendo el análisis, la
> implementación y las pruebas.
>
> La alternativa habitual en Scrum es la estimación relativa en puntos de
> historia, que mide complejidad e incertidumbre sin comprometerse con una
> duración. El equipo la adoptó al planificar y la sustituyó por horas por una
> razón práctica: un punto sólo se vuelve interpretable cuando existe una
> velocidad histórica contra la cual leerlo, y un equipo que se forma por
> primera vez no la tiene. Sin ese referente, el número relativo no permitía
> verificar lo único que hay que verificar al cerrar una planificación: si el
> trabajo comprometido cabe en la capacidad disponible.
>
> La hora sí lo permite. La capacidad de un Sprint es el producto de los
> integrantes por los días que dura por las horas diarias que cada uno puede
> dedicar, y el compromiso es admisible únicamente si no la excede. Ese
> contraste —capacidad contra compromiso— es el que da sentido a la
> planificación y el que se documenta en el apartado 3.11.
>
> Las estimaciones ya realizadas se convirtieron con la equivalencia empírica
> de **tres horas por punto**, obtenida del propio Sprint 0: veintiocho puntos
> comprometidos, seis integrantes y siete días de Sprint equivalen a ochenta y
> cuatro horas, es decir dos horas por persona y por día.
>
> La suma de horas completadas por Sprint constituye la velocidad del equipo,
> dato empírico que permite proyectar cuánto trabajo puede comprometerse en
> los siguientes.

> **Por qué conviene contar el cambio en vez de disimularlo.** Es más sólido
> explicar por qué se cambió de criterio que reescribir el documento como si
> siempre se hubiera estimado en horas. Un tribunal que ve un equipo corregir
> su método a mitad de camino, y sostener el porqué, lee madurez; uno que
> encuentra una contradicción entre el marco teórico y las tablas, lee
> descuido.

---

## 2. §3.4 — Definiciones, acrónimos y abreviaturas

Hay dos entradas de glosario que quedan colgadas.

### Entrada «Story Point»

**Actual:**

> **Story Point** — Unidad relativa de estimación del esfuerzo de una historia
> de usuario "SP", en escala Fibonacci (1, 2, 3, 5, 8, 13).

**Propuesta —** reemplazarla por:

> **Hora-persona** — Unidad de estimación del esfuerzo de una historia o de
> una tarea: las horas de trabajo de un integrante necesarias para
> completarla, incluyendo análisis, implementación y pruebas. Sustituye a la
> estimación relativa en puntos de historia; el criterio y su motivo están en
> el apartado 1.2.6.

### Entrada «Story»

**Actual:**

> **Story** — Ver Historia de Usuario / Story Point.

**Propuesta:**

> **Story** — Ver Historia de Usuario.

> **Alternativa,** si preferís no borrar el término: dejar la entrada de Story
> Point redactada en pasado —"unidad relativa… utilizada en la planificación
> inicial y sustituida por la hora-persona, ver 1.2.6"—. Tiene la ventaja de
> que el lector que encuentre "SP" en una captura vieja de Jira sepa qué era.

---

## 3. §2.9 y §2.11 — Comparación de herramientas

Acá hay **cuatro menciones**. Ninguna es falsa —Jira efectivamente tiene
puntos de historia—, pero tres de ellas se usan como *argumento* para elegir
Jira, y quedan raras si el proyecto ya no los usa. La cuarta es una celda de
tabla que describe la herramienta y podría quedarse igual.

| # | Dónde | Actual | Propuesto |
|---|---|---|---|
| 1 | Tabla, fila **Trello** | "Sin sprints, story points ni gráfico burndown de forma nativa; requiere extensiones" | "Sin sprints, **estimación** ni gráfico burndown de forma nativa; requiere extensiones" |
| 2 | Tabla, fila **Jira** | "backlog, sprints, épicas, story points y generación automática de burndown y velocidad" | "backlog, sprints, épicas, **estimación configurable en puntos o en horas** y generación automática de burndown y velocidad" |
| 3 | Párrafo "Se adopta Jira por tres razones" | "cuarenta y cinco historias de usuario con prioridad MoSCoW, estimación en story points y asignación a cinco sprints" | "cuarenta y cinco historias de usuario con prioridad MoSCoW, **estimación en horas** y asignación a cinco sprints" |
| 4 | Párrafo "Una ventaja secundaria pero real" | "el vocabulario de Scrum —épica, sprint, backlog, story point— está incorporado en la propia interfaz" | "el vocabulario de Scrum —épica, sprint, backlog, **incremento**— está incorporado en la propia interfaz" |
| 5 | Tabla resumen §2.12 | "Sprints, story points y burndown nativos" | "Sprints, **estimación** y burndown nativos" |

> **Dato que refuerza el punto 2 y conviene verificar en Jira antes de
> escribirlo:** la unidad de estimación es configurable por proyecto — se puede
> elegir entre puntos de historia y tiempo. Si es así en el proyecto de
> ustedes, decirlo fortalece la elección de la herramienta en vez de
> debilitarla, porque muestra que la decisión de estimar en horas no obligó a
> cambiar de herramienta. Confirmalo en la configuración del tablero antes de
> afirmarlo en el documento.

---

## 4. §3.11 — Planificación de Sprints

Reemplazar la columna **SP** por **Horas**:

| Sprint | Fechas de entrega | Historias | Antes (SP) | Ahora (horas) |
|---|---|---|---|---|
| Sprint 0 | 18/08 – 24/08 | 6 | 28 | **84 h** |
| Sprint 1 | 25/08 – 10/09 | 13 | 51 | **153 h** |
| Sprint 2 | 11/09 – 08/10 | 9 | 50 | **150 h** |
| Sprint 3 | 09/10 – 05/11 | 9 | 50 | **150 h** |
| Sprint 4 | 06/11 – 26/11 | 8 | 39 | **117 h** |
| **Total** | | **45** | **218** | **654 h** |

### Esto hay que resolverlo antes de poner las horas

Con puntos, nadie puede decir "eso no da". Con horas sí: se multiplica
integrantes × días × horas diarias y se compara. **Es la primera cuenta que va
a hacer la docente.**

| Sprint | Horas | Días | h/persona/día |
|---|---|---|---|
| Sprint 0 | 84 h | 7 | **2,0** |
| Sprint 1 | 153 h | 17 | **1,5** |
| Sprint 2 | 150 h | 28 | **0,9** |
| Sprint 3 | 150 h | 28 | **0,9** |
| Sprint 4 | 117 h | 21 | **0,9** |

Los números cierran **sólo si cada Sprint abarca el período entre entregas**,
que es como están calculados arriba. Si se leyeran como los tres días que hoy
figuran en el diagrama de Gantt, el Sprint 1 pediría 153 horas en 3 días entre
6 personas: **8,5 horas por persona y por día**, que es imposible y salta a
simple vista.

El apartado 1.2.7 ya dice que "cada Sprint transcurre entre una revisión y la
siguiente", así que el criterio está escrito y es correcto. Lo que falta es que
**las fechas de inicio y fin de cada Sprint queden explícitas en la tabla de
§3.11**, y no sólo las de entrega. Es un cambio chico que cierra el flanco.

---

## 5. §3.6 — Product Backlog

Reemplazar la columna **SP** por **Horas**. Las 45 filas convertidas:

| ID | Sprint | Rol | Característica / Funcionalidad | Prioridad | Antes (SP) | **Ahora (h)** |
|---|---|---|---|---|---|---|
| US-01 | Sprint 0 | Paciente | Registrarse con número de documento y datos básicos para acceder a la aplicación móvil. | 🔴 | 5 | **15 h** |
| US-02 | Sprint 0 | Usuario registrado | Iniciar sesión con sus credenciales para acceder a las funciones según su rol. | 🔴 | 3 | **9 h** |
| US-03 | Sprint 1 | Usuario | Recuperar su contraseña para no perder el acceso a su cuenta. | 🟡 | 3 | **9 h** |
| US-04 | Sprint 0 | Administrador | Crear y asignar roles de Paciente, Médico, Recepcionista y Administrador para controlar permisos. | 🔴 | 5 | **15 h** |
| US-05 | Sprint 1 | Usuario | Editar su perfil, datos de contacto y contraseña para mantener su información actualizada. | 🟡 | 2 | **6 h** |
| US-06 | Sprint 1 | Administrador | Consultar una bitácora de auditoría sobre acciones sensibles para garantizar trazabilidad y seguridad. | 🟡 | 5 | **15 h** |
| US-07 | Sprint 1 | Titular | Registrar familiares a cargo para poder agendarles citas. | 🔴 | 5 | **15 h** |
| US-08 | Sprint 1 | Paciente / Titular | Registrar antecedentes relevantes, como alergias y condiciones crónicas, para que el médico los tenga presentes. | 🟡 | 3 | **9 h** |
| US-09 | Sprint 1 | Recepcionista | Buscar y filtrar pacientes por nombre o documento para atenderlos rápidamente. | 🔴 | 3 | **9 h** |
| US-10 | Sprint 1 | Administrador | Realizar el ABM de pacientes desde la web para corregir datos o dar de baja registros duplicados. | 🟡 | 3 | **9 h** |
| US-11 | Sprint 1 | Administrador | Registrar las sucursales del centro médico con dirección, teléfono y horario. | 🔴 | 3 | **9 h** |
| US-12 | Sprint 1 | Administrador | Registrar especialidades y profesionales y asociarlos a una o más sucursales. | 🔴 | 5 | **15 h** |
| US-13 | Sprint 1 | Administrador | Definir las agendas de cada profesional con días, horarios, duración y cupos. | 🔴 | 8 | **24 h** |
| US-14 | Sprint 1 | Administrador | Bloquear la agenda de un profesional por vacaciones, feriados o ausencias. | 🟡 | 3 | **9 h** |
| US-15 | Sprint 1 | Paciente | Ver la disponibilidad consolidada de un profesional entre las tres sucursales. | 🔴 | 5 | **15 h** |
| US-16 | Sprint 1 | Paciente | Buscar profesionales por especialidad o nombre desde la aplicación móvil. | 🔴 | 3 | **9 h** |
| US-17 | Sprint 2 | Paciente | Reservar una ficha seleccionando sucursal, profesional, fecha y hora. | 🔴 | 8 | **24 h** |
| US-18 | Sprint 2 | Paciente | Pagar la ficha en línea mediante Stripe al momento de la reserva. | 🔴 | 8 | **24 h** |
| US-19 | Sprint 2 | Paciente | Recibir un comprobante digital con código QR único después de pagar la ficha. | 🔴 | 5 | **15 h** |
| US-20 | Sprint 2 | Paciente | Cancelar o reprogramar una ficha dentro de la política de anticipación permitida. | 🟡 | 5 | **15 h** |
| US-21 | Sprint 2 | Paciente | Confirmar su asistencia antes de la cita mediante una notificación. | 🟡 | 3 | **9 h** |
| US-22 | Sprint 2 | Recepcionista | Registrar el check-in del paciente verificando su código QR o documento. | 🔴 | 3 | **9 h** |
| US-23 | Sprint 2 | Recepcionista | Agendar y cobrar fichas de forma asistida para pacientes que llegan sin reserva previa. | 🟡 | 5 | **15 h** |
| US-24 | Sprint 2 | Médico | Registrar la atención del paciente, incluyendo motivo, evolución, diagnóstico, indicaciones y tratamiento. | 🔴 | 8 | **24 h** |
| US-25 | Sprint 2 | Médico | Consultar el historial clínico longitudinal del paciente entre las diferentes sucursales. | 🔴 | 5 | **15 h** |
| US-26 | Sprint 3 | Médico | Emitir recetas digitales y órdenes de laboratorio o estudios. | 🟡 | 5 | **15 h** |
| US-27 | Sprint 3 | Paciente | Consultar su historial clínico, recetas e indicaciones desde la aplicación móvil. | 🔴 | 3 | **9 h** |
| US-28 | Sprint 3 | Paciente | Recibir notificaciones push y correo sobre confirmaciones, recordatorios y cancelaciones. | 🟡 | 5 | **15 h** |
| US-29 | Sprint 3 | Administrador | Visualizar un panel de KPIs sobre ocupación, inasistencia, demanda e ingresos. | 🔴 | 8 | **24 h** |
| US-30 | Sprint 3 | Administrador | Exportar reportes operativos a PDF y Excel. | 🟡 | 3 | **9 h** |
| US-31 | Sprint 3 | Paciente | Describir síntomas a un chatbot y recibir una sugerencia de especialidad. | 🔴 | 8 | **24 h** |
| US-32 | Sprint 3 | Paciente | Consultar al chatbot sobre horarios, sucursales, costos y preparación de estudios. | 🟡 | 5 | **15 h** |
| US-33 | Sprint 3 | Paciente | Completar la reserva de una ficha mediante conversación con el chatbot. | 🟡 | 8 | **24 h** |
| US-34 | Sprint 3 | Paciente | Ser derivado inmediatamente a atención de emergencia cuando el chatbot detecte síntomas de alarma. | 🔴 | 5 | **15 h** |
| US-35 | Sprint 4 | Administrador | Clasificar cada cita según el riesgo bajo, medio o alto de inasistencia. | 🔴 | 8 | **24 h** |
| US-36 | Sprint 4 | Sistema | Enviar recordatorios reforzados a pacientes con alto riesgo de inasistencia. | 🟡 | 5 | **15 h** |
| US-37 | Sprint 4 | Administrador | Consultar la proyección de demanda de fichas por especialidad y franja horaria. | 🟢 | 5 | **15 h** |
| US-38 | Sprint 4 | Equipo de Desarrollo | Reentrenar periódicamente el modelo de no-show con datos reales. | 🟢 | 5 | **15 h** |
| US-39 | Sprint 4 | Paciente | Recibir un resumen de su consulta en lenguaje claro y sin tecnicismos. | 🟡 | 5 | **15 h** |
| US-40 | Sprint 4 | Paciente | Recibir instrucciones de preparación previa para estudios de laboratorio o imagenología. | 🟢 | 3 | **9 h** |
| US-41 | Sprint 4 | Médico | Recibir un resumen sintético del historial del paciente antes de una nueva consulta. | 🟢 | 5 | **15 h** |
| US-42 | Sprint 4 | Médico | Validar o editar cualquier texto generado por IA antes de enviarlo al paciente. | 🔴 | 3 | **9 h** |
| US-43 | Sprint 0 | Superadministrador de Plataforma | Registrar una nueva organización o centro médico cliente como tenant independiente. | 🔴 | 5 | **15 h** |
| US-44 | Sprint 0 | Superadministrador de Plataforma | Definir y asignar planes de suscripción Básico, Pro y Premium a cada organización. | 🟡 | 5 | **15 h** |
| US-45 | Sprint 0 | Superadministrador de Plataforma | Visualizar un panel con métricas globales de las organizaciones activas. | 🟢 | 5 | **15 h** |
| **Total** | | | **45 historias** | | **218** | **654 h** |

---

## 6. Capítulo 4 — Sprint Backlog

La tabla del Sprint Backlog tiene columna **Estimación**, y ahí no van las
horas de la *historia* sino las de cada **tarea**: una historia de 15 horas se
reparte entre análisis, implementación, pruebas y documentación.

Esa tabla está vacía todavía. Se puede llenar con las tareas **reales** del
Sprint 0 —lo que efectivamente se hizo, quién lo hizo y contra qué historia—
porque todo eso está en el repositorio: los commits, las ramas, los pull
requests y las pruebas. Es la parte del capítulo que más conviene que salga de
datos ciertos y no de memoria.

---

## Checklist

- [ ] §1.2.6 — reemplazar el párrafo de estimación
- [ ] §3.4 — entrada «Story Point» → «Hora-persona»
- [ ] §3.4 — entrada «Story», quitar la referencia cruzada
- [ ] §2.9 — tabla comparativa, filas Trello y Jira
- [ ] §2.9 — párrafo "Se adopta Jira por tres razones"
- [ ] §2.9 — párrafo "Una ventaja secundaria pero real"
- [ ] §2.12 — tabla resumen de decisiones tecnológicas
- [ ] §3.6 — columna SP → Horas, 45 filas
- [ ] §3.11 — columna SP → Horas, 5 filas
- [ ] §3.11 — agregar fechas de inicio y fin de cada Sprint
- [ ] Capítulo 4 — columna Estimación del Sprint Backlog
- [ ] Revisar que no queden "SP" sueltos: buscar `SP`, `story point` y `Fibonacci` en todo el documento
