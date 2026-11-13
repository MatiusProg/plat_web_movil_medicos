"""US-42 — Los bordes que faltaban (regla 17 del Sprint 4).

`test_us42.py` prueba la regla 14 y el aislamiento. Acá van las entradas raras,
los límites y los caminos de escritura que no tenían prueba:

- parámetros malformados en la bandeja y en el endpoint del paciente;
- textos vacíos, con sólo espacios o más largos que el tope;
- lo que se puede volver a generar (un descartado) y lo que no (un vivo);
- que otro médico no pueda ni corregir ni descartar, y que el texto no cambie;
- que el paciente no tenga ninguna forma de escribir;
- que lo que lee el paciente sea siempre el texto final, nunca el del modelo.
"""

import uuid

import pytest
from django.db import transaction
from django.db.utils import IntegrityError
from django.urls import reverse

from accounts.models import AuditLog
from ai import services
from ai.models import AiGeneratedText
from patients.models import Patient
from tenancy.context import tenant_context

from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    _medico,
    cliente,
    firmado,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)
from .test_us42 import (  # noqa: F401  (fixtures y ayudas de US-42)
    SUMMARY,
    TEXTO_IA,
    aprobar,
    bandeja,
    borrador,
    corregir,
    descartar,
    detalle,
    diego,
    encuentro,
    laura,
    mios,
    pedro,
)

pytestmark = pytest.mark.django_db

LARGO = "a" * (services.MAX_TEXT_CHARS + 1)


def _fila(org, pk):
    with tenant_context(org.id):
        return AiGeneratedText.objects.get(pk=pk)


# --------------------------------------------------------------------------
#  Parámetros malformados: nunca un 500
# --------------------------------------------------------------------------

@pytest.mark.parametrize("valor", ["no-es-un-uuid", "123", "' OR 1=1 --"])
def test_el_paciente_con_una_atencion_malformada_no_rompe(borrador, pedro, laura, valor):
    aprobar(laura, borrador.id)
    assert mios(pedro, encounter=valor).status_code == 400


def test_el_paciente_con_un_tipo_inexistente_no_ve_nada(borrador, pedro, laura):
    aprobar(laura, borrador.id)
    respuesta = mios(pedro, kind="cualquier-cosa")
    assert respuesta.status_code == 200
    assert respuesta.json()["results"] == []


def test_una_atencion_que_no_existe_no_devuelve_nada(borrador, pedro, laura):
    aprobar(laura, borrador.id)
    assert mios(pedro, encounter=str(uuid.uuid4())).json()["results"] == []


def test_la_bandeja_con_un_estado_inexistente_no_muestra_nada(borrador, laura):
    respuesta = bandeja(laura, status="aprobadisimo")
    assert respuesta.status_code == 200
    assert respuesta.json()["results"] == []


def test_un_texto_que_no_existe_da_404(laura):
    assert detalle(laura, uuid.uuid4()).status_code == 404
    assert aprobar(laura, uuid.uuid4()).status_code == 404
    assert descartar(laura, uuid.uuid4()).status_code == 404


# --------------------------------------------------------------------------
#  Textos vacíos y largos
# --------------------------------------------------------------------------

@pytest.mark.parametrize("texto", ["", "   ", "\n\t  "])
def test_no_se_aprueba_con_un_texto_vacio_o_de_espacios(borrador, laura, org_a, texto):
    assert aprobar(laura, borrador.id, final_text=texto).status_code == 400
    assert _fila(org_a, borrador.id).status == AiGeneratedText.Status.DRAFT


def test_no_se_corrige_con_un_texto_mas_largo_que_el_tope(borrador, laura, org_a):
    assert corregir(laura, borrador.id, LARGO).status_code == 400
    assert _fila(org_a, borrador.id).final_text == ""


def test_no_se_aprueba_con_un_texto_mas_largo_que_el_tope(borrador, laura, org_a):
    assert aprobar(laura, borrador.id, final_text=LARGO).status_code == 400
    assert _fila(org_a, borrador.id).status == AiGeneratedText.Status.DRAFT


