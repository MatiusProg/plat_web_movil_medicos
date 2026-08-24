-- ==========================================================
--  Arranque de la base local SIN Docker (PostgreSQL nativo).
--
--  Equivale a backend/init-db/01-app-user.sql, que el contenedor
--  corre solo, menos la línea de pgvector: el instalador de EDB
--  no trae la extensión y en el Sprint 0 no se usa.
--
--  Uso, desde la carpeta del repositorio:
--      psql -U postgres -f scripts/init-local-pg.sql
--
--  Documentado en docs/entorno/sin-docker.md, paso 2.
-- ==========================================================

CREATE DATABASE plataforma;

CREATE ROLE app_user WITH
    LOGIN
    PASSWORD 'app_local_pass'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOBYPASSRLS;

-- SÓLO EN LOCAL. Pytest crea su propia base de pruebas y se conecta como
-- app_user: correr las pruebas de aislamiento como postgres no probaría nada,
-- porque postgres es superusuario y omite RLS.
ALTER ROLE app_user CREATEDB;

-- Permite hacer SET LOCAL ROLE app_user desde psql para verificar el
-- aislamiento sin abrir otra conexión.
GRANT app_user TO postgres;

-- Lo que sigue va DENTRO de plataforma, no de postgres.
\c plataforma

-- app_user es dueño del esquema para que las migraciones de Django creen las
-- tablas a su nombre. Por eso las políticas RLS llevan FORCE: sin él, el
-- dueño quedaría exento de sus propias reglas.
ALTER SCHEMA public OWNER TO app_user;
GRANT USAGE, CREATE ON SCHEMA public TO app_user;
ALTER ROLE app_user SET search_path = public, extensions;

-- Comprobación: rolbypassrls tiene que decir false.
SELECT rolname, rolbypassrls, rolcreatedb FROM pg_roles WHERE rolname = 'app_user';
