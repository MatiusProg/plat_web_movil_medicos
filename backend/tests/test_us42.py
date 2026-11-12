"""US-42 — Validar o editar el texto que escribió la IA antes de que lo lea el paciente.

Lo que se prueba es la regla 14 del Sprint 4 y lo que la sostiene:

- un borrador no sale por el endpoint del paciente, nunca;
- el texto lo valida el médico de la atención, no cualquier médico del centro;
- se guardan los dos textos —el del modelo y el corregido— y la diferencia;
- una vez aprobado o descartado no cambia, y eso lo garantiza la **base**, no
  la vista;
- no se cruzan pacientes ni organizaciones.
"""

import datetime as dt
import uuid

import pytest
from django.db import transaction
from django.db.utils import DatabaseError, IntegrityError
from django.urls import reverse

from accounts.models import AuditLog, RolePermission
from ai import services
from ai.models import AiGeneratedText
from audit.actions import Action
from encounters.models import Encounter, MedicalOrder
from patients.models import Patient
from tenancy.context import platform_admin_context, tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    _medico,
    cliente,
    firmado,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)

pytestmark = pytest.mark.django_db

TEXTO_IA = "Tienes una cefalea tensional. Toma paracetamol 2 veces al día. Vuelve en un mes."
SUMMARY = AiGeneratedText.Kind.CONSULTATION_SUMMARY


def _revisor(user, org):
    dar_rol(user, org, f"revisor-{user.document_number}", "Revisor", ["ai.text.review"])
    return user


@pytest.fixture
def laura(medico_a, org_a):
    return _revisor(medico_a, org_a)


@pytest.fixture
def diego(otro_medico_a, org_a):
    return _revisor(otro_medico_a, org_a)


@pytest.fixture
def encuentro(laura, ficha_hoy, org_a):
    encuentro_id = firmado(laura, ficha_hoy)
    with tenant_context(org_a.id):
        return Encounter.objects.get(pk=encuentro_id)


@pytest.fixture
def borrador(encuentro, org_a):
    with tenant_context(org_a.id):
        return services.create_draft(kind=SUMMARY, encounter=encuentro, text=TEXTO_IA,
                                     generated_by="gemini")


@pytest.fixture
def pedro(paciente, org_a, user_a):
    """El paciente de la atención, con cuenta y con el permiso del historial."""
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-ia", "Paciente", ["encounters.history.read"])
    return user_a


def bandeja(user, **params):
    return cliente(user).get(reverse("ai:inbox"), params)


def detalle(user, texto_id):
    return cliente(user).get(reverse("ai:detail", args=[texto_id]))


def corregir(user, texto_id, final_text):
    return cliente(user).patch(reverse("ai:detail", args=[texto_id]),
                               {"final_text": final_text}, format="json")


def aprobar(user, texto_id, **datos):
    return cliente(user).post(reverse("ai:approve", args=[texto_id]), datos, format="json")


def descartar(user, texto_id):
    return cliente(user).post(reverse("ai:discard", args=[texto_id]))


def mios(user, **params):
    return cliente(user).get(reverse("ai:mine"), params)


# --------------------------------------------------------------------------
#  Cómo nace un texto: la interfaz para US-39 y US-40
# --------------------------------------------------------------------------

def test_el_borrador_toma_paciente_y_medico_de_la_atencion(borrador, encuentro):
    assert borrador.status == AiGeneratedText.Status.DRAFT
    assert borrador.patient_id == encuentro.patient_id
    assert borrador.practitioner_id == encuentro.practitioner_id
    assert borrador.organization_id == encuentro.organization_id
    assert borrador.final_text == ""


def test_no_se_guarda_un_texto_vacio(encuentro, org_a):
    with tenant_context(org_a.id), pytest.raises(ValueError):
        services.create_draft(kind=SUMMARY, encounter=encuentro, text="   ")


def test_la_preparacion_exige_que_la_orden_sea_de_esa_atencion(ficha_hoy, org_a, laura):
    # La orden se emite en el borrador; el trigger de US-26 no deja agregarla
    # después de firmar.
    from .test_us24 import abrir
    api = cliente(laura)
    encuentro_id = abrir(laura, ficha_hoy).json()["id"]
    api.patch(reverse("encounters:detail", args=[encuentro_id]),
              {"reason": "Control.", "diagnosis": "Anemia leve."}, format="json")
    api.post(reverse("encounters:orders", args=[encuentro_id]),
             {"kind": "laboratory", "description": "Hemograma completo"}, format="json")
    assert api.post(reverse("encounters:sign", args=[encuentro_id])).status_code == 200

    with tenant_context(org_a.id):
        encuentro = Encounter.objects.get(pk=encuentro_id)
        orden = MedicalOrder.objects.get(encounter=encuentro)
        texto = services.create_draft(kind=AiGeneratedText.Kind.PREPARATION,
                                      medical_order=orden, text="Ven en ayunas de 8 horas.")
        assert texto.encounter_id == encuentro.id

        otro = Encounter(id=uuid.uuid4())  # otra atención: basta con otro id
        with pytest.raises(ValueError):
            services.create_draft(kind=AiGeneratedText.Kind.PREPARATION,
                                  encounter=otro, medical_order=orden, text="x")


