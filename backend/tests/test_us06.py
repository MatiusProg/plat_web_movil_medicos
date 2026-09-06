"""US-06 — Bitácora de auditoría.

Casi todas entran por HTTP, como pide el punto 6 de las convenciones. Las tres
que no —las del punto (c)— prueban el mecanismo de escritura diferida, que por
definición ocurre *después* de que la vista devolvió su respuesta y no se puede
observar desde el cuerpo de una.

El bloque final es el criterio 4 de la Definition of Done: aislamiento
comprobado en ORM y en HTTP (RNF-08, punto g de la historia).
"""

import pytest
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory

from accounts.models import AuditLog
from accounts.tokens import tokens_for_user
from audit import services as bitacora
from audit.actions import Action
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"

# Lo que la historia le pide al rol que audita, y nada más: la bitácora se lee
# y no se escribe.
PERMISOS_AUDITORIA = ["audit.log.read"]


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


@pytest.fixture
def auditor_a(db, org_a, user_a):
    """`user_a` con permiso para leer la bitácora de su organización."""
    dar_rol(user_a, org_a, "auditor", "Auditor", PERMISOS_AUDITORIA)
    return user_a


@pytest.fixture
def auditor_b(db, org_b, user_b):
    dar_rol(user_b, org_b, "auditor", "Auditor", PERMISOS_AUDITORIA)
    return user_b


def asentar(organization, user, action, entity="roles", entity_id="1", detail=None,
            ip="10.0.0.1", agent="pytest"):
    """Deja un asiento directo, sin pasar por una vista.

    Las pruebas de la consulta necesitan asientos que ya existan; producirlos
    ejerciendo US-03 y US-04 ataría esta historia a los detalles de las otras
    dos.
    """
    with tenant_context(organization.id):
        return AuditLog.objects.create(
            organization=organization,
            user=user,
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=detail or {},
            ip_address=ip,
            user_agent=agent,
        )


# --------------------------------------------------------------------------
#  Punto (c) — la escritura vive fuera de la transacción de negocio
# --------------------------------------------------------------------------

def test_el_middleware_de_bitacora_corre_despues_de_cerrar_la_transaccion():
    """El orden de `MIDDLEWARE` es lo que hace cumplir el punto (c).

    Django llama a `process_response` en orden inverso al de la lista, así que
    `AuditTrailMiddleware` tiene que estar declarado ANTES que
    `TenantMiddleware` para correr DESPUÉS de que éste cierre la transacción.

    Sin esta prueba, moverlo de lugar no rompe nada visible: las pruebas de
    camino feliz siguen en verde y los asientos de las operaciones rechazadas
    dejan de escribirse en silencio.
    """
    orden = list(settings.MIDDLEWARE)
    assert orden.index("audit.middleware.AuditTrailMiddleware") < orden.index(
        "tenancy.middleware.TenantMiddleware",
    )


def test_el_asiento_sobrevive_a_que_la_operacion_se_deshaga(org_a, user_a):
    """Punto (c), segunda mitad: la constancia del intento no se borra.

    Es el caso que motiva todo el diseño. `TenantMiddleware` abre una
    transacción por petición y DRF llama a `set_rollback()` cuando maneja un
    rechazo: un asiento escrito dentro de esa transacción se perdería
    justamente en los casos que más interesa auditar.
    """
    peticion = APIRequestFactory().post("/api/accounts/roles/")
    peticion.user = user_a

    with pytest.raises(RuntimeError):
        with transaction.atomic():
            bitacora.record(
                peticion,
                action=Action.ROLE_CREATE,
                entity="roles",
                entity_id="777",
                detail={"code": "caja"},
            )
            raise RuntimeError("la operación de negocio falla y se deshace")

    # Nada se escribió todavía: el asiento estaba encolado en la petición.
    with tenant_context(org_a.id):
        assert not AuditLog.objects.filter(entity_id="777").exists()

    # Es lo que hace el middleware una vez cerrada la transacción.
    bitacora.flush(peticion)

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(entity_id="777")
        assert asiento.action == Action.ROLE_CREATE
        assert asiento.organization_id == org_a.id


