"""US-52 — Lista de espera con aviso de cupo liberado.

Dos mitades:

1. **El turno guardado vence de verdad.** La lista de espera guarda el turno 15
   minutos como una ficha `pending_payment`; si nadie la paga tiene que volver
   a ser libre. Hasta US-52 no lo era: una reserva vencida seguía ocupando el
   turno para siempre. Esta primera parte prueba ese arreglo.
2. La lista en sí: anotarse, el orden, el aviso y la tasa de recuperación
   (más abajo, a medida que se construye cada fase).
"""

import datetime as dt
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appointments import booking, waitlist
from appointments.holds import release_expired_holds
from appointments.models import Appointment, WaitlistEntry
from catalog.models import Practitioner, PractitionerSpecialty
from patients.models import Patient
from scheduling.availability import consolidated_availability
from scheduling.models import Schedule
from tenancy.context import tenant_context

from .conftest import PERMISOS_PACIENTE, dar_rol
from .fichas_comunes import (  # noqa: F401 — fixtures
    agenda_a,
    api_client,
    autenticar,
    crear_ficha,
    otro_paciente_a,
    paciente_a,
    perfil_paciente,
    recargar,
)
from .test_planes import con_plan
from .test_us28 import (  # noqa: F401 — fixtures y ayudantes de US-28
    fcm,
    paciente_b,
    pagar,
    sin_sesion_guardada,
    telefono,
)

pytestmark = pytest.mark.django_db

LA_PAZ = ZoneInfo("America/La_Paz")


def turno(dias=7, hora=9):
    """Un turno real de `agenda_a` (su día de la semana es el de hoy)."""
    dia = dt.date.today() + dt.timedelta(days=dias)
    return dt.datetime.combine(dia, dt.time(hora, 0), tzinfo=LA_PAZ)


def libres(org, practitioner, *, dias=7):
    """Las horas de inicio libres ese día, tal como las ve el paciente."""
    dia = dt.date.today() + dt.timedelta(days=dias)
    with tenant_context(org.id):
        datos = consolidated_availability(
            practitioner_id=practitioner.id, date_from=dia, date_to=dia,
        )
    return [
        dt.datetime.fromisoformat(espacio["start"]).astimezone(LA_PAZ).hour
        for dia_ in datos["days"] for espacio in dia_["slots"]
    ]


def reservar(org, usuario, practitioner, branches, agenda, inicio):
    with tenant_context(org.id):
        return booking.book_appointment(
            organization=org, patient_id=usuario.patient_profile.id,
            practitioner_id=practitioner.id, branch_id=branches["centro"].id,
            schedule_id=agenda.id, starts_at=inicio, booked_by=usuario,
        )


# ==========================================================================
#  Parte 1 — el turno guardado vence de verdad
# ==========================================================================
def vencida(org, paciente, practitioner, branches, agenda, inicio, **extra):
    return crear_ficha(
        org, paciente, practitioner, branches["centro"], agenda,
        starts_at=inicio, status=Appointment.Status.PENDING_PAYMENT,
        expires_at=timezone.now() - dt.timedelta(minutes=1), **extra,
    )


def test_una_reserva_vencida_deja_el_turno_libre_en_la_busqueda(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    vencida(org_a, paciente_a, practitioner_a, branches_a, agenda_a, turno())
    assert 9 in libres(org_a, practitioner_a)


def test_una_reserva_vigente_sigue_ocupando_el_turno(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=turno(), status=Appointment.Status.PENDING_PAYMENT,
        expires_at=timezone.now() + dt.timedelta(minutes=10),
    )
    assert 9 not in libres(org_a, practitioner_a)


def test_una_ficha_confirmada_ocupa_el_turno_aunque_no_tenga_vencimiento(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=turno(), status=Appointment.Status.CONFIRMED, expires_at=None,
    )
    assert 9 not in libres(org_a, practitioner_a)


def test_otro_paciente_puede_reservar_el_turno_de_una_reserva_vencida(
    paciente_a, otro_paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    vieja = vencida(org_a, paciente_a, practitioner_a, branches_a, agenda_a, turno())

    nueva = reservar(org_a, otro_paciente_a, practitioner_a, branches_a, agenda_a,
                     turno())

    assert nueva.status == Appointment.Status.PENDING_PAYMENT
    assert recargar(org_a, vieja).status == Appointment.Status.EXPIRED


def test_una_reserva_vigente_no_se_le_quita_a_su_dueno(
    paciente_a, otro_paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=turno(), status=Appointment.Status.PENDING_PAYMENT,
        expires_at=timezone.now() + dt.timedelta(minutes=10),
    )
    with pytest.raises(booking.SlotAlreadyTaken):
        reservar(org_a, otro_paciente_a, practitioner_a, branches_a, agenda_a,
                 turno())


def test_liberar_vencidas_marca_solo_las_vencidas_y_es_idempotente(
    paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    muerta = vencida(org_a, paciente_a, practitioner_a, branches_a, agenda_a,
                     turno(7))
    viva = crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=turno(7, 10), status=Appointment.Status.PENDING_PAYMENT,
        expires_at=timezone.now() + dt.timedelta(minutes=10),
    )
    confirmada = crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_a,
        starts_at=turno(14), status=Appointment.Status.CONFIRMED, expires_at=None,
    )

    with tenant_context(org_a.id):
        assert [f.id for f in release_expired_holds()] == [muerta.id]
        assert release_expired_holds() == []

    assert recargar(org_a, muerta).status == Appointment.Status.EXPIRED
    assert recargar(org_a, viva).status == Appointment.Status.PENDING_PAYMENT
    assert recargar(org_a, confirmada).status == Appointment.Status.CONFIRMED


# ==========================================================================
#  Parte 2 — la lista de espera
# ==========================================================================
LISTA = "appointments:waitlist"


@pytest.fixture
def agenda_unica(org_a, practitioner_a, branches_a):
    """Un solo turno, el de las 09:00 de dentro de 7 días: cabe en la prueba
    "no hay turnos, me anoto" sin depender del día en que corra."""
    objetivo = dt.date.today() + dt.timedelta(days=7)
    with tenant_context(org_a.id):
        return Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=objetivo.weekday(),
            start_time="09:00", end_time="10:00", slot_minutes=60,
            valid_from=objetivo - dt.timedelta(days=6), valid_until=objetivo,
        )


