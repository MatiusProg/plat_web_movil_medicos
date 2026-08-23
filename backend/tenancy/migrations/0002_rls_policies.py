"""Row Level Security, funciones de contexto y claves foráneas compuestas.

Todo lo que el ORM de Django no puede expresar y sin lo cual el aislamiento
multi-inquilino no existe. Es el criterio 4 de la Definición de Terminado.

Dos cosas que hay que entender antes de tocar este archivo:

* ``ENABLE`` sola no alcanza. Django corre las migraciones como ``app_user``,
  así que ``app_user`` es dueño de las tablas, y el dueño queda exento de sus
  propias políticas salvo que se aplique ``FORCE``.

* El Superadministrador de Plataforma **no** tiene excepción sobre las tablas
  de inquilino. El alcance del proyecto dice que no accede a información
  clínica de ninguna organización, y eso se hace cumplir acá, no sólo en la
  capa de aplicación.
"""

from django.db import migrations

# Tablas con organization_id: sólo se ven las filas del inquilino del contexto.
TENANT_TABLES = ["branches", "roles", "role_permissions", "user_roles", "patients"]

# Tablas donde además existen filas de nivel plataforma (organization_id NULL).
PLATFORM_SCOPED_TABLES = ["subscriptions", "usage_metrics"]

# Buzones de sólo escritura: cualquiera inserta, sólo el superadmin lee.
MAILBOX_TABLES = ["isolation_alerts", "login_attempts"]


FUNCTIONS = """
CREATE OR REPLACE FUNCTION app_current_tenant() RETURNS uuid
    LANGUAGE sql STABLE
    AS $fn$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $fn$;

CREATE OR REPLACE FUNCTION app_is_platform_admin() RETURNS boolean
    LANGUAGE sql STABLE
    AS $fn$ SELECT coalesce(current_setting('app.is_platform_admin', true) = 'on', false) $fn$;

-- Resuelve el inquilino a partir de su slug, para el formulario de login.
--
-- Existe por un problema del huevo y la gallina: antes de autenticar no hay
-- contexto, así que un SELECT sobre organizations devolvería cero filas por
-- la propia política, y el login nunca podría empezar.
--
-- Devuelve UNA columna —el uuid— y sólo de organizaciones activas. No permite
-- enumerar: hay que conocer el slug exacto de antemano. El permiso de
-- plataforma se activa y se restaura dentro de la misma llamada, de modo que
-- no sobrevive al retorno de la función.
CREATE OR REPLACE FUNCTION app_resolve_tenant(p_slug text) RETURNS uuid
    LANGUAGE plpgsql VOLATILE
    AS $fn$
DECLARE
    v_id   uuid;
    v_prev text;
BEGIN
    v_prev := coalesce(current_setting('app.is_platform_admin', true), '');
    PERFORM set_config('app.is_platform_admin', 'on', true);
    SELECT id INTO v_id FROM organizations
     WHERE slug = p_slug AND status = 'active';
    PERFORM set_config('app.is_platform_admin', v_prev, true);
    RETURN v_id;
END
$fn$;
"""

FUNCTIONS_REVERSE = """
DROP FUNCTION IF EXISTS app_resolve_tenant(text);
DROP FUNCTION IF EXISTS app_is_platform_admin();
DROP FUNCTION IF EXISTS app_current_tenant();
"""


