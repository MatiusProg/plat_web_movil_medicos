-- =========================================================================
--  Modelo de datos — Sprint 0
--  Historias cubiertas: US-43, US-44, US-45, US-01, US-02, US-04
--
--  ESTE ARCHIVO ES REFERENCIA DE DISEÑO, NO SE EJECUTA EN PRODUCCIÓN.
--  La fuente de verdad son las migraciones de Django. Este DDL existe para:
--    1. acordar el modelo entre los seis antes de escribir código,
--    2. poder validarlo contra un PostgreSQL 16 real,
--    3. copiar las políticas RLS a una migración RunSQL.
--
--  Se ejecuta COMO app_user, no como postgres: así las tablas quedan con el
--  dueño correcto y las políticas RLS se ejercitan de verdad (postgres es
--  superusuario y las omite aunque haya FORCE).
--
--    docker compose exec -T db psql -U app_user -d plataforma \
--        -v ON_ERROR_STOP=1 -f - < docs/modelo-datos/sprint-0.sql
-- =========================================================================

-- =========================================================================
--  0. Funciones de contexto de inquilino
--     El middleware ejecuta, dentro de la transacción de cada petición:
--        SET LOCAL app.tenant_id         = '<uuid de la organización>';
--        SET LOCAL app.is_platform_admin = 'on';   -- sólo para superadmin
--     SET LOCAL, nunca SET. Ver README, sección de aislamiento, punto 3.
-- =========================================================================

CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS uuid
    LANGUAGE sql STABLE
    AS $$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$;

CREATE OR REPLACE FUNCTION app_is_platform_admin() RETURNS boolean
    LANGUAGE sql STABLE
    AS $$ SELECT coalesce(current_setting('app.is_platform_admin', true) = 'on', false) $$;


-- =========================================================================
--  1. NIVEL PLATAFORMA  —  tablas sin organization_id
--     Las administra el Superadministrador. No llevan discriminador de
--     inquilino porque son, precisamente, el registro de los inquilinos.
-- =========================================================================

-- ---------- US-44 (Daniel) -----------------------------------------------
CREATE TABLE subscription_plans (
    id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code                    varchar(30)   NOT NULL,
    name                    varchar(80)   NOT NULL,
    description             text          NOT NULL DEFAULT '',
    monthly_price           numeric(10,2) NOT NULL DEFAULT 0,
    currency                char(3)       NOT NULL DEFAULT 'BOB',

    -- Límites cuantitativos. NULL = ilimitado.
    -- Se comparan contra usage_metrics para el panel de US-45.
    max_branches            integer,
    max_users               integer,
    max_practitioners       integer,
    max_appointments_month  integer,
    max_ai_queries_month    integer,
    storage_mb              integer,

    -- Funcionalidades on/off. Clave = código de funcionalidad, valor boolean.
    -- Ej: {"ai_chatbot": true, "noshow_prediction": false, "report_export": true}
    features                jsonb         NOT NULL DEFAULT '{}'::jsonb,

    is_active               boolean       NOT NULL DEFAULT true,
    created_at              timestamptz   NOT NULL DEFAULT now(),
    updated_at              timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT uq_plan_code     UNIQUE (code),
    CONSTRAINT ck_plan_price    CHECK (monthly_price >= 0),
    CONSTRAINT ck_plan_features CHECK (jsonb_typeof(features) = 'object'),
    CONSTRAINT ck_plan_limits   CHECK (
        coalesce(max_branches, 0)           >= 0 AND
        coalesce(max_users, 0)              >= 0 AND
        coalesce(max_practitioners, 0)      >= 0 AND
        coalesce(max_appointments_month, 0) >= 0 AND
        coalesce(max_ai_queries_month, 0)   >= 0 AND
        coalesce(storage_mb, 0)             >= 0
    )
);