@pytest.fixture
def tercer_paciente_a(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="tercero@centro.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Tercer", last_name="Paciente",
            document_number="TERC-52",
        )
    dar_rol(user, org_a, "patient-tercero", "Paciente", PERMISOS_PACIENTE)
    perfil_paciente(user, org_a)
    return user


@pytest.fixture
def dependiente_de_b(org_a, otro_paciente_a):
    with tenant_context(org_a.id):
        return Patient.objects.create(
            organization=org_a, guardian=otro_paciente_a.patient_profile,
            relationship=Patient.Relationship.CHILD,
            document_type=Patient.DocumentType.CI, document_number="DEP-52",
            first_name="Hijo", last_name="Chico", birth_date=dt.date(2016, 3, 1),
        )


@pytest.fixture
def admin_a(db, org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="admin52@centro.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Admin", last_name="Centro",
            document_number="ADM-52",
        )
    dar_rol(user, org_a, "admin-kpi", "Administración", ["reporting.kpi.read"])
    return user


def ocupar(org, usuario, practitioner, branches, agenda, **extra):
    """El turno de `agenda_unica` queda pagado por [usuario]."""
    return crear_ficha(
        org, usuario, practitioner, branches["centro"], agenda,
        starts_at=turno(), status=extra.pop("status", Appointment.Status.CONFIRMED),
        expires_at=None, **extra,
    )


def anotar(org, usuario, practitioner=None, *, especialidad=None, sucursal=None,
           desde=0, hasta=14, paciente=None):
    with tenant_context(org.id):
        return waitlist.join(
            organization=org, user=usuario,
            patient_id=(paciente or usuario.patient_profile).id,
            practitioner_id=practitioner.id if practitioner else None,
            specialty_id=especialidad.id if especialidad else None,
            branch_id=sucursal.id if sucursal else None,
            date_from=dt.date.today() + dt.timedelta(days=desde),
            date_to=dt.date.today() + dt.timedelta(days=hasta),
        )


def cancelar(api_client, usuario, ficha, ejecutar):
    """Cancela por la API y corre lo que quedó para después del COMMIT."""
    with ejecutar(execute=True):
        return autenticar(api_client, usuario).post(
            reverse("appointments:appointment-cancel", args=[ficha.id]),
        )


def entrada(org, e):
    with tenant_context(org.id):
        e.refresh_from_db()
    return e


def ofrecida_a(org, usuario):
    """La ficha pendiente que se le guardó a [usuario], o `None`."""
    with tenant_context(org.id):
        return Appointment.objects.filter(
            patient=usuario.patient_profile,
            status=Appointment.Status.PENDING_PAYMENT,
        ).first()


# ---------- Anotarse ------------------------------------------------------
def test_anotarse_crea_la_entrada_y_dice_su_posicion(
    api_client, paciente_a, practitioner_a, org_a,
):
    hoy = dt.date.today()
    respuesta = autenticar(api_client, paciente_a).post(reverse(LISTA), {
        "patient": str(paciente_a.patient_profile.id),
        "practitioner": str(practitioner_a.id),
        "date_from": hoy.isoformat(),
        "date_to": (hoy + dt.timedelta(days=10)).isoformat(),
    }, format="json")

    assert respuesta.status_code == 201, respuesta.json()
    cuerpo = respuesta.json()
    assert cuerpo["status"] == "waiting" and cuerpo["position"] == 1
    assert cuerpo["practitioner_name"] == "Laura Gómez"

    lista = autenticar(api_client, paciente_a).get(reverse(LISTA)).json()
    assert lista["enabled"] is True
    assert [e["id"] for e in lista["results"]] == [cuerpo["id"]]


def test_la_posicion_sigue_el_orden_de_llegada(
    paciente_a, otro_paciente_a, tercer_paciente_a, practitioner_a, org_a,
):
    primero = anotar(org_a, paciente_a, practitioner_a)
    segundo = anotar(org_a, otro_paciente_a, practitioner_a)
    tercero = anotar(org_a, tercer_paciente_a, practitioner_a)
    with tenant_context(org_a.id):
        assert [waitlist.position(e) for e in (primero, segundo, tercero)] == [1, 2, 3]
        waitlist.leave(primero)
        assert waitlist.position(primero) is None
        assert [waitlist.position(e) for e in (segundo, tercero)] == [1, 2]


