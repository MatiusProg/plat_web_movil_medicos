# Capítulo 4 — Sprint 2: lo que ya se puede escribir

**Estado al 16/09/2026.** El Sprint 2 va del **12/09 al 05/10**, con revisión el
06–08/10. Estamos en el día 5 de 24, así que hay apartados que todavía no
tienen con qué llenarse: se dicen abajo, en la sección final, para que nadie los
busque dos veces.

La sección del Sprint 2 en el Word está hoy **copiada del Sprint 0**: los
objetivos hablan de alta de organizaciones y las historias que figuran son
US-01, US-02, US-43, US-44 y US-45. Todo lo de acá **reemplaza** ese contenido.

Fuente de los datos: `docs/sprints/sprint-2/reparto.md`, que es el contrato del
sprint.

---

## 1.1 Objetivos del Sprint

> Cerrar el **circuito completo de la ficha médica** —reservarla, pagarla en
> línea, presentarse en el centro y ser atendido, quedando registro clínico de
> esa atención— y **adelantar el subsistema de inteligencia artificial**, que la
> planificación original ubicaba en el Sprint 3, de modo que el asistente de
> orientación funcione sobre el catálogo real de cada organización.
>
> El adelanto del subsistema de IA responde a un criterio explícito: **entran
> las historias de IA que ya tienen sus datos**. El corpus del asistente son las
> descripciones de especialidades cargadas en US-12 durante el Sprint 1, de modo
> que US-31, US-32 y US-34 pueden construirse ahora. En cambio, la predicción de
> inasistencia (US-35 a US-38) necesita fichas con resultado *asistió / no
> asistió*, dato que recién empieza a existir cuando US-21 y US-22 estén
> corriendo, y la generación de resúmenes (US-39 a US-42) depende del encuentro
> clínico que este mismo sprint construye.
>
> Para dar lugar a las tres historias de IA, **US-23** (agendamiento asistido en
> mostrador) y **US-33** (reserva conversacional) se trasladan al Sprint 3. El
> total del proyecto no cambia: son las mismas 436 horas, reubicadas.
>
> El sprint compromete **142 horas** entre cinco integrantes —28,4 horas de
> promedio, aproximadamente 1,2 horas por día y por persona sobre 24 días
> corridos, por debajo del ritmo sostenido en el Sprint 1—.

---

## 1.2 Historias de Usuario

Son **catorce**: las ocho del Sprint 2 planificado que se conservan, las tres de
arrastre del Sprint 1 y las tres del asistente adelantadas del Sprint 3.

| ID | Historia | Épica | Prioridad | Horas | Responsable |
|---|---|---|---|---|---|
| US-17 | Reserva de ficha | Agendamiento | Must have | 16 | Aguayo Quiroz, L. M. |
| US-18 | Pago en línea con Stripe | Agendamiento | Must have | 16 | Osinaga Blanco, A. |
| US-19 | Comprobante digital con QR | Agendamiento | Must have | 10 | Osinaga Blanco, A. |
| US-20 | Cancelación y reprogramación | Agendamiento | Should have | 10 | Aguayo Quiroz, L. M. |
| US-21 | Confirmación de asistencia | Agendamiento | Should have | 6 | Osinaga Blanco, A. |
| US-22 | Check-in en recepción | Agendamiento | Must have | 6 | Iporo Chulque, J. D. |
| US-24 | Registro de la atención | Historia clínica | Must have | 16 | Hurtado Castro, L. M. |
| US-25 | Historial clínico longitudinal | Historia clínica | Must have | 10 | Hurtado Castro, L. M. |
| US-31 | Sugerencia de especialidad por síntomas | IA · asistente | Must have | 16 | Ortega Mancilla, K. P. |
| US-32 | Consultas administrativas al asistente | IA · asistente | Should have | 10 | Hurtado Castro, L. M. |
| US-34 | Derivación a atención de emergencia | IA · asistente | Must have | 10 | Ortega Mancilla, K. P. |
| US-05 | Edición de perfil *(arrastre S1)* | Usuarios | Must have | 4 | Ortega Mancilla, K. P. |
| US-09 | Búsqueda de pacientes *(arrastre S1)* | Pacientes | Must have | 6 | Iporo Chulque, J. D. |
| US-10 | ABM de pacientes *(arrastre S1)* | Pacientes | Must have | 6 | Iporo Chulque, J. D. |

