"""US-35 — Riesgo de inasistencia: variables, modelo, puntuación y API.

Qué se prueba (regla 17 del Sprint 4: los bordes, no sólo el camino feliz):

- **Variables y etiqueta**: la anticipación, el pago adelantado y las faltas
  previas se calculan sin contar la propia ficha; la etiqueta es la misma
  inasistencia de US-29.
- **Entrenamiento**: sin datos suficientes no hay versión; con una señal fuerte
  el modelo le gana a la línea base; un modelo que no le gana nunca es el
  vigente; **cada organización entrena sólo con sus fichas** (regla 16).
- **Puntuación**: sólo fichas futuras activas, sin duplicar filas, y sin modelo
  vigente no se inventa nada.
- **API**: sólo la Administración, sólo con el plan que lo incluye, sólo de su
  organización, y **el paciente nunca ve su propio riesgo**.

Las pruebas de entrenamiento usan datos sintéticos con las mismas causas que
`seed_dataset` (`_causas_inasistencia.probabilidad_ausencia`), con semilla fija.
"""

import datetime as dt
import random
from collections import defaultdict
from decimal import Decimal
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment
from catalog.models import Practitioner, PractitionerBranch
from noshow import features, scoring, training
from noshow.models import ModelVersion, NoShowPrediction
from patients.models import Patient
from payments.models import Payment
from scheduling.models import Schedule
from tenancy.context import platform_admin_context, tenant_context
from tenancy.management.commands._causas_inasistencia import probabilidad_ausencia
from tenancy.models import Subscription

from .conftest import dar_rol
from .fichas_comunes import (  # noqa: F401  (fixtures)
    agenda_a,
    api_client,
    autenticar,
    paciente_a,
    perfil_paciente,
)

pytestmark = pytest.mark.django_db

LA_PAZ = ZoneInfo("America/La_Paz")


# --------------------------------------------------------------------------
#  Ayudantes y fixtures
# --------------------------------------------------------------------------

def _paciente(org, numero):
    with tenant_context(org.id):
        return Patient.objects.create(
            organization=org, document_type=Patient.DocumentType.CI,
            document_number=f"NS-{org.slug[:3]}-{numero}",
            first_name=f"Paciente{numero}", last_name="Prueba",
            birth_date=dt.date(1990, 1, 1),
        )


def _ficha(org, usuario, paciente, profesional, sucursal, agenda, inicio, estado, *,
           anticipacion=5.0, pago=None, checked_in=None):
    """Una ficha con su `created_at` y, si se pide, su pago `(proveedor, paid_at)`."""
    with tenant_context(org.id):
        ficha = Appointment.objects.create(
            organization=org, patient=paciente, booked_by=usuario,
            practitioner=profesional, branch=sucursal, schedule=agenda,
            starts_at=inicio, ends_at=inicio + dt.timedelta(hours=1),
            status=estado, checked_in_at=checked_in,
        )
        # `created_at` es `auto_now_add`: se corrige con `update`, que no lo pisa.
        Appointment.objects.filter(pk=ficha.pk).update(
            created_at=inicio - dt.timedelta(days=anticipacion))
        if pago:
            Payment.objects.create(
                organization=org, appointment=ficha, created_by=usuario,
                amount=Decimal("100"), currency="BOB", provider=pago[0],
                status="succeeded", paid_at=pago[1],
            )
        ficha.refresh_from_db()
    return ficha


def _poblar(org, usuario, profesional, sucursal, agenda, *, n, con_senal, semilla=1,
            pacientes=40):
    """`n` fichas pasadas con desenlace, repartidas en 120 días.

    Con señal, la ausencia sale de las mismas causas que el dataset de
    demostración; sin ella, es una moneda con la misma tasa para todas.
    """
    rnd = random.Random(semilla)
    pool = [_paciente(org, f"{semilla}-{i}") for i in range(pacientes)]
    hoy = timezone.now().astimezone(LA_PAZ).date()
    faltas = defaultdict(int)
    fichas, pagos, creadas = [], [], []
    with tenant_context(org.id):
        for i in range(n):
            dia = hoy - dt.timedelta(days=2 + int(118 * (n - i) / n))
            inicio = dt.datetime.combine(dia, dt.time(rnd.randint(8, 17), 0), tzinfo=LA_PAZ)
            paciente = rnd.choice(pool)
            anticipacion = rnd.choice([1, 2, 3, 5, 7, 10, 14, 21, 30, 40])
            adelantado = rnd.random() < 0.65 and anticipacion >= 2
            if con_senal:
                p = probabilidad_ausencia(anticipacion, adelantado, faltas[paciente.id],
                                          inicio.weekday(), inicio.hour)
            else:
                p = 0.15
            ausente = rnd.random() < p
            if ausente:
                faltas[paciente.id] += 1
            creada = inicio - dt.timedelta(days=anticipacion)
            ficha = Appointment(
                organization=org, patient=paciente, booked_by=usuario,
                practitioner=profesional, branch=sucursal, schedule=agenda,
                starts_at=inicio, ends_at=inicio + dt.timedelta(hours=1),
                status="no_show" if ausente else "attended",
            )
            fichas.append(ficha)
            creadas.append(creada)
            pagos.append(Payment(
                organization=org, appointment=ficha, created_by=usuario,
                amount=Decimal("100"), currency="BOB", status="succeeded",
                provider="simulated" if adelantado else "cash",
                paid_at=(creada + dt.timedelta(minutes=10)) if adelantado
                else inicio - dt.timedelta(minutes=15),
            ))
        Appointment.objects.bulk_create(fichas, batch_size=500)
        Payment.objects.bulk_create(pagos, batch_size=500)
        for ficha, creada in zip(fichas, creadas):
            ficha.created_at = creada
        Appointment.objects.bulk_update(fichas, ["created_at"], batch_size=500)