-- ---------- US-43 (Luis Mateo) -------------------------------------------
CREATE TABLE organizations (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identificador corto y estable. Es lo que el usuario escribe en el
    -- formulario de login para resolver el inquilino ANTES de autenticar.
    slug              varchar(40)  NOT NULL,

    name              varchar(120) NOT NULL,   -- nombre comercial
    legal_name        varchar(160) NOT NULL,   -- razón social
    tax_id            varchar(20)  NOT NULL,   -- NIT

    contact_email     varchar(254) NOT NULL,
    contact_phone     varchar(30)  NOT NULL DEFAULT '',
    address           varchar(200) NOT NULL DEFAULT '',
    city              varchar(80)  NOT NULL DEFAULT '',
    country           char(2)      NOT NULL DEFAULT 'BO',

    -- Personalización visual por inquilino (marca blanca).
    logo_url          varchar(300) NOT NULL DEFAULT '',
    primary_color     char(7)      NOT NULL DEFAULT '#0F766E',
    secondary_color   char(7)      NOT NULL DEFAULT '#134E4A',

    -- Necesaria desde el Sprint 1: las agendas, los recordatorios y la ventana
    -- de cancelación se calculan en la hora local de la organización, no del
    -- servidor. Agregarla después obliga a revisar cada consulta de agenda.
    timezone          varchar(40)  NOT NULL DEFAULT 'America/La_Paz',

    status            varchar(12)  NOT NULL DEFAULT 'active',
    onboarded_at      date         NOT NULL DEFAULT CURRENT_DATE,  -- fecha de alta
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_organization_slug   UNIQUE (slug),
    CONSTRAINT uq_organization_tax_id UNIQUE (tax_id),
    CONSTRAINT ck_organization_slug   CHECK (slug ~ '^[a-z0-9]([a-z0-9-]{1,38}[a-z0-9])$'),
    CONSTRAINT ck_organization_status CHECK (status IN ('active', 'suspended', 'inactive')),
    CONSTRAINT ck_organization_colors CHECK (
        primary_color   ~ '^#[0-9A-Fa-f]{6}$' AND
        secondary_color ~ '^#[0-9A-Fa-f]{6}$'
    )
);


-- =========================================================================
--  2. NIVEL ORGANIZACIÓN  —  tablas con organization_id + RLS
-- =========================================================================

-- ---------- US-11, Sprint 1. Mínima aquí porque users.branch_id la exige --
CREATE TABLE branches (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    name              varchar(120) NOT NULL,
    address           varchar(200) NOT NULL DEFAULT '',
    phone             varchar(30)  NOT NULL DEFAULT '',
    is_active         boolean      NOT NULL DEFAULT true,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT uq_branch_name  UNIQUE (organization_id, name),
    -- Necesaria para la clave foránea compuesta desde users (más abajo).
    CONSTRAINT uq_branch_id_org UNIQUE (id, organization_id)
);
CREATE INDEX ix_branches_org ON branches (organization_id);

-- ---------- US-01 (Alexander) y US-02 (Karen) ----------------------------
CREATE TABLE users (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),

    -- NULL exactamente para el Superadministrador de Plataforma.
    -- Cualquier otro usuario vive dentro de una organización.
    organization_id   uuid REFERENCES organizations(id) ON DELETE RESTRICT,
    branch_id         uuid,

    email             varchar(254) NOT NULL,
    password          varchar(128) NOT NULL,   -- hash de Django (Argon2/PBKDF2)

    first_name        varchar(80)  NOT NULL,
    last_name         varchar(80)  NOT NULL,
    document_type     varchar(10)  NOT NULL DEFAULT 'CI',
    document_number   varchar(20)  NOT NULL,
    phone             varchar(30)  NOT NULL DEFAULT '',
    birth_date        date,

    is_platform_admin boolean      NOT NULL DEFAULT false,
    is_active         boolean      NOT NULL DEFAULT true,

    -- RNF-07: bloqueo temporal tras 5 intentos fallidos.
    failed_login_attempts smallint NOT NULL DEFAULT 0,
    locked_until          timestamptz,
    last_login_at         timestamptz,

    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),

    -- El superadmin no pertenece a ninguna organización, y sólo él.
    CONSTRAINT ck_user_scope CHECK (
        (is_platform_admin     AND organization_id IS NULL) OR
        (NOT is_platform_admin AND organization_id IS NOT NULL)
    ),
    CONSTRAINT ck_user_doc_type CHECK (document_type IN ('CI', 'PAS', 'NIT', 'OTRO')),
    CONSTRAINT ck_user_attempts CHECK (failed_login_attempts >= 0),

    -- Unicidad POR INQUILINO, no global: la misma persona puede ser paciente
    -- en dos centros médicos distintos.
    CONSTRAINT uq_user_email    UNIQUE (organization_id, email),
    CONSTRAINT uq_user_document UNIQUE (organization_id, document_number),

    -- La sucursal asignada debe pertenecer a la misma organización.
    -- MATCH SIMPLE: si branch_id es NULL la restricción no se evalúa, que es
    -- justo lo que necesita el superadmin.
    CONSTRAINT fk_user_branch_same_org
        FOREIGN KEY (branch_id, organization_id)
        REFERENCES branches (id, organization_id) ON DELETE SET NULL
);

