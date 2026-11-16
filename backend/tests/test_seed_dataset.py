"""El dataset de demostración (`seed_dataset`).

Lo que se verifica no es cuántas filas exactas salen —eso depende de la
fecha—, sino que lo sembrado respete las mismas reglas que la aplicación:
que cada organización nazca por el alta de US-43, que todo quede dentro de su
inquilino, que las fichas pasadas tengan desenlace y que las atendidas tengan
su atención firmada. Desde US-35 también que la ausencia salga de causas
(anticipación, pago por adelantado, faltas previas) y que `--history` agregue
fichas viejas sin tocar las que ya estaban.
"""

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from accounts.models import Role, User, UserRole
from appointments.models import Appointment
from catalog.models import Practitioner, Service, Specialty
from encounters.models import Encounter
from patients.models import Patient
from payments.models import Payment
from scheduling.models import Schedule
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization
from assistant.medical_reference import reference_texts
from tenancy.management.commands._causas_inasistencia import (
    HISTORIAL_DESDE_DIAS, HISTORIAL_HASTA_DIAS, probabilidad_ausencia,
)

pytestmark = pytest.mark.django_db

LA_PAZ = ZoneInfo("America/La_Paz")

CLAVE = "clave-de-prueba-del-dataset"


@pytest.fixture
def sembrado(platform_admin, plans):
    call_command("seed_dataset", "--only", "losandes", "--password", CLAVE)
    with platform_admin_context():
        return Organization.objects.get(slug="losandes")


def test_sin_clave_no_siembra(platform_admin, plans, monkeypatch):
    monkeypatch.delenv("DATASET_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--only", "losandes")


def test_la_organizacion_nace_por_el_alta_de_us43(sembrado):
    with tenant_context(sembrado.id):
        roles = set(Role.objects.filter(organization=sembrado).values_list("code", flat=True))
        admin = User.objects.get(email="admin@losandes.test")
        assert UserRole.objects.filter(user=admin, role__code="org_admin").exists()
    assert {"org_admin", "practitioner", "receptionist", "patient"} <= roles


def test_las_cuentas_entran_con_la_clave_comun(sembrado):
    with tenant_context(sembrado.id):
        medico = User.objects.get(email="medico1@losandes.test")
    assert medico.check_password(CLAVE)


def test_solo_especialidades_con_referencia_medica(sembrado):
    with tenant_context(sembrado.id):
        nombres = list(Specialty.objects.values_list("name", flat=True))
    assert nombres
    assert all(reference_texts(n) for n in nombres)


def test_cada_profesional_tiene_cuenta_rol_y_agenda(sembrado):
    with tenant_context(sembrado.id):
        for prof in Practitioner.objects.all():
            assert prof.user_id is not None
            assert prof.schedules.exists()
            assert UserRole.objects.filter(user_id=prof.user_id, role__code="practitioner").exists()


def test_lo_pasado_tiene_desenlace_y_lo_atendido_su_atencion_firmada(sembrado):
    from django.utils import timezone
    with tenant_context(sembrado.id):
        pasadas = Appointment.objects.filter(starts_at__lt=timezone.now())
        assert not pasadas.filter(status__in=["pending_payment", "confirmed"]).exists()
        atendidas = pasadas.filter(status="attended")
        assert atendidas.exists()
        assert Encounter.objects.filter(status="signed").count() == atendidas.count()
        assert not Encounter.objects.filter(status="draft").exists()
        # Hay ausencias: el modelo de inasistencia del Sprint 4 las necesita.
        assert pasadas.filter(status="no_show").exists()


def test_hay_pacientes_con_cuenta_y_dependientes(sembrado):
    with tenant_context(sembrado.id):
        assert Patient.objects.filter(user__isnull=False).count() == 60
        assert Patient.objects.filter(guardian__isnull=False).exists()


def test_hay_servicios_con_precio_para_el_asistente(sembrado):
    with tenant_context(sembrado.id):
        assert Service.objects.filter(price__isnull=False).exists()


def test_lo_sembrado_no_se_ve_desde_otra_organizacion(sembrado, org_b):
    with tenant_context(org_b.id):
        assert not Appointment.objects.exists()
        assert not Encounter.objects.exists()
        assert not Patient.objects.filter(organization=sembrado).exists()


def test_correrlo_dos_veces_no_duplica(sembrado):
    with tenant_context(sembrado.id):
        antes = Appointment.objects.count()
    call_command("seed_dataset", "--only", "losandes", "--password", CLAVE)
    with tenant_context(sembrado.id):
        assert Appointment.objects.count() == antes


# --------------------------------------------------------------------------
#  --enrich: nutrir una organización que ya existe
# --------------------------------------------------------------------------

