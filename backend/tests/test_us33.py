"""US-33 — Reserva conversacional.

Lo que estas pruebas sostienen son las tres reglas del reparto del Sprint 3:

1. **Los turnos que se ofrecen salen de la disponibilidad**, no del modelo:
   cada oferta es un espacio que ``consolidated_availability`` devuelve.
2. **Nada se reserva sin confirmación**, y la reserva es ``book_appointment``:
   la misma concurrencia (409), la misma validación del turno (400) y la
   misma ficha *pendiente de pago* que la pantalla de US-17.
3. **La barrera de US-34 va primero**: una preferencia de horario que
   describe una urgencia deriva y no ofrece turnos.

Y una que no está en el reparto pero es la que más importa: desde el
asistente se reserva para uno mismo o para un dependiente a cargo, nunca a
nombre de otro paciente de la organización.
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, User
from appointments.models import Appointment
from assistant import preferences
from assistant.indexing import index_administrative, index_specialties
from audit.actions import Action
from catalog.models import Service, Specialty
from patients.models import Patient
from scheduling.availability import consolidated_availability
from scheduling.models import Schedule
from tenancy.context import tenant_context

from .conftest import PERMISOS_PACIENTE, dar_rol
from .fichas_comunes import autenticar, perfil_paciente
from .test_us31 import CARDIOLOGIA, proveedor_local  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db

LA_PAZ = ZoneInfo("America/La_Paz")
PERMISOS_PACIENTE_CON_ASISTENTE = PERMISOS_PACIENTE + ["assistant.suggest.use"]


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def paciente(db, org_a, user_a):
    """Paciente con el asistente, la reserva y su ficha de paciente."""
    dar_rol(user_a, org_a, "patient", "Paciente", PERMISOS_PACIENTE_CON_ASISTENTE)
    perfil_paciente(user_a, org_a)
    return user_a


@pytest.fixture
def agendas(db, org_a, practitioner_a, branches_a):
    """La profesional de Cardiología atiende todos los días, una hora a la
    mañana (09:00) y una a la tarde (15:00), con espacios de 30 minutos.

    Todos los días para que las pruebas no dependan del día en que corren.
    """
    with tenant_context(org_a.id):
        return [
            Schedule.objects.create(
                organization=org_a, practitioner=practitioner_a,
                branch=branches_a["centro"], weekday=dia,
                start_time=desde, end_time=hasta, slot_minutes=30,
                valid_from=dt.date.today() - dt.timedelta(days=7),
            )
            for dia in range(7)
            for desde, hasta in (("09:00", "10:00"), ("15:00", "16:00"))
        ]


def pedir_turnos(api_client, user, specialty, preference=""):
    return autenticar(api_client, user).post(
        reverse("assistant:slots"),
        {"specialty": str(specialty.id), "preference": preference},
        format="json",
    )


def reservar(api_client, user, oferta, **extra):
    datos = {
        "practitioner": oferta["practitioner"]["id"],
        "branch": oferta["branch"]["id"],
        "schedule": oferta["schedule"]["id"],
        "starts_at": oferta["start"],
        **extra,
    }
    return autenticar(api_client, user).post(
        reverse("assistant:book"), datos, format="json",
    )


# --------------------------------------------------------------------------
#  La preferencia de horario, con reglas
# --------------------------------------------------------------------------

LUNES = dt.date(2026, 10, 12)


@pytest.mark.parametrize("texto, dias, franja", [
    ("", set(), ""),
    ("lo antes posible", set(), ""),
    ("hoy", {LUNES}, ""),
    ("mañana", {LUNES + dt.timedelta(days=1)}, ""),
    ("pasado mañana", {LUNES + dt.timedelta(days=2)}, ""),
    ("en la mañana", set(), "manana"),
    ("mañana por la tarde", {LUNES + dt.timedelta(days=1)}, "tarde"),
    ("mañana temprano", {LUNES + dt.timedelta(days=1)}, "manana"),
    ("el jueves por la tarde", {dt.date(2026, 10, 15)}, "tarde"),
    ("el lunes", {LUNES}, ""),
    ("Miércoles o viernes", {dt.date(2026, 10, 14), dt.date(2026, 10, 16)}, ""),
    ("el fin de semana", {dt.date(2026, 10, 17), dt.date(2026, 10, 18)}, ""),
    ("el martes de la semana que viene", {dt.date(2026, 10, 20)}, ""),
    ("de noche", set(), "noche"),
])
def test_la_preferencia_se_entiende_con_reglas(texto, dias, franja):
    preferencia = preferences.parse(texto, today=LUNES)
    assert set(preferencia.days) == dias
    assert preferencia.part_of_day == franja


def test_la_semana_que_viene_son_sus_siete_dias():
    preferencia = preferences.parse("la próxima semana", today=LUNES)
    assert preferencia.date_from == dt.date(2026, 10, 19)
    assert preferencia.date_to == dt.date(2026, 10, 25)


def test_sin_dia_se_busca_en_las_proximas_dos_semanas():
    preferencia = preferences.parse("por la tarde", today=LUNES)
    assert preferencia.date_from == LUNES
    assert preferencia.date_to == LUNES + dt.timedelta(days=14)


@pytest.mark.parametrize("texto, quiere", [
    ("quiero reservar una ficha", True),
    ("necesito sacar turno con cardiología", True),
    ("¿hay horarios el jueves?", True),
    ("me duelen las rodillas al subir escaleras", False),
    ("tengo manchas en la piel", False),
])
def test_la_intencion_de_reservar(texto, quiere):
    assert preferences.has_booking_intent(texto) is quiere


# --------------------------------------------------------------------------
#  Los turnos que se ofrecen
# --------------------------------------------------------------------------

def _espacios_reales(practitioner, desde, hasta):
    data = consolidated_availability(
        practitioner_id=practitioner.id, date_from=desde, date_to=hasta,
    )
    return {
        (slot["schedule"]["id"], slot["start"])
        for day in data["days"] for slot in day["slots"] if slot["reservable"]
    }


def test_cada_turno_ofrecido_es_un_espacio_real_de_la_disponibilidad(
    api_client, paciente, org_a, specialty_a, practitioner_a, agendas,
):
    respuesta = pedir_turnos(api_client, paciente, specialty_a)
    assert respuesta.status_code == 200, respuesta.json()
    cuerpo = respuesta.json()

    assert cuerpo["emergency"] is False
    assert cuerpo["kind"] == "reserva"
    assert 0 < len(cuerpo["offers"]) <= 6
    hoy = timezone.localdate()
    with tenant_context(org_a.id):
        reales = _espacios_reales(practitioner_a, hoy, hoy + dt.timedelta(days=14))
    for oferta in cuerpo["offers"]:
        assert (oferta["schedule"]["id"], oferta["start"]) in reales
        assert oferta["practitioner"]["id"] == str(practitioner_a.id)


def test_los_turnos_vienen_del_mas_cercano_al_mas_lejano(
    api_client, paciente, specialty_a, agendas,
):
    ofertas = pedir_turnos(api_client, paciente, specialty_a).json()["offers"]
    inicios = [dt.datetime.fromisoformat(o["start"]) for o in ofertas]
    assert inicios == sorted(inicios)
    assert all(inicio > timezone.now() for inicio in inicios)


def test_por_la_tarde_ofrece_solo_turnos_de_la_tarde(
    api_client, paciente, specialty_a, agendas,
):
    cuerpo = pedir_turnos(api_client, paciente, specialty_a, "por la tarde").json()

    assert cuerpo["matched_preference"] is True
    assert cuerpo["preference"]["part_of_day"] == "tarde"
    assert cuerpo["offers"]
    for oferta in cuerpo["offers"]:
        hora = dt.datetime.fromisoformat(oferta["start"]).astimezone(LA_PAZ).time()
        assert dt.time(15, 0) <= hora < dt.time(16, 0)


def test_un_dia_pedido_ofrece_solo_ese_dia(
    api_client, paciente, specialty_a, agendas,
):
    manana = timezone.localdate() + dt.timedelta(days=1)
    cuerpo = pedir_turnos(api_client, paciente, specialty_a, "mañana").json()

    assert cuerpo["offers"]
    for oferta in cuerpo["offers"]:
        assert dt.datetime.fromisoformat(oferta["start"]).date() == manana


def test_si_lo_pedido_no_tiene_turnos_lo_dice_y_ofrece_los_mas_proximos(
    api_client, paciente, specialty_a, agendas,
):
    """Nadie atiende de noche: se avisa y se ofrece lo más próximo."""
    cuerpo = pedir_turnos(api_client, paciente, specialty_a, "de noche").json()

    assert cuerpo["matched_preference"] is False
    assert cuerpo["offers"]
    assert "No hay horarios" in cuerpo["answer"]


def test_sin_agendas_no_ofrece_nada_y_lo_dice(
    api_client, paciente, specialty_a, practitioner_a,
):
    cuerpo = pedir_turnos(api_client, paciente, specialty_a).json()
    assert cuerpo["offers"] == []
    assert "No encontré horarios" in cuerpo["answer"]


def test_un_turno_reservado_ya_no_se_ofrece(
    api_client, paciente, specialty_a, agendas,
):
    primera = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]
    assert reservar(api_client, paciente, primera).status_code == 201

    ofertas = pedir_turnos(api_client, paciente, specialty_a).json()["offers"]
    assert (primera["schedule"]["id"], primera["start"]) not in {
        (o["schedule"]["id"], o["start"]) for o in ofertas
    }


def test_un_profesional_inactivo_no_se_ofrece(
    api_client, paciente, org_a, specialty_a, practitioner_a, agendas,
):
    with tenant_context(org_a.id):
        practitioner_a.is_active = False
        practitioner_a.save(update_fields=["is_active"])

    assert pedir_turnos(api_client, paciente, specialty_a).json()["offers"] == []


def test_la_especialidad_de_otra_organizacion_da_404(
    api_client, paciente, org_b, agendas,
):
    with tenant_context(org_b.id):
        ajena = Specialty.objects.create(organization=org_b, name="Odontología")

    respuesta = pedir_turnos(api_client, paciente, ajena)
    assert respuesta.status_code == 404


# --------------------------------------------------------------------------
#  La barrera de US-34 sigue primero
# --------------------------------------------------------------------------

def test_una_urgencia_en_la_preferencia_deriva_y_no_ofrece_turnos(
    api_client, paciente, org_a, specialty_a, agendas,
):
    cuerpo = pedir_turnos(
        api_client, paciente, specialty_a, "mejor hoy, tengo dolor de pecho",
    ).json()

    assert cuerpo["emergency"] is True
    assert "offers" not in cuerpo
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.ASSISTANT_EMERGENCY)
    assert asiento.detail == {"layer": "regla"}


# --------------------------------------------------------------------------
#  La reserva, sólo con el turno confirmado
# --------------------------------------------------------------------------

def test_confirmar_un_turno_ofrecido_reserva_pendiente_de_pago(
    api_client, paciente, org_a, specialty_a, agendas,
):
    oferta = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]

    respuesta = reservar(api_client, paciente, oferta)

    assert respuesta.status_code == 201, respuesta.json()
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "pending_payment"
    assert cuerpo["patient"] == str(paciente.patient_profile.id)
    with tenant_context(org_a.id):
        ficha = Appointment.objects.get()
        assert ficha.booked_by_id == paciente.id
        assert ficha.expires_at is not None


def test_la_reserva_deja_asiento_sin_texto_del_paciente(
    api_client, paciente, org_a, specialty_a, agendas,
):
    oferta = pedir_turnos(
        api_client, paciente, specialty_a, "por la tarde",
    ).json()["offers"][0]
    ficha = reservar(api_client, paciente, oferta).json()

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.ASSISTANT_BOOKING)
    assert str(asiento.entity_id) == ficha["id"]
    assert "tarde" not in str(asiento.detail or "")


def test_reservar_no_cuenta_como_consulta_al_asistente(
    api_client, paciente, org_a, specialty_a, agendas,
):
    from tenancy.plans import ai_queries_this_month

    oferta = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]
    reservar(api_client, paciente, oferta)

    assert ai_queries_this_month(org_a) == 0


def test_dos_confirmaciones_del_mismo_turno_una_gana_y_la_otra_recibe_409(
    api_client, paciente, org_a, specialty_a, agendas,
):
    oferta = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]

    codigos = sorted([
        reservar(api_client, paciente, oferta).status_code,
        reservar(api_client, paciente, oferta).status_code,
    ])

    assert codigos == [201, 409]
    with tenant_context(org_a.id):
        assert Appointment.objects.count() == 1


def test_un_horario_que_la_agenda_no_tiene_da_400(
    api_client, paciente, specialty_a, agendas,
):
    oferta = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]
    inventado = dict(oferta)
    inventado["start"] = (
        dt.datetime.fromisoformat(oferta["start"]) + dt.timedelta(minutes=7)
    ).isoformat()

    respuesta = reservar(api_client, paciente, inventado)

    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "turno_invalido"


def test_no_se_reserva_a_nombre_de_otro_paciente(
    api_client, paciente, org_a, specialty_a, agendas,
):
    with tenant_context(org_a.id):
        ajeno = Patient.objects.create(
            organization=org_a, first_name="Otra", last_name="Persona",
            document_number="AJENO-33",
        )
    oferta = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]

    respuesta = reservar(api_client, paciente, oferta, patient=str(ajeno.id))

    assert respuesta.status_code == 404
    with tenant_context(org_a.id):
        assert not Appointment.objects.exists()


def test_se_reserva_para_un_dependiente_a_cargo(
    api_client, paciente, org_a, specialty_a, agendas,
):
    with tenant_context(org_a.id):
        hijo = Patient.objects.create(
            organization=org_a, first_name="Hijo", last_name="Pérez",
            document_number=None, guardian=paciente.patient_profile,
            relationship="child",
        )
    oferta = pedir_turnos(api_client, paciente, specialty_a).json()["offers"][0]

    respuesta = reservar(api_client, paciente, oferta, patient=str(hijo.id))

    assert respuesta.status_code == 201, respuesta.json()
    assert respuesta.json()["patient"] == str(hijo.id)


def test_sin_ficha_de_paciente_no_se_reserva_desde_el_asistente(
    api_client, org_a, specialty_a, agendas,
):
    """Personal con permiso de reservar pero sin ficha de paciente: la
    reserva a nombre de otro es del mostrador (US-23), no del asistente."""
    with tenant_context(org_a.id):
        recepcion = User.objects.create_user(
            email="recepcion@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Rita", last_name="Mostrador",
            document_number="REC-33",
        )
    dar_rol(recepcion, org_a, "recepcion-33", "Recepción",
            PERMISOS_PACIENTE_CON_ASISTENTE)
    oferta = pedir_turnos(api_client, recepcion, specialty_a).json()["offers"][0]

    respuesta = reservar(api_client, recepcion, oferta)

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "sin_ficha_de_paciente"


def test_sin_permiso_de_reservar_no_se_reserva(
    api_client, org_a, user_a, specialty_a, agendas,
):
    dar_rol(user_a, org_a, "solo-asistente", "Sólo asistente", [
        "assistant.suggest.use", "scheduling.slot.read",
    ])
    perfil_paciente(user_a, org_a)
    oferta = pedir_turnos(api_client, user_a, specialty_a).json()["offers"][0]

    assert reservar(api_client, user_a, oferta).status_code == 403


def test_sin_autenticar_no_se_entra(api_client, specialty_a):
    assert api_client.post(
        reverse("assistant:slots"), {"specialty": str(specialty_a.id)},
        format="json",
    ).status_code == 401
    assert api_client.post(reverse("assistant:book"), {}, format="json").status_code == 401


# --------------------------------------------------------------------------
#  La orientación avisa que se puede reservar
# --------------------------------------------------------------------------

@pytest.fixture
def cardiologia_indexada(org_a, specialty_a, proveedor_local):
    with tenant_context(org_a.id):
        Specialty.objects.filter(pk=specialty_a.pk).update(description=CARDIOLOGIA)
        index_specialties(org_a)
    return specialty_a


def _orientar(api_client, user, texto):
    return autenticar(api_client, user).post(
        reverse("assistant:suggest"), {"question": texto}, format="json",
    ).json()


def test_la_orientacion_dice_que_se_puede_reservar(
    api_client, paciente, cardiologia_indexada, agendas,
):
    cuerpo = _orientar(api_client, paciente, "tengo palpitaciones y presión alta")

    assert cuerpo["specialty"]["name"] == "Cardiología"
    assert cuerpo["booking"] == {
        "available": True, "booking_intent": False,
        "specialty": {"id": str(cardiologia_indexada.id), "name": "Cardiología"},
    }


def test_la_orientacion_detecta_que_la_pregunta_pide_reservar(
    api_client, paciente, cardiologia_indexada, agendas,
):
    cuerpo = _orientar(
        api_client, paciente,
        "tengo palpitaciones y presión alta, quiero reservar un turno el jueves",
    )

    assert cuerpo["specialty"]["name"] == "Cardiología"
    assert cuerpo["booking"]["booking_intent"] is True


def test_sin_permiso_de_reservar_la_orientacion_no_lo_ofrece(
    api_client, org_a, user_a, cardiologia_indexada,
):
    dar_rol(user_a, org_a, "solo-asistente", "Sólo asistente",
            ["assistant.suggest.use"])
    cuerpo = _orientar(api_client, user_a, "tengo palpitaciones y presión alta")

    assert cuerpo["booking"]["available"] is False
    assert cuerpo["booking"]["specialty"] is None


def test_pedir_turno_de_un_servicio_no_pierde_la_reserva(
    api_client, paciente, org_a, cardiologia_indexada, agendas,
):
    """"Quiero reservar un turno de cardiología" se parece más al servicio
    "Consulta de Cardiología" que a la especialidad, y la contesta US-32
    como administrativa. La reserva sale igual, con la especialidad del
    servicio."""
    with tenant_context(org_a.id):
        Service.objects.create(
            organization=org_a, name="Consulta de Cardiología",
            kind=Service.Kind.CONSULTATION, price=150,
            specialty=cardiologia_indexada,
        )
        index_administrative(org_a)

    cuerpo = _orientar(api_client, paciente, "quiero reservar un turno de cardiología")

    assert cuerpo["kind"] == "administrativa"
    assert cuerpo["booking"] == {
        "available": True, "booking_intent": True,
        "specialty": {"id": str(cardiologia_indexada.id), "name": "Cardiología"},
    }


def test_una_consulta_administrativa_sin_reserva_no_la_ofrece(
    api_client, paciente, org_a, cardiologia_indexada,
):
    with tenant_context(org_a.id):
        Service.objects.create(
            organization=org_a, name="Consulta de Cardiología",
            kind=Service.Kind.CONSULTATION, price=150,
            specialty=cardiologia_indexada,
        )
        index_administrative(org_a)

    cuerpo = _orientar(api_client, paciente, "cuánto cuesta la consulta de cardiología")

    assert cuerpo["kind"] == "administrativa"
    assert cuerpo["booking"]["available"] is False
