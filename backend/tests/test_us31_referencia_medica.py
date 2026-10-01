"""US-31 — La referencia médica que alimenta al asistente.

Lo que se fija acá no es que el contenido sea correcto —eso lo respaldan las
fuentes citadas y lo tiene que revisar alguien de clínica—, sino las reglas
que lo hacen seguro de usar en un sistema multi-inquilino:

- sólo entra para especialidades que la organización **ya tiene**;
- se muestra con el nombre que le da **la organización**;
- toda oración cita de dónde salió;
- se puede apagar.
"""

import pytest

from assistant.indexing import (
    fragments_for,
    index_specialties,
    medical_reference_enabled,
)
from assistant.medical_reference import REFERENCES, find_reference
from assistant.models import CatalogFragment
from catalog.models import Specialty
from tenancy.context import tenant_context

from .test_us31 import proveedor_local  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def referencia_encendida(settings, proveedor_local):  # noqa: F811
    """Encendida a mano: con el proveedor local, "auto" la apaga. Ver
    ``config/settings.py``. Lo que se prueba acá es el cableado, que no
    depende del proveedor."""
    settings.ASSISTANT_MEDICAL_REFERENCE = "on"


# --------------------------------------------------------------------------
#  El contenido
# --------------------------------------------------------------------------

def test_toda_oracion_cita_al_menos_una_fuente_verificable():
    for reference in REFERENCES:
        for sentence in reference.sentences:
            assert sentence.sources, f"{reference.name}: «{sentence.text}» sin fuente"
            for url in sentence.sources:
                assert url.startswith((
                    "https://medlineplus.gov/spanish/",
                    "https://www.who.int/es/",
                )), f"{reference.name}: fuente no admitida {url}"


def test_ninguna_oracion_menciona_medicamentos_ni_diagnosticos_de_urgencia():
    """La referencia orienta a una especialidad. Ir a urgencias lo decide
    `triage.py`, y un medicamento no lo sugiere nunca el asistente."""
    prohibidas = ("ibuprofeno", "paracetamol", "antibiotico", "911", "988")
    for reference in REFERENCES:
        for sentence in reference.sentences:
            texto = sentence.text.lower()
            assert not any(p in texto for p in prohibidas), sentence.text


def test_un_alias_no_se_repite_entre_dos_especialidades():
    vistos = {}
    for reference in REFERENCES:
        for nombre in (reference.name, *reference.aliases):
            clave = nombre.lower()
            assert clave not in vistos, (
                f"«{nombre}» está en {vistos.get(clave)} y en {reference.name}"
            )
            vistos[clave] = reference.name


@pytest.mark.parametrize("nombre, esperado", [
    ("Cardiología", "Cardiología"),
    ("CARDIOLOGIA", "Cardiología"),
    ("Ginecología y Obstetricia", "Ginecología"),
    ("Otorrino", "Otorrinolaringología"),
    ("Psiquiatría", "Psicología"),
])
def test_se_reconoce_por_nombre_o_alias_sin_tildes_ni_mayusculas(nombre, esperado):
    assert find_reference(nombre).name == esperado


@pytest.mark.parametrize("nombre", [
    # Parecidas y distintas. La coincidencia es exacta a propósito.
    "Cirugía cardiovascular", "Neurocirugía", "Odontología",
])
def test_una_especialidad_parecida_no_hereda_una_referencia_ajena(nombre):
    assert find_reference(nombre) is None


# --------------------------------------------------------------------------
#  Cómo entra al índice
# --------------------------------------------------------------------------

def test_la_referencia_va_detras_del_texto_propio_y_con_el_nombre_del_centro(
    org_a, proveedor_local,
):
    with tenant_context(org_a.id):
        especialidad = Specialty.objects.create(
            organization=org_a, name="Ortopedia",
            description="Atendemos lesiones de huesos y articulaciones.",
        )
    textos = fragments_for(especialidad)

    assert textos[1] == (
        "Especialidad: Ortopedia. Atendemos lesiones de huesos y articulaciones."
    ), "el texto del centro va primero"
    referencia = textos[2:]
    assert len(referencia) == len(find_reference("Traumatología").sentences)
    assert all(t.startswith("Especialidad: Ortopedia. ") for t in referencia), (
        "el paciente tiene que leer el nombre que usa su centro"
    )


def test_sin_descripcion_la_referencia_igual_la_hace_recuperable(
    org_a, proveedor_local,
):
    with tenant_context(org_a.id):
        Specialty.objects.create(organization=org_a, name="Neumología")
        resumen = index_specialties(org_a)

    assert resumen["empty"] == []
    assert resumen["fragments"] > 1


def test_nunca_agrega_una_especialidad_que_el_centro_no_tiene(
    org_a, proveedor_local,
):
    with tenant_context(org_a.id):
        cardio = Specialty.objects.create(organization=org_a, name="Cardiología")
        index_specialties(org_a)
        origenes = set(
            CatalogFragment.objects.values_list("source_id", flat=True)
        )
        textos = list(CatalogFragment.objects.values_list("text", flat=True))

    assert origenes == {cardio.id}
    assert not any("Dermatología" in t for t in textos)


def test_una_especialidad_sin_referencia_queda_como_estaba(org_a, proveedor_local):
    with tenant_context(org_a.id):
        especialidad = Specialty.objects.create(
            organization=org_a, name="Nutrición",
            description="Planes de alimentación y control de peso.",
        )
    assert len(fragments_for(especialidad)) == 2


def test_con_el_proveedor_local_auto_la_apaga(settings):
    settings.ASSISTANT_MEDICAL_REFERENCE = "auto"
    settings.ASSISTANT_EMBEDDING_PROVIDER = "local"
    assert not medical_reference_enabled()
    settings.ASSISTANT_EMBEDDING_PROVIDER = "gemini"
    assert medical_reference_enabled()


def test_se_puede_apagar(org_a, proveedor_local, settings):
    settings.ASSISTANT_MEDICAL_REFERENCE = "off"
    with tenant_context(org_a.id):
        especialidad = Specialty.objects.create(
            organization=org_a, name="Cardiología", description="",
        )
    assert fragments_for(especialidad) == ["Especialidad: Cardiología."]