@pytest.fixture
def admin_a(db, org_a):
    """La Administración de A, con el permiso del riesgo de inasistencia."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="admin-riesgo@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Admin", last_name="Riesgo",
            document_number="ADM-35A",
        )
    dar_rol(user, org_a, "admin-riesgo", "Administración", ["appointments.noshow.read"])
    return user


@pytest.fixture
def recepcion_a(db, org_a):
    """Recepción: puede ver fichas, pero no el riesgo de inasistencia."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="recepcion-riesgo@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Rosa", last_name="Recepción",
            document_number="REC-35A",
        )
    dar_rol(user, org_a, "recepcion-riesgo", "Recepción", ["appointments.appointment.read"])
    return user


@pytest.fixture
def mundo_b(db, org_b, branch_b):
    """Lo mínimo de B para tener fichas: profesional y agenda."""
    with tenant_context(org_b.id):
        profesional = Practitioner.objects.create(
            organization=org_b, first_name="Raúl", last_name="Peña",
            license_number="MP-2000",
        )
        PractitionerBranch.objects.create(
            organization=org_b, practitioner=profesional, branch=branch_b,
        )
        agenda = Schedule.objects.create(
            organization=org_b, practitioner=profesional, branch=branch_b,
            weekday=0, start_time="09:00", end_time="11:00", slot_minutes=60,
            valid_from=dt.date.today() - dt.timedelta(days=7),
        )
    return profesional, agenda


@pytest.fixture
def org_b_premium(org_b, plans):
    """B con el plan que incluye la predicción (por omisión es Básico)."""
    with platform_admin_context():
        Subscription.objects.filter(organization=org_b).update(plan=plans["premium"])
    return org_b


@pytest.fixture
def admin_b(db, org_b):
    with tenant_context(org_b.id):
        user = User.objects.create_user(
            email="admin-riesgo@sanluis.test", password="clave-de-prueba-1",
            organization=org_b, first_name="Admin", last_name="B",
            document_number="ADM-35B",
        )
    dar_rol(user, org_b, "admin-riesgo", "Administración", ["appointments.noshow.read"])
    return user


def _crear_modelo(org, *, estado="active", beats=True, version=1):
    """Una versión con coeficientes escritos a mano. Supone el contexto abierto.

    Sólo pesa la anticipación. Con intercepto -2 y 0,05 por día: 2 días → 13 %
    (bajo), 20 días → 27 % (medio), 40 días → 50 % (alto), con los cortes 0,2
    y 0,4.
    """
    names = features.FEATURE_NAMES
    coef = [0.0] * len(names)
    coef[names.index("lead_days")] = 0.05
    return ModelVersion.objects.create(
        organization=org, kind="noshow", version=version, status=estado,
        n_train=400, n_test=100, base_rate=0.1,
        params={"features": names, "coef": coef, "intercept": -2.0,
                "mean": [0.0] * len(names), "scale": [1.0] * len(names)},
        metrics={"auc": 0.8, "brier": 0.08, "brier_baseline": 0.1,
                 "accuracy_baseline": 0.9, "recall_high": 0.4,
                 "precision_high": 0.5,
                 "cutoffs": {"medium": 0.2, "high": 0.4}},
        beats_baseline=beats,
    )


def _modelo_a_mano(org, **datos):
    with tenant_context(org.id):
        return _crear_modelo(org, **datos)


