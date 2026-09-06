"""US-08 — Antecedentes del paciente.

Lo que más se prueba acá es el punto (g): quién alcanza los antecedentes de
quién. Es una historia de datos clínicos, así que el aislamiento no se juega
sólo entre organizaciones —RLS ya lo resuelve— sino **dentro** de una: el
paciente de al lado no es un extraño para la base de datos, y sí lo es para el
caso de uso.
"""

import datetime as dt

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from accounts.tokens import tokens_for_user
from audit.actions import Action
from catalog.models import Practitioner
from patients.models import Patient, PatientHistoryEntry
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"

PERMISOS_PACIENTE = [
    "patients.dependent.read",
    "patients.dependent.write",
    "patients.history.read",
    "patients.history.write",
]

# El médico sólo lee (punto g). No lleva `history.write`: lo que hay en esta
# tabla lo declaró el paciente, y el diagnóstico del profesional es del
# Sprint 3 y de otra tabla.
PERMISOS_MEDICO = ["patients.history.read"]


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def dar_rol(user, organization, code, name, permission_codes):
    """Reutiliza el rol si ya existe: el código es único por organización y
    estas pruebas necesitan dos pacientes en el mismo centro médico."""
    with tenant_context(organization.id):
        role, creado = Role.objects.get_or_create(
            organization=organization, code=code, defaults={"name": name},
        )
        if creado:
            RolePermission.objects.bulk_create([
                RolePermission(
                    role=role, permission=permission, organization=organization,
                )
                for permission in Permission.objects.filter(
                    code__in=permission_codes,
                )
            ])
        UserRole.objects.create(user=user, role=role, organization=organization)
    return role


def ficha(user, organization, documento):
    with tenant_context(organization.id):
        return Patient.objects.create(
            organization=organization, user=user,
            document_type=Patient.DocumentType.CI, document_number=documento,
            first_name=user.first_name, last_name=user.last_name,
            birth_date=dt.date(1990, 5, 20),
        )


@pytest.fixture
def paciente_a(db, org_a, user_a):
    dar_rol(user_a, org_a, "patient", "Paciente", PERMISOS_PACIENTE)
    ficha(user_a, org_a, "5001")
    return user_a


@pytest.fixture
def dependiente_a(db, org_a, paciente_a):
    """Un menor a cargo de `paciente_a`, sin cuenta de acceso."""
    with tenant_context(org_a.id):
        return Patient.objects.create(
            organization=org_a, guardian=paciente_a.patient_profile,
            relationship="child", first_name="Mateo", last_name="Ríos",
            birth_date=dt.date(2020, 3, 15),
        )


@pytest.fixture
def vecino_a(db, org_a):
    """Otro paciente de la misma organización. No es un extraño para la base:
    RLS lo deja ver todo lo de `org_a`. Sí lo es para el caso de uso."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="carla@kolping.test", password=CLAVE, organization=org_a,
            first_name="Carla", last_name="Vaca", document_number="5003",
        )
    dar_rol(user, org_a, "patient", "Paciente", PERMISOS_PACIENTE)
    ficha(user, org_a, "5003")
    return user


@pytest.fixture
def medico_a(db, org_a):
    """Cuenta **y ficha de profesional**: las dos hacen falta.

    El permiso solo no alcanza —el rol Paciente también lleva
    `patients.history.read`, para ver lo suyo—. Lo que distingue a quien puede
    leer la ficha de otro es estar en el catálogo de profesionales (US-12).
    """
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="doctora@kolping.test", password=CLAVE, organization=org_a,
            first_name="Laura", last_name="Gómez", document_number="5004",
        )
        Practitioner.objects.create(
            organization=org_a, user=user,
            first_name="Laura", last_name="Gómez", license_number="MP-1000",
        )
    dar_rol(user, org_a, "practitioner", "Médico", PERMISOS_MEDICO)
    return user


@pytest.fixture
def medico_dado_de_baja_a(db, org_a):
    """Un profesional inactivo (US-12 e). Conserva rol y permiso."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="exmedico@kolping.test", password=CLAVE, organization=org_a,
            first_name="Raúl", last_name="Soto", document_number="5005",
        )
        Practitioner.objects.create(
            organization=org_a, user=user, is_active=False,
            first_name="Raúl", last_name="Soto", license_number="MP-1001",
        )
    dar_rol(user, org_a, "practitioner", "Médico", PERMISOS_MEDICO)
    return user