-- UNIQUE (organization_id, email) no restringe a los superadmins, porque en
-- una clave compuesta los NULL se consideran distintos entre sí.
CREATE UNIQUE INDEX uq_user_email_platform ON users (email) WHERE organization_id IS NULL;
CREATE INDEX ix_users_org      ON users (organization_id);
CREATE INDEX ix_users_document ON users (organization_id, document_number);

-- ---------- US-44: historial de suscripciones ----------------------------
-- Va después de users porque referencia a quien asignó el plan.
CREATE TABLE subscriptions (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   uuid NOT NULL REFERENCES organizations(id)      ON DELETE RESTRICT,
    plan_id           uuid NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    starts_at         date NOT NULL DEFAULT CURRENT_DATE,
    ends_at           date,                       -- NULL = vigente
    status            varchar(12)  NOT NULL DEFAULT 'active',
    change_reason     varchar(200) NOT NULL DEFAULT '',
    assigned_by_id    uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at        timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT ck_subscription_status CHECK (status IN ('active', 'cancelled', 'expired')),
    CONSTRAINT ck_subscription_period CHECK (ends_at IS NULL OR ends_at >= starts_at)
);
-- Una sola suscripción vigente por organización, garantizado por la base.
CREATE UNIQUE INDEX uq_subscription_active ON subscriptions (organization_id) WHERE ends_at IS NULL;
CREATE INDEX ix_subscriptions_plan ON subscriptions (plan_id);

-- ---------- US-04 (Michael): roles y permisos ----------------------------
-- Catálogo global de permisos. Lo define el equipo, no el usuario.
-- Código: <modulo>.<recurso>.<accion>
CREATE TABLE permissions (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code        varchar(80)  NOT NULL,
    module      varchar(40)  NOT NULL,
    description varchar(200) NOT NULL DEFAULT '',
    CONSTRAINT uq_permission_code UNIQUE (code),
    CONSTRAINT ck_permission_code CHECK (code ~ '^[a-z_]+\.[a-z_]+\.[a-z_]+$')
);

CREATE TABLE roles (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    -- NULL = rol plantilla del sistema. Al crear una organización (US-43) se
    -- clonan las plantillas de nivel organización dentro del nuevo inquilino,
    -- para que su administrador pueda ajustarles los permisos (RF-W-02).
    organization_id   uuid REFERENCES organizations(id) ON DELETE CASCADE,
    code              varchar(40)  NOT NULL,
    name              varchar(80)  NOT NULL,
    description       varchar(200) NOT NULL DEFAULT '',
    is_system         boolean      NOT NULL DEFAULT false,
    is_active         boolean      NOT NULL DEFAULT true,
    created_at        timestamptz  NOT NULL DEFAULT now(),
    updated_at        timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT ck_role_system CHECK (NOT is_system OR organization_id IS NULL),
    CONSTRAINT uq_role_id_org UNIQUE (id, organization_id)
);
CREATE UNIQUE INDEX uq_role_code_org    ON roles (organization_id, code) WHERE organization_id IS NOT NULL;
CREATE UNIQUE INDEX uq_role_code_system ON roles (code)                  WHERE organization_id IS NULL;