def test_una_falla_al_escribir_la_bitacora_no_tumba_la_operacion(
    org_a, user_a, monkeypatch,
):
    """Punto (c), primera mitad. Un asiento perdido es un problema; una
    operación caída porque no se pudo auditar, uno peor."""
    def explota(*args, **kwargs):
        raise RuntimeError("la base de la bitácora no responde")

    monkeypatch.setattr(AuditLog.objects, "create", explota)

    peticion = APIRequestFactory().post("/api/accounts/roles/")
    peticion.user = user_a
    bitacora.record(
        peticion, action=Action.ROLE_CREATE, entity="roles", entity_id="778",
    )

    # No propaga. Si propagara, esta línea reventaría la prueba.
    bitacora.flush(peticion)


def test_la_cola_se_vacia_y_no_se_reintenta(org_a, user_a):
    """Dos `flush` seguidos no duplican el asiento."""
    peticion = APIRequestFactory().post("/api/accounts/roles/")
    peticion.user = user_a
    bitacora.record(
        peticion, action=Action.ROLE_CREATE, entity="roles", entity_id="779",
    )

    bitacora.flush(peticion)
    bitacora.flush(peticion)

    with tenant_context(org_a.id):
        assert AuditLog.objects.filter(entity_id="779").count() == 1


# --------------------------------------------------------------------------
#  Punto (b) — qué guarda cada asiento
# --------------------------------------------------------------------------

def test_el_asiento_guarda_quien_que_cuando_desde_donde_y_con_que_agente(
    org_a, user_a,
):
    peticion = APIRequestFactory().post(
        "/api/accounts/roles/",
        HTTP_X_FORWARDED_FOR="190.181.1.1, 10.0.0.9",
        HTTP_USER_AGENT="Mozilla/5.0 (prueba)",
    )
    peticion.user = user_a
    bitacora.record(
        peticion, action=Action.ROLE_ASSIGN, entity="user_roles",
        entity_id="780", detail={"role_code": "caja"},
    )
    bitacora.flush(peticion)

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(entity_id="780")

    assert asiento.user_id == user_a.id                      # quién
    assert asiento.action == Action.ROLE_ASSIGN              # qué
    assert asiento.entity == "user_roles"                    # sobre qué
    assert asiento.occurred_at is not None                   # cuándo
    # Detrás del proxy de Railway, la del cliente es la primera de la cadena.
    assert asiento.ip_address == "190.181.1.1"               # desde dónde
    assert asiento.user_agent == "Mozilla/5.0 (prueba)"      # con qué agente
    assert asiento.organization_id == org_a.id


def test_una_accion_de_us03_deja_su_asiento(api_client, org_a, user_a):
    """El registro es automático (punto a): la historia de al lado no hace
    nada especial para quedar auditada."""
    respuesta = api_client.post(
        reverse("accounts:password-reset"),
        {"organization": org_a.slug, "email": user_a.email},
        format="json",
    )
    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        assert AuditLog.objects.filter(
            action=Action.PASSWORD_RESET_REQUEST, user=user_a,
        ).exists()


# --------------------------------------------------------------------------
#  Puntos (e) y (f) — la consulta
# --------------------------------------------------------------------------

def test_el_listado_va_del_mas_reciente_al_mas_antiguo(
    api_client, auditor_a, org_a,
):
    asentar(org_a, auditor_a, Action.ROLE_CREATE, entity_id="1")
    asentar(org_a, auditor_a, Action.ROLE_UPDATE, entity_id="2")
    asentar(org_a, auditor_a, Action.ROLE_DELETE, entity_id="3")

    respuesta = autenticar(api_client, auditor_a).get(reverse("audit:log-list"))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["count"] == 3
    assert [fila["entity_id"] for fila in cuerpo["results"]] == ["3", "2", "1"]
    # Punto (b): la pantalla recibe el nombre del actor resuelto, no su uuid.
    assert cuerpo["results"][0]["actor"]["email"] == auditor_a.email
    assert cuerpo["results"][0]["action_label"] == "Rol eliminado"