def _futuras(org, usuario, paciente, profesional, sucursal, agenda, anticipaciones,
             estado="confirmed"):
    """Una ficha futura por cada anticipación, en días distintos."""
    ahora = timezone.now()
    return [
        _ficha(org, usuario, paciente, profesional, sucursal, agenda,
               (ahora + dt.timedelta(days=3 + i)).replace(minute=0, second=0, microsecond=0),
               estado, anticipacion=dias)
        for i, dias in enumerate(anticipaciones)
    ]


def _valores(fila):
    return dict(zip(features.FEATURE_NAMES, fila.values))


# --------------------------------------------------------------------------
#  Variables y etiqueta
# --------------------------------------------------------------------------

def test_las_variables_no_cuentan_la_propia_ficha_ni_las_posteriores(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    paciente = _paciente(org_a, "vars")
    suc = branches_a["centro"]
    ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
    atendida = _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a,
                      ahora - dt.timedelta(days=40), "attended")
    ausente = _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a,
                     ahora - dt.timedelta(days=20), "no_show")
    futura = _ficha(
        org_a, user_a, paciente, practitioner_a, suc, agenda_a,
        ahora + dt.timedelta(days=3), "confirmed", anticipacion=10,
        pago=("simulated", ahora - dt.timedelta(hours=1)),
    )
    with tenant_context(org_a.id):
        filas = {f.appointment_id: _valores(f)
                 for f in features.build_rows(org_a, [atendida, ausente, futura], ahora)}

    # La futura mira atrás: una visita y una falta.
    assert filas[futura.id]["prior_no_shows"] == 1
    assert filas[futura.id]["prior_visits"] == 1
    assert filas[futura.id]["lead_days"] == pytest.approx(10, abs=0.01)
    assert filas[futura.id]["paid_early"] == 1.0
    # La primera no tiene nada antes; la segunda sólo ve a la primera.
    assert (filas[atendida.id]["prior_no_shows"], filas[atendida.id]["prior_visits"]) == (0, 0)
    assert (filas[ausente.id]["prior_no_shows"], filas[ausente.id]["prior_visits"]) == (0, 1)


def test_pagar_en_ventanilla_el_mismo_dia_no_es_pagar_por_adelantado(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    paciente = _paciente(org_a, "pago")
    ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
    inicio = ahora + dt.timedelta(days=2)
    en_ventanilla = _ficha(org_a, user_a, paciente, practitioner_a, branches_a["centro"],
                           agenda_a, inicio, "confirmed",
                           pago=("cash", inicio - dt.timedelta(minutes=15)))
    sin_pago = _ficha(org_a, user_a, paciente, practitioner_a, branches_a["centro"],
                      agenda_a, inicio + dt.timedelta(days=1), "pending_payment")
    with tenant_context(org_a.id):
        filas = {f.appointment_id: _valores(f)
                 for f in features.build_rows(org_a, [en_ventanilla, sin_pago], ahora)}
    assert filas[en_ventanilla.id]["paid_early"] == 0.0
    assert filas[sin_pago.id]["paid_early"] == 0.0


def test_el_domingo_no_tiene_columna_de_dia(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    paciente = _paciente(org_a, "dom")
    hoy = timezone.now().astimezone(LA_PAZ).date()
    domingo = hoy + dt.timedelta(days=(6 - hoy.weekday()) % 7 or 7)
    inicio = dt.datetime.combine(domingo, dt.time(9, 0), tzinfo=LA_PAZ)
    ficha = _ficha(org_a, user_a, paciente, practitioner_a, branches_a["centro"],
                   agenda_a, inicio, "confirmed")
    with tenant_context(org_a.id):
        valores = _valores(features.build_rows(org_a, [ficha], timezone.now())[0])
    assert sum(valores[f"dow_{i}"] for i in range(6)) == 0.0
    assert valores["afternoon"] == 0.0


def test_la_etiqueta_es_la_inasistencia_de_us29(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    """Ausente: no_show, o confirmada vencida sin check-in. Una cancelada no cuenta."""
    paciente = _paciente(org_a, "etq")
    suc = branches_a["centro"]
    ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
    pasado = lambda dias: ahora - dt.timedelta(days=dias)  # noqa: E731
    hechas = {
        "atendida": _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a,
                           pasado(1), "attended"),
        "no_show": _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a,
                          pasado(2), "no_show"),
        "vencida_sin_checkin": _ficha(org_a, user_a, paciente, practitioner_a, suc,
                                      agenda_a, pasado(3), "confirmed"),
        "vencida_con_checkin": _ficha(org_a, user_a, paciente, practitioner_a, suc,
                                      agenda_a, pasado(4), "confirmed",
                                      checked_in=pasado(4)),
    }
    for nombre, esperado in [("atendida", 0), ("no_show", 1),
                             ("vencida_sin_checkin", 1), ("vencida_con_checkin", 0)]:
        assert features.label_of(hechas[nombre]) == esperado, nombre

    # Las que no debían atenderse no entran al conteo.
    _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a, pasado(5), "cancelled")
    _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a,
           ahora + dt.timedelta(days=2), "confirmed")
    _ficha(org_a, user_a, paciente, practitioner_a, suc, agenda_a,
           ahora + dt.timedelta(days=3), "pending_payment")
    with tenant_context(org_a.id):
        assert training.data_status(org_a, ahora) == (4, 2)