CREATE TABLE role_permissions (
    role_id         uuid NOT NULL,
    permission_id   uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    -- Denormalizado a propósito: toda tabla protegida por RLS necesita llevar
    -- el discriminador encima. Una política con subconsulta sería correcta,
    -- pero más lenta y mucho más difícil de probar.
    organization_id uuid,
    granted_at      timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (role_id, permission_id),
    CONSTRAINT fk_role_permission_role
        FOREIGN KEY (role_id, organization_id)
        REFERENCES roles (id, organization_id) ON DELETE CASCADE
);
CREATE INDEX ix_role_permissions_org ON role_permissions (organization_id);

CREATE TABLE user_roles (
    user_id         uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         uuid NOT NULL,
    organization_id uuid,
    assigned_by_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    assigned_at     timestamptz NOT NULL DEFAULT now(),

    PRIMARY KEY (user_id, role_id),
    CONSTRAINT fk_user_role_role
        FOREIGN KEY (role_id, organization_id)
        REFERENCES roles (id, organization_id) ON DELETE RESTRICT
);
CREATE INDEX ix_user_roles_org  ON user_roles (organization_id);
CREATE INDEX ix_user_roles_role ON user_roles (role_id);

-- ---------- US-07/US-08, Sprint 1. Mínima aquí: ver decisión D-6 ---------
CREATE TABLE patients (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   uuid NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    -- NULL = paciente a cargo, sin cuenta propia (US-07).
    user_id           uuid REFERENCES users(id)    ON DELETE SET NULL,
    -- Titular que lo administra. NULL = se administra a sí mismo.
    guardian_id       uuid REFERENCES patients(id) ON DELETE SET NULL,

    document_type     varchar(10) NOT NULL DEFAULT 'CI',
    -- NULABLE a propósito: un paciente a cargo recién nacido o menor todavía
    -- no tiene documento (US-07). Un NOT NULL aquí hace imposible registrarlo.
    document_number   varchar(20),
    first_name        varchar(80) NOT NULL,
    last_name         varchar(80) NOT NULL,
    birth_date        date,
    sex               varchar(1),
    phone             varchar(30) NOT NULL DEFAULT '',
    is_active         boolean     NOT NULL DEFAULT true,
    created_at        timestamptz NOT NULL DEFAULT now(),
    updated_at        timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_patient_doc_type CHECK (document_type IN ('CI', 'PAS', 'OTRO')),
    CONSTRAINT ck_patient_sex      CHECK (sex IS NULL OR sex IN ('M', 'F', 'X')),
    CONSTRAINT ck_patient_guardian CHECK (guardian_id IS NULL OR guardian_id <> id),
    -- Un paciente sin documento debe tener un titular que responda por él.
    CONSTRAINT ck_patient_doc_or_guardian CHECK (
        document_number IS NOT NULL OR guardian_id IS NOT NULL
    )
);
-- Unicidad sólo entre los que sí tienen documento: varios menores sin CI
-- dentro de la misma organización no deben chocar entre sí.
CREATE UNIQUE INDEX uq_patient_document ON patients (organization_id, document_type, document_number)
    WHERE document_number IS NOT NULL;
CREATE INDEX ix_patients_org      ON patients (organization_id);
CREATE INDEX ix_patients_guardian ON patients (guardian_id);


-- =========================================================================
--  3. OBSERVABILIDAD Y AUDITORÍA
-- =========================================================================

-- ---------- US-02 (Karen) + RNF-07 ---------------------------------------
-- Se escribe ANTES de saber si el usuario existe, por eso organization_id es
-- opcional y la tabla nunca se filtra por inquilino.
CREATE TABLE login_attempts (
    id                bigserial PRIMARY KEY,
    organization_id   uuid REFERENCES organizations(id) ON DELETE CASCADE,
    user_id           uuid REFERENCES users(id)         ON DELETE SET NULL,
    attempted_email   varchar(254) NOT NULL,
    succeeded         boolean      NOT NULL,
    failure_reason    varchar(40)  NOT NULL DEFAULT '',
    ip_address        inet,
    user_agent        varchar(300) NOT NULL DEFAULT '',
    occurred_at       timestamptz  NOT NULL DEFAULT now(),

    CONSTRAINT ck_login_reason CHECK (
        failure_reason IN ('', 'bad_credentials', 'unknown_user', 'inactive_user',
                           'locked', 'unknown_tenant', 'inactive_tenant')
    )
);
CREATE INDEX ix_login_attempts_email ON login_attempts (attempted_email, occurred_at DESC);

