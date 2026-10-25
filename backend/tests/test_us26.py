"""US-26 — Receta digital y órdenes.

Como en US-24, lo que más importa se prueba **contra la base**: que la receta
de un encuentro firmado no se pueda tocar aunque alguien salte la API. Y el
PDF se prueba por quién lo puede bajar, que es lo que lo vuelve un dato
clínico y no un archivo cualquiera.
"""

import datetime as dt

import pytest
from django.db import transaction
from django.db.utils import DatabaseError
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from audit.actions import Action
from encounters.models import Encounter, MedicalOrder, PrescriptionItem
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    LA_PAZ,
    _ficha,
    abrir,
    cliente,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)

pytestmark = pytest.mark.django_db

AMOXICILINA = {
    "medication": "Amoxicilina 500 mg cápsulas",
    "dose": "1 cápsula",
    "frequency": "cada 8 horas",
    "duration": "7 días",
    "instructions": "Después de las comidas",
}
HEMOGRAMA = {"kind": "laboratory", "description": "Hemograma completo",
             "notes": "En ayunas"}


def recetar(user, encuentro_id, datos=AMOXICILINA):
    return cliente(user).post(reverse("encounters:prescription", args=[encuentro_id]),
                              datos, format="json")


def ordenar(user, encuentro_id, datos=HEMOGRAMA):
    return cliente(user).post(reverse("encounters:orders", args=[encuentro_id]),
                              datos, format="json")


def firmar(user, encuentro_id):
    api = cliente(user)
    api.patch(reverse("encounters:detail", args=[encuentro_id]), {
        "reason": "Fiebre y dolor de garganta.",
        "diagnosis": "Faringoamigdalitis bacteriana.",
        "indications": "Abundante líquido. Volver si la fiebre sigue a las 72 h.",
    }, format="json")
    respuesta = api.post(reverse("encounters:sign", args=[encuentro_id]))
    assert respuesta.status_code == 200
    return respuesta.json()


def pdf(user, encuentro_id):
    return cliente(user).get(reverse("encounters:prescription-pdf", args=[encuentro_id]))


@pytest.fixture
def borrador(medico_a, ficha_hoy):
    return abrir(medico_a, ficha_hoy).json()["id"]


@pytest.fixture
def otro_borrador(org_a, medico_a, practitioner_a, branches_a, paciente, user_a):
    """Una segunda atención del mismo médico, dos horas antes."""
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    otra = _ficha(org_a, practitioner_a, branches_a["norte"], paciente, user_a,
                  ahora - dt.timedelta(hours=2))
    return abrir(medico_a, otra).json()["id"]


@pytest.fixture
def con_receta_firmada(medico_a, borrador):
    recetar(medico_a, borrador)
    ordenar(medico_a, borrador)
    firmar(medico_a, borrador)
    return borrador


# --------------------------------------------------------------------------
#  Emitir mientras es borrador
# --------------------------------------------------------------------------

def test_el_medico_receta_y_ordena_en_el_borrador(medico_a, borrador):
    respuesta = recetar(medico_a, borrador)
    assert respuesta.status_code == 201
    datos = ordenar(medico_a, borrador).json()
    assert [m["medication"] for m in datos["prescription_items"]] == [
        "Amoxicilina 500 mg cápsulas",
    ]
    assert datos["prescription_items"][0]["frequency"] == "cada 8 horas"
    assert datos["orders"][0]["kind_display"] == "Laboratorio"


def test_corregir_y_quitar_un_medicamento_del_borrador(medico_a, borrador):
    renglon = recetar(medico_a, borrador).json()["prescription_items"][0]["id"]
    api = cliente(medico_a)
    url = reverse("encounters:prescription-item", args=[borrador, renglon])
    datos = api.patch(url, {"dose": "2 cápsulas"}, format="json").json()
    assert datos["prescription_items"][0]["dose"] == "2 cápsulas"
    assert datos["prescription_items"][0]["medication"] == AMOXICILINA["medication"]
    assert api.delete(url).json()["prescription_items"] == []


def test_un_medicamento_sin_dosis_no_se_receta(medico_a, borrador):
    respuesta = recetar(medico_a, borrador, {**AMOXICILINA, "dose": "  "})
    assert respuesta.status_code == 400
    assert "dose" in respuesta.json()


def test_una_orden_de_tipo_desconocido_no_se_emite(medico_a, borrador):
    assert ordenar(medico_a, borrador, {**HEMOGRAMA, "kind": "magia"}).status_code == 400


def test_otro_medico_del_mismo_centro_no_receta_en_una_atencion_ajena(
    otro_medico_a, borrador,
):
    assert recetar(otro_medico_a, borrador).status_code == 404
    assert ordenar(otro_medico_a, borrador).status_code == 404


def test_sin_el_permiso_no_se_receta(patient_a, borrador):
    assert recetar(patient_a, borrador).status_code == 403


