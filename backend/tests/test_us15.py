"""US-15 — Disponibilidad consolidada.

Los espacios libres de un profesional entre **todas** sus sucursales, en una
sola vista, ordenados y etiquetados con la sede. Menos de 3 segundos (RNF-02):
una consulta por rango, no una por día. El corte de "hora ya pasada" se
calcula en la zona de la sucursal.
"""

import datetime as dt
import time
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from scheduling.availability import consolidated_availability
from scheduling.models import Schedule
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
def agendas_tres_sedes(db, org_a, practitioner_a, branches_a):
    """La misma profesional atiende lunes en Centro, martes en Norte y
    miércoles en Sur."""
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        for weekday, sede in enumerate(("centro", "norte", "sur")):
            Schedule.objects.create(
                organization=org_a, practitioner=practitioner_a,
                branch=branches_a[sede], weekday=weekday,
                start_time="09:00", end_time="11:00", slot_minutes=60,
                valid_from=lunes - dt.timedelta(days=7),
            )


def test_consolida_las_tres_sucursales_ordenado_y_etiquetado(
    api_client, patient_a, practitioner_a, agendas_tres_sedes,
):
    lunes = proximo_lunes()
    respuesta = autenticar(api_client, patient_a).get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": lunes.isoformat(),
            "to": (lunes + dt.timedelta(days=6)).isoformat(),
        },
    )
    assert respuesta.status_code == 200
    dias = respuesta.json()["days"]
    fechas = [d["date"] for d in dias]
    assert fechas == sorted(fechas)
    sedes_por_dia = {
        d["date"]: {s["branch"]["name"] for s in d["slots"]} for d in dias
    }
    assert sedes_por_dia[lunes.isoformat()] == {"Sede Centro"}
    assert sedes_por_dia[(lunes + dt.timedelta(days=1)).isoformat()] == {"Sede Norte"}
    assert sedes_por_dia[(lunes + dt.timedelta(days=2)).isoformat()] == {"Sede Sur"}


def test_rango_mayor_al_horizonte_devuelve_400(
    api_client, patient_a, practitioner_a,
):
    hoy = dt.date.today()
    respuesta = autenticar(api_client, patient_a).get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": hoy.isoformat(),
            "to": (hoy + dt.timedelta(days=45)).isoformat(),
        },
    )
    assert respuesta.status_code == 400
    assert "días" in respuesta.json()["detail"]


def test_corte_de_hora_pasada_en_la_zona_de_la_sucursal(
    db, org_a, practitioner_a, branches_a,
):
    hoy = dt.date.today()
    with tenant_context(org_a.id):
        Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=hoy.weekday(),
            start_time="09:00", end_time="12:00", slot_minutes=60,
            valid_from=hoy - dt.timedelta(days=7),
        )
        ahora = dt.datetime.combine(hoy, dt.time(10, 30), tzinfo=LAPAZ)
        data = consolidated_availability(
            practitioner_id=practitioner_a.id,
            date_from=hoy, date_to=hoy, now=ahora,
        )
    horas = [s["start"][11:16] for d in data["days"] for s in d["slots"]]
    # 09:00 y 10:00 ya pasaron a las 10:30; queda 11:00.
    assert horas == ["11:00"]


def test_profesional_inactivo_deja_los_espacios_no_reservables(
    api_client, patient_a, org_a, practitioner_a, agendas_tres_sedes,
):
    with tenant_context(org_a.id):
        practitioner_a.is_active = False
        practitioner_a.save(update_fields=["is_active"])
    lunes = proximo_lunes()
    respuesta = autenticar(api_client, patient_a).get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": lunes.isoformat(),
            "to": lunes.isoformat(),
        },
    )
    slots = respuesta.json()["days"][0]["slots"]
    assert slots  # no desaparecen
    assert all(s["reservable"] is False for s in slots)
    assert all(s["reason"] == "profesional_inactivo" for s in slots)