@pytest.fixture
def como_en_produccion(platform_admin, plans):
    """Igual que kolping3k y morita2: alta normal, el catálogo de
    `seed_catalog` con agendas, profesionales sin cuenta y un paciente que
    ya estaba (una cuenta de prueba de alguien del equipo)."""
    from tenancy.services import create_organization

    org, admin, _ = create_organization(
        organization_data={"slug": "morita2", "name": "Morita", "legal_name": "Morita",
                           "tax_id": "123456", "contact_email": "contacto@morita.test"},
        admin_data={"email": "admin@morita.test", "first_name": "Ad", "last_name": "Min",
                    "document_number": "1"},
        plan=plans["pro"], created_by=platform_admin,
    )
    call_command("seed_catalog", "--organization", "morita2", "--with-schedules")
    with tenant_context(org.id):
        previo = Patient.objects.create(
            organization=org, document_type=Patient.DocumentType.CI,
            document_number="555", first_name="Prueba", last_name="Del Equipo",
        )
        especialidades = set(Specialty.objects.values_list("name", flat=True))
    return org, previo, especialidades


def test_enrich_agrega_lo_que_falta(como_en_produccion):
    org, _previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert not Practitioner.objects.filter(user__isnull=True).exists()
        assert Service.objects.filter(price__isnull=False).exists()
        assert UserRole.objects.filter(role__code="receptionist").exists()
        assert Patient.objects.count() >= 100
        atendidas = Appointment.objects.filter(status="attended").count()
        assert atendidas > 0
        assert Encounter.objects.filter(status="signed").count() == atendidas


def test_enrich_no_crea_especialidades(como_en_produccion):
    org, _previo, antes = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert set(Specialty.objects.values_list("name", flat=True)) == antes


def test_enrich_no_toca_a_los_pacientes_que_ya_estaban(como_en_produccion):
    org, previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert not Appointment.objects.filter(patient=previo).exists()
        previo_ahora = Patient.objects.get(pk=previo.pk)
    assert (previo_ahora.first_name, previo_ahora.document_number) == ("Prueba", "555")


def test_enrich_respeta_la_vigencia_de_las_agendas(como_en_produccion):
    """Las agendas de `seed_catalog` empiezan hoy: no puede haber fichas
    antes de que la agenda existiera."""
    org, _previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        for ficha in Appointment.objects.select_related("schedule"):
            assert ficha.starts_at.astimezone(ZoneInfo("America/La_Paz")).date() >= ficha.schedule.valid_from


def test_enrich_dos_veces_no_duplica(como_en_produccion):
    org, _previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        conteo = (Appointment.objects.count(), Patient.objects.count(),
                  Service.objects.count(), Practitioner.objects.count())
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert (Appointment.objects.count(), Patient.objects.count(),
                Service.objects.count(), Practitioner.objects.count()) == conteo


def test_enrich_de_una_organizacion_inexistente_falla(platform_admin, plans):
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--enrich", "noexiste", "--password", CLAVE)


# --------------------------------------------------------------------------
#  US-35: la inasistencia tiene causas
# --------------------------------------------------------------------------

def _prob(**cambios):
    """`probabilidad_ausencia` con un caso base (martes a la mañana, sin nada)."""
    base = dict(anticipacion_dias=5, pago_adelantado=False, faltas_previas=0,
                dia_semana=1, hora=9)
    base.update(cambios)
    return probabilidad_ausencia(**base)


def test_la_probabilidad_siempre_esta_entre_cero_y_uno():
    for dias in (0, 1, 14, 45, 400):
        for pago in (False, True):
            for faltas in (0, 1, 3, 10):
                for dia in range(7):
                    for hora in (8, 13, 14, 18):
                        p = probabilidad_ausencia(dias, pago, faltas, dia, hora)
                        assert 0 < p < 1


def test_la_base_ronda_el_siete_por_ciento():
    # Reserva para el mismo día, sin adelanto, sin faltas, martes a la mañana.
    assert 0.06 < _prob(anticipacion_dias=0) < 0.08


def test_mas_anticipacion_sube_la_probabilidad():
    assert _prob(anticipacion_dias=1) < _prob(anticipacion_dias=10) < _prob(anticipacion_dias=40)


def test_la_anticipacion_tiene_tope_a_los_45_dias():
    assert _prob(anticipacion_dias=45) == _prob(anticipacion_dias=200)


def test_el_pago_adelantado_baja_la_probabilidad():
    assert _prob(pago_adelantado=True) < _prob(pago_adelantado=False)


def test_mas_faltas_previas_suben_la_probabilidad():
    assert _prob(faltas_previas=0) < _prob(faltas_previas=1) < _prob(faltas_previas=2) \
        < _prob(faltas_previas=3)


def test_las_faltas_previas_tienen_tope_en_tres():
    assert _prob(faltas_previas=3) == _prob(faltas_previas=9)


