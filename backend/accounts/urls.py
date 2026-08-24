"""Rutas de la app `accounts`.

Cada historia agrega su router o su `path` **acá**, nunca en
`config/urls.py`. Ese archivo ya incluye esta app y no hay que volver a
tocarlo: si los seis editaran el mismo archivo, cada pull request traeria un
conflicto.

Convencion del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import register_patient

app_name = "accounts"

router = DefaultRouter()
# router.register("recurso", RecursoViewSet, basename="recurso")

urlpatterns = [
    path("register/", register_patient, name="register"),
] + router.urls
