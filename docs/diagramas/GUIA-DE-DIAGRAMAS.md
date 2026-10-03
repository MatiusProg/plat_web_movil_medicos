# Guía de diagramas de la Plataforma Médica

Esta guía reúne en un solo lugar cómo se hacen los diagramas del documento:

- **el modelo C4**, en Lucidchart, a partir de los `.drawio` de `c4-lucidchart/`;
- **los diagramas UML** de clases, secuencia, estado, navegación y tiempo, en Enterprise Architect, sobre `PlataformaMedica.eapx`.

Sale de dos guías que ya existían:

1. **La guía del modelo C4 de Mateo** (PR #51), que estaba en `c4-lucidchart/COMO-HACERLO-EN-LUCIDCHART.md`. Su contenido está entero en la [parte 2](#2-modelo-c4-en-lucidchart).
2. **La guía de Enterprise Architect de Karen** (`GUIA-DIAGRAMAS-EA.md`), escrita para otro proyecto de la materia (Violet Boutique, primer parcial). Todo lo que dice de EA está verificado contra **EA 15 Trial** sobre archivos `.eapx` reales. Acá se tomaron sus recetas de clases, secuencia, estado, navegación y tiempo, con las correcciones de cátedra que recibió, y se adaptaron a este proyecto: los ejemplos usan archivos y funciones que existen en `main`.

---

## Índice

1. [Reglas que valen para todos los diagramas](#1-reglas-que-valen-para-todos-los-diagramas)
2. [Modelo C4 en Lucidchart](#2-modelo-c4-en-lucidchart)
3. [Antes de abrir Enterprise Architect](#3-antes-de-abrir-enterprise-architect)
4. [Diagramas de clases](#4-diagramas-de-clases)
5. [Diagrama de secuencia](#5-diagrama-de-secuencia)
6. [Diagrama de estado](#6-diagrama-de-estado)
7. [Diagrama de navegación](#7-diagrama-de-navegación)
8. [Diagrama de tiempo](#8-diagrama-de-tiempo)
9. [Exportar a PNG para el Word](#9-exportar-a-png-para-el-word)
10. [Errores frecuentes en EA: síntoma, causa y arreglo](#10-errores-frecuentes-en-ea-síntoma-causa-y-arreglo)
11. [Checklist antes de pegar un diagrama en el Word](#11-checklist-antes-de-pegar-un-diagrama-en-el-word)

---

## 1. Reglas que valen para todos los diagramas

**1. Los nombres son los exactos del código.** Una clase, una línea de vida o una caja de navegación se llama como el archivo, la clase o la función que representa: `accounts/views/profile.py`, `SuggestView`, `book_appointment`. Nada de `GestorDePerfil` ni `ControladorDeReservas`. Es lo que permite defender un diagrama: cada elemento se puede abrir en el repositorio.

**2. Cada rótulo que afirma algo lleva su ancla.** Una guarda, una restricción o un código de error van con el archivo y la línea, o con el verbo y la ruta del endpoint, entre llaves: `[correo ya usado en el centro] {400 serializers/profile.py:102}`.

**3. Un solo tipo de línea entre clases.** En los diagramas de clases, la unión entre dos clases es siempre una **asociación**, con el rol en MAYÚSCULAS (`CONSULTA`, `PERTENECE_A`) y la cardinalidad en los dos extremos. Nada de dependencia, agregación ni composición: con un solo tipo de línea, los diagramas del capítulo se comparan entre sí sin discutir la semántica de cada estilo.

**4. El mismo color para el mismo rol en todos los diagramas.** Frontera, controlador y entidad llevan siempre los mismos tres colores, en clases y en secuencia, con una nota al pie que diga qué es cada color.

**5. Qué diagrama va para qué caso de uso.** Es la regla que la ingeniera le corrigió al otro proyecto el 15/09/2026:

- **Secuencia, estado y tiempo van solo de los casos de uso transaccionales.** Transaccional quiere decir que el caso de uso **escribe**. En este backend se reconoce por un `transaction.atomic()`, un `save()` o un `create()` en la vista o el servicio. Las consultas puras quedan fuera.
- **Navegación va por actor**, no por caso de uso.
- **Clases de análisis van una por caso de uso.**

Cómo quedan las historias del Sprint 2 con esa regla:

| Historia | ¿Escribe? | Secuencia, estado, tiempo |
|---|---|---|
| US-05 — Edición de perfil | Sí: `profile()` y `change_password()` | Sí |
| US-17 — Reserva de ficha | Sí: `book_appointment()` | Sí |
| US-20 — Cancelación y reprogramación | Sí | Sí |
| US-24 — Registro de la atención | Sí | Sí |
| US-25 — Historial longitudinal | No: sólo lee (deja asiento de bitácora) | No |
| US-31 / US-34 — Asistente | No escribe datos del dominio: sólo el asiento de bitácora | Secuencia sí, porque es el camino que el reparto eligió mostrar (sección 5); estado y tiempo, no |

**6. El `.eapx` es binario.** Dos ramas que lo tocan en paralelo no se pueden fusionar. Todos los diagramas de EA van en la misma rama y los hace una sola persona (reparto del Sprint 2, sección 5).

---

## 2. Modelo C4 en Lucidchart

Hay cuatro archivos de diagrams.net en `c4-lucidchart/`, uno por nivel:

| Archivo | Nivel |
|---|---|
| `c4-lucidchart/c1-contexto.drawio` | C1: contexto |
| `c4-lucidchart/c2-contenedores.drawio` | C2: contenedores |
| `c4-lucidchart/c3-componentes.drawio` | C3: componentes (solo la API REST) |
| `c4-lucidchart/c4-codigo.drawio` | C4: código (solo el componente `assistant`) |

Siguen las indicaciones de la docente (`D:\UNI\Si2\Diagramas c4, estado, navegacion y tiempo.md`):

- las personas son **nubes**, no monigotes;
- la base de datos es un **cilindro**;
- el sistema va al centro;
- en C2 y C3 el sistema o el backend es un **límite punteado** con los nodos adentro;
- todas las relaciones son líneas de **asociación** (sin punta de flecha);
- C3 es solo del backend, sin usuarios, y muestra solo los externos que se relacionan con él;
- C4 es **un único diagrama**: un componente semitransparente con los archivos adentro, y cada archivo con sus funciones en lista.

**Qué muestran.** Muestran el **sistema completo, todo como terminado**. Lo implementado sale de `origin/main`; `encounters` (US-24 y US-25) ya está en `main` desde los PR #48 y #50. Lo que todavía no tiene código figura igual, y en la tabla de la sección 2.4 se indica la historia de usuario que lo implementa.

La rama `docs/c4-sprint-2` está atrasada: le faltan `appointments`, `assistant/corpus.py`, `assistant/reindex_views.py` y `assistant/medical_reference.py`. Si comparan el diagrama con el código, comparen contra `main`.

### 2.1 Importar los `.drawio` en Lucidchart

1. Abran Lucidchart.
2. Busquen la opción de importar. Puede estar en **Archivo › Importar** con un documento abierto, o en el botón **Importar** del panel de documentos. El nombre exacto del menú cambia entre versiones de Lucid. Si no lo encuentran, busquen "import draw.io" en la ayuda de Lucid.
3. Elijan **draw.io / diagrams.net** como origen y suban el `.drawio`. Cada archivo trae una sola página.
4. Hagan un archivo por vez. Así cada nivel queda como un documento o una página aparte.

#### Cómo vienen armados los archivos

Esto cambió después de la primera importación, en la que Lucid mostraba cosas como "#10" en lugar de los textos:

- **Saltos de línea.** Todos los textos son texto plano, sin HTML. Los saltos de línea van como `&#xa;`, que es como los escribe draw.io. Antes iban como `&#10;`; es el mismo carácter en XML, pero el importador de Lucid lo mostraba como el texto literal "#10".
- **Dos formas por nodo.** El título de cada nodo es el texto de la forma, en negrita de 17 pt. La tecnología y la descripción van, en 13 pt, en una forma de texto aparte apoyada sobre la caja. Hacen falta dos formas porque en texto plano no se pueden mezclar dos tamaños dentro de una misma etiqueta. Esa forma de texto se llama `<id>-texto`.
- **Etiquetas de las relaciones:** 12 pt.
- **Títulos de las cajas de C4:** 16 pt en negrita. Las funciones van a 13 pt, una por renglón, cada una con "• ".
- **Ids descriptivos.** Todos los ids son descriptivos: `c2-api-django`, `c3-encounters`, `c4-retrieval`, `c1-rel-sistema-stripe`, etc. Si Lucid llegara a mostrar un id, igual se entiende qué es.

#### Qué revisar después de importar

- **Texto encima de su caja.** Cada caja tiene encima su forma de texto, con la tecnología y la descripción. Si quedó detrás, tráiganla al frente. Después agrupen la caja con su texto (Ctrl+G) para moverlas juntas. En C4, agrupen el cuerpo con su encabezado azul (`<id>-titulo`).
- **Texto que se corta.** Las cajas tienen margen para la letra de Lucid. Si igual algún texto se corta, agranden la caja; no achiquen la letra.
- **Si aparece "#xa".** Si aparece "#xa" en algún texto, el importador no está leyendo los saltos de línea. Avisen: hay que generar los archivos con otra codificación.
- **Nubes y cilindros.** Confirmen que siguen siendo nubes y cilindros. Si alguno quedó como rectángulo, cámbienlo a mano: busquen "cloud" o "cylinder" en el buscador de formas y usen **Reemplazar forma**, si su versión lo tiene.
- **Límite punteado (C2 y C3).** Tiene que quedar con relleno transparente y **detrás** de los nodos. Si tapa a los nodos, envíenlo al fondo con clic derecho › *Enviar al fondo*.
- **Contenedor semitransparente (C4).** Lo mismo: debe quedar al fondo. Si perdió la transparencia, bájenle la opacidad del relleno a unos 30–40 %.
- **Las tres líneas con quiebres de C4.** Son `views.py → retrieval.py`, `reindex_views.py → audit.services` y `indexing.py → embeddings.py`. Si Lucid las dejó rectas y atraviesan otra caja, arrastren el punto medio de la línea para volver a quebrarla.
- **Agrupar.** Los nodos no son "hijos" del límite, porque así Lucid los importa mejor. Para mover todo junto, selecciónenlo y agrúpenlo.

### 2.2 Construir cada nivel a mano

Usen esta sección si la importación no queda bien.

**Formas.** Activen la biblioteca **Standard** o **Formas básicas**, que trae el rectángulo redondeado, la nube y el texto. La biblioteca de **Diagramas de flujo** trae el cilindro de base de datos. Lucid tiene además una biblioteca específica de **C4** en algunas cuentas. No la usen para las personas: su forma es un monigote y la docente pidió nubes.

**Letra:**

| Texto | Tamaño |
|---|---|
| Títulos de nodo | 17 pt en negrita |
| Tecnología y descripción | 13 pt |
| Etiquetas de las relaciones | 12 pt |
| Encabezados de C4 | 16 pt en negrita |
| Funciones de C4 | 13 pt |

**Colores** (son los del estándar C4; son opcionales):

| Elemento | Color |
|---|---|
| Sistema | azul oscuro `#1168BD` |
| Contenedores | azul `#438DD5` |
| Componentes | celeste `#85BBF0` |
| Externos | gris `#999999` |
| Nubes de personas | celeste claro `#DAE8FC` |

**Líneas.** Todas son líneas simples, sin punta, con la etiqueta en el medio. Si quieren mostrar el sentido, pueden poner una punta abierta en el destino, pero tiene que ser igual en los cuatro niveles.

#### C1: Contexto

**Disposición:** el sistema en el centro. Las personas a la izquierda y arriba. Los cuatro externos en columna a la derecha. La base de datos abajo.

**Los externos son los mismos en C1, C2 y C3, con los mismos nombres:** Google Gemini API, Servidor de correo, Stripe, Firebase Cloud Messaging y la base de datos.

| Id | Forma | Texto |
|---|---|---|
| Sistema | Rectángulo redondeado, azul oscuro | Plataforma Médica Multi-inquilino / [Sistema de software] / Reserva y pago de fichas, agendas, atención clínica, reportes y asistente con IA, aislado por organización |
| Paciente | Nube | Paciente (titular y dependientes) / [Persona] / Reserva y paga fichas, gestiona dependientes y consulta al asistente |
| Recepcionista | Nube | Recepcionista / [Persona] / Registra pacientes, valida comprobantes y gestiona fichas |
| Médico | Nube | Médico (profesional) / [Persona] / Consulta su agenda y registra la atención clínica |
| Admin. org. | Nube | Administrador de Organización / [Persona] / Gestiona usuarios, catálogo, reportes y copias de su centro |
| Superadmin | Nube | Superadministrador de Plataforma / [Persona] / Administra organizaciones, planes y suscripciones |
| Gemini | Rectángulo gris | Google Gemini API / [Sistema externo] / Embeddings y redacción del asistente |
| Correo | Rectángulo gris | Servidor de correo / [Sistema externo · SMTP] / Recuperación de contraseña, comprobantes y reportes |
| Stripe | Rectángulo gris | Stripe / [Sistema externo] / Cobro en línea de la ficha y webhook firmado |
| FCM | Rectángulo gris | Firebase Cloud Messaging / [Sistema externo] / Notificaciones push al móvil |
| Supabase | Cilindro gris | Supabase / [PostgreSQL 16 + pgvector] / Base de datos gestionada |

**Relaciones:**

| Origen → destino | Etiqueta |
|---|---|
| Paciente, Recepcionista, Médico, Admin. org., Superadmin → Sistema | usa |
| Sistema → Gemini | embeddings y chat [HTTPS] |
| Sistema → Correo | envía correos [SMTP/TLS] |
| Sistema → Stripe | cobros y webhook firmado [HTTPS] |
| Sistema → FCM | envía notificaciones push [HTTPS] |
| Sistema → Supabase | lee y escribe datos y vectores [SQL/TLS] |

#### C2: Contenedores

**Disposición:**

- Las cinco nubes en fila arriba, en este orden: Recepcionista, Médico, Paciente, Admin. org., Superadmin. Llevan solo el nombre y "[Persona]".
- Debajo, un **rectángulo grande punteado y sin relleno**, con el texto abajo a la izquierda: "Plataforma Médica Multi-inquilino [Sistema de software]".
- Adentro del límite: la web arriba a la izquierda, el móvil arriba a la derecha, la API en el centro y la base de datos abajo.
- Afuera, a la derecha, de arriba abajo: FCM (a la altura del móvil), Gemini, Stripe y el correo.

| Id | Forma | Texto |
|---|---|---|
| Web | Rectángulo azul | Aplicación web / [React 19 + Vite + TypeScript] / SPA de administración, recepción, médicos y pacientes (Railway) |
| Móvil | Rectángulo azul | Aplicación móvil / [Flutter / Dart · APK Android] / Reserva y pago, comprobante QR, asistente y paneles por rol |
| API | Rectángulo azul | API REST / [Python 3.13 · Django 5.2 + DRF] / Lógica de negocio, JWT, multi-inquilino, pagos y asistente RAG (Railway) |
| BD | Cilindro azul (adentro del límite) | Base de datos / [PostgreSQL 16 + pgvector] / Datos con RLS por organización y vectores del asistente (Supabase) |
| FCM, Gemini, Stripe, Correo | Rectángulos grises (afuera) | Los mismos textos que en C1 |
| Nota | Texto | Las líneas sin etiqueta entre una persona y una aplicación son asociaciones «usa»… |

**Relaciones:**

| Origen → destino | Etiqueta |
|---|---|
| Cada una de las 5 personas → Web y → Móvil (10 líneas) | sin etiqueta; la nota aclara que significan «usa» |
| Web → API | llama a la API [HTTPS/JSON + JWT] |
| Móvil → API | llama a la API [HTTPS/JSON + JWT] |
| API → BD | lee y escribe [SQL/TLS · RLS] |
| API → Gemini | embeddings y chat [HTTPS] |
| API → Stripe | cobros y webhook firmado [HTTPS] |
| API → Correo | envía correos [SMTP/TLS] |
| API → FCM | envía push [HTTPS] |
| FCM → Móvil | entrega notificaciones push |

Las diez líneas de personas a aplicaciones van porque los dos clientes atienden a los cinco roles:

- **Móvil:** `mobile/lib/core/router/app_router.dart` tiene rutas `/platform/...`, `/org/...` filtradas por permiso, y rutas de paciente detrás de `patient_gate.dart`.
- **Web:** `frontend/src/paginas` tiene `RegistroPaciente`, `MisFichas`, `Agendas`, `Organizaciones` y otras.

#### C3: Componentes (solo la API REST)

**Disposición:**

- Un **límite punteado** al centro, con el texto "API REST — backend [Python 3.13 · Django 5.2 + DRF]".
- Adentro, 17 componentes en una grilla de 3 columnas por 6 filas.
- A la izquierda, afuera: la web y el móvil. Son los otros contenedores que le hablan al backend; no son usuarios.
- A la derecha, afuera: Gemini, el correo, Stripe, FCM y el cilindro de la base.
- No se dibujan las relaciones internas: la docente dijo que se pueden omitir.

**Grilla:**

| | Columna 1 | Columna 2 | Columna 3 |
|---|---|---|---|
| Fila 1 | tenancy | scheduling | assistant |
| Fila 2 | Rutas de la API | appointments | accounts |
| Fila 3 | AuditTrailMiddleware | encounters | reporting |
| Fila 4 | catalog | audit | payments |
| Fila 5 | patients | backups | notifications |
| Fila 6 | TenantMiddleware | (vacío) | Acceso a datos |

La columna 3 queda junto a los externos con los que se conecta.

**Textos** (rectángulos celestes; formato "nombre / [tecnología] / descripción"):

| Componente | Texto |
|---|---|
| tenancy | [App Django · tenancy/] / Organizaciones, planes, suscripciones y métricas de plataforma |
| Rutas de la API | [Django · config/urls.py] / Monta /api/<app>/ de cada app y /api/health/ |
| AuditTrailMiddleware | [Middleware · audit/middleware.py] / Asienta cada petición en la bitácora |
| catalog | [App Django · catalog/] / Sucursales, especialidades, profesionales, servicios y búsqueda |
| patients | [App Django · patients/] / Pacientes, dependientes y antecedentes |
| TenantMiddleware | [Middleware · tenancy/middleware.py] / Abre la transacción y fija el inquilino (RLS) |
| scheduling | [App Django · scheduling/] / Agendas, bloqueos y disponibilidad |
| appointments | [App Django · appointments/] / Reserva, cancelación y reprogramación de fichas |
| encounters | [App Django · encounters/] / Registro de la atención e historial clínico |
| audit | [App Django · audit/] / Consulta de la bitácora de auditoría |
| backups | [App Django · backups/] / Copia y restauración en JSON por organización |
| assistant | [App Django · pgvector + google-genai] / Asistente RAG: urgencias, recuperación y redacción |
| accounts | [App Django · SimpleJWT + Argon2] / Usuarios, roles, login JWT, registro, perfil y recuperación de contraseña |
| reporting | [App Django · openpyxl + reportlab] / Reportes a Excel, PDF, HTML, CSV y correo |
| payments | [App Django · Stripe] / Pago en línea, webhook firmado y comprobante QR |
| notifications | [App Django · Firebase Admin] / Notificaciones push al móvil |
| Acceso a datos | [ORM de Django · psycopg 3 · pgvector] / Consultas SQL bajo el contexto del inquilino |

**Elementos de afuera:**

| Elemento | Forma | Texto |
|---|---|---|
| Web | Rectángulo azul | Aplicación web [React + Vite + TypeScript] |
| Móvil | Rectángulo azul | Aplicación móvil [Flutter / Dart] |
| Gemini, Correo, Stripe, FCM | Rectángulos grises | Los mismos textos que en C1 |
| BD | Cilindro | Base de datos [PostgreSQL 16 + pgvector · Supabase] / Tablas con RLS y vectores del asistente |

**Relaciones:**

| Origen → destino | Etiqueta |
|---|---|
| Web → Rutas de la API | HTTPS/JSON + JWT |
| Móvil → Rutas de la API | HTTPS/JSON + JWT |
| assistant → Gemini | embeddings y chat [HTTPS] |
| accounts → Correo | correo de recuperación |
| reporting → Correo | envía el reporte adjunto |
| payments → Stripe | cobros y webhook firmado |
| notifications → FCM | envía push |
| Acceso a datos → BD | lee y escribe [SQL/TLS] |

#### C4: Código (componente `assistant`)

**Disposición:**

- Un **rectángulo grande semitransparente** (relleno celeste al 30–40 %) con este título arriba a la izquierda: "assistant [Componente · App Django · backend/assistant/] — US-31, US-32, US-34".
- Adentro van **14 cajas**, una por archivo. Cada caja tiene un encabezado azul con el nombre del archivo y su papel, y debajo la lista de funciones.
- En Lucid es cómodo usar la forma **Clase UML** de la biblioteca UML, ya que tiene encabezado y lista. Si usan esa forma, borren el compartimento de atributos que no usen.
- Las cajas van en 4 columnas:

| Columna | Papel | Cajas, de arriba abajo |
|---|---|---|
| 1 | Entrada | urls.py, permissions.py, serializers.py, embed_catalog.py |
| 2 | Vistas | views.py, reindex_views.py |
| 3 | Lógica | generation.py, triage.py, retrieval.py, indexing.py |
| 4 | Soporte | embeddings.py, models.py, medical_reference.py, corpus.py |

- Afuera van cuatro elementos:
  - arriba: `audit.services`, como caja gris punteada (es otro componente);
  - a la derecha: `Google Gemini API` (gris), el cilindro `Base de datos` y `catalog.models` (caja gris punteada).

**Contenido de cada caja:**

Cada función va en su propio renglón y empieza con «• ». En Lucid se escribe con Enter entre función y función; no las pongan corridas en un mismo párrafo.

| Caja (encabezado) | Funciones (un renglón por función, con «• ») |
|---|---|
| urls.py [rutas de la app] | • path("suggest/", SuggestView)<br>• path("reindex/", ReindexView) |
| permissions.py [permisos DRF] | • CanUseAssistant.has_permission(request, view)<br>• CanReindexCatalog (assistant.catalog.reindex) |
| serializers.py [DRF] | • SuggestRequestSerializer<br>• FragmentSerializer<br>• SpecialtySuggestionSerializer |
| management/commands/embed_catalog.py [comando de manage.py] | • Command.add_arguments(parser)<br>• Command.handle(*args, **opciones)<br>• Command._dry_run(organizacion)<br>• Command._indexar(organizacion, modelo) |
| views.py [SuggestView · POST /api/assistant/suggest/] | • SuggestView.post(request)<br>• SuggestView._administrativa(request, question, fragments)<br>• _emergency_response(generated_by)<br>• _audit(request, *, emergency_layer, specialty_suggested, kind) |
| reindex_views.py [ReindexView · POST /api/assistant/reindex/] | • ReindexView.post(request) |
| generation.py [redacción con el modelo] | • answer(question, fragments, specialty_name)<br>• answer_administrative(question, fragments)<br>• _call_model(question, context, *, system_prompt)<br>• _grounded_fallback(specialty_name)<br>• _administrative_fallback(fragments) |
| triage.py [barrera de urgencias] | • check(question) → TriageResult<br>• TriageResult (dataclass)<br>• EMERGENCY_SIGNALS / COMBINED_SIGNALS |
| retrieval.py [búsqueda por similitud coseno] | • retrieve(organization, question, *, limit=5)<br>• rank_specialties(fragments)<br>• is_administrative(fragment)<br>• _source_names(organization, fragments) |
| indexing.py [construcción del índice] | • index_specialties(organization, *, stdout)<br>• index_administrative(organization, *, stdout)<br>• fragments_for(specialty)<br>• split_into_fragments(name, description)<br>• medical_reference_enabled() |
| embeddings.py [proveedor de vectores] | • embed_query(text)<br>• embed_documents(texts)<br>• active_model_name()<br>• normalize_text(text)<br>• _gemini_embeddings(texts, task_type)<br>• _gemini_client()<br>• _local_embedding(text)<br>• _tokens(text)<br>• _l2_normalize(vector)<br>• _check_dimensions(vector) |
| models.py [modelo de datos] | • CatalogFragment (tabla assistant_catalog_fragments)<br>• CatalogFragment.__str__()<br>• SourceType: specialty, branch, service, policy<br>• EMBEDDING_DIMENSIONS = 768 |
| medical_reference.py [referencia médica] | • reference_texts(specialty_name)<br>• find_reference(specialty_name)<br>• _index() |
| corpus.py [corpus administrativo] | • administrative_sources(organization)<br>• branch_fragments(branch, hours, staff)<br>• service_fragments(service)<br>• policy_fragments(organization)<br>• describe_hours(hours)<br>• format_price(price, currency)<br>• _hhmm(value)<br>• _join(items) |

**Relaciones.** Cada una corresponde a un `import` o a una llamada que existe en el código.

| Origen → destino | Etiqueta |
|---|---|
| urls.py → views.py | suggest/ |
| urls.py → reindex_views.py | reindex/ |
| views.py → audit.services | record() |
| reindex_views.py → audit.services | record() (con quiebre por la izquierda de views.py) |
| views.py → generation.py | answer() · answer_administrative() |
| views.py → triage.py | check() |
| views.py → retrieval.py | retrieve() · rank_specialties() |
| reindex_views.py → indexing.py | index_specialties() · index_administrative() |
| embed_catalog.py → indexing.py | index_specialties() · index_administrative() |
| triage.py → embeddings.py | normalize_text() |
| retrieval.py → embeddings.py | embed_query() |
| retrieval.py → models.py | CatalogFragment · CosineDistance |
| indexing.py → embeddings.py | embed_documents() |
| indexing.py → models.py | guarda fragmentos |
| indexing.py → medical_reference.py | reference_texts() |
| indexing.py → corpus.py | administrative_sources() |
| generation.py → Gemini | generate_content() |
| embeddings.py → Gemini | embed_content() |
| models.py → Base de datos | assistant_catalog_fragments |
| corpus.py → catalog.models | lee el catálogo |

**Relaciones reales que se dejaron afuera para no cruzar líneas:**

- `views.py` usa `permissions.py` y `serializers.py`;
- `reindex_views.py` usa `permissions.py`;
- `views.py` usa `active_model_name()` de `embeddings.py`;
- `retrieval.py` e `indexing.py` leen `catalog.models`.

Se pueden agregar si la docente las pide.

### 2.3 Exportar el C4 a PNG

1. Con el diagrama abierto, vayan a **Archivo › Exportar › PNG**. En algunas versiones dice "Descargar como".
2. Elijan **alta resolución**. Si da a elegir DPI, pongan 300.
3. Marquen **fondo blanco**, no transparente. Con fondo transparente, Word muestra las letras sobre gris.
4. Si hay opción de **recortar al contenido**, actívenla para que no queden márgenes grandes.
5. En el plan gratuito, Lucid puede limitar la resolución o el tamaño del documento. Si la imagen sale chica, prueben exportar en **PDF** o **SVG** y convertirlo, o subir el zoom antes de exportar.
6. Guarden los PNG en `docs/diagramas/png/Sprint 2/` con estos nombres: `C1-contexto.png`, `C2-contenedores.png`, `C3-componentes.png` y `C4-codigo.png`.
7. En Word, insértenlos con **Insertar › Imagen** al ancho de la página. El C4 es apaisado, así que conviene ponerlo en una sección con orientación horizontal.

### 2.4 De dónde sale cada elemento del C4

| Elemento | Nivel | De dónde sale en el repositorio (`main`) |
|---|---|---|
| Paciente, Recepcionista, Médico, Administrador de Organización, Superadministrador de Plataforma | C1, C2 | `backend/tenancy/migrations/0003_seed_catalog.py` (`ROLES`: patient, receptionist, practitioner, org_admin, platform_admin) y los permisos de `accounts/migrations/0003_…`, `0006_…`, `patients/migrations/0002_us07_dependents.py` y `0004_us08_rls.py` |
| "(titular y dependientes)" en Paciente | C1, C2 | `backend/patients/dependents.py` y los permisos `patients.dependent.*` del rol patient. El titular no es un rol aparte |
| Plataforma Médica Multi-inquilino | C1, C2 | `backend/config/settings.py` (INSTALLED_APPS) y `backend/tenancy/` |
| Google Gemini API | C1–C4 | `settings.py` (`GEMINI_API_KEY`, `ASSISTANT_EMBEDDING_MODEL=gemini-embedding-001`, `ASSISTANT_CHAT_MODEL=gemini-3.5-flash-lite`), `requirements.txt` (`google-genai`), `assistant/embeddings.py` (`embed_content`) y `assistant/generation.py` (`generate_content`) |
| Servidor de correo SMTP | C1–C3 | `settings.py` (`EMAIL_BACKEND`, `EMAIL_HOST`…), `accounts/services/password_reset.py` (`send_mail`) y `reporting/delivery.py` (`EmailMessage`). Los comprobantes por correo salen de **US-19 / US-21** |
| Supabase / Base de datos PostgreSQL 16 + pgvector | C1–C4 | `settings.py` (`DATABASE_URL`, `DB_SEARCH_PATH` por el esquema `extensions` de Supabase), `requirements.txt` (`psycopg`, `pgvector`) y `assistant/models.py` (`VectorField(768)`) |
| Stripe | C1–C3 | **US-18** (pago en línea con Stripe y webhook firmado). Está descrito en `docs/sprints/sprint-2/reparto.md`; todavía no tiene archivo en `main` |
| Firebase Cloud Messaging | C1–C3 | **US-28** (notificaciones push, Épica 6). Está nombrado en `docs/documento/sprint-2-capitulo-4.md` 2.1.1.1 y en `reparto.md`; todavía no tiene archivo en `main` |
| Aplicación web | C2, C3 | `frontend/package.json` (react 19, vite 8, typescript), `frontend/src/api/cliente.ts` (`VITE_API_BASE_URL`, JWT y `X-Organization`) y `frontend/src/paginas/` |
| Aplicación móvil | C2, C3 | `mobile/pubspec.yaml` (Flutter, `http`, `go_router`), `mobile/lib/core/config.dart` (`API_BASE_URL`), `core/api/client.dart` y `core/router/app_router.dart` |
| API REST | C2, C3 | `backend/config/settings.py`, `backend/config/urls.py` y `requirements.txt` (Django 5.2, DRF, SimpleJWT, gunicorn y whitenoise para Railway) |
| Railway / Supabase (en las descripciones) | C2 | Despliegue documentado en `docs/entorno/` y en los comentarios de `settings.py` |
| Rutas de la API | C3 | `backend/config/urls.py` (`/api/health/` y un `include` por app) |
| TenantMiddleware | C3 | `backend/tenancy/middleware.py` y la lista `MIDDLEWARE` de `settings.py` |
| AuditTrailMiddleware | C3 | `backend/audit/middleware.py` y la lista `MIDDLEWARE` de `settings.py` |
| accounts | C3 | `backend/accounts/urls.py` (register, login, token/refresh, logout, me, users/me, password-reset, users, roles), `authentication.py` y `PASSWORD_HASHERS` (Argon2) |
| tenancy | C3 | `backend/tenancy/urls.py` (organizations, plans, subscriptions, dashboard, alerts) |
| catalog | C3 | `backend/catalog/urls.py` (branches, specialties, professionals, services) y `search.py` |
| patients | C3 | `backend/patients/urls.py` (dependents, history) |
| scheduling | C3 | `backend/scheduling/urls.py` (schedules, blocks, availability) |
| appointments | C3 | `backend/appointments/urls.py` (appointments, cancel, reschedule) y `booking.py` |
| audit | C3 | `backend/audit/urls.py` (logs) y `services.py` |
| reporting | C3 | `backend/reporting/urls.py` (datasets, run), `exporters.py` (`FORMATS = csv, xlsx, html, pdf`) y `delivery.py` |
| backups | C3 | `backend/backups/urls.py` (create, inspect, restore, records) y `services.py` (copia en JSON) |
| encounters | C3 | **US-24 / US-25**, en `main` desde los PR #48 y #50: `backend/encounters/urls.py` (agenda, apertura, detalle, sign, amendments), `models.py` y `services.py` |
| payments | C3 | **US-18 / US-19** (pago con Stripe, webhook firmado y comprobante QR). Según `reparto.md` es la app `payments` más `appointments/receipts.py`; todavía no tiene archivo en `main` |
| notifications | C3 | **US-28** (push con FCM). El nombre `notifications` es una convención de estos diagramas: el reparto no le fija un nombre a la app. Todavía no tiene archivo en `main` |
| assistant | C3 | `backend/assistant/urls.py` (suggest, reindex) y INSTALLED_APPS |
| Acceso a datos (ORM) | C3 | `settings.py` (`DATABASES`, psycopg 3) y `pgvector.django` (usado en `retrieval.py` y `models.py`) |
| Las 14 cajas de C4 | C4 | Los archivos homónimos de `backend/assistant/`. Las funciones están copiadas de las definiciones `def` y `class` de cada archivo |
| audit.services | C4 | `assistant/views.py` y `reindex_views.py` importan `audit.services.record` |
| catalog.models | C4 | `assistant/corpus.py` importa `Branch`, `BranchHours`, `PractitionerBranch`, `PractitionerSpecialty` y `Service`. `retrieval.py` e `indexing.py` importan `Specialty` |

#### Coherencia con el capítulo 4

Los diagramas siguen el sistema completo que describe `docs/documento/sprint-2-capitulo-4.md`, en el apartado 2.1.1:

- los cuatro externos son Stripe, Gemini, FCM y el correo;
- `appointments`, `payments`, `encounters` y `assistant` figuran como componentes.

Hay dos diferencias con ese texto:

1. **El Titular no es un actor aparte.** Figura como "Paciente (titular y dependientes)", porque así está en los roles sembrados.
2. **C3 suma tres piezas transversales:** `notifications`, como el componente que habla con FCM, y los dos middlewares. Además dibuja el acceso a datos como un solo componente, en lugar de una línea de cada app a la base.

---

## 3. Antes de abrir Enterprise Architect

Los diagramas UML de las secciones 4 a 8 van en `docs/diagramas/PlataformaMedica.eapx`.

| Requisito | Detalle |
|---|---|
| **Enterprise Architect** | Versión 15. Sirve la Trial, pero según el reparto (sección 5) **la licencia Trial del equipo caducaba cerca del 22/09/26**: confirmen que EA sigue abriendo antes de planificar el trabajo. |
| **Una sola persona y una sola rama** | El `.eapx` es binario y no se fusiona (regla 6 de la sección 1). |
| **EA cerrado para cualquier script** | Si EA está abierto, su copia en memoria pisa lo que escriba un script y se pierde todo el trabajo, **sin error**. |

**A mano o por script.** Los cinco tipos se pueden dibujar a mano en EA. La guía de Violet Boutique los generó con scripts de PowerShell sobre la API COM de EA (`scripts/ea-*.ps1` de ese repositorio), en dos pasadas: primero la API COM crea elementos, conectores y diagramas; después, con EA cerrado, se escribe por OLEDB directo sobre el `.eapx` lo que la API no deja tocar (orden Z, colores, geometría de los mensajes de secuencia, operandos de los fragmentos). Las recetas de abajo dicen en cada caso qué hace falta saber para cualquiera de las dos formas. Si se decide automatizar, la guía completa sigue en `D:\UNI\SI2\Primer_Parcial\GUIA-DIAGRAMAS-EA.md`.

**Tres trampas de EA que aparecen en los cinco tipos:**

- **EA dibuja toda relación que exista entre los elementos presentes en el lienzo**, aunque la hayan creado para otro diagrama. Si aparece una línea que no corresponde, se oculta en ese diagrama (clic derecho › *Visibility › Hide Connector*); no se borra, porque desaparecería también del diagrama donde sí va.
- **Borrar un diagrama no borra sus conectores.** Quedan en el modelo y vuelven a aparecer en el próximo diagrama que muestre esos elementos.
- **Un diagrama y sus elementos van en el mismo paquete.** Si no, EA escribe `(from OtroPaquete)` debajo de cada elemento.

---

## 4. Diagramas de clases

Hay dos diagramas de clases distintos, y no hay que confundirlos: las **clases de análisis**, que son de comportamiento y van una por caso de uso, y el **modelo de dominio**, que es de datos y va uno para todo el sistema.

### 4.1 Clases de análisis (una por caso de uso)

**Tipo de EA:** `Logical`.

Cada caso de uso tiene su diagrama, con tres estereotipos que EA dibuja como tabla: `frontera`, `controlador` y `entidad`. Son las mismas clases del diagrama de comunicación del mismo caso de uso.

**Nivel de detalle:**

| Estereotipo | Qué es en este proyecto | Atributos | Operaciones |
|---|---|---|---|
| `frontera` | la pantalla (React o Flutter) **y** la vista de DRF que la atiende | — | la acción de la pantalla y el endpoint |
| `controlador` | el servicio o la función que decide | — | las funciones reales, con su firma |
| `entidad` | el modelo de Django, es decir, la tabla | **las columnas**, con su tipo de la base | las consultas que se hacen sobre esa tabla |

**El actor va en el diagrama** (corrección del 17/09/2026). La frontera existe porque alguien la usa: sin el actor, el diagrama no dice quién empieza el caso de uso. Va unido a la frontera con una asociación, con rol en mayúsculas y cardinalidad `1 — 1`. Si el caso de uso tiene dos disparadores, van los dos. En US-31, por ejemplo, el paciente pregunta (`SuggestView`) y el administrador dispara la indexación (`ReindexView`).

**Las uniones son siempre asociaciones**, con el rol en MAYÚSCULAS (`DELEGA_EN`, `CONSULTA`, `PERTENECE_A`) y la cardinalidad en los dos extremos (regla 3 de la sección 1).

**Ejemplo: US-05, edición de perfil.**

| Clase | Estereotipo | Contenido |
|---|---|---|
| Paciente | actor | — |
| `api/perfil.ts` (lo que llama `Perfil.tsx`) | frontera | `obtenerPerfil(contexto)`, `actualizarPerfil(datos, contexto)`, `cambiarContrasena(datos, contexto)` |
| `accounts/views/profile.py` | frontera | `GET /api/accounts/users/me/`, `PATCH /api/accounts/users/me/`, `POST /api/accounts/users/me/password/` |
| `ProfileSerializer` | controlador | `to_internal_value(data)`, `validate_email(value)` |
| `PasswordChangeSerializer` | controlador | `validate(attrs)` |
| `accounts/passwords.py` | controlador | `validate_password_strength(password, user)`, `confirm_match(password, confirmation)` |
| `User` | entidad | `id: uuid`, `organization_id: uuid`, `email: varchar(254)`, `first_name`, `last_name`, `phone`… |
| `Patient` | entidad | `user_id: uuid`, `first_name`, `last_name`, `phone`… |
| `AuditLog` | entidad | `action`, `entity`, `entity_id`, `detail: jsonb`… |

**Cómo se escribe en EA:**

- **Las operaciones se cargan con sus parámetros, no con la firma en el nombre.** Si se escribe `validate_email(value)` como nombre, EA le agrega `()` y sale `validate_email(value)()`. Se pone el nombre solo y los parámetros en la pestaña de parámetros. **EA imprime el tipo de cada parámetro, no su nombre**: si el tipo queda vacío, sale `retrieve(, , )`. Pongan el mismo texto en el nombre y en el tipo.
- **Un endpoint va como atributo, no como operación**: `POST /api/assistant/suggest/ : 200 | 403 | 503`. Como no lleva paréntesis, EA le agregaría `()` si fuera operación.
- **El alto de la caja** es más o menos `60 + atributos × 18 + operaciones × 18` píxeles. Si queda corta, EA recorta la lista sin avisar.

### 4.2 Modelo de dominio (uno para todo el sistema)

**Tipo de EA:** `Logical`.

Convenciones del modelo de referencia de cátedra:

- **una clase por tabla**, con el nombre de la entidad en **MAYÚSCULAS**: `USERS`, `APPOINTMENTS`, `ENCOUNTERS`;
- **sin operaciones**: es un modelo de datos, no de comportamiento;
- **atributos privados**, con la clave primaria **primero**;
- **nombres de columna en minúsculas**, como en el código: `organization_id`, `starts_at`;
- relaciones como **asociación** con un **verbo en MAYÚSCULAS** (`TIENE`, `RESERVA`, `SE_ATIENDE_EN`) y cardinalidad en los dos extremos.

Dos agregados que valen la pena:

1. **El tipo de cada columna**, para que el modelo lógico y el esquema físico digan lo mismo.
2. **El estereotipo `«PK»` / `«FK»`** en cada columna que lo sea, y `«PK,FK»` cuando es las dos cosas. Sin eso hay que adivinar qué columna cierra cada relación.

**El contenido no se transcribe a mano.** Sale de los modelos de Django (`backend/*/models.py`) y de las migraciones, y se verifica columna por columna después de dibujar. El esquema documentado está en `docs/modelo-datos/`.

**Las cardinalidades salen de lo que la base obliga, no de la prosa.** Dos casos de este proyecto donde es fácil equivocarse:

- **`patients.user_id` es `OneToOne` y admite NULL.** Un usuario tiene **0 o 1** ficha de paciente, nunca "exactamente 1": un administrador no es paciente, y un dependiente es paciente sin usuario.
- **El UNIQUE compuesto no hace única a cada columna.** `users` tiene `UNIQUE(organization_id, email)`: **el correo no es único en toda la plataforma**, sólo dentro de cada organización (decisión D-5). Si las cardinalidades se derivan de `information_schema`, un `JOIN` contra `key_column_usage` devuelve una fila por columna de la restricción, y parece que `email` es único. Hay que agrupar por `constraint_name` y quedarse sólo con las restricciones de **una** columna.

**`organization_id` va en todas las clases.** Toda tabla protegida por RLS lleva el discriminador encima, aunque se pueda deducir por otra relación (`RolePermission` lo tiene denormalizado a propósito). Es el argumento multi-inquilino del proyecto aplicado al modelo de datos: conviene que se vea.

**Disposición:** columnas agrupadas por app (`accounts`, `tenancy`, `catalog`, `patients`, `scheduling`, `appointments`, `encounters`, `assistant`), de izquierda a derecha. Las autorreferencias —`patients.guardian_id`, el dependiente que apunta a su titular— necesitan aire a la derecha. El alto de cada caja es más o menos `60 + columnas × 18`.

---

## 5. Diagrama de secuencia

**Tipo de EA:** `Sequence`. Es el más difícil de los cinco.

### 5.1 Las líneas de vida

- **Una línea de vida no es la clase puesta en el lienzo.** Es un elemento de secuencia, **sin nombre**, cuyo clasificador es la clase del diagrama de clases de análisis. Así EA la rotula `: SuggestView` y **el vínculo queda vivo**: si se renombra la clase, se renombra la línea de vida. Si se escribe el nombre a mano, es texto suelto y se desincroniza.
- **El actor es el mismo elemento del modelo de casos de uso**, no una copia.
- **El orden es por rol, no por aparición:** actor · frontera · controladores · entidades · sistemas externos. Algunos mensajes van hacia atrás, y se acepta: lo que se gana es que el diagrama se lea por capas de izquierda a derecha.
- **La línea de vida no muestra el estereotipo de su clase**, así que hay que ponérselo también a ella, y pintarla con el color de su rol (regla 4 de la sección 1).

### 5.2 Qué se escribe en cada mensaje

| Tramo | Qué se escribe | Ejemplo de este proyecto |
|---|---|---|
| Actor → frontera | la acción del usuario | `1.1: describirSintomas(texto)` |
| Frontera → controlador | la función real, con su firma | `1.3: check(question)` |
| Controlador → controlador | la función auxiliar | `1.5: embed_query(text)` |
| Controlador → entidad | la consulta, literal | `1.6: SELECT … FROM assistant_catalog_fragments WHERE organization_id = … ORDER BY embedding <=> …` |
| Entidad → controlador | el tipo del resultado, como **retorno** (línea punteada) | `1.6.1: list[CatalogFragment]` |
| Controlador → externo | la llamada al servicio | `1.8: generate_content(prompt)` |
| Controlador → frontera (error) | el error y su código HTTP | `4.1: turno_ocupado → 409` |

**La numeración se hereda del diagrama de comunicación** del mismo caso de uso, para que el mismo mensaje se siga en los dos capítulos. Los retornos, que el diagrama de comunicación no tiene, se numeran como subnivel del mensaje que los provoca (`1.6` → `1.6.1`), para no correr la numeración.

**El mensaje a sí mismo** (el lazo que un objeto se manda) es el que muestra que el trabajo ocurre adentro y no en un ida y vuelta inventado. Toda llamada de un módulo a una función propia es uno de estos: `_grounded_fallback()` dentro de `generation.py`, o `_sincronizar_paciente()` dentro de `accounts/views/profile.py`.

### 5.3 Fragmentos combinados

- **`alt`** para las ramas: cada operando lleva su guarda entre corchetes, y la guarda es la condición literal del `if`.
- **`loop`** para una repetición: un solo operando cuyo nombre es la guarda. Puede ir anidado dentro de un operando de un `alt`.
- Para cambiar el operador, doble clic sobre el fragmento y el desplegable **Interaction Operator**. Los operandos se agregan con clic derecho › *Combined Fragment › Add Operand*.

### 5.4 EA reacomoda el diagrama cada vez que lo abre

Esto es lo que más tiempo costó en el otro proyecto, y vale igual a mano:

1. **EA no respeta la altura de los mensajes.** Los apila por su número de orden, de 35 en 35 píxeles, cada vez que abre el diagrama.
2. **Las cajas de los fragmentos y las notas sí quedan donde están.** Por eso una caja puede terminar encerrando mensajes que no son suyos, y **no da ningún error**: el diagrama parece bien hasta que se lee.
3. **Mover cualquier cosa "mueve todo".** Al arrastrar una nota, una caja o un mensaje, EA recalcula y las cajas de abajo dejan de encerrar lo que encerraban. **No acomoden las cajas a mano al final**: agreguen los mensajes en orden y ajusten las cajas una sola vez, revisando cada operando.
4. **Las notas de separación de flujo van en una columna a la izquierda**, fuera de toda caja. Una nota dentro de una caja queda atada a ella.

### 5.5 Ejemplo: US-31, consulta al asistente

Es el camino que el reparto propone (sección 5, "Tiempo (secuencia)", alternativa). Líneas de vida, en orden de rol:

| Línea de vida | Rol | Archivo |
|---|---|---|
| Paciente | actor | — |
| `: Asistente.tsx` | frontera | `frontend/src/paginas/Asistente.tsx` (o `assistant_screen.dart` en el móvil) |
| `: SuggestView` | frontera | `backend/assistant/views.py:53` |
| `: triage` | controlador | `backend/assistant/triage.py:231` |
| `: retrieval` | controlador | `backend/assistant/retrieval.py:117` |
| `: embeddings` | controlador | `backend/assistant/embeddings.py:226` |
| `: generation` | controlador | `backend/assistant/generation.py:80` |
| `: CatalogFragment` | entidad | `backend/assistant/models.py` |
| `: Google Gemini API` | externo | — |

Guion:

```
1.1   Paciente → Asistente.tsx        describirSintomas(texto)
1.2   Asistente.tsx → SuggestView     POST /api/assistant/suggest/ {question}
1.3   SuggestView → triage            check(question)
1.3.1 triage → SuggestView            TriageResult                          (retorno)
alt  [is_emergency]
  2.1 SuggestView → Asistente.tsx     {emergency: true, answer: EMERGENCY_MESSAGE}
     [no es urgencia]
  1.4 SuggestView → retrieval         retrieve(organization, question, limit=5)
  1.5 retrieval → embeddings          embed_query(question)
  1.5.1 embeddings → Gemini           embed_content(question)
  1.6 retrieval → CatalogFragment     SELECT … WHERE organization_id = … ORDER BY embedding <=> …
  1.6.1 CatalogFragment → retrieval   list[CatalogFragment]                 (retorno)
  1.7 SuggestView → retrieval         rank_specialties(fragments)
  1.8 SuggestView → generation        answer(question, fragments, specialty_name)
  1.9 generation → generation         _call_model(question, context)        (mensaje a sí mismo)
  1.9.1 generation → Gemini           generate_content(prompt)
  1.10 SuggestView → Asistente.tsx    {specialty, fragments, answer}
```

Dos cosas que el diagrama tiene que dejar ver, porque son las que se defienden: **el `WHERE organization_id` va antes del `ORDER BY`** (regla 9 del reparto), y **si `triage` dispara, no se consulta a nadie más**.

---

## 6. Diagrama de estado

**Tipo de EA:** `Statechart`.

### 6.1 Qué se dibuja, y qué no

**No es el ciclo de vida de un objeto.** Es el **flujo de una transacción** de principio a fin, y va **uno por caso de uso transaccional**. Así es el ejemplo de cátedra (`CU1`, pág. 10 de *todos los diagramas.pdf*):

```
Inicio → Loguear Administrador ─[correcto]→ Seleccionar opcion Usuario
                                              ├─[listar]→ Desplegar lista
                                              ├─[crear]→ Crear Usuario ─[llenar datos]→ Revisar Datos
                                              ├─[modificar]→ Modificar Usuario ─[llenar datos]↗
                                              └─[eliminar]→ ID del usuario a eliminar ─[correcto]→ Eliminar Usuario
                                   → Transaccion completada → Fin
```

> **Ojo con la propuesta del reparto.** La sección 5 del reparto del Sprint 2 propone como diagrama de estados "el ciclo de vida de la ficha" (*pendiente de pago → confirmada → atendida…*). En el otro proyecto se hizo justamente eso con el objeto `Reserva`, y la ingeniera lo corrigió el 15/09/2026: estaba bien como máquina de estados y mal como entregable. **Conviene seguir el ejemplo de cátedra.** Los estados de la ficha no se pierden: son la segunda línea de vida del diagrama de tiempo de US-17 (sección 8.4).

**Los estados son actividades de la transacción**, no valores de una columna: autenticar, seleccionar, capturar, validar, informar. El sumidero es siempre `Transaccion completada`, y después el estado final.

### 6.2 Cómo se lee contra el código de este proyecto

| Elemento del diagrama | Qué es en el código |
|---|---|
| Primer estado (`Autenticar <actor>`) | `permission_classes` de la vista: `IsAuthenticated`, o la clase de permiso (`CanUseAssistant`) que llama a `user.has_permission(...)` |
| Guarda del rechazo de autorización | 401 sin token, 403 sin permiso |
| `Seleccionar operacion` | el menú de la pantalla: cada rama es un endpoint o un método HTTP distinto |
| Estados `Capturar ...` | el formulario de la pantalla |
| `Validar datos` | el serializer y las comprobaciones que hay antes de escribir |
| `Informar error` | la respuesta con su `code` estable (`contrasena_actual_incorrecta`, `turno_ocupado`) |
| `Transaccion completada` | el `transaction.atomic()` que se cierra sin excepción |
| Guarda de cada transición | la condición literal del `if`, entre corchetes |
| `{...}` al final del rótulo | el ancla: `archivo:línea`, o el código HTTP |

### 6.3 Ejemplo completo: US-05, edición de perfil

| Desde | Hasta | Guarda | Sale de |
|---|---|---|---|
| *(inicial)* | Autenticar Paciente | — | — |
| Autenticar Paciente | Seleccionar operacion | `[token válido]` | `IsAuthenticated`, `views/profile.py:45` |
| Autenticar Paciente | *(final de rechazo)* | `[sin token]` | `{401}` |
| Seleccionar operacion | Desplegar perfil | `[consultar]` | `GET /api/accounts/users/me/` |
| Seleccionar operacion | Capturar datos de contacto | `[editar datos]` | `PATCH /api/accounts/users/me/` |
| Seleccionar operacion | Capturar contraseñas | `[cambiar contraseña]` | `POST /api/accounts/users/me/password/` |
| Capturar datos de contacto | Validar datos | `[guardar]` | `Perfil.tsx` |
| Validar datos | Transaccion completada | `[sólo campos editables y correo libre]` | `serializers/profile.py:83` y `:102` |
| Validar datos | Informar error | `[campo no editable]` | `{400 serializers/profile.py:83}` |
| Validar datos | Informar error | `[correo ya usado en el centro]` | `{400 serializers/profile.py:102}` |
| Capturar contraseñas | Validar contraseña | `[cambiar]` | `Perfil.tsx` |
| Validar contraseña | Informar error | `[la actual no coincide]` | `{400 contrasena_actual_incorrecta, views/profile.py:103}` |
| Validar contraseña | Informar error | `[nueva igual a la actual]` | `{400 contrasena_repetida, views/profile.py:110}` |
| Validar contraseña | Transaccion completada | `[actual correcta y nueva válida] / revoke_all_sessions()` | `views/profile.py:116–119` |
| Informar error | Seleccionar operacion | `reintentar()` | — |
| Desplegar perfil | Transaccion completada | — | — |
| Transaccion completada | *(final)* | — | — |

El rótulo usa la notación de UML `evento [guarda] / acción`. La acción `/ revoke_all_sessions()` es la que hace defendible el punto (c) de la historia: la contraseña cambia y las demás sesiones mueren en la misma transacción.

### 6.4 Cómo dibujarlo para que se lea

- **Las piezas son tres:** estados, el pseudoestado inicial (círculo negro) y el estado final (círculo negro con anillo). En EA, el inicial y el final son elementos `StateNode`; si se crean por script, sólo se dibujan los subtipos `100` (inicial), `101` (final) y `102` (punto de salida). Del `103` en adelante el elemento queda en el árbol y el lienzo sale vacío en ese punto, sin error.
- **Todos los rechazos van a un sumidero único** (`Informar error`), y de ahí sale **una sola** flecha de vuelta al menú. **Nunca dos flechas entre las mismas dos cajas**: EA pone el rótulo en el punto medio del conector, y con ida y vuelta los dos rótulos salen encimados, sin ningún error.
- **Puede haber varios estados finales, y conviene.** El rechazo de autorización muere en uno propio, dibujado al lado de la autenticación. Es UML válido, dice algo verdadero —un 401 no llega a haber transacción— y evita una flecha que cruce el lienzo entero.
- **La maqueta va en cinco columnas:** autenticación · menú · operaciones · validación · cierre. Las operaciones se apilan en la columna del medio, con unos 180 px entre una y otra, y el hueco entre el menú y las operaciones tiene que ser ancho (unos 600 px): por ahí salen las flechas del menú con sus rótulos, que son largos.
- **El rótulo de cada flecha cae en su punto medio, y el punto medio choca.** Si dos flechas terminan a la misma altura, los rótulos se encima. Se arregla corriendo medio renglón un estado: el sumidero de errores un poco más abajo que la última operación, el cierre entre dos filas. La regla general: **el punto medio de la flecha de vuelta tiene que caer en el hueco entre dos operaciones, nunca sobre una.**
- **El pseudoestado inicial va lejos del primer estado**: con la flecha corta, el rótulo queda encima del círculo.

---

## 7. Diagrama de navegación

**Tipo de EA:** `Logical` (es un diagrama de clases).

### 7.1 No es UML, y hay que decirlo

El diagrama de navegación **no existe en UML 2.5**. Es la extensión **UWE** (*UML-based Web Engineering*): un diagrama de clases con un perfil de navegación encima. Si en la defensa preguntan qué diagrama UML es, la respuesta honesta es que no lo es.

### 7.2 Va uno por actor

El ejemplo de cátedra se titula `class navegacion cliente`, y eso fija tres reglas:

1. **Va uno por actor.** El título nombra al actor, y el actor está dibujado adentro. No es un mapa del sistema entero.
2. **Lleva los controladores**, no sólo las pantallas.
3. **Los enlaces van rotulados `build` y `submit`**: se construye una vista, una vista postea.

En este proyecto hay dos clientes, así que el corte natural es **un diagrama por actor y por cliente**: *navegación Paciente — móvil*, *navegación Paciente — web*, *navegación Recepcionista — web*, etc. El reparto propone empezar por las pantallas del móvil del paciente (sección 5), porque es la superficie que más creció y la que se demuestra.

### 7.3 Qué es cada caja

| Estereotipo | Qué es | Ejemplo de este proyecto |
|---|---|---|
| `«menu»` | la pantalla eje del actor, la que deja el login | `Panel.tsx` (web), `_HomeScreen` de `app_router.dart` (móvil) |
| `«navigationClass»` | una vista de lista. Sus atributos son **los filtros reales** que manda al endpoint | `MisFichas.tsx`, `BuscarProfesionales.tsx` (`q`, `specialty`, `branch`) |
| `«formClass»` | un formulario. Sus atributos son **los campos reales** | `Perfil.tsx` (`first_name`, `last_name`, `phone`, `email`) |
| `«controller»` | el archivo de vistas del backend. Sus operaciones son **las funciones**, una por una | `accounts/views/profile.py` (`profile`, `change_password`) |
| actor | el mismo del modelo de casos de uso, no una copia | Paciente |

> **`view` y `form` son estereotipos reservados de EA.** Si se usan, EA cambia la forma de la caja por la de su perfil de interfaz de usuario, no escribe el `«...»` y —lo grave— **deja de dibujar los atributos**: el formulario sale como una caja vacía. Por eso `navigationClass` y `formClass`.

### 7.4 De dónde sale cada caja y cada guarda

**El diagrama es el espejo de las rutas.** Si se agrega una ruta, se agrega un nodo. Eso es lo que lo hace defendible.

| Cliente | Las rutas | Las guardas |
|---|---|---|
| Web | `frontend/src/App.tsx`, ruta por ruta | `RutaProtegida` (hay sesión) + el `requiere` de cada entrada de `frontend/src/componentes/BarraPlataforma.tsx` (el permiso) |
| Móvil | `mobile/lib/core/router/app_router.dart` | `redirect` (hay sesión), `SoloPacientes` / `patient_gate.dart` y `org_gate.dart` |

- **La ruta va como atributo, no en el nombre:** el nodo se lee «Mis fichas» y debajo `+ ruta: /mis-fichas`. Con el path en el nombre, el diagrama deja de leerse como un mapa de pantallas.
- **La guarda va en el nombre del enlace, entre corchetes:** `[sesión + appointments.appointment.read]`. Sale del `requiere` de la entrada del menú.
- **Las pantallas públicas cuelgan del actor, no del menú:** `/ingresar`, `/registro`, `/recuperar` y `/restablecer` no pasan por `RutaProtegida`. Dibujarlas colgando del menú sería mentir sobre la guarda.
- **El rótulo del enlace va en el nombre y sin estereotipo.** Con los dos puestos EA escribe `build` y debajo `«build»`. El estereotipo `navigationLink` se reserva para el enlace del actor al menú.

### 7.5 La cadena, sin idas y vueltas

```
Paciente ─[sesión]→ Panel.tsx ─build→ Perfil.tsx ─submit→ accounts/views/profile.py
                             ─build→ Asistente.tsx ─submit→ assistant/views.py
                             ─build→ MisFichas.tsx ─submit→ appointments/booking.py
```

- **No hay flecha de vuelta del controlador a la vista.** Con ida y vuelta entre las mismas dos cajas, EA encima los dos rótulos (sale `sbuild:` en lugar de `submit` y `build`). Además, la vuelta ya está contada: `Panel → Vista` es el mismo `build` que hace el controlador al devolver la página.
- **El cliente HTTP no se dibuja como clase** (`frontend/src/api/*.ts`, `mobile/lib/features/*/…_api.dart`): serían cajas que no deciden nada. Se nombra en la nota de cada controlador.
- **Si dos áreas comparten archivo, comparten caja.** Un elemento no puede estar dos veces en el mismo lienzo: se dibuja en la primera banda que lo usa y las demás le tiran la flecha. En dos diagramas distintos sí puede estar, y es **el mismo elemento**: `accounts/views/profile.py` sale en la navegación de todos los actores, porque todos tienen perfil.

### 7.6 Maqueta

- **Una banda por área funcional:** la vista arriba, su formulario debajo y el controlador a la derecha, centrado entre los dos. Así ninguna flecha cruza una caja.
- **El alto de una caja es un mínimo, no una medida.** Si tiene más atributos u operaciones de los que entran, **EA la agranda hacia abajo sin avisar** y se come la banda siguiente. Calculen el alto con el contenido.
- **El corredor entre el menú y la columna de vistas tiene que ser ancho** (unos 680 px): por ahí se abren en abanico las flechas `build` del menú. Si es angosto, cruzan por encima de los formularios.
- **Son acumulativos por sprint:** el del Sprint 2 lleva también lo del Sprint 1, porque un mapa de navegación es la foto de todo lo que el actor puede alcanzar.

---

## 8. Diagrama de tiempo

**Tipo de EA:** `Timing`.

### 8.1 Qué mide

Va **uno por caso de uso transaccional**. La línea de vida principal es **la transacción**, es decir, el viaje de una petición por las capas del backend:

```
Inactiva → Autenticando → Validando → Escribiendo → Confirmada → Inactiva
```

Es el mismo reparto de los diagramas de secuencia y de la arquitectura en capas:

| Estado | Qué es en este backend |
|---|---|
| `Autenticando` | `accounts/authentication.py` resuelve el JWT y fija el contexto del inquilino; después corre `permission_classes` |
| `Validando` | el serializer y las comprobaciones previas a escribir |
| `Escribiendo` | el cuerpo del `transaction.atomic()`: los `INSERT` / `UPDATE` |
| `Confirmada` | el `COMMIT`, que en este proyecto cierra `TenantMiddleware` al terminar la petición |

### 8.2 Un diagrama cuenta un solo escenario

Un caso de uso tiene varias ramas y una línea de vida dibuja una sola. **Se elige la rama donde el reloj manda**, no la más común. Y conviene sumar una **segunda línea de vida**: la del objeto cuyo estado cambia por el tiempo. Es lo que hace que el diagrama diga algo que el de secuencia no dice.

### 8.3 La regla es relativa, y hay que decirlo

**Los números de la regla (0 a 100) son instantes del escenario, no milisegundos medidos.** Nadie corrió un perfilador. Si preguntan, la respuesta honesta es esa.

**Lo que sí es real son las restricciones `{...}`: cada una sale de una constante del código o de un requisito.** En este proyecto el reloj manda en estos sitios, y son los que hay que mostrar primero:

| Dónde | La constante | Historia |
|---|---|---|
| ficha pendiente de pago | `APPOINTMENT_HOLD_MINUTES = 15` (`settings.py:257`), `expires_at` en `appointments/booking.py:140` | US-17 |
| bloqueo por intentos fallidos | `LOGIN_LOCKOUT_MINUTES = 15` (`settings.py:248`), tras 5 intentos (RNF-07) | US-02 |
| vida del token de acceso | `ACCESS_TOKEN_LIFETIME = 30 min` (`settings.py:294`) | US-02, US-05 |
| vida del token de refresco | `REFRESH_TOKEN_LIFETIME = 7 días` (`settings.py:295`), con rotación | US-02, US-05 |
| enlace de recuperación | 30 minutos, de un solo uso | US-03 |
| anticipación para cancelar | `cancellation_notice_hours` de cada organización | US-20 |
| webhook del pago | confirmación asíncrona de Stripe | US-18 (todavía sin código) |

Inventar milisegundos es peor que dejar la regla relativa y decirlo.

### 8.4 Ejemplo: US-17, la ficha que vence

Es el escenario donde el reloj manda en este sistema.

| Línea de vida | Estados (eje Y, de arriba abajo) |
|---|---|
| `: Transaccion` | Inactiva · Autenticando · Validando · Escribiendo · Confirmada |
| `: Appointment` | — · pending_payment · confirmed · expired |

| Instante | Línea de vida | Pasa a | Evento | Restricción |
|---|---|---|---|---|
| 5 | Transaccion | Autenticando | `POST /api/appointments/appointments/` | |
| 15 | Transaccion | Validando | `book_appointment()` | |
| 25 | Transaccion | Escribiendo | `select_for_update()` | |
| 35 | Transaccion | Confirmada | `COMMIT` | |
| 35 | Appointment | pending_payment | `create()` | |
| 40 | Transaccion | Inactiva | | |
| 84 | Appointment | expired | vence `expires_at` | `15 min` |

`Validando` son las comprobaciones de `book_appointment()` antes de entrar a la transacción (paciente, profesional, sucursal y `turno_pasado`). La validación del espacio, `_validate_slot_is_real()`, corre **después** del `select_for_update()`, ya con la agenda bloqueada (`booking.py:113` y `:127`): por eso está dentro de `Escribiendo` y no en `Validando`.

Las dos líneas escalonan **en el mismo instante del `COMMIT`**: ahí nace la ficha y empieza a correr su plazo. La rama alternativa —el pago llega antes de los 15 minutos y la ficha pasa a `confirmed`— es de US-18, y se puede dibujar como un segundo diagrama cuando exista.

### 8.5 Lo que este diagrama tiene flojo, y qué contestar

- **`Transaccion` no es una clase del modelo.** UML 2.5 dice que una línea de vida representa la instancia de un clasificador; `Appointment` lo tiene, `Transaccion` no. *Qué contestar:* que es la **petición HTTP en curso**, y que sus estados son las fases que atraviesa en el backend, las mismas de las capas y de los diagramas de secuencia. Se evaluó usar la vista como línea de vida y se descartó, porque la vista no cambia de estado; la petición sí.
- **Sin números medidos, agrega poco sobre el de secuencia** cuando no hay reloj. Por eso conviene elegir casos de uso con una restricción real (la tabla de 8.3).

### 8.6 Cómo se hace en EA

- La línea de vida es un elemento **`TimeLine`**, uno solo para las dos variantes. Por script, `StateLifeline` y `ValueLifeline` **no existen** en la API y fallan con «Referencia a objeto no establecida».
- Con la clase puesta como clasificador, **dejen el nombre vacío**: si no, EA rotula `Appointment: Appointment`.
- **La regla horizontal es fija, de 0 a 100**, estirada al ancho del elemento. Los instantes van en esa escala.
- **La restricción se escribe SIN llaves.** Las pone EA al dibujar; si se escriben, salen dobles: `{{15 min}}`.
- **El rótulo se dibuja hacia la derecha y EA no lo corta.** Con la línea de vida angosta, los rótulos consecutivos se pisan y el último se sale del marco. Funciona: línea de vida ancha (unos 1400 px), rótulos cortos, restricciones de una o dos palabras, la última marca en 84 como mucho. Lo que significa cada `{...}` va en la nota del diagrama, no en el rótulo.
- **Por script, las franjas se duplican si se corre dos veces** sobre el mismo elemento: `Partitions.AddNew` guarda solo y la colección vuelve a leerse vacía. Creen la línea de vida nueva cada vez.

---

## 9. Exportar a PNG para el Word

**Desde EA, a mano:** con el diagrama abierto, *Diagram › Save Image to File*, formato PNG.

- **Marca de agua.** Con EA 15 **Trial**, algunas exportaciones salen con *"EA 15.0 Unregistered Trial Version"* y otras no, sin patrón claro. **Revisen cada PNG antes de pegarlo.** Si salió con marca, exportar de nuevo desde la interfaz suele salir limpio.
- **Exporten después de abrir el diagrama**, no desde el árbol: EA recalcula la maqueta (sobre todo la de secuencia) al abrirlo.
- **Por script**, `PutDiagramImageToFile(guid, ruta, 1)` recibe el `DiagramGUID`, no el `DiagramID`, y los ids cambian cada vez que se regenera un paquete.

**Dónde y con qué nombre:** `docs/diagramas/png/Sprint 2/`, con el número de figura del documento y el nombre del caso de uso, como los del Sprint 1: `3.2 Diagrama de Estado - US-05 Edicion de perfil.png`.

---

## 10. Errores frecuentes en EA: síntoma, causa y arreglo

Los de esta tabla aparecen en los cinco tipos de diagrama de esta guía. La lista completa, con los de comunicación, componentes y la automatización, está en la sección 9 de `GUIA-DIAGRAMAS-EA.md`.

| Síntoma | Causa | Arreglo |
|---|---|---|
| Un script corre sin error pero **el modelo no cambió** | EA estaba abierto y su copia en memoria pisó lo escrito | Cerrar EA y volver a correr |
| Aparecen **relaciones que no corresponden** al diagrama | EA dibuja toda relación entre elementos presentes | Ocultarla en ese diagrama, no borrarla |
| Cada elemento lleva **`(from OtroPaquete)`** debajo | El diagrama y el elemento están en paquetes distintos | Mover el diagrama al paquete de sus elementos |
| Una operación sale como **`check(question)(): TriageResult`** | Se escribió la firma entera en el nombre | Nombre solo y parámetros aparte (sección 4.1) |
| Los parámetros salen **vacíos**: `retrieve(, , )` | EA imprime el **tipo** del parámetro, y quedó vacío | El mismo texto en nombre y tipo |
| El formulario de navegación sale **como una caja vacía** | Se usó el estereotipo reservado `form` o `view` | `formClass` / `navigationClass` |
| La caja **se come la de abajo** | EA agranda la caja hacia abajo cuando el contenido no entra | Calcular el alto con el contenido |
| Dos rótulos **encimados e ilegibles** | Ida y vuelta entre las mismas dos cajas: los puntos medios coinciden | Sumidero único (estado) o cadena (navegación) |
| En secuencia, una caja `alt` **encierra mensajes que no son** | EA reapila los mensajes de 35 en 35 al abrir y deja fijas las cajas | Ajustar las cajas una sola vez, al final, y no arrastrar nada después |
| En secuencia, **la guarda del flujo principal rotula la rama del error** | Las bandas del `alt` quedaron corridas | Revisar operando por operando qué mensajes encierra |
| Un estado inicial o final **no se dibuja** | Por script, `StateNode` con un subtipo fuera de `100`, `101`, `102` | Usar uno de esos tres |
| La línea de vida del de tiempo se rotula **`Appointment: Appointment`** | Tiene nombre **y** clasificador | Dejar el nombre vacío |
| La restricción del de tiempo sale **`{{15 min}}`** | Se escribieron las llaves | Escribirla sin llaves |
| Las franjas del de tiempo **salen duplicadas** | Por script, se corrió dos veces sobre el mismo elemento | Crear la línea de vida nueva en cada corrida |
| Los **atributos salen en orden alfabético** | Opción de EA *ordenar características alfabéticamente* | Desactivarla en las preferencias |
| El PNG sale con **marca de agua** | EA 15 Trial | Exportar de nuevo desde la interfaz |

---

## 11. Checklist antes de pegar un diagrama en el Word

- [ ] Cada nombre es el exacto del código, y se puede abrir en `main`.
- [ ] Cada guarda, restricción y código de error tiene su ancla.
- [ ] No hay relaciones ajenas visibles ni elementos duplicados en el árbol del proyecto.
- [ ] Las cardinalidades están en los dos extremos de cada asociación.
- [ ] Los estereotipos se ven entre comillas angulares (`«controlador»`), y en el caso correcto.
- [ ] **Secuencia:** cada operando del `alt` encierra exactamente los mensajes que le tocan, mirado **después** de que EA reacomodó el diagrama al abrirlo.
- [ ] **Estado:** no hay dos flechas entre las mismas dos cajas, y ningún rótulo está encimado.
- [ ] **Navegación:** las rutas coinciden una por una con `App.tsx` o `app_router.dart`.
- [ ] **Tiempo:** la nota del diagrama dice que la regla es relativa y qué significa cada restricción.
- [ ] El PNG no tiene la marca de agua de la versión Trial, y tiene fondo blanco.