@pytest.fixture
def paciente_b(db, org_b, user_b):
    dar_rol(user_b, org_b, "patient", "Paciente", PERMISOS_PACIENTE)
    ficha(user_b, org_b, "5002")
    return user_b


def registrar(api_client, user, **datos):
    cuerpo = {
        "kind": "allergy",
        "description": "Penicilina",
        "severity": "severe",
    }
    cuerpo.update(datos)
    return autenticar(api_client, user).post(
        reverse("patients:history-list"), cuerpo, format="json",
    )


def asentar(patient, organization, **datos):
    campos = {"kind": "condition", "description": "Hipertensión"}
    campos.update(datos)
    with tenant_context(organization.id):
        return PatientHistoryEntry.objects.create(
            organization=organization, patient=patient, **campos,
        )


# --------------------------------------------------------------------------
#  Puntos (a), (b) y (d) — qué se registra
# --------------------------------------------------------------------------

def test_se_registran_los_tres_tipos_de_antecedente(
    api_client, paciente_a, org_a,
):
    assert registrar(api_client, paciente_a).status_code == 201
    assert registrar(
        api_client, paciente_a,
        kind="condition", description="Hipertensión", severity="",
    ).status_code == 201
    assert registrar(
        api_client, paciente_a,
        kind="medication", description="Metformina 850mg", severity="",
    ).status_code == 201

    respuesta = autenticar(api_client, paciente_a).get(
        reverse("patients:history-list"),
    )
    assert respuesta.json()["count"] == 3


def test_la_alergia_lleva_severidad_y_las_demas_no(api_client, paciente_a):
    """Punto (b). Una medicación "grave" no significa nada, y dejarla entrar
    obligaría a la pantalla a decidir cuándo mostrarla."""
    sin_severidad = registrar(api_client, paciente_a, severity="")
    assert sin_severidad.status_code == 400
    assert "severity" in sin_severidad.json()

    medicacion_grave = registrar(
        api_client, paciente_a,
        kind="medication", description="Metformina", severity="severe",
    )
    assert medicacion_grave.status_code == 400
    assert "severity" in medicacion_grave.json()


def test_el_antecedente_queda_marcado_como_declarado(api_client, paciente_a):
    """Punto (d). No es un diagnóstico: el del médico llega en el Sprint 3, en
    otra tabla, y no vale lo mismo."""
    creado = registrar(api_client, paciente_a).json()
    assert creado["source"] == "self_reported"

    # Y el cliente no puede hacerlo pasar por registrado por un profesional.
    forzado = registrar(api_client, paciente_a, source="practitioner").json()
    assert forzado["source"] == "self_reported"


def test_la_fecha_de_registro_se_guarda_sola(api_client, paciente_a, org_a):
    """Punto (a). Es un dato clínico que se muestra, no una marca técnica."""
    creado = registrar(api_client, paciente_a).json()
    assert creado["recorded_at"] == dt.date.today().isoformat()


# --------------------------------------------------------------------------
#  Punto (c) — sobre uno mismo o sobre un dependiente
# --------------------------------------------------------------------------

def test_el_titular_registra_antecedentes_de_su_dependiente(
    api_client, paciente_a, dependiente_a, org_a,
):
    """Misma pantalla, mismo selector de US-07."""
    respuesta = registrar(
        api_client, paciente_a,
        patient=str(dependiente_a.id),
        kind="allergy", description="Maní", severity="anaphylactic",
    )

    assert respuesta.status_code == 201
    with tenant_context(org_a.id):
        entrada = PatientHistoryEntry.objects.get(id=respuesta.json()["id"])
        assert entrada.patient_id == dependiente_a.id
        assert entrada.declared_by_id == paciente_a.id


def test_sin_indicar_paciente_se_asume_el_propio(
    api_client, paciente_a, org_a,
):
    creado = registrar(api_client, paciente_a).json()

    with tenant_context(org_a.id):
        entrada = PatientHistoryEntry.objects.get(id=creado["id"])
        assert entrada.patient_id == paciente_a.patient_profile.id


# --------------------------------------------------------------------------
#  Punto (e) — edición y baja lógica
# --------------------------------------------------------------------------

