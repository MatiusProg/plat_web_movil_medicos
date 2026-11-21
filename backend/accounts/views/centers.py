"""Los centros médicos que se pueden elegir en el login (web y móvil).

Antes el slug se escribía a mano y, por la decisión D-5, el login no dejaba
enumerar organizaciones. El 21/11/26 Luis decidió mostrar una lista
desplegable: es más simple para el paciente y el costo es que cualquiera ve
**qué** clínicas usan el sistema. Por eso sale sólo lo mínimo para elegir:
el nombre comercial y el slug (que el login ya pedía). Nada de NIT, correo,
plan ni estado.

Sólo las **activas**, las mismas que `app_resolve_tenant` deja entrar: una
suspendida o dada de baja no aparece, así que la lista se actualiza sola con
las altas y las bajas.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from tenancy.context import platform_admin_context
from tenancy.models import Organization


@api_view(["GET"])
@permission_classes([AllowAny])
def centers(request):
    # Sin sesión no hay contexto, y la política de `organizations` no deja ver
    # ninguna fila: se lee como plataforma, sólo estas dos columnas.
    with platform_admin_context():
        filas = list(
            Organization.objects.filter(status=Organization.Status.ACTIVE)
            .order_by("name", "slug")
            .values("slug", "name")
        )
    return Response(filas)