def test_un_solo_resumen_vivo_por_atencion(borrador, encuentro, org_a, laura):
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError), transaction.atomic():
            services.create_draft(kind=SUMMARY, encounter=encuentro, text="Otro")
    descartar(laura, borrador.id)
    # Descartado no cuenta: se puede volver a generar.
    with tenant_context(org_a.id):
        nuevo = services.create_draft(kind=SUMMARY, encounter=encuentro, text="Otro")
    assert nuevo.status == AiGeneratedText.Status.DRAFT


# --------------------------------------------------------------------------
#  La bandeja del médico
# --------------------------------------------------------------------------

def test_el_medico_ve_sus_pendientes(borrador, laura):
    datos = bandeja(laura).json()
    assert [t["id"] for t in datos["results"]] == [str(borrador.id)]
    fila = datos["results"][0]
    assert fila["patient_name"] == "Pedro Mamani"
    assert fila["generated_text"] == TEXTO_IA
    assert fila["kind_display"] == "Resumen de la consulta"
    assert fila["encounter_date"] is not None


def test_otro_medico_del_centro_no_lo_ve_ni_lo_aprueba(borrador, diego):
    assert bandeja(diego).json()["results"] == []
    assert detalle(diego, borrador.id).status_code == 404
    assert aprobar(diego, borrador.id).status_code == 404
    assert descartar(diego, borrador.id).status_code == 404


def test_sin_el_permiso_no_hay_bandeja(medico_a):
    # Es médico, con los permisos de la atención, pero sin ai.text.review.
    assert bandeja(medico_a).status_code == 403


def test_el_permiso_es_solo_del_medico(db):
    with platform_admin_context():
        con_permiso = set(RolePermission.objects.filter(
            role__organization__isnull=True, permission__code="ai.text.review",
        ).values_list("role__code", flat=True))
    assert con_permiso == {"practitioner"}


def test_corregir_guarda_los_dos_textos_y_la_diferencia(borrador, laura):
    corregido = TEXTO_IA.replace("2 veces", "3 veces")
    datos = corregir(laura, borrador.id, corregido).json()
    assert datos["status"] == "draft"
    assert datos["generated_text"] == TEXTO_IA
    assert datos["final_text"] == corregido
    assert datos["was_edited"] is True
    assert {"op": "delete", "text": "2"} in datos["diff"]
    assert {"op": "insert", "text": "3"} in datos["diff"]
    assert "".join(t["text"] for t in datos["diff"] if t["op"] != "delete") == corregido


def test_no_se_corrige_a_un_texto_vacio(borrador, laura):
    assert corregir(laura, borrador.id, "   ").status_code == 400
    assert aprobar(laura, borrador.id, final_text="").status_code == 400


def test_aprobar_sin_corregir_aprueba_el_texto_del_modelo(borrador, laura):
    datos = aprobar(laura, borrador.id).json()
    assert datos["status"] == "approved"
    assert datos["final_text"] == TEXTO_IA
    assert datos["was_edited"] is False
    assert datos["reviewed_by_name"] == "Laura Gómez"
    assert datos["reviewed_at"] is not None


def test_aprobar_con_correccion(borrador, laura, org_a):
    aprobar(laura, borrador.id, final_text="Vuelve en dos semanas.")
    with tenant_context(org_a.id):
        fila = AiGeneratedText.objects.get(pk=borrador.pk)
    assert fila.generated_text == TEXTO_IA
    assert fila.final_text == "Vuelve en dos semanas."
    assert fila.reviewed_by_id == laura.id


def test_lo_decidido_no_se_vuelve_a_decidir(borrador, laura):
    aprobar(laura, borrador.id)
    assert corregir(laura, borrador.id, "otra cosa").status_code == 409
    assert aprobar(laura, borrador.id).status_code == 409
    assert descartar(laura, borrador.id).status_code == 409


def test_la_bandeja_filtra_por_estado(borrador, laura):
    aprobar(laura, borrador.id)
    assert bandeja(laura).json()["results"] == []
    assert len(bandeja(laura, status="approved").json()["results"]) == 1
    assert len(bandeja(laura, status="all").json()["results"]) == 1
    assert bandeja(laura, status="cualquiera").json()["results"] == []


def test_la_bitacora_registra_la_decision_sin_el_texto(borrador, laura, org_a):
    corregir(laura, borrador.id, "Vuelve en dos semanas.")
    aprobar(laura, borrador.id)
    with tenant_context(org_a.id):
        asientos = {a.action: a.detail for a in AuditLog.objects.filter(
            entity="ai_generated_texts", entity_id=str(borrador.id))}
    assert asientos[Action.AI_TEXT_EDIT] == {"tipo": "consultation_summary"}
    assert asientos[Action.AI_TEXT_APPROVE] == {"tipo": "consultation_summary",
                                                "corregido": True}


# --------------------------------------------------------------------------
#  La base lo garantiza, no la vista
# --------------------------------------------------------------------------