def test_sucursal_inactiva_deja_los_espacios_no_reservables(
    api_client, patient_a, org_a, practitioner_a, branches_a,
):
    lunes = proximo_lunes()
    with tenant_context(org_a.id):
        Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=0,
            start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=lunes - dt.timedelta(days=7),
        )
        branches_a["centro"].is_active = False
        branches_a["centro"].save(update_fields=["is_active"])
    respuesta = autenticar(api_client, patient_a).get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(practitioner_a.id),
            "from": lunes.isoformat(),
            "to": lunes.isoformat(),
        },
    )
    slots = respuesta.json()["days"][0]["slots"]
    assert slots
    assert all(s["reason"] == "sucursal_inactiva" for s in slots)


@pytest.mark.isolation
def test_un_paciente_no_ve_la_disponibilidad_de_otra_organizacion(
    api_client, patient_a, org_b,
):
    with tenant_context(org_b.id):
        from catalog.models import Branch, Practitioner
        sede_b = Branch.objects.create(organization=org_b, name="Sede B")
        profesional_b = Practitioner.objects.create(
            organization=org_b, first_name="Otra", last_name="Médica",
        )
        Schedule.objects.create(
            organization=org_b, practitioner=profesional_b, branch=sede_b,
            weekday=0, start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=proximo_lunes() - dt.timedelta(days=7),
        )
    respuesta = autenticar(api_client, patient_a).get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(profesional_b.id),
            "from": proximo_lunes().isoformat(),
            "to": proximo_lunes().isoformat(),
        },
    )
    # RLS deja invisible al profesional de B.
    assert respuesta.status_code == 400
    assert "no existe" in respuesta.json()["detail"]


@pytest.mark.isolation
def test_aislamiento_en_orm_con_contexto_de_otra_organizacion(
    db, org_a, org_b, practitioner_a, agendas_tres_sedes,
):
    from django.core.exceptions import ValidationError

    with tenant_context(org_b.id):
        with pytest.raises(ValidationError):
            consolidated_availability(
                practitioner_id=practitioner_a.id,
                date_from=proximo_lunes(),
                date_to=proximo_lunes(),
            )


def test_rnf_02_el_costo_no_crece_con_el_rango_y_baja_de_tres_segundos(
    api_client, patient_a, org_a, practitioner_a, branches_a,
):
    """Tres sucursales, catorce días: el bucle ingenuo son 42 idas a la base.
    Acá la cantidad de consultas es la misma para un día que para dos semanas
    —se resuelve por rango— y la respuesta baja de 3 segundos."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    inicio = proximo_lunes()
    with tenant_context(org_a.id):
        for weekday in range(7):
            for sede in branches_a.values():
                Schedule.objects.create(
                    organization=org_a, practitioner=practitioner_a,
                    branch=sede, weekday=weekday,
                    start_time="08:00", end_time="17:00", slot_minutes=20,
                    valid_from=inicio - dt.timedelta(days=7),
                )
    api = autenticar(api_client, patient_a)
    url = reverse("scheduling:availability")

    def pedir(dias):
        return api.get(url, {
            "practitioner": str(practitioner_a.id),
            "from": inicio.isoformat(),
            "to": (inicio + dt.timedelta(days=dias)).isoformat(),
        })

    assert pedir(0).status_code == 200  # calienta cachés de permisos

    with CaptureQueriesContext(connection) as un_dia:
        arranque = time.perf_counter()
        assert pedir(0).status_code == 200
        assert time.perf_counter() - arranque < 3.0

    with CaptureQueriesContext(connection) as dos_semanas:
        arranque = time.perf_counter()
        respuesta = pedir(13)
        assert time.perf_counter() - arranque < 3.0

    assert len(un_dia) == len(dos_semanas), (
        len(un_dia), len(dos_semanas),
    )
    total = sum(len(d["slots"]) for d in respuesta.json()["days"])
    assert total > 0