# --------------------------------------------------------------------------
#  Claves foráneas compuestas
#
#  Django sólo sabe expresar FK de una columna. Estas llevan también el
#  organization_id, que es lo que impide, por ejemplo, asignarle a un usuario
#  una sucursal de otra organización.
#
#  MATCH SIMPLE (el modo por omisión): si alguna columna es NULL, la
#  restricción no se evalúa. Es justo lo que necesita el superadministrador,
#  que tiene organization_id NULL.
#
#  ON DELETE SET NULL lleva lista de columnas explícita para anular sólo la
#  referencia y NO el organization_id, que dejaría al usuario violando
#  ck_user_scope. Requiere PostgreSQL 15 o superior.
# --------------------------------------------------------------------------
COMPOSITE_FKS = """
-- users.branch debe pertenecer a la misma organización que el usuario.
DO $do$
DECLARE c text;
BEGIN
    SELECT conname INTO c FROM pg_constraint
     WHERE conrelid = 'users'::regclass AND contype = 'f'
       AND confrelid = 'branches'::regclass;
    IF c IS NOT NULL THEN
        EXECUTE format('ALTER TABLE users DROP CONSTRAINT %I', c);
    END IF;
END
$do$;

ALTER TABLE users ADD CONSTRAINT fk_user_branch_same_org
    FOREIGN KEY (branch_id, organization_id)
    REFERENCES branches (id, organization_id) ON DELETE SET NULL (branch_id);

-- patients.user debe pertenecer a la misma organización que el paciente.
DO $do$
DECLARE c text;
BEGIN
    SELECT conname INTO c FROM pg_constraint
     WHERE conrelid = 'patients'::regclass AND contype = 'f'
       AND confrelid = 'users'::regclass;
    IF c IS NOT NULL THEN
        EXECUTE format('ALTER TABLE patients DROP CONSTRAINT %I', c);
    END IF;
END
$do$;

ALTER TABLE patients ADD CONSTRAINT fk_patient_user_same_org
    FOREIGN KEY (user_id, organization_id)
    REFERENCES users (id, organization_id) ON DELETE SET NULL (user_id);

-- El titular de un paciente debe ser de la misma organización.
DO $do$
DECLARE c text;
BEGIN
    SELECT conname INTO c FROM pg_constraint
     WHERE conrelid = 'patients'::regclass AND contype = 'f'
       AND confrelid = 'patients'::regclass;
    IF c IS NOT NULL THEN
        EXECUTE format('ALTER TABLE patients DROP CONSTRAINT %I', c);
    END IF;
END
$do$;

ALTER TABLE patients ADD CONSTRAINT fk_patient_guardian_same_org
    FOREIGN KEY (guardian_id, organization_id)
    REFERENCES patients (id, organization_id) ON DELETE SET NULL (guardian_id);

-- Un inquilino no puede asignarse un rol de otro.
DO $do$
DECLARE c text;
BEGIN
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'role_permissions'::regclass AND contype = 'f'
           AND confrelid = 'roles'::regclass
    LOOP
        EXECUTE format('ALTER TABLE role_permissions DROP CONSTRAINT %I', c);
    END LOOP;
    FOR c IN
        SELECT conname FROM pg_constraint
         WHERE conrelid = 'user_roles'::regclass AND contype = 'f'
           AND confrelid = 'roles'::regclass
    LOOP
        EXECUTE format('ALTER TABLE user_roles DROP CONSTRAINT %I', c);
    END LOOP;
END
$do$;

ALTER TABLE role_permissions ADD CONSTRAINT fk_role_permission_role_same_org
    FOREIGN KEY (role_id, organization_id)
    REFERENCES roles (id, organization_id) ON DELETE CASCADE;

ALTER TABLE user_roles ADD CONSTRAINT fk_user_role_role_same_org
    FOREIGN KEY (role_id, organization_id)
    REFERENCES roles (id, organization_id) ON DELETE RESTRICT;
"""


def _tenant_policies():
    sql = []
    for table in TENANT_TABLES:
        sql.append(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE  ROW LEVEL SECURITY;
            CREATE POLICY tenant_isolation ON {table}
                USING (organization_id = app_current_tenant())
                WITH CHECK (organization_id = app_current_tenant());
        """)
    return "\n".join(sql)


SPECIAL_POLICIES = """
-- roles y role_permissions: las plantillas del sistema (organization_id NULL)
-- las LEE cualquier inquilino, para poder clonarlas al dar de alta una
-- organización; sólo el superadministrador las ESCRIBE.
--
-- Sin la política de escritura, la migración semilla falla: Django corre las
-- migraciones como app_user, sujeto a RLS.
CREATE POLICY system_templates_read ON roles
    FOR SELECT USING (organization_id IS NULL);
CREATE POLICY system_templates_write ON roles
    USING (organization_id IS NULL AND app_is_platform_admin())
    WITH CHECK (organization_id IS NULL AND app_is_platform_admin());

CREATE POLICY system_templates_read ON role_permissions
    FOR SELECT USING (organization_id IS NULL);
CREATE POLICY system_templates_write ON role_permissions
    USING (organization_id IS NULL AND app_is_platform_admin())
    WITH CHECK (organization_id IS NULL AND app_is_platform_admin());

-- users: el superadministrador debe poder verse a sí mismo para iniciar
-- sesión, pero no a los usuarios de ninguna organización.
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

-- audit_log: mismo patrón que users. El superadministrador audita sus propias
-- acciones (alta de organización, asignación de plan) con organization_id
-- NULL, y no ve la bitácora de ningún inquilino.
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

-- organizations: el superadmin las administra todas; cada inquilino sólo lee
-- su propia ficha, que necesita para el logo y los colores.
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE  ROW LEVEL SECURITY;
CREATE POLICY platform_admin_all ON organizations
    USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin());
