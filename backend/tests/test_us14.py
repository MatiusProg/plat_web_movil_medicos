"""US-14 — Bloqueo de agenda.

Los espacios bloqueados dejan de ofrecerse en la disponibilidad, pero la regla
de agenda no se toca: al levantar el bloqueo, la agenda vuelve sola. Un
feriado de organización (sin profesional) afecta a todos.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from scheduling.models import Schedule, ScheduleBlock
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db

LAPAZ = ZoneInfo("America/La_Paz")


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
def agenda_a(db, org_a, practitioner_a, branches_a):
    """Una regla: lunes 09:00–12:00, consultas de 30 minutos."""
    with tenant_context(org_a.id):
        return Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=0,
            start_time="09:00", end_time="12:00", slot_minutes=30,
            valid_from=proximo_lunes() - dt.timedelta(days=7),
        )


def disponibilidad(api, practitioner):
    lunes = proximo_lunes()
    return api.get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner.id),
            "from": lunes.isoformat(),
            "to": lunes.isoformat(),
        },
    )


def horas_libres(respuesta, fecha):
    for dia in respuesta.json()["days"]:
        if dia["date"] == fecha:
            return [slot["start"][11:16] for slot in dia["slots"]]
    return []


def test_un_bloqueo_oculta_los_espacios_de_su_rango(
    api_client, staff_a, org_a, practitioner_a, agenda_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        ScheduleBlock.objects.create(
            organization=org_a, practitioner=practitioner_a,
            starts_at=dt.datetime.combine(lunes, dt.time(9, 0), tzinfo=LAPAZ),
            ends_at=dt.datetime.combine(lunes, dt.time(11, 0), tzinfo=LAPAZ),
            reason="leave",
        )
    api = autenticar(api_client, staff_a)
    libres = horas_libres(disponibilidad(api, practitioner_a), lunes.isoformat())
    # 09:00, 09:30, 10:00, 10:30 caen dentro del bloqueo; quedan 11:00 y 11:30.
    assert libres == ["11:00", "11:30"]


def test_bloqueo_de_franja_de_un_dia(
    api_client, staff_a, org_a, practitioner_a, agenda_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        ScheduleBlock.objects.create(
            organization=org_a, practitioner=practitioner_a,
            starts_at=dt.datetime.combine(lunes, dt.time(10, 0), tzinfo=LAPAZ),
            ends_at=dt.datetime.combine(lunes, dt.time(11, 0), tzinfo=LAPAZ),
            reason="absence",
        )
    api = autenticar(api_client, staff_a)
    libres = horas_libres(disponibilidad(api, practitioner_a), lunes.isoformat())
    assert libres == ["09:00", "09:30", "11:00", "11:30"]


def test_feriado_de_organizacion_afecta_a_todos(
    api_client, staff_a, org_a, practitioner_a, agenda_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        ScheduleBlock.objects.create(
            organization=org_a, practitioner=None,  # feriado de la organización
            starts_at=dt.datetime.combine(lunes, dt.time(0, 0), tzinfo=LAPAZ),
            ends_at=dt.datetime.combine(
                lunes + dt.timedelta(days=1), dt.time(0, 0), tzinfo=LAPAZ,
            ),
            reason="holiday",
        )
    api = autenticar(api_client, staff_a)
    libres = horas_libres(disponibilidad(api, practitioner_a), lunes.isoformat())
    assert libres == []


def test_levantar_el_bloqueo_devuelve_los_espacios(
    api_client, staff_a, org_a, practitioner_a, agenda_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        bloqueo = ScheduleBlock.objects.create(
            organization=org_a, practitioner=practitioner_a,
            starts_at=dt.datetime.combine(lunes, dt.time(9, 0), tzinfo=LAPAZ),
            ends_at=dt.datetime.combine(lunes, dt.time(12, 0), tzinfo=LAPAZ),
            reason="vacation",
        )
    api = autenticar(api_client, staff_a)
    assert horas_libres(disponibilidad(api, practitioner_a), lunes.isoformat()) == []

    levantar = api.post(reverse("scheduling:block-lift", args=[bloqueo.id]))
    assert levantar.status_code == 200
    assert levantar.json()["is_active"] is False

    libres = horas_libres(disponibilidad(api, practitioner_a), lunes.isoformat())
    assert len(libres) == 6


def test_fichas_afectadas_por_ahora_vacio(
    api_client, staff_a, org_a, practitioner_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        bloqueo = ScheduleBlock.objects.create(
            organization=org_a, practitioner=practitioner_a,
            starts_at=dt.datetime.combine(lunes, dt.time(9, 0), tzinfo=LAPAZ),
            ends_at=dt.datetime.combine(lunes, dt.time(12, 0), tzinfo=LAPAZ),
            reason="vacation",
        )
    api = autenticar(api_client, staff_a)
    respuesta = api.get(reverse("scheduling:block-affected", args=[bloqueo.id]))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"count": 0, "appointments": []}


def test_se_crea_un_feriado_omitiendo_el_profesional(
    api_client, staff_a, org_a,
):
    lunes = proximo_lunes()
    api = autenticar(api_client, staff_a)
    respuesta = api.post(
        reverse("scheduling:block-list"),
        {
            "starts_at": dt.datetime.combine(
                lunes, dt.time(0, 0), tzinfo=LAPAZ,
            ).isoformat(),
            "ends_at": dt.datetime.combine(
                lunes + dt.timedelta(days=1), dt.time(0, 0), tzinfo=LAPAZ,
            ).isoformat(),
            "reason": "holiday",
        },
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.content
    assert respuesta.json()["practitioner"] is None


@pytest.mark.isolation
def test_no_se_levanta_un_bloqueo_de_otra_organizacion(
    api_client, staff_a, org_b,
):
    with tenant_context(org_b.id):
        from catalog.models import Practitioner
        profesional_b = Practitioner.objects.create(
            organization=org_b, first_name="Otro", last_name="Médico",
        )
        bloqueo_b = ScheduleBlock.objects.create(
            organization=org_b, practitioner=profesional_b,
            starts_at=dt.datetime(2026, 12, 1, 9, tzinfo=LAPAZ),
            ends_at=dt.datetime(2026, 12, 1, 12, tzinfo=LAPAZ),
            reason="vacation",
        )
    respuesta = autenticar(api_client, staff_a).post(
        reverse("scheduling:block-lift", args=[bloqueo_b.id]),
    )
    assert respuesta.status_code == 404
