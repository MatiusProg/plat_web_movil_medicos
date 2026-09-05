"""US-04 — Lógica de roles, permisos y asignaciones que no entra en una vista.

Dos cosas viven acá y no en el serializer:

1. **La bitácora.** Crear un rol, cambiarle los permisos o asignárselo a
   alguien son acciones sensibles (RNF-18), y las tres se auditan igual. Con
   una función se escribe una vez y no seis.
2. **El reemplazo del conjunto de permisos de un rol**, que es un cálculo de
   diferencias y no una asignación: hay que saber qué entró y qué salió para
   poder auditarlo.

La bitácora del Sprint 0 (``accounts.AuditLog``) es la que existe hoy. Cuando
US-06 publique la app ``audit``, estas escrituras se mudan allá; queda anotado
para no duplicar el registro cuando eso pase.
"""

from django.db import transaction

from ..models import AuditLog, Permission, RolePermission
# `_ip_del_cliente` es de US-02 y del mismo paquete: las dos historias son de
# la misma dueña y comparten el problema —Railway pone un proxy delante—, así
# que se reutiliza en vez de copiarla. Cuando US-06 se lleve la bitácora a la
# app `audit`, esta función se va con ella.
from .auth import _ip_del_cliente

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

    ``organization`` sale del usuario y no del contexto: es una acción de la
    organización sobre sí misma, y con ``NULL`` quedaría como acción de
    plataforma, que nadie del inquilino podría leer después.
    """
    return AuditLog.objects.create(
        organization=request.user.organization,
        user=request.user,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        detail=detail,
        ip_address=_ip_del_cliente(request),
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
