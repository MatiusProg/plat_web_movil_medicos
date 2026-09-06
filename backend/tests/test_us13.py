"""US-13 — Agendas médicas.

La agenda se guarda como regla; de ella se derivan los espacios. Se prueban
las tres validaciones que definen la historia —solapamiento entre sucursales,
horario de la sucursal y vigencia—, el cupo por franja, la baja lógica y el
aislamiento entre organizaciones (RNF-08).
"""

import datetime as dt

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from catalog.models import BranchHours, Practitioner, PractitionerBranch
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


def cuerpo_agenda(practitioner, branch, **extra):
    datos = {
        "practitioner": str(practitioner.id),
        "branch": str(branch.id),
        "weekday": 0,
        "start_time": "09:00",
        "end_time": "12:00",
        "slot_minutes": 30,
        "capacity": 1,
        "valid_from": proximo_lunes().isoformat(),
    }
    datos.update(extra)
    return datos


def test_una_regla_deriva_los_espacios_reservables(
    api_client, staff_a, org_a, practitioner_a, branches_a,
):
    api = autenticar(api_client, staff_a)

    creacion = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(practitioner_a, branches_a["centro"]),
        format="json",
    )
    assert creacion.status_code == 201, creacion.content

    lunes = proximo_lunes()
    calendario = api.get(
        reverse("scheduling:schedule-calendar"),
        {"practitioner": str(practitioner_a.id), "week": lunes.isoformat()},
    )
    assert calendario.status_code == 200
    dias = {d["date"]: d["slots"] for d in calendario.json()["days"]}
    # 09:00 a 12:00 de a 30 minutos = 6 espacios, todos el lunes.
    assert len(dias[lunes.isoformat()]) == 6
    assert dias[lunes.isoformat()][0]["start"].endswith("09:00:00-04:00")
    otro_dia = (lunes + dt.timedelta(days=1)).isoformat()
    assert dias[otro_dia] == []


def test_solapamiento_rechazado_entre_sucursales(
    api_client, staff_a, org_a, practitioner_a, branches_a,
):
    api = autenticar(api_client, staff_a)
    api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(practitioner_a, branches_a["centro"]),
        format="json",
    )

    # Misma profesional, mismo lunes, otra sucursal, horario que se pisa.
    respuesta = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(
            practitioner_a, branches_a["norte"],
            start_time="11:00", end_time="14:00",
        ),
        format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "agenda_solapada"


def test_agenda_fuera_del_horario_de_la_sucursal(
    api_client, staff_a, org_a, practitioner_a, branches_a,
):
    with tenant_context(org_a.id):
        BranchHours.objects.create(
            organization=org_a, branch=branches_a["centro"],
            weekday=0, opens_at="08:00", closes_at="12:00",
        )
    api = autenticar(api_client, staff_a)

    fuera = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(
            practitioner_a, branches_a["centro"],
            start_time="09:00", end_time="14:00",
        ),
        format="json",
    )
    assert fuera.status_code == 400
    assert fuera.json()["code"] == "fuera_de_horario"

    dentro = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(practitioner_a, branches_a["centro"]),
        format="json",
    )
    assert dentro.status_code == 201, dentro.content


def test_sin_horario_de_sucursal_no_se_valida(
    api_client, staff_a, practitioner_a, branches_a,
):
    api = autenticar(api_client, staff_a)
    respuesta = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(
            practitioner_a, branches_a["centro"],
            start_time="06:00", end_time="23:00",
        ),
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.content


def test_la_vigencia_saca_la_regla_del_calendario(
    api_client, staff_a, org_a, practitioner_a, branches_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=0,
            start_time="09:00", end_time="12:00", slot_minutes=30,
            valid_from=lunes - dt.timedelta(days=30),
            valid_until=lunes - dt.timedelta(days=1),
        )
    api = autenticar(api_client, staff_a)
    calendario = api.get(
        reverse("scheduling:schedule-calendar"),
        {"practitioner": str(practitioner_a.id), "week": lunes.isoformat()},
    )
    dias = {d["date"]: d["slots"] for d in calendario.json()["days"]}
    assert dias[lunes.isoformat()] == []


def test_cupo_por_franja_mayor_a_uno(
    api_client, staff_a, practitioner_a, branches_a,
):
    api = autenticar(api_client, staff_a)
    creacion = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(practitioner_a, branches_a["centro"], capacity=3),
        format="json",
    )
    assert creacion.status_code == 201
    assert creacion.json()["capacity"] == 3


def test_la_baja_es_logica(
    api_client, staff_a, org_a, practitioner_a, branches_a,
):
    with tenant_context(org_a.id):
        agenda = Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=0,
            start_time="09:00", end_time="12:00", slot_minutes=30,
            valid_from=proximo_lunes(),
        )
    api = autenticar(api_client, staff_a)
    respuesta = api.delete(
        reverse("scheduling:schedule-detail", args=[agenda.id]),
    )
    assert respuesta.status_code == 204
    with tenant_context(org_a.id):
        agenda.refresh_from_db()
        assert agenda.is_active is False


@pytest.mark.isolation
def test_no_se_crea_una_agenda_para_un_profesional_de_otra_organizacion(
    api_client, staff_a, org_b,
):
    with tenant_context(org_b.id):
        from catalog.models import Branch
        sucursal_b = Branch.objects.create(organization=org_b, name="Sede B")
        profesional_b = Practitioner.objects.create(
            organization=org_b, first_name="Otro", last_name="Médico",
        )
        PractitionerBranch.objects.create(
            organization=org_b, practitioner=profesional_b, branch=sucursal_b,
        )

    api = autenticar(api_client, staff_a)
    respuesta = api.post(
        reverse("scheduling:schedule-list"),
        cuerpo_agenda(profesional_b, sucursal_b),
        format="json",
    )
    # RLS deja invisible al profesional de B: el serializer lo rechaza.
    assert respuesta.status_code == 400
    assert "practitioner" in respuesta.json()


@pytest.mark.isolation
def test_el_listado_no_muestra_agendas_de_otra_organizacion(
    api_client, staff_a, staff_b, org_a, org_b, branches_a, practitioner_a,
):
    with tenant_context(org_a.id):
        Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=0,
            start_time="09:00", end_time="12:00", slot_minutes=30,
            valid_from=proximo_lunes(),
        )
    with tenant_context(org_b.id):
        from catalog.models import Branch
        sucursal_b = Branch.objects.create(organization=org_b, name="Sede B")
        profesional_b = Practitioner.objects.create(
            organization=org_b, first_name="Otro", last_name="Médico",
        )
        Schedule.objects.create(
            organization=org_b, practitioner=profesional_b, branch=sucursal_b,
            weekday=0, start_time="09:00", end_time="12:00", slot_minutes=30,
            valid_from=proximo_lunes(),
        )

    listado = autenticar(api_client, staff_a).get(
        reverse("scheduling:schedule-list"),
    )
    assert listado.status_code == 200
    resultados = listado.json()["results"]
    assert len(resultados) == 1
    assert resultados[0]["practitioner"] == str(practitioner_a.id)
