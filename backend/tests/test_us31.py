"""US-31 — Sugerencia de especialidad por síntomas (RAG sobre pgvector).

Las pruebas corren con ``ASSISTANT_EMBEDDING_PROVIDER=local``: el proveedor
determinista de ``assistant/embeddings.py``. No es una comodidad, es un
requisito. Una prueba que llama a Gemini depende de la red, de la cuota y de
que el modelo no cambie de opinión entre dos corridas — tres formas de que la
suite falle sin que nadie haya roto nada.

Lo que estas pruebas verifican **no es la calidad del modelo**; es el
cableado: que se recupere sólo dentro de la organización, que la respuesta
traiga su respaldo, que una urgencia corte el flujo y que sin permiso no se
entre. Eso sí tiene que valer con cualquier proveedor.

⚠️ **Necesitan pgvector en la base de pruebas.** El tipo `vector` es parte del
esquema: sin la extensión, la migración 0001 se detiene con el mensaje que
explica cómo instalarla. Ver docs/entorno/sin-docker.md.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from assistant.indexing import index_specialties
from assistant.models import CatalogFragment, SourceType
from catalog.models import Specialty
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def proveedor_local(settings):
    """Fuerza el proveedor determinista en toda la suite.

    Las fixtures que indexan lo piden explícitamente, además de que sea
    `autouse`: el catálogo se vectoriza dentro de ellas, así que el proveedor
    tiene que estar elegido **antes**, no da lo mismo el orden.
    """
    settings.ASSISTANT_EMBEDDING_PROVIDER = "local"
    settings.ASSISTANT_CHAT_PROVIDER = "local"
    # El mismo valor que settings.py elige para el proveedor local. Se fija
    # acá explícitamente para que estas pruebas no cambien de significado si
    # mañana se ajusta el valor por omisión.
    settings.ASSISTANT_MIN_SIMILARITY = 0.12


CARDIOLOGIA = (
    "Corazón, presión arterial y sistema circulatorio. "
    "Motivos de consulta frecuentes: dolor u opresión en el pecho, "
    "palpitaciones, falta de aire al subir escaleras, presión alta."
)
DERMATOLOGIA = (
    "Piel, cabello y uñas. "
    "Motivos de consulta frecuentes: manchas en la piel, lunares que cambian "
    "de color, acné y granos, picazón, caída del cabello."
)
# El catálogo de la otra organización no comparte una sola palabra con el de
# la primera. Es a propósito: si la prueba de aislamiento fallara por un
# empate de vocabulario en vez de por una fuga, no probaría nada.
ODONTOLOGIA = (
    "Dientes, encías y boca. "
    "Motivos de consulta frecuentes: caries, dolor de muela, limpieza "
    "dental, sangrado de encías, ortodoncia."
)


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


@pytest.fixture
def catalogo_indexado_a(db, org_a, proveedor_local):
    with tenant_context(org_a.id):
        Specialty.objects.create(
            organization=org_a, name="Cardiología", description=CARDIOLOGIA,
        )
        Specialty.objects.create(
            organization=org_a, name="Dermatología", description=DERMATOLOGIA,
        )
        index_specialties(org_a)
    return org_a


@pytest.fixture
def catalogo_indexado_b(db, org_b, proveedor_local):
    with tenant_context(org_b.id):
        Specialty.objects.create(
            organization=org_b, name="Odontología", description=ODONTOLOGIA,
        )
        index_specialties(org_b)
    return org_b


@pytest.fixture
def paciente_a(db, org_a, user_a):
    return dar_rol(
        user_a, org_a, "patient", "Paciente", ["assistant.suggest.use"],
    ) and user_a


@pytest.fixture
def paciente_b(db, org_b, user_b):
    return dar_rol(
        user_b, org_b, "patient", "Paciente", ["assistant.suggest.use"],
    ) and user_b


def preguntar(api_client, user, texto):
    return autenticar(api_client, user).post(
        reverse("assistant:suggest"), {"question": texto}, format="json",
    )


# --------------------------------------------------------------------------
#  El camino feliz
# --------------------------------------------------------------------------

def test_describir_un_sintoma_devuelve_la_especialidad_que_corresponde(
    api_client, catalogo_indexado_a, paciente_a,
):
    """El síntoma no puede ser uno que la barrera de emergencia corte.

    Esta prueba pedía Cardiología para "tengo dolor en el pecho al subir
    escaleras", que es una señal de ``triage.py``: la barrera derivaba antes
    de recuperar nada y la prueba fallaba contra su propio diseño. El dolor
    de pecho de esfuerzo se deriva —ver la prueba de más abajo—, así que el
    camino feliz se describe con un motivo cardiológico que no es urgencia.
    """
    respuesta = preguntar(
        api_client, paciente_a, "tengo la presión alta y palpitaciones",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["specialty"]["name"] == "Cardiología"


def test_la_respuesta_trae_los_fragmentos_que_la_respaldan(
    api_client, catalogo_indexado_a, paciente_a,
):
    """Sin esta lista no hay forma de demostrar que el asistente no alucinó.

    Es el criterio con el que se muestra la historia el 16/09, así que es
    parte del contrato del endpoint y no información de depuración.
    """
    cuerpo = preguntar(
        api_client, paciente_a, "me salieron manchas en la piel",
    ).json()

    assert cuerpo["fragments"], "la respuesta tiene que venir con su respaldo"
    for fragmento in cuerpo["fragments"]:
        assert fragmento["text"]
        assert 0.0 <= fragmento["similarity"] <= 1.0
    # El respaldo tiene que sostener lo que se sugirió, no ser cualquier cosa.
    assert any(
        f["source_name"] == cuerpo["specialty"]["name"]
        for f in cuerpo["fragments"]
    )


def test_lo_que_no_esta_en_el_catalogo_no_inventa_una_especialidad(
    api_client, catalogo_indexado_a, paciente_a,
):
    """Con cinco especialidades siempre hay una "menos lejana". El umbral es
    lo que evita que esa se convierta en una recomendación médica."""
    cuerpo = preguntar(
        api_client, paciente_a, "cuanto sale alquilar un departamento",
    ).json()

    assert cuerpo["specialty"] is None
    assert cuerpo["fragments"] == []


# --------------------------------------------------------------------------
#  Aislamiento — criterio 4 de la DoD y regla 9 del Sprint 2
# --------------------------------------------------------------------------

@pytest.mark.isolation
def test_la_misma_pregunta_en_dos_organizaciones_devuelve_catalogos_distintos(
    api_client, catalogo_indexado_a, catalogo_indexado_b, paciente_a, paciente_b,
):
    """La prueba de la sección 2 del reparto, la que se muestra el 16/09.

    A tiene Cardiología y Dermatología; B sólo Odontología. La misma pregunta
    no puede cruzar de una a la otra.
    """
    en_a = preguntar(api_client, paciente_a, "me duele una muela").json()
    en_b = preguntar(api_client, paciente_b, "me duele una muela").json()

    # B sí tiene con qué contestar.
    assert en_b["specialty"]["name"] == "Odontología"
    # A no, y no puede tomarlo prestado de B.
    nombres_en_a = {f["source_name"] for f in en_a["fragments"]}
    assert "Odontología" not in nombres_en_a
    if en_a["specialty"] is not None:
        assert en_a["specialty"]["name"] != "Odontología"


@pytest.mark.isolation
def test_los_fragmentos_de_una_organizacion_no_se_ven_desde_la_otra(
    catalogo_indexado_a, catalogo_indexado_b, org_a, org_b,
):
    """El mismo aislamiento, pero a nivel de tabla: es RLS quien lo garantiza,
    no la consulta que escribimos en `retrieval.py`."""
    with tenant_context(org_a.id):
        textos_a = set(CatalogFragment.objects.values_list("text", flat=True))
    with tenant_context(org_b.id):
        textos_b = set(CatalogFragment.objects.values_list("text", flat=True))

    assert textos_a and textos_b
    assert not textos_a & textos_b


# --------------------------------------------------------------------------
#  Barrera de emergencia — semilla de US-34
# --------------------------------------------------------------------------

def test_una_urgencia_corta_el_flujo_y_no_sugiere_reservar_ficha(
    api_client, catalogo_indexado_a, paciente_a,
):
    cuerpo = preguntar(
        api_client, paciente_a, "me duele el pecho y no puedo respirar",
    ).json()

    assert cuerpo["emergency"] is True
    assert cuerpo["specialty"] is None, (
        "una urgencia no se contesta con una especialidad para reservar"
    )
    assert "emergencias" in cuerpo["answer"].lower()


@pytest.mark.parametrize("pregunta", [
    "me duele el pecho cuando subo escaleras",
    "tengo dolor en el pecho al subir escaleras",
    "siento presión en el pecho",
])
def test_las_formas_de_decir_dolor_de_pecho_derivan_todas(
    api_client, catalogo_indexado_a, paciente_a, pregunta,
):
    """Tres maneras de contar el mismo síntoma, una sola respuesta.

    La coincidencia de ``triage.py`` es por subcadena, así que cada forma de
    decirlo hay que ponerla. Sin esta prueba, "me duele el pecho" contestaba
    Cardiología y "dolor en el pecho" derivaba a emergencias: el paciente
    recibía una respuesta distinta según cómo redactara.
    """
    cuerpo = preguntar(api_client, paciente_a, pregunta).json()

    assert cuerpo["emergency"] is True, f"«{pregunta}» tendría que derivar"
    assert cuerpo["specialty"] is None


# --------------------------------------------------------------------------
#  Autorización
# --------------------------------------------------------------------------

def test_sin_el_permiso_del_asistente_no_se_entra(
    api_client, catalogo_indexado_a, org_a, user_a,
):
    dar_rol(user_a, org_a, "otro", "Sin asistente", ["catalog.specialty.read"])
    assert preguntar(api_client, user_a, "me duele la cabeza").status_code == 403


def test_sin_autenticar_no_se_entra(api_client, catalogo_indexado_a):
    respuesta = api_client.post(
        reverse("assistant:suggest"), {"question": "hola"}, format="json",
    )
    assert respuesta.status_code == 401


# --------------------------------------------------------------------------
#  Indexación
# --------------------------------------------------------------------------

def test_reindexar_reemplaza_los_fragmentos_en_vez_de_duplicarlos(
    catalogo_indexado_a, org_a,
):
    with tenant_context(org_a.id):
        antes = CatalogFragment.objects.count()
        index_specialties(org_a)
        despues = CatalogFragment.objects.count()

    assert antes == despues


def test_cada_fragmento_dice_de_que_especialidad_salio(
    catalogo_indexado_a, org_a,
):
    """Un fragmento que hay que ir a completar a otra tabla no sirve: el
    modelo de lenguaje lo lee solo, y el paciente también."""
    with tenant_context(org_a.id):
        textos = list(CatalogFragment.objects.values_list("text", flat=True))

    assert textos
    assert all(texto.startswith("Especialidad: ") for texto in textos)


def test_una_especialidad_dada_de_baja_no_queda_en_el_indice(org_a, proveedor_local):
    with tenant_context(org_a.id):
        activa = Specialty.objects.create(
            organization=org_a, name="Cardiología", description=CARDIOLOGIA,
        )
        Specialty.objects.create(
            organization=org_a, name="Dermatología",
            description=DERMATOLOGIA, is_active=False,
        )
        index_specialties(org_a)

        indexadas = set(
            CatalogFragment.objects
            .filter(source_type=SourceType.SPECIALTY)
            .values_list("source_id", flat=True)
        )

    assert indexadas == {activa.id}
