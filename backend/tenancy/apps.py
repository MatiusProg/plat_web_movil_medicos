"""La app del inquilino, y el `search_path` de cada conexión nueva.

**Por qué el `search_path` vive acá.** `config/settings.py` ya lo pide como
parámetro de conexión (`-c search_path=…`), que es la forma correcta y la que
alcanza contra PostgreSQL directo. Pero el *pooler* de Supabase puede ignorar
los parámetros de arranque del cliente: en ese caso el ajuste se pierde sin
decir nada y la migración del asistente vuelve a fallar con «type "vector" does
not exist», que fue D-18. Un `SET` sobre la conexión ya abierta no depende de
que el pooler respete nada.

Los dos caminos hacen lo mismo y no se estorban. Es a propósito: el que se
pierde en silencio es el que no se puede dejar solo.
"""

import re

from django.apps import AppConfig
from django.conf import settings
from django.db.backends.signals import connection_created

# Nombres de esquema separados por comas, nada más. El valor sale de una
# variable de entorno y termina interpolado en una sentencia: no se parametriza
# —`SET` no acepta parámetros— así que se valida antes.
_SEARCH_PATH_VALIDO = re.compile(r"[A-Za-z0-9_, ]+")


def _fijar_search_path(sender, connection, **kwargs):
    """`SET search_path` sobre cada conexión nueva a PostgreSQL."""
    if connection.vendor != "postgresql":
        return

    search_path = getattr(settings, "DB_SEARCH_PATH", "")
    if not search_path or not _SEARCH_PATH_VALIDO.fullmatch(search_path):
        return

    with connection.cursor() as cursor:
        cursor.execute(f"SET search_path = {search_path}")


class TenancyConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenancy"

    def ready(self):
        connection_created.connect(
            _fijar_search_path, dispatch_uid="tenancy.search_path",
        )
