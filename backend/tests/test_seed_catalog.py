"""El comando `seed_catalog`.

No es una historia, es la herramienta que reemplaza al ABM web que US-11 y
US-12 todavía no tienen. Aun así lleva pruebas, y sobre todo **una**: que
después de sembrar, la disponibilidad de US-15 devuelva espacios. Sembrar filas
que no llegan a producir un espacio reservable no sirve para nada, y es
exactamente el modo de fallo que tuvo la migración a la que reemplaza —corrió,
no sembró y salió con éxito—.
"""

import datetime as dt
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from catalog.models import Branch, Practitioner, Specialty
from scheduling.models import Schedule
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

PERMISOS_PACIENTE = [
    "catalog.branch.read",
    "catalog.specialty.read",
    "catalog.professional.read",
    "scheduling.slot.read",
]


def sembrar(slug, **opciones):
    salida = StringIO()
    call_command("seed_catalog", organization=slug, stdout=salida, **opciones)
    return salida.getvalue()


def proximo_lunes():
    hoy = dt.date.today()
    return hoy + dt.timedelta(days=(7 - hoy.weekday()) % 7 or 7)


def test_una_organizacion_inexistente_falla_ruidosamente(org_a):
    """Es el defecto que motivó el comando.

    `catalog/0004_seed_demo` busca el slug fijo `kolping`, y cuando no lo
    encuentra **retorna en silencio**: la migración queda marcada como aplicada,
    el catálogo vacío y nadie se entera hasta que alguien abre la pantalla de
    agendas y no hay a quién elegir.
    """
    with pytest.raises(CommandError) as fallo:
        sembrar("no-existe")

    # Y dice cuáles hay, que es lo que uno necesita en ese momento.
    assert org_a.slug in str(fallo.value)


def test_siembra_el_catalogo_completo(org_a):
    sembrar(org_a.slug)

    with tenant_context(org_a.id):
        assert Branch.objects.count() == 3
        assert Specialty.objects.count() == 5
        assert Practitioner.objects.count() == 4

        # US-12 (c) y (d): las asociaciones muchos a muchos. Sin la de
        # sucursales, la disponibilidad consolidada de US-15 no existe.
        laura = Practitioner.objects.get(license_number="MP-1001")
        assert {e.name for e in laura.specialties.all()} == {
            "Cardiología", "Medicina general",
        }
        assert {s.name for s in laura.branches.all()} == {
            "Sede Centro", "Sede Norte",
        }
        # El nombre normalizado lo calcula `save()`, y es lo que busca US-16.
        assert laura.search_name == "laura gomez"


def test_es_repetible(org_a):
    sembrar(org_a.slug)
    salida = sembrar(org_a.slug)

    with tenant_context(org_a.id):
        assert Branch.objects.count() == 3
        assert Practitioner.objects.count() == 4
    assert "0 creados" in salida


def test_no_toca_a_las_demas_organizaciones(org_a, org_b):
    sembrar(org_a.slug)

    with tenant_context(org_b.id):
        assert Branch.objects.count() == 0
        assert Practitioner.objects.count() == 0


def test_las_agendas_reparten_los_dias_entre_las_sedes(org_a):
    """US-13 (c): un profesional no puede tener dos agendas que se pisen **ni
    siquiera en sucursales distintas**, porque no puede estar en dos sedes a la
    vez. Por eso el reparto es por día y no por sede."""
    sembrar(org_a.slug, with_schedules=True)

    with tenant_context(org_a.id):
        laura = Practitioner.objects.get(license_number="MP-1001")
        agendas = list(
            Schedule.objects.filter(practitioner=laura)
            .values_list("weekday", "branch__name")
        )

    dias = [weekday for weekday, _ in agendas]
    assert sorted(dias) == [0, 1, 2, 3, 4]      # una por día hábil
    assert len(set(dias)) == len(dias)          # ninguno repetido
    # Atiende en dos sedes, así que los días se alternan entre las dos.
    assert {sede for _, sede in agendas} == {"Sede Centro", "Sede Norte"}


def test_despues_de_sembrar_la_disponibilidad_devuelve_espacios(org_a, user_a):
    """La prueba que justifica el comando.

    Sembrar sucursales, especialidades y profesionales no sirve de nada si la
    cadena no llega hasta el final: profesional → agenda → espacio reservable.
    Es lo que consumen US-15 y US-16, y lo que se muestra en la revisión.
    """
    sembrar(org_a.slug, with_schedules=True)
    dar_rol(user_a, org_a, "patient", "Paciente", PERMISOS_PACIENTE)

    with tenant_context(org_a.id):
        laura = Practitioner.objects.get(license_number="MP-1001")

    cliente = APIClient()
    cliente.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user_a)['access']}",
    )
    lunes = proximo_lunes()
    respuesta = cliente.get(
        reverse("scheduling:availability"),
        {
            "practitioner": str(laura.id),
            "from": lunes.isoformat(),
            "to": (lunes + dt.timedelta(days=4)).isoformat(),
        },
    )

    assert respuesta.status_code == 200
    dias = respuesta.json()["days"]
    espacios = [s for d in dias for s in d["slots"]]
    assert espacios, "sembramos el catálogo y no hay un solo espacio reservable"

    # Media jornada de 08:00 a 12:00 en consultas de media hora: ocho por día.
    por_dia = {d["date"]: len(d["slots"]) for d in dias if d["slots"]}
    assert set(por_dia.values()) == {8}

    # Y aparece etiquetado con su sede, que es el caso que da nombre al
    # proyecto: el paciente elige por conveniencia, no por sucursal.
    assert {s["branch"]["name"] for s in espacios} <= {
        "Sede Centro", "Sede Norte",
    }
