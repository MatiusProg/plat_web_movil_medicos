"""US-12 â€” API, permisos, asociaciones, bajas e aislamiento multi-tenant."""
import datetime as dt
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.tokens import tokens_for_user
from catalog.models import (
    Specialty, Practitioner, PractitionerBranch, PractitionerSpecialty,
)
from scheduling.models import Schedule
from tenancy.context import tenant_context
from tests.conftest import dar_rol

pytestmark = pytest.mark.django_db

CODES = [
    "catalog.specialty.create", "catalog.specialty.read", "catalog.specialty.update",
    "catalog.professional.create", "catalog.professional.read", "catalog.professional.update",
]

@pytest.fixture
def admin_a(user_a, org_a):
    dar_rol(user_a, org_a, "catalog_manager", "Gestor de catÃ¡logo", CODES)
    return user_a

def api(user):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}")
    return client

def url(name, pk=None):
    return reverse("catalog:" + name, args=[pk] if pk else [])

def data_professional(specialty, branch, **extra):
    data = {
        "first_name": "Maria", "last_name": "Perez", "license_number": "MP-9012",
        "specialties": [str(specialty.pk)], "branches": [str(branch.pk)],
    }
    data.update(extra)
    return data

def test_especialidad_crear_editar_y_detectar_duplicado(admin_a, org_a):
    client = api(admin_a)
    created = client.post(url("specialty-list"), {"name": "  NeurologÃ­a  ", "description": "Sistema nervioso."}, format="json")
    assert created.status_code == 201, created.content
    pk = created.json()["id"]
    assert created.json()["name"] == "NeurologÃ­a"
    edited = client.patch(url("specialty-detail", pk), {"description": "Consulta neurolÃ³gica."}, format="json")
    assert edited.status_code == 200, edited.content
    assert edited.json()["description"] == "Consulta neurolÃ³gica."
    duplicate = client.post(url("specialty-list"), {"name": "neurologÃ­a"}, format="json")
    assert duplicate.status_code == 400

def test_profesional_y_asociaciones_se_guardan_y_actualizan(admin_a, org_a, branches_a, specialty_a):
    client = api(admin_a)
    created = client.post(url("professional-manage-list"),
                          data_professional(specialty_a, branches_a["centro"]), format="json")
    assert created.status_code == 201, created.content
    pk = created.json()["id"]
    assert len(created.json()["specialties"]) == 1
    assert len(created.json()["branches"]) == 1
    updated = client.patch(url("professional-detail", pk), {
        "first_name": "Maria Jose",
        "branches": [str(branches_a["norte"].pk), str(branches_a["sur"].pk)],
    }, format="json")
    assert updated.status_code == 200, updated.content
    assert len(updated.json()["branches"]) == 2
    with tenant_context(org_a.id):
        obj = Practitioner.objects.get(pk=pk)
        assert obj.search_name == "maria jose perez"
        assert set(obj.branches.values_list("pk", flat=True)) == {
            branches_a["norte"].pk, branches_a["sur"].pk,
        }

def test_no_se_aceptan_referencias_de_otro_tenant(admin_a, org_a, org_b, branch_b, specialty_a):
    client = api(admin_a)
    response = client.post(url("professional-manage-list"),
                           data_professional(specialty_a, branch_b), format="json")
    assert response.status_code == 400
    with tenant_context(org_a.id):
        assert not Practitioner.objects.filter(license_number="MP-9012").exists()

@pytest.mark.isolation
def test_no_se_puede_leer_editar_ni_desactivar_un_profesional_ajeno(admin_a, org_b):
    with tenant_context(org_b.id):
        foreign = Practitioner.objects.create(organization=org_b, first_name="Otro", last_name="MÃ©dico")
    client = api(admin_a)
    for method, endpoint in [
        ("get", url("professional-detail", foreign.pk)),
        ("patch", url("professional-detail", foreign.pk)),
        ("post", url("professional-deactivate", foreign.pk)),
    ]:
        kwargs = {"data": {"first_name": "Intruso"}, "format": "json"} if method == "patch" else {}
        response = getattr(client, method)(endpoint, **kwargs)
        assert response.status_code == 404, response.content

def test_usuario_sin_permiso_de_escritura_no_puede_crear(patient_a, specialty_a):
    client = api(patient_a)
    response = client.post(url("professional-manage-list"), {
        "first_name": "Sin", "last_name": "Permiso",
    }, format="json")
    assert response.status_code == 403
    assert client.get(url("specialty-list")).status_code == 200

def test_baja_logica_no_borra_asociaciones(admin_a, org_a, branches_a, specialty_a):
    client = api(admin_a)
    created = client.post(url("professional-manage-list"),
                          data_professional(specialty_a, branches_a["centro"]), format="json")
    pk = created.json()["id"]
    response = client.post(url("professional-deactivate", pk))
    assert response.status_code == 200, response.content
    assert response.json()["is_active"] is False
    with tenant_context(org_a.id):
        assert Practitioner.objects.filter(pk=pk, is_active=False).exists()
        assert PractitionerSpecialty.objects.filter(practitioner_id=pk).count() == 1
        assert PractitionerBranch.objects.filter(practitioner_id=pk).count() == 1
    assert all(row["id"] != pk for row in client.get(url("professional-search")).json()["results"])

def test_no_se_quita_sucursal_con_agenda_activa(admin_a, org_a, branches_a, specialty_a):
    client = api(admin_a)
    created = client.post(url("professional-manage-list"),
                          data_professional(specialty_a, branches_a["centro"]), format="json")
    pk = created.json()["id"]
    with tenant_context(org_a.id):
        practitioner = Practitioner.objects.get(pk=pk)
        Schedule.objects.create(
            organization=org_a, practitioner=practitioner,
            branch=branches_a["centro"], weekday=0,
            start_time=dt.time(9), end_time=dt.time(12),
            slot_minutes=30, capacity=1, valid_from=dt.date.today(),
        )
    response = client.patch(url("professional-detail", pk), {"branches": []}, format="json")
    assert response.status_code == 400, response.content
    with tenant_context(org_a.id):
        assert PractitionerBranch.objects.filter(practitioner_id=pk).count() == 1
    assert client.post(url("professional-deactivate", pk)).status_code == 400

def test_baja_de_especialidad_con_profesionales_activos_se_rechaza(admin_a, org_a, branches_a, specialty_a):
    client = api(admin_a)
    client.post(url("professional-manage-list"),
                data_professional(specialty_a, branches_a["centro"]), format="json")
    response = client.post(url("specialty-deactivate", specialty_a.pk))
    assert response.status_code == 400
    with tenant_context(org_a.id):
        specialty_a.refresh_from_db()
        assert specialty_a.is_active

def test_matricula_duplicada_y_asociaciones_repetidas(admin_a, branches_a, specialty_a):
    client = api(admin_a)
    data = data_professional(specialty_a, branches_a["centro"])
    assert client.post(url("professional-manage-list"), data, format="json").status_code == 201
    assert client.post(url("professional-manage-list"), data, format="json").status_code == 400
    data["license_number"] = "MP-9013"
    data["specialties"] = [str(specialty_a.pk)] * 2
    assert client.post(url("professional-manage-list"), data, format="json").status_code == 400

