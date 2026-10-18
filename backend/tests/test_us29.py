"""US-29 — Panel de KPIs: ocupación, inasistencia, demanda e ingresos.

Las definiciones están en `docs/sprints/sprint-3/us-29-indicadores.md`.
"""

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from django.utils import timezone

from catalog.models import (
    Branch,
    Practitioner,
    PractitionerBranch,
    PractitionerSpecialty,
    Specialty,
)
from payments.models import Payment
from scheduling.models import Schedule, ScheduleBlock
from tenancy.context import tenant_context

from .conftest import dar_rol
from .fichas_comunes import (  # noqa: F401  (fixtures)
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    paciente_a,
    perfil_paciente,
)

LA_PAZ = ZoneInfo("America/La_Paz")


def hace(dias, *, hora=None):
    """Una hora redonda `dias` atrás (o adelante si es negativo)."""
    base = timezone.now() - dt.timedelta(days=dias)
    return base.replace(minute=0, second=0, microsecond=0)


def rango(dias_atras=10, dias_adelante=10):
    hoy = timezone.now().astimezone(LA_PAZ).date()
    return {
        "from": (hoy - dt.timedelta(days=dias_atras)).isoformat(),
        "to": (hoy + dt.timedelta(days=dias_adelante)).isoformat(),
    }


@pytest.fixture
def admin_a(paciente_a, org_a):
    """`user_a` (que ya es paciente de A) con el permiso del panel."""
    dar_rol(paciente_a, org_a, "admin-kpi", "Administración", ["reporting.kpi.read"])
    return paciente_a


def ficha(org, paciente, practitioner, branch, schedule, dias, **extra):
    return crear_ficha(
        org, paciente, practitioner, branch, schedule,
        starts_at=hace(dias), **extra,
    )


def pagar(org, ficha_, usuario, monto, *, estado="succeeded", moneda="BOB"):
    with tenant_context(org.id):
        return Payment.objects.create(
            organization=org, appointment=ficha_, created_by=usuario,
            amount=Decimal(monto), currency=moneda, provider="simulated",
            status=estado,
        )


def pedir(client, **params):
    return client.get(reverse("reporting:kpis"), params)


# ---------------------------------------------------------------------------
#  Permiso y validación
# ---------------------------------------------------------------------------

def test_sin_permiso_es_403(api_client, paciente_a):
    autenticar(api_client, paciente_a)
    assert pedir(api_client).status_code == 403


def test_sin_sesion_es_401(db, api_client):
    assert pedir(api_client).status_code == 401


def test_rango_invertido_es_400(api_client, admin_a):
    autenticar(api_client, admin_a)
    respuesta = pedir(api_client, **{"from": "2026-10-10", "to": "2026-10-01"})
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "invalid_range"


def test_fecha_invalida_es_400(api_client, admin_a):
    autenticar(api_client, admin_a)
    respuesta = pedir(api_client, **{"from": "ayer"})
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "invalid_date"


def test_rango_demasiado_largo_es_400(api_client, admin_a):
    autenticar(api_client, admin_a)
    respuesta = pedir(api_client, **{"from": "2024-01-01", "to": "2026-01-01"})
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "range_too_long"


def test_sucursal_invalida_es_400(api_client, admin_a):
    autenticar(api_client, admin_a)
    assert pedir(api_client, branch="no-es-uuid").status_code == 400


def test_sucursal_de_otra_organizacion_es_400(api_client, admin_a, branch_b):
    autenticar(api_client, admin_a)
    respuesta = pedir(api_client, branch=str(branch_b.id))
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "invalid_branch"


def test_sin_rango_usa_los_ultimos_30_dias(api_client, admin_a):
    autenticar(api_client, admin_a)
    datos = pedir(api_client).data
    desde = dt.date.fromisoformat(datos["range"]["from"])
    hasta = dt.date.fromisoformat(datos["range"]["to"])
    assert (hasta - desde).days == 29


# ---------------------------------------------------------------------------
#  Inasistencia
# ---------------------------------------------------------------------------