def test_lunes_sabado_y_tarde_suben_la_probabilidad():
    martes = _prob(dia_semana=1)
    assert _prob(dia_semana=0) > martes          # lunes
    assert _prob(dia_semana=5) > martes          # sábado
    assert _prob(hora=14) > _prob(hora=13)       # tarde
    assert _prob(dia_semana=5) > _prob(dia_semana=0)   # el sábado pesa 0,40 y el lunes 0,35


def test_la_ventana_del_historial_no_pisa_a_las_fichas_recientes():
    assert HISTORIAL_DESDE_DIAS > HISTORIAL_HASTA_DIAS > 60


def _filas_pasadas():
    """`(estado, starts_at, created_at, proveedor del pago)` de atendidas y ausentes."""
    return list(
        Appointment.objects.filter(status__in=["attended", "no_show"],
                                   starts_at__lt=timezone.now())
        .values_list("status", "starts_at", "created_at", "payments__provider")
    )


def _tasa(filas):
    return sum(1 for f in filas if f[0] == "no_show") / len(filas)


def test_la_ausencia_ya_no_es_azar_parejo(sembrado):
    """Quien pagó en efectivo y reservó con mucha anticipación falta bastante
    más que quien pagó por adelantado: es lo que el modelo tiene que aprender."""
    with tenant_context(sembrado.id):
        filas = _filas_pasadas()
    adelantado = [f for f in filas if f[3] == "simulated"]
    efectivo_lejos = [f for f in filas
                      if f[3] == "cash" and (f[1] - f[2]) >= timedelta(days=10)]
    assert adelantado and efectivo_lejos
    assert _tasa(efectivo_lejos) > _tasa(adelantado) + 0.05


def test_quien_ya_falto_vuelve_a_faltar_mas(sembrado):
    with tenant_context(sembrado.id):
        pasadas = (Appointment.objects
                   .filter(status__in=["attended", "no_show"], starts_at__lt=timezone.now())
                   .order_by("starts_at").values_list("patient_id", "status"))
        faltas, con, sin = {}, [0, 0], [0, 0]
        for paciente, estado in pasadas:
            grupo = con if faltas.get(paciente) else sin
            grupo[0] += 1
            if estado == "no_show":
                grupo[1] += 1
                faltas[paciente] = faltas.get(paciente, 0) + 1
    assert con[0] and sin[0]
    assert con[1] / con[0] > sin[1] / sin[0]


def test_la_reserva_es_anterior_al_turno_y_la_anticipacion_varia(sembrado):
    """`created_at` no puede ser la fecha del alta (`auto_now_add`): se corrige."""
    with tenant_context(sembrado.id):
        filas = list(Appointment.objects.values_list("starts_at", "created_at"))
    ahora = timezone.now()
    assert filas
    assert all(creada < inicio and creada <= ahora for inicio, creada in filas)
    assert len({(inicio - creada).days for inicio, creada in filas}) > 10


def test_los_pagos_siguen_las_reglas_del_adelanto(sembrado):
    ahora = timezone.now()
    with tenant_context(sembrado.id):
        pagos = list(Payment.objects.select_related("appointment"))
        sin_pago = Payment.objects.filter(
            appointment__status__in=["cancelled", "pending_payment"]).exists()
    assert not sin_pago
    assert {p.provider for p in pagos} == {"simulated", "cash"}
    for pago in pagos:
        ficha = pago.appointment
        assert ficha.created_at <= pago.paid_at <= ahora
        if pago.provider == "simulated":
            # Adelantado: al reservar, con 24 h o más de margen.
            assert pago.paid_at <= ficha.starts_at - timedelta(days=1)
        else:
            assert pago.paid_at <= ficha.starts_at


# --------------------------------------------------------------------------
#  --history: más fichas pasadas para una organización que ya tiene datos
# --------------------------------------------------------------------------

def _corte_de_60_dias():
    """El mismo corte que usa el comando: la medianoche de hace 60 días."""
    hoy = timezone.now().astimezone(LA_PAZ).date()
    return datetime.combine(hoy - timedelta(days=60), time.min, tzinfo=LA_PAZ)


@pytest.fixture
def con_enrich(como_en_produccion, monkeypatch):
    """Una organización con sólo 60 días de fichas: como las que se nutrieron
    antes de US-35, que es el caso para el que existe `--history`. Hoy una
    organización nueva se siembra con `DIAS_DE_HISTORIA` días en una sola
    pasada y `--history` no tiene nada que agregarle."""
    from tenancy.management.commands import seed_dataset

    monkeypatch.setattr(seed_dataset, "DIAS_DE_HISTORIA", 60)
    org, previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    return org, previo