def test_un_renglon_de_otra_atencion_no_se_toca_por_esta_url(
    medico_a, borrador, otro_borrador,
):
    """El id del renglón tiene que ser de *este* encuentro, no de cualquiera."""
    renglon = recetar(medico_a, borrador).json()["prescription_items"][0]["id"]
    url = reverse("encounters:prescription-item", args=[otro_borrador, renglon])
    assert cliente(medico_a).delete(url).status_code == 404
    assert cliente(medico_a).patch(url, {"dose": "9"}, format="json").status_code == 404


# --------------------------------------------------------------------------
#  Firmado no se toca: por la API y contra la base
# --------------------------------------------------------------------------

def test_firmado_la_api_no_deja_agregar_corregir_ni_quitar(medico_a, con_receta_firmada):
    assert recetar(medico_a, con_receta_firmada).status_code == 409
    assert ordenar(medico_a, con_receta_firmada).status_code == 409
    datos = cliente(medico_a).get(
        reverse("encounters:detail", args=[con_receta_firmada])).json()
    renglon = datos["prescription_items"][0]["id"]
    url = reverse("encounters:prescription-item", args=[con_receta_firmada, renglon])
    assert cliente(medico_a).patch(url, {"dose": "9"}, format="json").status_code == 409
    assert cliente(medico_a).delete(url).status_code == 409


def test_firmado_la_base_rechaza_insertar_aunque_se_salte_la_api(
    org_a, con_receta_firmada,
):
    with tenant_context(org_a.id):
        encuentro = Encounter.objects.get(pk=con_receta_firmada)
        with pytest.raises(DatabaseError), transaction.atomic():
            PrescriptionItem.objects.create(
                organization=org_a, encounter=encuentro, medication="Otra",
                dose="1", frequency="1", duration="1",
            )
        with pytest.raises(DatabaseError), transaction.atomic():
            MedicalOrder.objects.create(
                organization=org_a, encounter=encuentro, kind="imaging",
                description="Radiografía",
            )


def test_firmado_la_base_rechaza_modificar_y_borrar(org_a, con_receta_firmada):
    with tenant_context(org_a.id):
        renglon = PrescriptionItem.objects.get(encounter_id=con_receta_firmada)
        orden = MedicalOrder.objects.get(encounter_id=con_receta_firmada)
        with pytest.raises(DatabaseError), transaction.atomic():
            PrescriptionItem.objects.filter(pk=renglon.pk).update(dose="10 cápsulas")
        with pytest.raises(DatabaseError), transaction.atomic():
            renglon.delete()
        with pytest.raises(DatabaseError), transaction.atomic():
            MedicalOrder.objects.filter(pk=orden.pk).update(description="Otra cosa")
        with pytest.raises(DatabaseError), transaction.atomic():
            orden.delete()
        assert PrescriptionItem.objects.get(pk=renglon.pk).dose == "1 cápsula"


def test_la_base_no_deja_mover_un_renglon_a_un_encuentro_firmado(
    org_a, medico_a, con_receta_firmada, otro_borrador,
):
    """El trigger mira el encuentro nuevo, no sólo el viejo."""
    renglon = recetar(medico_a, otro_borrador).json()["prescription_items"][0]["id"]
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            PrescriptionItem.objects.filter(pk=renglon).update(
                encounter_id=con_receta_firmada)