def test_no_se_puede_anotar_dos_veces_al_mismo_profesional(
    paciente_a, practitioner_a, org_a,
):
    anotar(org_a, paciente_a, practitioner_a)
    with pytest.raises(Exception) as error:
        anotar(org_a, paciente_a, practitioner_a)
    assert getattr(error.value, "code", "") == "ya_anotado"
    with tenant_context(org_a.id):
        assert WaitlistEntry.objects.count() == 1


def test_si_hay_turno_libre_no_tiene_sentido_anotarse(
    paciente_a, practitioner_a, org_a, agenda_unica,
):
    with pytest.raises(Exception) as error:
        anotar(org_a, paciente_a, practitioner_a)
    assert getattr(error.value, "code", "") == "hay_turnos"


def test_un_rango_en_el_pasado_o_invertido_no_se_acepta(
    paciente_a, practitioner_a, org_a,
):
    def codigo(**rango):
        with pytest.raises(Exception) as error:
            anotar(org_a, paciente_a, practitioner_a, **rango)
        return getattr(error.value, "code", "")

    assert codigo(desde=-2, hasta=3) == "rango_pasado"
    assert codigo(desde=5, hasta=2) == "rango_invalido"
    assert codigo(desde=0, hasta=400) == "rango_largo"


def test_hay_que_elegir_profesional_o_especialidad_pero_no_las_dos(
    paciente_a, practitioner_a, specialty_a, org_a,
):
    for profesional, especialidad in ((None, None), (practitioner_a, specialty_a)):
        with pytest.raises(Exception) as error:
            anotar(org_a, paciente_a, profesional, especialidad=especialidad)
        assert getattr(error.value, "code", "") == "destino_invalido"


def test_anotarse_por_un_dependiente_y_no_por_un_ajeno(
    paciente_a, otro_paciente_a, dependiente_de_b, practitioner_a, org_a,
):
    propia = anotar(org_a, otro_paciente_a, practitioner_a,
                    paciente=dependiente_de_b)
    assert propia.patient_id == dependiente_de_b.id

    with pytest.raises(Exception) as error:
        anotar(org_a, paciente_a, practitioner_a, paciente=dependiente_de_b)
    assert getattr(error.value, "code", "") == "paciente_invalido"


def test_quien_no_es_paciente_no_se_anota(admin_a, practitioner_a, org_a):
    with pytest.raises(Exception) as error:
        with tenant_context(org_a.id):
            waitlist.join(
                organization=org_a, user=admin_a, patient_id=practitioner_a.id,
                practitioner_id=practitioner_a.id,
                date_from=dt.date.today(),
                date_to=dt.date.today() + dt.timedelta(days=3),
            )
    assert getattr(error.value, "code", "") == "no_es_paciente"


def test_el_basico_no_tiene_lista_de_espera(
    api_client, paciente_a, practitioner_a, org_a, plans,
):
    con_plan(org_a, plans, "basic")
    hoy = dt.date.today()
    cliente = autenticar(api_client, paciente_a)

    respuesta = cliente.post(reverse(LISTA), {
        "patient": str(paciente_a.patient_profile.id),
        "practitioner": str(practitioner_a.id),
        "date_from": hoy.isoformat(),
        "date_to": (hoy + dt.timedelta(days=5)).isoformat(),
    }, format="json")
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "plan_limit"

    lista = cliente.get(reverse(LISTA)).json()
    assert lista == {"enabled": False, "results": []}


def test_el_pro_si_tiene_lista_de_espera(
    api_client, paciente_a, practitioner_a, org_a, plans,
):
    con_plan(org_a, plans, "pro")
    assert autenticar(api_client, paciente_a).get(reverse(LISTA)).json()["enabled"]


def test_el_profesional_de_otra_organizacion_no_existe(
    api_client, paciente_a, paciente_b, org_a, org_b,
):
    with tenant_context(org_b.id):
        ajeno = Practitioner.objects.create(
            organization=org_b, first_name="Pedro", last_name="Vaca",
        )
    hoy = dt.date.today()
    respuesta = autenticar(api_client, paciente_a).post(reverse(LISTA), {
        "patient": str(paciente_a.patient_profile.id),
        "practitioner": str(ajeno.id),
        "date_from": hoy.isoformat(),
        "date_to": (hoy + dt.timedelta(days=5)).isoformat(),
    }, format="json")
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "profesional_invalido"


def test_cada_paciente_ve_y_borra_solo_lo_suyo(
    api_client, paciente_a, otro_paciente_a, paciente_b, practitioner_a, org_a,
):
    mia = anotar(org_a, paciente_a, practitioner_a)

    ajena_lista = autenticar(api_client, otro_paciente_a).get(reverse(LISTA)).json()
    assert ajena_lista["results"] == []
    for intruso in (otro_paciente_a, paciente_b):
        borrado = autenticar(api_client, intruso).delete(
            reverse("appointments:waitlist-entry", args=[mia.id]))
        assert borrado.status_code == 404
    assert entrada(org_a, mia).status == "waiting"

    salir = autenticar(api_client, paciente_a).delete(
        reverse("appointments:waitlist-entry", args=[mia.id]))
    assert salir.status_code == 204
    assert entrada(org_a, mia).status == "cancelled"
    assert autenticar(api_client, paciente_a).get(reverse(LISTA)).json()["results"] == []