def test_inasistencia_no_cuenta_canceladas_ni_reprogramadas(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
):
    centro = branches_a["centro"]
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 9, status="attended")
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 8, status="no_show")
    # Confirmada que ya pasó y nunca hizo check-in: ausente.
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 7, status="confirmed")
    # Lo que no cuenta para la tasa:
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 6, status="cancelled")
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 5, status="rescheduled")
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 4, status="expired")
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 3, status="pending_payment")
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, -2, status="confirmed")

    autenticar(api_client, admin_a)
    datos = pedir(api_client, **rango()).data["no_show"]

    assert datos["expected"] == 3
    assert datos["missed"] == 2
    assert datos["rate"] == pytest.approx(2 / 3, abs=1e-4)


def test_inasistencia_sin_fichas_es_null_no_cero(api_client, admin_a):
    autenticar(api_client, admin_a)
    datos = pedir(api_client, **rango()).data["no_show"]
    assert datos == {"expected": 0, "missed": 0, "rate": None}


# ---------------------------------------------------------------------------
#  Demanda y filtros
# ---------------------------------------------------------------------------

def test_demanda_por_sucursal_y_filtro_de_sucursal(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
):
    ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, 9, status="attended")
    ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, 8, status="attended")
    ficha(org_a, admin_a, practitioner_a, branches_a["norte"], agenda_a, 7, status="attended")
    ficha(org_a, admin_a, practitioner_a, branches_a["norte"], agenda_a, 6, status="cancelled")

    autenticar(api_client, admin_a)
    todo = pedir(api_client, **rango()).data["demand"]
    assert todo["total"] == 3
    assert {s["name"]: s["total"] for s in todo["by_branch"]} == {
        "Sede Centro": 2, "Sede Norte": 1,
    }

    solo_norte = pedir(
        api_client, **rango(), branch=str(branches_a["norte"].id),
    ).data["demand"]
    assert solo_norte["total"] == 1
    assert [s["name"] for s in solo_norte["by_branch"]] == ["Sede Norte"]


def test_el_rango_deja_afuera_lo_que_no_cae_en_el_(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
):
    ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, 40, status="attended")
    ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, 5, status="attended")

    autenticar(api_client, admin_a)
    assert pedir(api_client, **rango(10, 0)).data["demand"]["total"] == 1


def test_profesional_con_dos_especialidades_cuenta_en_cada_una(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a, specialty_a,
):
    with tenant_context(org_a.id):
        pediatria = Specialty.objects.create(
            organization=org_a, name="Pediatría", description="Niños.",
        )
        PractitionerSpecialty.objects.create(
            organization=org_a, practitioner=practitioner_a, specialty=pediatria,
        )
    ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, 5, status="attended")

    autenticar(api_client, admin_a)
    demanda = pedir(api_client, **rango()).data["demand"]

    assert demanda["total"] == 1  # el total no se duplica
    assert {e["name"]: e["total"] for e in demanda["by_specialty"]} == {
        "Cardiología": 1, "Pediatría": 1,
    }


def test_profesional_sin_especialidad_cae_en_sin_especialidad(
    api_client, admin_a, org_a, branches_a, agenda_a,
):
    with tenant_context(org_a.id):
        sin = Practitioner.objects.create(
            organization=org_a, first_name="Sin", last_name="Título",
            license_number="MP-2000",
        )
        PractitionerBranch.objects.create(
            organization=org_a, practitioner=sin, branch=branches_a["centro"],
        )
        agenda = Schedule.objects.create(
            organization=org_a, practitioner=sin, branch=branches_a["centro"],
            weekday=agenda_a.weekday, start_time="09:00", end_time="11:00",
            slot_minutes=60, valid_from=agenda_a.valid_from,
        )
    ficha(org_a, admin_a, sin, branches_a["centro"], agenda, 5, status="attended")

    autenticar(api_client, admin_a)
    demanda = pedir(api_client, **rango()).data["demand"]
    assert [(e["name"], e["total"]) for e in demanda["by_specialty"]] == [
        ("Sin especialidad", 1),
    ]


