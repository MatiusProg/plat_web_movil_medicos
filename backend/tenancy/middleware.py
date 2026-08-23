"""Middleware que fija el contexto de inquilino en cada petición.

Es la mitad de la aplicación del aislamiento; la otra mitad son las políticas
RLS. Existen las dos porque la primera depende de que nadie se olvide nunca.

Orden de resolución del inquilino:

1. Si el usuario está autenticado, manda su ``organization``. El token no
   puede pedir una organización distinta de la del usuario: si lo intenta, se
   registra una IsolationAlert y se rechaza.
2. Si no lo está, se intenta resolver por el encabezado ``X-Organization`` o
   por el parámetro ``organization`` del cuerpo/query. Lo necesita el login:
   hay que saber en qué inquilino buscar el correo ANTES de autenticar,
   porque el correo es único por organización y no globalmente (decisión D-5).
3. Si no se resuelve nada, la petición sigue sin contexto y toda consulta
   sobre una tabla con RLS devuelve cero filas.
"""

import logging

from django.db import transaction
from django.utils.deprecation import MiddlewareMixin

from .context import PLATFORM_ADMIN_PARAM, TENANT_PARAM, _set_local

logger = logging.getLogger(__name__)

ORGANIZATION_HEADER = "HTTP_X_ORGANIZATION"


class TenantMiddleware(MiddlewareMixin):
    """Envuelve la petición en una transacción con el contexto fijado.

    Tiene que ir DESPUÉS de AuthenticationMiddleware, porque necesita
    ``request.user`` para saber a qué organización pertenece.
    """

    def process_request(self, request):
        organization_id = None
        is_platform_admin = False

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            is_platform_admin = user.is_platform_admin
            organization_id = user.organization_id
        else:
            organization_id = self._organization_from_request(request)

        request.tenant_id = organization_id
        request.is_platform_admin = is_platform_admin

        # atomic() se abre a mano para que el SET LOCAL viva exactamente lo
        # que dura la petición y se descarte al cerrar.
        atomic = transaction.atomic()
        atomic.__enter__()
        request._tenant_atomic = atomic

        if organization_id is not None:
            _set_local(TENANT_PARAM, str(organization_id))
        if is_platform_admin:
            _set_local(PLATFORM_ADMIN_PARAM, "on")

        return None

    def process_response(self, request, response):
        self._close(request, exception=None)
        return response

    def process_exception(self, request, exception):
        self._close(request, exception=exception)
        return None

    @staticmethod
    def _close(request, exception):
        atomic = getattr(request, "_tenant_atomic", None)
        if atomic is None:
            return
        del request._tenant_atomic
        if exception is not None:
            atomic.__exit__(type(exception), exception, exception.__traceback__)
        else:
            atomic.__exit__(None, None, None)

    @staticmethod
    def _organization_from_request(request):
        """Resuelve el inquilino por slug para las peticiones sin autenticar.

        Problema del huevo y la gallina: en este punto no hay contexto, así que
        un ``SELECT`` sobre ``organizations`` devolvería cero filas por la
        propia política RLS, y el login nunca podría empezar.

        Se resuelve con ``app_resolve_tenant``, una función de base de datos
        que hace exactamente una cosa: dado un slug exacto, devuelve el uuid de
        la organización activa que le corresponde, o NULL. No devuelve ninguna
        otra columna y **no permite enumerar**: hay que conocer el slug de
        antemano. Es lo mínimo que necesita el formulario de login.
        """
        from django.db import connection

        slug = request.META.get(ORGANIZATION_HEADER) or request.GET.get("organization")
        if not slug:
            return None

        with connection.cursor() as cursor:
            cursor.execute("SELECT app_resolve_tenant(%s)", [slug])
            row = cursor.fetchone()
        return row[0] if row and row[0] else None
