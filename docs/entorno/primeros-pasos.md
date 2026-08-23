# Primeros pasos — de cero a desarrollando

Para los cinco integrantes que no armaron la base. Toma unos 20 minutos, casi
todos de descarga.

**Al terminar tenés que ver `21 passed`.** Ese es el único criterio: si sale,
tu entorno está bien y podés tomar tu historia.

---

## Lo que hay que entender antes de empezar (2 minutos)

**Trabajás siempre contra TU propia base de datos**, un PostgreSQL que corre en
Docker en tu máquina. No contra Supabase.

| | Tu base local | Supabase |
|---|---|---|
| Dónde | Docker, en tu máquina | en la nube |
| Para qué | **todo el desarrollo y las pruebas** | la demostración |
| Quién la toca | vos, sólo vos | sólo el Scrum Master |
| Si la rompés | la borrás y la rehacés en 2 minutos | se para el sprint |

**No necesitás credenciales de Supabase para desarrollar.** Si alguna vez las
necesitás, se piden por el gestor de contraseñas del equipo — nunca por
WhatsApp.

Y la idea que hace que todo esto funcione: **el esquema de la base no se copia
de nadie, se reconstruye**. Los modelos de Django y sus migraciones están en el
repositorio. Corrés `migrate` y tu base queda idéntica a la de los otros cinco,
sin pedirle nada a nadie.

---

## 1. Instalar Python 3.13

**Tiene que ser 3.13.** Ni 3.12 ni 3.14. Si ya tenés otra versión instalada,
**no la desinstales**: conviven sin problema.

```powershell
winget install --id Python.Python.3.13 -e
```

En macOS: `brew install python@3.13`.

> ¿Por qué esa y no la última? Porque la biblioteca que maneja el inicio de
> sesión soporta hasta Django 5.2, y Django 5.2 llega hasta Python 3.13. El
> detalle está en [versiones.md](versiones.md).

## 2. Clonar y crear el entorno virtual

```bash
git clone https://github.com/MatiusProg/plat_web_movil_medicos.git
cd plat_web_movil_medicos/backend

py -3.13 -m venv .venv          # Windows
python3.13 -m venv .venv        # macOS / Linux
```

Ahora **activalo**. Esto hay que hacerlo cada vez que abrís una terminal nueva:

```bash
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
```

Sabés que está activado porque el prompt cambia a `(.venv)`. Comprobá:

```bash
python --version                # tiene que decir 3.13.x
```

> Si dice otra versión, el entorno virtual **no** está activado. Es el error
> más común de todos.

## 3. Instalar las dependencias

```bash
pip install -r requirements.txt
```

## 4. Armar tu `.env`

Desde la **raíz** del repositorio (no desde `backend/`):

```bash
cp .env.example .env
```

Ahora generá **tu propia** clave de Django:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Copiá esa salida y pegala en el `.env`, en la línea de `SECRET_KEY`:

```
SECRET_KEY=aqui_va_lo_que_te_imprimio_el_comando
```

**Eso es todo lo que hay que completar.** Las demás líneas ya vienen listas.

Tres cosas importantes:

- **La clave es tuya.** No pidas la de otro ni pases la tuya. Firma tus
  cookies y tus tokens de sesión; compartirla es como compartir la contraseña.
- **El `.env` no se sube.** Está en `.gitignore`. Si alguna vez lo ves en un
  `git status`, avisá antes de commitear.
- **Nadie te va a pasar un `.env` armado.** Cada uno hace el suyo con estos dos
  pasos.

### Los dos errores de formato que rompen el archivo

```bash
SECRET_KEY=abc123              # BIEN
SECRET_KEY = abc123            # MAL: los espacios descartan la línea entera
SECRET_KEY=abc123  # mi clave  # MAL: el comentario se vuelve parte del valor
```

## 5. Levantar la base de datos

Desde la raíz del repositorio, con Docker Desktop abierto:

```bash
docker compose up -d
```

La primera vez descarga la imagen de PostgreSQL; puede tardar un par de
minutos. Verificá que quedó sana:

```bash
docker compose ps
# STATUS tiene que decir: Up (healthy)
```

