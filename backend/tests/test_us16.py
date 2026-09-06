"""US-16 — Búsqueda de profesionales.

Búsqueda por nombre (parcial, sin distinguir mayúsculas ni tildes) y filtros
por especialidad y por sucursal. Búsqueda vacía devuelve el catálogo paginado.
Sólo profesionales activos y de la organización del paciente (RNF-08).
"""

import datetime as dt

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from catalog.models import (
    Practitioner,
    PractitionerBranch,
    PractitionerSpecialty,
    Specialty,
)
from scheduling.models import Schedule
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def proximo_lunes():
    hoy = dt.date.today()
    return hoy + dt.timedelta(days=(7 - hoy.weekday()) % 7 or 7)


@pytest.fixture
def catalogo_a(db, org_a, branches_a):
    with tenant_context(org_a.id):
        cardio = Specialty.objects.create(organization=org_a, name="Cardiología")
        pedia = Specialty.objects.create(organization=org_a, name="Pediatría")

        gonzalez = Practitioner.objects.create(
            organization=org_a, first_name="Marta", last_name="González",
        )
        PractitionerSpecialty.objects.create(
            organization=org_a, practitioner=gonzalez, specialty=cardio,
        )
        PractitionerBranch.objects.create(
            organization=org_a, practitioner=gonzalez, branch=branches_a["centro"],
        )

        perez = Practitioner.objects.create(
            organization=org_a, first_name="Juan", last_name="Pérez",
        )
        PractitionerSpecialty.objects.create(
            organization=org_a, practitioner=perez, specialty=pedia,
        )
        PractitionerBranch.objects.create(
            organization=org_a, practitioner=perez, branch=branches_a["norte"],
        )

        inactivo = Practitioner.objects.create(
            organization=org_a, first_name="Ex", last_name="Médico",
            is_active=False,
        )
    return {"cardio": cardio, "pedia": pedia, "gonzalez": gonzalez,
            "perez": perez, "inactivo": inactivo}


def nombres(respuesta):
    return {r["full_name"] for r in respuesta.json()["results"]}


def test_busqueda_por_nombre_parcial_y_sin_tildes(
    api_client, patient_a, catalogo_a,
):
    api = autenticar(api_client, patient_a)
    respuesta = api.get(reverse("catalog:professional-search"), {"q": "gonzalez"})
    assert respuesta.status_code == 200
    assert nombres(respuesta) == {"Marta González"}


def test_filtro_por_especialidad(api_client, patient_a, catalogo_a):
    api = autenticar(api_client, patient_a)
    respuesta = api.get(
        reverse("catalog:professional-search"),
        {"specialty": str(catalogo_a["pedia"].id)},
    )
    assert nombres(respuesta) == {"Juan Pérez"}


def test_filtro_por_sucursal(api_client, patient_a, catalogo_a, branches_a):
    api = autenticar(api_client, patient_a)
    respuesta = api.get(
        reverse("catalog:professional-search"),
        {"branch": str(branches_a["centro"].id)},
    )
    assert nombres(respuesta) == {"Marta González"}


def test_busqueda_vacia_devuelve_el_catalogo_paginado(
    api_client, patient_a, catalogo_a,
):
    api = autenticar(api_client, patient_a)
    respuesta = api.get(reverse("catalog:professional-search"))
    cuerpo = respuesta.json()
    assert "results" in cuerpo and "count" in cuerpo
    # Sólo los activos: no aparece "Ex Médico".
    assert nombres(respuesta) == {"Marta González", "Juan Pérez"}


def test_cada_resultado_trae_el_proximo_espacio_disponible(
    api_client, patient_a, org_a, catalogo_a, branches_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        Schedule.objects.create(
            organization=org_a, practitioner=catalogo_a["gonzalez"],
            branch=branches_a["centro"], weekday=lunes.weekday(),
            start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=lunes - dt.timedelta(days=7),
        )
    api = autenticar(api_client, patient_a)
    respuesta = api.get(reverse("catalog:professional-search"), {"q": "gonzalez"})
    tarjeta = respuesta.json()["results"][0]
    assert tarjeta["next_available_slot"] is not None
    assert tarjeta["next_available_slot"].startswith(lunes.isoformat())
    # Pérez no tiene agenda: su próximo espacio es None.
    perez = api.get(
        reverse("catalog:professional-search"), {"q": "perez"},
    ).json()["results"][0]
    assert perez["next_available_slot"] is None


@pytest.mark.isolation
def test_solo_profesionales_de_la_organizacion_del_paciente(
    api_client, patient_a, org_b,
):
    with tenant_context(org_b.id):
        from catalog.models import Branch
        sede_b = Branch.objects.create(organization=org_b, name="Sede B")
        ajeno = Practitioner.objects.create(
            organization=org_b, first_name="Ajeno", last_name="González",
        )
        PractitionerBranch.objects.create(
            organization=org_b, practitioner=ajeno, branch=sede_b,
        )
    respuesta = autenticar(api_client, patient_a).get(
        reverse("catalog:professional-search"), {"q": "gonzalez"},
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["results"] == []


@pytest.mark.isolation
def test_aislamiento_en_orm(db, org_a, org_b):
    with tenant_context(org_b.id):
        Practitioner.objects.create(
            organization=org_b, first_name="Solo", last_name="B",
        )
    with tenant_context(org_a.id):
        assert Practitioner.objects.count() == 0