def test_la_base_no_deja_tocar_lo_aprobado(borrador, laura, org_a):
    aprobar(laura, borrador.id)
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            AiGeneratedText.objects.filter(pk=borrador.pk).update(final_text="cambiado")
        with pytest.raises(DatabaseError), transaction.atomic():
            AiGeneratedText.objects.filter(pk=borrador.pk).update(status="draft")


def test_la_base_no_deja_cambiar_el_texto_del_modelo(borrador, org_a):
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            AiGeneratedText.objects.filter(pk=borrador.pk).update(generated_text="otro")


def test_la_base_no_deja_borrar(borrador, org_a):
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            AiGeneratedText.objects.filter(pk=borrador.pk).delete()


def test_la_base_no_deja_aprobar_sin_quien_ni_cuando(borrador, org_a):
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError), transaction.atomic():
            AiGeneratedText.objects.filter(pk=borrador.pk).update(
                status="approved", final_text="x")


# --------------------------------------------------------------------------
#  El paciente: sólo lo aprobado, sólo lo suyo (regla 14)
# --------------------------------------------------------------------------

def test_el_paciente_no_ve_el_borrador(borrador, pedro):
    respuesta = mios(pedro)
    assert respuesta.status_code == 200
    assert respuesta.json()["results"] == []


def test_el_paciente_no_ve_lo_descartado(borrador, pedro, laura):
    descartar(laura, borrador.id)
    assert mios(pedro).json()["results"] == []


def test_el_paciente_ve_solo_el_texto_aprobado(borrador, pedro, laura, encuentro):
    corregir(laura, borrador.id, "Texto corregido por la médica.")
    # Corregido pero sin aprobar: todavía no.
    assert mios(pedro).json()["results"] == []

    aprobar(laura, borrador.id)
    resultados = mios(pedro, encounter=str(encuentro.id)).json()["results"]
    assert len(resultados) == 1
    fila = resultados[0]
    assert fila["text"] == "Texto corregido por la médica."
    assert fila["practitioner_name"] == "Laura Gómez"
    # Lo que escribió el modelo y la diferencia son del médico, no del paciente.
    assert "generated_text" not in fila and "diff" not in fila


def test_un_paciente_no_ve_los_textos_de_otro(borrador, laura, org_a):
    aprobar(laura, borrador.id)
    with tenant_context(org_a.id):
        from accounts.models import User
        otra = User.objects.create_user(
            email="otra@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Eva", last_name="Paz",
            document_number="5050",
        )
        Patient.objects.create(
            organization=org_a, user=otra, document_type=Patient.DocumentType.CI,
            document_number="5050", first_name="Eva", last_name="Paz",
        )
    dar_rol(otra, org_a, "paciente-eva", "Paciente", ["encounters.history.read"])
    assert mios(otra).json()["results"] == []
    # Ni pasando la atención ajena como filtro.
    assert mios(otra, encounter=str(borrador.encounter_id)).json()["results"] == []


def test_el_titular_ve_los_de_su_dependiente(org_a, user_a, laura, practitioner_a,
                                            branches_a):
    from .test_us24 import LA_PAZ, _ficha
    from django.utils import timezone

    with tenant_context(org_a.id):
        titular = Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
        hijo = Patient.objects.create(
            organization=org_a, guardian=titular, relationship="child",
            first_name="Tomás", last_name="Ríos", birth_date=dt.date(2018, 6, 1),
        )
    dar_rol(user_a, org_a, "paciente-ana", "Paciente", ["encounters.history.read"])
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    encuentro_id = firmado(laura, _ficha(org_a, practitioner_a, branches_a["centro"],
                                         hijo, user_a, ahora))
    with tenant_context(org_a.id):
        texto = services.create_draft(
            kind=SUMMARY, encounter=Encounter.objects.get(pk=encuentro_id), text=TEXTO_IA)
    aprobar(laura, texto.id)
    resultados = mios(user_a).json()["results"]
    assert [r["patient_name"] for r in resultados] == ["Tomás Ríos"]


def test_sin_el_permiso_el_paciente_no_entra(borrador, paciente, org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    assert mios(user_a).status_code == 403


# --------------------------------------------------------------------------
#  Otra organización
# --------------------------------------------------------------------------

def test_otra_organizacion_no_ve_ni_aprueba(borrador, org_b, branch_b):
    from catalog.models import Practitioner
    with tenant_context(org_b.id):
        ajena = Practitioner.objects.create(
            organization=org_b, first_name="Ana", last_name="Paz",
            license_number="MP-9000",
        )
    medica_b = _revisor(_medico(org_b, ajena, "ana@otra.test", "8001"), org_b)
    assert bandeja(medica_b).json()["results"] == []
    assert detalle(medica_b, borrador.id).status_code == 404
    assert aprobar(medica_b, borrador.id).status_code == 404


def test_la_rls_esconde_los_textos_de_otra_organizacion(borrador, org_b):
    with tenant_context(org_b.id):
        assert AiGeneratedText.objects.count() == 0