# --------------------------------------------------------------------------
#  Entrenamiento
# --------------------------------------------------------------------------

def test_sin_datos_suficientes_no_se_crea_ninguna_version(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=training.MIN_LABELED - 50, con_senal=True)
    resultado = training.train_for(org_a)
    assert resultado.version is None
    assert resultado.reason == "sin_datos"
    assert "datos suficientes" in resultado.message
    with tenant_context(org_a.id):
        assert not ModelVersion.objects.exists()


def test_con_una_senal_fuerte_el_modelo_le_gana_a_la_linea_base(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=800, con_senal=True)
    resultado = training.train_for(org_a)
    version = resultado.version
    assert version is not None
    assert version.beats_baseline is True
    assert version.status == ModelVersion.Status.ACTIVE
    assert version.version == 1
    assert version.n_train + version.n_test == 800
    # Lo que se guarda son números en JSON, nada que haya que deserializar.
    assert set(version.params) == {"features", "coef", "intercept", "mean", "scale"}
    assert version.params["features"] == features.FEATURE_NAMES
    m = version.metrics
    assert m["brier"] < m["brier_baseline"]
    assert m["auc"] > 0.5
    assert 0 < m["cutoffs"]["medium"] < m["cutoffs"]["high"] < 1
    # Los umbrales son relativos a la tasa base de la organización.
    assert m["cutoffs"]["medium"] == pytest.approx(1.2 * version.base_rate)
    assert m["cutoffs"]["high"] == pytest.approx(2.0 * version.base_rate)


def test_el_modelo_redescubre_el_signo_de_las_causas(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    """Más anticipación y más faltas previas suben el riesgo; pagar adelantado lo baja."""
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=800, con_senal=True)
    params = training.train_for(org_a).version.params
    coef = dict(zip(params["features"], params["coef"]))
    assert coef["lead_days"] > 0
    assert coef["prior_no_shows"] > 0
    assert coef["paid_early"] < 0


def test_un_modelo_nunca_es_vigente_si_no_le_gana_a_la_base(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    """Con ausencias al azar no hay nada que aprender. Lo que se garantiza no
    depende de la suerte: vigente si y sólo si supera la línea base."""
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=600, con_senal=False, semilla=3)
    version = training.train_for(org_a).version
    assert version is not None
    if version.beats_baseline:
        assert version.status == ModelVersion.Status.ACTIVE
    else:
        assert version.status == ModelVersion.Status.REJECTED
        with tenant_context(org_a.id):
            assert scoring.active_version(org_a) is None


def test_entrenar_otra_vez_deja_candidato_al_nuevo_y_no_reemplaza_al_vigente(
    org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=800, con_senal=True)
    primero = training.train_for(org_a).version
    segundo = training.train_for(org_a).version
    assert (primero.version, segundo.version) == (1, 2)
    assert segundo.status == ModelVersion.Status.CANDIDATE
    with tenant_context(org_a.id):
        assert scoring.active_version(org_a).pk == primero.pk

        # Promover retira al anterior: nunca dos vigentes (índice único parcial).
        training.promote(segundo)
        estados = dict(ModelVersion.objects.values_list("version", "status"))
    assert estados == {1: "retired", 2: "active"}


def test_un_modelo_rechazado_no_se_promueve(org_a):
    rechazado = _modelo_a_mano(org_a, estado="rejected", beats=False)
    with pytest.raises(ValueError):
        training.promote(rechazado)


def test_cada_organizacion_entrena_solo_con_sus_fichas(
    org_a, org_b_premium, user_a, user_b, practitioner_a, branches_a, agenda_a,
    mundo_b, branch_b,
):
    """Regla 16: el modelo de A no ve las fichas de B, aunque B tenga más."""
    profesional_b, agenda_b = mundo_b
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=300, con_senal=True)
    _poblar(org_b_premium, user_b, profesional_b, branch_b, agenda_b,
            n=500, con_senal=False, semilla=9)

    version_a = training.train_for(org_a).version
    assert version_a.n_train + version_a.n_test == 300
    with tenant_context(org_b_premium.id):
        assert not ModelVersion.objects.exists()
    with tenant_context(org_a.id):
        assert not ModelVersion.objects.filter(organization=org_b_premium).exists()

    version_b = training.train_for(org_b_premium).version
    assert version_b.n_train + version_b.n_test == 500
    assert version_b.organization_id == org_b_premium.id


