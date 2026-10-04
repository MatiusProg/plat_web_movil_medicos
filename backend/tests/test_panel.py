"""El panel de inicio (``/api/platform/my-panel/``): cada rol ve lo suyo.

Lo que más importa es lo que NO aparece: un paciente nunca ve las fichas del
centro ni el plan; un médico ve sólo su agenda, no la de sus colegas.
"""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    LA_PAZ, _ficha, _medico, cliente, ficha_hoy, medico_a, otro_medico_a, paciente,
)

pytestmark = pytest.mark.django_db


def panel(user):
    return cliente(user).get(reverse("tenancy:my-panel")).json()


def test_administracion_ve_el_uso_del_plan(org_a, user_a):
    dar_rol(user_a, org_a, "admin-panel", "Administración",
            ["users.user.read", "appointments.appointment.read"])
    datos = panel(user_a)
    assert datos["plan"]["code"] == "premium"
    etiquetas = [u["etiqueta"] for u in datos["plan"]["uso"]]
    assert "Sucursales activas" in etiquetas and "Personal" in etiquetas
    assert "hoy" in datos and "asistencia" in datos


def test_recepcion_ve_el_dia_pero_no_el_plan(org_a, user_a, ficha_hoy):
    dar_rol(user_a, org_a, "recepcion-panel", "Recepción", ["appointments.appointment.read"])
    datos = panel(user_a)
    assert "plan" not in datos
    assert datos["hoy"]["total"] >= 1


def test_el_medico_ve_solo_su_agenda(org_a, medico_a, otro_medico_a, ficha_hoy):
    assert [f["id"] for f in panel(medico_a)["mi_agenda"]["fichas"]] == [str(ficha_hoy.id)]
    assert panel(otro_medico_a)["mi_agenda"]["fichas"] == []


def test_el_medico_ve_sus_atenciones_sin_firmar(org_a, medico_a, ficha_hoy):
    cliente(medico_a).post(reverse("encounters:open"), {"appointment": str(ficha_hoy.id)}, format="json")
    assert panel(medico_a)["mi_agenda"]["sin_firmar"] == 1


def test_el_paciente_ve_sus_fichas_y_nada_del_centro(org_a, user_a, practitioner_a, branches_a):
    dar_rol(user_a, org_a, "patient", "Paciente", ["appointments.appointment.read"])
    with tenant_context(org_a.id):
        propio = Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
    manana = timezone.now() + dt.timedelta(days=1)
    _ficha(org_a, practitioner_a, branches_a["centro"], propio, user_a, manana)
    datos = panel(user_a)
    assert len(datos["mis_fichas"]) == 1
    # En su propia ficha no se le dice su nombre; sólo en la de un dependiente.
    assert "patient" not in datos["mis_fichas"][0]
    assert "hoy" not in datos and "plan" not in datos and "asistencia" not in datos
    # Lo que incluye el plan lo sabe cualquiera: así no se le ofrece lo que no hay.
    assert datos["incluye"]["asistente"] is True


def test_el_superadministrador_tiene_su_propio_panel(platform_admin):
    assert panel(platform_admin) == {"plataforma": True}
