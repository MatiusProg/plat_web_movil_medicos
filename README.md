# plat_web_movil_medicos

Plataforma web y móvil multi-inquilino para la gestión de atención médica
ambulatoria. Caso de estudio: Fundación Centro Multifuncional Adolfo Kolping.

Proyecto académico — Sistemas de Información 2, Grupo 15.

> **Repositorio público.** No se cargan datos de personas reales en ningún
> entorno, ni en fixtures, ni en capturas, ni en la demostración. Todos los
> datos son ficticios.

---

## Tecnologías

| Capa | Herramienta |
|---|---|
| Backend | Django + Django REST Framework |
| Base de datos | PostgreSQL 16 + pgvector + Row Level Security |
| Frontend web | React |
| Móvil | Flutter |
| Base de demostración | Supabase (PostgreSQL gestionado) |
| Hospedaje de la aplicación | Railway |
| Gestión del proyecto | Jira |

---

## Arranque rápido

Requisitos: Docker, Python 3.11+, Node 20+, Flutter.

```bash
git clone https://github.com/USUARIO/plat_web_movil_medicos.git
cd plat_web_movil_medicos

cp .env.example .env        # completar los valores
docker compose up -d        # levanta PostgreSQL con pgvector y app_user

cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Verificación de que el entorno quedó bien:

```bash
docker compose exec db psql -U app_user -d plataforma -c "select current_user;"
```

Debe devolver `app_user`. Si devuelve `postgres`, el aislamiento
multi-inquilino está desactivado — ver la sección siguiente.

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
backend/     Django + DRF (init-db/ contiene el SQL de arranque local)
frontend/    React
mobile/      Flutter
docs/
  sprints/   Actas de Scrum por sprint — la evidencia del proceso
  entorno/   Guías de instalación
```

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