# ---------- Ofrecer el turno liberado --------------------------------------
@pytest.fixture
def fila(
    paciente_a, otro_paciente_a, tercer_paciente_a, practitioner_a, branches_a,
    agenda_unica, org_a,
):
    """A tiene el único turno; B y C esperan, en ese orden."""
    ficha = ocupar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica)
    return {
        "ficha": ficha,
        "b": anotar(org_a, otro_paciente_a, practitioner_a),
        "c": anotar(org_a, tercer_paciente_a, practitioner_a),
    }


def test_cancelar_le_guarda_el_turno_al_primero_y_le_avisa(
    api_client, fcm, fila, paciente_a, otro_paciente_a, tercer_paciente_a,
    practitioner_a, org_a, django_capture_on_commit_callbacks,
):
    telefono(otro_paciente_a, org_a, "tel-b")
    telefono(tercer_paciente_a, org_a, "tel-c")

    respuesta = cancelar(api_client, paciente_a, fila["ficha"],
                         django_capture_on_commit_callbacks)
    assert respuesta.status_code == 200, respuesta.json()

    guardada = ofrecida_a(org_a, otro_paciente_a)
    assert guardada is not None
    assert guardada.starts_at == fila["ficha"].starts_at
    minutos = (guardada.expires_at - timezone.now()).total_seconds() / 60
    assert 13 < minutos <= 15

    b = entrada(org_a, fila["b"])
    assert b.status == "offered" and b.offered_appointment_id == guardada.id
    assert entrada(org_a, fila["c"]).status == "waiting"
    assert ofrecida_a(org_a, tercer_paciente_a) is None

    # El aviso: sólo a B, con el turno guardado y sin datos de los demás.
    [aviso] = fcm.a("tel-b")
    assert aviso["notification"]["title"] == "Se liberó un turno para ti"
    assert aviso["data"] == {"appointment_id": str(guardada.id),
                             "event": "cupo_liberado"}
    assert fcm.a("tel-c") == []
    textos = [aviso["notification"]["body"]]
    correo = [m for m in mail.outbox if "Se liberó un turno" in m.subject]
    assert len(correo) == 1 and correo[0].to == [otro_paciente_a.email]
    textos += [correo[0].subject, correo[0].body]
    for texto in textos:
        for ajeno in ("Tercer", "tercero@", paciente_a.email):
            assert ajeno not in texto
    assert "15 minutos" in correo[0].body


def test_dos_pacientes_compiten_por_el_mismo_cupo_y_solo_uno_se_lo_queda(
    fila, otro_paciente_a, tercer_paciente_a, org_a,
):
    ficha = fila["ficha"]
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=ficha.pk).update(
            status=Appointment.Status.CANCELLED, cancelled_at=timezone.now())

    primera = waitlist.offer_freed_slot(ficha.id, org_a.id)
    segunda = waitlist.offer_freed_slot(ficha.id, org_a.id)

    assert (primera, segunda) == (True, False)
    with tenant_context(org_a.id):
        activas = Appointment.objects.filter(
            starts_at=ficha.starts_at, status__in=Appointment.ACTIVE_STATUSES)
        assert activas.count() == 1
    assert entrada(org_a, fila["b"]).status == "offered"
    assert entrada(org_a, fila["c"]).status == "waiting"


def test_si_alguien_reserva_antes_el_turno_ya_no_se_ofrece(
    fila, tercer_paciente_a, practitioner_a, branches_a, agenda_unica, org_a,
):
    ficha = fila["ficha"]
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=ficha.pk).update(
            status=Appointment.Status.CANCELLED, cancelled_at=timezone.now())
    # Un tercero —que no está en la lista— se lo lleva primero.
    reservar(org_a, tercer_paciente_a, practitioner_a, branches_a, agenda_unica,
             turno())

    assert waitlist.offer_freed_slot(ficha.id, org_a.id) is False
    assert entrada(org_a, fila["b"]).status == "waiting"


def test_el_turno_guardado_vence_y_pasa_al_siguiente(
    api_client, fcm, fila, paciente_a, otro_paciente_a, tercer_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    telefono(tercer_paciente_a, org_a, "tel-c")
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada_b = ofrecida_a(org_a, otro_paciente_a)
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=guardada_b.pk).update(
            expires_at=timezone.now() - dt.timedelta(minutes=1))

    resultado = waitlist.run_organization(org_a)

    assert resultado == {"liberadas": 1, "ofrecidas": 1}
    assert recargar(org_a, guardada_b).status == Appointment.Status.EXPIRED
    assert entrada(org_a, fila["b"]).status == "expired"
    guardada_c = ofrecida_a(org_a, tercer_paciente_a)
    assert guardada_c is not None and guardada_c.starts_at == guardada_b.starts_at
    assert entrada(org_a, fila["c"]).status == "offered"
    assert len(fcm.a("tel-c")) == 1


def test_si_nadie_mas_espera_el_turno_vuelve_a_estar_libre(
    api_client, fila, paciente_a, practitioner_a, org_a,
    django_capture_on_commit_callbacks, otro_paciente_a, tercer_paciente_a,
):
    with tenant_context(org_a.id):
        waitlist.leave(entrada(org_a, fila["c"]))
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada = ofrecida_a(org_a, otro_paciente_a)
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=guardada.pk).update(
            expires_at=timezone.now() - dt.timedelta(minutes=1))

    assert waitlist.run_organization(org_a) == {"liberadas": 1, "ofrecidas": 0}
    assert 9 in libres(org_a, practitioner_a)


