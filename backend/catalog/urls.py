"""Rutas de la app `catalog`.

Cada historia agrega su router o su `path` **acá**, nunca en `config/urls.py`.
Ese archivo ya incluye esta app.

Convención del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .branches import BranchListView
from .search import ProfessionalSearchView
from .specialties import SpecialtyListView

app_name = "catalog"

router = DefaultRouter()

urlpatterns = router.urls + [
    # ---------- US-11 / US-12 (lectura) ---------------------------------
    path("branches/", BranchListView.as_view(), name="branch-list"),
    path("specialties/", SpecialtyListView.as_view(), name="specialty-list"),

    # ---------- US-16 (Alexander): búsqueda de profesionales ------------
    path("professionals/", ProfessionalSearchView.as_view(),
         name="professional-search"),
]
