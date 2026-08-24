# Despliegue — Railway y Supabase

El backend corre en **Railway** y la base en **Supabase**. El frontend es un
sitio estático y va aparte.

> **Por qué desplegar temprano y con poco.** El primer despliegue siempre falla,
> y falla por cosas del entorno que no se ven leyendo código: una variable mal
> escrita, un dominio que falta, `collectstatic` que revienta, CORS que rechaza
> el origen de producción. Descubrirlo con seis endpoints cuesta una tarde;
> descubrirlo la noche anterior a la defensa cuesta la defensa.

---

## Lo que ya está resuelto en el repositorio

| Archivo | Qué hace |
|---|---|
| `scripts/start.sh` | migra, recolecta estáticos y levanta gunicorn |
| `Procfile` · `railway.json` | le dicen a Railway que use ese script |
| `requirements.txt` | `gunicorn` y `whitenoise` |
| `config/settings.py` | `STATIC_ROOT`, WhiteNoise, `CSRF_TRUSTED_ORIGINS`, HTTPS y HSTS bajo `DEBUG=False` |

Está **probado en local con `DEBUG=False`**: `collectstatic` procesa los
archivos, `check --deploy` queda limpio salvo dos avisos deliberados, y la API
responde correctamente detrás de un proxy simulado. Lo único que no se puede
probar acá es gunicorn: **no corre en Windows** (necesita `fcntl`), sólo en el
contenedor Linux de Railway.

---

## 1. Primero Supabase, después Railway

Sin base no hay nada que desplegar. El paso a paso está en
[supabase.md](supabase.md); en resumen:

1. Crear el proyecto y anotar la contraseña del rol `postgres`.
2. Crear el rol `app_user` con `NOBYPASSRLS` y darle el esquema.
3. Correr `manage.py migrate` apuntando a Supabase, **como `app_user`**.

El punto 3 no es un detalle: las tablas quedan siendo de quien corre las
migraciones, y las políticas llevan `FORCE ROW LEVEL SECURITY` justamente para
que el dueño no quede exento de sus propias reglas. Si se migra como
`postgres`, el aislamiento entre organizaciones **no se aplica** y no hay
ningún error que lo avise.

---

## 2. Las variables en Railway

```env
DEBUG=False
SECRET_KEY=<50+ caracteres al azar>
ALLOWED_HOSTS=<tu-servicio>.up.railway.app
CSRF_TRUSTED_ORIGINS=https://<tu-servicio>.up.railway.app
CORS_ALLOWED_ORIGINS=https://<donde-este-el-frontend>
DATABASE_URL=postgresql://app_user.<REF>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres
```

Para la clave:

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Cuatro cosas que cuestan una tarde si no se saben:

- **`CORS_ALLOWED_ORIGINS` lleva el origen completo, con `https://` y sin barra
  final.** Si no coincide exactamente, el navegador rechaza cada petición del
  frontend y en el servidor no aparece ningún error.
- **`ALLOWED_HOSTS` va sin esquema**; `CSRF_TRUSTED_ORIGINS`, con esquema.
  Es la confusión más frecuente entre las dos.
- **La contraseña del `DATABASE_URL` es la de `app_user`, no la de
  `postgres`.** El usuario que aparece en la URL es el que manda.
- **Cambiar `SECRET_KEY` invalida todos los tokens emitidos.** Si en medio de
  la demostración alguien la rota, a todos se les cierra la sesión. Se fija una
  vez y no se toca.

---

## 3. El superadministrador de producción

**No viaja desde tu máquina.** Tu base local y Supabase son bases distintas: la
cuenta que usás para probar no existe allá. Hay que crear una **contra
Supabase**, una sola vez.

Desde la consola de Railway, con el servicio ya desplegado:

```bash
python backend/manage.py createsuperuser
```

O desde tu máquina, apuntando `DATABASE_URL` a Supabase por un rato.

> **Una sola cuenta, compartida, no seis.** Es el entorno de la demostración:
> seis superadministradores creando organizaciones de prueba sobre la misma
> base es exactamente cómo se llega a la defensa con datos basura. La
> contraseña se pasa **por fuera del repositorio** — nunca en un commit, ni en
> el `.env.example`, ni en un comentario del pull request. GitHub tiene *push
> protection* activo, y si algo se filtra hay que **rotar la credencial**, no
> borrar el commit: el historial lo conserva.

Con ese usuario se entra a la aplicación desplegada y se registra la primera
organización, igual que en local ([primera-organizacion.md](primera-organizacion.md)).

---

## 4. El frontend

Es un sitio estático: `npm run build` deja todo en `frontend/dist`. Puede ir en
Railway como un servicio aparte, o en Vercel o Netlify, que para un sitio
estático son más simples y gratuitos.

Necesita **una** variable, en tiempo de compilación:

```env
VITE_API_BASE_URL=https://<tu-servicio>.up.railway.app/api
```

Vite incrusta el valor al compilar, así que **cambiarla exige recompilar**: no
alcanza con editarla en el panel y reiniciar.

Y su origen tiene que estar en `CORS_ALLOWED_ORIGINS` del backend. Son dos
variables que se apuntan mutuamente, y es donde falla el primer intento de
todos.

---

## 5. Comprobar que quedó bien

```bash
# 1. Responde y rechaza sin token
curl -i https://<tu-servicio>.up.railway.app/api/platform/organizations/   # 401

# 2. El login funciona
curl -X POST https://<tu-servicio>.up.railway.app/api/accounts/login/ \
     -H 'Content-Type: application/json' \
     -d '{"organizacion":"","email":"<superadmin>","password":"<clave>"}'   # 200

# 3. CORS acepta el origen del frontend
curl -i -X OPTIONS https://<tu-servicio>.up.railway.app/api/accounts/login/ \
     -H 'Origin: https://<donde-este-el-frontend>' \
     -H 'Access-Control-Request-Method: POST'   # debe traer access-control-allow-origin
```

Y la comprobación que de verdad importa, la del criterio 4 de la Definición de
Terminado: registrar **dos** organizaciones, entrar con el administrador de
una y verificar que no ve absolutamente nada de la otra.

---

## Los dos avisos de `check --deploy` que quedan, y por qué

**`security.W003` — falta `CsrfViewMiddleware`.** Es deliberado: la API es sin
estado y autentica por JWT en el encabezado, no por cookie de sesión. No hay
CSRF que proteger porque no hay nada que el navegador adjunte solo.

**`security.W021` — falta `SECURE_HSTS_PRELOAD`.** El *preload* sirve para
inscribir un dominio propio en la lista que traen los navegadores. El dominio
es `up.railway.app`, que no es nuestro, así que activarlo no haría nada.

---

## Problemas frecuentes

| Síntoma | Causa casi segura |
|---|---|
| `DisallowedHost` | falta el dominio en `ALLOWED_HOSTS` |
| El frontend no recibe respuesta y la consola dice CORS | el origen no está en `CORS_ALLOWED_ORIGINS`, o le sobra la barra final |
| Todo redirige a HTTPS en un bucle | el proxy no manda `X-Forwarded-Proto`; se resuelve con `SECURE_PROXY_SSL_HEADER`, que ya está puesto |
| `collectstatic` falla en el despliegue | un archivo estático referencia a otro que no existe. Es a propósito que falle: mejor que no levante a que sirva un 404 en la demostración |
| Toda consulta devuelve cero filas | se migró como `postgres` en vez de `app_user`, o falta el contexto de inquilino |
| "User not found" al iniciar sesión con un token válido | el token se firmó con otra `SECRET_KEY` |
