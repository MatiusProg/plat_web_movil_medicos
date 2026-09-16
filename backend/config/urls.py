"""Rutas del proyecto.

Sin ``django.contrib.admin`` a propósito: el admin no conoce el contexto de
inquilino, así que un administrador de una organización vería y editaría los
datos de todas. La administración va por la API y el frontend de React, con
los permisos de accounts.RolePermission.

**Este archivo está cerrado: no se le agregan rutas.** Cada app tiene su propio
``urls.py`` y ya está incluida acá. Si los seis editaran este archivo, cada
pull request traería un conflicto. La única excepción es incluir una app
**nueva** una sola vez, que es lo que hacen las líneas de ``scheduling`` y de
``audit``. Con ésas dos el Sprint 1 no crea ninguna app más, así que el archivo
vuelve a estar cerrado.

Las dos últimas —``reporting`` y ``backups``— son las características
generales 5 y 6 de la materia, y se agregaron juntas por lo mismo: una app
nueva es la única razón para abrir este archivo, así que se abre una vez para
las dos y no una vez por cada una.

**Sprint 2.** El sprint crea cuatro apps —``appointments``, ``payments``,
``encounters`` y ``assistant``—. El reparto pedía abrir este archivo **una
sola vez**, al inicio, para incluir las cuatro juntas; ``assistant`` entró así
para el corte del 16/09. ``appointments`` entra ahora, aparte, porque US-17 es
la ruta crítica del sprint y no podía esperar a que ``payments`` y
``encounters`` existieran (avisar al SM). ``payments`` y ``encounters`` quedan
para cuando Alexander y el SM las tengan listas.

    tu historia toca…          agregá la ruta en…
    organizaciones y planes    tenancy/urls.py       (US-43, US-44, US-45)
    usuarios, roles, login     accounts/urls.py      (US-01, US-02, US-04)
    sucursales, profesionales  catalog/urls.py       (US-11, US-12, US-16)
    agendas y disponibilidad   scheduling/urls.py    (US-13, US-14, US-15)
    pacientes                  patients/urls.py      (US-07 en adelante)
    fichas                     appointments/urls.py  (US-17, US-20)
    bitácora                   audit/urls.py         (US-06)
    reportes                   reporting/urls.py     (característica 5)
    copias de seguridad        backups/urls.py       (característica 6)
    asistente                  assistant/urls.py     (US-31, US-32, US-34)
"""

from django.urls import include, path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from tenancy.context import current_context


@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    """Sonda de estado.

    Es una vista de DRF y no de Django a propósito: así la autenticación
    —y con ella el contexto de inquilino— corre igual que en cualquier
    endpoint real. Devuelve el contexto tal como lo ve PostgreSQL, no lo que
    la aplicación cree haber fijado.
    """
    tenant, es_admin_plataforma = current_context()
    return Response({
        "status": "ok",
        "tenant": tenant,
        "platform_admin": es_admin_plataforma,
        "user": request.user.email if request.user.is_authenticated else None,
    })


urlpatterns = [
    path("api/health/", health, name="health"),
    path("api/platform/", include("tenancy.urls")),
    path("api/accounts/", include("accounts.urls")),
    path("api/catalog/", include("catalog.urls")),
    path("api/scheduling/", include("scheduling.urls")),
    path("api/patients/", include("patients.urls")),
    path("api/audit/", include("audit.urls")),
    path("api/reporting/", include("reporting.urls")),
    path("api/backups/", include("backups.urls")),
    path("api/assistant/", include("assistant.urls")),
    path("api/appointments/", include("appointments.urls")),
]
