"""HISTÓRICO — no correr sobre otro documento.

Generó el 02/10/26 el texto y las tablas del capítulo del Sprint 2 sobre la copia
(partiendo de "Proyecto SI2 Grupo15 - avance sprint2.docx"). Usa índices de elemento
fijos de ese documento: sirve como registro de qué se escribió y con qué formato.
Para llevar ese contenido a otro .docx se usa trasplantar.py.
"""
from gen import *

x = load()
E = elements(x)
def S(n): t, a, b = E[n]; return x[a:b]
def T(n):
    s = S(n)
    assert E[n][0] == 'tbl', n
    assert '<w:drawing' not in s and '<w:pict' not in s, n
    return s
def para_text(n): return txt(S(n))

ops = {}  # índice -> (modo, xml)  modo: 'rep' reemplaza, 'after' inserta detrás
def rep(n, xml, expect=None):
    if expect is not None:
        assert expect in para_text(n), (n, para_text(n)[:80])
    assert '<w:drawing' not in S(n) and '<w:pict' not in S(n), n
    ops[n] = ('rep', xml)
def after(n, xml):
    assert n not in ops or ops[n][0] == 'rep'
    ops.setdefault(('after', n), xml)

# =====================================================================
# CAPÍTULO 2 — 2.4.3 y 2.4.4 (corrección del Modelo C4)
# =====================================================================
rep(580, P('C4 no reemplaza a UML: opera en un plano distinto. UML modela requisitos y diseño detallado —qué hace el sistema y cómo se estructura internamente—, mientras que C4 organiza la arquitectura por **nivel de zoom**: qué piezas existen, dónde corre cada una y cómo se comunican. En este proyecto se emplean ambos, con una división explícita:'), 'C4 no reemplaza a UML')
rep(581, BUL('**C4, en sus cuatro niveles.** Los niveles C1 y C2 se presentan en este capítulo: describen el sistema completo y no cambian de un sprint a otro. Los niveles C3 y C4 se presentan en el Capítulo 4, dentro del apartado 2.1.1 de cada sprint, porque su contenido sí cambia: son los componentes y el código que ese sprint construye.'), 'para los niveles C1')
rep(582, BUL('**UML** para casos de uso y paquetes (Capítulo 3) y para clases, secuencia, estados y despliegue (Capítulo 4).'), 'UML para casos')
rep(583, P('**C4 no es una notación nueva que haya que aprender aparte.** Es una forma de ordenar diagramas, y cada uno de sus cuatro niveles se dibuja con un diagrama UML corriente en Enterprise Architect: diagramas de componentes para C1, C2 y C3, y un diagrama de clases para C4. El nivel se indica con el estereotipo de cada elemento —«person», «software system», «container», «component»—, de modo que el diagrama sigue siendo UML válido y se lee como C4 al mismo tiempo.')
    + P('**Cómo se evita duplicar el diagrama de clases.** El nivel C4 podría solaparse con el diagrama de clases del Capítulo 4 si se dibujara el sistema entero. No se hace: el nivel C4 abre un solo componente por sprint, el más representativo de lo que ese sprint construyó, mientras que el diagrama de clases cubre el modelo de datos completo. Son dos recortes distintos del mismo código y responden preguntas distintas.'), 'fuera del alcance')

rep(585, P('**Nivel C1 — Contexto.** Muestra la plataforma como caja única, rodeada de sus usuarios y de los sistemas de terceros con los que intercambia datos.')
    + P('**Usuarios:** el Paciente y el Titular (aplicación móvil); el Recepcionista, el Médico y el Administrador de Organización (aplicación web); y el Superadministrador de Plataforma.')
    + P('**Sistemas externos:** Stripe (procesamiento de pagos), el proveedor de modelo de lenguaje (asistente de orientación y generación de resúmenes), Firebase Cloud Messaging (notificaciones push) y el servicio de correo transaccional.')
    + P('Lo que este diagrama debe dejar claro es que el **Superadministrador de Plataforma y el Administrador de Organización son dos actores distintos**: el primero da de alta organizaciones y planes, el segundo administra una sola organización y no ve los datos de las demás. Confundirlos es confundir el modelo multi-inquilino entero.'), 'Diagrama C1')
rep(586, P('**Nivel C2 — Contenedores.** Descompone la plataforma en las unidades que se despliegan y se ejecutan por separado. Son cuatro:'), 'cinco contenedores')
rep(587, table(T(587), [(0, None), (1, None), (2, None), (3, ['API REST', 'Django REST Framework', 'Lógica de negocio, autenticación y resolución de inquilino']), (4, None)], [], 1))
c3_rows = [
    ['accounts', 'Sprint 0', 'Autenticación, usuarios, roles y permisos'],
    ['tenancy', 'Sprint 0', 'Organizaciones, sucursales y planes de suscripción'],
    ['catalog', 'Sprint 1', 'Especialidades, profesionales y sucursales'],
    ['patients', 'Sprint 1', 'Pacientes, titulares, dependientes y antecedentes'],
    ['scheduling', 'Sprint 1', 'Agendas, disponibilidad y bloqueos'],
    ['appointments', 'Sprint 2', 'Reserva, cancelación y reprogramación de la ficha'],
    ['payments', 'Sprint 2', 'Pago en línea, confirmación y comprobante'],
    ['encounters', 'Sprint 2', 'Historia clínica digital'],
    ['assistant', 'Sprint 2', 'Asistente de orientación (RAG)'],
    ['audit', 'Sprint 1', 'Bitácora de auditoría'],
    ['reporting', 'Sprint 2', 'Reportes configurables y su exportación'],
    ['backups', 'Sprint 2', 'Copias de seguridad y restauración'],
]
rep(588,
    P('**El subsistema de inteligencia artificial no es un contenedor, y conviene decir por qué.** Un contenedor, en C4, es algo que se despliega y se reinicia por separado. El asistente de orientación es una aplicación de Django que corre dentro del mismo proceso que el resto de la API: comparte su despliegue, su configuración y su ciclo de vida. Su lugar es el nivel C3, que es donde aparece. El modelo de predicción de inasistencia, que sí podría justificar un contenedor propio por entrenarse fuera del ciclo de la petición, corresponde a las historias US-35 a US-38 y todavía no existe.')
    + P('El punto arquitectónico que este diagrama debe mostrar es que **el aislamiento por inquilino se aplica dos veces**: en la API, donde la organización se resuelve desde el token y nunca desde el cuerpo de la petición; y en la base de datos, donde Row Level Security forzado lo hace cumplir aunque la consulta provenga de un comando de mantenimiento. El filtro explícito documenta la intención; RLS la hace cumplir. Es el apartado 1.1.6 llevado a la arquitectura.')
    + P('**Nivel C3 — Componentes.** Abre un contenedor y muestra sus bloques internos. Se abre la API REST, que es el contenedor que concentra la lógica y el que más crece en cada sprint. Cada componente corresponde a una aplicación de Django, con su propio conjunto de rutas:')
    + table(T(587), [(0, ['Componente', 'Sprint', 'Responsabilidad'])], c3_rows, 1)
    + P('Aparte de los doce se dibuja el **middleware de inquilino**, que no es una aplicación más sino una pieza transversal: corre en todas las peticiones, resuelve la organización desde el token y la fija en la sesión de PostgreSQL antes de que cualquier componente consulte.')
    + P('**Nivel C4 — Código.** Abre un componente y muestra sus clases y módulos. Se abre el componente assistant, por ser el énfasis del proyecto: es un diagrama de clases de las cuatro piezas del asistente —la barrera de urgencias, la recuperación por similitud, la redacción y la indexación—, con la entidad que guarda los fragmentos y su vector, y con el modelo del catálogo del que sale el corpus.')
    + P('Este diagrama tiene una regla propia: **cada relación dibujada corresponde a una dependencia que existe en el código**. No se dibujan relaciones conceptuales. Es lo que permite usarlo para leer el módulo sin abrirlo.')
    + P('**Nota sobre la elaboración.** Los cuatro diagramas se construyen en Enterprise Architect, en el modelo PlataformaMedica.eapx. Las fronteras de sistema y de contenedor se dibujan con el elemento Boundary —un recuadro— y no con un paquete, que Enterprise Architect representa como una carpeta opaca que tapa lo que contiene.'),
    'Nota para elaborar')