> **Las fichas individuales de cada historia** —con sus casos de uso asociados,
> criterios de aceptación y prototipos— siguen la misma plantilla del Sprint 1.
> No están en este archivo; se redactan historia por historia a medida que se
> cierran, que es como se hizo en el sprint anterior.

**Por qué el reparto no es parejo.** Las tres historias del asistente quedan
entre dos personas porque son el énfasis del proyecto y lo que se presenta ante
la docente: repartirlas entre tres hace que nadie tenga la fotografía completa
del subsistema, que es justamente lo que hay que poder defender. El integrante
con menos horas asignadas las tiene para **cerrar temprano la deuda del Sprint
1**, que ya lleva un sprint sin entregarse.

---

## 1.3 Contexto del Sistema

Va un diagrama de casos de uso que reúna los casos del sprint con sus actores,
igual que en el Sprint 1. Los casos que entran son los de reserva, pago,
comprobante, cancelación, confirmación de asistencia, check-in, registro de la
atención, historial y las tres consultas al asistente.

> **Pendiente de dibujar en Enterprise Architect.** Es el único diagrama del
> Sprint 2 que todavía no está en el modelo.

---

## 1.4 Sprint Backlog

La numeración del Sprint 1 llegó hasta T-24; el Sprint 2 arranca en **T-25**.

| ID | Tarea | Tipo | Estimación | Responsable | Prioridad |
|---|---|---|---|---|---|
| T-25 | Reserva de ficha | Historia | 16 horas | Aguayo Quiroz, L. M. | Must have |
| T-26 | Pago en línea con Stripe | Historia | 16 horas | Osinaga Blanco, A. | Must have |
| T-27 | Comprobante digital con QR | Historia | 10 horas | Osinaga Blanco, A. | Must have |
| T-28 | Cancelación y reprogramación | Historia | 10 horas | Aguayo Quiroz, L. M. | Should have |
| T-29 | Confirmación de asistencia | Historia | 6 horas | Osinaga Blanco, A. | Should have |
| T-30 | Check-in en recepción | Historia | 6 horas | Iporo Chulque, J. D. | Must have |
| T-31 | Registro de la atención | Historia | 16 horas | Hurtado Castro, L. M. | Must have |
| T-32 | Historial clínico longitudinal | Historia | 10 horas | Hurtado Castro, L. M. | Must have |
| T-33 | Sugerencia de especialidad por síntomas (RAG) | Historia | 16 horas | Ortega Mancilla, K. P. | Must have |
| T-34 | Consultas administrativas al asistente | Historia | 10 horas | Hurtado Castro, L. M. | Should have |
| T-35 | Derivación a atención de emergencia | Historia | 10 horas | Ortega Mancilla, K. P. | Must have |
| T-36 | Modelo C4 y diagramas de estado, navegación y tiempo | Técnica | *(a estimar)* | Hurtado Castro, L. M. | Must have |

Las tres historias de arrastre **conservan el identificador que ya tienen** en
el Sprint Backlog del Sprint 1 —hay que verificarlo en el documento antes de
pegar—, tal como se hizo con T-06 cuando US-04 pasó del Sprint 0 al Sprint 1. No
se les asigna número nuevo.

> **Corregir también el apartado 3.11.** La tabla de planificación por sprint
> sigue con las horas viejas: el Sprint 2 pasa a **142 h** y el Sprint 3 a
> **74 h**. El total de 436 h no cambia.

---

## 1.5 Equipo Scrum

| Rol | Integrante |
|---|---|
| Scrum Master | Hurtado Castro, Luis Mateo |
| Product Owner | Osinaga Blanco, Alexander |
| Equipo de Desarrollo | Aguayo Quiroz, Luis Miguel |
| Equipo de Desarrollo | Iporo Chulque, José Daniel |
| Equipo de Desarrollo | Ortega Mancilla, Karen Paola |

