"""US-06 (c) — Escribe los asientos después de la transacción de la petición.

**El orden en ``MIDDLEWARE`` es el punto entero de este archivo.** Django llama
a ``process_response`` en orden inverso al de la lista, así que para correr
*después* de ``TenantMiddleware`` —que es quien cierra la transacción— hay que
estar declarado *antes* que él. Si alguien lo mueve debajo, todo sigue
compilando, las pruebas de camino feliz siguen pasando, y los asientos de las
operaciones rechazadas desaparecen sin un solo error. Hay una prueba en
``tests/test_us06.py`` que falla si el orden se rompe.

No toca ``TenantMiddleware``: ese archivo es de ``tenancy`` y esta historia no
es dueña de él.
"""

from django.utils.deprecation import MiddlewareMixin

from .services import flush


class AuditTrailMiddleware(MiddlewareMixin):

    def process_response(self, request, response):
        flush(request)
        return response

    def process_exception(self, request, exception):
        # Una excepción que llega hasta acá ya deshizo la transacción de la
        # petición. El asiento tiene que sobrevivir igual: es la constancia del
        # intento.
        flush(request)
        return None