# 2.5: tabla de diagramas, dos filas más
rep(595, table(T(595), [(i, None) for i in range(6)],
               [['Modelo C4, niveles C1 y C2', '2.4', 'Scrum Master'],
                ['Modelo C4, niveles C3 y C4', '4 (2.1.1 de cada sprint)', 'Scrum Master']], 5))

# =====================================================================
# CAPÍTULO 4 — SPRINT 2
# =====================================================================
# 1.3 Contexto del Sistema
rep(2106, P('Va un diagrama de casos de uso que reúne los casos del sprint con sus actores, igual que en el Sprint 1. Los casos que entran son los de reserva, pago, comprobante, cancelación, confirmación de asistencia, check-in, registro de la atención, historial y las tres consultas al asistente: CU18 a CU23, CU25, CU26, CU32, CU33 y CU35, más los tres de arrastre del Sprint 1 (CU6, CU10 y CU11).')
     + P('**Pendiente de dibujar en Enterprise Architect.** Es el único diagrama de planificación del Sprint 2 que todavía no está en el modelo.'), 'Al parecer viene')

# 1.4 Sprint Backlog: estado real al 02/10/26
bk = T(2111)
estado = {'T-25': 'Completado', 'T-28': 'Completado', 'T-33': 'Completado',
          'T-35': 'Completado', 'T-34': 'En progreso', 'T-36': 'En progreso'}
pre, rs, post = split_tbl(bk)
new_rows = []
for r in rs:
    cs = [txt(c) for c in cells(r)]
    if cs[0] in estado:
        r = set_row(r, [None, None, None, None, None, estado[cs[0]], None])
    new_rows.append(r)
rep(2111, pre + ''.join(new_rows) + post)
rep(2112, P('**Estado al 02/10/26.** Están integradas en la rama principal cuatro historias: US-17 y US-20 (PR #45, 16/09), US-31 (PR #41, 16/09) y US-34 (PR #46, 30/09). La tarea T-36 tiene terminado el Modelo C4 y los diagramas de lógica de negocio de US-31; los diagramas de estado, navegación y tiempo todavía no se hicieron. Las demás historias no tienen código en el repositorio a esta fecha.'))

# 2.1.1 — textos que acompañan a cada figura (reemplazan las notas copiadas de EA)
c1 = ['El primer nivel presenta la plataforma como una caja única y muestra únicamente quién la usa y con qué sistemas de terceros intercambia datos. Su propósito es que alguien ajeno al desarrollo entienda el alcance del sistema sin necesidad de conocer su construcción.',
      'Intervienen seis roles de usuario. Del lado de la aplicación móvil, el **Paciente**, que consulta especialidades, reserva y paga su ficha y consulta al asistente de orientación, y el **Titular**, que además gestiona a sus dependientes y reserva por ellos. Del lado de la aplicación web, el **Recepcionista**, que registra pacientes, cobra en caja y marca la asistencia; el **Médico**, que consulta la agenda y registra la historia clínica; y el **Administrador de Organización**, que administra su centro médico y consulta sus reportes. Por fuera de ambas aplicaciones, el **Superadministrador de Plataforma** da de alta organizaciones y planes de suscripción.',
      'La distinción entre estos dos últimos roles no es un detalle de nomenclatura: el Superadministrador opera sobre la plataforma y el Administrador de Organización sobre una única organización, sin acceso a los datos de las demás. Es la traducción, en términos de actores, del modelo multi-inquilino descrito en el apartado 1.1.',
      'Los sistemas externos son cuatro: **Stripe**, que cobra la ficha y confirma el pago mediante un webhook; **Google Gemini**, proveedor del modelo de lenguaje que vectoriza el texto y redacta las respuestas del asistente; **Firebase Cloud Messaging**, que entrega las notificaciones push al teléfono del paciente; y el **servicio de correo transaccional**, que envía comprobantes y reportes. De los cuatro, Stripe y Gemini se integran en este sprint; el envío de correo ya está operativo desde la característica de reportes, y las notificaciones push corresponden a la Épica 6.']
c2 = ['El segundo nivel abre la caja y muestra las unidades que se despliegan y se ejecutan por separado. Son cuatro: la **aplicación móvil** en Flutter, que se distribuye como APK; la **aplicación web** en React, que se compila a un bundle estático; la **API REST** en Django REST Framework, que concentra la lógica de negocio; y la **base de datos** PostgreSQL con la extensión pgvector, que guarda tanto los datos transaccionales como los vectores del asistente.',
      'Ambas aplicaciones cliente hablan con la API por HTTPS, con formato JSON y autenticación por token JWT; la API habla con la base de datos por el session pooler, sobre TLS.',
      '**El punto que este diagrama debe hacer visible es que el aislamiento entre organizaciones se aplica en dos lugares distintos.** En la API, porque la organización se resuelve a partir del token y nunca a partir del cuerpo de la petición, y se fija en la sesión de PostgreSQL antes de ejecutar cualquier consulta. Y en la base de datos, porque Row Level Security está forzado sobre las tablas del inquilino: aunque una consulta olvide filtrar, la base no devuelve filas ajenas. La primera capa documenta la intención; la segunda la hace cumplir. Es el apartado 1.1.6 llevado a la arquitectura, y es el diferencial del proyecto.']
c3 = ['El tercer nivel abre uno de los cuatro contenedores. Se abre la **API REST**, por ser el que concentra la lógica de negocio y el que más crece en este sprint. Cada componente corresponde a una aplicación de Django con su propio conjunto de rutas.',
      'De los doce componentes, **cuatro los crea este sprint**: appointments, que reserva la ficha; payments, que la cobra y emite el comprobante; encounters, que registra la atención clínica; y assistant, el asistente de orientación. Los ocho restantes —accounts, tenancy, catalog, patients, scheduling, audit, reporting y backups— vienen de sprints anteriores. Al 02/10/26 existen en el código appointments y assistant; payments y encounters siguen siendo diseño.',
      'Se dibuja además, separado de los doce, el **middleware de inquilino**. No es una aplicación más: es una pieza transversal que corre en todas las peticiones y fija el contexto de organización en la sesión de base de datos antes de que cualquier componente consulte. Dibujarlo una vez evita las cuarenta relaciones que harían falta para unir cada componente con la base de datos.',
      '**appointments es la ruta crítica del sprint.** Tres componentes dependen de que la ficha exista: payments cobra una ficha ya reservada, encounters registra la consulta sobre la ficha atendida, y el check-in de recepción marca la asistencia sobre esa misma ficha. Un atraso ahí atrasa tres historias más, de tres personas distintas.']