> **El equipo pasó de seis a cinco integrantes.** Mamani Samurio, Michael
> Alexander retiró la materia al inicio de este sprint. Sus tres historias
> pendientes del Sprint 1 —US-05, US-09 y US-10, 16 horas— se redistribuyeron
> entre quienes ya eran responsables de esos módulos, sin agregar historias
> nuevas al alcance.

La tabla que hoy figura en el Word incluye seis nombres: hay que quitar el
sexto de esta sección del Sprint 2 en adelante.

---

## 2.1.1 Diseñar la arquitectura (Modelo C4)

Los cuatro diagramas están en `docs/diagramas/PlataformaMedica.eapx`, en el
paquete `CAP. 4 > Sprint 2 - Arquitectura > 2.1.1 Arquitectura (Modelo C4)`. Se
generan con `scripts/ea-c4-2-1-1.ps1`.

**Antes de pegar estas figuras**, el apartado 2.4 del Capítulo 2 tiene que
corregirse: hoy dice que los niveles C3 y C4 quedan fuera del alcance. El texto
de reemplazo está en `2-4-modelo-c4-correccion.md`.

### 2.1.1.1 Nivel 1: Diagrama de contexto

> El primer nivel presenta la plataforma como una caja única y muestra
> únicamente quién la usa y con qué sistemas de terceros intercambia datos. Su
> propósito es que alguien ajeno al desarrollo entienda el alcance del sistema
> sin necesidad de conocer su construcción.
>
> Intervienen seis roles de usuario. Del lado de la aplicación móvil, el
> **Paciente**, que consulta especialidades, reserva y paga su ficha y consulta
> al asistente de orientación, y el **Titular**, que además gestiona a sus
> dependientes y reserva por ellos. Del lado de la aplicación web, el
> **Recepcionista**, que registra pacientes, cobra en caja y marca la
> asistencia; el **Médico**, que consulta la agenda y registra la historia
> clínica; y el **Administrador de Organización**, que administra su centro
> médico y consulta sus reportes. Por fuera de ambas aplicaciones, el
> **Superadministrador de Plataforma** da de alta organizaciones y planes de
> suscripción.
>
> La distinción entre estos dos últimos roles no es un detalle de nomenclatura:
> el Superadministrador opera sobre la plataforma y el Administrador de
> Organización sobre una única organización, sin acceso a los datos de las
> demás. Es la traducción, en términos de actores, del modelo multi-inquilino
> descrito en el apartado 1.1.
>
> Los sistemas externos son cuatro: **Stripe**, que cobra la ficha y confirma el
> pago mediante un webhook; **Google Gemini**, proveedor del modelo de lenguaje
> que vectoriza el texto y redacta las respuestas del asistente; **Firebase
> Cloud Messaging**, que entrega las notificaciones push al teléfono del
> paciente; y el **servicio de correo transaccional**, que envía comprobantes y
> reportes. De los cuatro, Stripe y Gemini se integran en este sprint; el envío
> de correo ya está operativo desde la característica de reportes, y las
> notificaciones push corresponden a la Épica 6.

### 2.1.1.2 Nivel 2: Diagrama de contenedores

> El segundo nivel abre la caja y muestra las unidades que se despliegan y se
> ejecutan por separado. Son cuatro: la **aplicación móvil** en Flutter, que se
> distribuye como APK; la **aplicación web** en React, que se compila a un
> bundle estático; la **API REST** en Django REST Framework, que concentra la
> lógica de negocio; y la **base de datos** PostgreSQL con la extensión
> pgvector, que guarda tanto los datos transaccionales como los vectores del
> asistente.
>
> Ambas aplicaciones cliente hablan con la API por HTTPS, con formato JSON y
> autenticación por token JWT; la API habla con la base de datos por el
> *session pooler*, sobre TLS.
>
> **El punto que este diagrama debe hacer visible es que el aislamiento entre
> organizaciones se aplica en dos lugares distintos.** En la API, porque la
> organización se resuelve a partir del token y nunca a partir del cuerpo de la
> petición, y se fija en la sesión de PostgreSQL antes de ejecutar cualquier
> consulta. Y en la base de datos, porque Row Level Security está forzado sobre
> las tablas del inquilino: aunque una consulta olvide filtrar, la base no
> devuelve filas ajenas. La primera capa documenta la intención; la segunda la
> hace cumplir. Es el apartado 1.1.6 llevado a la arquitectura, y es el
> diferencial del proyecto.