def test_pagar_el_turno_ofrecido_cierra_la_entrada(
    api_client, fila, paciente_a, otro_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada = ofrecida_a(org_a, otro_paciente_a)

    pagar(org_a, guardada, otro_paciente_a)
    with tenant_context(org_a.id):
        waitlist.refresh_entries()

    assert recargar(org_a, guardada).status == Appointment.Status.CONFIRMED
    assert entrada(org_a, fila["b"]).status == "booked"


def test_un_pago_tardio_sobre_la_reserva_vencida_se_devuelve(
    api_client, fila, paciente_a, otro_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    from payments.models import Payment

    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada = ofrecida_a(org_a, otro_paciente_a)
    with tenant_context(org_a.id):
        Appointment.objects.filter(pk=guardada.pk).update(
            expires_at=timezone.now() - dt.timedelta(minutes=1))
    waitlist.run_organization(org_a)

    pago = pagar(org_a, guardada, otro_paciente_a)

    assert recargar(org_a, guardada).status == Appointment.Status.EXPIRED
    assert pago.status == Payment.Status.REFUNDED


def test_reprogramar_tambien_libera_el_turno_y_se_ofrece(
    api_client, fila, paciente_a, otro_paciente_a, practitioner_a, branches_a,
    org_a, django_capture_on_commit_callbacks,
):
    objetivo = dt.date.today() + dt.timedelta(days=7)
    with tenant_context(org_a.id):
        otra = Schedule.objects.create(
            organization=org_a, practitioner=practitioner_a,
            branch=branches_a["centro"], weekday=objetivo.weekday(),
            start_time="14:00", end_time="15:00", slot_minutes=60,
            valid_from=objetivo - dt.timedelta(days=6), valid_until=objetivo,
        )
    with django_capture_on_commit_callbacks(execute=True):
        respuesta = autenticar(api_client, paciente_a).post(
            reverse("appointments:appointment-reschedule", args=[fila["ficha"].id]),
            {"branch": str(branches_a["centro"].id), "schedule": str(otra.id),
             "starts_at": turno(7, 14).isoformat()}, format="json")
    assert respuesta.status_code == 200, respuesta.json()

    guardada = ofrecida_a(org_a, otro_paciente_a)
    assert guardada is not None and guardada.starts_at == fila["ficha"].starts_at


def test_quien_cancela_no_se_ofrece_a_si_mismo_el_turno(
    api_client, fila, paciente_a, practitioner_a, org_a,
    django_capture_on_commit_callbacks, otro_paciente_a,
):
    # Sólo A espera (B y C salen): si el turno es suyo, se lo estaría ofreciendo
    # a quien lo acaba de soltar.
    with tenant_context(org_a.id):
        waitlist.leave(entrada(org_a, fila["b"]))
        waitlist.leave(entrada(org_a, fila["c"]))
    anotar(org_a, paciente_a, practitioner_a)
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)

    assert ofrecida_a(org_a, paciente_a) is None
    assert ofrecida_a(org_a, otro_paciente_a) is None


def test_no_se_ofrece_a_quien_ya_tiene_otra_ficha_a_esa_hora(
    api_client, fila, paciente_a, otro_paciente_a, tercer_paciente_a,
    practitioner_a, branches_a, org_a, django_capture_on_commit_callbacks,
):
    with tenant_context(org_a.id):
        otro_medico = Practitioner.objects.create(
            organization=org_a, first_name="Otro", last_name="Medico",
            license_number="MP-2000",
        )
        agenda = Schedule.objects.create(
            organization=org_a, practitioner=otro_medico,
            branch=branches_a["centro"],
            weekday=fila["ficha"].starts_at.astimezone(LA_PAZ).weekday(),
            start_time="09:00", end_time="10:00", slot_minutes=60,
            valid_from=dt.date.today() - dt.timedelta(days=7),
        )
    # B ya tiene ficha a la misma hora con otro médico.
    crear_ficha(org_a, otro_paciente_a, otro_medico, branches_a["centro"], agenda,
                starts_at=turno(), status=Appointment.Status.CONFIRMED,
                expires_at=None)

    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)

    assert ofrecida_a(org_a, otro_paciente_a) is None
    assert ofrecida_a(org_a, tercer_paciente_a) is not None
    assert entrada(org_a, fila["b"]).status == "waiting"


def test_cancelar_un_turno_que_ya_paso_no_ofrece_nada(
    api_client, paciente_a, otro_paciente_a, tercer_paciente_a, practitioner_a,
    branches_a, agenda_unica, org_a, django_capture_on_commit_callbacks, fcm,
):
    telefono(otro_paciente_a, org_a)
    ocupar(org_a, tercer_paciente_a, practitioner_a, branches_a, agenda_unica)
    pasada = crear_ficha(
        org_a, paciente_a, practitioner_a, branches_a["centro"], agenda_unica,
        starts_at=timezone.now() - dt.timedelta(hours=2),
        status=Appointment.Status.CONFIRMED, expires_at=None)
    espera = anotar(org_a, otro_paciente_a, practitioner_a)

    respuesta = cancelar(api_client, paciente_a, pasada,
                         django_capture_on_commit_callbacks)

    assert respuesta.status_code == 400
    assert entrada(org_a, espera).status == "waiting"
    assert fcm.enviados == []