-- ---------- US-06 (Sprint 1) + RNF-18 ------------------------------------
-- La estructura se crea ahora porque asignar un rol (US-04) ya es una acción
-- sensible y debe quedar registrada desde el primer día.
CREATE TABLE audit_log (
    id                bigserial PRIMARY KEY,
    organization_id   uuid REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id           uuid REFERENCES users(id)         ON DELETE SET NULL,
    action            varchar(60) NOT NULL,   -- 'role.assign', 'organization.create'
    entity            varchar(60) NOT NULL,
    entity_id         varchar(64) NOT NULL DEFAULT '',
    detail            jsonb       NOT NULL DEFAULT '{}'::jsonb,
    ip_address        inet,
    occurred_at       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT ck_audit_detail CHECK (jsonb_typeof(detail) = 'object')
);
CREATE INDEX ix_audit_log_org ON audit_log (organization_id, occurred_at DESC);

-- ---------- US-45 (Luis Miguel): métricas de uso -------------------------
-- Instantáneas precalculadas por una tarea programada. El panel del
-- superadministrador NO cuenta en vivo sobre todos los inquilinos.
CREATE TABLE usage_metrics (
    id                bigserial PRIMARY KEY,
    organization_id   uuid NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    metric_code       varchar(40)   NOT NULL,
    granularity       varchar(10)   NOT NULL DEFAULT 'day',
    period_start      date          NOT NULL,
    value             numeric(14,2) NOT NULL DEFAULT 0,
    computed_at       timestamptz   NOT NULL DEFAULT now(),

    CONSTRAINT uq_usage_metric UNIQUE (organization_id, metric_code, granularity, period_start),
    CONSTRAINT ck_usage_granularity CHECK (granularity IN ('day', 'month')),
    -- Sólo se valida el formato, no una lista cerrada de métricas: cada sprint
    -- agrega las suyas (citas en el 2, consultas de IA en el 3, no-show en el
    -- 4) y una lista fija obligaría a un ALTER en la base compartida por cada
    -- métrica nueva. El vocabulario acordado está en sprint-0.md.
    CONSTRAINT ck_usage_metric_code CHECK (metric_code ~ '^[a-z][a-z0-9_]{2,39}$')
);
CREATE INDEX ix_usage_metrics_period ON usage_metrics (period_start DESC, metric_code);

-- ---------- US-45: alertas de aislamiento --------------------------------
CREATE TABLE isolation_alerts (
    id                      bigserial PRIMARY KEY,
    -- Inquilino desde el que se originó el intento.
    source_organization_id  uuid REFERENCES organizations(id) ON DELETE SET NULL,
    -- Inquilino cuyos datos se intentó alcanzar. NULL si no aplica.
    target_organization_id  uuid REFERENCES organizations(id) ON DELETE SET NULL,
    user_id                 uuid REFERENCES users(id)         ON DELETE SET NULL,

    alert_type    varchar(40)  NOT NULL,
    severity      varchar(10)  NOT NULL,
    description   varchar(300) NOT NULL,
    endpoint      varchar(200) NOT NULL DEFAULT '',
    http_method   varchar(10)  NOT NULL DEFAULT '',
    ip_address    inet,
    detail        jsonb        NOT NULL DEFAULT '{}'::jsonb,

    status          varchar(12)  NOT NULL DEFAULT 'pending',
    occurred_at     timestamptz  NOT NULL DEFAULT now(),
    resolved_by_id  uuid REFERENCES users(id) ON DELETE SET NULL,
    resolved_at     timestamptz,
    resolution_note varchar(300) NOT NULL DEFAULT '',

    CONSTRAINT ck_alert_type CHECK (alert_type IN (
        'cross_tenant_access', 'missing_tenant_context', 'jwt_tenant_mismatch',
        'rls_denied', 'plan_limit_exceeded'
    )),
    CONSTRAINT ck_alert_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT ck_alert_status   CHECK (status   IN ('pending', 'reviewing', 'resolved', 'dismissed')),
    CONSTRAINT ck_alert_resolution CHECK (
        (status IN ('resolved', 'dismissed')) = (resolved_at IS NOT NULL)
    )
);
CREATE INDEX ix_isolation_alerts_pending ON isolation_alerts (occurred_at DESC) WHERE status = 'pending';
CREATE INDEX ix_isolation_alerts_source  ON isolation_alerts (source_organization_id, occurred_at DESC);


