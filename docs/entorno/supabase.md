# Supabase — conexión, `.env` y sincronización con el PostgreSQL local

Guía para los seis. Cubre tres cosas:

1. cómo armar tu `.env` y de dónde sale cada valor,
2. cómo conectarte a la base de demostración en Supabase,
3. cómo traerte los datos de Supabase a tu contenedor local.

---

## 0. Antes de empezar: qué vive dónde

Hay **dos bases** y confundirlas es el error más caro de este proyecto.

| | Local (Docker) | Supabase |
|---|---|---|
| Para qué | desarrollar y correr pruebas | demostración y datos compartidos |
| Quién la toca | cada uno la suya | **sólo el Scrum Master** aplica cambios de esquema |
| Se rompe y | la borrás y la volvés a levantar | se para el sprint |
| Puerto | `localhost:5432` (contenedor `plataforma_db`) | pooler de sesión, `5432` |

**Regla que evita el 90 % de los problemas:**

> El **esquema** viaja en una sola dirección: migraciones de Django → tu local, y
> migraciones de Django → Supabase. Nunca al revés, nunca a mano.
> Los **datos** de demostración viajan Supabase → tu local, y sólo eso.

Nadie corre `ALTER TABLE` a mano en Supabase. Si el esquema de Supabase y las
migraciones se separan, `makemigrations` empieza a generar migraciones absurdas
y no hay forma limpia de volver atrás.

> **Nota de estado (2026-08-23).** Todavía no existe el proyecto Django, así que
> hoy el esquema se aplica corriendo `docs/modelo-datos/sprint-0.sql` a mano.
> Eso es un arranque, no el procedimiento definitivo: en cuanto existan los
> modelos de Django, la base de Supabase se **borra y se reconstruye** desde las
> migraciones. Como todavía no hay datos reales, no se pierde nada. Conviene
> hacerlo antes de cargar el primer dato de demostración.

---

## 1. Crear el proyecto en Supabase

Lo hace **una sola persona** (el Scrum Master). Los demás sólo se conectan.

1. Entrar a `supabase.com`, iniciar sesión con GitHub.
2. **New project**. Nombre: `plat-medicos-demo`. Región: la más cercana
   (`South America (São Paulo)` o `East US`).
3. Anotar la **Database Password** que genera. Es la del usuario `postgres`, la
   única vez que se muestra. Va al gestor de contraseñas del equipo, no a
   WhatsApp y no al repositorio.
4. Esperar a que termine de aprovisionar (un par de minutos).

**El `PROJECT_REF`** es la cadena de ~20 letras que aparece en la URL del panel:

```
https://supabase.com/dashboard/project/abcdefghijklmnopqrst
                                       ^^^^^^^^^^^^^^^^^^^^  este
```

Aparece en todas las cadenas de conexión. No es secreto.

### Límites del plan gratuito que importan para noviembre

- 500 MB de base de datos. De sobra para el proyecto.
- **El proyecto se pausa tras 7 días sin actividad** y hay que reactivarlo desde
  el panel. Antes de una defensa o una demo, entrar el día anterior y verificar
  que está activo.
- 2 proyectos gratuitos por cuenta.

---

## 2. Preparar la base de Supabase

Todo esto se corre desde el **SQL Editor** del panel de Supabase, que ejecuta
como `postgres` (superusuario).

### 2.1 · Crear `app_user`

Es el equivalente de `backend/init-db/01-app-user.sql`, adaptado a Supabase.
**Cambiar la contraseña** por una real antes de ejecutarlo.

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE ROLE app_user WITH
    LOGIN
    PASSWORD 'PONER_UNA_CLAVE_REAL_AQUI'
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOBYPASSRLS;

GRANT USAGE, CREATE ON SCHEMA public TO app_user;

-- Sin esto las migraciones fallan con un error que NO menciona el search_path:
-- Supabase instala pgvector en el esquema `extensions`, no en `public`.
ALTER ROLE app_user SET search_path = public, extensions;