def test_por_especialidad_sirve_cualquier_profesional_de_ella(
    api_client, paciente_a, otro_paciente_a, specialty_a, practitioner_a,
    branches_a, agenda_unica, org_a, django_capture_on_commit_callbacks,
):
    ficha = ocupar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica)
    espera = anotar(org_a, otro_paciente_a, especialidad=specialty_a)

    cancelar(api_client, paciente_a, ficha, django_capture_on_commit_callbacks)

    assert entrada(org_a, espera).status == "offered"
    assert ofrecida_a(org_a, otro_paciente_a).practitioner_id == practitioner_a.id


def test_una_especialidad_distinta_no_recibe_el_turno(
    api_client, paciente_a, otro_paciente_a, practitioner_a, branches_a,
    agenda_unica, org_a, django_capture_on_commit_callbacks,
):
    from catalog.models import Specialty

    ficha = ocupar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica)
    with tenant_context(org_a.id):
        otra = Specialty.objects.create(organization=org_a, name="Dermatología")
    # Esa especialidad no tiene profesionales ni turnos: puede anotarse.
    espera = anotar(org_a, otro_paciente_a, especialidad=otra)

    cancelar(api_client, paciente_a, ficha, django_capture_on_commit_callbacks)

    assert entrada(org_a, espera).status == "waiting"


def test_la_sucursal_pedida_se_respeta(
    api_client, paciente_a, otro_paciente_a, practitioner_a, branches_a,
    agenda_unica, org_a, django_capture_on_commit_callbacks,
):
    ficha = ocupar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica)
    espera = anotar(org_a, otro_paciente_a, practitioner_a,
                    sucursal=branches_a["norte"])

    cancelar(api_client, paciente_a, ficha, django_capture_on_commit_callbacks)

    assert entrada(org_a, espera).status == "waiting"   # el turno es del centro


def test_fuera_del_rango_de_fechas_no_se_ofrece(
    api_client, paciente_a, otro_paciente_a, practitioner_a, branches_a,
    agenda_unica, org_a, django_capture_on_commit_callbacks,
):
    ficha = ocupar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica)
    espera = anotar(org_a, otro_paciente_a, practitioner_a, desde=0, hasta=3)

    cancelar(api_client, paciente_a, ficha, django_capture_on_commit_callbacks)

    assert entrada(org_a, espera).status == "waiting"


def test_una_organizacion_sin_el_plan_no_ofrece(
    api_client, fila, paciente_a, otro_paciente_a, org_a, plans,
    django_capture_on_commit_callbacks,
):
    con_plan(org_a, plans, "basic")
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    assert ofrecida_a(org_a, otro_paciente_a) is None
    assert entrada(org_a, fila["b"]).status == "waiting"


def test_con_el_tope_de_fichas_del_mes_no_se_ofrece(
    api_client, fila, paciente_a, otro_paciente_a, org_a, plans,
    django_capture_on_commit_callbacks,
):
    con_plan(org_a, plans, "pro", max_appointments_month=1)
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    assert ofrecida_a(org_a, otro_paciente_a) is None


