"""US-32 — Consultas administrativas al asistente.

Mismo endpoint, mismo índice y mismo proveedor determinista que
``test_us31.py``. Lo que se verifica es el cableado de la historia:

- que cada sede, servicio y política entre al índice en fragmentos que se
  bastan solos, y que reindexar no duplique;
- que una pregunta administrativa se conteste con el dato y **sin** sugerir
  especialidad, y que una de síntomas siga el camino de US-31;
- que lo administrativo tampoco cruce organizaciones;
- que la barrera de urgencias siga yendo primero.

No se prueba la calidad de la redacción de Gemini: con el proveedor local la
respuesta es el fragmento recuperado tal cual, que es justamente lo que deja
afirmar qué dato se usó.
"""

import datetime as dt
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.tokens import tokens_for_user
from assistant import generation
from assistant.corpus import describe_hours, format_price, policy_fragments
from assistant.indexing import index_administrative, index_specialties
from assistant.models import CatalogFragment, SourceType
from catalog.models import (
    Branch,
    BranchHours,
    Practitioner,
    PractitionerBranch,
    PractitionerSpecialty,
    Service,
    Specialty,
)
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def proveedor_local(settings):
    settings.ASSISTANT_EMBEDDING_PROVIDER = "local"
    settings.ASSISTANT_CHAT_PROVIDER = "local"
    settings.ASSISTANT_MIN_SIMILARITY = 0.12


def _hora(texto):
    return dt.time.fromisoformat(texto)


@pytest.fixture
def centro_a(db, org_a, proveedor_local):
    """Dos sedes con horarios distintos, quién atiende en cada una, dos
    servicios y una especialidad, todo indexado."""
    with tenant_context(org_a.id):
        norte = Branch.objects.create(
            organization=org_a, name="Sede Norte",
            address="Av. América 4500", phone="4-6600200",
        )
        sur = Branch.objects.create(
            organization=org_a, name="Sede Sur",
            address="Av. Panamericana Km 4", phone="4-6600300",
        )
        for weekday in range(5):
            BranchHours.objects.create(
                organization=org_a, branch=norte, weekday=weekday,
                opens_at=_hora("08:00"), closes_at=_hora("12:00"),
            )
            BranchHours.objects.create(
                organization=org_a, branch=norte, weekday=weekday,
                opens_at=_hora("14:00"), closes_at=_hora("18:00"),
            )
        # La Sur abre también los sábados: dos sedes con horarios
        # distintos es lo que permite afirmar que se recuperó la correcta.
        for weekday in range(6):
            BranchHours.objects.create(
                organization=org_a, branch=sur, weekday=weekday,
                opens_at=_hora("07:00"), closes_at=_hora("13:00"),
            )

        dermatologia = Specialty.objects.create(
            organization=org_a, name="Dermatología",
            description=(
                "Piel, cabello y uñas. Motivos de consulta frecuentes: "
                "manchas en la piel, lunares, acné, picazón."
            ),
        )
        juan = Practitioner.objects.create(
            organization=org_a, first_name="Juan", last_name="Pérez",
            license_number="MP-1003",
        )
        PractitionerSpecialty.objects.create(
            organization=org_a, practitioner=juan, specialty=dermatologia,
        )
        PractitionerBranch.objects.create(
            organization=org_a, practitioner=juan, branch=norte,
        )

        Service.objects.create(
            organization=org_a, name="Electrocardiograma",
            kind=Service.Kind.STUDY, price=Decimal("90"),
            preparation="No requiere ayuno. Venir sin cremas en el pecho.",
        )
        Service.objects.create(
            organization=org_a, name="Análisis de sangre",
            kind=Service.Kind.STUDY, price=Decimal("80"),
            preparation=(
                "Ayuno de 8 horas: no comer nada desde la noche anterior, "
                "sólo agua."
            ),
        )

        index_specialties(org_a)
        index_administrative(org_a)
    return {"org": org_a, "norte": norte, "sur": sur}


