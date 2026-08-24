"""Configuración de Django — Plataforma médica multi-inquilino, Grupo 15.

Requiere Python 3.13 y Django 5.2 LTS. El porqué de esas versiones está en
``docs/entorno/versiones.md``.

Los valores sensibles salen del ``.env`` de la raíz del repositorio, que NO se
versiona. Los predeterminados de este archivo apuntan al contenedor local, de
modo que el proyecto arranca recién clonado sin configurar nada.
"""

from pathlib import Path

import environ

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
    CSRF_TRUSTED_ORIGINS=(list, []),
    DEFAULT_TENANT_ID=(str, ""),
    SECRET_KEY=(str, "clave-insegura-solo-para-desarrollo-local"),
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
    "accounts",
    "catalog",
    "patients",
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
