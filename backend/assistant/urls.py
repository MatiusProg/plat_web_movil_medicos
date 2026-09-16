"""Rutas de la app assistant.

US-32 (consultas administrativas) reutiliza este mismo endpoint: amplía el
corpus, no agrega ruta. Si aparece una segunda, se agrega acá y no en
``config/urls.py``, que está cerrado.
"""

from django.urls import path

from .views import SuggestView

app_name = "assistant"

urlpatterns = [
    # US-31: sugerencia de especialidad por síntomas.
    path("suggest/", SuggestView.as_view(), name="suggest"),
]