def test_si_el_push_falla_la_cancelacion_y_la_oferta_siguen(
    api_client, fcm, fila, paciente_a, otro_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    telefono(otro_paciente_a, org_a)
    fcm.caido = True

    respuesta = cancelar(api_client, paciente_a, fila["ficha"],
                         django_capture_on_commit_callbacks)

    assert respuesta.status_code == 200
    assert recargar(org_a, fila["ficha"]).status == Appointment.Status.CANCELLED
    assert ofrecida_a(org_a, otro_paciente_a) is not None


def test_un_error_al_ofrecer_no_deshace_la_cancelacion(
    api_client, fila, paciente_a, org_a, monkeypatch,
    django_capture_on_commit_callbacks,
):
    def roto(*args, **kwargs):
        raise RuntimeError("falló la oferta")

    monkeypatch.setattr(waitlist, "offer_slot", roto)
    respuesta = cancelar(api_client, paciente_a, fila["ficha"],
                         django_capture_on_commit_callbacks)

    assert respuesta.status_code == 200
    assert recargar(org_a, fila["ficha"]).status == Appointment.Status.CANCELLED


# ---------- El proceso y el mantenimiento ----------------------------------
def test_el_proceso_es_idempotente(
    api_client, fila, paciente_a, org_a, django_capture_on_commit_callbacks,
):
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    primera = waitlist.run_due()
    segunda = waitlist.run_due()
    assert primera == {"liberadas": 0, "ofrecidas": 0}
    assert segunda == {"liberadas": 0, "ofrecidas": 0}
    with tenant_context(org_a.id):
        assert Appointment.objects.filter(
            status=Appointment.Status.PENDING_PAYMENT).count() == 1


def test_el_comando_corre_una_vuelta_y_se_apaga_con_la_variable(
    fila, org_a, capsys,
):
    call_command("process_waitlist")
    assert "Lista de espera:" in capsys.readouterr().out

    with override_settings(WAITLIST_PROCESS="off"):
        call_command("process_waitlist")
    assert "apagada" in capsys.readouterr().out


def test_una_entrada_cuyo_rango_ya_paso_vence(paciente_a, practitioner_a, org_a):
    espera = anotar(org_a, paciente_a, practitioner_a, desde=0, hasta=2)
    with tenant_context(org_a.id):
        waitlist.refresh_entries(today=dt.date.today() + dt.timedelta(days=3))
    assert entrada(org_a, espera).status == "expired"


def test_si_el_paciente_reserva_por_su_cuenta_la_entrada_se_cierra(
    paciente_a, practitioner_a, branches_a, agenda_a, org_a,
):
    with tenant_context(org_a.id):
        espera = WaitlistEntry.objects.create(
            organization=org_a, patient=paciente_a.patient_profile,
            requested_by=paciente_a, practitioner=practitioner_a,
            date_from=dt.date.today(),
            date_to=dt.date.today() + dt.timedelta(days=14),
        )
    ficha = reservar(org_a, paciente_a, practitioner_a, branches_a, agenda_a,
                     turno())
    pagar(org_a, ficha, paciente_a)

    with tenant_context(org_a.id):
        waitlist.refresh_entries(organization=org_a)

    assert entrada(org_a, espera).status == "booked"


# ---------- El resumen de la administración --------------------------------
RESUMEN = "appointments:waitlist-summary"


def test_el_resumen_cuenta_anotados_tomaron_y_la_tasa_de_recuperacion(
    api_client, fila, admin_a, paciente_a, otro_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    pagar(org_a, ofrecida_a(org_a, otro_paciente_a), otro_paciente_a)
    with tenant_context(org_a.id):
        waitlist.refresh_entries()

    cuerpo = autenticar(api_client, admin_a).get(reverse(RESUMEN)).json()

    assert cuerpo["waitlist"]["enrolled"] == 2
    assert cuerpo["waitlist"]["booked"] == 1
    assert cuerpo["waitlist"]["waiting"] == 1
    assert cuerpo["recovery"] == {"cancelled": 1, "recovered": 1, "rate": 1.0}
    [medico] = cuerpo["waitlist"]["by_practitioner"]
    assert medico["name"] == "Laura Gómez" and medico["enrolled"] == 2


def test_una_cancelacion_que_nadie_ocupo_baja_la_tasa(
    api_client, admin_a, paciente_a, practitioner_a, branches_a, agenda_unica,
    org_a, django_capture_on_commit_callbacks,
):
    ficha = ocupar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica)
    cancelar(api_client, paciente_a, ficha, django_capture_on_commit_callbacks)

    cuerpo = autenticar(api_client, admin_a).get(reverse(RESUMEN)).json()

    assert cuerpo["recovery"] == {"cancelled": 1, "recovered": 0, "rate": 0.0}


def test_sin_cancelaciones_la_tasa_no_se_inventa(api_client, admin_a):
    cuerpo = autenticar(api_client, admin_a).get(reverse(RESUMEN)).json()
    assert cuerpo["recovery"] == {"cancelled": 0, "recovered": 0, "rate": None}
    assert cuerpo["waitlist"]["enrolled"] == 0


def test_el_resumen_es_solo_de_administracion_y_de_su_organizacion(
    api_client, fila, paciente_a, admin_a, user_b, org_a, org_b, plans,
):
    assert autenticar(api_client, paciente_a).get(reverse(RESUMEN)).status_code == 403

    con_plan(org_b, plans, "pro")
    dar_rol(user_b, org_b, "admin-kpi", "Administración", ["reporting.kpi.read"])
    ajeno = autenticar(api_client, user_b).get(reverse(RESUMEN)).json()
    assert ajeno["waitlist"]["enrolled"] == 0
    assert ajeno["recovery"]["cancelled"] == 0


def test_el_resumen_en_el_basico_dice_plan_limit(
    api_client, admin_a, org_a, plans,
):
    con_plan(org_a, plans, "basic")
    respuesta = autenticar(api_client, admin_a).get(reverse(RESUMEN))
    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "plan_limit"


@pytest.mark.parametrize("consulta, codigo", [
    ("?from=ayer", "invalid_date"),
    ("?from=2026-11-10&to=2026-11-01", "invalid_range"),
    ("?from=2020-01-01&to=2026-11-01", "range_too_long"),
])
def test_el_resumen_valida_las_fechas(api_client, admin_a, consulta, codigo):
    respuesta = autenticar(api_client, admin_a).get(reverse(RESUMEN) + consulta)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == codigo

# ---------- La copia de seguridad ------------------------------------------
def test_una_copia_con_la_lista_de_espera_se_restaura_sin_romperse(
    api_client, fila, paciente_a, otro_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    """La entrada apunta a la ficha con `PROTECT`: si no viajara en la copia,
    purgar las fichas al restaurar fallaría con una entrada colgando."""
    from backups import services

    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada = ofrecida_a(org_a, otro_paciente_a)
    documento = services.create(org_a)
    assert documento["counts"]["appointments.WaitlistEntry"] == 2

    services.restore(documento, org_a)

    b = entrada(org_a, fila["b"])
    assert b.status == "offered" and b.offered_appointment_id == guardada.id
    assert entrada(org_a, fila["c"]).status == "waiting"


# ---------- Lo que dejó la revisión del código -----------------------------
def vencer(org, ficha, *, hace_minutos=1):
    with tenant_context(org.id):
        Appointment.objects.filter(pk=ficha.pk).update(
            expires_at=timezone.now() - dt.timedelta(minutes=hace_minutos))


def test_la_oferta_vencida_sigue_bloqueando_unos_minutos_para_no_saltarse_la_fila(
    api_client, fila, paciente_a, otro_paciente_a, tercer_paciente_a,
    practitioner_a, branches_a, agenda_unica, org_a,
    django_capture_on_commit_callbacks,
):
    """Si el turno de B vence y lo soltáramos en el acto, cualquiera que
    reservara antes de la próxima vuelta se lo llevaría antes que C."""
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada = ofrecida_a(org_a, otro_paciente_a)
    vencer(org_a, guardada)

    assert 9 not in libres(org_a, practitioner_a)         # la búsqueda no lo ve
    with pytest.raises(booking.SlotAlreadyTaken):          # ni se puede reservar
        reservar(org_a, paciente_a, practitioner_a, branches_a, agenda_unica,
                 turno())

    # El proceso sí lo libera, y se lo da a C, el siguiente.
    waitlist.run_organization(org_a)
    assert ofrecida_a(org_a, tercer_paciente_a) is not None


def test_pasado_el_margen_el_turno_se_libera_aunque_el_proceso_no_corra(
    api_client, fila, paciente_a, otro_paciente_a, practitioner_a, org_a,
    django_capture_on_commit_callbacks,
):
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    vencer(org_a, ofrecida_a(org_a, otro_paciente_a), hace_minutos=10)

    assert 9 in libres(org_a, practitioner_a)


def test_una_oferta_que_fallo_se_reintenta_en_la_vuelta_siguiente(
    api_client, fila, paciente_a, otro_paciente_a, org_a, monkeypatch,
    django_capture_on_commit_callbacks,
):
    original = waitlist.offer_slot
    monkeypatch.setattr(waitlist, "offer_slot",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("caída")))
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    assert ofrecida_a(org_a, otro_paciente_a) is None      # la oferta falló

    monkeypatch.setattr(waitlist, "offer_slot", original)
    resultado = waitlist.run_organization(org_a)

    assert resultado["ofrecidas"] == 1
    assert ofrecida_a(org_a, otro_paciente_a) is not None


def test_el_reintento_no_le_ofrece_el_turno_a_quien_lo_solto(
    api_client, fila, paciente_a, practitioner_a, org_a, otro_paciente_a,
    tercer_paciente_a, monkeypatch, django_capture_on_commit_callbacks,
):
    with tenant_context(org_a.id):
        waitlist.leave(entrada(org_a, fila["b"]))
        waitlist.leave(entrada(org_a, fila["c"]))
    anotar(org_a, paciente_a, practitioner_a)   # A, que va a cancelar, también espera
    monkeypatch.setattr(waitlist, "offer_slot",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("caída")))
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    monkeypatch.undo()

    assert waitlist.run_organization(org_a)["ofrecidas"] == 0
    assert ofrecida_a(org_a, paciente_a) is None


