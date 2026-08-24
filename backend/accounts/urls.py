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

from .views.registration import register_patient

app_name = "accounts"

router = DefaultRouter()

# ---------- US-02 (Karen): inicio de sesión -------------------------------
# Las vistas van en views/auth.py y los serializers en serializers/auth.py.

# ---------- US-04 (Michael): roles y permisos -----------------------------
# Las vistas van en views/roles.py y los serializers en serializers/roles.py.


urlpatterns = router.urls + [
    # ---------- US-01 (Alexander): registro de paciente -------------------
    path("register/", register_patient, name="register"),
]
