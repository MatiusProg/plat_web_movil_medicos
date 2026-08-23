# Versiones fijadas

**Los seis usamos exactamente estas versiones.** La deriva de versiones rompe
compilaciones y produce errores que parecen de código pero no lo son. Es el
mismo criterio que ya acordamos para Flutter en
[setup-movil.md](setup-movil.md).

Verificado el **2026-08-23** contra PyPI y contra el contenedor del proyecto.

---

## Backend

| Componente | Versión | Restrictiva |
|---|---|---|
| **Python** | **3.13.x** | **sí — ver abajo** |
| Django | 5.2.17 (LTS) | sí |
| djangorestframework | 3.18.0 | no |
| djangorestframework-simplejwt | 5.5.1 | **es la que impone el límite** |
| psycopg | 3.3.4 (`psycopg[binary]`) | no — pero **no** usar psycopg2 |
| argon2-cffi | 25.1.0 | no |
| pytest / pytest-django | 9.1.1 / 4.14.0 | no |

Todo está fijado con `==` en [`backend/requirements.txt`](../../backend/requirements.txt).

## Base de datos

| Componente | Versión |
|---|---|
| PostgreSQL (contenedor local) | 16 (`pgvector/pgvector:pg16`) |
| pgvector | 0.8.6 |
| PostgreSQL (Supabase) | la que provisione Supabase — mínimo 15 |

El mínimo de 15 no es arbitrario: la migración de políticas RLS usa
`ON DELETE SET NULL (columna)` con lista de columnas explícita, que existe
desde PostgreSQL 15.

---

## Por qué Python 3.13 y no 3.14

Esta es la restricción que más incomoda, así que va el razonamiento completo.

### La cadena de dependencias

1. El proyecto autentica con JWT: US-02 (iniciar sesión) y CU4 (cerrar sesión
   invalidando el token). Eso lo resuelve `djangorestframework-simplejwt`.
2. SimpleJWT 5.5.1 declara soporte para Django **4.2, 5.0, 5.1 y 5.2**. Ahí se
   corta: no declara Django 6.x.
3. Django 5.2 —que además es la LTS— soporta Python 3.10 a 3.13.
4. Django 6.x, la única línea que cubre Python 3.14, declara
   `Requires-Python >=3.12`.

O sea: **usar Python 3.14 obliga a Django 6.x, donde la biblioteca que
autentica todo el sistema queda sin soporte declarado.**

### Lo que se comprobó, y lo que no era el problema

La sospecha inicial era que Python 3.14 no tendría wheels binarios y haría
falta un compilador de C en Windows. **Es falso**: se verificó contra PyPI que
todo el stack resuelve en 3.14 con wheels nativos
(`psycopg_binary-3.3.4-cp314-cp314-win_amd64.whl`, `cffi-2.1.1-cp314-...`).
Descartado eso, el único diferencial real es SimpleJWT.

`pip` tampoco bloquea: Django 5.2 declara `Requires-Python >=3.10`, así que
instalarlo sobre 3.14 *funciona*. Pero 3.14 está fuera de la matriz que Django
5.2 prueba, y "instala" no es "soportado".

### El beneficio adicional

Con Django 5.2 LTS, cada tutorial, respuesta de StackOverflow y `settings.py`
que consulte el equipo coincide con lo que tenemos en pantalla. Para cinco
personas aprendiendo Django, eso es la diferencia entre destrabarse en cinco
minutos o en dos horas.

### Cuándo revisar esta decisión

Cuando SimpleJWT publique una versión que declare Django 6.x. Ahí conviene
esperar igual al siguiente Django LTS antes de moverse. Para este proyecto,
que termina en noviembre de 2026, no hace falta.

---

## Instalación

Tener Python 3.14 instalado **no es un problema**: conviven. El entorno
virtual fija cuál se usa, una sola vez.

```powershell
# Windows
winget install --id Python.Python.3.13 -e
cd backend
py -3.13 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

```bash
# macOS / Linux
cd backend
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Comprobar que quedó bien

```bash
python --version        # 3.13.x  — si dice 3.14, el venv no está activado
python -c "import django; print(django.get_version())"   # 5.2.17
pytest                  # todas en verde
```

**El error más común** es tener el entorno virtual sin activar y estar usando
el Python del sistema. Si `python --version` dice 3.14, no seguís dentro del
`venv`. En VS Code, además, hay que elegir el intérprete a mano:
`Ctrl+Shift+P` → *Python: Select Interpreter* → el de `backend\.venv`.

---

## Nota sobre `app_user` y las pruebas

`app_user` se crea con `NOCREATEDB` a propósito: es el usuario con el que se
conecta la aplicación y no tiene por qué poder crear bases.

Pytest, en cambio, crea una base de pruebas (`test_plataforma`). Por eso el
contenedor local —**y sólo el local**— le concede el permiso:

```sql
ALTER ROLE app_user CREATEDB;
```

Está en `backend/init-db/01-app-user.sql`. **En Supabase no se concede**: ahí
no se corren pruebas, es el entorno compartido de demostración.

Que las pruebas corran como `app_user` no es un detalle: correrlas como
`postgres` no probaría nada, porque `postgres` es superusuario y omite las
políticas RLS aunque las tablas tengan `FORCE`. Ya nos costó cinco defectos.
