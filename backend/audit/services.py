"""US-06 — Cómo se deja un asiento en la bitácora.

**El modelo vive en ``accounts.AuditLog`` y no acá.** La tabla ``audit_log``
existe desde el Sprint 0 —asignar un rol ya era una acción sensible— con su
política RLS y con ``REVOKE UPDATE, DELETE`` aplicados en local y en Supabase.
Mudar el modelo de app habría obligado a tocar migraciones de dos apps y a
reapuntar imports en código ya mergeado, sin ganar una sola garantía: lo que el
reparto pide de esta historia —prefijo ``/api/audit/`` propio, sin verbos de
escritura y con filtros— se cumple igual leyendo el modelo de al lado. Queda
anotado en ``docs/registro-de-defectos.md``.

El punto (c) es lo único delicado de este archivo:

    «Escritura fuera de la transacción de negocio: que falle la auditoría no
    puede tumbar la operación auditada, y que la operación se deshaga no borra
    la constancia del intento.»

Las dos mitades necesitan cosas distintas:

1. *Que falle la auditoría no tumba la operación.* Se resuelve tragando toda
   excepción al escribir. Un asiento perdido es un problema; una operación
   caída porque no se pudo auditar, uno peor.

2. *Que la operación se deshaga no borra la constancia.* Ésta no se resuelve
   con un ``try``. ``TenantMiddleware`` abre **una transacción por petición**,
   y cuando DRF maneja una excepción llama a ``set_rollback()``: todo lo
   escrito durante ese rechazo se descarta, asiento incluido. Justo los casos
   que más interesa auditar —el intento rechazado— serían los que no dejan
   rastro.

   Por eso el asiento no se escribe cuando se llama a ``record``: se **encola
   en la petición** y lo escribe ``AuditTrailMiddleware`` después de que
   ``TenantMiddleware`` cerró la transacción. Es el mismo recurso que el
   proyecto ya usa para ``isolation_alerts`` y ``login_attempts``, y por la
   misma razón.

Fuera del ciclo HTTP —comandos de gestión, tareas, migraciones— no hay
petición donde encolar ni transacción de la que escapar: ``record`` sin
``request`` escribe en el momento, envuelto igual.
"""

import logging

from django.db import transaction

from tenancy.context import set_context

logger = logging.getLogger(__name__)

# Dónde se acumulan los asientos mientras dura la petición.
PENDING_ATTR = "pending_audit_entries"


def client_ip(request):
    """La IP del cliente, mirando primero el encabezado del proxy.

    En Railway la aplicación corre detrás de un proxy, así que ``REMOTE_ADDR``
    es el del proxy y no el del cliente. ``X-Forwarded-For`` lleva la cadena
    completa y el primero es el cliente.

    Vive acá y no en ``accounts`` porque la usan las tres cosas que registran
    de dónde vino una petición —la bitácora, ``login_attempts`` y los tokens de
    restablecimiento—, y ninguna de las tres es dueña de las otras dos.
    ``accounts.services.auth._ip_del_cliente`` quedó como alias hacia acá.
    """
    if request is None:
        return None
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if reenviada:
        return reenviada.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


def user_agent(request):
    """El agente del cliente, recortado al ancho de la columna."""
    if request is None:
        return ""
    return request.META.get("HTTP_USER_AGENT", "")[:300]


def record(request, action, entity, entity_id="", detail=None,
           organization=None, user=None):
    """Deja un asiento en la bitácora. RNF-18 y US-06 (a), (b) y (c).

    ``organization`` y ``user`` salen de quien hizo la petición salvo que se
    los pase explícitamente. La organización sale del **usuario** y no del
    contexto de inquilino a propósito: es una acción de la organización sobre
    sí misma, y con ``organization`` en NULL quedaría archivada como acción de
    plataforma, que nadie del inquilino podría leer después.

    Devuelve ``None``: el asiento todavía no existe cuando esto retorna. Quien
    necesite el objeto —sólo las pruebas, hasta ahora— que lo busque después de
    la respuesta.
    """
    autor = user if user is not None else _usuario_de(request)
    entry = {
        "organization_id": _organization_id(organization, autor),
        "user_id": getattr(autor, "id", None),
        "action": action,
        "entity": entity,
        "entity_id": str(entity_id or "")[:64],
        "detail": detail or {},
        "ip_address": client_ip(request),
        "user_agent": user_agent(request),
    }

    if request is None:
        # Sin petición no hay transacción de la que escapar ni dónde encolar.
        _write(entry)
        return None

    destino = _http_request(request)
    pendientes = getattr(destino, PENDING_ATTR, None)
    if pendientes is None:
        pendientes = []
        setattr(destino, PENDING_ATTR, pendientes)
    pendientes.append(entry)
    return None


def _http_request(request):
    """El ``HttpRequest`` de Django que hay debajo.

    Las vistas y los serializers reciben el ``Request`` de DRF, que es un
    envoltorio: ``getattr`` sobre él delega en el de Django, pero ``setattr``
    **no** —el atributo queda en el envoltorio, que se descarta al terminar la
    vista—. El middleware recibe el de Django, así que la cola tiene que
    colgar de ése o los asientos no se escriben nunca. Costó una prueba en
    rojo; ver ``tests/test_us06.py::test_una_accion_de_us03_deja_su_asiento``.
    """
    return getattr(request, "_request", request)


def flush(request):
    """Escribe los asientos encolados. Lo llama ``AuditTrailMiddleware``.

    Vacía la cola **antes** de escribir: si algo sale mal a mitad de camino, la
    petición siguiente no reintenta asientos ajenos.
    """
    destino = _http_request(request)
    pendientes = getattr(destino, PENDING_ATTR, None)
    if not pendientes:
        return
    setattr(destino, PENDING_ATTR, [])
    for entry in pendientes:
        _write(entry)


def _write(entry):
    """Un asiento, en su propia transacción y sin propagar nunca un error.

    El contexto se fija acá y no se hereda: para cuando esto corre, la
    transacción de la petición ya cerró y ``TenantMiddleware`` limpió
    ``app.tenant_id``. Sin volver a fijarlo, ``tenant_isolation`` compara
    contra NULL y el INSERT se rechaza.
    """
    from accounts.models import AuditLog

    organization_id = entry.get("organization_id")
    try:
        with transaction.atomic():
            # Un asiento de plataforma —alta de organización— va con
            # ``organization`` en NULL, y esa mitad de la política sólo la pasa
            # el superadministrador.
            if organization_id is None:
                set_context(platform_admin=True)
            else:
                set_context(organization_id=organization_id)
            AuditLog.objects.create(**entry)
    except Exception:  # noqa: BLE001
        # Punto (c), primera mitad. Se registra en el log de la aplicación para
        # que la pérdida no sea silenciosa, y no se propaga.
        logger.exception(
            "No se pudo escribir el asiento de bitácora %s sobre %s",
            entry.get("action"), entry.get("entity"),
        )
    finally:
        set_context(organization_id=None, platform_admin=False)


def _usuario_de(request):
    usuario = getattr(request, "user", None)
    if usuario is None or not getattr(usuario, "is_authenticated", False):
        return None
    return usuario


def _organization_id(organization, autor):
    if organization is not None:
        return getattr(organization, "id", organization)
    return getattr(autor, "organization_id", None)