-- =========================================================================
--  4. VISTA DE APOYO PARA EL PANEL DE US-45
-- =========================================================================
CREATE VIEW v_organization_current_plan AS
SELECT o.id        AS organization_id,
       o.name      AS organization_name,
       o.status    AS organization_status,
       o.onboarded_at,
       s.id        AS subscription_id,
       s.starts_at AS subscription_starts_at,
       p.id        AS plan_id,
       p.code      AS plan_code,
       p.name      AS plan_name,
       p.max_users,
       p.max_branches,
       p.max_appointments_month,
       p.max_ai_queries_month,
       p.storage_mb
FROM organizations o
LEFT JOIN subscriptions s
       ON s.organization_id = o.id AND s.ends_at IS NULL
LEFT JOIN subscription_plans p
       ON p.id = s.plan_id;


-- =========================================================================
--  5. ROW LEVEL SECURITY
--     Criterio 4 de la Definición de Terminado. ENABLE no alcanza: app_user
--     es dueño de las tablas porque corre las migraciones, y el dueño queda
--     exento salvo que se aplique FORCE.
-- =========================================================================

-- ---------- Tablas de inquilino ------------------------------------------
-- Regla: sólo se ven las filas de la organización del contexto.
-- El superadministrador NO tiene excepción aquí, deliberadamente: el alcance
-- del proyecto dice que no accede a información clínica de ninguna
-- organización, y eso se hace cumplir en la base, no sólo en la aplicación.
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['branches', 'roles', 'role_permissions',
                             'user_roles', 'patients']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE  ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY tenant_isolation ON %I'
            ' USING (organization_id = app_current_tenant())'
            ' WITH CHECK (organization_id = app_current_tenant())', t);
    END LOOP;
END $$;

-- roles y role_permissions admiten además las plantillas del sistema
-- (organization_id IS NULL): cualquier inquilino las LEE, para poder clonarlas
-- al dar de alta una organización; sólo el superadministrador las ESCRIBE.
--
-- Sin la segunda política, la migración semilla falla: Django corre las
-- migraciones como app_user, y app_user no puede insertar una fila con
-- organization_id NULL bajo la política tenant_isolation. La migración de
-- datos debe empezar con  SET LOCAL app.is_platform_admin = 'on';
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['roles', 'role_permissions']
    LOOP
        EXECUTE format(
            'CREATE POLICY system_templates_read ON %I'
            ' FOR SELECT USING (organization_id IS NULL)', t);
        EXECUTE format(
            'CREATE POLICY system_templates_write ON %I'
            ' USING (organization_id IS NULL AND app_is_platform_admin())'
            ' WITH CHECK (organization_id IS NULL AND app_is_platform_admin())', t);
    END LOOP;
END $$;

-- audit_log: igual que users, admite filas de nivel plataforma.
-- El superadministrador audita sus propias acciones (alta de organización,
-- asignación de plan) con organization_id NULL, y NO ve la bitácora de
-- ningún inquilino.
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON audit_log
    USING (
        organization_id = app_current_tenant()
        OR (app_is_platform_admin() AND organization_id IS NULL)
    )
    WITH CHECK (
        organization_id = app_current_tenant()
        OR (app_is_platform_admin() AND organization_id IS NULL)
    );

-- ---------- users: caso especial -----------------------------------------
-- El superadministrador debe poder verse a sí mismo para iniciar sesión,
-- pero no a los usuarios de ninguna organización.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE users FORCE  ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON users
    USING (
        organization_id = app_current_tenant()
        OR (app_is_platform_admin() AND organization_id IS NULL)
    )
    WITH CHECK (
        organization_id = app_current_tenant()
        OR (app_is_platform_admin() AND organization_id IS NULL)
    );

