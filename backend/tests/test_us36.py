"""US-36 — El recordatorio reforzado.

Lo que se prueba es lo que la historia tiene que cumplir:

- La ficha con riesgo **alto** (US-35) recibe un segundo recordatorio, más cerca
  de la hora, en la misma vuelta del proceso de US-28.
- **Nunca dos veces**: tiene su propia marca y es independiente de la del primer
  recordatorio.
- Se lee la predicción, no se calcula: sin predicción vigente, sin plan o con
  una ficha que ya no corresponde, no hay refuerzo.
- Cada organización refuerza sólo sus fichas, y el texto no le dice al paciente
  cómo lo califica el centro.

FCM nunca se llama de verdad: se reutiliza el falso de las pruebas de US-28.
"""

import datetime as dt

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from appointments import reminders
from appointments.models import Appointment
from noshow.models import ModelVersion, NoShowPrediction
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Subscription

from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    paciente_a,
    recargar,
)
from .test_us28 import (  # noqa: F401 — fixtures y ayudantes de US-28
    ficha_b,
    ficha_confirmada,
    fcm,
    paciente_b,
    sin_sesion_guardada,
    telefono,
)
from .test_us35 import _crear_modelo

pytestmark = pytest.mark.django_db

REFORZADO = "recordatorio_reforzado"


# ==========================================================================
#  Ayudantes
# ==========================================================================
def predecir(org, ficha, nivel="high", modelo=None):
    """La predicción de US-35 de una ficha, como la dejaría `score_noshow`."""
    with tenant_context(org.id):
        modelo = modelo or _modelo_de(org)
        return NoShowPrediction.objects.create(
            organization=org, appointment=ficha, model_version=modelo,
            probability={"high": 0.6, "medium": 0.3, "low": 0.1}[nivel],
            level=nivel, factors=[],
        )


def _modelo_de(org):
    """El modelo vigente de la organización, o uno nuevo. Supone el contexto."""
    vigente = ModelVersion.objects.filter(organization=org, status="active").first()
    return vigente or _crear_modelo(org)


def con_marca(org, ficha):
    return recargar(org, ficha).reinforced_reminder_sent_at


def eventos(fcm):
    return [m["data"]["event"] for m in fcm.enviados]


@pytest.fixture
def pronto(paciente_a, org_a, practitioner_a, branches_a, agenda_a):
    """Una ficha pagada que empieza en 2 horas, reservada hace tres días."""
    return ficha_confirmada(org_a, paciente_a, practitioner_a,
                            branches_a["centro"], agenda_a, en_horas=2)


# ==========================================================================
#  Quién recibe el refuerzo
# ==========================================================================
def test_la_ficha_con_riesgo_alto_recibe_el_recordatorio_reforzado(
    fcm, paciente_a, org_a, pronto,
):
    telefono(paciente_a, org_a)
    predecir(org_a, pronto)

    assert reminders.run_cycle() == (1, 1)

    # Falta menos de 24 h, así que también le toca el primero: son dos avisos.
    assert sorted(eventos(fcm)) == ["recordatorio", REFORZADO]
    reforzado = next(m for m in fcm.enviados if m["data"]["event"] == REFORZADO)
    assert reforzado["data"]["appointment_id"] == str(pronto.id)
    assert reforzado["notification"]["title"] == "Tu ficha empieza pronto"
    assert "Laura Gómez" in reforzado["notification"]["body"]
    assert len(mail.outbox) == 2
    assert con_marca(org_a, pronto) is not None


