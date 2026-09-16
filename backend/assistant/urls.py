"""Rutas de la app `assistant`. US-31, US-32 y US-34.

`config/urls.py` la incluye bajo `/api/assistant/`.

    POST /api/assistant/suggest/   la consulta al asistente
    GET  /api/assistant/status/    si el índice está armado y con qué proveedor

No hay verbos para administrar el índice: lo arma `manage.py embed_catalog`.
Exponerlo por HTTP sería un endpoint que recorre el catálogo entero y llama al
proveedor de embeddings una vez por fragmento, disparable desde una pantalla.
"""

from django.urls import path

from .views import StatusView, SuggestView

app_name = "assistant"

urlpatterns = [
    path("suggest/", SuggestView.as_view(), name="suggest"),
    path("status/", StatusView.as_view(), name="status"),
]
