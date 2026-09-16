"""US-31, US-32 y US-34 — El asistente de orientación.

Las tres piezas que pide el reparto —indexar, recuperar, responder— y la
barrera de seguridad de US-34.

**La prueba que justifica todo lo demás** es
``test_la_recuperacion_no_cruza_organizaciones``. El reparto lo dice: «el
riesgo del chatbot no es que responda mal, es que responda con datos de otro
inquilino». Una búsqueda vectorial mal acotada no falla: contesta, y contesta
con el catálogo del vecino.

Todas corren con el proveedor **local** de embeddings, sin red y sin clave. No
es una limitación de las pruebas: es el modo en que el asistente tiene que
poder funcionar en la máquina de cualquiera del equipo y en la demostración.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog
from accounts.tokens import tokens_for_user
from assistant import embeddings, generation, retrieval, triage
from assistant.models import KnowledgeChunk
from audit.actions import Action
from catalog.models import Branch, BranchHours, Specialty
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

PERMISOS_PACIENTE_IA = ["assistant.query.create"]


@pytest.fixture(autouse=True)
def sin_clave(monkeypatch, settings):
    """Fuerza el proveedor local en todas las pruebas de este archivo.

    Sin esto, una máquina con ``OPENAI_API_KEY`` en el entorno correría las
    pruebas contra la API de verdad: lentas, con costo, y con resultados que
    cambian entre corridas. Un test que depende de un servicio externo no es un
    test.
    """
    settings.OPENAI_API_KEY = ""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert embeddings.provider_name() == embeddings.LOCAL


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


# Las descripciones traen los motivos de consulta con las palabras de quien
# consulta, que es la regla que quedó escrita en `seed_catalog`.
CATALOGO = [
    ("Cardiología",
     "Corazón y sistema circulatorio. Motivos frecuentes de consulta: dolor "
     "en el pecho, palpitaciones, presión alta, hinchazón de piernas y "
     "tobillos, colesterol alto."),
    ("Pediatría",
     "Salud de niñas y niños. Motivos frecuentes de consulta: fiebre en "
     "bebés y chicos, tos, otitis y dolor de oído, vacunas, control de "
     "crecimiento."),
    ("Dermatología",
     "Piel, cabello y uñas. Motivos frecuentes de consulta: manchas en la "
     "piel, lunares, acné y granos, caída del cabello, picazón y ronchas."),
]


@pytest.fixture
def catalogo_a(db, org_a):
    with tenant_context(org_a.id):
        for nombre, descripcion in CATALOGO:
            Specialty.objects.create(
                organization=org_a, name=nombre, description=descripcion,
            )
        sucursal = Branch.objects.create(
            organization=org_a, name="Sede Norte",
            address="Av. América 4500", phone="4-6600200",
        )
        for dia in range(5):
            BranchHours.objects.create(
                organization=org_a, branch=sucursal, weekday=dia,
                opens_at="08:00", closes_at="12:00",
            )
    return org_a


@pytest.fixture
def indexado_a(catalogo_a, org_a):
    """El catálogo de A, ya indexado. Es ``embed_catalog`` por dentro."""
    from django.core.management import call_command
    call_command("embed_catalog", organization=org_a.slug, verbosity=0)
    return org_a


@pytest.fixture
def paciente_ia(db, org_a, user_a):
    dar_rol(user_a, org_a, "paciente_ia", "Paciente", PERMISOS_PACIENTE_IA)
    return user_a


def preguntar(api_client, texto, **extra):
    return api_client.post(
        reverse("assistant:suggest"), {"question": texto, **extra},
        format="json",
    )


# --------------------------------------------------------------------------
#  Pieza 1: indexación
# --------------------------------------------------------------------------
def test_indexar_arma_un_fragmento_por_cosa_preguntable(indexado_a, org_a):
    """La regla de granularidad del corpus: un fragmento = una cosa sobre la
    que alguien puede preguntar."""
    with tenant_context(org_a.id):
        titulos = set(
            KnowledgeChunk.objects
            .filter(source_type=KnowledgeChunk.Source.SPECIALTY)
            .values_list("title", flat=True)
        )
        # `list(...)` y no el QuerySet: un QuerySet es perezoso y se evaluaría
        # DESPUÉS de salir del contexto, cuando RLS ya devuelve cero filas.
        # Es la trampa que el apartado 5 de las convenciones describe, y caer
        # en ella acá daba «0 == 1» sin ninguna pista de por qué.
        sucursales = list(
            KnowledgeChunk.objects.filter(
                source_type=KnowledgeChunk.Source.BRANCH,
            )
        )

    assert titulos == {"Cardiología", "Pediatría", "Dermatología"}
    assert len(sucursales) == 1
    # El horario va DENTRO del fragmento de la sucursal: «¿a qué hora abre la
    # Sede Norte?» es una sola pregunta.
    assert "08:00" in sucursales[0].content
    assert "lunes" in sucursales[0].content


def test_reindexar_reemplaza_y_no_acumula(indexado_a, org_a):
    """Sin la restricción de unicidad, correr el comando dos veces duplica el
    corpus y la respuesta cita dos veces el mismo texto."""
    from django.core.management import call_command

    with tenant_context(org_a.id):
        antes = KnowledgeChunk.objects.count()

    call_command("embed_catalog", organization=org_a.slug, verbosity=0)

    with tenant_context(org_a.id):
        assert KnowledgeChunk.objects.count() == antes


def test_lo_que_sale_del_catalogo_sale_del_indice(indexado_a, org_a):
    """Una especialidad dada de baja no se puede seguir sugiriendo: sería
    mandar al paciente a pedir una ficha que no existe."""
    from django.core.management import call_command

    with tenant_context(org_a.id):
        Specialty.objects.filter(name="Dermatología").update(is_active=False)

    call_command("embed_catalog", organization=org_a.slug, verbosity=0)

    with tenant_context(org_a.id):
        titulos = set(
            KnowledgeChunk.objects.values_list("title", flat=True),
        )
    assert "Dermatología" not in titulos
    assert "Cardiología" in titulos


# --------------------------------------------------------------------------
#  Pieza 2: recuperación — y el aislamiento, que es lo que importa
# --------------------------------------------------------------------------
def test_la_recuperacion_no_cruza_organizaciones(indexado_a, org_a, org_b):
    """**La prueba que justifica la app entera.**

    B indexa una especialidad con un nombre inconfundible. Una consulta desde
    A que la nombra literalmente no tiene que recuperarla: si la recuperara, el
    asistente de A leería el catálogo de B en voz alta y nadie lo notaría,
    porque la respuesta se vería perfectamente razonable.
    """
    from django.core.management import call_command

    with tenant_context(org_b.id):
        Specialty.objects.create(
            organization=org_b, name="Traumatología del vecino",
            description="Fracturas, esguinces y lesiones deportivas.",
        )
    call_command("embed_catalog", organization=org_b.slug, verbosity=0)

    with tenant_context(org_a.id):
        fragmentos = retrieval.search(
            org_a, "fracturas esguinces y lesiones deportivas del vecino",
        )

    titulos = [f.title for f in fragmentos]
    assert "Traumatología del vecino" not in titulos


def test_un_sintoma_recupera_su_especialidad(indexado_a, org_a):
    with tenant_context(org_a.id):
        fragmentos = retrieval.search(
            org_a, "se me cae mucho el cabello y tengo manchas en la piel",
        )
    assert fragmentos
    assert fragmentos[0].title == "Dermatología"
    assert fragmentos[0].rank == 1


def test_una_pregunta_administrativa_recupera_la_sucursal(indexado_a, org_a):
    """US-32 sobre el mismo índice y el mismo endpoint."""
    with tenant_context(org_a.id):
        fragmentos = retrieval.search(org_a, "a qué hora abre la Sede Norte")
    assert fragmentos[0].source_type == KnowledgeChunk.Source.BRANCH
    assert fragmentos[0].title == "Sede Norte"


def test_una_pregunta_ajena_al_catalogo_no_recupera_nada(indexado_a, org_a):
    """El umbral es lo que impide inventar.

    Sin él, esta pregunta recupera los cinco fragmentos menos malos y el
    modelo responde como si vinieran al caso.
    """
    with tenant_context(org_a.id):
        fragmentos = retrieval.search(
            org_a, "quiero saber el precio de un pasaje en avión a Madrid",
        )
    assert fragmentos == []


def test_se_puede_acotar_la_busqueda_a_un_tipo_de_fuente(indexado_a, org_a):
    """US-32: el asistente de mostrador ya sabe de qué está preguntando."""
    with tenant_context(org_a.id):
        fragmentos = retrieval.search(
            org_a, "Sede Norte horario",
            source_types=[KnowledgeChunk.Source.BRANCH],
        )
    assert all(f.source_type == KnowledgeChunk.Source.BRANCH
               for f in fragmentos)


def test_los_fragmentos_de_otro_proveedor_son_invisibles(indexado_a, org_a):
    """Dos modelos producen vectores incomparables del mismo tamaño.

    Mezclarlos no da error: da resultados absurdos que parecen un problema de
    calidad del corpus. Por eso la búsqueda filtra por proveedor.
    """
    with tenant_context(org_a.id):
        KnowledgeChunk.objects.update(provider="otro-modelo")
        fragmentos = retrieval.search(org_a, "manchas en la piel y lunares")
    assert fragmentos == []


# --------------------------------------------------------------------------
#  Pieza 3: la respuesta, y lo que la sostiene
# --------------------------------------------------------------------------
def test_la_respuesta_viaja_con_los_fragmentos_que_la_sustentan(
    api_client, indexado_a, paciente_ia,
):
    """Punto 3 de la historia: «sin esa lista no hay cómo demostrar que no
    alucinó»."""
    respuesta = preguntar(
        autenticar(api_client, paciente_ia),
        "mi hija de tres años tiene fiebre y tos",
    )
    assert respuesta.status_code == 200

    assert respuesta.data["fragments"]
    primero = respuesta.data["fragments"][0]
    assert primero["title"] == "Pediatría"
    # Viaja el texto completo del fragmento: es lo que permite comprobar cada
    # afirmación de la respuesta contra su origen.
    assert "fiebre" in primero["content"]
    assert primero["rank"] == 1
    assert "distance" in primero


def test_la_sugerencia_trae_el_uuid_de_la_especialidad(
    api_client, indexado_a, org_a, paciente_ia,
):
    """La pantalla tiene que poder ofrecer «reservar con esta especialidad».

    Un nombre casi correcto no encuentra nada al reservar, y el error aparece
    dos pantallas después.
    """
    respuesta = preguntar(
        autenticar(api_client, paciente_ia),
        "tengo palpitaciones y la presión alta",
    )
    sugerida = respuesta.data["specialty"]
    assert sugerida["name"] == "Cardiología"

    with tenant_context(org_a.id):
        assert Specialty.objects.filter(id=sugerida["id"]).exists()


def test_sin_contexto_el_asistente_dice_que_no_sabe(
    api_client, indexado_a, paciente_ia,
):
    """Nunca una respuesta inventada. Es la regla 1 del prompt y también del
    backend, que es el que se puede probar."""
    respuesta = preguntar(
        autenticar(api_client, paciente_ia),
        "cuánto cuesta un pasaje en avión a Madrid",
    )
    assert respuesta.data["fragments"] == []
    assert respuesta.data["specialty"] is None
    assert respuesta.data["answer"]["text"] == generation.SIN_CONTEXTO


def test_la_respuesta_dice_si_la_redacto_un_modelo_o_el_sistema(
    api_client, indexado_a, paciente_ia,
):
    """Sin proveedor de lenguaje no se finge una charla.

    Se arma por plantilla y **se dice**: cada oración sale de un fragmento que
    viaja en la misma respuesta.
    """
    respuesta = preguntar(
        autenticar(api_client, paciente_ia), "manchas en la piel y lunares",
    )
    assert respuesta.data["answer"]["source"] == generation.TEMPLATE
    assert respuesta.data["provider"] == embeddings.LOCAL
    assert "sin un modelo de lenguaje" in respuesta.data["answer"]["text"]


def test_no_se_ofrecen_alternativas_que_no_compiten(indexado_a, org_a):
    """Pasar el umbral no es empatar.

    Ofrecer Ginecología como alternativa a alguien con dolor de pecho —con el
    mismo tono con el que se acertó Cardiología— es peor que no ofrecer nada.
    """
    with tenant_context(org_a.id):
        fragmentos = retrieval.search(org_a, "tengo dolor en el pecho")
    texto = generation.answer("tengo dolor en el pecho", fragmentos)["text"]

    assert "Cardiología" in texto
    if "También podría corresponder" in texto:
        # Si hay alternativa, tiene que estar de verdad cerca de la primera.
        especialidades = [
            f for f in fragmentos
            if f.source_type == KnowledgeChunk.Source.SPECIALTY
        ]
        assert (especialidades[1].distance - especialidades[0].distance
                <= generation.ALTERNATIVE_MARGIN)


# --------------------------------------------------------------------------
#  US-34 — la barrera de seguridad
# --------------------------------------------------------------------------
@pytest.mark.parametrize("descripcion, motivo", [
    ("tengo un dolor fuerte en el pecho desde hace una hora", "dolor_de_pecho"),
    ("no puedo respirar bien y me falta el aire", "dificultad_para_respirar"),
    ("mi papá se desmayó y no reacciona", "perdida_de_conciencia"),
    ("mi mamá tiene la boca torcida y no puede hablar", "signos_de_acv"),
    ("mi hermano se cortó y no para de sangrar", "sangrado_abundante"),
    ("mi hijo se tomó unas pastillas del botiquín", "intoxicacion"),
    ("está convulsionando hace un minuto", "convulsiones"),
    ("no quiero vivir más, quiero matarme", "riesgo_autolesion"),
])
def test_una_urgencia_se_deriva_a_emergencia(descripcion, motivo):
    """La capa del backend, que es la que se puede probar.

    La del prompt sola no sirve: se la puede rodear conversando.
    """
    evaluacion = triage.evaluate(descripcion)
    assert evaluacion.is_emergency is True
    assert motivo in evaluacion.reasons


@pytest.mark.parametrize("descripcion", [
    "quiero un control de rutina y análisis de sangre",
    "se me cae el cabello desde hace meses",
    "a qué hora abre la Sede Norte los martes",
    "necesito renovar una receta",
])
def test_una_consulta_comun_no_se_deriva(descripcion):
    """La otra mitad: derivar todo a emergencias es no derivar nada."""
    assert triage.evaluate(descripcion).is_emergency is False


def test_la_derivacion_corta_el_flujo_de_reserva(
    api_client, indexado_a, paciente_ia,
):
    """US-34 dice que el asistente «corta el flujo de reserva».

    Devolver igual una especialidad reservable sería no cortarlo: la pantalla
    mostraría el botón de reservar justo debajo del aviso de ir a emergencias.
    """
    respuesta = preguntar(
        autenticar(api_client, paciente_ia),
        "tengo un dolor muy fuerte en el pecho y me falta el aire",
    )
    assert respuesta.status_code == 200
    assert respuesta.data["triage"]["is_emergency"] is True
    assert respuesta.data["specialty"] is None
    assert respuesta.data["answer"]["text"] == triage.MESSAGE
    assert "emergencias" in respuesta.data["answer"]["text"]


def test_la_derivacion_no_depende_del_indice_ni_del_proveedor(
    api_client, org_a, paciente_ia,
):
    """Sale aunque no haya nada indexado.

    Si la detección dependiera de la respuesta del modelo, una caída del
    proveedor dejaría a alguien con un dolor de pecho sin la derivación. Por
    eso corre **antes** de recuperar nada.
    """
    with tenant_context(org_a.id):
        assert KnowledgeChunk.objects.count() == 0

    respuesta = preguntar(
        autenticar(api_client, paciente_ia),
        "mi papá se desmayó y no reacciona",
    )
    assert respuesta.data["triage"]["is_emergency"] is True
    assert respuesta.data["fragments"] == []


def test_la_derivacion_no_diagnostica(api_client, indexado_a, paciente_ia):
    """El asistente no nombra enfermedades. Decir «puede ser un infarto»
    sería diagnosticar, que es lo que las reglas prohíben."""
    respuesta = preguntar(
        autenticar(api_client, paciente_ia),
        "tengo un dolor fuerte en el pecho",
    )
    texto = respuesta.data["answer"]["text"].lower()
    for enfermedad in ("infarto", "acv", "angina", "embolia", "trombosis"):
        assert enfermedad not in texto


# --------------------------------------------------------------------------
#  Permisos, entrada y bitácora
# --------------------------------------------------------------------------
def test_sin_permiso_no_se_consulta_el_asistente(
    api_client, org_a, user_a, indexado_a,
):
    dar_rol(user_a, org_a, "sin_ia", "Sin IA", ["catalog.branch.read"])
    respuesta = preguntar(autenticar(api_client, user_a), "dolor de cabeza")
    assert respuesta.status_code == 403


def test_una_pregunta_de_dos_palabras_se_rechaza(
    api_client, indexado_a, paciente_ia,
):
    """El proveedor local descarta las palabras cortas y las vacías, así que
    «hola» produce el vector nulo y la búsqueda devuelve cualquier cosa
    ordenada al azar. Mejor pedir que escriba."""
    respuesta = preguntar(autenticar(api_client, paciente_ia), "hola")
    assert respuesta.status_code == 400
    assert "question" in respuesta.data


def test_la_consulta_se_audita_sin_guardar_los_sintomas(
    api_client, org_a, indexado_a, paciente_ia,
):
    """Quien le cuenta sus síntomas a un chatbot está escribiendo información
    de salud. Una bitácora que la copie es una historia clínica paralela sin
    ninguna de las protecciones de una.
    """
    sintoma = "se me cae el cabello y tengo manchas raras en la piel"
    preguntar(autenticar(api_client, paciente_ia), sintoma)

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(
            action=Action.ASSISTANT_QUERY,
        ).first()

    assert asiento is not None
    assert asiento.detail["question_length"] == len(sintoma)
    assert asiento.detail["specialty"] == "Dermatología"
    assert asiento.detail["provider"] == embeddings.LOCAL
    # El texto no está en ninguna parte del asiento.
    import json
    assert "cabello" not in json.dumps(asiento.detail)


def test_la_derivacion_a_emergencia_queda_registrada(
    api_client, org_a, indexado_a, paciente_ia,
):
    """Es lo único que alguien podría necesitar reconstruir después."""
    preguntar(
        autenticar(api_client, paciente_ia),
        "mi papá se desmayó y no reacciona",
    )
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(
            action=Action.ASSISTANT_QUERY,
        ).first()

    assert asiento.detail["emergency"] is True
    assert "perdida_de_conciencia" in asiento.detail["emergency_reasons"]


# --------------------------------------------------------------------------
#  El estado del índice
# --------------------------------------------------------------------------
def test_el_estado_distingue_indice_vacio_de_respuesta_vacia(
    api_client, catalogo_a, paciente_ia,
):
    """Las dos formas de contestar «no sé» son indistinguibles desde afuera.

    Es lo primero que hay que mirar cuando el asistente no encuentra nada.
    """
    cliente = autenticar(api_client, paciente_ia)

    antes = cliente.get(reverse("assistant:status"))
    assert antes.data["indexed"] is False
    assert antes.data["chunks"] == 0

    from django.core.management import call_command
    call_command("embed_catalog", organization=catalogo_a.slug, verbosity=0)

    despues = cliente.get(reverse("assistant:status"))
    assert despues.data["indexed"] is True
    assert despues.data["chunks"] == 4
    assert despues.data["provider"] == embeddings.LOCAL
    assert despues.data["by_source"]["specialty"]["chunks"] == 3


def test_el_estado_avisa_de_los_fragmentos_de_otro_proveedor(
    api_client, indexado_a, org_a, paciente_ia,
):
    """Con `chunks` en cero y `stale_chunks` alto, el diagnóstico es «se
    cambió de modelo y falta reindexar» — imposible de hacer sin este dato."""
    with tenant_context(org_a.id):
        KnowledgeChunk.objects.update(provider="otro-modelo")

    respuesta = autenticar(api_client, paciente_ia).get(
        reverse("assistant:status"),
    )
    assert respuesta.data["indexed"] is False
    assert respuesta.data["chunks"] == 0
    assert respuesta.data["stale_chunks"] == 4
