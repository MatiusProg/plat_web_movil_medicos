"""Lo que promete el plan, se cumple (tenancy/plans.py).

La primera prueba es la guardiana de la regla, con el mismo espíritu que la
que exige RLS en toda tabla con organization_id: si alguien agrega un límite
o una función a un plan sin registrar dónde se hace cumplir, falla.
"""

import datetime as dt

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import Role, User
from accounts.tokens import tokens_for_user
from catalog.models import Branch, Practitioner
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Subscription, SubscriptionPlan
from tenancy.plans import PLAN_RULES

from .conftest import dar_rol

pytestmark = pytest.mark.django_db


def cliente(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}")
    return client


def con_plan(org, plans, codigo, **cambios):
    """Asigna el plan a la organización; `cambios` ajusta sus topes (sólo en la prueba)."""
    with platform_admin_context():
        if cambios:
            SubscriptionPlan.objects.filter(pk=plans[codigo].pk).update(**cambios)
        Subscription.objects.filter(organization=org).update(plan=plans[codigo])


def es_limite_de_plan(respuesta):
    return respuesta.status_code == 403 and respuesta.json().get("code") == "plan_limit"


# --------------------------------------------------------------------------
#  La guardiana
# --------------------------------------------------------------------------

def test_todo_lo_que_declara_un_plan_tiene_donde_se_hace_cumplir(plans):
    campos = {f.name for f in SubscriptionPlan._meta.get_fields()
              if f.name.startswith("max_") or f.name == "storage_mb"}
    funciones = {clave for plan in plans.values() for clave in (plan.features or {})}
    faltan = (campos | funciones) - set(PLAN_RULES)
    assert not faltan, (
        f"El plan declara {sorted(faltan)} y nadie lo hace cumplir. Registralo en "
        f"tenancy/plans.py::PLAN_RULES con dónde se aplica (o por qué no aplica)."
    )


def test_el_registro_no_tiene_reglas_huerfanas(plans):
    campos = {f.name for f in SubscriptionPlan._meta.get_fields()}
    funciones = {clave for plan in plans.values() for clave in (plan.features or {})}
    sobran = set(PLAN_RULES) - campos - funciones
    assert not sobran, f"PLAN_RULES menciona {sorted(sobran)}, que ningún plan declara."


def test_cada_regla_dice_su_estado_y_donde(plans):
    for clave, (estado, donde) in PLAN_RULES.items():
        assert estado in {"aplicado", "pendiente", "no_aplica"}, clave
        assert donde.strip(), clave


# --------------------------------------------------------------------------
#  Sucursales y profesionales
# --------------------------------------------------------------------------

@pytest.fixture
def admin_a(org_a, user_a):
    dar_rol(user_a, org_a, "admin-plan", "Administración", [
        "catalog.branch.create", "catalog.branch.read",
        "catalog.professional.create", "catalog.professional.read",
        "users.role.assign", "users.user.read",
    ])
    return user_a


