"""Contexto de inquilino a nivel de conexión de base de datos.

Todo lo que hace cumplir el aislamiento en PostgreSQL depende de dos
parámetros de sesión:

    app.tenant_id          uuid de la organización de la petición
    app.is_platform_admin  'on' sólo para el Superadministrador

Las políticas RLS los leen con ``current_setting(..., true)``. Sin ellos, la
política compara contra NULL, ninguna comparación con NULL es verdadera, y la
consulta devuelve **cero filas**. Es deliberado: si el middleware falla, el
sistema no devuelve nada en lugar de devolverlo todo.

Dos cosas que no son obvias y que ya causaron un defecto:

1. Se usa SET LOCAL (``set_config(..., is_local => true)``), nunca SET. Con
   SET a secas el valor sobrevive al COMMIT, la conexión vuelve al pool
   arrastrando el inquilino anterior y la petición siguiente lee datos ajenos.

2. SET LOCAL vive hasta el fin de la **transacción**, no del bloque. Salir de
   un ``atomic()`` anidado libera el savepoint pero NO devuelve el parámetro a
   su valor anterior. Por eso estos gestores guardan el valor previo y lo
   restauran al salir; sin eso, un contexto de superadministrador abierto al
   principio de una transacción seguiría vigente durante todo el resto.

Cada gestor fija **los dos** parámetros, no sólo el suyo: un contexto tiene
que ser inequívoco. Entrar en el de un inquilino apaga el de plataforma, y al
revés.
"""

from contextlib import contextmanager

from django.db import connection, transaction

TENANT_PARAM = "app.tenant_id"
PLATFORM_ADMIN_PARAM = "app.is_platform_admin"
_PARAMS = (TENANT_PARAM, PLATFORM_ADMIN_PARAM)


def _get(cursor, param: str) -> str:
    cursor.execute("SELECT current_setting(%s, true)", [param])
    return cursor.fetchone()[0] or ""


def _set(cursor, param: str, value: str) -> None:
    # `SET LOCAL x = %s` no admite parámetros; set_config sí.
    cursor.execute("SELECT set_config(%s, %s, true)", [param, value])


@contextmanager
def _scoped(tenant_id: str = "", platform_admin: bool = False):
    """Fija el contexto y lo restaura al salir, pase lo que pase."""
    values = {
        TENANT_PARAM: str(tenant_id or ""),
        PLATFORM_ADMIN_PARAM: "on" if platform_admin else "",
    }
    with transaction.atomic():
        with connection.cursor() as cursor:
            previous = {param: _get(cursor, param) for param in _PARAMS}
            for param, value in values.items():
                _set(cursor, param, value)
        try:
            yield
        finally:
            with connection.cursor() as cursor:
                for param, value in previous.items():
                    _set(cursor, param, value)


@contextmanager
def tenant_context(organization_id):
    """Abre una transacción con el contexto de un inquilino.

    Uso::

        with tenant_context(org.id):
            Patient.objects.all()     # sólo los de esa organización
    """
    with _scoped(tenant_id=organization_id, platform_admin=False):
        yield


@contextmanager
def platform_admin_context():
    """Abre una transacción con el contexto del Superadministrador.

    Ojo: NO da acceso a los datos de los inquilinos. Es deliberado — el
    alcance del proyecto dice que el superadministrador no accede a
    información clínica de ninguna organización, y eso se hace cumplir en la
    base. Dentro de este contexto, ``User.objects.count()`` cuenta sólo a los
    superadministradores.
    """
    with _scoped(tenant_id="", platform_admin=True):
        yield


@contextmanager
def no_tenant_context():
    """Transacción sin contexto. Toda tabla con RLS devuelve cero filas.

    Sirve para las pruebas de aislamiento y para el registro de intentos de
    login, que ocurre antes de saber a qué organización pertenece el correo.
    """
    with _scoped(tenant_id="", platform_admin=False):
        yield