@pytest.fixture
def centro_b(db, org_b, proveedor_local):
    with tenant_context(org_b.id):
        altiplano = Branch.objects.create(
            organization=org_b, name="Sede Altiplano",
            address="Calle Murillo 77", phone="2-2400100",
        )
        index_administrative(org_b)
    return {"org": org_b, "altiplano": altiplano}


@pytest.fixture
def paciente_a(db, org_a, user_a):
    dar_rol(user_a, org_a, "patient", "Paciente", ["assistant.suggest.use"])
    return user_a


def preguntar(user, texto):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return client.post(
        reverse("assistant:suggest"), {"question": texto}, format="json",
    )


# --------------------------------------------------------------------------
#  El corpus
# --------------------------------------------------------------------------

def test_el_horario_se_agrupa_por_tramos_de_dias_iguales(centro_a):
    with tenant_context(centro_a["org"].id):
        horas = list(BranchHours.objects.filter(branch=centro_a["norte"]))
    texto = describe_hours(horas)
    assert texto.startswith("De lunes a viernes abre de 08:00 a 12:00 y de 14:00 a 18:00")
    assert "sábado y domingo no abre" in texto


def test_el_precio_se_escribe_como_en_bolivia():
    assert format_price(Decimal("80"), "BOB") == "Bs 80"
    assert format_price(Decimal("80.50"), "BOB") == "Bs 80,50"


def test_la_politica_dice_lo_que_hace_us20_y_no_una_regla_inventada(org_a):
    texto = policy_fragments(org_a)[0]
    assert f"{org_a.cancellation_notice_hours} horas" in texto
    # Con menos aviso se cancela igual; lo que se pierde es la devolución.
    assert "se cancela igual" in texto


def test_cada_sede_entra_en_sus_propios_fragmentos_y_cada_uno_se_basta_solo(centro_a):
    with tenant_context(centro_a["org"].id):
        de_la_norte = list(
            CatalogFragment.objects.filter(
                source_type=SourceType.BRANCH, source_id=centro_a["norte"].id,
            ).values_list("text", flat=True)
        )
    # Contacto, horario y quién atiende: tres fragmentos, no uno.
    assert len(de_la_norte) == 3
    assert all(t.startswith("Sucursal: Sede Norte.") for t in de_la_norte)
    assert not any("Sede Sur" in t for t in de_la_norte)
    assert any("Juan Pérez (Dermatología)" in t for t in de_la_norte)


def test_reindexar_reescribe_y_no_duplica(centro_a):
    org = centro_a["org"]
    with tenant_context(org.id):
        antes = CatalogFragment.objects.count()
        resumen = index_administrative(org)
        index_administrative(org)
        assert CatalogFragment.objects.count() == antes
        # Las especialidades no las toca: son de index_specialties.
        assert CatalogFragment.objects.filter(
            source_type=SourceType.SPECIALTY,
        ).exists()
    assert resumen["branches"] == 2
    assert resumen["services"] == 2


# --------------------------------------------------------------------------
#  El endpoint
# --------------------------------------------------------------------------

def test_preguntar_el_horario_de_una_sede_devuelve_el_de_esa_sede(centro_a, paciente_a):
    respuesta = preguntar(paciente_a, "¿A qué hora abre la Sede Sur?")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["kind"] == "administrativa"
    assert datos["emergency"] is False
    assert datos["specialty"] is None
    assert datos["alternatives"] == []
    mejor = datos["fragments"][0]
    assert mejor["source_type"] == "branch"
    assert mejor["source_name"] == "Sede Sur"
    assert "07:00 a 13:00" in datos["answer"]


def test_preguntar_un_precio_devuelve_el_del_servicio(centro_a, paciente_a):
    datos = preguntar(paciente_a, "¿Cuánto cuesta el electrocardiograma?").json()
    assert datos["kind"] == "administrativa"
    assert datos["fragments"][0]["source_name"] == "Electrocardiograma"
    assert "Bs 90" in datos["answer"]


def test_preguntar_la_preparacion_devuelve_la_del_estudio(centro_a, paciente_a):
    datos = preguntar(
        paciente_a, "¿Tengo que ir en ayunas al análisis de sangre?",
    ).json()
    assert datos["kind"] == "administrativa"
    assert datos["fragments"][0]["source_name"] == "Análisis de sangre"
    assert "Ayuno de 8 horas" in datos["answer"]


