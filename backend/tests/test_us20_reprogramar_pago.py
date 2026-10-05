"""US-20 × US-18 — Reprogramar una ficha ya pagada: ¿qué pasa con el pago?

`reschedule_appointment` crea una ficha **nueva** y deja la vieja en
`rescheduled`. La nueva nace `confirmed` ("la misma compra movida de
horario"), pero el `Payment` se enlaza por `appointment_id` y sigue
apuntando a la ficha **vieja**.

Estas pruebas dicen lo que debería pasar. Si fallan, el pago quedó atrás:

- la ficha nueva muestra `payment_status` vacío, y
- cancelarla a tiempo no devuelve nada, porque `refund_for_cancellation`
  busca un `Payment` `succeeded` de **esa** ficha y no lo encuentra.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from appointments.models import Appointment
from payments.models import Payment
from tenancy.context import platform_admin_context, tenant_context

from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    paciente_a,
)

pytestmark = pytest.mark.django_db

LAPAZ = ZoneInfo("America/La_Paz")


def _hora(dias, hora):
    """Un turno de la agenda de `agenda_a` (mismo día de la semana que hoy)."""
    dia = dt.date.today() + dt.timedelta(days=dias)
    return dt.datetime.combine(dia, dt.time(hora, 0), tzinfo=LAPAZ)


@pytest.fixture
def ficha_pagada(
    api_client, client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    """Una ficha del paciente, pagada por el camino simulado (queda `confirmed`)."""
    ficha = crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=_hora(7, 9),
    )
    url = autenticar(api_client, paciente_a).post(
        reverse("payments:checkout", args=[ficha.id]),
    ).json()["checkout_url"]
    client.post(url, {"accion": "pagar"})
    with tenant_context(org_a.id):
        ficha.refresh_from_db()
        assert ficha.status == Appointment.Status.CONFIRMED
        assert Payment.objects.get(appointment=ficha).status == "succeeded"
    return ficha


@pytest.fixture
def ficha_reprogramada(api_client, paciente_a, branches_a, agenda_a, ficha_pagada):
    """La ficha nueva que devuelve el backend al reprogramar la pagada."""
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-reschedule", args=[ficha_pagada.id]),
        {
            "branch": str(branches_a["centro"].id),
            "schedule": str(agenda_a.id),
            "starts_at": _hora(7, 10).isoformat(),
        },
        format="json",
    )
    assert respuesta.status_code == 200, respuesta.json()
    return respuesta.json()


def test_la_ficha_reprogramada_conserva_el_estado_de_pago(
    api_client, paciente_a, ficha_reprogramada,
):
    detalle = autenticar(api_client, paciente_a).get(
        reverse("appointments:appointment-detail", args=[ficha_reprogramada["id"]]),
    ).json()

    assert detalle["status"] == "confirmed"
    assert detalle["payment_status"] == "succeeded"


def test_cancelar_a_tiempo_la_ficha_reprogramada_devuelve_el_pago(
    api_client, paciente_a, org_a, ficha_pagada, ficha_reprogramada,
):
    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha_reprogramada["id"]]),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["refund_eligible"] is True
    # El paciente pagó una vez: ese pago tiene que haberse devuelto.
    with tenant_context(org_a.id):
        assert Payment.objects.filter(
            organization=org_a, status="refunded",
        ).count() == 1


# ---------- Casos alrededor del arreglo -------------------------------------

def _reprogramar(api_client, user, ficha_id, branches_a, agenda_a, starts_at):
    return autenticar(api_client, user).post(
        reverse("appointments:appointment-reschedule", args=[ficha_id]),
        {
            "branch": str(branches_a["centro"].id),
            "schedule": str(agenda_a.id),
            "starts_at": starts_at.isoformat(),
        },
        format="json",
    )


def _pago_de(org, ficha_id):
    with tenant_context(org.id):
        return Payment.objects.get(status="succeeded", appointment_id=ficha_id)


def test_el_pago_se_muda_a_la_ficha_nueva(
    org_a, ficha_pagada, ficha_reprogramada,
):
    pago = _pago_de(org_a, ficha_reprogramada["id"])

    assert str(pago.appointment_id) == ficha_reprogramada["id"]
    with tenant_context(org_a.id):
        # La ficha vieja ya no tiene un pago `succeeded` que le pertenezca.
        assert not Payment.objects.filter(
            appointment_id=ficha_pagada.id, status="succeeded",
        ).exists()


def test_reprogramar_dos_veces_y_cancelar_devuelve_el_pago(
    api_client, paciente_a, org_a, branches_a, agenda_a, ficha_reprogramada,
):
    segunda = _reprogramar(
        api_client, paciente_a, ficha_reprogramada["id"], branches_a, agenda_a,
        _hora(14, 9),
    )
    assert segunda.status_code == 200, segunda.json()
    id_final = segunda.json()["id"]
    assert str(_pago_de(org_a, id_final).appointment_id) == id_final

    cancelada = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[id_final]),
    )
    assert cancelada.status_code == 200
    with tenant_context(org_a.id):
        assert Payment.objects.filter(status="refunded").count() == 1
        assert not Payment.objects.filter(status="succeeded").exists()


def test_reprogramar_una_ficha_sin_pagar_no_mueve_ningun_pago(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    ficha = crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=_hora(7, 9),
    )
    respuesta = _reprogramar(
        api_client, paciente_a, ficha.id, branches_a, agenda_a, _hora(7, 10),
    )

    assert respuesta.status_code == 200, respuesta.json()
    assert respuesta.json()["status"] == "pending_payment"
    assert respuesta.json()["payment_status"] is None
    with tenant_context(org_a.id):
        assert Payment.objects.count() == 0


def test_cancelar_fuera_de_plazo_la_ficha_reprogramada_no_devuelve(
    api_client, paciente_a, org_a, ficha_reprogramada,
):
    # El plazo pasa a 30 días: la ficha, a 7, queda fuera de la política.
    with platform_admin_context():
        type(org_a).objects.filter(pk=org_a.pk).update(
            cancellation_notice_hours=24 * 30,
        )

    respuesta = autenticar(api_client, paciente_a).post(
        reverse("appointments:appointment-cancel", args=[ficha_reprogramada["id"]]),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["refund_eligible"] is False
    pago = _pago_de(org_a, ficha_reprogramada["id"])
    assert pago.status == "succeeded"


def test_si_reprogramar_falla_el_pago_sigue_en_la_ficha_original(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
    ficha_pagada,
):
    # Otro turno ocupa las 10:00: reprogramar ahí devuelve 409.
    crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=_hora(7, 10),
    )
    respuesta = _reprogramar(
        api_client, paciente_a, ficha_pagada.id, branches_a, agenda_a, _hora(7, 10),
    )

    assert respuesta.status_code == 409
    pago = _pago_de(org_a, ficha_pagada.id)
    assert pago.appointment_id == ficha_pagada.id
    with tenant_context(org_a.id):
        ficha_pagada.refresh_from_db()
    assert ficha_pagada.status == Appointment.Status.CONFIRMED