def test_salir_de_la_lista_con_un_turno_guardado_lo_suelta_y_lo_ofrece(
    api_client, fila, paciente_a, otro_paciente_a, tercer_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada_b = ofrecida_a(org_a, otro_paciente_a)

    with django_capture_on_commit_callbacks(execute=True):
        respuesta = autenticar(api_client, otro_paciente_a).delete(
            reverse("appointments:waitlist-entry", args=[fila["b"].id]))

    assert respuesta.status_code == 204
    assert entrada(org_a, fila["b"]).status == "cancelled"
    assert recargar(org_a, guardada_b).status == Appointment.Status.EXPIRED
    assert ofrecida_a(org_a, tercer_paciente_a) is not None


def test_salir_de_la_lista_con_el_turno_ya_pagado_no_lo_cancela(
    api_client, fila, paciente_a, otro_paciente_a, org_a,
    django_capture_on_commit_callbacks,
):
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    guardada = ofrecida_a(org_a, otro_paciente_a)
    pagar(org_a, guardada, otro_paciente_a)

    autenticar(api_client, otro_paciente_a).delete(
        reverse("appointments:waitlist-entry", args=[fila["b"].id]))

    assert recargar(org_a, guardada).status == Appointment.Status.CONFIRMED
    assert entrada(org_a, fila["b"]).status == "booked"


def test_una_reserva_sin_pagar_no_cierra_la_entrada_como_tomada(
    paciente_a, practitioner_a, branches_a, agenda_a, org_a,
):
    with tenant_context(org_a.id):
        espera = WaitlistEntry.objects.create(
            organization=org_a, patient=paciente_a.patient_profile,
            requested_by=paciente_a, practitioner=practitioner_a,
            date_from=dt.date.today(),
            date_to=dt.date.today() + dt.timedelta(days=14),
        )
    reservar(org_a, paciente_a, practitioner_a, branches_a, agenda_a, turno())

    with tenant_context(org_a.id):
        waitlist.refresh_entries(organization=org_a)

    assert entrada(org_a, espera).status == "waiting"

def test_quien_cancelo_no_recibe_el_turno_cuando_vence_la_oferta_de_otro(
    api_client, fila, paciente_a, otro_paciente_a, practitioner_a, org_a,
    django_capture_on_commit_callbacks,
):
    """El turno tiene dos fichas sueltas encima: la que A canceló y la oferta
    vencida de B. A no tiene que volver a recibirlo, aunque esté en la fila."""
    with tenant_context(org_a.id):
        waitlist.leave(entrada(org_a, fila["c"]))
    anotar(org_a, paciente_a, practitioner_a)
    cancelar(api_client, paciente_a, fila["ficha"],
             django_capture_on_commit_callbacks)
    vencer(org_a, ofrecida_a(org_a, otro_paciente_a))

    assert waitlist.run_organization(org_a)["ofrecidas"] == 0
    assert ofrecida_a(org_a, paciente_a) is None
