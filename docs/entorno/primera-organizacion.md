# Entrar por primera vez y registrar una organización

De la base recién migrada a estar dentro del sistema, con una organización
propia contra la cual probar. Son cinco minutos y se hace **una vez por
máquina**.

> Antes de esto tenés que haber completado [primeros-pasos.md](primeros-pasos.md)
> hasta el punto 7 —entorno armado, base levantada, `migrate` corrido y las
> pruebas en verde—.

---

## El problema del huevo y la gallina

Vale la pena entenderlo, porque explica el orden de los pasos y por qué no se
puede empezar por donde uno esperaría:

- Para **registrar una organización** hay que iniciar sesión como
  Superadministrador de Plataforma (US-43, sólo él puede).
- El Superadministrador **no se registra desde la aplicación**: no hay
  pantalla que lo cree, y no debería haberla — sería un formulario público
  para fabricarse permisos de plataforma.
- Se crea por consola, una sola vez, y de ahí en adelante todo lo demás sale
  de la aplicación.

---

## 1. Crear tu Superadministrador de Plataforma

```bash
cd backend
.venv/Scripts/python manage.py createsuperuser      # Windows
.venv/bin/python manage.py createsuperuser          # macOS / Linux
```

Te va a pedir correo, nombres, apellidos, documento y contraseña. **Es tu
máquina y tu base**, así que poné lo que quieras y anotalo — se usa en cada
inicio de sesión.

```
Email: super@plataforma.local
First name: Tu
Last name: Nombre
Document number: 0000001
Password: ********
```

> **Si te da `new row violates row-level security policy for table "users"`**,
> tu rama no tiene el comando corregido: hacé `git pull origin main`. El
> `createsuperuser` de Django inserta sin contexto de inquilino, y RLS lo
> rechaza; `accounts` lo sobrescribe para fijar el contexto de plataforma.

---

## 2. Levantar las dos mitades

Cada una en su terminal, las dos al mismo tiempo:

```bash
# Terminal 1 — backend
cd backend
.venv/Scripts/python manage.py runserver

# Terminal 2 — frontend
cd frontend
npm install          # sólo la primera vez
npm run dev
```

El frontend queda en <http://localhost:5173> y el backend en
<http://localhost:8000>. El frontend le pega al backend por `VITE_API_BASE_URL`,
que ya viene apuntando a `localhost:8000` — si querés cambiarlo, copiá
`frontend/.env.example` a `frontend/.env.local`.

---

## 3. Entrar como Superadministrador

En <http://localhost:5173/ingresar>:

| Campo | Qué poner |
|---|---|
| **Organización** | **vacío** |
| Correo | el del paso 1 |
| Contraseña | la del paso 1 |

**El campo de organización va vacío a propósito.** El Superadministrador no
pertenece a ningún centro médico —un `CHECK` de la base lo garantiza—, así
que dejarlo en blanco es lo que le dice al backend que estás intentando entrar
a nivel plataforma.

---

## 4. Registrar tu organización

En el menú de arriba aparece **Organizaciones** (sólo la ve el
Superadministrador). Entrá y tocá **Registrar organización**.

El formulario pide dos cosas:

- **El centro médico** — nombre, razón social, NIT, correo, y el
  **identificador**: eso es lo que vos y los demás van a escribir en el campo
  "Organización" al iniciar sesión. Minúsculas, números y guiones; poné algo
  corto y fácil de tipear, como `demo` o `kolping`.
- **Su primer administrador** — la persona que va a manejar ese centro
  médico. No le ponés contraseña: la genera el sistema.

Al guardar, el sistema crea **en una sola transacción** la organización, su
suscripción al plan elegido, las cuatro plantillas de rol copiadas adentro
del nuevo inquilino, y ese primer usuario administrador con su rol.

### La contraseña temporal se muestra UNA sola vez

La pantalla que aparece después del alta trae la contraseña del administrador.
**Copiala en ese momento.** No queda guardada en ningún lado —en la base sólo
está su hash— y no hay forma de volver a consultarla. Si se pierde, hay que
registrar otra organización o restablecer la contraseña por la base.

---

## 5. Entrar como esa organización

Cerrá sesión y volvé a entrar, ahora con:

| Campo | Qué poner |
|---|---|
| **Organización** | el identificador que elegiste (ej. `demo`) |
| Correo | el del administrador que creaste |
| Contraseña | la temporal que copiaste |

Y listo: estás dentro de un inquilino, con sus datos aislados de cualquier
otro. Ésa es la cuenta con la que vas a probar tu historia.

---

## 6. Dejarlo anotado en tu `.env`

El `.env` tiene una variable para trabajar cómodo en desarrollo:

```env
DEFAULT_TENANT_ID=<el uuid de tu organización>
```

El uuid sale de la lista de organizaciones, o de:

```bash
docker compose exec db psql -U app_user -d plataforma \
  -c "SELECT id, slug, name FROM organizations;"
```

> Es **tu** uuid, distinto del de cada compañero: cada uno tiene su propia
> base local. No lo compartas ni lo copies del de otro.

---

## Preguntas que van a aparecer

**¿Cada uno crea su propia organización?** Sí. Cada máquina tiene su base
PostgreSQL, así que lo que registres vos no existe para los demás. Es a
propósito: nadie rompe los datos de nadie.

**¿Puedo crear varias?** Todas las que quieras, y conviene: con dos
organizaciones podés comprobar de verdad que una no ve los datos de la otra,
que es el criterio 4 de la Definición de Terminado.

**¿Y si el superadministrador no ve los usuarios de la organización que
acaba de crear?** Es correcto y es deliberado (decisión **D-3**): el
Superadministrador administra la plataforma, no los datos de los inquilinos.
Lo hace cumplir la base con RLS, no la aplicación. Hasta hay una prueba que lo
verifica.

**¿Por qué mi usuario aparece sin roles ni permisos en el panel?** Si sos el
Superadministrador, es lo esperado: `user_roles` está aislada por organización
y sus filas irían con organización NULL, que nunca compara verdadero — así que
no puede tener roles asignados. Sus permisos se resuelven por el indicador
`is_platform_admin`, no por la tabla de roles.