def test_filtro_por_actor(api_client, auditor_a, org_a, user_b):
    otro = asentar(org_a, None, Action.ROLE_CREATE, entity_id="sin-actor")
    asentar(org_a, auditor_a, Action.ROLE_UPDATE, entity_id="con-actor")

    respuesta = autenticar(api_client, auditor_a).get(
        reverse("audit:log-list"), {"actor": str(auditor_a.id)},
    )

    assert respuesta.status_code == 200
    resultados = respuesta.json()["results"]
    assert [fila["entity_id"] for fila in resultados] == ["con-actor"]
    assert otro.user_id is None


def test_filtro_por_tipo_de_accion(api_client, auditor_a, org_a):
    asentar(org_a, auditor_a, Action.ROLE_CREATE, entity_id="1")
    asentar(org_a, auditor_a, Action.PASSWORD_RESET_COMPLETE, entity_id="2")
    asentar(org_a, auditor_a, Action.ROLE_ASSIGN, entity_id="3")

    cliente = autenticar(api_client, auditor_a)

    una = cliente.get(reverse("audit:log-list"), {"action": Action.ROLE_CREATE})
    assert [f["entity_id"] for f in una.json()["results"]] == ["1"]

    # Varias separadas por coma, para que el filtro pueda ofrecer un grupo.
    varias = cliente.get(
        reverse("audit:log-list"),
        {"action": f"{Action.ROLE_CREATE},{Action.ROLE_ASSIGN}"},
    )
    assert {f["entity_id"] for f in varias.json()["results"]} == {"1", "3"}