def test_la_receta_firmada_se_corrige_con_una_enmienda(medico_a, con_receta_firmada):
    respuesta = cliente(medico_a).post(
        reverse("encounters:amend", args=[con_receta_firmada]),
        {"section": "prescription", "text": "Suspender amoxicilina: refiere alergia."},
        format="json",
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["section_display"] == "Receta"


# --------------------------------------------------------------------------
#  Aislamiento entre organizaciones
# --------------------------------------------------------------------------

@pytest.mark.isolation
def test_otra_organizacion_no_ve_la_receta(org_a, org_b, con_receta_firmada):
    with tenant_context(org_b.id):
        assert PrescriptionItem.objects.count() == 0
        assert MedicalOrder.objects.count() == 0
    with tenant_context(org_a.id):
        assert PrescriptionItem.objects.count() == 1


# --------------------------------------------------------------------------
#  El PDF
# --------------------------------------------------------------------------

def test_el_medico_baja_la_receta_firmada_en_pdf(medico_a, con_receta_firmada, org_a):
    respuesta = pdf(medico_a, con_receta_firmada)
    assert respuesta.status_code == 200
    assert respuesta["Content-Type"] == "application/pdf"
    assert respuesta.content.startswith(b"%PDF")
    assert "receta-" in respuesta["Content-Disposition"]
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(action=Action.RECORD_READ).latest("occurred_at")
    assert asiento.detail["origen"] == "receta_pdf"
    assert asiento.detail["alcance"] == "attending"
    assert "Amoxicilina" not in str(asiento.detail)


def test_un_borrador_no_tiene_pdf(medico_a, borrador):
    recetar(medico_a, borrador)
    assert pdf(medico_a, borrador).status_code == 409


def test_una_atencion_sin_receta_ni_ordenes_no_tiene_pdf(medico_a, borrador):
    firmar(medico_a, borrador)
    assert pdf(medico_a, borrador).status_code == 409


def test_el_paciente_baja_su_receta(con_receta_firmada, paciente, org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-receta", "Paciente", ["encounters.history.read"])
    respuesta = pdf(user_a, con_receta_firmada)
    assert respuesta.status_code == 200
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(action=Action.RECORD_READ).latest("occurred_at")
    assert asiento.detail["alcance"] == "own"


def test_el_paciente_no_baja_el_borrador_de_su_receta(medico_a, borrador, paciente,
                                                       org_a, user_a):
    recetar(medico_a, borrador)
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-receta", "Paciente", ["encounters.history.read"])
    assert pdf(user_a, borrador).status_code == 404


def test_otro_paciente_no_baja_la_receta(con_receta_firmada, org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
    dar_rol(user_a, org_a, "paciente-receta", "Paciente", ["encounters.history.read"])
    assert pdf(user_a, con_receta_firmada).status_code == 404


def test_un_medico_sin_vinculo_con_el_paciente_no_baja_la_receta(
    otro_medico_a, con_receta_firmada,
):
    """Diego tiene el permiso del historial pero nunca tuvo ficha con Pedro."""
    assert pdf(otro_medico_a, con_receta_firmada).status_code == 404


def test_sin_ningun_permiso_no_se_baja(con_receta_firmada, org_a, user_a, paciente):
    """El paciente mismo, sin `encounters.history.read`, tampoco."""
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    assert pdf(user_a, con_receta_firmada).status_code == 404


def test_el_medico_de_la_ficha_sin_permisos_no_la_baja(medico_a, con_receta_firmada, org_a):
    """Ser el profesional de la ficha no alcanza: hace falta el permiso.

    Dar de baja el rol corta el acceso en ese momento, como en US-08.
    """
    from accounts.models import UserRole
    with tenant_context(org_a.id):
        UserRole.objects.filter(user=medico_a).delete()
    assert pdf(medico_a, con_receta_firmada).status_code == 404


@pytest.mark.isolation
def test_desde_otra_organizacion_la_receta_no_existe(con_receta_firmada, user_b, org_b):
    dar_rol(user_b, org_b, "paciente-b", "Paciente", ["encounters.history.read"])
    assert pdf(user_b, con_receta_firmada).status_code == 404


# --------------------------------------------------------------------------
#  El historial (US-25) ya trae la receta: es lo que lee US-27
# --------------------------------------------------------------------------

def test_el_historial_trae_la_receta_y_las_ordenes(medico_a, con_receta_firmada, paciente):
    datos = cliente(medico_a).get(
        reverse("encounters:history", args=[paciente.id])).json()
    assert datos["encounters"][0]["prescription_items"][0]["dose"] == "1 cápsula"
    assert datos["encounters"][0]["orders"][0]["description"] == "Hemograma completo"


# --------------------------------------------------------------------------
#  Copias de seguridad (característica 6)
# --------------------------------------------------------------------------

def test_la_receta_firmada_viaja_en_la_copia_y_sobrevive_la_restauracion(
    org_a, con_receta_firmada,
):
    from backups import services as respaldos
    documento = respaldos.create(org_a)
    assert documento["counts"]["encounters.PrescriptionItem"] == 1
    assert documento["counts"]["encounters.MedicalOrder"] == 1
    respaldos.restore(documento, org_a)
    with tenant_context(org_a.id):
        assert PrescriptionItem.objects.filter(encounter_id=con_receta_firmada).count() == 1


def test_restaurar_no_mete_en_una_receta_firmada_lo_que_se_quito_del_borrador(
    org_a, medico_a, borrador,
):
    """Copia con la amoxicilina en el borrador; después se quita, se receta
    otra cosa y se firma. Restaurar no puede reponer la amoxicilina: la receta
    firmada es la que vale, y el trigger lo rechazaría con un error."""
    from backups import services as respaldos
    renglon = recetar(medico_a, borrador).json()["prescription_items"][0]["id"]
    documento = respaldos.create(org_a)
    cliente(medico_a).delete(
        reverse("encounters:prescription-item", args=[borrador, renglon]))
    recetar(medico_a, borrador, {**AMOXICILINA, "medication": "Azitromicina 500 mg"})
    firmar(medico_a, borrador)

    respaldos.restore(documento, org_a)

    with tenant_context(org_a.id):
        assert list(PrescriptionItem.objects.filter(encounter_id=borrador)
                    .values_list("medication", flat=True)) == ["Azitromicina 500 mg"]