c4 = ['El cuarto nivel abre un componente y llega a las clases. Se abre assistant, por ser el énfasis del proyecto.',
      'El diagrama muestra las cuatro piezas del asistente en el orden en que se ejecutan. **triage** es la barrera de urgencias: compara el texto de la consulta contra una lista de señales y corre antes que todo lo demás; si dispara, no se recupera nada ni se llama al modelo de lenguaje. **retrieval** busca por similitud coseno sobre los vectores almacenados, filtrando por organización, y descarta el resultado si no supera un umbral mínimo. **generation** redacta la respuesta usando exclusivamente los fragmentos recuperados. Y **indexing**, que no corre por consulta sino cuando cambia el catálogo, parte cada descripción de especialidad en oraciones y guarda cada una con su vector.',
      'La entidad **CatalogFragment** guarda esos fragmentos, con una columna de tipo vector y el nombre del modelo que la generó. Aparece también **catalog.Specialty**, que no pertenece a este componente: se dibuja porque su campo de descripción es el corpus del asistente, lo que hace explícito que el sistema sólo puede responder sobre lo que la organización cargó en su propio catálogo.',
      'Cada relación de este diagrama corresponde a una dependencia que existe en el código fuente. No hay relaciones conceptuales.']
rep(2123, ''.join(P(t) for t in c1), 'NIVEL C1')
rep(2127, ''.join(P(t) for t in c2), 'NIVEL C2')
rep(2131, ''.join(P(t) for t in c3), 'NIVEL C3')
rep(2135, ''.join(P(t) for t in c4), 'NIVEL C4')

# 2.1.2 Diseño de datos
cols = lambda n, data: table(T(587), [(0, ['Columna', 'Tipo', 'Restricción'])], data, 1)
conceptual = [
    'El Sprint 2 agrega cuatro entidades al modelo y una columna a una entidad existente. Todas pertenecen a una organización y, como el resto de las tablas del inquilino, quedan bajo Row Level Security forzado con la política tenant_isolation.',
    '**Ficha (appointments).** Es la entidad central del sprint. Une a un Paciente con un Profesional en una Sucursal, sobre un espacio derivado de una Agenda, y registra qué Usuario la reservó —el propio paciente o su titular—. Una ficha reprogramada referencia a la ficha de la que proviene, de modo que el historial de cambios queda encadenado y no se pierde.',
    '**Fragmento del catálogo (assistant_catalog_fragments).** Es el corpus vectorizado del asistente. Cada fragmento pertenece a una organización y apunta a su fuente mediante el par tipo de fuente / identificador —una especialidad hoy; una sucursal o un servicio cuando entre US-32—. Se usa una referencia polimórfica y no una clave foránea por tipo para que todo el corpus viva en un único índice vectorial.',
    '**Reporte guardado (saved_reports)** y **Registro de respaldo (backup_records)** corresponden a las características generales 5 y 6: el primero guarda la definición de un reporte configurable de un usuario; el segundo deja constancia de cada copia de seguridad y de cada restauración.',
    '**Organización** suma el parámetro **cancellation_notice_hours**, la ventana de anticipación que exige US-20 para cancelar con devolución. Es un dato de la organización y no un número fijo en el código.',
    'Las entidades **Pago**, **Comprobante** y **Encuentro clínico** (US-18, US-19 y US-24) forman parte del diseño del sprint, pero a la fecha no tienen tablas creadas.',
]
logico_intro = 'El mapeo al modelo relacional de las tablas que el sprint efectivamente creó. Las claves foráneas de appointments hacia pacientes, profesionales, sucursales y agendas son **compuestas** —(x_id, organization_id)—, de modo que una ficha no puede referenciar un registro de otra organización ni aunque la aplicación se equivoque (RNF-08).'
t_app = [
    ['id', 'uuid', 'PK'],
    ['organization_id', 'uuid', 'FK organizations, NOT NULL'],
    ['patient_id', 'uuid', 'FK compuesta a patients (id, organization_id)'],
    ['booked_by_id', 'uuid', 'FK users, NOT NULL'],
    ['practitioner_id', 'uuid', 'FK compuesta a practitioners'],
    ['branch_id', 'uuid', 'FK compuesta a branches'],
    ['schedule_id', 'uuid', 'FK compuesta a schedules'],
    ['starts_at / ends_at', 'timestamptz', 'NOT NULL; ends_at > starts_at'],
    ['status', 'varchar(16)', 'pending_payment, confirmed, attended, cancelled, rescheduled, expired o no_show'],
    ['expires_at', 'timestamptz', 'Vencimiento de la reserva pendiente de pago (15 minutos por defecto)'],
    ['cancelled_at', 'timestamptz', 'NULL mientras no se cancele'],
    ['cancellation_reason', 'varchar(20)', 'patient, no_show_policy u organization'],
    ['refund_eligible', 'boolean', 'Se decide al cancelar, según la anticipación'],
    ['rescheduled_from_id', 'uuid', 'FK a appointments, ON DELETE SET NULL'],
    ['created_at / updated_at', 'timestamptz', 'NOT NULL'],
    ['(schedule_id, starts_at)', 'índice único parcial', 'Un solo turno activo por espacio: sólo cuenta si status es pending_payment o confirmed'],
]
t_frag = [
    ['id', 'uuid', 'PK'],
    ['organization_id', 'uuid', 'FK organizations, ON DELETE CASCADE'],
    ['source_type', 'varchar(20)', 'specialty, branch o service'],
    ['source_id', 'uuid', 'Identificador de la fuente'],
    ['position', 'smallint', 'Orden del fragmento dentro de su fuente'],
    ['text', 'text', 'El fragmento, prefijado con el nombre de su fuente'],
    ['embedding', 'vector(768)', 'Índice HNSW con vector_cosine_ops'],
    ['embedding_model', 'varchar(80)', 'Modelo que generó el vector'],
    ['(organization_id, source_type, source_id, position)', 'único', 'Reindexar reemplaza, no duplica'],
]
t_rep = [
    ['id', 'uuid', 'PK'],
    ['organization_id / owner_id', 'uuid', 'FK organizations / FK users'],
    ['name', 'varchar(120)', 'Único por organización y propietario'],
    ['description', 'varchar(300)', ''],
    ['dataset', 'varchar(40)', 'Conjunto de datos del catálogo de reportes'],
    ['definition', 'jsonb', 'Columnas, criterios y orden del reporte'],
    ['is_shared', 'boolean', 'Visible para el resto de la organización'],
]
t_bak = [
    ['id', 'uuid', 'PK'],
    ['organization_id / performed_by_id', 'uuid', 'FK organizations / FK users'],
    ['kind', 'varchar(10)', 'backup o restore'],
    ['filename / size_bytes', 'varchar(200) / bigint', 'Archivo generado y su tamaño'],
    ['row_counts', 'jsonb', 'Filas por tabla incluidas'],
    ['checksum', 'varchar(64)', 'Huella del archivo'],
    ['ip_address', 'inet', 'Origen de la operación'],
]
sql = """BEGIN;

-- =================================================================
-- Sprint 2 - fichas, asistente, reportes y respaldos
-- =================================================================

ALTER TABLE organizations
    ADD COLUMN cancellation_notice_hours integer NOT NULL DEFAULT 24
    CHECK (cancellation_notice_hours >= 0);

CREATE TABLE "appointments" (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations (id),
    patient_id uuid NOT NULL,
    booked_by_id uuid NOT NULL REFERENCES users (id),
    practitioner_id uuid NOT NULL,
    branch_id uuid NOT NULL,
    schedule_id uuid NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    status varchar(16) NOT NULL DEFAULT 'pending_payment',
    expires_at timestamptz NULL,
    cancelled_at timestamptz NULL,
    cancellation_reason varchar(20) NOT NULL DEFAULT '',
    refund_eligible boolean NULL,
    rescheduled_from_id uuid NULL
        REFERENCES appointments (id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT uq_appointment_id_org UNIQUE (id, organization_id),
    CONSTRAINT ck_appointment_time_order CHECK (ends_at > starts_at),
    CONSTRAINT ck_appointment_status CHECK (status IN ('pending_payment',
        'confirmed', 'attended', 'cancelled', 'rescheduled', 'expired', 'no_show'))
);
CREATE UNIQUE INDEX uq_appointment_active_slot
    ON appointments (schedule_id, starts_at)
    WHERE status IN ('pending_payment', 'confirmed');
ALTER TABLE appointments ADD CONSTRAINT fk_appointments_patients_same_org
    FOREIGN KEY (patient_id, organization_id)
    REFERENCES patients (id, organization_id) ON DELETE RESTRICT;
-- idem: practitioners, branches y schedules

CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE "assistant_catalog_fragments" (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL
        REFERENCES organizations (id) ON DELETE CASCADE,
    source_type varchar(20) NOT NULL,
    source_id uuid NOT NULL,
    position smallint NOT NULL DEFAULT 0,
    text text NOT NULL,
    embedding vector(768) NOT NULL,
    embedding_model varchar(80) NOT NULL,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT uq_fragment_source_position
        UNIQUE (organization_id, source_type, source_id, position)
);
CREATE INDEX ix_fragment_embedding_cosine
    ON assistant_catalog_fragments USING hnsw (embedding vector_cosine_ops);

CREATE TABLE "saved_reports" (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations (id),
    owner_id uuid NOT NULL REFERENCES users (id),
    name varchar(120) NOT NULL,
    description varchar(300) NOT NULL DEFAULT '',
    dataset varchar(40) NOT NULL,
    definition jsonb NOT NULL,
    is_shared boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL,
    updated_at timestamptz NOT NULL,
    CONSTRAINT uq_saved_report_name UNIQUE (organization_id, owner_id, name)
);

CREATE TABLE "backup_records" (
    id uuid PRIMARY KEY,
    organization_id uuid NOT NULL REFERENCES organizations (id),
    kind varchar(10) NOT NULL,
    performed_by_id uuid NULL REFERENCES users (id),
    filename varchar(200) NOT NULL DEFAULT '',
    size_bytes bigint NOT NULL DEFAULT 0,
    row_counts jsonb NOT NULL,
    checksum varchar(64) NOT NULL DEFAULT '',
    ip_address inet NULL,
    created_at timestamptz NOT NULL
);

-- Aislamiento: el mismo bloque para las cuatro tablas
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON appointments
    USING (organization_id = app_current_tenant())
    WITH CHECK (organization_id = app_current_tenant());

COMMIT;"""
dd = (H('titulo5', '2.1.2.1 Diseño Conceptual', 708)
      + ''.join(P(t) for t in conceptual)
      + H('titulo5', '2.1.2.2 Diseño lógico (Mapeo)', 708)
      + P(logico_intro)
      + P('**appointments** — la ficha (US-17, US-20)') + cols(0, t_app) + EMPTY()
      + P('**assistant_catalog_fragments** — el corpus del asistente (US-31, US-34)') + cols(0, t_frag) + EMPTY()
      + P('**saved_reports** — reportes configurables (característica 5)') + cols(0, t_rep) + EMPTY()
      + P('**backup_records** — copias de seguridad (característica 6)') + cols(0, t_bak) + EMPTY()
      + P('**organizations** — se agrega cancellation_notice_hours, entero no negativo, 24 por defecto.'))