def test_el_texto_del_tope_exacto_se_acepta(borrador, laura):
    exacto = "b" * services.MAX_TEXT_CHARS
    assert aprobar(laura, borrador.id, final_text=exacto).status_code == 200


def test_el_texto_del_modelo_se_recorta_al_tope(encuentro, org_a):
    with tenant_context(org_a.id):
        texto = services.create_draft(kind=SUMMARY, encounter=encuentro, text=LARGO + "zzz")
    assert len(texto.generated_text) == services.MAX_TEXT_CHARS


def test_el_borrador_no_acepta_un_paciente_ajeno(encuentro, org_a):
    with tenant_context(org_a.id):
        otro = Patient.objects.create(
            organization=org_a, document_type=Patient.DocumentType.CI,
            document_number="7070", first_name="Ana", last_name="Ríos",
        )
        with pytest.raises(ValueError):
            services.create_draft(kind=SUMMARY, encounter=encuentro, text=TEXTO_IA,
                                  patient=otro)


# --------------------------------------------------------------------------
#  Qué se puede volver a generar
# --------------------------------------------------------------------------

def test_un_descartado_se_puede_volver_a_generar(borrador, laura, encuentro, org_a):
    descartar(laura, borrador.id)
    with tenant_context(org_a.id):
        nuevo = services.create_draft(kind=SUMMARY, encounter=encuentro, text="Otra versión.")
    assert nuevo.status == AiGeneratedText.Status.DRAFT
    assert nuevo.id != borrador.id


def test_un_aprobado_no_deja_generar_otro_resumen(borrador, laura, encuentro, org_a):
    aprobar(laura, borrador.id)
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError), transaction.atomic():
            services.create_draft(kind=SUMMARY, encounter=encuentro, text="Otra versión.")


# --------------------------------------------------------------------------
#  Lo decidido no cambia, por ningún camino
# --------------------------------------------------------------------------

def test_lo_aprobado_no_se_descarta_ni_se_corrige(borrador, laura, org_a):
    aprobar(laura, borrador.id)
    assert descartar(laura, borrador.id).status_code == 409
    assert corregir(laura, borrador.id, "Cambio tardío.").status_code == 409
    fila = _fila(org_a, borrador.id)
    assert fila.status == AiGeneratedText.Status.APPROVED
    assert fila.final_text == TEXTO_IA


def test_lo_descartado_no_se_aprueba(borrador, laura, org_a):
    descartar(laura, borrador.id)
    assert aprobar(laura, borrador.id).status_code == 409
    assert _fila(org_a, borrador.id).status == AiGeneratedText.Status.DISCARDED


# --------------------------------------------------------------------------
#  Otro médico del centro: ni corrige ni descarta, y el texto no cambia
# --------------------------------------------------------------------------

def test_otro_medico_no_corrige_ni_descarta(borrador, diego, org_a):
    assert corregir(diego, borrador.id, "Lo cambio yo.").status_code == 404
    assert descartar(diego, borrador.id).status_code == 404
    fila = _fila(org_a, borrador.id)
    assert fila.status == AiGeneratedText.Status.DRAFT
    assert fila.final_text == ""
    assert fila.reviewed_by_id is None


def test_otro_medico_no_lo_ve_en_ninguna_lista(borrador, diego):
    for estado in ("draft", "approved", "discarded", "all"):
        assert bandeja(diego, status=estado).json()["results"] == []


# --------------------------------------------------------------------------
#  El paciente sólo lee
# --------------------------------------------------------------------------

def test_el_paciente_no_tiene_bandeja_ni_puede_aprobar(borrador, pedro, org_a):
    assert bandeja(pedro).status_code == 403
    assert detalle(pedro, borrador.id).status_code == 403
    assert aprobar(pedro, borrador.id).status_code == 403
    assert corregir(pedro, borrador.id, "Me lo apruebo yo.").status_code == 403
    assert descartar(pedro, borrador.id).status_code == 403
    assert _fila(org_a, borrador.id).status == AiGeneratedText.Status.DRAFT