### 2.1.1.3 Nivel 3: Diagrama de componentes

> El tercer nivel abre uno de los cuatro contenedores. Se abre la **API REST**,
> por ser el que concentra la lógica de negocio y el que más crece en este
> sprint. Cada componente corresponde a una aplicación de Django con su propio
> conjunto de rutas.
>
> De los doce componentes, **cuatro los crea este sprint**: `appointments`, que
> reserva la ficha; `payments`, que la cobra y emite el comprobante;
> `encounters`, que registra la atención clínica; y `assistant`, el asistente de
> orientación. Los ocho restantes —`accounts`, `tenancy`, `catalog`, `patients`,
> `scheduling`, `audit`, `reporting` y `backups`— vienen de sprints anteriores.
>
> Se dibuja además, separado de los doce, el **middleware de inquilino**. No es
> una aplicación más: es una pieza transversal que corre en todas las peticiones
> y fija el contexto de organización en la sesión de base de datos antes de que
> cualquier componente consulte. Dibujarlo una vez evita las cuarenta relaciones
> que harían falta para unir cada componente con la base de datos.
>
> **`appointments` es la ruta crítica del sprint.** Tres componentes dependen de
> que la ficha exista: `payments` cobra una ficha ya reservada, `encounters`
> registra la consulta sobre la ficha atendida, y el check-in de recepción marca
> la asistencia sobre esa misma ficha. Un atraso ahí atrasa tres historias más,
> de tres personas distintas.

### 2.1.1.4 Nivel 4: Diagrama de código

> El cuarto nivel abre un componente y llega a las clases. Se abre `assistant`,
> por ser el énfasis del proyecto.
>
> El diagrama muestra las cuatro piezas del asistente en el orden en que se
> ejecutan. **`triage`** es la barrera de urgencias: compara el texto de la
> consulta contra una lista de señales y corre antes que todo lo demás; si
> dispara, no se recupera nada ni se llama al modelo de lenguaje. **`retrieval`**
> busca por similitud coseno sobre los vectores almacenados, filtrando por
> organización, y descarta el resultado si no supera un umbral mínimo.
> **`generation`** redacta la respuesta usando exclusivamente los fragmentos
> recuperados. Y **`indexing`**, que no corre por consulta sino cuando cambia el
> catálogo, parte cada descripción de especialidad en oraciones y guarda cada
> una con su vector.
>
> La entidad **`CatalogFragment`** guarda esos fragmentos, con una columna de
> tipo `vector` y el nombre del modelo que la generó. Aparece también
> **`catalog.Specialty`**, que no pertenece a este componente: se dibuja porque
> su campo de descripción **es** el corpus del asistente, lo que hace explícito
> que el sistema sólo puede responder sobre lo que la organización cargó en su
> propio catálogo.
>
> Cada relación de este diagrama corresponde a una dependencia que existe en el
> código fuente. No hay relaciones conceptuales.

---

## 2.1.3 Diseñar la lógica de negocio (US-31)

Los tres diagramas están en `docs/diagramas/PlataformaMedica.eapx`, en el
paquete `CAP. 4 > Sprint 2 - Arquitectura > 2.1.3 Logica de negocio (US-31)`.
Se generan con `scripts/ea-us31-2-1-3.ps1`, y los PNG salen en
`docs/diagramas/png/Sprin2/`.

**Se documenta US-31 y no otra historia** porque es la única terminada del
sprint, y porque es la que la materia pide poder explicar: el subsistema de
inteligencia artificial. Cada elemento lleva el nombre exacto del archivo, de
la función o de la tabla que representa, y cada mensaje es una llamada que
existe en `backend/assistant/`. Eso es lo que permite abrir el repositorio en
la defensa y señalar la línea.