## 6. Crear las tablas

```bash
cd backend
python manage.py migrate
```

Esto lee las migraciones del repositorio y arma las 14 tablas en tu base. No
copiaste nada de nadie: se construyeron desde el código.

## 7. Comprobar que todo quedó bien

```bash
pytest
```

**Tiene que decir `21 passed`.** Esas 21 son las pruebas de aislamiento entre
organizaciones: verifican que un centro médico no pueda ver los datos de otro.
Si pasan, tu entorno está correcto.

Si querés ver el servidor andando:

```bash
python manage.py runserver
```

Y abrí `http://localhost:8000/api/health/` — debe responder un JSON con
`"status": "ok"`.

---

## El día a día

Cada vez que te sentás a trabajar:

```bash
cd backend
.venv\Scripts\activate          # activar el entorno
git pull                        # traer lo de los demás
python manage.py migrate        # aplicar migraciones nuevas, si las hay
```

**Ese `migrate` después del `pull` es el hábito que evita más dolores de
cabeza.** Si alguien agregó una tabla y vos no migraste, vas a ver errores tipo
*"column does not exist"* que parecen bugs de código pero no lo son.

### Si algo se enreda, empezá de cero

Tu base local es descartable. No tengas miedo:

```bash
docker compose down -v          # borra el volumen y TODOS tus datos locales
docker compose up -d
cd backend && python manage.py migrate
```

Dos minutos y estás igual que el primer día.

---

## Reglas de este sprint

**No corras `makemigrations`.** Los modelos del Sprint 0 ya están hechos y son
la base compartida de las seis historias. Si dos personas generan migraciones
en paralelo, salen dos con el mismo número y chocan al fusionar. Este sprint se
escriben *serializers*, vistas, permisos y pruebas.

Si de verdad creés que necesitás cambiar un modelo, escribilo en el grupo antes
de tocarlo.

**Las pruebas se conectan como `app_user`, nunca como `postgres`.** Ya viene
configurado así; sólo hay que no cambiarlo. `postgres` ignora todas las reglas
de aislamiento, así que las pruebas pasarían sin verificar nada.

---

## Problemas frecuentes

**`python --version` dice 3.14 (o 3.12).**
El entorno virtual no está activado. Corré `.venv\Scripts\activate`. En VS
Code, además: `Ctrl+Shift+P` → *Python: Select Interpreter* → elegí el de
`backend\.venv`.

**`django.db.utils.OperationalError: connection refused`.**
El contenedor no está corriendo. `docker compose up -d` y esperá a que
`docker compose ps` diga *healthy*.

**`port is already allocated` al levantar Docker.**
Tenés otro PostgreSQL ocupando el 5432. Paralo desde los Servicios de Windows,
o cambiá el puerto del tuyo.

**Una consulta devuelve 0 filas y jurás que hay datos.**
Es lo esperado, no un error. Sin contexto de organización, las políticas de
aislamiento devuelven cero en lugar de devolverlo todo. Se resuelve envolviendo
la consulta:

```python
from tenancy.context import tenant_context

with tenant_context(mi_organizacion.id):
    Patient.objects.all()
```

**`pytest` falla al crear la base de pruebas.**
Rehacé el contenedor: `docker compose down -v && docker compose up -d`. El
permiso que necesita se otorga al crear el volumen.

---

## Qué leer según tu historia

| Historia | Quién | Leé antes de empezar |
|---|---|---|
| US-01, US-02 | Alexander, Karen | [modelo-datos/sprint-0.md](../modelo-datos/sprint-0.md) §2, decisión **D-5** — el correo es único por organización, así que el login tiene que resolver la organización **antes** de autenticar |
| US-04 | Michael | §2, decisión **D-4** — nada de `user.has_perm()`; la autorización va por `user.permission_codes()` |
| US-43, US-44 | Luis Mateo, Daniel | §2, decisiones **D-2** y **D-7** |
| US-45 | Luis Miguel | §7.3, riesgo **R-2** — la tarea de métricas no puede leer los datos de los inquilinos, tiene que recorrerlos uno por uno |