@pytest.mark.parametrize("metodo", ["post", "put", "patch", "delete"])
def test_el_endpoint_del_paciente_no_acepta_escrituras(pedro, metodo):
    respuesta = getattr(cliente(pedro), metodo)(reverse("ai:mine"), {}, format="json")
    assert respuesta.status_code == 405


def test_el_paciente_lee_la_ultima_correccion_y_no_la_anterior(borrador, pedro, laura):
    corregir(laura, borrador.id, "Primera corrección.")
    aprobar(laura, borrador.id, final_text="Corrección final.")
    (fila,) = mios(pedro).json()["results"]
    assert fila["text"] == "Corrección final."
    assert "Primera corrección." not in str(fila)
    assert TEXTO_IA not in str(fila)


def test_el_medico_no_lee_por_el_endpoint_del_paciente(borrador, laura):
    """El médico tiene el permiso del historial, pero no es paciente: en
    `/mine/` no ve ni sus propios textos aprobados."""
    aprobar(laura, borrador.id)
    respuesta = mios(laura)
    assert respuesta.status_code == 200
    assert respuesta.json()["results"] == []


# --------------------------------------------------------------------------
#  Bitácora: corregir también queda asentado, sin el texto
# --------------------------------------------------------------------------

def test_corregir_queda_en_la_bitacora_sin_el_texto(borrador, laura, org_a):
    corregir(laura, borrador.id, "Texto con un dato sensible: VIH negativo.")
    with tenant_context(org_a.id):
        asientos = list(AuditLog.objects.filter(entity_id=str(borrador.id)))
    assert asientos, "corregir no dejó asiento"
    assert all("VIH" not in str(a.detail) for a in asientos)


# --------------------------------------------------------------------------
#  Copias de seguridad (característica 6): los textos viajan y no se pisan
# --------------------------------------------------------------------------

def test_la_copia_lleva_los_textos_y_restaurar_no_los_cambia(borrador, laura, encuentro,
                                                             org_a):
    from backups import services as copias

    aprobar(laura, borrador.id, final_text="Texto aprobado antes de la copia.")
    documento = copias.create(org_a)
    assert documento["counts"]["ai.AiGeneratedText"] == 1

    # Un texto que nace después de la copia no se borra al restaurar.
    with tenant_context(org_a.id):
        posterior = services.create_draft(
            kind=AiGeneratedText.Kind.HISTORY_SUMMARY, encounter=encuentro,
            text="Escrito después de la copia.")

    copias.restore(documento, org_a)

    aprobado = _fila(org_a, borrador.id)
    assert aprobado.status == AiGeneratedText.Status.APPROVED
    assert aprobado.final_text == "Texto aprobado antes de la copia."
    assert _fila(org_a, posterior.id).status == AiGeneratedText.Status.DRAFT


def test_un_borrador_de_la_copia_no_deshace_la_aprobacion(borrador, laura, org_a):
    from backups import services as copias

    documento = copias.create(org_a)          # el texto está en borrador
    aprobar(laura, borrador.id)
    copias.restore(documento, org_a)
    assert _fila(org_a, borrador.id).status == AiGeneratedText.Status.APPROVED


def test_el_servicio_tambien_pone_el_tope_sin_pasar_por_la_vista(borrador, laura, org_a):
    """El serializer ya corta a 4000, pero US-39 y US-40 llaman al servicio
    directo: el tope tiene que estar también ahí."""
    from rest_framework.exceptions import ValidationError

    with tenant_context(org_a.id):
        with pytest.raises(ValidationError):
            services.edit(borrador, LARGO)
        with pytest.raises(ValidationError):
            services.approve(borrador, laura, final_text="   ")
    assert _fila(org_a, borrador.id).status == AiGeneratedText.Status.DRAFT