def test_el_basico_permite_una_sucursal(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic")
    api = cliente(admin_a)
    assert api.post(reverse("catalog:branch-list"), {"name": "Sede Única"}, format="json").status_code == 201
    segunda = api.post(reverse("catalog:branch-list"), {"name": "Sede Dos"}, format="json")
    assert es_limite_de_plan(segunda)
    assert "El plan Básico de tu centro médico permite hasta 1 sucursal activa" in segunda.json()["detail"]


def test_el_premium_no_tiene_tope_de_sucursales(org_a, plans, admin_a):
    con_plan(org_a, plans, "premium")
    api = cliente(admin_a)
    for i in range(3):
        assert api.post(reverse("catalog:branch-list"), {"name": f"Sede {i}"}, format="json").status_code == 201


def test_lo_que_ya_existe_no_se_bloquea(org_a, plans, admin_a):
    """Una organización que ya pasa el tope conserva lo que tiene."""
    with tenant_context(org_a.id):
        for i in range(3):
            Branch.objects.create(organization=org_a, name=f"Previa {i}")
    con_plan(org_a, plans, "basic")
    sedes = cliente(admin_a).get(reverse("catalog:branch-list")).json()
    assert len(sedes) == 3


def test_el_tope_de_profesionales(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic", max_practitioners=1)
    api = cliente(admin_a)
    primero = api.post(reverse("catalog:professional-manage-list"), {
        "first_name": "Ana", "last_name": "Paz", "license_number": "MP-1",
    }, format="json")
    assert primero.status_code == 201
    segundo = api.post(reverse("catalog:professional-manage-list"), {
        "first_name": "Luis", "last_name": "Mena", "license_number": "MP-2",
    }, format="json")
    assert es_limite_de_plan(segundo)


# --------------------------------------------------------------------------
#  Usuarios del personal (los pacientes no cuentan)
# --------------------------------------------------------------------------

def _usuario(org, n):
    with tenant_context(org.id):
        return User.objects.create_user(
            email=f"u{n}@kolping.test", password="clave-de-prueba-1", organization=org,
            first_name="U", last_name=str(n), document_number=f"77{n}",
        )


def _rol(org, codigo):
    with tenant_context(org.id):
        return Role.objects.get_or_create(organization=org, code=codigo,
                                          defaults={"name": codigo})[0]


def asignar(admin, usuario, rol):
    return cliente(admin).post(reverse("accounts:user_role-list"),
                               {"user": str(usuario.id), "role": str(rol.id)}, format="json")


def test_el_tope_de_usuarios_cuenta_al_personal(org_a, plans, admin_a):
    # El admin ya es personal (1). Con tope 2, entra uno más y el tercero no.
    con_plan(org_a, plans, "basic", max_users=2)
    recepcion = _rol(org_a, "receptionist")
    assert asignar(admin_a, _usuario(org_a, 1), recepcion).status_code == 201
    assert es_limite_de_plan(asignar(admin_a, _usuario(org_a, 2), recepcion))


def test_los_pacientes_no_cuentan_para_el_tope(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic", max_users=1)   # sólo el admin
    paciente = _rol(org_a, "patient")
    for n in range(3):
        assert asignar(admin_a, _usuario(org_a, n), paciente).status_code == 201


def test_con_muchos_pacientes_igual_entra_personal_hasta_el_tope(org_a, plans, admin_a):
    """El conteo del tope excluye a los pacientes, no sólo la asignación.

    La prueba de arriba asigna roles de paciente, que nunca consultan el tope:
    no detectaba un conteo que sumara pacientes. Ésta sí: hay tres pacientes,
    y el tope de 2 (el admin más uno) igual deja entrar a una recepcionista.
    """
    con_plan(org_a, plans, "basic", max_users=2)
    paciente = _rol(org_a, "patient")
    for n in range(3):
        assert asignar(admin_a, _usuario(org_a, n), paciente).status_code == 201
    assert asignar(admin_a, _usuario(org_a, 50), _rol(org_a, "receptionist")).status_code == 201


def test_darle_otro_rol_a_quien_ya_es_personal_no_suma(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic", max_users=2)
    persona = _usuario(org_a, 9)
    assert asignar(admin_a, persona, _rol(org_a, "receptionist")).status_code == 201
    # Ya está en el tope, pero es la misma persona: no suma.
    assert asignar(admin_a, persona, _rol(org_a, "practitioner")).status_code == 201


# --------------------------------------------------------------------------
#  El asistente
# --------------------------------------------------------------------------

@pytest.fixture
def paciente_ia(org_a, user_a, settings):
    settings.ASSISTANT_EMBEDDING_PROVIDER = "local"
    settings.ASSISTANT_CHAT_PROVIDER = "local"
    dar_rol(user_a, org_a, "paciente-ia", "Paciente", ["assistant.suggest.use"])
    return user_a


def preguntar(user, texto="me duele la cabeza"):
    return cliente(user).post(reverse("assistant:suggest"), {"question": texto}, format="json")


def test_el_basico_no_tiene_asistente(org_a, plans, paciente_ia):
    con_plan(org_a, plans, "basic")
    respuesta = preguntar(paciente_ia)
    assert es_limite_de_plan(respuesta)
    assert "no incluye el asistente" in respuesta.json()["detail"]


def test_sin_asistente_tampoco_contesta_una_urgencia(org_a, plans, paciente_ia):
    """Un plan sin chatbot no tiene asistente: no hay un chat a medias."""
    con_plan(org_a, plans, "basic")
    assert es_limite_de_plan(preguntar(paciente_ia, "tengo un dolor de pecho muy fuerte"))


def test_el_tope_mensual_de_consultas(org_a, plans, paciente_ia):
    con_plan(org_a, plans, "pro", max_ai_queries_month=1)
    assert preguntar(paciente_ia).status_code == 200
    assert es_limite_de_plan(preguntar(paciente_ia))


def test_el_basico_no_reindexa(org_a, plans, user_a):
    dar_rol(user_a, org_a, "reindexa", "Reindexa", ["assistant.catalog.reindex"])
    con_plan(org_a, plans, "basic")
    assert es_limite_de_plan(cliente(user_a).post(reverse("assistant:reindex")))


# --------------------------------------------------------------------------
#  Reportes
# --------------------------------------------------------------------------

@pytest.fixture
def analista(org_a, user_a):
    dar_rol(user_a, org_a, "analista-plan", "Analista",
            ["reporting.report.run", "patients.patient.read"])
    return user_a


def correr(user, formato):
    return cliente(user).post(reverse("reporting:run"), {
        "dataset": "patients", "columns": ["last_name"], "format": formato,
    }, format="json")


def test_el_basico_ve_reportes_en_pantalla_pero_no_exporta(org_a, plans, analista):
    con_plan(org_a, plans, "basic")
    assert correr(analista, "json").status_code == 200
    respuesta = correr(analista, "csv")
    assert es_limite_de_plan(respuesta)
    assert "exportación de reportes" in respuesta.json()["detail"]


def test_el_pro_exporta(org_a, plans, analista):
    con_plan(org_a, plans, "pro")
    assert correr(analista, "csv").status_code == 200


# --------------------------------------------------------------------------
#  Fichas por mes
# --------------------------------------------------------------------------

def test_el_tope_mensual_de_fichas(org_a, plans):
    from appointments.models import Appointment
    from tenancy.plans import PlanLimitExceeded, appointments_this_month, check_limit
    con_plan(org_a, plans, "basic", max_appointments_month=0)
    with tenant_context(org_a.id):
        with pytest.raises(PlanLimitExceeded):
            check_limit(org_a, "max_appointments_month",
                        appointments_this_month(org_a), "fichas por mes")
        assert appointments_this_month(org_a) == Appointment.objects.count()


def test_sin_plan_vigente_no_hay_nada_habilitado(org_a, admin_a):
    with platform_admin_context():
        Subscription.objects.filter(organization=org_a).update(status=Subscription.Status.CANCELLED)
    respuesta = cliente(admin_a).post(reverse("catalog:branch-list"), {"name": "X"}, format="json")
    assert es_limite_de_plan(respuesta)


# --------------------------------------------------------------------------
#  Lo que la interfaz consulta para no ofrecer lo que el plan no incluye
# --------------------------------------------------------------------------

def test_mi_plan_dice_que_incluye_el_plan_del_centro(org_a, plans, user_a):
    con_plan(org_a, plans, "basic")
    datos = cliente(user_a).get(reverse("tenancy:my-plan")).json()
    assert datos["code"] == "basic"
    assert datos["features"]["ai_chatbot"] is False


def test_mi_plan_sin_suscripcion(org_a, user_a):
    with platform_admin_context():
        Subscription.objects.filter(organization=org_a).update(status=Subscription.Status.CANCELLED)
    datos = cliente(user_a).get(reverse("tenancy:my-plan")).json()
    assert datos == {"code": None, "name": None, "features": {}}