# ---------------------------------------------------------------------------
#  Ocupación
# ---------------------------------------------------------------------------

def test_ocupacion_resta_bloqueos_y_cuenta_las_fichas(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
):
    hoy = dt.date.today()
    # Siete días seguidos contienen el día de la semana de la agenda una vez:
    # dos espacios (09:00 y 10:00).
    desde, hasta = hoy - dt.timedelta(days=6), hoy
    parametros = {"from": desde.isoformat(), "to": hasta.isoformat()}

    autenticar(api_client, admin_a)
    assert pedir(api_client, **parametros).data["occupancy"] == {
        "offered": 2, "booked": 0, "rate": 0.0,
    }

    # Un bloqueo de 09:00 a 10:00 quita un espacio.
    with tenant_context(org_a.id):
        ScheduleBlock.objects.create(
            organization=org_a, practitioner=practitioner_a,
            starts_at=dt.datetime.combine(hoy, dt.time(9), tzinfo=LA_PAZ),
            ends_at=dt.datetime.combine(hoy, dt.time(10), tzinfo=LA_PAZ),
            reason="holiday",
        )
    # Y una ficha en el espacio que queda.
    crear_ficha(
        org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=dt.datetime.combine(hoy, dt.time(10), tzinfo=LA_PAZ),
        status="confirmed",
    )

    assert pedir(api_client, **parametros).data["occupancy"] == {
        "offered": 1, "booked": 1, "rate": 1.0,
    }


def test_ocupacion_sin_agendas_es_null(api_client, admin_a):
    autenticar(api_client, admin_a)
    datos = pedir(api_client, **rango()).data["occupancy"]
    assert datos == {"offered": 0, "booked": 0, "rate": None}


# ---------------------------------------------------------------------------
#  Ingresos
# ---------------------------------------------------------------------------

def test_ingresos_suman_solo_pagos_cobrados_por_moneda(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
):
    centro, norte = branches_a["centro"], branches_a["norte"]
    f1 = ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 9, status="attended")
    f2 = ficha(org_a, admin_a, practitioner_a, norte, agenda_a, 8, status="attended")
    f3 = ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 7, status="cancelled")
    f4 = ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 6, status="attended")
    f5 = ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 5, status="attended")
    pagar(org_a, f1, admin_a, "100.00")
    pagar(org_a, f2, admin_a, "50.50")
    pagar(org_a, f3, admin_a, "80.00", estado="refunded")  # devuelto: no suma
    pagar(org_a, f4, admin_a, "40.00", estado="pending")   # sin cobrar: no suma
    pagar(org_a, f5, admin_a, "10.00", moneda="USD")

    autenticar(api_client, admin_a)
    ingresos = pedir(api_client, **rango()).data["revenue"]

    assert {f["currency"]: f["total"] for f in ingresos["by_currency"]} == {
        "BOB": "150.50", "USD": "10.00",
    }
    assert {
        (f["name"], f["currency"]): f["total"] for f in ingresos["by_branch"]
    } == {
        ("Sede Centro", "BOB"): "100.00",
        ("Sede Centro", "USD"): "10.00",
        ("Sede Norte", "BOB"): "50.50",
    }

    solo_norte = pedir(api_client, **rango(), branch=str(norte.id)).data["revenue"]
    assert [(f["currency"], f["total"]) for f in solo_norte["by_currency"]] == [
        ("BOB", "50.50"),
    ]


# ---------------------------------------------------------------------------
#  Aislamiento entre organizaciones (RNF-08)
# ---------------------------------------------------------------------------

