-- ==========================================================
--  Réplica local del entorno de Supabase.
--
--  Objetivo: que el aislamiento multi-inquilino se comporte
--  igual en la máquina de cada desarrollador que en la
--  demostración. Si en local se usa el superusuario, el RLS
--  queda apagado y el fallo aparece recién en la presentación.
--
--  Se ejecuta automáticamente al crear el contenedor.
-- ==========================================================

CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE app_user WITH
    LOGIN
    PASSWORD 'app_local_pass'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOBYPASSRLS;

GRANT USAGE, CREATE ON SCHEMA public TO app_user;
ALTER ROLE app_user SET search_path = public, extensions;

-- app_user es dueño del esquema para que las migraciones de Django creen las
-- tablas a su nombre. Por eso las políticas RLS llevan FORCE: sin él, el
-- dueño quedaría exento de sus propias reglas.
ALTER SCHEMA public OWNER TO app_user;

-- SÓLO EN LOCAL. Pytest crea su propia base de pruebas (test_plataforma) y se
-- conecta como app_user, porque correr las pruebas de aislamiento como
-- postgres no probaría nada: postgres es superusuario y omite RLS.
-- En Supabase este permiso NO se concede: ahí no se corren pruebas.
ALTER ROLE app_user CREATEDB;

-- Permite hacer SET LOCAL ROLE app_user desde psql para
-- verificar el aislamiento sin abrir otra conexión.
GRANT app_user TO postgres;

-- Comprobación rápida (ejecutar a mano, no forma parte del init):
--   SELECT extname FROM pg_extension WHERE extname = 'vector';
--   SELECT rolname, rolbypassrls FROM pg_roles WHERE rolname = 'app_user';
