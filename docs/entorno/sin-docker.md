# Sin Docker — PostgreSQL instalado directamente

Para quien no puede correr Docker Desktop: máquinas más antiguas, Windows Home
sin virtualización, o poca memoria.

**Sí se puede trabajar igual.** Docker es una comodidad, no un requisito: lo
único que aporta es levantar un PostgreSQL configurado en un comando. Se puede
instalar PostgreSQL a mano y dejarlo igual de bien.

Al terminar tenés que ver lo mismo que los demás: **`21 passed`**.

> **Verificado el 2026-08-23.** Las 6 migraciones del Sprint 0 y las 21 pruebas
> de aislamiento se corrieron contra una base **sin pgvector**, que es como
> queda un PostgreSQL recién instalado. Todo pasa.

---

## Por qué esto funciona

El único componente del proyecto que Docker aporta hoy es **PostgreSQL 16**.
Nada más: Django, las pruebas y el resto corren en tu Python.

La única diferencia real con el contenedor es **pgvector**, la extensión para
búsqueda por similitud. **En el Sprint 0 no se usa**: no hay ninguna columna de
tipo vector en el modelo. Recién hace falta en el **Sprint 3**, para el chatbot.
Ese problema se resuelve entonces — abajo está el plan.

Todo lo demás es idéntico: las mismas migraciones, las mismas políticas de
aislamiento y las mismas 21 pruebas.

---

## 1. Instalar PostgreSQL

Bajá el instalador de **EDB** desde
`postgresql.org/download/windows` y elegí la versión **16 o 17**.

> **Mínimo: PostgreSQL 15.** La migración de políticas de aislamiento usa
> `ON DELETE SET NULL (columna)`, que existe desde la 15. Con la 14 o anterior
> el `migrate` falla.

Durante la instalación:

| Paso | Qué poner |
|---|---|
| Componentes | PostgreSQL Server y Command Line Tools. **pgAdmin es opcional**; en máquinas con poca memoria conviene no instalarlo |
| Contraseña de `postgres` | la que quieras, pero **anotala** — la vas a necesitar en el paso 2 |
| Puerto | **5432**. Si el instalador propone otro es porque ya hay un PostgreSQL; ver la nota al final |
| Locale | dejá el que viene |

Es una instalación liviana: no necesita virtualización, ni WSL, ni máquina
virtual. Anda en cualquier Windows que corra el resto del proyecto.

## 2. Crear la base y el usuario de la aplicación

Abrí **SQL Shell (psql)** desde el menú de inicio. Te va a pedir varios datos:
aceptá todos con Enter hasta la contraseña, y ahí poné la de `postgres`.

Pegá esto tal cual:

```sql
CREATE DATABASE plataforma;

CREATE ROLE app_user WITH
    LOGIN
    PASSWORD 'app_local_pass'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOBYPASSRLS;

-- Pytest crea su propia base de pruebas. Sólo en local.
ALTER ROLE app_user CREATEDB;
```

Ahora conectate a la base recién creada y dale el esquema a `app_user`:

```
\c plataforma
```

```sql
ALTER SCHEMA public OWNER TO app_user;
GRANT USAGE, CREATE ON SCHEMA public TO app_user;
ALTER ROLE app_user SET search_path = public, extensions;
```

Salís con `\q`.

### Qué es cada cosa, en dos líneas

- **`app_user` con `NOBYPASSRLS`** es lo que hace que el aislamiento entre
  organizaciones signifique algo. Django se conecta con este rol, nunca con
  `postgres`, que ignora todas las políticas.
- **`app_user` dueño del esquema** para que las migraciones creen las tablas a
  su nombre, igual que en el contenedor y en Supabase.

Es exactamente el contenido de `backend/init-db/01-app-user.sql`, sin la línea
de pgvector.

## 3. Seguir el tutorial normal

Volvé a [primeros-pasos.md](primeros-pasos.md) y hacé los pasos **1 a 4**
(Python 3.13, clonar, entorno virtual, dependencias, `.env`).

**Saltate el paso 5** (`docker compose up -d`): tu base ya está corriendo como
un servicio de Windows, arranca sola con la máquina.

El `DATABASE_URL` de la plantilla **te sirve tal cual**, sin cambiarle nada:

```
DATABASE_URL=postgresql://app_user:app_local_pass@localhost:5432/plataforma
```

Y seguí con los pasos 6 y 7:

```bash
cd backend
python manage.py migrate
pytest
```

**`21 passed`** y estás listo.

---

## El día a día

Igual que los demás, pero sin Docker:

```bash
cd backend
.venv\Scripts\activate
git pull
python manage.py migrate
```

No hay que levantar nada: PostgreSQL corre como servicio de Windows.

### Si algo se enreda, empezá de cero

Los otros usan `docker compose down -v`. Tu equivalente, desde **SQL Shell**
conectado a `postgres` (no a `plataforma`):

```sql
DROP DATABASE plataforma;
CREATE DATABASE plataforma;
\c plataforma
ALTER SCHEMA public OWNER TO app_user;
GRANT USAGE, CREATE ON SCHEMA public TO app_user;
```

Y después `python manage.py migrate`.

---

## Lo único que te va a faltar: pgvector, en el Sprint 3

El chatbot con RAG guarda *embeddings* en columnas de tipo `vector`. Eso
necesita la extensión pgvector, que el instalador de EDB **no trae**.

**No es un problema ahora.** Cuando llegue el Sprint 3 hay tres caminos, en
orden de conveniencia:

1. **Instalar pgvector sobre tu PostgreSQL.** Hay binarios para Windows en
   `github.com/pgvector/pgvector`; se copian dos archivos dentro de la carpeta
   de PostgreSQL y después `CREATE EXTENSION vector;`. Es el camino limpio.
2. **Que para entonces la máquina corra Docker.** A veces sólo falta activar la
   virtualización en la BIOS, que es gratis. Ver el paso 0 de
   [primeros-pasos.md](primeros-pasos.md).
3. **Trabajar esa historia contra Supabase**, que ya tiene pgvector. Requiere
   pedirle las credenciales al Scrum Master y coordinar, así que es el último
   recurso.

Conviene resolverlo **antes** de que empiece el Sprint 3, no el mismo día.

---

## Problemas frecuentes

**El instalador propone el puerto 5433 en vez del 5432.**
Ya hay otro PostgreSQL instalado en la máquina. Dos opciones: desinstalar el
viejo si no lo usás, o aceptar el 5433 y ajustar el `.env`:

```
DATABASE_URL=postgresql://app_user:app_local_pass@localhost:5433/plataforma
```

**`psql` no se reconoce como comando.**
El instalador de EDB no agrega `psql` al PATH. Usá **SQL Shell (psql)** desde
el menú de inicio, o agregá `C:\Program Files\PostgreSQL\16\bin` al PATH de
usuario.

**`FATAL: password authentication failed for user "app_user"`.**
La contraseña del `.env` no coincide con la del `CREATE ROLE`. Si la cambiaste,
volvé a ponerla igual:

```sql
ALTER ROLE app_user WITH PASSWORD 'app_local_pass';
```

**`permission denied for schema public` al migrar.**
Faltó el `ALTER SCHEMA public OWNER TO app_user;` del paso 2, o lo corriste
conectado a la base equivocada. Tiene que ser **dentro de `plataforma`**, no de
`postgres`.

**`pytest` falla al crear la base de pruebas.**
Faltó `ALTER ROLE app_user CREATEDB;`.

**`syntax error at or near "("` durante `tenancy.0002_rls_policies`.**
Tu PostgreSQL es anterior a la 15. Hay que actualizar.
