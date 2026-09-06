"""US-04 — Lógica de roles, permisos y asignaciones que no entra en una vista.

Dos cosas viven acá y no en el serializer:

1. **La bitácora.** Crear un rol, cambiarle los permisos o asignárselo a
   alguien son acciones sensibles (RNF-18), y las tres se auditan igual. Con
   una función se escribe una vez y no seis.
2. **El reemplazo del conjunto de permisos de un rol**, que es un cálculo de
   diferencias y no una asignación: hay que saber qué entró y qué salió para
   poder auditarlo.

La mudanza que este archivo anunciaba **ya pasó**: US-06 publicó la app
``audit`` y ``record`` es ahora un alias de ``audit.services.record``. Los seis
lugares que lo llamaban siguen llamándolo igual —misma firma, mismo orden de
argumentos— y lo que cambió está una capa más abajo: el asiento ya no se
escribe dentro de la transacción de la petición, así que sobrevive a los
rechazos. Ver el punto (c) de US-06.
"""

from django.db import transaction

from audit import services as bitacora

from ..models import Permission, RolePermission

# Los permisos del módulo `platform` son del Superadministrador y no se le
# pueden conceder a un rol de una organización. Sin este corte, el
# administrador de un centro médico podría armarse un rol con
# `platform.organization.create` y darse de alta organizaciones.
PLATFORM_MODULE = "platform"


def assignable_permissions():
    """El catálogo que un rol de organización puede llegar a tener."""
    return Permission.objects.exclude(module=PLATFORM_MODULE)


def record(request, action, entity, entity_id, detail):
    """Deja el asiento en la bitácora. RNF-18.

    Alias hacia ``audit.services.record``, que es donde vive la bitácora desde
    US-06. Se conserva el nombre para no tocar los seis lugares de US-04 que ya
    lo llamaban, y porque ``servicio.record(...)`` se lee mejor en una vista de
    roles que un import de otra app.

    Ojo con una diferencia: esto ya **no devuelve** el asiento. El asiento se
    escribe después de que cierre la transacción de la petición, así que
    todavía no existe cuando esta llamada retorna.
    """
    return bitacora.record(
        request,
        action=action,
        entity=entity,
        entity_id=entity_id,
        detail=detail,
    )


@transaction.atomic
def replace_permissions(role, permissions):
    """Deja el rol con exactamente los permisos de ``permissions``.

    Devuelve ``(agregados, quitados)`` como listas de códigos ordenadas, que
    es lo que la bitácora necesita para que el asiento diga qué cambió y no
    sólo que algo cambió.

    Se calcula la diferencia en vez de borrar todo y volver a insertar: así
    ``granted_at`` sobrevive para los permisos que el rol ya tenía, y la
    respuesta no miente diciendo que se concedieron de nuevo.
    """
    current = set(
        RolePermission.objects
        .filter(role=role)
        .values_list("permission__code", flat=True)
    )
    wanted = {permission.code for permission in permissions}

    added = sorted(wanted - current)
    removed = sorted(current - wanted)

    if removed:
        RolePermission.objects.filter(
            role=role, permission__code__in=removed,
        ).delete()

    if added:
        RolePermission.objects.bulk_create([
            RolePermission(
                role=role,
                permission=permission,
                # El discriminador va denormalizado en la fila: es lo que
                # compara la política `tenant_isolation`. Sin él, el INSERT
                # lo rechaza la base.
                organization_id=role.organization_id,
            )
            for permission in permissions
            if permission.code in added
        ])

    return added, removed
