"""Rutas de la app `accounts`.

Cada historia agrega su router o su `path` **acá**, nunca en
`config/urls.py`. Ese archivo ya incluye esta app y no hay que volver a
tocarlo: si los seis editaran el mismo archivo, cada pull request traería un
conflicto.

Convención del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.

Está agrupado por historia y con las importaciones separadas a propósito: es
el único archivo de la app que las tres historias comparten, así que cada una
toca su bloque y no la línea de al lado.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.auth import login, logout, refresh
from .views.password_reset import confirm_reset, request_reset, verify_reset
from .views.registration import register_patient
from .views.roles import (
    AssignableUserViewSet,
    PermissionViewSet,
    RoleViewSet,
    UserRoleViewSet,
)

app_name = "accounts"

router = DefaultRouter()

# ---------- US-02 (Karen): inicio de sesión -------------------------------
# Las vistas van en views/auth.py y los serializers en serializers/auth.py.

# ---------- US-04 (Karen): roles y permisos -------------------------------
# Las vistas van en views/roles.py y los serializers en serializers/roles.py.
# US-04 pasó a Karen en el reparto del Sprint 1 (docs/sprints/sprint-1/).
#
# `users` queda registrado acá con el listado de sólo lectura que necesita la
# pantalla de asignación. Su ruta de detalle sólo acepta un UUID, así que
# `users/me/` sigue libre para US-05.
router.register("permissions", PermissionViewSet, basename="permission")
router.register("roles", RoleViewSet, basename="role")
router.register("users", AssignableUserViewSet, basename="user")
router.register("user-roles", UserRoleViewSet, basename="user_role")


urlpatterns = router.urls + [
    # ---------- US-01 (Alexander): registro de paciente -------------------
    path("register/", register_patient, name="register"),

    # ---------- US-02 (Karen): inicio de sesión ---------------------------
    path("login/", login, name="login"),
    path("token/refresh/", refresh, name="token-refresh"),
    path("logout/", logout, name="logout"),

    # ---------- US-03 (Karen): recuperación de contraseña -----------------
    # Las vistas van en views/password_reset.py y los serializers en
    # serializers/password_reset.py. La política de complejidad, compartida
    # con US-05, está en accounts/passwords.py.
    path("password-reset/", request_reset, name="password-reset"),
    path("password-reset/verify/", verify_reset, name="password-reset-verify"),
    path("password-reset/confirm/", confirm_reset, name="password-reset-confirm"),
]