rep(2138, dd, '2.1.2.1 Diseño Conceptual')
rep(2139, H('titulo5', '2.1.2.3 Diseño Físico (Script)', 708)
     + P('El script reúne lo que crean las migraciones del sprint: appointments 0001 y 0002, assistant 0001 a 0003, reporting 0001 y 0002, backups 0001 y 0002, y tenancy 0004. Las claves compuestas y las políticas se muestran una vez; en las migraciones se repiten para cada tabla.')
     + EMPTY() + ''.join(CODE(l) for l in sql.split('\n')), '2.1.2.3')

# 2.1.3 / 2.1.4 lógica de negocio y procesos (US-31)
after(2140, P('Los diagramas están en el modelo PlataformaMedica.eapx, en el paquete CAP. 4 > Sprint 2 - Arquitectura > 2.1.3 Logica de negocio (US-31), y se exportan a docs/diagramas/png/Sprin2/.')
      + P('**Se documenta US-31** porque es la historia que la materia pide poder explicar: el subsistema de inteligencia artificial, y porque fue la primera del sprint en quedar integrada. Al 02/10/26 también están integradas US-17, US-20 y US-34; el mismo juego de diagramas para el flujo de reserva y pago se hace cuando exista US-18. Cada elemento lleva el nombre exacto del archivo, de la función o de la tabla que representa, y cada mensaje es una llamada que existe en backend/assistant/. Eso es lo que permite abrir el repositorio en la defensa y señalar la línea.')
      + P('**Dos apartamientos del formato del ejemplo, y por qué.** Primero: los mensajes del diagrama de comunicación llevan flecha. Por un mismo enlace viajan la pregunta y la respuesta, y sin la punta los dos mensajes se leen igual. Segundo: el diagrama de clases de análisis lleva actores. El Paciente inicia la consulta y el Administrador de Organización dispara la indexación; sin ellos las dos fronteras quedan sin origen y el diagrama no dice quién empieza.'))
comm = ['El diagrama de comunicación muestra quiénes intervienen en el caso de uso y en qué orden se hablan, sin el eje del tiempo. Los objetos se agrupan por su papel: el actor, las fronteras —la pantalla del móvil y el proveedor externo de modelo de lenguaje—, los controladores, que son los módulos de la aplicación assistant, y las entidades, que son las dos tablas que se consultan.',
        'La numeración divide la conversación en cuatro grupos, que son los cuatro desenlaces posibles de una consulta. El **grupo 1** es el flujo principal: el paciente escribe lo que le pasa, el sistema verifica su permiso, descarta que sea una urgencia, vectoriza la consulta, recupera del catálogo de su organización los fragmentos más parecidos, agrupa los que corresponden a una misma especialidad y redacta la respuesta usando únicamente eso. El **grupo 2** es la derivación a emergencia: la barrera corta el flujo antes de recuperar nada, de modo que no se llega a sugerir ninguna especialidad. El **grupo 3** es la consulta que no se parece a nada del catálogo, donde el asistente responde que no sabe sin llamar al modelo de lenguaje. Y el **grupo 4** es la caída del proveedor de vectores, que termina en un 503 y no en una respuesta inventada.',
        '**Cada mensaje se dibuja como su propia flecha**, y la punta indica hacia dónde va. Donde dos objetos se hablan varias veces —la pantalla y la vista intercambian cinco mensajes, uno por cada desenlace— las flechas se abren en abanico en lugar de superponerse, de modo que se puede seguir una por una. Los colores son los mismos de los otros dos apartados: azul la frontera, verde el controlador, ámbar la entidad.',
        '**El mensaje 1.8 es donde vive el multi-inquilino dentro de la inteligencia artificial.** El filtro por organización va en el WHERE, antes del ORDER BY por similitud. Filtrarlo después devuelve el mismo resultado, y es una fuga: el índice de todos los inquilinos ya se recorrió.']
