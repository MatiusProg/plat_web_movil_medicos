"""Rutas de la app assistant.

US-32 (consultas administrativas) reutiliza ``suggest/``: amplía el corpus,
no agrega ruta de consulta. Sí agrega ``reindex/``, para que lo que se carga
en la pantalla de servicios llegue al asistente. Las rutas nuevas van acá y
no en ``config/urls.py``, que está cerrado.
"""

from django.urls import path

from .booking_views import BookView, SlotsView
from .reindex_views import ReindexView
from .views import SuggestView

app_name = "assistant"

urlpatterns = [
    # US-31: sugerencia de especialidad por síntomas.
    path("suggest/", SuggestView.as_view(), name="suggest"),
    # US-32: reindexar el catálogo de la propia organización.
    path("reindex/", ReindexView.as_view(), name="reindex"),
    # US-33: turnos que se ofrecen en la conversación, y la reserva del que
    # el paciente confirmó.
    path("slots/", SlotsView.as_view(), name="slots"),
    path("book/", BookView.as_view(), name="book"),
]