def asentar_con_fecha(organization, user, action, entity_id, occurred_at):
    """Un asiento fechado a mano, insertado con SQL.

    No se puede hacer con el ORM: ``occurred_at`` es ``auto_now_add``, así que
    Django la pisa al crear, y corregirla después con un UPDATE lo rechaza la
    propia base —``app_user`` tiene ``REVOKE UPDATE`` sobre esta tabla, que es
    justamente el punto (f)—. Insertar con la fecha puesta sí se puede: lo que
    la bitácora no admite es cambiar lo ya escrito.
    """
    from django.db import connection

    with tenant_context(organization.id), connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO audit_log (
                organization_id, user_id, action, entity, entity_id,
                detail, ip_address, user_agent, occurred_at
            )
            VALUES (%s, %s, %s, 'roles', %s, '{}'::jsonb, NULL, '', %s)
            """,
            [organization.id, user.id, action, entity_id, occurred_at],
        )


def test_filtro_por_rango_de_fechas(api_client, auditor_a, org_a):
    from datetime import timedelta

    from django.utils import timezone

    asentar_con_fecha(
        org_a, auditor_a, Action.ROLE_CREATE, "viejo",
        timezone.now() - timedelta(days=10),
    )
    asentar(org_a, auditor_a, Action.ROLE_UPDATE, entity_id="hoy")

    hoy = timezone.localdate()
    cliente = autenticar(api_client, auditor_a)

    desde_hoy = cliente.get(
        reverse("audit:log-list"), {"date_from": hoy.isoformat()},
    )
    assert [f["entity_id"] for f in desde_hoy.json()["results"]] == ["hoy"]

    hasta_ayer = cliente.get(
        reverse("audit:log-list"),
        {"date_to": (hoy - timedelta(days=1)).isoformat()},
    )
    assert [f["entity_id"] for f in hasta_ayer.json()["results"]] == ["viejo"]


def test_una_fecha_mal_escrita_se_rechaza_y_no_devuelve_todo(
    api_client, auditor_a, org_a,
):
    """Sin esto, `date_from=ayer` devuelve la lista entera como si no se
    hubiera filtrado, y quien audita concluye que no pasó nada raro."""
    asentar(org_a, auditor_a, Action.ROLE_CREATE)

    respuesta = autenticar(api_client, auditor_a).get(
        reverse("audit:log-list"), {"date_from": "ayer"},
    )

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "fecha_invalida"


def test_el_catalogo_de_acciones_trae_solo_las_registradas(
    api_client, auditor_a, org_a,
):
    asentar(org_a, auditor_a, Action.ROLE_CREATE)

    respuesta = autenticar(api_client, auditor_a).get(
        reverse("audit:log-actions"),
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == [
        {"code": Action.ROLE_CREATE, "label": "Rol creado"},
    ]


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_la_bitacora_no_expone_verbos_de_escritura(
    api_client, auditor_a, org_a, metodo,
):
    """Punto (f): ni siquiera al administrador."""
    asiento = asentar(org_a, auditor_a, Action.ROLE_CREATE)
    cliente = autenticar(api_client, auditor_a)

    if metodo == "post":
        respuesta = cliente.post(reverse("audit:log-list"), {}, format="json")
    else:
        url = reverse("audit:log-detail", args=[asiento.id])
        respuesta = getattr(cliente, metodo)(url, {}, format="json")

    assert respuesta.status_code == 405


def test_la_base_tampoco_deja_modificar_un_asiento_ya_escrito(org_a, auditor_a):
    """Punto (f), una capa más abajo que la vista.

    Que la API no exponga PUT no alcanza: cualquier código del proyecto podría
    llamar a `.save()`. La garantía real es el `REVOKE UPDATE, DELETE` que la
    migración de RLS aplica sobre `audit_log`, y esta prueba es la que avisa si
    alguien lo devuelve con un GRANT.
    """
    from django.db import Error, transaction as tx

    asiento = asentar(org_a, auditor_a, Action.ROLE_CREATE, entity_id="fijo")

    with pytest.raises(Error):
        with tx.atomic(), tenant_context(org_a.id):
            AuditLog.objects.filter(pk=asiento.pk).update(action="otra.cosa")


def test_sin_el_permiso_no_se_lee_la_bitacora(api_client, org_a, user_a):
    """Punto (h). `user_a` entra pero no lleva `audit.log.read`."""
    asentar(org_a, user_a, Action.ROLE_CREATE)

    respuesta = autenticar(api_client, user_a).get(reverse("audit:log-list"))

    assert respuesta.status_code == 403


# --------------------------------------------------------------------------
#  Punto (g) — aislamiento (RNF-08). Criterio 4 de la Definition of Done.
# --------------------------------------------------------------------------

def test_un_administrador_no_ve_los_asientos_de_otra_organizacion(
    api_client, auditor_a, auditor_b, org_a, org_b,
):
    asentar(org_a, auditor_a, Action.ROLE_CREATE, entity_id="de-a")
    asentar(org_b, auditor_b, Action.ROLE_CREATE, entity_id="de-b")

    respuesta = autenticar(api_client, auditor_a).get(reverse("audit:log-list"))

    assert respuesta.status_code == 200
    entidades = [fila["entity_id"] for fila in respuesta.json()["results"]]
    assert entidades == ["de-a"]


def test_el_asiento_de_otra_organizacion_no_se_abre_por_su_id(
    api_client, auditor_a, auditor_b, org_a, org_b,
):
    ajeno = asentar(org_b, auditor_b, Action.ROLE_CREATE, entity_id="de-b")

    respuesta = autenticar(api_client, auditor_a).get(
        reverse("audit:log-detail", args=[ajeno.id]),
    )

    assert respuesta.status_code == 404


def test_rls_esconde_los_asientos_ajenos_tambien_en_el_orm(
    auditor_a, auditor_b, org_a, org_b,
):
    """La misma comprobación una capa más abajo: si mañana alguien se olvida
    del filtro en la vista, la base sigue respondiendo cero filas."""
    asentar(org_a, auditor_a, Action.ROLE_CREATE, entity_id="de-a")
    asentar(org_b, auditor_b, Action.ROLE_CREATE, entity_id="de-b")

    with tenant_context(org_a.id):
        assert list(
            AuditLog.objects.values_list("entity_id", flat=True),
        ) == ["de-a"]

    with tenant_context(org_b.id):
        assert list(
            AuditLog.objects.values_list("entity_id", flat=True),
        ) == ["de-b"]