def test_preguntar_como_cancelar_devuelve_la_politica(centro_a, paciente_a):
    datos = preguntar(
        paciente_a, "¿Con cuánta anticipación puedo cancelar mi ficha?",
    ).json()
    assert datos["kind"] == "administrativa"
    assert datos["fragments"][0]["source_type"] == "policy"
    assert "24 horas" in datos["answer"]


def test_un_sintoma_sigue_el_camino_de_us31_sin_evidencia_administrativa(
    centro_a, paciente_a,
):
    datos = preguntar(
        paciente_a, "Me salieron manchas en la piel y tengo picazón",
    ).json()
    assert datos["kind"] == "orientacion"
    assert datos["specialty"]["name"] == "Dermatología"
    assert all(f["source_type"] == "specialty" for f in datos["fragments"])


def test_lo_administrativo_tampoco_cruza_organizaciones(
    centro_a, centro_b, paciente_a,
):
    datos = preguntar(paciente_a, "¿Dónde queda la Sede Altiplano?").json()
    altiplano = str(centro_b["altiplano"].id)
    assert all(f["source_id"] != altiplano for f in datos["fragments"])
    assert "Murillo" not in datos["answer"]


def test_la_barrera_de_urgencia_va_antes_que_la_pregunta_administrativa(
    centro_a, paciente_a,
):
    datos = preguntar(
        paciente_a,
        "¿A qué hora abre la Sede Norte? Tengo un dolor de pecho muy fuerte "
        "y no puedo respirar",
    ).json()
    assert datos["emergency"] is True
    assert datos["fragments"] == []


# --------------------------------------------------------------------------
#  Con el modelo de lenguaje (simulado)
# --------------------------------------------------------------------------

class ModeloSimulado:
    def __init__(self, texto):
        self.texto = texto
        self.prompts = []

    def __call__(self, question, context, *, system_prompt=generation.SYSTEM_PROMPT):
        self.prompts.append(system_prompt)
        return self.texto


@pytest.fixture
def con_gemini(settings):
    settings.ASSISTANT_CHAT_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "clave-de-prueba"


def test_con_gemini_la_consulta_administrativa_usa_su_propio_prompt(
    centro_a, paciente_a, con_gemini, monkeypatch,
):
    simulado = ModeloSimulado("La Sede Sur abre de lunes a sábado de 07:00 a 13:00.")
    monkeypatch.setattr(generation, "_call_model", simulado)

    datos = preguntar(paciente_a, "¿A qué hora abre la Sede Sur?").json()
    assert datos["generated_by"] == "gemini"
    assert datos["answer"] == simulado.texto
    assert simulado.prompts == [generation.ADMINISTRATIVE_PROMPT]


def test_con_gemini_la_marca_de_urgencia_tambien_deriva_en_lo_administrativo(
    centro_a, paciente_a, con_gemini, monkeypatch,
):
    monkeypatch.setattr(
        generation, "_call_model", ModeloSimulado(generation.EMERGENCY_MARK),
    )
    datos = preguntar(paciente_a, "¿A qué hora abre la Sede Sur?").json()
    assert datos["emergency"] is True
    assert datos["fragments"] == []


# --------------------------------------------------------------------------
#  El modelo de datos
# --------------------------------------------------------------------------

def test_un_servicio_no_puede_colgar_de_la_especialidad_de_otra_organizacion(
    org_a, org_b,
):
    with tenant_context(org_b.id):
        ajena = Specialty.objects.create(organization=org_b, name="Odontología")
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError), transaction.atomic():
            Service.objects.create(
                organization=org_a, name="Limpieza", specialty_id=ajena.id,
            )


def test_un_precio_negativo_no_se_guarda(org_a):
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError), transaction.atomic():
            Service.objects.create(
                organization=org_a, name="Raro", price=Decimal("-1"),
            )


# --------------------------------------------------------------------------
#  El ABM de servicios y la reindexación (pantalla web)
# --------------------------------------------------------------------------

