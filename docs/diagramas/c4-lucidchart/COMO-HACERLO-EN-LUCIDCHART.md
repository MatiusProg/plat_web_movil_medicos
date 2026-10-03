# Modelo C4 en Lucidchart

Hay cuatro archivos de diagrams.net en esta carpeta, uno por nivel:

| Archivo | Nivel |
|---|---|
| `c1-contexto.drawio` | C1: contexto |
| `c2-contenedores.drawio` | C2: contenedores |
| `c3-componentes.drawio` | C3: componentes (solo la API REST) |
| `c4-codigo.drawio` | C4: código (solo el componente `assistant`) |

Siguen las indicaciones de la docente (`D:\UNI\Si2\Diagramas c4, estado, navegacion y tiempo.md`):

- las personas son **nubes**, no monigotes;
- la base de datos es un **cilindro**;
- el sistema va al centro;
- en C2 y C3 el sistema o el backend es un **límite punteado** con los nodos adentro;
- todas las relaciones son líneas de **asociación** (sin punta de flecha);
- C3 es solo del backend, sin usuarios, y muestra solo los externos que se relacionan con él;
- C4 es **un único diagrama**: un componente semitransparente con los archivos adentro, y cada archivo con sus funciones en lista.

**Qué muestran.** Muestran el **sistema completo, todo como terminado**. Lo implementado sale de `origin/main` en el commit `1f79be4` (merge de US-32), más `encounters`, que está en la rama `feat/US-24-registro-de-la-atencion`. Lo que todavía no tiene código figura igual, y en la tabla (d) se indica la historia de usuario que lo implementa.

La rama `docs/c4-sprint-2` está atrasada: le faltan `appointments`, `assistant/corpus.py`, `assistant/reindex_views.py` y `assistant/medical_reference.py`. Si comparan el diagrama con el código, comparen contra `main`.

---

## (a) Importar los `.drawio` en Lucidchart

1. Abran Lucidchart.
2. Busquen la opción de importar. Puede estar en **Archivo › Importar** con un documento abierto, o en el botón **Importar** del panel de documentos. El nombre exacto del menú cambia entre versiones de Lucid. Si no lo encuentran, busquen "import draw.io" en la ayuda de Lucid.
3. Elijan **draw.io / diagrams.net** como origen y suban el `.drawio`. Cada archivo trae una sola página.
4. Hagan un archivo por vez. Así cada nivel queda como un documento o una página aparte.

### Cómo vienen armados los archivos

Esto cambió después de la primera importación, en la que Lucid mostraba cosas como "#10" en lugar de los textos:

- **Saltos de línea.** Todos los textos son texto plano, sin HTML. Los saltos de línea van como `&#xa;`, que es como los escribe draw.io. Antes iban como `&#10;`; es el mismo carácter en XML, pero el importador de Lucid lo mostraba como el texto literal "#10".
- **Dos formas por nodo.** El título de cada nodo es el texto de la forma, en negrita de 17 pt. La tecnología y la descripción van, en 13 pt, en una forma de texto aparte apoyada sobre la caja. Hacen falta dos formas porque en texto plano no se pueden mezclar dos tamaños dentro de una misma etiqueta. Esa forma de texto se llama `<id>-texto`.
- **Etiquetas de las relaciones:** 12 pt.
- **Títulos de las cajas de C4:** 16 pt en negrita. Las funciones van a 13 pt, una por renglón, cada una con "• ".
- **Ids descriptivos.** Todos los ids son descriptivos: `c2-api-django`, `c3-encounters`, `c4-retrieval`, `c1-rel-sistema-stripe`, etc. Si Lucid llegara a mostrar un id, igual se entiende qué es.

### Qué revisar después de importar

- **Texto encima de su caja.** Cada caja tiene encima su forma de texto, con la tecnología y la descripción. Si quedó detrás, tráiganla al frente. Después agrupen la caja con su texto (Ctrl+G) para moverlas juntas. En C4, agrupen el cuerpo con su encabezado azul (`<id>-titulo`).
- **Texto que se corta.** Las cajas tienen margen para la letra de Lucid. Si igual algún texto se corta, agranden la caja; no achiquen la letra.
- **Si aparece "#xa".** Si aparece "#xa" en algún texto, el importador no está leyendo los saltos de línea. Avisen: hay que generar los archivos con otra codificación.
- **Nubes y cilindros.** Confirmen que siguen siendo nubes y cilindros. Si alguno quedó como rectángulo, cámbienlo a mano: busquen "cloud" o "cylinder" en el buscador de formas y usen **Reemplazar forma**, si su versión lo tiene.
- **Límite punteado (C2 y C3).** Tiene que quedar con relleno transparente y **detrás** de los nodos. Si tapa a los nodos, envíenlo al fondo con clic derecho › *Enviar al fondo*.
- **Contenedor semitransparente (C4).** Lo mismo: debe quedar al fondo. Si perdió la transparencia, bájenle la opacidad del relleno a unos 30–40 %.
- **Las tres líneas con quiebres de C4.** Son `views.py → retrieval.py`, `reindex_views.py → audit.services` y `indexing.py → embeddings.py`. Si Lucid las dejó rectas y atraviesan otra caja, arrastren el punto medio de la línea para volver a quebrarla.
- **Agrupar.** Los nodos no son "hijos" del límite, porque así Lucid los importa mejor. Para mover todo junto, selecciónenlo y agrúpenlo.