after(2141, ''.join(P(t) for t in comm))
clases = ['El diagrama de clases de análisis muestra la estructura de la historia: las mismas piezas del diagrama anterior, pero con sus atributos y sus operaciones, y unidas por asociaciones con su rol y su cardinalidad.',
          'Las fronteras llevan el nombre del archivo de la pantalla y el endpoint que consumen. Los controladores llevan el nombre del **módulo** y no de una clase, porque en Python la unidad de código es el módulo: retrieval.py son dos funciones sueltas y no una clase con dos métodos; cada operación es el nombre y la firma reales de esa función. Las entidades llevan el nombre exacto de la tabla y sus columnas con el tipo de la base, incluida la columna embedding de tipo vector(768), que es la que hace posible la búsqueda por similitud.',
          '**El diagrama tiene dos mitades que no corren al mismo tiempo.** De embed_catalog.py hacia abajo está la indexación, que no ocurre durante la consulta: corre cuando cambia el catálogo y deja los fragmentos vectorizados en la tabla. De assistant_screen.dart hacia la derecha está la consulta, que es la que ocurre cuando el paciente pregunta. Un asistente de este tipo no aprende de las preguntas: lo que sabe se escribe en la indexación.',
          'La entidad specialties aparece aunque no pertenezca al componente: **su campo description es el corpus**. Es lo que hace explícito que el sistema sólo puede responder sobre lo que la organización cargó en su propio catálogo, y que la calidad de la respuesta depende de cómo esté escrito ese texto.']
after(2144, ''.join(P(t) for t in clases))
secu = ['El diagrama de secuencia es el mismo caso de uso con el eje del tiempo. Se lee de arriba hacia abajo, y cada línea de vida está clasificada por la clase correspondiente del apartado anterior, de modo que los dos diagramas nombran exactamente lo mismo.',
        '**Las líneas de vida están ordenadas por rol y no por orden de aparición**: primero el actor, después la frontera —la pantalla del paciente—, después los seis controladores, que son los módulos de la aplicación assistant, después las dos entidades, que son las tablas, y al final el sistema externo. Cada rol tiene su color, el mismo que en los dos apartados anteriores: azul la frontera, verde el controlador, ámbar la entidad. Es lo que permite ver, sin leer un solo nombre, que el trabajo ocurre en el centro y que a la derecha sólo hay datos.',
        'La numeración se hereda del diagrama de comunicación, para poder seguir un mismo mensaje en los dos apartados. Los retornos, que el diagrama de comunicación no representa, se numeran como sub-nivel del mensaje que los provoca —el retorno de 1.5 es 1.5.1—, de manera que agregar retornos no corre la numeración original.',
        '**El fragmento combinado alt contiene los cuatro desenlaces**, en el mismo orden que los cuatro grupos del diagrama de comunicación. Lo que se ve al comparar las cuatro bandas es que los tres desenlaces que no son el flujo principal son más cortos, y esa brevedad es deliberada: en la urgencia no se recupera ni se redacta nada, en la consulta sin respaldo no se llama al modelo de lenguaje, y en la caída del proveedor se responde 503. Las tres son formas distintas de la misma decisión de diseño: **el asistente prefiere no contestar antes que contestar sin respaldo.**',
        'Los mensajes que van contra la base de datos llevan el SQL, y los que van contra el proveedor externo llevan el modelo que se invoca —gemini-embedding-001 para vectorizar y gemini-3.5-flash-lite para redactar—, porque son los dos puntos donde el sistema sale de su propio proceso.',
        '**Actualización de US-34 (30/09/26).** La derivación a emergencia pasó a tener dos capas: primero las reglas de triage.py y, si no disparan, el propio modelo puede marcar la consulta como urgencia, y se deriva con el mismo mensaje. La segunda capa sólo escala: si la regla ya disparó, el modelo no se consulta. El diagrama de secuencia muestra la primera capa; la segunda se agrega al diagrama cuando se regenere.']
after(2145, ''.join(P(t) for t in secu))
pend_diag = P('**Pendiente.** Los diagramas de estado, de tiempo y de navegación del Sprint 2 todavía no se elaboraron. El candidato natural para el de estados es la ficha, cuyos siete estados ya existen en appointments.')
after(2146, pend_diag)
after(2147, P('**Pendiente.** Se elabora junto con el diagrama de estados.'))
after(2148, P('**Pendiente.** Se elabora junto con el diagrama de estados.'))

# 2.2.1 Componentes y artefactos
comp_rows = [
    ['US-17 — Reserva de ficha', 'appointments/models.py (Appointment), booking.py, serializers.py, permissions.py, mixins.py, urls.py, migraciones 0001_initial y 0002_rls_policies; frontend/src/api/fichas.ts, ModalReservarFicha.tsx, MisFichas.tsx, Disponibilidad.tsx', 'Reserva sobre la disponibilidad consolidada de US-15. GET y POST /api/appointments/appointments/. La concurrencia la resuelve el índice único parcial del turno: de dos reservas simultáneas una gana y la otra recibe 409.'],
    ['US-20 — Cancelación y reprogramación', 'appointments/changes.py; tenancy/migrations/0004 (cancellation_notice_hours); frontend/src/componentes/ModalReprogramarFicha.tsx', 'POST /api/appointments/appointments/{id}/cancel/ y /reschedule/. La reprogramación libera el turno viejo y toma el nuevo en una sola transacción.'],
    ['US-31 — Sugerencia de especialidad', 'assistant/models.py (CatalogFragment), embeddings.py, indexing.py, retrieval.py, generation.py, views.py, serializers.py, permissions.py, medical_reference.py, management/commands/embed_catalog.py, migraciones 0001 a 0003; mobile/lib/features/assistant/assistant_screen.dart y assistant_api.dart', 'POST /api/assistant/suggest/ con el permiso assistant.suggest.use. Recupera por similitud coseno dentro de la organización y responde sólo con los fragmentos recuperados, que viajan con la respuesta.'],
    ['US-34 — Derivación a emergencia', 'assistant/triage.py, assistant/generation.py, audit/actions.py (assistant.emergency)', 'Dos capas: reglas revisadas contra MedlinePlus y la OMS y, si no disparan, la marca de urgencia del modelo. Cada derivación deja asiento en la bitácora sin el texto del paciente.'],
    ['Característica 5 — Reportes', 'reporting/datasets.py, query.py, exporters.py, delivery.py, models.py (SavedReport); mobile/lib/features/reporting/reports_screen.dart', 'GET /api/reporting/datasets/, POST /api/reporting/run/ y /api/reporting/reports/. Exporta a CSV, XLSX, HTML y PDF.'],
    ['Característica 6 — Copias de seguridad', 'backups/services.py, manifest.py, models.py (BackupRecord); comandos backup_organization, restore_organization y dump_database', 'POST /api/backups/create/, /inspect/ y /restore/, y GET /api/backups/records/.'],
    ['US-05, US-09, US-10, US-18, US-19, US-21, US-22, US-24, US-25 y US-32', '—', 'Sin artefactos en la rama principal al 02/10/26.'],
]
after(2150, P('Durante el Sprint 2 se incorporaron a la rama principal las apps appointments y assistant, las pantallas web de reserva, cancelación y reprogramación, la pantalla del asistente en el móvil y las características generales 5 y 6. La tabla identifica los archivos presentes en el repositorio y su relación con cada historia; la existencia de un archivo no reemplaza la evidencia funcional del reporte de pruebas.')
      + table(T(1484), [(0, None)], comp_rows, 1) + EMPTY())

