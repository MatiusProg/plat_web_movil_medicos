"""Rutas de la app `patients`.

Cada historia agrega su router o su `path` **acá**, nunca en
`config/urls.py`. Ese archivo ya incluye esta app y no hay que volver a
tocarlo: si los seis editaran el mismo archivo, cada pull request traeria un
conflicto.

Convencion del prefijo y de los nombres de ruta en
`docs/convenciones-de-codigo.md`.
"""

from rest_framework.routers import DefaultRouter

from .dependents import DependentViewSet
from .history import PatientHistoryViewSet

app_name = "patients"

router = DefaultRouter()

# ---------- US-07 (SM): pacientes dependientes --------------------------
# El selector compartido de "¿para quién es esta ficha?" cuelga de acá:
# `dependents/patient-options/`. Lo consumen US-08 y la reserva del Sprint 2.
router.register("dependents", DependentViewSet, basename="dependent")

# ---------- US-08 (SM): antecedentes del paciente -----------------------
# `history/highlights/` es la mitad web de la historia: el conjunto vigente que
# el módulo de atención del Sprint 3 muestra al abrir la consulta.
router.register("history", PatientHistoryViewSet, basename="history")

urlpatterns = router.urls