ADMIN_PERMS = [
    "catalog.service.read", "catalog.service.create", "catalog.service.update",
    "assistant.catalog.reindex", "assistant.suggest.use",
]


@pytest.fixture
def admin_a(db, org_a, user_a):
    dar_rol(user_a, org_a, "org_admin_prueba", "Administración", ADMIN_PERMS)
    return user_a


def cliente(user):
    client = APIClient()
    client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return client


def test_el_administrador_registra_edita_y_desactiva_un_servicio(admin_a, org_a):
    api = cliente(admin_a)
    creado = api.post(reverse("catalog:service-list"), {
        "name": "Radiografía de tórax", "kind": "study", "price": "120.00",
        "preparation": "Sacarse collares y objetos metálicos.",
    }, format="json")
    assert creado.status_code == 201, creado.content
    servicio = creado.json()
    assert servicio["kind_display"] == "Estudio"

    editado = api.patch(
        reverse("catalog:service-detail", args=[servicio["id"]]),
        {"price": "130.00"}, format="json",
    )
    assert editado.status_code == 200
    assert editado.json()["price"] == "130.00"

    baja = api.post(reverse("catalog:service-deactivate", args=[servicio["id"]]))
    assert baja.json()["is_active"] is False

    listado = api.get(reverse("catalog:service-list"), {"is_active": "true"}).json()
    assert servicio["id"] not in [s["id"] for s in listado]


def test_sin_permiso_no_se_registran_servicios(paciente_a):
    respuesta = cliente(paciente_a).post(
        reverse("catalog:service-list"), {"name": "X"}, format="json",
    )
    assert respuesta.status_code == 403


def test_no_se_acepta_la_especialidad_de_otra_organizacion(admin_a, org_b):
    with tenant_context(org_b.id):
        ajena = Specialty.objects.create(organization=org_b, name="Odontología")
    respuesta = cliente(admin_a).post(reverse("catalog:service-list"), {
        "name": "Limpieza", "specialty": str(ajena.id),
    }, format="json")
    assert respuesta.status_code == 400
    assert "specialty" in respuesta.json()


def test_reindexar_desde_la_web_hace_llegar_el_servicio_al_asistente(
    admin_a, org_a, proveedor_local,
):
    api = cliente(admin_a)
    api.post(reverse("catalog:service-list"), {
        "name": "Ecografía abdominal", "kind": "study", "price": "180",
        "preparation": "Ayuno de 6 horas y la vejiga llena.",
    }, format="json")

    # Antes de reindexar el asistente no lo conoce.
    antes = api.post(reverse("assistant:suggest"),
                     {"question": "¿Cuánto cuesta la ecografía abdominal?"},
                     format="json").json()
    assert "Bs 180" not in antes["answer"]

    resumen = api.post(reverse("assistant:reindex"))
    assert resumen.status_code == 200
    assert resumen.json()["services"] == 1

    despues = api.post(reverse("assistant:suggest"),
                       {"question": "¿Cuánto cuesta la ecografía abdominal?"},
                       format="json").json()
    assert despues["kind"] == "administrativa"
    assert "Bs 180" in despues["answer"]


def test_reindexar_exige_su_permiso(paciente_a):
    assert cliente(paciente_a).post(reverse("assistant:reindex")).status_code == 403


def test_la_migracion_le_da_los_permisos_al_administrador_y_lectura_a_recepcion(db):
    """Sobre las plantillas de rol, que son las que copia cada organización
    nueva. Las organizaciones de prueba no clonan roles."""
    from accounts.models import RolePermission
    from tenancy.context import platform_admin_context

    with platform_admin_context():
        def codigos(rol):
            return set(RolePermission.objects.filter(
                role__organization__isnull=True, role__code=rol,
            ).values_list("permission__code", flat=True))
        admin, recepcion = codigos("org_admin"), codigos("receptionist")
    assert {"catalog.service.create", "assistant.catalog.reindex"} <= admin
    assert "catalog.service.read" in recepcion
    assert "catalog.service.create" not in recepcion