# 2.3.1 Plan de pruebas
plans = [
    ('CU18 — Reserva de Ficha Médica', ['CU18 — Reserva de Ficha Médica', 'US-17 · Web / móvil', 'El paciente reserva una ficha sobre un espacio de la disponibilidad consolidada; la ficha nace pendiente de pago y el espacio deja de ofrecerse.', 'Organización activa con agendas cargadas, paciente ficticio con sesión iniciada y una segunda organización para probar el aislamiento.', 'Luis Miguel Aguayo Quiroz'],
     [('CP-17-01', 'Reservar un espacio libre de la agenda', 'La ficha se crea en estado pendiente de pago, con su vencimiento.', 'test_reserva_exitosa_queda_pendiente_de_pago'),
      ('CP-17-02', 'Dos pacientes piden el mismo espacio al mismo tiempo', 'Uno obtiene la ficha y el otro recibe 409; no hay ficha duplicada.', 'test_dos_reservas_del_mismo_turno_una_gana_y_la_otra_recibe_409'),
      ('CP-17-03', 'Consultar la disponibilidad después de reservar', 'El espacio reservado ya no se ofrece.', 'test_el_turno_reservado_desaparece_de_la_disponibilidad'),
      ('CP-17-04', 'Reservar un horario que no deriva de la agenda', 'Se rechaza con 400.', 'test_reservar_un_horario_que_no_corresponde_a_la_agenda_da_400'),
      ('CP-17-05', 'Reservar sobre un profesional de otra organización', 'Se rechaza y no se crea la ficha.', 'test_un_paciente_no_reserva_sobre_un_profesional_de_otra_organizacion'),
      ('CP-17-06', 'Listar fichas desde otra organización', 'No se ven fichas ajenas.', 'test_un_paciente_no_ve_las_fichas_de_otra_organizacion')]),
    ('CU21 — Cancelación / Reprogramación de Ficha', ['CU21 — Cancelación / Reprogramación de Ficha', 'US-20 · Web / móvil', 'El paciente cancela o reprograma su ficha dentro de la ventana de anticipación de su organización.', 'Ficha confirmada o pendiente de pago, parámetro cancellation_notice_hours de la organización (24 h por defecto) y un segundo espacio libre.', 'Luis Miguel Aguayo Quiroz'],
     [('CP-20-01', 'Cancelar con más de 24 horas de anticipación', 'La ficha queda cancelada y con reembolso elegible.', 'test_cancelar_con_mas_de_24_horas_marca_reembolso_elegible'),
      ('CP-20-02', 'Cancelar con menos de 24 horas', 'La ficha queda cancelada sin reembolso.', 'test_cancelar_con_menos_de_24_horas_no_da_reembolso'),
      ('CP-20-03', 'Cancelar y consultar la disponibilidad', 'El espacio vuelve a ofrecerse.', 'test_cancelar_libera_el_turno_en_la_disponibilidad'),
      ('CP-20-04', 'Cancelar una ficha ya cancelada', 'Se rechaza.', 'test_no_se_puede_cancelar_dos_veces'),
      ('CP-20-05', 'Reprogramar a un espacio libre', 'El turno viejo se libera y el nuevo queda ocupado.', 'test_reprogramar_libera_el_turno_viejo_y_ocupa_el_nuevo'),
      ('CP-20-06', 'Reprogramar a un espacio ya tomado', 'Se rechaza y la ficha original no se modifica.', 'test_reprogramar_a_un_turno_ya_tomado_no_toca_la_ficha_original'),
      ('CP-20-07', 'Cancelar una ficha de otra organización', 'Se rechaza sin modificarla.', 'test_no_se_puede_cancelar_una_ficha_de_otra_organizacion')]),
    ('CU32 — Orientación Médica mediante Chatbot', ['CU32 — Orientación Médica mediante Chatbot', 'US-31 · Móvil', 'El paciente describe sus síntomas y recibe una sugerencia de especialidad construida sólo sobre los fragmentos del catálogo de su organización.', 'Dos organizaciones con catálogos distintos, indexados con embed_catalog; paciente con el permiso assistant.suggest.use.', 'Karen Paola Ortega Mancilla'],
     [('CP-31-01', 'Describir un síntoma', 'Se sugiere la especialidad que corresponde.', 'test_describir_un_sintoma_devuelve_la_especialidad_que_corresponde'),
      ('CP-31-02', 'Revisar el respaldo de la respuesta', 'La respuesta trae los fragmentos que la sustentan.', 'test_la_respuesta_trae_los_fragmentos_que_la_respaldan'),
      ('CP-31-03', 'Consultar algo que no está en el catálogo', 'No se inventa una especialidad.', 'test_lo_que_no_esta_en_el_catalogo_no_inventa_una_especialidad'),
      ('CP-31-04', 'Hacer la misma pregunta en dos organizaciones', 'Cada una recibe su propio catálogo.', 'test_la_misma_pregunta_en_dos_organizaciones_devuelve_catalogos_distintos'),
      ('CP-31-05', 'Buscar fragmentos de otra organización', 'No se recuperan.', 'test_los_fragmentos_de_una_organizacion_no_se_ven_desde_la_otra'),
      ('CP-31-06', 'Entrar sin permiso o sin autenticar', 'Se rechaza.', 'test_sin_el_permiso_del_asistente_no_se_entra; test_sin_autenticar_no_se_entra'),
      ('CP-31-07', 'Reindexar el catálogo', 'Los fragmentos se reemplazan sin duplicarse y una especialidad dada de baja sale del índice.', 'test_reindexar_reemplaza_los_fragmentos_en_vez_de_duplicarlos; test_una_especialidad_dada_de_baja_no_queda_en_el_indice'),
      ('CP-31-08', 'Revisar un fragmento recuperado', 'Dice de qué especialidad salió.', 'test_cada_fragmento_dice_de_que_especialidad_salio'),
      ('CP-31-09', 'Ampliar el corpus con la referencia médica', 'Sólo se agrega a especialidades que el centro tiene, detrás de su propio texto, y cada oración cita su fuente.', 'test_nunca_agrega_una_especialidad_que_el_centro_no_tiene; test_la_referencia_va_detras_del_texto_propio_y_con_el_nombre_del_centro; test_toda_oracion_cita_al_menos_una_fuente_verificable')]),
    ('CU35 — Derivación a Atención de Emergencia', ['CU35 — Derivación a Atención de Emergencia', 'US-34 · Móvil', 'Ante una descripción compatible con una urgencia, el asistente corta el flujo de reserva y deriva a atención de emergencia.', 'Catálogo indexado; consultas de prueba con y sin señales de urgencia; proveedor de modelo simulado para la segunda capa.', 'Karen Paola Ortega Mancilla'],
     [('CP-34-01', 'Describir una urgencia', 'Se corta el flujo y no se sugiere reservar ficha.', 'test_una_urgencia_corta_el_flujo_y_no_sugiere_reservar_ficha; test_las_urgencias_de_la_revision_derivan'),
      ('CP-34-02', 'Decir la misma urgencia de formas distintas', 'Todas las formas derivan.', 'test_las_formas_de_decir_dolor_de_pecho_derivan_todas; test_las_senales_nuevas_derivan'),
      ('CP-34-03', 'Hacer una consulta normal', 'No deriva y queda registrada como consulta.', 'test_una_consulta_normal_no_deriva; test_una_consulta_normal_queda_como_consulta_y_no_como_derivacion'),
      ('CP-34-04', 'Combinar varias señales', 'La derivación indica qué partes dispararon.', 'test_una_combinada_dice_que_partes_dispararon'),
      ('CP-34-05', 'Disparar una regla', 'El modelo de lenguaje no se consulta.', 'test_si_las_reglas_disparan_el_modelo_ni_se_consulta'),
      ('CP-34-06', 'Las reglas no disparan pero el modelo marca urgencia', 'Se deriva, y la derivación queda distinguida como del modelo.', 'test_el_prompt_pide_la_marca_ante_una_urgencia; test_si_el_modelo_levanta_la_marca_se_deriva; test_la_marca_manda_aunque_venga_acompanada; test_la_derivacion_del_modelo_queda_distinguida'),
      ('CP-34-07', 'Consultar sin fragmentos recuperados', 'Igual se consulta la marca y el texto del modelo se descarta.', 'test_sin_fragmentos_igual_se_consulta_la_marca; test_sin_fragmentos_el_texto_del_modelo_se_descarta'),
      ('CP-34-08', 'Revisar la bitácora', 'Cada derivación deja asiento sin el texto de la consulta.', 'test_cada_derivacion_deja_asiento_sin_el_texto_de_la_consulta')]),
    ('CU33 — Consulta de Información mediante Chatbot', ['CU33 — Consulta de Información mediante Chatbot', 'US-32 · Móvil (sobre la pantalla de US-31)', 'El paciente consulta horarios de sucursal, costos y preparación previa a estudios por el mismo punto de entrada del asistente.', 'Catálogo con al menos tres sucursales con horario y servicios con costo y preparación, indexado como fragmentos branch y service.', 'Luis Mateo Hurtado Castro'],
     [('CP-32-01', 'Preguntar el horario de una sucursal', 'Responde con el horario de esa sucursal y el fragmento que lo respalda.', None),
      ('CP-32-02', 'Preguntar por una sucursal entre varias', 'Se recupera la sucursal pedida y no las otras.', None),
      ('CP-32-03', 'Preguntar el costo o la preparación de un estudio', 'Responde con el servicio correspondiente.', None),
      ('CP-32-04', 'Preguntar algo que no está cargado', 'Responde que no sabe; no inventa.', None),
      ('CP-32-05', 'Preguntar desde otra organización', 'No se recuperan sucursales ni servicios ajenos.', None),
      ('CP-32-06', 'Mencionar una urgencia en una consulta administrativa', 'Igual deriva a emergencia (US-34).', None)]),
]
crit = T(1491)
plan_xml = (P('El plan define entradas, acciones y salidas esperadas para validar el comportamiento funcional mediante técnicas de caja negra. Cubre las historias del Sprint 2 que ya tienen código y la de US-32, que se implementa a continuación. Las demás historias del sprint redactan su plan antes de implementarse.')
            + table(T(1489), [(0, ['**Convención de identificadores.** Se continúa la convención del Sprint 1: CP-<historia>-<número>. El número intermedio corresponde a la historia de usuario, no al caso de uso.'])], [], 0)
            + P(' ')
            + table(crit, [(0, None), (1, ['Entorno', 'Backend Django REST Framework, clientes React y Flutter, y PostgreSQL con pgvector, con usuario de aplicación sin privilegios y aislamiento RLS. El asistente se prueba con el proveedor local de vectores, sin llamadas a Gemini.']), (2, None), (3, None), (4, None), (5, None), (6, None)], [], 1)
            + P(' ') + P('Cobertura por caso de uso')
            + table(T(1494), [(0, None)], [[p[1][0].replace(' — ', ' · '), p[1][1].split(' ')[0], str(len(p[2]))] for p in plans], 1)
            + P(' '))