def test_el_comando_solo_entrena_a_quien_tiene_el_plan(
    org_a, org_b, user_a, user_b, practitioner_a, branches_a, agenda_a, mundo_b, branch_b,
):
    """A es Premium y B es Básica: el comando saltea a B aunque tenga datos."""
    profesional_b, agenda_b = mundo_b
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=300, con_senal=True)
    _poblar(org_b, user_b, profesional_b, branch_b, agenda_b, n=300, con_senal=True)
    salida = StringIO()
    call_command("train_noshow", "--all", stdout=salida)
    texto = salida.getvalue()
    assert "kolping" in texto
    with tenant_context(org_a.id):
        assert ModelVersion.objects.filter(organization=org_a).exists()
    with tenant_context(org_b.id):
        assert not ModelVersion.objects.exists()


def test_con_lo_que_siembra_seed_dataset_el_modelo_aprende_y_puntua(platform_admin, plans):
    """De punta a punta, con datos reales del generador y no sintéticos míos.

    Es la prueba que justifica el diseño: una organización nueva se siembra
    **en una sola pasada** y de ahí sale un modelo que le gana a la línea base.
    (Con el pasado reciente y el historial sembrados por separado, el modelo
    veía faltas que el generador no había usado como causa y quedaba rechazado:
    predecía 24 % de ausencias donde había 16 %.)
    """
    call_command("seed_dataset", "--only", "losandes",
                 "--password", "clave-de-demostracion-1")
    with platform_admin_context():
        from tenancy.models import Organization
        org = Organization.objects.get(slug="losandes")

    version = training.train_for(org).version
    assert version is not None
    assert version.beats_baseline and version.status == ModelVersion.Status.ACTIVE
    m = version.metrics
    assert m["auc"] > 0.7
    assert m["brier"] < m["brier_baseline"]
    # Las causas del generador, en el orden de importancia que se les dio.
    coef = dict(zip(version.params["features"], version.params["coef"]))
    assert coef["prior_no_shows"] > 0 and coef["lead_days"] > 0 and coef["paid_early"] < 0

    # Y puntúa lo futuro: cada ficha activa queda con nivel y razones.
    puntuadas = scoring.score_for(org)
    assert puntuadas > 0
    with tenant_context(org.id):
        activas = Appointment.objects.filter(
            status__in=Appointment.ACTIVE_STATUSES, starts_at__gt=timezone.now(),
            starts_at__lte=timezone.now() + dt.timedelta(days=scoring.HORIZON_DAYS),
        ).count()
        assert puntuadas == activas
        assert NoShowPrediction.objects.count() == activas
        assert {p.level for p in NoShowPrediction.objects.all()} <= {"low", "medium", "high"}
        assert all(len(p.factors) <= 3 for p in NoShowPrediction.objects.all())


# --------------------------------------------------------------------------
#  Predecir
# --------------------------------------------------------------------------

def test_la_probabilidad_es_la_logistica_de_los_coeficientes():
    params = {"features": ["x"], "coef": [1.0], "intercept": 0.0, "mean": [0.0], "scale": [1.0]}
    assert scoring.predict_proba(params, [0.0]) == pytest.approx(0.5)
    assert scoring.predict_proba(params, [2.0]) == pytest.approx(0.8808, abs=1e-4)
    # Sin desbordarse en los extremos.
    assert scoring.predict_proba({**params, "intercept": -900.0}, [0.0]) == 0.0
    assert scoring.predict_proba({**params, "intercept": 900.0}, [0.0]) == 1.0
    # La escala 0 (variable constante) no divide por cero.
    constante = {**params, "scale": [0.0]}
    assert 0.0 <= scoring.predict_proba(constante, [5.0]) <= 1.0


def test_los_niveles_salen_de_los_cortes():
    cortes = {"medium": 0.2, "high": 0.4}
    assert scoring.level_for(0.05, cortes) == "low"
    assert scoring.level_for(0.2, cortes) == "medium"
    assert scoring.level_for(0.39, cortes) == "medium"
    assert scoring.level_for(0.4, cortes) == "high"