def test_el_refuerzo_sale_mas_cerca_de_la_hora_que_el_primero(
    fcm, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    telefono(paciente_a, org_a)
    ficha = ficha_confirmada(org_a, paciente_a, practitioner_a,
                             branches_a["centro"], agenda_a, en_horas=10)
    predecir(org_a, ficha)
    ahora = timezone.now()

    # Faltan 10 h: toca el primero, todavía no el reforzado.
    assert reminders.run_cycle(ahora) == (1, 0)
    assert eventos(fcm) == ["recordatorio"]
    assert con_marca(org_a, ficha) is None

    # Faltan 2 h: ahora sí el reforzado, y el primero no se repite.
    assert reminders.run_cycle(ahora + dt.timedelta(hours=8)) == (0, 1)
    assert eventos(fcm) == ["recordatorio", REFORZADO]
    assert con_marca(org_a, ficha) is not None


def test_correr_dos_veces_no_repite_el_refuerzo(fcm, paciente_a, org_a, pronto):
    telefono(paciente_a, org_a)
    predecir(org_a, pronto)

    assert reminders.run_cycle() == (1, 1)
    assert reminders.run_cycle() == (0, 0)
    assert eventos(fcm).count(REFORZADO) == 1
    assert len(mail.outbox) == 2


def test_solo_el_riesgo_alto_recibe_el_refuerzo(
    fcm, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    telefono(paciente_a, org_a)
    fichas = {
        nivel: ficha_confirmada(org_a, paciente_a, practitioner_a,
                                branches_a["centro"], agenda_a, en_horas=horas)
        for nivel, horas in (("high", 0.5), ("medium", 1.5), ("low", 2.5))
    }
    for nivel, ficha in fichas.items():
        predecir(org_a, ficha, nivel)

    _, reforzados = reminders.run_cycle()

    assert reforzados == 1
    assert con_marca(org_a, fichas["high"]) is not None
    assert con_marca(org_a, fichas["medium"]) is None
    assert con_marca(org_a, fichas["low"]) is None


def test_el_refuerzo_y_el_primero_son_independientes(fcm, paciente_a, org_a, pronto):
    """Aunque el primero ya salió, el refuerzo sale; y al revés."""
    telefono(paciente_a, org_a)
    predecir(org_a, pronto)
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=pronto.pk).update(
            reminder_sent_at=timezone.now(),
        )

    assert reminders.run_cycle() == (0, 1)
    assert eventos(fcm) == [REFORZADO]


# ==========================================================================
#  Cuándo no hay refuerzo
# ==========================================================================
def test_sin_prediccion_no_hay_refuerzo(fcm, paciente_a, org_a, pronto):
    telefono(paciente_a, org_a)

    assert reminders.run_cycle() == (1, 0)
    assert eventos(fcm) == ["recordatorio"]
    assert con_marca(org_a, pronto) is None


def test_sin_modelo_vigente_no_hay_refuerzo(fcm, paciente_a, org_a, pronto):
    """La predicción de un modelo retirado ya no se usa."""
    telefono(paciente_a, org_a)
    with tenant_context(org_a.id):
        retirado = _crear_modelo(org_a)
    predecir(org_a, pronto, modelo=retirado)
    with tenant_context(org_a.id):
        retirado.status = ModelVersion.Status.RETIRED
        retirado.save(update_fields=["status"])

    assert reminders.run_cycle() == (1, 0)
    assert con_marca(org_a, pronto) is None


def test_sin_el_plan_que_incluye_la_prediccion_no_hay_refuerzo(
    fcm, plans, paciente_a, org_a, pronto,
):
    """La predicción queda guardada, pero el centro bajó de plan."""
    telefono(paciente_a, org_a)
    predecir(org_a, pronto)
    with platform_admin_context():
        Subscription.objects.filter(organization=org_a).update(plan=plans["basic"])

    assert reminders.run_cycle() == (1, 0)
    assert REFORZADO not in eventos(fcm)
    assert con_marca(org_a, pronto) is None


def test_no_se_refuerza_lo_que_no_corresponde(
    fcm, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    telefono(paciente_a, org_a)
    centro = branches_a["centro"]
    args = (org_a, paciente_a, practitioner_a, centro, agenda_a)
    candidatas = [
        ficha_confirmada(*args, en_horas=8),                       # falta mucho
        ficha_confirmada(*args, en_horas=0.5,                       # sin pagar
                         status=Appointment.Status.PENDING_PAYMENT),
        ficha_confirmada(*args, en_horas=1.5,                       # cancelada
                         status=Appointment.Status.CANCELLED),
        ficha_confirmada(*args, en_horas=-1,                        # ya empezó
                         status=Appointment.Status.CONFIRMED),
        # Reservada hace unos minutos para dentro de dos horas y media, ya con
        # la ventana de 3 horas abierta: el aviso de confirmación acaba de
        # salir, reforzarla sería repetirlo.
        ficha_confirmada(*args, en_horas=2.5, reservada_hace_horas=0.2),
    ]
    for ficha in candidatas:
        predecir(org_a, ficha)

    _, reforzados = reminders.run_cycle()

    assert reforzados == 0
    assert REFORZADO not in eventos(fcm)
    assert all(con_marca(org_a, f) is None for f in candidatas)


def test_el_paciente_sin_telefono_igual_queda_marcado(paciente_a, org_a, pronto):
    """Si el aviso fallara cada vuelta, se repetiría para siempre."""
    predecir(org_a, pronto)

    assert reminders.run_cycle() == (1, 1)
    assert reminders.run_cycle() == (0, 0)
    assert con_marca(org_a, pronto) is not None


# ==========================================================================
#  El texto
# ==========================================================================
def test_el_aviso_no_le_dice_al_paciente_como_lo_califica_el_centro(
    fcm, paciente_a, org_a, pronto,
):
    telefono(paciente_a, org_a)
    predecir(org_a, pronto)
    reminders.run_cycle()

    reforzado = next(m for m in fcm.enviados if m["data"]["event"] == REFORZADO)
    correo = next(c for c in mail.outbox if c.subject.startswith("Tu ficha de "))
    textos = " ".join([
        reforzado["notification"]["title"], reforzado["notification"]["body"],
        correo.subject, correo.body,
    ]).lower()
    for palabra in ("riesgo", "inasistencia", "probabilidad", "falt"):
        assert palabra not in textos


def test_el_correo_del_refuerzo_pide_confirmar_solo_si_no_confirmo(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    centro = branches_a["centro"]
    sin_confirmar = ficha_confirmada(org_a, paciente_a, practitioner_a, centro,
                                     agenda_a, en_horas=2)
    confirmada = ficha_confirmada(org_a, paciente_a, practitioner_a, centro,
                                  agenda_a, en_horas=1,
                                  attendance_confirmed_at=timezone.now())
    predecir(org_a, sin_confirmar)
    predecir(org_a, confirmada)

    assert reminders.run_cycle()[1] == 2

    reforzados = [c for c in mail.outbox if c.subject.startswith("Tu ficha de ")]
    con_enlace = [c for c in reforzados if "/api/appointments/attendance/" in c.body]
    assert len(reforzados) == 2
    assert len(con_enlace) == 1


# ==========================================================================
#  Varias organizaciones y el proceso
# ==========================================================================
@pytest.mark.isolation
def test_cada_organizacion_refuerza_solo_sus_fichas_a_sus_telefonos(
    fcm, plans, paciente_a, paciente_b, org_a, org_b, pronto, ficha_b,
):
    with platform_admin_context():
        Subscription.objects.filter(organization=org_b).update(plan=plans["premium"])
    with tenant_context(org_b.id):
        Appointment.objects.filter(pk=ficha_b.pk).update(
            starts_at=timezone.now() + dt.timedelta(hours=2),
        )
    telefono(paciente_a, org_a, "telefono-de-a")
    telefono(paciente_b, org_b, "telefono-de-b")
    predecir(org_a, pronto)
    predecir(org_b, ficha_b)

    assert reminders.run_cycle()[1] == 2

    de_a = [m["data"]["event"] for m in fcm.a("telefono-de-a")]
    de_b = [m["data"]["event"] for m in fcm.a("telefono-de-b")]
    assert de_a.count(REFORZADO) == 1 and de_b.count(REFORZADO) == 1
    assert {m["data"]["appointment_id"] for m in fcm.a("telefono-de-a")} == {
        str(pronto.id)}
    assert {m["data"]["appointment_id"] for m in fcm.a("telefono-de-b")} == {
        str(ficha_b.id)}


def test_si_una_organizacion_falla_las_demas_reciben_su_refuerzo(
    fcm, monkeypatch, plans, paciente_a, paciente_b, org_a, org_b, pronto, ficha_b,
):
    with platform_admin_context():
        Subscription.objects.filter(organization=org_b).update(plan=plans["premium"])
    with tenant_context(org_b.id):
        Appointment.objects.filter(pk=ficha_b.pk).update(
            starts_at=timezone.now() + dt.timedelta(hours=2),
        )
    predecir(org_a, pronto)
    predecir(org_b, ficha_b)
    original = reminders.run_reinforced_for

    def falla_en_a(organization, now=None):
        if organization.id == org_a.id:
            raise RuntimeError("la organización A falló")
        return original(organization, now)

    monkeypatch.setattr(reminders, "run_reinforced_for", falla_en_a)

    assert reminders.run_cycle()[1] == 1
    assert con_marca(org_a, pronto) is None
    assert con_marca(org_b, ficha_b) is not None


def test_si_falla_el_refuerzo_el_primer_recordatorio_sale_igual(
    fcm, monkeypatch, paciente_a, org_a, pronto,
):
    telefono(paciente_a, org_a)
    predecir(org_a, pronto)

    def siempre_falla(organization, now=None):
        raise RuntimeError("el refuerzo falló")

    monkeypatch.setattr(reminders, "run_reinforced_for", siempre_falla)

    assert reminders.run_cycle() == (1, 0)
    assert eventos(fcm) == ["recordatorio"]


def test_el_comando_cuenta_los_reforzados(org_a, pronto, capsys):
    predecir(org_a, pronto)

    call_command("send_appointment_reminders")

    salida = capsys.readouterr().out
    assert "Recordatorios de fichas: 1 enviado(s)." in salida
    assert "Recordatorios reforzados: 1 enviado(s)." in salida


@override_settings(APPOINTMENT_REMINDERS="off")
def test_con_los_recordatorios_apagados_tampoco_sale_el_refuerzo(
    org_a, pronto, capsys,
):
    predecir(org_a, pronto)

    call_command("send_appointment_reminders")

    assert "apagados" in capsys.readouterr().out
    assert con_marca(org_a, pronto) is None
    assert mail.outbox == []


@override_settings(APPOINTMENT_REINFORCED_REMINDER_HOURS=6)
def test_las_horas_del_refuerzo_se_configuran(
    fcm, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    telefono(paciente_a, org_a)
    ficha = ficha_confirmada(org_a, paciente_a, practitioner_a,
                             branches_a["centro"], agenda_a, en_horas=5)
    predecir(org_a, ficha)

    assert reminders.run_cycle()[1] == 1