-- ---------- Tablas de plataforma -----------------------------------------
-- organizations: el superadmin las administra todas; cada inquilino sólo lee
-- su propia ficha (la necesita para el logo y los colores).
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE  ROW LEVEL SECURITY;
CREATE POLICY platform_admin_all ON organizations
    USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin());
CREATE POLICY tenant_reads_itself ON organizations
    FOR SELECT USING (id = app_current_tenant());

-- subscription_plans: catálogo legible por todos (el inquilino ve qué
-- contrató), escribible sólo por el superadministrador.
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_plans FORCE  ROW LEVEL SECURITY;
CREATE POLICY plans_readable ON subscription_plans FOR SELECT USING (true);
CREATE POLICY plans_writable ON subscription_plans
    USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin());

-- subscriptions y usage_metrics: el superadmin ve todo; el inquilino, lo suyo.
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['subscriptions', 'usage_metrics']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE  ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY platform_admin_all ON %I'
            ' USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin())', t);
        EXECUTE format(
            'CREATE POLICY tenant_reads_itself ON %I'
            ' FOR SELECT USING (organization_id = app_current_tenant())', t);
    END LOOP;
END $$;

-- isolation_alerts y login_attempts: buzón de sólo escritura.
--
-- Cualquier contexto puede INSERTAR, y esto es imprescindible: quien detecta
-- un acceso cruzado es el middleware, que en ese momento está en el contexto
-- de un inquilino cualquiera, no del superadministrador; y un intento de login
-- fallido se registra ANTES de saber siquiera a qué organización pertenece el
-- correo. Con una política que exigiera ser superadmin para escribir, ni US-45
-- ni RNF-07 podrían registrar nada.
--
-- Leer, modificar y resolver, en cambio, es exclusivo del superadministrador.
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY['isolation_alerts', 'login_attempts']
    LOOP
        EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
        EXECUTE format('ALTER TABLE %I FORCE  ROW LEVEL SECURITY', t);
        EXECUTE format(
            'CREATE POLICY platform_admin_manages ON %I'
            ' USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin())', t);
        EXECUTE format(
            'CREATE POLICY anyone_reports ON %I FOR INSERT WITH CHECK (true)', t);
    END LOOP;
END $$;

-- RNF-18: la bitácora es inalterable. Se inserta, nunca se modifica.
REVOKE UPDATE, DELETE ON audit_log      FROM PUBLIC;
REVOKE UPDATE, DELETE ON login_attempts FROM PUBLIC;


-- =========================================================================
--  6. DATOS SEMILLA  —  catálogo del sistema, no datos de prueba
--
--  Las plantillas de rol viven a nivel plataforma (organization_id NULL) y su
--  política exige contexto de superadministrador. Sin la línea de abajo, este
--  bloque falla cuando el archivo lo ejecuta app_user — que es el caso normal,
--  porque app_user es quien corre las migraciones.
--
--  Al pasarlo a una migración de datos de Django, la función debe empezar con
--  el equivalente:  SET LOCAL app.is_platform_admin = 'on';
-- =========================================================================

SET app.is_platform_admin = 'on';

INSERT INTO subscription_plans
    (code, name, description, monthly_price,
     max_branches, max_users, max_practitioners, max_appointments_month,
     max_ai_queries_month, storage_mb, features)
VALUES
    ('basic', 'Básico', 'Una sucursal, agenda y fichas. Sin inteligencia artificial.',
     350.00, 1, 15, 8, 800, 0, 2048,
     '{"ai_chatbot": false, "noshow_prediction": false, "ai_summaries": false,
       "report_export": false, "online_payment": true}'::jsonb),

    ('pro', 'Pro', 'Multi-sucursal, reportes exportables y chatbot de orientación.',
     890.00, 5, 60, 40, 4000, 3000, 10240,
     '{"ai_chatbot": true, "noshow_prediction": false, "ai_summaries": false,
       "report_export": true, "online_payment": true}'::jsonb),

    ('premium', 'Premium', 'Todo lo anterior más predicción de inasistencia y resúmenes por IA.',
     1750.00, NULL, NULL, NULL, NULL, NULL, 51200,
     '{"ai_chatbot": true, "noshow_prediction": true, "ai_summaries": true,
       "report_export": true, "online_payment": true}'::jsonb);