def test_las_razones_son_pocas_en_español_y_con_sentido():
    names = features.FEATURE_NAMES
    coef = [0.0] * len(names)
    coef[names.index("prior_no_shows")] = 1.0
    coef[names.index("paid_early")] = -1.0
    coef[names.index("lead_days")] = 0.5
    coef[names.index("dow_0")] = 0.4
    params = {"features": names, "coef": coef, "intercept": 0.0,
              "mean": [0.0] * len(names), "scale": [1.0] * len(names)}
    valores = [0.0] * len(names)
    valores[names.index("prior_no_shows")] = 2.0
    valores[names.index("paid_early")] = 1.0
    valores[names.index("lead_days")] = 10.0
    valores[names.index("dow_0")] = 1.0
    razones = scoring.explain(params, valores)
    assert len(razones) <= 3
    assert razones[0]["key"] == "lead_days" and razones[0]["direction"] == "up"
    assert {r["direction"] for r in razones} <= {"up", "down"}
    assert all(r["label"] for r in razones)
    etiquetas = {r["key"]: r["label"] for r in razones}
    assert etiquetas["lead_days"] == "Reservó con 10 días de anticipación"


def test_solo_se_puntuan_las_fichas_futuras_y_activas(
    org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _modelo_a_mano(org_a)
    perfil = paciente_a.patient_profile
    suc = branches_a["centro"]
    ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
    confirmadas = _futuras(org_a, paciente_a, perfil, practitioner_a, suc, agenda_a, [2, 20])
    pendiente = _ficha(org_a, paciente_a, perfil, practitioner_a, suc, agenda_a,
                       ahora + dt.timedelta(days=9), "pending_payment", anticipacion=40)
    cancelada = _ficha(org_a, paciente_a, perfil, practitioner_a, suc, agenda_a,
                       ahora + dt.timedelta(days=10), "cancelled")
    pasada = _ficha(org_a, paciente_a, perfil, practitioner_a, suc, agenda_a,
                    ahora - dt.timedelta(days=2), "attended")
    lejana = _ficha(org_a, paciente_a, perfil, practitioner_a, suc, agenda_a,
                    ahora + dt.timedelta(days=scoring.HORIZON_DAYS + 5), "confirmed")

    assert scoring.score_for(org_a, ahora) == 3
    with tenant_context(org_a.id):
        puntuadas = set(NoShowPrediction.objects.values_list("appointment_id", flat=True))
        niveles = {p.appointment_id: p.level for p in NoShowPrediction.objects.all()}
    assert puntuadas == {confirmadas[0].id, confirmadas[1].id, pendiente.id}
    assert not puntuadas & {cancelada.id, pasada.id, lejana.id}
    assert niveles[confirmadas[0].id] == "low"        # 2 días: 13 %
    assert niveles[confirmadas[1].id] == "medium"     # 20 días: 27 %
    assert niveles[pendiente.id] == "high"            # 40 días: 50 %


def test_puntuar_dos_veces_no_duplica_ni_repite_filas(
    org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _modelo_a_mano(org_a)
    _futuras(org_a, paciente_a, paciente_a.patient_profile, practitioner_a,
             branches_a["centro"], agenda_a, [2, 20, 40])
    ahora = timezone.now()
    assert scoring.score_for(org_a, ahora) == 3
    assert scoring.score_for(org_a, ahora + dt.timedelta(minutes=5)) == 3
    with tenant_context(org_a.id):
        assert NoShowPrediction.objects.count() == 3


def test_sin_modelo_vigente_no_se_inventa_ninguna_prediccion(
    org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _futuras(org_a, paciente_a, paciente_a.patient_profile, practitioner_a,
             branches_a["centro"], agenda_a, [5, 10])
    assert scoring.score_for(org_a) == 0
    # Un modelo rechazado tampoco sirve.
    _modelo_a_mano(org_a, estado="rejected", beats=False)
    assert scoring.score_for(org_a) == 0
    with tenant_context(org_a.id):
        assert not NoShowPrediction.objects.exists()


def test_el_proceso_no_puntua_a_una_organizacion_sin_el_plan(
    org_a, org_b, user_b, mundo_b, branch_b,
):
    profesional_b, agenda_b = mundo_b
    _modelo_a_mano(org_b)                       # B es Básica: no debería usarse
    paciente = _paciente(org_b, "plan")
    _ficha(org_b, user_b, paciente, profesional_b, branch_b, agenda_b,
           timezone.now() + dt.timedelta(days=3), "confirmed")
    assert scoring.run_due() == 0
    with tenant_context(org_b.id):
        assert not NoShowPrediction.objects.exists()


def test_el_comando_de_puntuacion_se_apaga_con_la_variable(settings):
    settings.NOSHOW_SCORING = "off"
    salida = StringIO()
    call_command("score_noshow", stdout=salida)
    assert "apagada" in salida.getvalue()


# --------------------------------------------------------------------------
#  La API
# --------------------------------------------------------------------------

def _listar(api_client, **params):
    return api_client.get(reverse("noshow:appointments"), params)


def _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a):
    """Tres fichas futuras de A, una por nivel, ya puntuadas."""
    _modelo_a_mano(org_a)
    fichas = _futuras(org_a, paciente_a, paciente_a.patient_profile, practitioner_a,
                      branches_a["centro"], agenda_a, [2, 20, 40])
    scoring.score_for(org_a)
    return fichas


def test_la_administracion_ve_el_riesgo_de_sus_fichas(
    api_client, admin_a, org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    respuesta = _listar(autenticar(api_client, admin_a))
    assert respuesta.status_code == 200, respuesta.content
    datos = respuesta.json()
    assert datos["count"] == 3
    assert [f["level"] for f in datos["results"]] == ["low", "medium", "high"]
    fila = datos["results"][2]
    assert set(fila) == {"appointment_id", "patient_name", "practitioner_name",
                         "branch_name", "starts_at", "status", "level", "probability",
                         "factors", "computed_at"}
    assert 0 < fila["probability"] < 1
    assert fila["branch_name"] == "Sede Centro"
    assert fila["factors"] and fila["factors"][0]["label"]


def test_se_filtra_por_nivel_y_por_sucursal(
    api_client, admin_a, org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    cliente = autenticar(api_client, admin_a)
    altos = _listar(cliente, level="high").json()
    assert altos["count"] == 1 and altos["results"][0]["level"] == "high"
    assert _listar(cliente, branch=str(branches_a["centro"].id)).json()["count"] == 3
    assert _listar(cliente, branch=str(branches_a["norte"].id)).json()["count"] == 0


def test_el_rango_por_omision_son_catorce_dias_y_se_puede_ampliar(
    api_client, admin_a, org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _modelo_a_mano(org_a)
    ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
    perfil = paciente_a.patient_profile
    _ficha(org_a, paciente_a, perfil, practitioner_a, branches_a["centro"], agenda_a,
           ahora + dt.timedelta(days=5), "confirmed")
    _ficha(org_a, paciente_a, perfil, practitioner_a, branches_a["centro"], agenda_a,
           ahora + dt.timedelta(days=30), "confirmed")
    scoring.score_for(org_a)
    cliente = autenticar(api_client, admin_a)
    assert _listar(cliente).json()["count"] == 1
    hasta = (timezone.now().astimezone(LA_PAZ).date() + dt.timedelta(days=45)).isoformat()
    assert _listar(cliente, to=hasta).json()["count"] == 2


def test_la_lista_se_pagina(
    api_client, admin_a, org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    pagina = _listar(autenticar(api_client, admin_a), page_size=2).json()
    assert pagina["count"] == 3 and len(pagina["results"]) == 2 and pagina["next"]


@pytest.mark.parametrize("params,codigo", [
    ({"from": "15-11-2026"}, "invalid_date"),
    ({"from": "2026-11-20", "to": "2026-11-10"}, "invalid_range"),
    ({"from": "2024-01-01", "to": "2026-12-31"}, "range_too_long"),
    ({"level": "critico"}, "invalid_level"),
    ({"branch": "no-es-un-uuid"}, "invalid_branch"),
])
def test_los_parametros_malos_responden_400_con_su_codigo(
    api_client, admin_a, params, codigo,
):
    respuesta = _listar(autenticar(api_client, admin_a), **params)
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == codigo


def test_una_sucursal_de_otra_organizacion_no_se_acepta(
    api_client, admin_a, branch_b,
):
    respuesta = _listar(autenticar(api_client, admin_a), branch=str(branch_b.id))
    assert respuesta.status_code == 400
    assert respuesta.json()["code"] == "invalid_branch"


def test_sin_sesion_no_se_ve_nada(api_client):
    assert _listar(api_client).status_code == 401
    assert api_client.get(reverse("noshow:model")).status_code == 401


def test_recepcion_no_ve_el_riesgo(
    api_client, recepcion_a, org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    cliente = autenticar(api_client, recepcion_a)
    assert _listar(cliente).status_code == 403
    assert cliente.get(reverse("noshow:model")).status_code == 403


def test_el_paciente_no_ve_su_propio_riesgo(
    api_client, paciente_a, org_a, practitioner_a, branches_a, agenda_a,
):
    """Regla del diseño: la calificación es de la organización, no del paciente.
    Ni los endpoints de riesgo ni la ficha que él lee traen nada de esto."""
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    cliente = autenticar(api_client, paciente_a)
    assert _listar(cliente).status_code == 403
    assert cliente.get(reverse("noshow:model")).status_code == 403

    propias = cliente.get(reverse("appointments:appointment-list"))
    assert propias.status_code == 200
    fichas = propias.json()
    assert len(fichas) == 3
    prohibidas = {"level", "probability", "factors", "risk", "noshow", "model_version"}
    for ficha in fichas:
        assert not prohibidas & set(ficha)
    assert "noshow" not in propias.content.decode().lower()


def test_el_plan_basico_recibe_plan_limit(
    api_client, admin_b, org_b,
):
    cliente = autenticar(api_client, admin_b)
    for ruta in ("noshow:appointments", "noshow:model"):
        respuesta = cliente.get(reverse(ruta))
        assert respuesta.status_code == 403
        assert respuesta.json()["code"] == "plan_limit"


def test_una_organizacion_no_ve_las_predicciones_de_otra(
    api_client, admin_b, org_b_premium, org_a, paciente_a, practitioner_a,
    branches_a, agenda_a,
):
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    respuesta = _listar(autenticar(api_client, admin_b))
    assert respuesta.status_code == 200
    assert respuesta.json()["count"] == 0


def test_una_version_retirada_no_aparece_en_la_lista(
    api_client, admin_a, org_a, paciente_a, practitioner_a, branches_a, agenda_a,
):
    _con_predicciones(org_a, paciente_a, practitioner_a, branches_a, agenda_a)
    with tenant_context(org_a.id):
        ModelVersion.objects.filter(organization=org_a).update(status="retired")
    assert _listar(autenticar(api_client, admin_a)).json()["count"] == 0


# ---- El estado del modelo ------------------------------------------------

def _estado(api_client, usuario):
    respuesta = autenticar(api_client, usuario).get(reverse("noshow:model"))
    assert respuesta.status_code == 200, respuesta.content
    return respuesta.json()


def test_sin_modelo_y_sin_datos_la_pantalla_dice_por_que(api_client, admin_a):
    datos = _estado(api_client, admin_a)
    assert datos["model"] is None and datos["reason"] == "sin_datos"
    assert "datos suficientes" in datos["message"]


def test_con_datos_pero_sin_entrenar_dice_que_falta_entrenar(
    api_client, admin_a, org_a, user_a, practitioner_a, branches_a, agenda_a,
):
    _poblar(org_a, user_a, practitioner_a, branches_a["centro"], agenda_a,
            n=300, con_senal=True)
    assert _estado(api_client, admin_a)["reason"] == "sin_modelo"


def test_un_modelo_rechazado_se_explica_y_no_se_usa(api_client, admin_a, org_a):
    _modelo_a_mano(org_a, estado="rejected", beats=False)
    datos = _estado(api_client, admin_a)
    assert datos["model"] is None
    assert datos["reason"] == "no_supera_base"
    assert datos["rejected"]["version"] == 1
    assert "no se usa" in datos["message"]


def test_el_modelo_vigente_trae_sus_metricas_contra_la_base(api_client, admin_a, org_a):
    _modelo_a_mano(org_a)
    datos = _estado(api_client, admin_a)
    assert datos["reason"] is None and datos["rejected"] is None
    modelo = datos["model"]
    assert modelo["version"] == 1 and modelo["status"] == "active"
    assert modelo["beats_baseline"] is True
    assert modelo["metrics"]["brier"] < modelo["metrics"]["brier_baseline"]
    assert modelo["cutoffs"] == {"medium": 0.2, "high": 0.4}
    assert (modelo["n_train"], modelo["n_test"]) == (400, 100)


# --------------------------------------------------------------------------
#  Lo que la base garantiza aunque la aplicación se equivoque
# --------------------------------------------------------------------------

def test_una_prediccion_no_cuelga_de_una_ficha_de_otra_organizacion(
    org_a, org_b, user_b, mundo_b, branch_b,
):
    """Clave compuesta `(appointment_id, organization_id)`."""
    from django.db import IntegrityError, transaction

    profesional_b, agenda_b = mundo_b
    paciente_b = _paciente(org_b, "cruce")
    ficha_b = _ficha(org_b, user_b, paciente_b, profesional_b, branch_b, agenda_b,
                     timezone.now() + dt.timedelta(days=3), "confirmed")
    version_a = _modelo_a_mano(org_a)
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                NoShowPrediction.objects.create(
                    organization=org_a, appointment_id=ficha_b.id,
                    model_version=version_a, probability=0.5, level="high",
                )


def test_dos_versiones_vigentes_a_la_vez_no_caben(org_a):
    from django.db import IntegrityError, transaction

    _modelo_a_mano(org_a, version=1)
    # El contexto va afuera y el `atomic` adentro: un error de integridad dentro
    # de `tenant_context` rompe la transacción antes de que pueda restaurarse.
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _crear_modelo(org_a, version=2)


def test_un_modelo_que_no_supera_la_base_no_puede_ser_vigente(org_a):
    from django.db import IntegrityError, transaction

    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                _crear_modelo(org_a, estado="active", beats=False)
