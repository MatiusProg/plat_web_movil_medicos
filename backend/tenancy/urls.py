"""Rutas de la app `tenancy`.

Cada historia agrega su router o su `path` **acá**, nunca en
`config/urls.py`. Ese archivo ya incluye esta app y no hay que volver a
tocarlo: si los seis editaran el mismo archivo, cada pull request traería un
conflicto.

Convención del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

from tenancy.views import (
    OrganizationSubscriptionViewSet,
    SubscriptionPlanViewSet,
    SubscriptionViewSet,
)


app_name = "tenancy"

router = DefaultRouter()

router.register(
    "plans",
    SubscriptionPlanViewSet,
    basename="platform-plan",
)

router.register(
    "subscriptions",
    SubscriptionViewSet,
    basename="platform-subscription",
)


organization_subscription_list = (
    OrganizationSubscriptionViewSet.as_view({
        "get": "list",
    })
)


urlpatterns = router.urls + [
    path(
        "organizations/<uuid:organization_id>/subscriptions/",
        organization_subscription_list,
        name="organization-subscriptions",
    ),
]