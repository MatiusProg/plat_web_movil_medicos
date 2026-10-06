"""Característica general 5 — Pedir un reporte hablando.

El reconocimiento de voz lo hace el dispositivo, así que acá no hay audio: lo
que se prueba es la traducción del texto dictado a una definición de reporte, y
sobre todo **lo que no puede pasar**:

- que la voz sirva para leer datos que la pantalla niega;
- que una columna o un filtro inventados por el modelo se cuelen en silencio;
- que una falla del proveedor termine en un reporte improvisado.

El proveedor se simula siempre: una prueba que llamara a Gemini de verdad
gastaría cuota, tardaría y fallaría los días que la API esté caída.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog
from accounts.tokens import tokens_for_user
from audit.actions import Action
from patients.models import Patient
from reporting import voice
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

PERMISOS_ANALISTA = [
    "reporting.report.run",
    "patients.patient.read",
]

# Quien además audita: el mismo constructor, pero con la bitácora habilitada.
PERMISOS_AUDITOR = [*PERMISOS_ANALISTA, "audit.log.read"]


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


@pytest.fixture
def analista_a(db, org_a, user_a):
    dar_rol(user_a, org_a, "analista", "Analista", PERMISOS_ANALISTA)
    return user_a


@pytest.fixture
def pacientes_a(db, org_a):
    """Pacientes ficticios: el repositorio es público (regla 7 del reparto)."""
    with tenant_context(org_a.id):
        return [
            Patient.objects.create(
                organization=org_a, first_name=nombre, last_name=apellido,
                document_number=documento, sex=sexo,
            )
            for nombre, apellido, documento, sexo in [
                ("Ana", "Álvarez", "9001", "F"),
                ("Bruno", "Bustos", "9002", "M"),
                ("Carla", "Cárdenas", "9003", "F"),
            ]
        ]


def simular_modelo(monkeypatch, respuesta, registro=None):
    """Hace que el proveedor devuelva `respuesta` sin salir a la red."""
    def falso(prompt):
        if registro is not None:
            registro.append(prompt)
        return respuesta

    monkeypatch.setattr(voice, "_call_model", falso)
    monkeypatch.setattr(voice.settings, "ASSISTANT_CHAT_PROVIDER", "gemini")
    monkeypatch.setattr(voice.settings, "GEMINI_API_KEY", "clave-de-prueba")


def dictar(api_client, texto, **extra):
    return api_client.post(
        reverse("reporting:interpret"), {"text": texto, **extra}, format="json",
    )


# --------------------------------------------------------------------------
#  Lo que se espera que funcione
# --------------------------------------------------------------------------
def test_una_frase_se_convierte_en_definicion(
    api_client, analista_a, pacientes_a, monkeypatch,
):
    simular_modelo(monkeypatch, {
        "dataset": "patients",
        "columns": ["first_name", "last_name", "phone"],
        "filters": [{"field": "sex", "operator": "eq", "value": "F"}],
        "order_by": ["last_name"],
        "format": "xlsx",
    })

    respuesta = dictar(
        autenticar(api_client, analista_a),
        "pacientes mujeres con nombre y teléfono en Excel",
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["understood"] is True
    assert cuerpo["generated_by"] == "gemini"
    assert cuerpo["definition"] == {
        "dataset": "patients",
        "columns": ["first_name", "last_name", "phone"],
        "filters": [{"field": "sex", "operator": "eq", "value": "F"}],
        "order_by": ["last_name"],
        "format": "xlsx",
    }


def test_la_definicion_dictada_se_puede_ejecutar(
    api_client, analista_a, pacientes_a, monkeypatch,
):
    """El puente entre las dos mitades: lo interpretado corre tal cual.

    Si esta prueba se rompe, la voz propone algo que el endpoint de siempre no
    acepta, que es la forma más fácil de que la característica se vea bien en
    la demostración y no sirva.
    """
    simular_modelo(monkeypatch, {
        "dataset": "patients",
        "columns": ["last_name"],
        "filters": [{"field": "sex", "operator": "eq", "value": "F"}],
    })
    cliente = autenticar(api_client, analista_a)

    definicion = dictar(cliente, "pacientes mujeres").json()["definition"]
    corrida = cliente.post(reverse("reporting:run"), definicion, format="json")

    assert corrida.status_code == 200
    filas = corrida.json()["rows"]
    assert sorted(fila[0] for fila in filas) == ["Cárdenas", "Álvarez"]


def test_el_resumen_lo_arma_el_sistema_con_las_etiquetas(
    api_client, analista_a, monkeypatch,
):
    """El resumen describe la definición saneada, no lo que dijo el modelo."""
    simular_modelo(monkeypatch, {
        "dataset": "patients",
        "columns": ["last_name"],
        "filters": [{"field": "sex", "operator": "eq", "value": "F"}],
    })

    cuerpo = dictar(
        autenticar(api_client, analista_a), "pacientes mujeres",
    ).json()

    # «F» es el valor guardado; en el resumen tiene que leerse la etiqueta.
    assert "Femenino" in cuerpo["spoken_summary"]
    assert "Apellidos" in cuerpo["spoken_summary"]


# --------------------------------------------------------------------------
#  Lo que no puede pasar
# --------------------------------------------------------------------------
def test_la_voz_no_presta_permisos(api_client, org_a, user_a, monkeypatch):
    """Quien no puede ver la bitácora no la obtiene dictándola.

    El modelo recibe un catálogo filtrado por permisos, así que ni siquiera
    debería nombrarla; la prueba simula que la nombra igual —un modelo puede
    devolver cualquier cosa— y comprueba que el saneado la rechaza.
    """
    dar_rol(user_a, org_a, "analista", "Analista", PERMISOS_ANALISTA)
    simular_modelo(monkeypatch, {"dataset": "audit", "columns": ["action"]})

    cuerpo = dictar(
        autenticar(api_client, user_a), "la bitácora de ayer",
    ).json()

    assert cuerpo["understood"] is False
    assert cuerpo["definition"] is None
    assert any("audit" in texto for texto in cuerpo["unresolved"])


def test_el_catalogo_del_prompt_sale_filtrado_por_permisos(
    api_client, org_a, user_a, monkeypatch,
):
    """La bitácora no viaja al proveedor si quien habla no puede leerla."""
    dar_rol(user_a, org_a, "analista", "Analista", PERMISOS_ANALISTA)
    prompts = []
    simular_modelo(monkeypatch, {"dataset": "patients"}, registro=prompts)

    dictar(autenticar(api_client, user_a), "pacientes")

    assert "## patients" in prompts[0]
    assert "## audit" not in prompts[0]


def test_una_columna_inventada_se_descarta_y_se_avisa(
    api_client, analista_a, monkeypatch,
):
    """El defecto clásico: aceptar lo que no existe y devolver otra cosa."""
    simular_modelo(monkeypatch, {
        "dataset": "patients",
        "columns": ["last_name", "obra_social"],
    })

    cuerpo = dictar(
        autenticar(api_client, analista_a),
        "pacientes con apellido y obra social",
    ).json()

    assert cuerpo["understood"] is True
    assert cuerpo["definition"]["columns"] == ["last_name"]
    assert any("obra_social" in texto for texto in cuerpo["unresolved"])


def test_un_filtro_con_operador_invalido_no_se_aplica(
    api_client, analista_a, monkeypatch,
):
    """«contiene» no existe para un booleano: se descarta, no se traduce."""
    simular_modelo(monkeypatch, {
        "dataset": "patients",
        "filters": [{"field": "is_active", "operator": "contains",
                     "value": True}],
    })

    cuerpo = dictar(autenticar(api_client, analista_a), "pacientes activos").json()

    assert cuerpo["definition"]["filters"] == []
    assert cuerpo["unresolved"]


def test_sin_proveedor_degrada_y_no_inventa_filtros(
    api_client, analista_a, monkeypatch,
):
    """Sin Gemini se adivina el conjunto y nada más."""
    monkeypatch.setattr(voice.settings, "ASSISTANT_CHAT_PROVIDER", "local")
    monkeypatch.setattr(voice.settings, "GEMINI_API_KEY", "")

    cuerpo = dictar(
        autenticar(api_client, analista_a),
        "pacientes dados de alta en septiembre",
    ).json()

    assert cuerpo["generated_by"] == "plantilla"
    assert cuerpo["understood"] is True
    assert cuerpo["definition"]["dataset"] == "patients"
    # Lo importante: «septiembre» no se convirtió en un filtro adivinado.
    assert cuerpo["definition"]["filters"] == []


def test_si_el_proveedor_falla_no_se_rompe_el_endpoint(
    api_client, analista_a, monkeypatch,
):
    def explota(prompt):
        raise RuntimeError("cuota agotada")

    monkeypatch.setattr(voice, "_call_model", explota)
    monkeypatch.setattr(voice.settings, "ASSISTANT_CHAT_PROVIDER", "gemini")
    monkeypatch.setattr(voice.settings, "GEMINI_API_KEY", "clave-de-prueba")

    respuesta = dictar(autenticar(api_client, analista_a), "pacientes")

    assert respuesta.status_code == 200
    assert respuesta.json()["generated_by"] == "plantilla"


def test_lo_que_no_se_entiende_se_dice(api_client, analista_a, monkeypatch):
    simular_modelo(monkeypatch, {"dataset": "", "unresolved": ["ventas"]})

    cuerpo = dictar(autenticar(api_client, analista_a), "las ventas del mes").json()

    assert cuerpo["understood"] is False
    assert cuerpo["definition"] is None
    assert cuerpo["spoken_summary"]


def test_sin_permiso_de_reportes_no_se_puede_dictar(
    api_client, org_a, user_a, monkeypatch,
):
    dar_rol(user_a, org_a, "mirador", "Mirador", ["patients.patient.read"])
    simular_modelo(monkeypatch, {"dataset": "patients"})

    assert dictar(autenticar(api_client, user_a), "pacientes").status_code == 403


# --------------------------------------------------------------------------
#  Aislamiento y bitácora
# --------------------------------------------------------------------------
def test_el_reporte_dictado_sale_de_la_organizacion_de_quien_habla(
    api_client, org_a, org_b, user_a, user_b, monkeypatch,
):
    """El de la organización B no ve a los pacientes de la A ni dictando."""
    dar_rol(user_a, org_a, "analista", "Analista", PERMISOS_ANALISTA)
    dar_rol(user_b, org_b, "analista", "Analista", PERMISOS_ANALISTA)
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, first_name="Ana", last_name="Álvarez",
            document_number="9001", sex="F",
        )
    simular_modelo(monkeypatch, {"dataset": "patients", "columns": ["last_name"]})

    cliente_b = autenticar(api_client, user_b)
    definicion = dictar(cliente_b, "pacientes").json()["definition"]
    filas = cliente_b.post(
        reverse("reporting:run"), definicion, format="json",
    ).json()["rows"]

    assert filas == []


def test_queda_asiento_en_la_bitacora_sin_la_frase_dictada(
    api_client, org_a, analista_a, monkeypatch,
):
    """Se audita el hecho, no el texto: puede nombrar a un paciente."""
    simular_modelo(monkeypatch, {"dataset": "patients"})

    dictar(autenticar(api_client, analista_a), "pacientes de apellido Álvarez")

    # Dentro del contexto de la organización: la bitácora tiene RLS, y leerla
    # sin contexto devuelve cero filas, que es lo que corresponde.
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(action=Action.REPORT_VOICE).first()

    assert asiento is not None
    assert asiento.detail["dataset"] == "patients"
    assert asiento.detail["understood"] is True
    assert "Álvarez" not in str(asiento.detail)