CREATE POLICY tenant_reads_itself ON organizations
    FOR SELECT USING (id = app_current_tenant());

-- subscription_plans: catálogo legible por todos, escribible sólo por el
-- superadministrador.
ALTER TABLE subscription_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_plans FORCE  ROW LEVEL SECURITY;
CREATE POLICY plans_readable ON subscription_plans FOR SELECT USING (true);
CREATE POLICY plans_writable ON subscription_plans
    USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin());
"""


def _platform_scoped_policies():
    sql = []
    for table in PLATFORM_SCOPED_TABLES:
        sql.append(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE  ROW LEVEL SECURITY;
            CREATE POLICY platform_admin_all ON {table}
                USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin());
            CREATE POLICY tenant_reads_itself ON {table}
                FOR SELECT USING (organization_id = app_current_tenant());
        """)
    return "\n".join(sql)


def _mailbox_policies():
    """Buzones de sólo escritura.

    Cualquier contexto puede INSERTAR, y es imprescindible: quien detecta un
    acceso cruzado es el middleware, que en ese momento está en el contexto de
    un inquilino cualquiera; y un intento de login fallido se registra antes de
    saber siquiera a qué organización pertenece el correo.
    """
    sql = []
    for table in MAILBOX_TABLES:
        sql.append(f"""
            ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table} FORCE  ROW LEVEL SECURITY;
            CREATE POLICY platform_admin_manages ON {table}
                USING (app_is_platform_admin()) WITH CHECK (app_is_platform_admin());
            CREATE POLICY anyone_reports ON {table}
                FOR INSERT WITH CHECK (true);
        """)
    return "\n".join(sql)


# RNF-18: la bitácora es inalterable. Se inserta, nunca se modifica.
# Se revoca al usuario que corre la migración, que es el mismo con el que se
# conecta la aplicación.
IMMUTABLE_LOGS = """
REVOKE UPDATE, DELETE ON audit_log      FROM CURRENT_USER;
REVOKE UPDATE, DELETE ON login_attempts FROM CURRENT_USER;
"""

IMMUTABLE_LOGS_REVERSE = """
GRANT UPDATE, DELETE ON audit_log      TO CURRENT_USER;
GRANT UPDATE, DELETE ON login_attempts TO CURRENT_USER;
"""


# Vista de apoyo para el panel de US-45: el plan vigente de cada organización,
# ya resuelto.
VIEW = """
CREATE OR REPLACE VIEW v_organization_current_plan AS
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
"""

VIEW_REVERSE = "DROP VIEW IF EXISTS v_organization_current_plan;"


def _drop_policies():
    """Vuelta atrás: quita políticas y desactiva RLS."""
    all_tables = (
        TENANT_TABLES + PLATFORM_SCOPED_TABLES + MAILBOX_TABLES
        + ["users", "audit_log", "organizations", "subscription_plans"]
    )
    sql = []
    for table in all_tables:
        sql.append(f"""
            DO $do$
            DECLARE p text;
            BEGIN
                FOR p IN SELECT policyname FROM pg_policies
                          WHERE schemaname = 'public' AND tablename = '{table}'
                LOOP
                    EXECUTE format('DROP POLICY %I ON {table}', p);
                END LOOP;
            END
            $do$;
            ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
        """)
    return "\n".join(sql)


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0001_initial"),
        ("accounts", "0002_initial"),
        ("catalog", "0001_initial"),
        ("patients", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(FUNCTIONS, FUNCTIONS_REVERSE),
        migrations.RunSQL(COMPOSITE_FKS, migrations.RunSQL.noop),
        migrations.RunSQL(VIEW, VIEW_REVERSE),
        migrations.RunSQL(_tenant_policies(), migrations.RunSQL.noop),
        migrations.RunSQL(SPECIAL_POLICIES, migrations.RunSQL.noop),
        migrations.RunSQL(_platform_scoped_policies(), migrations.RunSQL.noop),
        migrations.RunSQL(_mailbox_policies(), _drop_policies()),
        migrations.RunSQL(IMMUTABLE_LOGS, IMMUTABLE_LOGS_REVERSE),
    ]
