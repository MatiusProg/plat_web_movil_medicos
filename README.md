# plat_web_movil_medicos

Plataforma web y móvil multi-inquilino para la gestión de atención médica
ambulatoria. Caso de estudio: Fundación Centro Multifuncional Adolfo Kolping.

Proyecto académico — Sistemas de Información 2, Grupo 15.

> **Repositorio público.** No se cargan datos de personas reales en ningún
> entorno, ni en fixtures, ni en capturas, ni en la demostración. Todos los
> datos son ficticios.

---

## Tecnologías

| Capa | Herramienta | Versión |
|---|---|---|
| Backend | Django + Django REST Framework | Django **5.2 LTS** · DRF 3.18 |
| Lenguaje del backend | Python | **3.13** — ver la advertencia de abajo |
| Base de datos | PostgreSQL + pgvector + Row Level Security | **16** |
| Controlador de base de datos | psycopg | **3.3** (no psycopg2) |
| Frontend web | React + Vite + TailwindCSS | React **19.2** · Vite 8.2 · Tailwind 4.3 |
| Móvil | Flutter | _(a fijar en la tarea 6 del Sprint 0)_ |
| Base de demostración | Supabase (PostgreSQL gestionado) | — |
| Hospedaje de la aplicación | Railway | — |
| Gestión del proyecto | Jira | — |

### ⚠️ Python 3.13, no 3.14

**Los seis usamos exactamente Python 3.13.** No es una preferencia: es una
restricción con una causa concreta.

`djangorestframework-simplejwt` —de la que dependen el inicio de sesión
(US-02) y el cierre de sesión con lista negra (CU4)— declara soporte **hasta
Django 5.2**. Y Django 5.2, que es la LTS, cubre Python 3.10 a 3.13. Subir a
Python 3.14 obligaría a Django 6.x, donde SimpleJWT queda sin soporte
declarado, justo en la pieza que autentica a todo el sistema.

Si ya tenés Python 3.14, **no hace falta desinstalarlo**: conviven sin
problema. El entorno virtual fija cuál se usa.

```powershell
winget install --id Python.Python.3.13 -e     # Windows
py -3.13 -m venv .venv                        # el venv fija la versión
```

Las versiones exactas están fijadas en `backend/requirements.txt`. El
razonamiento completo, con los datos de PyPI que lo respaldan, está en
[docs/entorno/versiones.md](docs/entorno/versiones.md).

---

## Arranque rápido

Requisitos: Docker, **Python 3.13**, Node 20+, Flutter.

```bash
git clone https://github.com/USUARIO/plat_web_movil_medicos.git
cd plat_web_movil_medicos

cp .env.example .env        # completar los valores
docker compose up -d        # levanta PostgreSQL con pgvector y app_user

cd backend
py -3.13 -m venv .venv                  # Windows
python3.13 -m venv .venv                # macOS / Linux
.venv\Scripts\activate                  # Windows
source .venv/bin/activate               # macOS / Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Verificación de que el entorno quedó bien:

```bash
# 1. La versión del intérprete del entorno virtual.
python --version                        # debe decir 3.13.x

# 2. La conexión va como app_user, nunca como postgres.
docker compose exec db psql -U app_user -d plataforma -c "select current_user;"

# 3. El aislamiento está realmente activo. Es el criterio 4 de la
#    Definición de Terminado, y estas pruebas se conectan como app_user.
cd backend && pytest
```

El paso 2 debe devolver `app_user`. Si devuelve `postgres`, el aislamiento
multi-inquilino está desactivado — ver la sección siguiente.

El paso 3 debe cerrar con todas las pruebas en verde. Si alguna falla, el
aislamiento está roto y ninguna historia puede darse por terminada.

---

## Aislamiento multi-inquilino — lo que hay que saber

El sistema atiende a varias organizaciones sobre una misma base de datos
(modelo *pool*: esquema compartido con discriminador `tenant_id`). El
aislamiento tiene dos barreras: el filtro en la capa de aplicación y las
políticas RLS en PostgreSQL. La segunda existe porque la primera depende de
que nadie se olvide nunca.

Estos siete puntos están verificados sobre la infraestructura real. Ignorar
cualquiera de ellos apaga el aislamiento **sin producir ningún error**.

**1. Django y Pytest se conectan como `app_user`, nunca como `postgres`.**
El rol `postgres` de Supabase tiene el atributo `BYPASSRLS`: ignora todas las
políticas. Si el `DATABASE_URL` de pruebas apunta a `postgres`, los tests de
aislamiento pasan siempre sin verificar nada.

**2. Toda tabla con `tenant_id` necesita `ENABLE` y `FORCE`.**

```sql
ALTER TABLE mi_tabla ENABLE ROW LEVEL SECURITY;
ALTER TABLE mi_tabla FORCE  ROW LEVEL SECURITY;
```

`ENABLE` sola no alcanza: el dueño de la tabla queda exento, y como las
migraciones de Django las corre `app_user`, `app_user` es el dueño. El botón
del panel de Supabase aplica únicamente `ENABLE`.

**3. El middleware usa `SET LOCAL`, nunca `SET`.**

```sql
BEGIN;
  SET LOCAL app.tenant_id = '...';
  -- consultas