-- Plantillas de rol. organization_id NULL, is_system true.
INSERT INTO roles (organization_id, code, name, description, is_system) VALUES
    (NULL, 'platform_admin', 'Superadministrador de Plataforma',
           'Administra organizaciones y planes. Sin acceso a datos clínicos.', true),
    (NULL, 'org_admin',      'Administrador de Organización',
           'Gestiona usuarios, sucursales, catálogo y reportes de su organización.', true),
    (NULL, 'practitioner',   'Médico',
           'Atiende pacientes y registra la consulta.', true),
    (NULL, 'receptionist',   'Recepcionista',
           'Agenda, cobra fichas y registra el check-in.', true),
    (NULL, 'patient',        'Paciente',
           'Reserva fichas y consulta su propio historial.', true);

INSERT INTO permissions (code, module, description) VALUES
    -- Plataforma (sólo el superadministrador)
    ('platform.organization.create',  'platform', 'Registrar una nueva organización'),
    ('platform.organization.read',    'platform', 'Consultar organizaciones'),
    ('platform.organization.update',  'platform', 'Editar datos de una organización'),
    ('platform.organization.suspend', 'platform', 'Suspender o reactivar una organización'),
    ('platform.plan.create',          'platform', 'Crear un plan de suscripción'),
    ('platform.plan.update',          'platform', 'Editar un plan de suscripción'),
    ('platform.plan.assign',          'platform', 'Asignar un plan a una organización'),
    ('platform.metric.read',          'platform', 'Ver el panel de métricas globales'),
    ('platform.alert.read',           'platform', 'Ver alertas de aislamiento'),
    ('platform.alert.resolve',        'platform', 'Marcar una alerta como resuelta'),
    -- Usuarios y seguridad (organización)
    ('users.user.create',     'users', 'Crear usuarios en la organización'),
    ('users.user.read',       'users', 'Consultar usuarios de la organización'),
    ('users.user.update',     'users', 'Editar usuarios de la organización'),
    ('users.user.deactivate', 'users', 'Dar de baja un usuario'),
    ('users.role.create',     'users', 'Crear roles'),
    ('users.role.read',       'users', 'Consultar roles'),
    ('users.role.update',     'users', 'Editar roles y sus permisos'),
    ('users.role.assign',     'users', 'Asignar roles a usuarios'),
    ('users.audit.read',      'users', 'Consultar la bitácora de auditoría'),
    -- Catálogo (Sprint 1; se declaran ahora para no migrar dos veces)
    ('catalog.branch.create', 'catalog', 'Registrar sucursales'),
    ('catalog.branch.read',   'catalog', 'Consultar sucursales'),
    ('catalog.branch.update', 'catalog', 'Editar sucursales'),
    -- Pacientes
    ('patients.patient.create', 'patients', 'Registrar pacientes'),
    ('patients.patient.read',   'patients', 'Consultar pacientes'),
    ('patients.patient.update', 'patients', 'Editar pacientes');

-- Permisos de las plantillas de rol.
INSERT INTO role_permissions (role_id, permission_id, organization_id)
SELECT r.id, p.id, NULL
FROM roles r
JOIN permissions p ON (
        (r.code = 'platform_admin' AND p.module = 'platform')
     OR (r.code = 'org_admin'      AND p.module IN ('users', 'catalog', 'patients'))
     OR (r.code = 'receptionist'   AND p.code IN ('patients.patient.create',
                                                  'patients.patient.read',
                                                  'patients.patient.update',
                                                  'catalog.branch.read'))
     OR (r.code = 'practitioner'   AND p.code IN ('patients.patient.read',
                                                  'catalog.branch.read'))
)
WHERE r.organization_id IS NULL;

RESET app.is_platform_admin;