def test_una_organizacion_nueva_se_siembra_en_una_sola_pasada(sembrado):
    """Las fichas pasadas llegan hasta `DIAS_DE_HISTORIA` días atrás, de modo que
    las faltas previas de cada paciente se cuentan desde el principio. Por eso
    `--history` no tiene nada que agregarle."""
    from tenancy.management.commands.seed_dataset import DIAS_DE_HISTORIA

    with tenant_context(sembrado.id):
        primera = Appointment.objects.order_by("starts_at").first()
        assert primera.starts_at < _corte_de_60_dias()
        assert primera.starts_at >= timezone.now() - timedelta(days=DIAS_DE_HISTORIA + 1)
    call_command("seed_dataset", "--history", "losandes")
    with tenant_context(sembrado.id):
        assert not Appointment.objects.filter(
            starts_at__lt=timezone.now() - timedelta(days=DIAS_DE_HISTORIA + 1)).exists()


def test_history_agrega_fichas_mas_viejas_de_60_dias(con_enrich):
    org, _previo = con_enrich
    corte = _corte_de_60_dias()
    with tenant_context(org.id):
        assert not Appointment.objects.filter(starts_at__lt=corte).exists()
    call_command("seed_dataset", "--history", "morita2")
    with tenant_context(org.id):
        viejas = Appointment.objects.filter(starts_at__lt=corte)
        assert viejas.exists()
        assert viejas.filter(starts_at__gte=corte - timedelta(days=150)).count() == viejas.count()
        # Sólo desenlaces pasados, y cada atendida con su atención firmada.
        assert set(viejas.values_list("status", flat=True)) <= {"attended", "no_show", "cancelled"}
        atendidas = viejas.filter(status="attended")
        assert Encounter.objects.filter(appointment__in=atendidas, status="signed").count() \
            == atendidas.count()


def test_history_sin_clave_y_con_pacientes_existentes(con_enrich, monkeypatch):
    monkeypatch.delenv("DATASET_PASSWORD", raising=False)
    org, _previo = con_enrich
    with tenant_context(org.id):
        pacientes = set(Patient.objects.values_list("pk", flat=True))
        usuarios = User.objects.count()
    call_command("seed_dataset", "--history", "morita2")
    with tenant_context(org.id):
        usados = set(Appointment.objects.filter(starts_at__lt=_corte_de_60_dias())
                     .values_list("patient_id", flat=True))
        assert usados <= pacientes
        assert Patient.objects.count() == len(pacientes)   # no crea pacientes
        assert User.objects.count() == usuarios            # ni cuentas


def test_history_es_idempotente(con_enrich):
    org, _previo = con_enrich
    call_command("seed_dataset", "--history", "morita2")
    with tenant_context(org.id):
        antes = (Appointment.objects.count(), Payment.objects.count(),
                 Encounter.objects.count())
    call_command("seed_dataset", "--history", "morita2")
    with tenant_context(org.id):
        assert (Appointment.objects.count(), Payment.objects.count(),
                Encounter.objects.count()) == antes


def test_history_no_toca_las_fichas_que_ya_estaban(con_enrich):
    org, _previo = con_enrich

    def foto():
        return {a.pk: (a.status, a.starts_at, a.created_at, a.updated_at, a.patient_id)
                for a in Appointment.objects.all()}

    with tenant_context(org.id):
        antes = foto()
        agendas = list(Schedule.objects.values_list("pk", "valid_from", "weekday"))
    call_command("seed_dataset", "--history", "morita2")
    with tenant_context(org.id):
        despues = foto()
        assert all(despues[pk] == datos for pk, datos in antes.items())
        assert len(despues) > len(antes)
        # Las agendas quedan como estaban: el historial no las modifica.
        assert list(Schedule.objects.values_list("pk", "valid_from", "weekday")) == agendas


def test_history_no_hace_nada_si_ya_hay_fichas_viejas(sembrado):
    """`losandes` ya se sembró con fichas de hace más de 60 días (una sola
    pasada): `--history` no agrega nada, ni la primera ni la segunda vez."""
    with tenant_context(sembrado.id):
        antes = Appointment.objects.count()
        assert Appointment.objects.filter(starts_at__lt=_corte_de_60_dias()).exists()
    call_command("seed_dataset", "--history", "losandes")
    with tenant_context(sembrado.id):
        assert Appointment.objects.count() == antes
    call_command("seed_dataset", "--history", "losandes")
    with tenant_context(sembrado.id):
        assert Appointment.objects.count() == antes


def test_history_es_excluyente_con_only_y_enrich(platform_admin, plans):
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--history", "losandes", "--only", "losandes")
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--history", "losandes", "--enrich", "losandes",
                     "--password", CLAVE)


def test_history_de_una_organizacion_inexistente_falla(platform_admin, plans):
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--history", "noexiste")