COMMIT;
```

`SET LOCAL` se descarta al cerrar la transacción. Con `SET` a secas el valor
persiste en la sesión, y la conexión vuelve al pooler arrastrando el inquilino
anterior: la petición siguiente lee datos ajenos. Es una fuga silenciosa,
intermitente e imposible de reproducir con poca carga.

**4. Sin `app.tenant_id` definido, las consultas devuelven cero filas.**
La política compara contra `NULL` y ninguna comparación con `NULL` es
verdadera. Es deliberado: si el middleware falla, el sistema no devuelve nada
en lugar de devolverlo todo. **Si ves cero filas al depurar, es esto** — no se
borraron los datos.

**5. El panel de Supabase siempre muestra todas las filas.** El SQL Editor y
el Table Editor corren como `postgres`. No es un error de las políticas. Para
verificar el aislamiento desde el panel:

```sql
BEGIN;
  SET LOCAL ROLE app_user;
  SET LOCAL app.tenant_id = '...';
  SELECT * FROM mi_tabla;
COMMIT;
```

**6. Conexión por Session pooler, puerto 5432.** El Transaction pooler (6543)
rompe las sentencias preparadas de Django. El usuario lleva el ref del
proyecto como sufijo: `app_user.REF_PROYECTO`.

**7. `app_user` necesita `search_path = public, extensions`.** Supabase
instala pgvector en el esquema `extensions`. Sin esa configuración, las
migraciones fallan con un error que no menciona el `search_path`.

---

## Estructura

```
backend/
  config/        settings, urls, wsgi
  tenancy/       organizaciones, planes, suscripciones, métricas, alertas
                 + el middleware que fija el contexto de inquilino
  accounts/      usuarios, roles, permisos, bitácora, intentos de login
  catalog/       sucursales (y en el Sprint 1: especialidades y agendas)
  patients/      pacientes y pacientes a cargo
  tests/         pruebas de aislamiento multi-inquilino
  init-db/       SQL de arranque del contenedor local
frontend/
  src/api/       el contrato con el backend
  src/sesion/    estado de la sesion, renovacion automatica
  src/componentes/  los reutilizables
  src/paginas/   una carpeta por pantalla
mobile/      Flutter
docs/
  sprints/       Actas de Scrum por sprint — la evidencia del proceso
  entorno/       Guías de instalación, versiones fijadas y Supabase
  modelo-datos/  El modelo por sprint, con su DDL de referencia
```

### Dónde mirar antes de escribir código

| Si vas a… | Leé primero |
|---|---|
| **montar tu entorno por primera vez** | **[docs/entorno/primeros-pasos.md](docs/entorno/primeros-pasos.md)** — de cero a las pruebas en verde |
| **entrar al sistema y registrar tu organización** | **[docs/entorno/primera-organizacion.md](docs/entorno/primera-organizacion.md)** — el superadministrador y el primer inquilino |
| montarlo en una máquina que no corre Docker | [docs/entorno/sin-docker.md](docs/entorno/sin-docker.md) |
| entender por qué Python 3.13 y no 3.14 | [docs/entorno/versiones.md](docs/entorno/versiones.md) |
| conectarte a Supabase o traerte datos | [docs/entorno/supabase.md](docs/entorno/supabase.md) |
| **escribir código del backend** | **[docs/convenciones-de-codigo.md](docs/convenciones-de-codigo.md)** — dónde va cada cosa, y las reglas que no se rompen |
| **escribir código del frontend web** | **[docs/frontend/decisiones.md](docs/frontend/decisiones.md)** — el stack, el idioma del código y lo que falta acordar |
| tocar la base de datos | [docs/modelo-datos/sprint-0.md](docs/modelo-datos/sprint-0.md) |
| saber qué se rompió y por qué | [docs/registro-de-defectos.md](docs/registro-de-defectos.md) |
| instalar Flutter | [docs/entorno/setup-movil.md](docs/entorno/setup-movil.md) |

---

## Cómo contribuir

Ver [CONTRIBUTING.md](CONTRIBUTING.md): convención de ramas, formato de
commits, proceso de pull request y Definición de Terminado.

## Equipo — Grupo 15

| Rol | Integrante | Registrto |
|---|---|---|
| Scrum Master | Luis Mateo Hurtado Castro | 222008687 |
| Product Owner | Alexander Osinaga Blanco | 223043631 |
| Developer | Karen Paola Ortega Mancilla | 222056592 |
| Developer | Luis Miguel Aguayo Quiroz | 218000405 |
| Developer | José Daniel Iporo Chulque | 216024773 |
| Developer | Michael Alexander Mamani Samurio | 220153590 |

## Licencia

MIT — ver [LICENSE](LICENSE).
