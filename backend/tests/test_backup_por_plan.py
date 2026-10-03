"""Característica general 6 — La frecuencia de las copias depende del plan.

    Básico    una copia por semana
    Pro       una copia por día
    Premium   a voluntad

Lo que se limita es **generar** la copia. Restaurar nunca: recuperarse de un
desastre no puede depender de cuánto paga el cliente.
"""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from accounts.tokens import tokens_for_user
from backups.models import BackupRecord
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Subscription

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

PERMISOS = ["backups.backup.create", "backups.backup.restore"]


def cliente(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}")
    return client


@pytest.fixture
def admin_a(org_a, user_a):
    dar_rol(user_a, org_a, "admin-respaldos", "Administración", PERMISOS)
    return user_a


def con_plan(org, plans, codigo):
    with platform_admin_context():
        Subscription.objects.filter(organization=org).update(plan=plans[codigo])


def respaldar(user):
    return cliente(user).post(reverse("backups:create"))


def politica(user):
    return cliente(user).get(reverse("backups:policy")).json()


def atrasar_ultima_copia(org, horas):
    """Simula que la última copia se hizo hace `horas` horas."""
    with tenant_context(org.id):
        ultima = BackupRecord.objects.filter(organization=org).latest("created_at")
        BackupRecord.objects.filter(pk=ultima.pk).update(
            created_at=timezone.now() - dt.timedelta(hours=horas),
        )


# --------------------------------------------------------------------------
#  Los tres planes
# --------------------------------------------------------------------------

def test_el_plan_basico_permite_una_copia_por_semana(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic")
    assert respaldar(admin_a).status_code == 200
    segunda = respaldar(admin_a)
    assert segunda.status_code == 429
    assert segunda.json()["code"] == "backup_limit"
    assert "una copia por semana" in segunda.json()["detail"]
    # Seis días después todavía no; siete, sí.
    atrasar_ultima_copia(org_a, 24 * 6)
    assert respaldar(admin_a).status_code == 429
    atrasar_ultima_copia(org_a, 24 * 7)
    assert respaldar(admin_a).status_code == 200


def test_el_plan_pro_permite_una_copia_por_dia(org_a, plans, admin_a):
    con_plan(org_a, plans, "pro")
    assert respaldar(admin_a).status_code == 200
    assert respaldar(admin_a).status_code == 429
    atrasar_ultima_copia(org_a, 25)
    assert respaldar(admin_a).status_code == 200


def test_el_plan_premium_respalda_a_voluntad(org_a, plans, admin_a):
    con_plan(org_a, plans, "premium")
    for _ in range(3):
        assert respaldar(admin_a).status_code == 200


# --------------------------------------------------------------------------
#  La política que ve la pantalla
# --------------------------------------------------------------------------

def test_la_politica_dice_la_regla_y_la_proxima_fecha(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic")
    antes = politica(admin_a)
    assert antes["plan_code"] == "basic"
    assert antes["interval_hours"] == 168
    assert antes["allowed_now"] is True
    assert antes["next_available_at"] is None

    respaldar(admin_a)
    despues = politica(admin_a)
    assert despues["allowed_now"] is False
    assert despues["next_available_at"] is not None
    assert despues["description"] == "Tu plan Básico permite una copia por semana."


def test_la_politica_de_premium_no_tiene_proxima_fecha(org_a, plans, admin_a):
    con_plan(org_a, plans, "premium")
    respaldar(admin_a)
    datos = politica(admin_a)
    assert datos["interval_hours"] is None
    assert datos["allowed_now"] is True
    assert "a voluntad" in datos["description"]


# --------------------------------------------------------------------------
#  Los bordes
# --------------------------------------------------------------------------

def test_el_limite_es_de_la_organizacion_no_de_cada_administrador(org_a, plans, admin_a):
    """Si contara por persona, dos administradores duplicarían la cuota."""
    con_plan(org_a, plans, "pro")
    with tenant_context(org_a.id):
        otro = User.objects.create_user(
            email="otro.admin@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Otro", last_name="Admin",
            document_number="9999",
        )
    dar_rol(otro, org_a, "admin-respaldos-2", "Administración 2", PERMISOS)
    assert respaldar(admin_a).status_code == 200
    assert respaldar(otro).status_code == 429


def test_restaurar_no_depende_del_plan(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic")
    archivo = respaldar(admin_a).content
    assert respaldar(admin_a).status_code == 429   # sin cuota para respaldar…
    from django.core.files.uploadedfile import SimpleUploadedFile
    respuesta = cliente(admin_a).post(reverse("backups:restore"), {
        "file": SimpleUploadedFile("copia.json", archivo, content_type="application/json"),
        "confirm": "true",
    }, format="multipart")
    assert respuesta.status_code == 200            # …pero sí para restaurar


def test_sin_plan_vigente_no_se_respalda(org_a, admin_a):
    with platform_admin_context():
        Subscription.objects.filter(organization=org_a).update(
            status=Subscription.Status.CANCELLED,
        )
    respuesta = respaldar(admin_a)
    assert respuesta.status_code == 403
    assert politica(admin_a)["allowed_now"] is False


def test_la_copia_rechazada_no_queda_en_el_historial(org_a, plans, admin_a):
    con_plan(org_a, plans, "basic")
    respaldar(admin_a)
    respaldar(admin_a)
    with tenant_context(org_a.id):
        assert BackupRecord.objects.filter(kind="backup").count() == 1


def test_los_planes_del_sistema_traen_su_frecuencia(plans):
    assert plans["basic"].features["backup_interval_hours"] == 168
    assert plans["pro"].features["backup_interval_hours"] == 24
    assert plans["premium"].features["backup_interval_hours"] is None