> **Dos apartamientos del formato del ejemplo, y por qué.** Primero: los
> mensajes del diagrama de comunicación llevan **flecha**. Por un mismo enlace
> viajan la pregunta y la respuesta, y sin la punta los dos mensajes se leen
> igual. Segundo: el diagrama de clases de análisis lleva **actores**. El
> Paciente inicia la consulta y el Administrador de Organización dispara la
> indexación; sin ellos las dos fronteras quedan sin origen y el diagrama no
> dice quién empieza.

### 2.1.3.1 Diagrama de comunicación

> El diagrama de comunicación muestra quiénes intervienen en el caso de uso y
> en qué orden se hablan, sin el eje del tiempo. Los objetos se agrupan por su
> papel: el actor, las fronteras —la pantalla del móvil y el proveedor externo
> de modelo de lenguaje—, los controladores, que son los módulos de la
> aplicación `assistant`, y las entidades, que son las dos tablas que se
> consultan.
>
> La numeración divide la conversación en cuatro grupos, que son los cuatro
> desenlaces posibles de una consulta. El **grupo 1** es el flujo principal:
> el paciente escribe lo que le pasa, el sistema verifica su permiso, descarta
> que sea una urgencia, vectoriza la consulta, recupera del catálogo de su
> organización los fragmentos más parecidos, agrupa los que corresponden a una
> misma especialidad y redacta la respuesta usando únicamente eso. El **grupo
> 2** es la derivación a emergencia: la barrera corta el flujo antes de
> recuperar nada, de modo que no se llega a sugerir ninguna especialidad. El
> **grupo 3** es la consulta que no se parece a nada del catálogo, donde el
> asistente responde que no sabe sin llamar al modelo de lenguaje. Y el
> **grupo 4** es la caída del proveedor de vectores, que termina en un 503 y
> no en una respuesta inventada.
>
> **Cada mensaje se dibuja como su propia flecha**, y la punta indica hacia
> dónde va. Donde dos objetos se hablan varias veces —la pantalla y la vista
> intercambian cinco mensajes, uno por cada desenlace— las flechas se abren
> en abanico en lugar de superponerse, de modo que se puede seguir una por
> una. Los colores son los mismos de los otros dos apartados: azul la
> frontera, verde el controlador, ámbar la entidad.
>
> **El mensaje 1.8 es donde vive el multi-inquilino dentro de la inteligencia
> artificial.** El filtro por organización va en el `WHERE`, antes del
> `ORDER BY` por similitud. Filtrarlo después devuelve el mismo resultado, y
> es una fuga: el índice de todos los inquilinos ya se recorrió.

### 2.1.3.2 Diagrama de clases de análisis

> El diagrama de clases de análisis muestra la estructura de la historia:
> las mismas piezas del diagrama anterior, pero con sus atributos y sus
> operaciones, y unidas por asociaciones con su rol y su cardinalidad.
>
> Las fronteras llevan el nombre del archivo de la pantalla y el endpoint que
> consumen. Los controladores llevan el nombre del **módulo** y no de una
> clase, porque en Python la unidad de código es el módulo: `retrieval.py` son
> dos funciones sueltas y no una clase con dos métodos; cada operación es el
> nombre y la firma reales de esa función. Las entidades llevan el nombre
> exacto de la tabla y sus columnas con el tipo de la base, incluida la
> columna `embedding` de tipo `vector(768)`, que es la que hace posible la
> búsqueda por similitud.
>
> **El diagrama tiene dos mitades que no corren al mismo tiempo.** De
> `embed_catalog.py` hacia abajo está la indexación, que no ocurre durante la
> consulta: corre cuando cambia el catálogo y deja los fragmentos vectorizados
> en la tabla. De `assistant_screen.dart` hacia la derecha está la consulta,
> que es la que ocurre cuando el paciente pregunta. Un asistente de este tipo
> no aprende de las preguntas: lo que sabe se escribe en la indexación.
>
> La entidad `specialties` aparece aunque no pertenezca al componente:
> **su campo `description` es el corpus**. Es lo que hace explícito que el
> sistema sólo puede responder sobre lo que la organización cargó en su propio
> catálogo, y que la calidad de la respuesta depende de cómo esté escrito ese
> texto.