---

## (b) Construir cada nivel a mano

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

### C1: Contexto

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

### C2: Contenedores

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

### C3: Componentes (solo la API REST)

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
| accounts | [App Django · SimpleJWT + Argon2] / Usuarios, roles, login JWT, registro y recuperación de contraseña |
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

### C4: Código (componente `assistant`)

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

---

## (c) Exportar a PNG para el Word

1. Con el diagrama abierto, vayan a **Archivo › Exportar › PNG**. En algunas versiones dice "Descargar como".
2. Elijan **alta resolución**. Si da a elegir DPI, pongan 300.
3. Marquen **fondo blanco**, no transparente. Con fondo transparente, Word muestra las letras sobre gris.
4. Si hay opción de **recortar al contenido**, actívenla para que no queden márgenes grandes.
5. En el plan gratuito, Lucid puede limitar la resolución o el tamaño del documento. Si la imagen sale chica, prueben exportar en **PDF** o **SVG** y convertirlo, o subir el zoom antes de exportar.
6. Guarden los PNG en `docs/diagramas/png/Sprin2/` con estos nombres: `C1-contexto.png`, `C2-contenedores.png`, `C3-componentes.png` y `C4-codigo.png`.
7. En Word, insértenlos con **Insertar › Imagen** al ancho de la página. El C4 es apaisado, así que conviene ponerlo en una sección con orientación horizontal.

---

## (d) De dónde sale cada elemento

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
| accounts | C3 | `backend/accounts/urls.py` (register, login, token/refresh, logout, me, password-reset, users, roles), `authentication.py` y `PASSWORD_HASHERS` (Argon2) |
| tenancy | C3 | `backend/tenancy/urls.py` (organizations, plans, subscriptions, dashboard, alerts) |
| catalog | C3 | `backend/catalog/urls.py` (branches, specialties, professionals, services) y `search.py` |
| patients | C3 | `backend/patients/urls.py` (dependents, history) |
| scheduling | C3 | `backend/scheduling/urls.py` (schedules, blocks, availability) |
| appointments | C3 | `backend/appointments/urls.py` (appointments, cancel, reschedule) y `booking.py` |
| audit | C3 | `backend/audit/urls.py` (logs) y `services.py` |
| reporting | C3 | `backend/reporting/urls.py` (datasets, run), `exporters.py` (`FORMATS = csv, xlsx, html, pdf`) y `delivery.py` |
| backups | C3 | `backend/backups/urls.py` (create, inspect, restore, records) y `services.py` (copia en JSON) |
| encounters | C3 | **US-24 / US-25**. Está en la rama `feat/US-24-registro-de-la-atencion` (commit `314a9bd`): `backend/encounters/urls.py` (agenda, apertura, detalle, sign, amendments), `models.py` y `services.py`. Todavía no está en `main` |
| payments | C3 | **US-18 / US-19** (pago con Stripe, webhook firmado y comprobante QR). Según `reparto.md` es la app `payments` más `appointments/receipts.py`; todavía no tiene archivo en `main` |
| notifications | C3 | **US-28** (push con FCM). El nombre `notifications` es una convención de estos diagramas: el reparto no le fija un nombre a la app. Todavía no tiene archivo en `main` |
| assistant | C3 | `backend/assistant/urls.py` (suggest, reindex) y INSTALLED_APPS |
| Acceso a datos (ORM) | C3 | `settings.py` (`DATABASES`, psycopg 3) y `pgvector.django` (usado en `retrieval.py` y `models.py`) |
| Las 14 cajas de C4 | C4 | Los archivos homónimos de `backend/assistant/`. Las funciones están copiadas de las definiciones `def` y `class` de cada archivo |
| audit.services | C4 | `assistant/views.py` y `reindex_views.py` importan `audit.services.record` |
| catalog.models | C4 | `assistant/corpus.py` importa `Branch`, `BranchHours`, `PractitionerBranch`, `PractitionerSpecialty` y `Service`. `retrieval.py` e `indexing.py` importan `Specialty` |

### Coherencia con el capítulo 4

Los diagramas siguen el sistema completo que describe `docs/documento/sprint-2-capitulo-4.md`, en el apartado 2.1.1:

- los cuatro externos son Stripe, Gemini, FCM y el correo;
- `appointments`, `payments`, `encounters` y `assistant` figuran como componentes.

Hay dos diferencias con ese texto:

1. **El Titular no es un actor aparte.** Figura como "Paciente (titular y dependientes)", porque así está en los roles sembrados.
2. **C3 suma tres piezas transversales:** `notifications`, como el componente que habla con FCM, y los dos middlewares. Además dibuja el acceso a datos como un solo componente, en lugar de una línea de cada app a la base.
