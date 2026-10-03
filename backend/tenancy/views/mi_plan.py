"""``GET /api/platform/my-plan/`` — qué incluye el plan de mi centro médico.

Lo usa la interfaz para no ofrecer lo que el plan no incluye: si el centro
tiene plan Básico, el menú no muestra el asistente. **Esconder no autoriza
nada**: la puerta real la pone el backend en cada endpoint
(``tenancy/plans.py``). Esto es sólo para que nadie toque un botón que después
le diga que no.

Cualquier usuario de una organización lo puede leer: el plan del centro no es
un secreto para quien trabaja o se atiende en él, y sin esto la interfaz no
sabe qué mostrar. No expone precios ni nada de la suscripción.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..plans import current_plan


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mi_plan(request):
    plan = current_plan(getattr(request.user, "organization", None))
    if plan is None:
        return Response({"code": None, "name": None, "features": {}})
    return Response({
        "code": plan.code,
        "name": plan.name,
        # Sólo las funciones (sí/no y frecuencias), no los topes numéricos.
        "features": plan.features or {},
    })
