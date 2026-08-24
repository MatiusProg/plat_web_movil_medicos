"""Rutas de la app `tenancy`.

Cada historia agrega su router o su `path` **acá**, nunca en
`config/urls.py`. Ese archivo ya incluye esta app y no hay que volver a
tocarlo: si los seis editaran el mismo archivo, cada pull request traería un
conflicto.

Convención del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.

Está agrupado por historia y con las importaciones separadas a propósito: es
el único archivo de la app que las tres historias tienen que compartir, así
que cada una toca su bloque y no la línea de al lado.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.metrics import IsolationAlertViewSet, dashboard
from .views.organizations import OrganizationViewSet
from .views.plans import (
    OrganizationSubscriptionViewSet,
    SubscriptionPlanViewSet,
    SubscriptionViewSet,
)

app_name = "tenancy"

router = DefaultRouter()

# ---------- US-43 (Luis Mateo): alta de organizaciones --------------------
router.register("organizations", OrganizationViewSet, basename="organization")

# ---------- US-44 (Daniel): planes y suscripciones ------------------------
router.register("plans", SubscriptionPlanViewSet, basename="platform-plan")
router.register(
    "subscriptions", SubscriptionViewSet, basename="platform-subscription",
)

# ---------- US-45 (Luis Miguel): panel del superadministrador -------------
router.register("alerts", IsolationAlertViewSet, basename="alert")


urlpatterns = router.urls + [
    # ---------- US-44 -----------------------------------------------------
    path(
        "organizations/<uuid:organization_id>/subscriptions/",
        OrganizationSubscriptionViewSet.as_view({"get": "list"}),
        name="organization-subscriptions",
    ),
    # ---------- US-45 -----------------------------------------------------
    path("dashboard/", dashboard, name="dashboard"),
]