def test_la_baja_es_logica_y_el_historico_no_se_pierde(
    api_client, paciente_a, org_a,
):
    """Alguien que dejó de ser alérgico sigue habiéndolo sido, y el módulo de
    atención tiene que poder verlo."""
    creado = registrar(api_client, paciente_a).json()

    respuesta = autenticar(api_client, paciente_a).delete(
        reverse("patients:history-detail", args=[creado["id"]]),
    )
    assert respuesta.status_code == 204

    with tenant_context(org_a.id):
        entrada = PatientHistoryEntry.objects.get(id=creado["id"])
        assert entrada.is_active is False

    # Ya no aparece entre lo vigente…
    vigentes = autenticar(api_client, paciente_a).get(
        reverse("patients:history-list"),
    )
    assert vigentes.json()["count"] == 0

    # …pero sigue estando si se lo pide.
    todo = autenticar(api_client, paciente_a).get(
        reverse("patients:history-list"), {"include_inactive": "true"},
    )
    assert todo.json()["count"] == 1


def test_el_paciente_edita_lo_que_declaro(api_client, paciente_a):
    creado = registrar(api_client, paciente_a).json()

    respuesta = autenticar(api_client, paciente_a).patch(
        reverse("patients:history-detail", args=[creado["id"]]),
        {"severity": "mild"}, format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["severity_label"] == "Leve"


# --------------------------------------------------------------------------
#  Punto (f) — el conjunto vigente para el módulo de atención
# --------------------------------------------------------------------------

def test_los_destacados_llegan_agrupados_y_las_alergias_de_mas_grave_a_menos(
    api_client, medico_a, paciente_a, org_a,
):
    """Es la mitad web de la historia. Las alergias van primero y ordenadas
    porque son el dato que cambia una receta."""
    ficha_a = paciente_a.patient_profile
    asentar(ficha_a, org_a, kind="allergy", description="Ibuprofeno",
            severity="mild")
    asentar(ficha_a, org_a, kind="allergy", description="Penicilina",
            severity="anaphylactic")
    asentar(ficha_a, org_a, kind="condition", description="Hipertensión")
    asentar(ficha_a, org_a, kind="medication", description="Enalapril")
    dada_de_baja = asentar(ficha_a, org_a, kind="condition",
                           description="Vieja", is_active=False)

    respuesta = autenticar(api_client, medico_a).get(
        reverse("patients:history-highlights"), {"patient": str(ficha_a.id)},
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert [a["description"] for a in cuerpo["allergies"]] == [
        "Penicilina", "Ibuprofeno",
    ]
    assert [c["description"] for c in cuerpo["conditions"]] == ["Hipertensión"]
    assert [m["description"] for m in cuerpo["medications"]] == ["Enalapril"]
    # Punto (d) dicho en la respuesta, no sólo en la documentación.
    assert cuerpo["self_reported"] is True
    assert dada_de_baja.description not in respuesta.content.decode()


# --------------------------------------------------------------------------
#  Punto (g) — quién alcanza qué, y qué queda en la bitácora
# --------------------------------------------------------------------------

def test_la_lectura_de_un_profesional_queda_en_la_bitacora(
    api_client, medico_a, paciente_a, org_a,
):
    ficha_a = paciente_a.patient_profile
    asentar(ficha_a, org_a)

    respuesta = autenticar(api_client, medico_a).get(
        reverse("patients:history-highlights"), {"patient": str(ficha_a.id)},
    )
    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.HISTORY_READ)
    assert asiento.user_id == medico_a.id
    assert asiento.entity_id == str(ficha_a.id)
    assert asiento.detail["origen"] == "destacados"


def test_el_paciente_leyendo_lo_suyo_no_genera_asiento(
    api_client, paciente_a, org_a,
):
    """Una fila por cada vez que alguien abre su propia pantalla convertiría la
    bitácora en un registro de navegación, y enterraría el asiento que importa:
    quién de afuera miró la ficha de quién."""
    asentar(paciente_a.patient_profile, org_a)

    autenticar(api_client, paciente_a).get(reverse("patients:history-list"))

    with tenant_context(org_a.id):
        assert not AuditLog.objects.filter(action=Action.HISTORY_READ).exists()


def test_un_profesional_no_registra_ni_edita_antecedentes(
    api_client, medico_a, paciente_a, org_a,
):
    ficha_a = paciente_a.patient_profile
    entrada = asentar(ficha_a, org_a)

    alta = autenticar(api_client, medico_a).post(
        reverse("patients:history-list"),
        {"patient": str(ficha_a.id), "kind": "condition",
         "description": "Diabetes"},
        format="json",
    )
    # El médico no lleva `patients.history.write`: no pasa ni la clase de
    # permiso.
    assert alta.status_code == 403

    baja = autenticar(api_client, medico_a).delete(
        reverse("patients:history-detail", args=[entrada.id]),
    )
    assert baja.status_code == 403


def test_un_paciente_no_ve_los_antecedentes_de_su_vecino(
    api_client, paciente_a, vecino_a, org_a,
):
    """RLS no separa acá: los dos son de la misma organización, y los dos
    llevan `patients.history.read` porque los dos leen los suyos. Lo que separa
    es de quién es la ficha, y quién está en el catálogo de profesionales."""
    asentar(paciente_a.patient_profile, org_a, description="Hipertensión")

    respuesta = autenticar(api_client, vecino_a).get(
        reverse("patients:history-list"),
        {"patient": str(paciente_a.patient_profile.id)},
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "paciente_no_encontrado"


def test_la_respuesta_no_distingue_un_paciente_ajeno_de_uno_inexistente(
    api_client, paciente_a, vecino_a, org_a,
):
    """Un 403 confirmaría que esa persona está registrada en este centro
    médico. Con un 404 quien prueba identificadores no aprende nada."""
    ajeno = autenticar(api_client, vecino_a).get(
        reverse("patients:history-list"),
        {"patient": str(paciente_a.patient_profile.id)},
    )
    inexistente = autenticar(api_client, vecino_a).get(
        reverse("patients:history-list"),
        {"patient": "00000000-0000-4000-8000-000000000000"},
    )

    assert ajeno.status_code == inexistente.status_code == 404
    assert ajeno.json() == inexistente.json()


def test_un_antecedente_ajeno_no_se_abre_por_su_id(
    api_client, paciente_a, vecino_a, org_a,
):
    entrada = asentar(paciente_a.patient_profile, org_a)

    respuesta = autenticar(api_client, vecino_a).get(
        reverse("patients:history-detail", args=[entrada.id]),
    )

    assert respuesta.status_code == 404


def test_sin_permiso_no_se_leen_antecedentes(api_client, org_a, user_a):
    dar_rol(user_a, org_a, "pelado", "Sin permisos", [])

    respuesta = autenticar(api_client, user_a).get(
        reverse("patients:history-list"),
    )

    assert respuesta.status_code == 403


# --------------------------------------------------------------------------
#  Aislamiento entre organizaciones (RNF-08)
# --------------------------------------------------------------------------

def test_un_medico_no_lee_los_antecedentes_de_otra_organizacion(
    api_client, medico_a, paciente_b, org_b,
):
    ficha_b = paciente_b.patient_profile
    asentar(ficha_b, org_b, description="Hipertensión")

    respuesta = autenticar(api_client, medico_a).get(
        reverse("patients:history-highlights"), {"patient": str(ficha_b.id)},
    )

    assert respuesta.status_code == 404


def test_el_listado_de_cada_organizacion_trae_solo_lo_suyo(
    api_client, paciente_a, paciente_b, org_a, org_b,
):
    asentar(paciente_a.patient_profile, org_a, description="De A")
    asentar(paciente_b.patient_profile, org_b, description="De B")

    de_a = autenticar(api_client, paciente_a).get(
        reverse("patients:history-list"),
    )
    de_b = autenticar(APIClient(), paciente_b).get(
        reverse("patients:history-list"),
    )

    assert [e["description"] for e in de_a.json()["results"]] == ["De A"]
    assert [e["description"] for e in de_b.json()["results"]] == ["De B"]


def test_un_profesional_dado_de_baja_deja_de_leer_antecedentes(
    api_client, medico_dado_de_baja_a, paciente_a, org_a,
):
    """US-12 (e) desactiva al profesional sin quitarle el rol. Si el alcance se
    resolviera sólo por el permiso, seguiría leyendo historias clínicas."""
    ficha_a = paciente_a.patient_profile
    asentar(ficha_a, org_a)

    respuesta = autenticar(api_client, medico_dado_de_baja_a).get(
        reverse("patients:history-highlights"), {"patient": str(ficha_a.id)},
    )

    assert respuesta.status_code == 404