for title, info, steps in plans:
    plan_xml += (P(title)
                 + table(T(1499), [(0, None)] + [(i + 1, [None, info[i]]) for i in range(5)], [], 1)
                 + P(' ')
                 + P('Escenarios planificados y resultados esperados. La columna de estado se completa únicamente en el reporte de ejecución.')
                 + table(T(1502), [(0, None)], [[s[0], s[1], s[2]] for s in steps], 1)
                 + P(' '))
after(2152, plan_xml)

# 2.3.2 Reporte de prueba
leg = table(T(1598), [(0, None)], [
    ['Cubierto por prueba automatizada', 'Existe una función de prueba en backend/tests que verifica el escenario, y la suite completa terminó en verde en la última ejecución comunicada. Falta adjuntar la evidencia de interfaz del responsable.'],
    ['Pendiente', 'No hay evidencia suficiente, o la historia todavía no está implementada o integrada.'],
], 1)
summary = [
    ['CU18', 'US-17', 'Luis Miguel Aguayo Quiroz', 'Integrada (PR #45). 6 pruebas automatizadas; evidencia de interfaz por completar.'],
    ['CU21', 'US-20', 'Luis Miguel Aguayo Quiroz', 'Integrada (PR #45). 7 pruebas automatizadas; evidencia de interfaz por completar.'],
    ['CU32', 'US-31', 'Karen Paola Ortega Mancilla', 'Integrada (PR #41). 12 pruebas más 11 de la referencia médica; evidencia de interfaz por completar.'],
    ['CU35', 'US-34', 'Karen Paola Ortega Mancilla', 'Integrada (PR #46). 13 pruebas automatizadas; evidencia de interfaz por completar.'],
    ['CU33', 'US-32', 'Luis Mateo Hurtado Castro', 'En implementación.'],
    ['CU6', 'US-05', 'Karen Paola Ortega Mancilla', 'Pendiente de implementación.'],
    ['CU10', 'US-09', 'José Daniel Iporo Chulque', 'Pendiente de implementación.'],
    ['CU11', 'US-10', 'José Daniel Iporo Chulque', 'Pendiente de implementación.'],
    ['CU19', 'US-18', 'Alexander Osinaga Blanco', 'Pendiente de implementación.'],
    ['CU20', 'US-19', 'Alexander Osinaga Blanco', 'Pendiente de implementación.'],
    ['CU22', 'US-21', 'Alexander Osinaga Blanco', 'Pendiente de implementación.'],
    ['CU23', 'US-22', 'José Daniel Iporo Chulque', 'Pendiente de implementación.'],
    ['CU25', 'US-24', 'Luis Mateo Hurtado Castro', 'Pendiente de implementación.'],
    ['CU26', 'US-25', 'Luis Mateo Hurtado Castro', 'Pendiente de implementación.'],
]
files = {'US-17': ('backend/tests/test_us17.py', 6), 'US-20': ('backend/tests/test_us20.py', 7),
         'US-31': ('backend/tests/test_us31.py y backend/tests/test_us31_referencia_medica.py', 23),
         'US-34': ('backend/tests/test_us34.py', 13)}
