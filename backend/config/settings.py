"""Configuración de Django — Plataforma médica multi-inquilino, Grupo 15.

Requiere Python 3.13 y Django 5.2 LTS. El porqué de esas versiones está en
``docs/entorno/versiones.md``.

Los valores sensibles salen del ``.env`` de la raíz del repositorio, que NO se
versiona. Los predeterminados de este archivo apuntan al contenedor local, de
modo que el proyecto arranca recién clonado sin configurar nada.
"""

from pathlib import Path

import environ
from corsheaders.defaults import default_headers

# backend/config/settings.py -> backend/ -> raíz del repositorio
BASE_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE_DIR.parent

env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://localhost:3000"]),
    DATABASE_URL=(
        str, "postgresql://app_user:app_local_pass@localhost:5432/plataforma"
    ),
    DB_SEARCH_PATH=(str, "public,extensions"),  # D-18, ver más abajo
    CSRF_TRUSTED_ORIGINS=(list, []),
    DEFAULT_TENANT_ID=(str, ""),
    SECRET_KEY=(str, "clave-insegura-solo-para-desarrollo-local"),
    # US-31 — asistente. Los proveedores arrancan en `local` a propósito: es
    # la misma idea que el resto de este bloque, que un clon recién bajado
    # funcione sin configurar nada ni tener ninguna clave.
    GEMINI_API_KEY=(str, ""),
    ASSISTANT_EMBEDDING_PROVIDER=(str, "local"),
    ASSISTANT_EMBEDDING_MODEL=(str, "gemini-embedding-001"),
    ASSISTANT_CHAT_PROVIDER=(str, "local"),
    # `-lite` y no el flash grande: medido el 16/09, `gemini-3.5-flash`
    # contesta 503 "high demand" en el nivel gratuito —cinco de cinco
    # intentos— y `gemini-3.5-flash-lite` responde en 0,8 s. El endpoint
    # degrada solo a `plantilla` cuando el modelo no está, así que esto no
    # rompe nada; sólo decide si la demostración se ve redactada o armada.
    ASSISTANT_CHAT_MODEL=(str, "gemini-3.5-flash-lite"),
    ASSISTANT_MIN_SIMILARITY=(float, -1.0),
)
environ.Env.read_env(REPO_ROOT / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# UUID de la organización con la que se trabaja en desarrollo.
DEFAULT_TENANT_ID = env("DEFAULT_TENANT_ID") or None


# --------------------------------------------------------------------------
#  Aplicaciones
# --------------------------------------------------------------------------
INSTALLED_APPS = [
    # `accounts` va ANTES que django.contrib.auth a propósito: Django resuelve
    # los comandos de `manage.py` con el orden de esta lista, y `accounts`
    # sobrescribe `createsuperuser` para fijar el contexto de plataforma —sin
    # el cual RLS rechaza la fila—. Si se mueve más abajo, gana el comando de
    # Django y crear el primer superadministrador vuelve a fallar.
    "accounts",
    "django.contrib.contenttypes",
    # django.contrib.auth se instala por AbstractBaseUser y los hashers de
    # contraseña. Su sistema de permisos NO se usa: `auth_permission` y
    # `auth_group` no están aislados por inquilino. La autorización va por
    # accounts.UserRole -> accounts.RolePermission.
    "django.contrib.auth",
    "django.contrib.staticfiles",
    "rest_framework",
    # CU4 (cerrar sesión): permite invalidar un refresh token antes de que
    # expire. Sin esta app, BLACKLIST_AFTER_ROTATION no tiene efecto.
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "tenancy",
    "catalog",
    "patients",
    "scheduling",
    # US-06: la bitácora. No trae modelos —lee `accounts.AuditLog`—, pero es
    # una app igual porque tiene su propio prefijo de rutas, su permiso y su
    # middleware.
    "audit",
    # Característica general 5 de la materia: reportes que arma el usuario,
    # con sus columnas, sus criterios y su orden, exportables a Excel, PDF,
    # HTML y correo.
    "reporting",
    # Característica general 6: copias de seguridad y restauración.
    "backups",
    # US-31: el asistente. Guarda los fragmentos del catálogo con su embedding
    # en una columna `vector` de pgvector.
    "assistant",
]

# Sin AuthenticationMiddleware ni SessionMiddleware: esto es una API pura con
# JWT, no hay sesiones de navegador. AuthenticationMiddleware, además, exige
# SessionMiddleware y dejaría un request.user siempre anónimo que invita a
# construir el aislamiento sobre algo que nunca se completa.
#
# La autenticación la hace DRF dentro de la vista, con
# accounts.authentication.TenantJWTAuthentication, que es también donde se
# fija el contexto de inquilino.
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Sirve los estáticos desde el propio proceso. Va justo detrás de
    # SecurityMiddleware y por delante de todo lo demás, como pide su
    # documentación: así una petición de un archivo estático se resuelve sin
    # atravesar el resto de la cadena —incluido TenantMiddleware, que abriría
    # una transacción para servir un CSS—.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    # US-06 (c). Va ANTES que TenantMiddleware y no después, aunque escriba lo
    # último: Django llama a `process_response` en orden inverso al de esta
    # lista, así que estar arriba es lo que lo hace correr DESPUÉS de que
    # TenantMiddleware cerró la transacción de la petición. Ésa es toda la
    # gracia: un asiento escrito dentro de la transacción se pierde cuando DRF
    # llama a `set_rollback()` al manejar un rechazo, que es justo lo que más
    # interesa auditar. Moverlo debajo no rompe ninguna prueba de camino feliz
    # y apaga la mitad de la bitácora.
    "audit.middleware.AuditTrailMiddleware",
    # Abre la transacción de la petición y resuelve el inquilino por slug para
    # las peticiones sin autenticar (el login). Sin este middleware, toda
    # consulta sobre una tabla con RLS devuelve cero filas.
    "tenancy.middleware.TenantMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]


# --------------------------------------------------------------------------
#  Base de datos
# --------------------------------------------------------------------------
#  Django se conecta SIEMPRE como app_user, nunca como postgres. El rol
#  postgres tiene BYPASSRLS: con él, las pruebas de aislamiento pasan siempre
#  sin verificar nada. Ver el punto 1 del README.
DATABASES = {
    "default": env.db_url("DATABASE_URL"),
}
DATABASES["default"]["ATOMIC_REQUESTS"] = False  # lo maneja TenantMiddleware
DATABASES["default"].setdefault("OPTIONS", {})

# --------------------------------------------------------------------------
#  `search_path` de la conexión — D-18
# --------------------------------------------------------------------------
#  **Supabase instala pgvector en el esquema `extensions`, no en `public`.** El
#  tipo `vector` sólo se resuelve si ese esquema está en el `search_path`, y si
#  no lo está la migración del asistente falla con un error que no lo menciona:
#
#      django.db.utils.ProgrammingError: type "vector" does not exist
#
#  Hasta ahora eso dependía de un `ALTER ROLE app_user SET search_path = public,
#  extensions` corrido a mano en el panel de Supabase —documentado en
#  `docs/entorno/supabase.md`, pero fuera del repositorio—. Un ajuste que vive
#  sólo en la base no se revisa en un pull request, no viaja con el código y no
#  sobrevive a recrear el rol o a conectarse con otro: por eso la conexión lo
#  fija por su cuenta.
#
#  Un esquema que no existe en el `search_path` **no es un error** en
#  PostgreSQL: simplemente se ignora. Por eso la misma línea sirve en local,
#  donde la extensión está en `public` y no hay esquema `extensions`.
#
#  `setdefault` y no asignación: si el `DATABASE_URL` ya trae su propio
#  `?options=`, manda el de la URL.
#  Va por dos caminos a propósito. El parámetro de conexión es el correcto y
#  alcanza contra PostgreSQL directo; pero el *pooler* de Supabase (Supavisor,
#  puerto 6543) puede ignorar los parámetros de arranque del cliente, y entonces
#  esto no haría nada y el error sería idéntico. El segundo camino
#  —`tenancy.apps`, que lo fija con un `SET` sobre cada conexión ya abierta— no
#  depende de eso. Repetirlo no cuesta nada; que falte, cuesta un despliegue.
DB_SEARCH_PATH = env("DB_SEARCH_PATH")
DATABASES["default"]["OPTIONS"].setdefault(
    "options", f"-c search_path={DB_SEARCH_PATH}",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --------------------------------------------------------------------------
#  Autenticación
# --------------------------------------------------------------------------
#  AUTH_USER_MODEL no se puede cambiar después de la primera migración sin
#  borrar la base. Está decidido y no se toca.
AUTH_USER_MODEL = "accounts.User"

# auth.E003 exige que el USERNAME_FIELD sea único de forma global. Acá el
# correo es único POR ORGANIZACIÓN (decisión D-5): la misma persona puede ser
# paciente en dos centros médicos, y con un único global el segundo registro
# fallaría.
#
# La advertencia existe porque el backend de autenticación estándar hace
# `User.objects.get(email=...)`, que con correos repetidos entre inquilinos
# lanzaría MultipleObjectsReturned. Por eso la autenticación de este proyecto
# resuelve SIEMPRE la organización primero:
#
#     1. el middleware resuelve el inquilino por slug y fija app.tenant_id,
#     2. RLS deja visibles únicamente los usuarios de esa organización,
#     3. recién ahí se busca el correo — que dentro del inquilino sí es único.
#
# Consecuencia para US-02: NO se puede usar `django.contrib.auth.authenticate`
# sin un backend propio que filtre por organización. Silenciar esta
# comprobación sin cumplir ese contrato produce un error intermitente que sólo
# aparece cuando dos inquilinos comparten un correo.
SILENCED_SYSTEM_CHECKS = ["auth.E003"]

# RNF-04: contraseñas con hash y salt. Argon2 primero por ser el algoritmo
# recomendado hoy; los demás quedan para poder verificar hashes antiguos.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# RNF-07: bloqueo temporal tras 5 intentos fallidos.
LOGIN_MAX_FAILED_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

# US-15: tope de días que se pueden pedir de disponibilidad de una vez, para
# que nadie pida un año entero. Pasado el tope, el endpoint responde 400.
AVAILABILITY_MAX_HORIZON_DAYS = env.int("AVAILABILITY_MAX_HORIZON_DAYS", default=30)

# US-07 (g): tope de dependientes por titular. Es configurable y no una
# constante porque el número correcto depende del centro médico —una familia
# numerosa es normal, cien dependientes es alguien inflando el padrón—, y
# porque sin tope el alta de pacientes queda abierta desde una cuenta común.
PATIENT_MAX_DEPENDENTS = env.int("PATIENT_MAX_DEPENDENTS", default=10)

# US-07 (f): a partir de qué edad un dependiente puede pasar a titular. Es la
# mayoría de edad en Bolivia.
PATIENT_MAJORITY_AGE = env.int("PATIENT_MAJORITY_AGE", default=18)


# --------------------------------------------------------------------------
#  API
# --------------------------------------------------------------------------
REST_FRAMEWORK = {
    # NO usar rest_framework_simplejwt.authentication.JWTAuthentication a
    # secas: no fija el contexto de inquilino, y sin contexto la propia
    # búsqueda del usuario devuelve cero filas por RLS ("User not found").
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "accounts.authentication.TenantJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

# RNF-06: expiración configurable y renovación segura.
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,   # lo hace la vista de login, junto al registro
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")

# El login resuelve el inquilino por el encabezado `X-Organization` (ver
# tenancy/middleware.py). No viene en la lista por omisión de django-cors-headers,
# y sin declararlo el navegador rechaza la petición en el preflight —antes de
# que salga—. Las pruebas no lo detectan: el cliente de Django no hace preflight.
CORS_ALLOW_HEADERS = (*default_headers, "x-organization")


# --------------------------------------------------------------------------
#  Correo — US-03, el enlace de restablecimiento
# --------------------------------------------------------------------------
#  En desarrollo el correo se imprime en la consola: no hace falta configurar
#  ningún SMTP para probar el flujo completo, y el enlace queda a la vista en
#  la terminal donde corre `runserver`. En producción se define EMAIL_BACKEND
#  en el `.env` junto con las credenciales del proveedor.
#
#  Las pruebas no usan nada de esto: Django reemplaza el backend por uno en
#  memoria y `mail.outbox` deja ver lo que se habría mandado.
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="no-responder@centromedico.test",
)

# Dónde vive el frontend, para armar el enlace del correo. No se deduce de la
# petición: el enlace lo abre un navegador contra la aplicación web, no contra
# la API, y en producción son dos dominios distintos.
FRONTEND_BASE_URL = env(
    "FRONTEND_BASE_URL", default="http://localhost:5173",
).rstrip("/")


# --------------------------------------------------------------------------
#  Internacionalización
# --------------------------------------------------------------------------
LANGUAGE_CODE = "es-bo"
# Se guarda todo en UTC y se convierte a la zona de cada organización
# (Organization.timezone) al presentarlo.
TIME_ZONE = "America/La_Paz"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# Donde `collectstatic` deja los archivos para que WhiteNoise los sirva. En
# local no hace falta correrlo: con DEBUG=True Django los sirve solo.
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Comprime y agrega un hash al nombre de cada archivo, para poder
        # cachearlos sin límite. Si un archivo referencia a otro que no existe,
        # `collectstatic` falla en el despliegue en vez de servir un 404 en
        # producción.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# --------------------------------------------------------------------------
#  Seguridad en producción
# --------------------------------------------------------------------------
# La API es **sin estado**: autentica por JWT en el encabezado, no por cookie
# de sesión, así que no hay CSRF que proteger y `CsrfViewMiddleware` no está
# en la cadena. Es la razón del aviso security.W003 de `check --deploy`, y es
# deliberado.
#
# Esta variable queda declarada igual, vacía por omisión, porque el día que
# alguien agregue una vista con sesión —el panel de administración de Django,
# que hoy ni siquiera está instalado— detrás del proxy HTTPS de Railway, los
# POST van a fallar con "CSRF verification failed" y el motivo no es evidente.
# Con la variable ya en su lugar, se resuelve poniendo el dominio:
#     CSRF_TRUSTED_ORIGINS=https://<tu-servicio>.up.railway.app
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

if not DEBUG:
    # RNF-05: toda comunicación por HTTPS/TLS.
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}


# --------------------------------------------------------------------------
#  US-31 — Asistente de orientación (RAG sobre pgvector)
# --------------------------------------------------------------------------
# La clave del proveedor **no se versiona** (regla 11 del Sprint 2): va en el
# .env, y en Railway con el botón de aplicar cambios, no con Redeploy.
GEMINI_API_KEY = env("GEMINI_API_KEY")

# "gemini" o "local". El proveedor local es determinista y no sale a la red:
# es el que deja correr las pruebas y la demostración sin clave y sin
# conexión. El porqué está en assistant/embeddings.py.
ASSISTANT_EMBEDDING_PROVIDER = env("ASSISTANT_EMBEDDING_PROVIDER")
ASSISTANT_EMBEDDING_MODEL = env("ASSISTANT_EMBEDDING_MODEL")
ASSISTANT_CHAT_PROVIDER = env("ASSISTANT_CHAT_PROVIDER")
ASSISTANT_CHAT_MODEL = env("ASSISTANT_CHAT_MODEL")

# Similitud mínima para que un fragmento cuente como recuperado. Por debajo,
# el asistente contesta que no sabe en lugar de sugerir la especialidad menos
# lejana, que con cinco especialidades siempre existe.
#
# El valor depende del proveedor —los dos espacios no tienen la misma escala—
# así que -1 significa "elegilo vos según el proveedor". Fijar la variable en
# el .env gana siempre.
#
# El 0,12 del proveedor local está medido sobre el catálogo de demostración:
# las preguntas que sí corresponden a una especialidad puntúan entre 0,15 y
# 0,55, y una pregunta ajena ("cuánto sale alquilar un departamento") llega a
# 0,105. El margen es de tres centésimas, y eso es una propiedad del método,
# no un defecto de la calibración: comparar por palabras compartidas no
# separa mucho mejor que eso.
#
# **El 0,62 de Gemini está medido, y desmiente lo que decía este comentario.**
# Acá se afirmaba que con Gemini el hueco era holgado y que el umbral se podía
# poner alto sin miedo; el valor puesto era 0,35, escrito sin medir. Medición
# del 16/09 sobre `morita2` con `gemini-embedding-001`, 17 preguntas:
#
#     preguntas del catálogo   0,637 – 0,762   (10 preguntas)
#     preguntas ajenas         0,518 – 0,608   ( 7 preguntas)
#
# El hueco real es de **0,029**, casi el mismo que el del proveedor local: los
# espacios de Gemini no separan más, puntúan más alto todo. Con 0,35, "cuánto
# sale alquilar un departamento" recuperaba Medicina general con 0,55 y el
# asistente contestaba con una especialidad — exactamente lo que este umbral
# existe para impedir, y lo que se muestra en el punto (c) de la demostración.
#
# Un margen de tres centésimas es estrecho: al cambiar el corpus o el modelo
# hay que volver a medirlo, no heredarlo. El procedimiento es el del script de
# medición: preguntas que sí tienen especialidad contra preguntas ajenas, y el
# umbral al medio del hueco.
_umbral = env("ASSISTANT_MIN_SIMILARITY")
ASSISTANT_MIN_SIMILARITY = (
    _umbral if _umbral >= 0
    else (0.12 if ASSISTANT_EMBEDDING_PROVIDER == "local" else 0.62)
)
