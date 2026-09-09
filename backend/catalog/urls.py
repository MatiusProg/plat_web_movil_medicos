"""Rutas de la app catalog.

Las rutas existentes se conservan para no afectar otras historias.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .branches import BranchListView
from .branch_views import BranchDetailView, BranchDeactivateView
from .search import ProfessionalSearchView
from .us12_views import (
    SpecialtyManageListView,
    SpecialtyDetailView,
    SpecialtyDeactivateView,
    PractitionerManageListView,
    PractitionerDetailView,
    PractitionerDeactivateView,
)

app_name = "catalog"

router = DefaultRouter()

urlpatterns = router.urls + [
    # US-11: gestión de sucursales.
    path("branches/", BranchListView.as_view(), name="branch-list"),
    path("branches/<uuid:pk>/", BranchDetailView.as_view(), name="branch-detail"),
    path(
        "branches/<uuid:pk>/deactivate/",
        BranchDeactivateView.as_view(),
        name="branch-deactivate",
    ),

    # US-12: especialidades.
    path("specialties/", SpecialtyManageListView.as_view(), name="specialty-list"),
    path(
        "specialties/<uuid:pk>/",
        SpecialtyDetailView.as_view(),
        name="specialty-detail",
    ),
    path(
        "specialties/<uuid:pk>/deactivate/",
        SpecialtyDeactivateView.as_view(),
        name="specialty-deactivate",
    ),

    # US-12: administración de profesionales.
    path(
        "professionals/manage/",
        PractitionerManageListView.as_view(),
        name="professional-manage-list",
    ),
    path(
        "professionals/<uuid:pk>/",
        PractitionerDetailView.as_view(),
        name="professional-detail",
    ),
    path(
        "professionals/<uuid:pk>/deactivate/",
        PractitionerDeactivateView.as_view(),
        name="professional-deactivate",
    ),

    # US-16: búsqueda de profesionales (se conserva).
    path(
        "professionals/",
        ProfessionalSearchView.as_view(),
        name="professional-search",
    ),
]