@pytest.mark.isolation
def test_cada_administrador_ve_solo_su_organizacion(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
    org_b, user_b, branch_b,
):
    # Datos de A: una ficha atendida con su pago.
    f_a = ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, 5, status="attended")
    pagar(org_a, f_a, admin_a, "100.00")

    # Datos de B: tres fichas y dos pagos.
    perfil_paciente(user_b, org_b)
    dar_rol(user_b, org_b, "admin-kpi", "Administración", ["reporting.kpi.read"])
    with tenant_context(org_b.id):
        spec_b = Specialty.objects.create(organization=org_b, name="Otra", description="x")
        prof_b = Practitioner.objects.create(
            organization=org_b, first_name="Bruno", last_name="Paz",
            license_number="MP-3000",
        )
        PractitionerBranch.objects.create(
            organization=org_b, practitioner=prof_b, branch=branch_b,
        )
        PractitionerSpecialty.objects.create(
            organization=org_b, practitioner=prof_b, specialty=spec_b,
        )
        agenda_b = Schedule.objects.create(
            organization=org_b, practitioner=prof_b, branch=branch_b,
            weekday=agenda_a.weekday, start_time="09:00", end_time="11:00",
            slot_minutes=60, valid_from=agenda_a.valid_from,
        )
    fichas_b = [
        ficha(org_b, user_b, prof_b, branch_b, agenda_b, d, status="attended")
        for d in (9, 8, 7)
    ]
    pagar(org_b, fichas_b[0], user_b, "300.00")
    pagar(org_b, fichas_b[1], user_b, "200.00")

    autenticar(api_client, admin_a)
    de_a = pedir(api_client, **rango()).data
    assert de_a["demand"]["total"] == 1
    assert [s["name"] for s in de_a["demand"]["by_branch"]] == ["Sede Centro"]
    assert [e["name"] for e in de_a["demand"]["by_specialty"]] == ["Cardiología"]
    assert de_a["revenue"]["by_currency"] == [
        {"currency": "BOB", "total": "100.00", "payments": 1},
    ]

    autenticar(api_client, user_b)
    de_b = pedir(api_client, **rango()).data
    assert de_b["demand"]["total"] == 3
    assert [s["name"] for s in de_b["demand"]["by_branch"]] == ["Sucursal de B"]
    assert de_b["revenue"]["by_currency"] == [
        {"currency": "BOB", "total": "500.00", "payments": 2},
    ]


# ---------------------------------------------------------------------------
#  Se agrega en la base, no en Python
# ---------------------------------------------------------------------------

def test_las_consultas_no_crecen_con_las_fichas(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
    django_assert_max_num_queries,
):
    for dias in range(1, 9):
        f = ficha(org_a, admin_a, practitioner_a, branches_a["centro"], agenda_a, dias, status="attended")
        pagar(org_a, f, admin_a, "10.00")

    autenticar(api_client, admin_a)
    # Auth y contexto de inquilino aparte, el cálculo son unas pocas
    # agregaciones: el tope no depende de cuántas fichas haya.
    with django_assert_max_num_queries(25):
        assert pedir(api_client, **rango()).status_code == 200


# ---------------------------------------------------------------------------
#  El panel de inicio usa la misma definición de inasistencia
# ---------------------------------------------------------------------------

def test_el_panel_de_inicio_da_la_misma_tasa_que_los_kpis(
    api_client, admin_a, org_a, practitioner_a, branches_a, agenda_a,
):
    dar_rol(admin_a, org_a, "admin-panel", "Administración",
            ["users.user.read", "appointments.appointment.read"])
    centro = branches_a["centro"]
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 9, status="attended")
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 8, status="no_show")
    # Confirmada vencida sin check-in: también es ausente.
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 7, status="confirmed")
    # Cancelada: se muestra en la barra, pero no entra en la tasa.
    ficha(org_a, admin_a, practitioner_a, centro, agenda_a, 6, status="cancelled")

    autenticar(api_client, admin_a)
    asistencia = api_client.get(reverse("tenancy:my-panel")).json()["asistencia"]
    kpis = pedir(api_client, **rango()).data["no_show"]

    assert asistencia["atendidas"] == 1
    assert asistencia["ausentes"] == 2
    assert asistencia["canceladas"] == 1
    assert asistencia["tasa_inasistencia"] == kpis["rate"] == pytest.approx(2 / 3, abs=1e-4)