### 2.1.3.3 Diagrama de secuencia

> El diagrama de secuencia es el mismo caso de uso con el eje del tiempo. Se
> lee de arriba hacia abajo, y cada línea de vida está clasificada por la
> clase correspondiente del apartado anterior, de modo que los dos diagramas
> nombran exactamente lo mismo.
>
> **Las líneas de vida están ordenadas por rol y no por orden de aparición**:
> primero el actor, después la frontera —la pantalla del paciente—, después
> los seis controladores, que son los módulos de la aplicación `assistant`,
> después las dos entidades, que son las tablas, y al final el sistema
> externo. Cada rol tiene su color, el mismo que en los dos apartados
> anteriores: azul la frontera, verde el controlador, ámbar la entidad. Es
> lo que permite ver, sin leer un solo nombre, que el trabajo ocurre en el
> centro y que a la derecha sólo hay datos.
>
> La numeración se hereda del diagrama de comunicación, para poder seguir un
> mismo mensaje en los dos apartados. Los retornos, que el diagrama de
> comunicación no representa, se numeran como sub-nivel del mensaje que los
> provoca —el retorno de `1.5` es `1.5.1`—, de manera que agregar retornos no
> corre la numeración original.
>
> **El fragmento combinado `alt` contiene los cuatro desenlaces**, en el mismo
> orden que los cuatro grupos del diagrama de comunicación. Lo que se ve al
> comparar las cuatro bandas es que **los tres desenlaces que no son el flujo
> principal son más cortos, y esa brevedad es deliberada**: en la urgencia no
> se recupera ni se redacta nada, en la consulta sin respaldo no se llama al
> modelo de lenguaje, y en la caída del proveedor se responde 503. Las tres
> son formas distintas de la misma decisión de diseño: **el asistente prefiere
> no contestar antes que contestar sin respaldo.**
>
> Los mensajes que van contra la base de datos llevan el SQL, y los que van
> contra el proveedor externo llevan el modelo que se invoca
> —`gemini-embedding-001` para vectorizar y `gemini-3.5-flash-lite` para
> redactar—, porque son los dos puntos donde el sistema sale de su propio
> proceso.

---

## Lo que todavía no se puede llenar, y desde cuándo

| Apartado | Estado | Cuándo se puede |
|---|---|---|
| 1.3 Contexto del Sistema | Falta el diagrama de casos de uso del sprint | Ya: es dibujarlo en EA. **Antes del 22/09**, que es cuando caduca la licencia Trial |
| 2.1.2 Diseño de datos | Sólo existe el esquema de `assistant` —tabla de fragmentos, políticas RLS y el permiso—. Las tablas de `appointments`, `payments` y `encounters` no están creadas | A medida que cada historia migre. El conceptual y el lógico se pueden dibujar antes que el código |
| 2.1.3 Lógica de negocio | **Hecho para US-31**: comunicación, clases de análisis y secuencia | Falta el mismo juego para el flujo de reserva y pago, cuando US-17 y US-18 existan |
| 2.2.1 Componentes y artefactos | Sólo el asistente: la app `assistant` con sus tres migraciones, el comando `embed_catalog` y el endpoint `POST /api/assistant/suggest/` | Se completa por historia |
| 2.3.1 Plan de pruebas | Hay criterios de aceptación escritos sólo para las historias del asistente | Por historia, antes de implementarla |
| 2.3.2 Reporte de prueba | Corren las pruebas de `backend/tests/test_us31.py`: el camino feliz, que la respuesta viaja con los fragmentos que la respaldan, que bajo el umbral contesta que no sabe, que dos organizaciones reciben catálogos distintos, que la barrera de urgencias corta el flujo y que reindexar no duplica | El resto, por historia |
| 3. Daily Scrum | El sprint está en el día 5 de 24 | Se completa al cierre |
| 4. Sprint Review | — | 06–08/10 |
| 5. Sprint Retrospective | — | 06–08/10 |
| 6. Burn Down / Burn Up | — | Al cierre |
| 7. Gráfica de esfuerzo | — | Al cierre |
| 8. Scrum Taskboard | — | Al cierre |
