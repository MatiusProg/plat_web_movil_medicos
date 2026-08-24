"""Middleware de inquilino.

Hace **dos** cosas, y a propósito ninguna más:

1. Envuelve la petición en una transacción, para que el ``SET LOCAL`` del
   contexto viva exactamente lo que dura la petición y se descarte al cerrar.
2. Para peticiones **sin autenticar**, resuelve el inquilino a partir del
   encabezado ``X-Organization``. Lo necesita el login: el correo es único por
   organización, así que hay que saber en cuál buscar antes de autenticar.

**Lo que este middleware NO hace: leer el usuario.** Un middleware corre antes
de la vista, y la autenticación de DRF ocurre dentro de la vista; acá
``request.user`` sería siempre anónimo para un cliente con JWT. El contexto de
una petición autenticada lo fija ``accounts.authentication`` a partir del claim
del token, que es el único momento en que se puede.

Si la petición trae token, lo que fije la autenticación **pisa** lo que haya
resuelto el slug. Y si los dos no coinciden, queda registrada una alerta: es
exactamente el escenario de mandar el token de una organización con el slug de
otra.
"""

import logging

from django.db import transaction
from django.utils.deprecation import MiddlewareMixin

from .context import set_context

logger = logging.getLogger(__name__)

ORGANIZATION_HEADER = "HTTP_X_ORGANIZATION"


class TenantMiddleware(MiddlewareMixin):

    def process_request(self, request):
        # La transacción se abre a mano para que abarque toda la petición.
        atomic = transaction.atomic()
        atomic.__enter__()
        request._tenant_atomic = atomic

        # Sólo sirve para las peticiones sin autenticar (el login). Para las
        # demás, la clase de autenticación lo va a sobrescribir enseguida.
        organization = self._organization_from_slug(request)
        request.tenant_id_from_slug = organization
        if organization is not None:
            set_context(organization_id=organization)

        return None

    def process_response(self, request, response):
        self._close(request, None)
        self._persist_alerts(request)
        return response

    def process_exception(self, request, exception):
        self._close(request, exception)
        self._persist_alerts(request)
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

        # Limpieza explícita del contexto.
        #
        # Al cerrar la transacción, PostgreSQL descarta solo los SET LOCAL. Pero
        # si esta transacción era interna a otra —como pasa en las pruebas, o
        # si alguien anida atomic()— liberar el savepoint NO los deshace, y el
        # contexto sobreviviría a la petición. Con conexiones agrupadas eso
        # significa que la petición siguiente leería datos ajenos.
        try:
            set_context(organization_id=None, platform_admin=False)
        except Exception:  # noqa: BLE001
            logger.exception("No se pudo limpiar el contexto de inquilino")

    @staticmethod
    def _persist_alerts(request):
        """Persiste las alertas que dejó pendientes la autenticación.

        Va después de cerrar la transacción de la petición, porque cuando DRF
        maneja una excepción llama a ``set_rollback()`` y todo lo escrito
        durante el rechazo se descarta. Estas alertas tienen que sobrevivir
        justamente a los rechazos: son el registro de los intentos.
        """
        pending = getattr(request, "pending_alerts", None)
        if not pending:
            return
        request.pending_alerts = []

        from django.db import transaction as tx

        from .models import IsolationAlert

        for data in pending:
            try:
                with tx.atomic():
                    set_context(platform_admin=True)
                    IsolationAlert.objects.create(**data)
            except Exception:  # noqa: BLE001
                logger.exception("No se pudo registrar la alert de aislamiento")
            finally:
                set_context(organization_id=None, platform_admin=False)

    @staticmethod
    def _organization_from_slug(request):
        """Resuelve el inquilino por slug, para las peticiones sin autenticar.

        Problema del huevo y la gallina: en este punto no hay contexto, así que
        un ``SELECT`` sobre ``organizations`` devolvería cero filas por la
        propia política RLS.

        Lo resuelve ``app_resolve_tenant``, una función de base de datos que
        hace exactamente una cosa: dado un slug exacto, devuelve el uuid de la
        organización activa que le corresponde, o NULL. No devuelve ninguna
        otra columna y **no permite enumerar**: hay que conocer el slug de
        antemano.
        """
        from django.db import connection

        slug = request.META.get(ORGANIZATION_HEADER) or request.GET.get("organization")
        if not slug:
            return None

        with connection.cursor() as cursor:
            cursor.execute("SELECT app_resolve_tenant(%s)", [slug])
            row = cursor.fetchone()
        return row[0] if row and row[0] else None