rep_xml = (leg + P(' ')
           + P('**Evidencia global acreditada:** según el registro de integración de US-34 (commit 3ee2b84, 30/09/26), la suite completa del backend terminó con 396 pruebas aprobadas. Para esta versión del documento la suite no se volvió a ejecutar.')
           + P('**Alcance de los resultados:** la regresión general no acredita por sí sola las interfaces web y móvil. Los estados de esta sección se refieren a la lógica del backend; las capturas de cada pantalla las adjunta su responsable.')
           + P('Resumen de casos de uso')
           + table(T(1603), [(0, None)], summary, 1) + P(' '))
for title, info, steps in plans[:4]:
    us = info[1].split(' ')[0]
    f, n = files[us]
    rep_xml += (P('Prueba de caso de uso ' + title.replace(' — ', ': '))
                + table(T(1608), [(0, None), (1, [None, info[0].split(' — ')[0] + ' · ' + info[1]]), (2, [None, info[2]]), (3, [None, info[3]]), (4, [None, info[4]])], [], 1)
                + P(' ')
                + table(T(1610), [(0, None)], [[str(i + 1), s[1], s[2], 'Cubierto por prueba automatizada'] for i, s in enumerate(steps)], 1)
                + P(' ')
                + P('Resultado de la prueba y evidencias')
                + P(f'**Resultado general:** los {len(steps)} escenarios están cubiertos por pruebas automatizadas del backend, que pasan dentro de la suite completa. Falta la evidencia de interfaz.')
                + P(f'**Archivo de pruebas revisado:** {f}. Se identificaron {n} funciones de prueba. Su existencia no se utiliza como sustituto de la evidencia funcional de la interfaz.')
                + P('Adjuntos')
                + P('Insertar aquí las capturas de la interfaz o las respuestas de la API correspondientes a los pasos ejecutados. Cada imagen debe indicar el paso al que corresponde.')
                + P('Trazabilidad automatizada')
                + table(T(1619), [(0, None)], [[s[0], s[3]] for s in steps], 1)
                + P(' '))
rep_xml += P('**Pendiente:** el reporte de CU33 (US-32) y el de las historias restantes se agregan cuando cada una se integre a la rama principal.')
after(2153, rep_xml)

# 3. Daily Scrum — semana 2 corregida y semanas 3 y 4
def daily(week, rango, dias):
    base = T(2160)
    keep = [(0, None), (1, [f'Semana {week}\n{rango}']), (2, [None, None] + dias)]
    keep += [(i, None) for i in range(3, 18)]
    return table(base, keep, [], 3)
d2 = daily(2, '19 septiembre – 25 septiembre', ['Sáb\n19 – sep.', 'Dom\n20 – sep.', 'Lun\n21 – sep.', 'Mar\n22 – sep.', 'Mie\n23 – sep.', 'Jue\n24 – sep.', 'Vie\n25 – sep.'])
d3 = daily(3, '26 septiembre – 02 octubre', ['Sáb\n26 – sep.', 'Dom\n27 – sep.', 'Lun\n28 – sep.', 'Mar\n29 – sep.', 'Mie\n30 – sep.', 'Jue\n1 – oct.', 'Vie\n2 – oct.'])
d4 = daily(4, '03 octubre – 05 octubre', ['Sáb\n3 – oct.', 'Dom\n4 – oct.', 'Lun\n5 – oct.', '', '', '', ''])
rep(2160, d2 + EMPTY() + EMPTY() + d3 + EMPTY() + EMPTY() + d4)
after(2161, P('**Pendiente.** Las semanas 2 a 4 se completan con lo que informe cada integrante; el sprint cierra el 05/10/26. La fila del sexto integrante se quitó: retiró la materia antes de empezar este sprint.'))

# 4. Sprint Review — estructura del Sprint 2
rv = T(2164)
review_rows = [
    ['US-17 | Reserva de ficha médica', ''], ['US-18 | Pago de ficha en línea', ''], ['US-19 | Comprobante digital con QR', ''],
    ['US-20 | Cancelación y reprogramación de ficha', ''], ['US-21 | Confirmación de asistencia', ''], ['US-22 | Check-in en recepción', ''],
    ['US-24 | Registro de la atención médica', ''], ['US-25 | Historial clínico longitudinal', ''],
    ['US-31 | Sugerencia de especialidad por síntomas', ''], ['US-32 | Consultas administrativas al asistente', ''],
    ['US-34 | Derivación a atención de emergencia', ''], ['US-05, US-09, US-10 | Arrastre del Sprint 1: perfil, búsqueda y ABM de pacientes', ''],
    ['Características 5 y 6 | Reportes personalizables y copias de seguridad', ''],
]
rep(2164, table(rv, [(0, ['REVISION DE SPRINT 2']),
                     (1, ['OBJETIVOS DEL SPRINT\nCerrar el circuito completo de la ficha médica —reservarla, pagarla, presentarse y ser atendido— y adelantar el subsistema de inteligencia artificial para que el asistente de orientación funcione sobre el catálogo real de cada organización.'])]
                + [(i, None) for i in range(2, 12)], review_rows, 12))
rep(2165, P('**Pendiente.** La retroalimentación de cada función se completa en la revisión del 06–08/10/26.'))

# 5. Retrospectiva — estructura del Sprint 2
rt = T(2170)
rep(2170, table(rt, [(0, ['RETROSPECTIVA DEL SPRINT 2']), (1, [None, 'Pendiente (06–08/10/26)']), (2, None),
                     (3, ['OBJETIVO:\nIdentificar áreas de mejora en el proceso de desarrollo del Sprint 2.']),
                     (4, None), (5, ['TEMAS A TRATAR\nPendiente']), (6, None), (7, None),
                     (8, ['', '', '']), (9, ['', '', '']), (10, ['', '', ''])], [], 8))
rep(2171, P('**Pendiente.** Se completa en la retrospectiva, al cierre del sprint.'))

# 7. Gráfica de esfuerzo
after(2175, P('**Pendiente.** La gráfica y los datos de esfuerzo se completan al cierre del sprint (05/10/26), con las horas reales que reporte cada integrante.'))

# =====================================================================
# Aplicar de abajo hacia arriba
# =====================================================================
edits = []
for k, v in ops.items():
    if isinstance(k, tuple):
        n = k[1]; t, a, b = E[n]
        edits.append((b, b, v))
    else:
        mode, xml = v; t, a, b = E[k]
        edits.append((a, b, xml))
edits.sort(key=lambda e: (e[0], e[1]), reverse=True)
out = x
last = None
for a, b, xml in edits:
    if last is not None:
        assert b <= last, 'solapamiento'
    out = out[:a] + xml + out[b:]
    last = a
open('un/word/document.xml', 'w', encoding='utf8', newline='').write(out)
print('ediciones:', len(edits), 'tamaño', len(x), '->', len(out))