-- Permite verificar el aislamiento desde el SQL Editor sin abrir otra conexión.
GRANT app_user TO postgres;
```

`NOBYPASSRLS` es lo que hace que las pruebas de aislamiento signifiquen algo.
El rol `postgres` de Supabase **sí** tiene `BYPASSRLS`: por eso el SQL Editor y
el Table Editor del panel siempre muestran todas las filas de todos los
inquilinos. No es un error de las políticas.

### 2.2 · Aplicar el modelo — **como `app_user`, no desde el SQL Editor**

El SQL Editor del panel corre como `postgres`. Si el esquema se crea desde ahí,
las tablas quedan siendo de `postgres` y hay que ir repartiendo permisos a mano.
Peor: no se parece a lo que hará Django, que crea las tablas como `app_user`.

Lo correcto es conectarse con `psql` **como `app_user`** y correr el archivo:

```bash
psql "postgresql://app_user.PROJECT_REF:CLAVE@aws-0-sa-east-1.pooler.supabase.com:5432/postgres" \
  -v ON_ERROR_STOP=1 -f docs/modelo-datos/sprint-0.sql
```

Así las 14 tablas quedan siendo de `app_user`, igual que en local y que en
producción. Es exactamente por esto que las políticas llevan `FORCE`: sin él,
`app_user` sería dueño y quedaría exento de sus propias reglas.

Al terminar, comprobar:

```sql
SELECT count(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';   -- 14

SELECT relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND NOT (c.relrowsecurity AND c.relforcerowsecurity);        -- solo: permissions
```

### 2.3 · Si aun así lo corriste desde el SQL Editor

Entonces las tablas son de `postgres` y hay que habilitar a `app_user`:

```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES    IN SCHEMA public TO app_user;
GRANT USAGE, SELECT                  ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- RNF-18: la bitácora es inalterable.
REVOKE UPDATE, DELETE ON audit_log, login_attempts FROM app_user;
```

Si seguiste 2.2, este paso **no hace falta**.

### 2.4 · Verificar que el aislamiento quedó activo

```sql
BEGIN;
  SET LOCAL ROLE app_user;
  SET LOCAL app.tenant_id = '00000000-0000-0000-0000-000000000000';
  SELECT count(*) FROM users;   -- debe devolver 0, no error
COMMIT;
```

Si devuelve un número mayor a cero con un UUID inventado, el aislamiento **no**
está funcionando y hay que revisar antes de seguir.

---

## 3. El archivo `.env`

Copiar la plantilla y completarla. **El `.env` nunca se sube**: está en
`.gitignore` y GitHub tiene *push protection* activo.

```bash
cp .env.example .env
```

### De dónde sale cada valor

| Variable | De dónde | ¿Hace falta ahora? |
|---|---|---|
| `SECRET_KEY` | se genera, ver abajo | **sí** |
| `DEBUG` | `True` en local, `False` en Railway | sí, ya viene |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` en local | sí, ya viene |
| `DATABASE_URL` | tu contenedor local **o** Supabase, ver abajo | **sí** |
| `DEFAULT_TENANT_ID` | consulta a la base, después de sembrar | sí, en cuanto exista una organización |
| `VITE_API_BASE_URL` | `http://localhost:8000/api` | sí, ya viene |
| `STRIPE_SECRET_KEY` | panel de Stripe, modo prueba | no — Sprint 2 |
| `STRIPE_WEBHOOK_SECRET` | `stripe listen` o panel de Stripe | no — Sprint 2 |
| `OPENAI_API_KEY` | `platform.openai.com` | no — Sprint 3 |

Las tres últimas **se dejan vacías** por ahora. No hay que ir a sacar claves de
Stripe ni de OpenAI para el Sprint 0.

#### `SECRET_KEY`

Django todavía no está instalado, así que se genera con la librería estándar:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Cuando Django esté instalado, el equivalente idiomático es:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Cada uno genera la suya en local. La de producción se genera aparte y vive sólo
en las variables de entorno de Railway.

#### `DATABASE_URL` — local (lo normal, día a día)

Ya viene bien en la plantilla y no hay que tocarla:

```
DATABASE_URL=postgresql://app_user:app_local_pass@localhost:5432/plataforma
```

**Usuario `app_user`, no `postgres`.** Si apunta a `postgres`, las pruebas de
aislamiento pasan siempre sin verificar nada, porque `postgres` omite RLS.

> Ojo: el PostgreSQL 18 que algunos tienen instalado en Windows escucha en el
> **5433**, no en el 5432. El 5432 es el contenedor, y ese es el del proyecto.

#### `DATABASE_URL` — Supabase (sólo cuando trabajes contra la demo)

En el panel del proyecto, botón **Connect** arriba (en versiones anteriores del
panel: *Project Settings → Database → Connection string*). Aparecen tres
opciones; hay que usar la del medio:

| Opción | Puerto | ¿Usar? |
|---|---|---|
| Direct connection | 5432 | no — sólo IPv6 en el plan gratuito |
| Transaction pooler | **6543** | **no** — rompe las sentencias preparadas de Django |
| **Session pooler** | **5432** | **sí** |

La cadena que da el panel viene con el usuario `postgres`. Hay que cambiar dos
cosas: el usuario a `app_user.PROJECT_REF` y la contraseña a la de `app_user`.

```
DATABASE_URL=postgresql://app_user.abcdefghijklmnopqrst:CLAVE_APP_USER@aws-0-sa-east-1.pooler.supabase.com:5432/postgres
             ................^^^^^^^^ ^^^^^^^^^^^^^^^^^^^^                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                             usuario   tu PROJECT_REF                           el host que muestre TU panel
```

Tres detalles que hacen fallar la conexión:

- El usuario del pooler lleva el `PROJECT_REF` **como sufijo, con un punto**.
  Sin eso el pooler no sabe a qué proyecto mandarte.
- La base se llama `postgres`, no `plataforma`.
- Si la contraseña tiene `@`, `:`, `/` o `#`, hay que escaparla en la URL
  (`@` → `%40`). Lo más simple es elegir una contraseña sin esos caracteres.

#### `DEFAULT_TENANT_ID`

Sale de la base, una vez que exista al menos una organización:

```bash
docker compose exec db psql -U postgres -d plataforma \
  -c "SELECT id, slug, name FROM organizations;"
```

Se copia el `id` de la organización con la que vas a trabajar en desarrollo.

#### `STRIPE_SECRET_KEY` y `STRIPE_WEBHOOK_SECRET` (Sprint 2)

- `dashboard.stripe.com` → activar **Test mode** (el interruptor arriba a la
  derecha) → *Developers → API keys* → **Secret key**. Empieza con `sk_test_`.
  Si empieza con `sk_live_`, está en modo real: no usar.
- El `whsec_` sale de correr `stripe listen --forward-to
  localhost:8000/api/webhooks/stripe`, que lo imprime al arrancar.

#### `OPENAI_API_KEY` (Sprint 3)

`platform.openai.com` → *API keys* → *Create new secret key*. Empieza con
`sk-`. Requiere saldo cargado; conviene una sola clave del equipo con límite de
gasto mensual, no una por persona.

---

## 4. Conectarse a Supabase desde tu máquina

### Con `psql`

Ya tenés el cliente: viene con el PostgreSQL 18 nativo, en
`C:\Program Files\PostgreSQL\18\bin` (ya está en el PATH de usuario).

```bash
psql "postgresql://app_user.abcdefghijklmnopqrst:CLAVE@aws-0-sa-east-1.pooler.supabase.com:5432/postgres"
```

Las comillas son necesarias en PowerShell. La conexión va cifrada sola; no hace
falta agregar `sslmode`.

Prueba de que estás donde creés:

```sql
SELECT current_user, current_database(), inet_server_addr();
```

### Con pgAdmin 4

Ya lo tenés instalado con el PostgreSQL 18.

*Servers → Register → Server*:

- **General → Name:** `Supabase demo`
- **Connection → Host:** `aws-0-sa-east-1.pooler.supabase.com` (el de tu panel)
- **Port:** `5432`
- **Maintenance database:** `postgres`
- **Username:** `app_user.abcdefghijklmnopqrst`
- **Password:** la de `app_user`, marcando *Save password*
- **Parameters → SSL mode:** `require`

### Con DBeaver o VS Code

Cualquier cliente que acepte una URL de PostgreSQL sirve: se pega la misma
cadena del `DATABASE_URL`.

### Por qué en el panel de Supabase ves todo y en tu app no

El SQL Editor y el Table Editor corren como `postgres`, que tiene `BYPASSRLS`.
Ves todas las filas de todos los inquilinos. **No es un error.** Para ver lo
mismo que verá la aplicación:

```sql
BEGIN;
  SET LOCAL ROLE app_user;
  SET LOCAL app.tenant_id = 'el-uuid-de-la-organizacion';
  SELECT * FROM users;
COMMIT;
```

---

## 5. Traerse los datos de Supabase al PostgreSQL local

Sí, se puede. Pero **sólo los datos, nunca el esquema**.

### 5.1 · El esquema NO se copia — se reconstruye

Cada uno arma su base local desde la misma fuente que Supabase:

```bash
# Hoy (todavía sin Django):
docker compose down -v          # borra el volumen y arranca de cero
docker compose up -d
docker compose exec -T db psql -U app_user -d plataforma -v ON_ERROR_STOP=1 \
  -f - < docs/modelo-datos/sprint-0.sql

# En cuanto exista el proyecto Django, esto lo reemplaza:
python manage.py migrate
```

**`-U app_user`, no `-U postgres`.** Es lo que hará Django, y deja las tablas
con el dueño correcto. Dentro del contenedor la conexión va por socket local,
así que no pide contraseña. Verificar que quedó bien:

```bash
docker compose exec db psql -U app_user -d plataforma -c "\dt"
# las 14 tablas deben aparecer con Owner = app_user
```

Así los esquemas son idénticos por construcción, sin depender de la red ni de
que alguien se acuerde de exportar. Un `pg_dump` del esquema de Supabase
arrastraría además roles, permisos y objetos propios de Supabase que en tu
contenedor no existen.

### 5.2 · Los datos sí: exportar de Supabase

```bash
pg_dump "postgresql://postgres.PROJECT_REF:CLAVE_POSTGRES@aws-0-sa-east-1.pooler.supabase.com:5432/postgres" \
  --data-only \
  --schema=public \
  --no-owner \
  --no-privileges \
  --disable-triggers \
  --exclude-table=django_migrations \
  -f datos_demo.sql
```

Qué hace cada bandera y por qué está:

| Bandera | Por qué |
|---|---|
| `--data-only` | el esquema ya lo tenés; sólo querés las filas |
| `--schema=public` | deja fuera `auth`, `storage` y demás esquemas internos de Supabase |
| `--no-owner --no-privileges` | en tu máquina no existen los roles de Supabase |
| `--disable-triggers` | inserta sin respetar el orden de las claves foráneas |
| `--exclude-table=django_migrations` | el historial de migraciones es de cada base |

**Se exporta como `postgres`, no como `app_user`.** `app_user` está sujeto a
RLS: el volcado saldría vacío o incompleto, y sin ningún error.

### 5.3 · Importar en tu contenedor

```bash
docker compose exec -T db psql -U postgres -d plataforma < datos_demo.sql
```

**También como `postgres`.** Este es el error silencioso más feo del proyecto:
si importás como `app_user`, con `FORCE ROW LEVEL SECURITY` y sin
`app.tenant_id` definido, **PostgreSQL rechaza o descarta las filas y el
proceso parece haber funcionado**. Terminás con tablas vacías y sin mensaje de
error.

Comprobar siempre después de importar:

```bash
docker compose exec db psql -U postgres -d plataforma -c \
  "SELECT 'organizations' t, count(*) FROM organizations
   UNION ALL SELECT 'users', count(*) FROM users
   UNION ALL SELECT 'patients', count(*) FROM patients;"
```

### 5.4 · Empezar de cero cuando algo se enreda

```bash
docker compose down -v      # -v borra el volumen: se pierde TODO lo local
docker compose up -d
```

Local se puede tirar cuantas veces haga falta. Es la ventaja de tenerlo en un
contenedor. **`down -v` jamás se corre contra Supabase**, ni existe el
equivalente por accidente.

### 5.5 · Lo que NO hay que hacer

- **Sincronización en las dos direcciones.** No existe una forma limpia de
  fusionar dos PostgreSQL con datos divergentes. Si tu local y Supabase se
  separaron, se tira el local y se vuelve a importar.
- **`pg_dump` del esquema desde Supabase** para armar el local. Ver 5.1.
- **`ALTER TABLE` a mano en Supabase.** Va por migración, la aplica el Scrum
  Master, y se anota en el pull request.
- **Correr las pruebas contra Supabase.** Pytest borra y recrea la base de
  pruebas. Contra la base compartida, borra el trabajo de los otros cinco.

---

## 6. Resumen operativo

**El Scrum Master, una vez:** crea el proyecto, crea `app_user`, aplica el
esquema, comparte `PROJECT_REF` y la contraseña de `app_user` por el gestor de
contraseñas.

**Cada integrante, una vez:**

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(64))"   # -> SECRET_KEY
docker compose up -d
docker compose exec -T db psql -U app_user -d plataforma -v ON_ERROR_STOP=1 \
  -f - < docs/modelo-datos/sprint-0.sql
docker compose exec db psql -U app_user -d plataforma -c "\dt"   # 14 tablas
```

**Cada integrante, cuando necesite los datos de la demo:** los pasos 5.2 y 5.3.

**Todos los días:** se desarrolla contra el contenedor local. A Supabase se va
sólo para probar la demo.
