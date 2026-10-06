"""Característica general 6 — Copias automáticas, y respaldo de lo del Sprint 2.

Dos cosas que se revisaron el 06/10/26 y estaban rotas o no existían:

1. **Las copias automáticas no existían.** Había un comando de consola que
   «haría una tarea nocturna», pero nada lo corría y el archivo quedaba en el
   disco del contenedor, que se borra en cada despliegue. Ahora el sistema
   respalda solo, guarda la copia cifrada y la ofrece en el historial.
2. **El respaldo no llevaba fichas, pagos, servicios ni historia clínica**, y
   restaurar una organización que tuviera una sola ficha fallaba con un 500.
   La historia clínica es inalterable (US-24): la restauración la conserva y
   agrega lo que falte, nunca la borra.
"""

import datetime as dt
import json

import pytest
from django.apps import apps
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AuditLog
from accounts.tokens import tokens_for_user
from appointments.models import Appointment
from audit.actions import Action
from backups import automatic, manifest, services
from backups.models import BackupRecord, StoredBackup
from catalog.models import Service
from encounters.models import Encounter, EncounterAmendment
from patients.models import Patient
from payments.models import Payment
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization, Subscription

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401 - fixtures de US-24
    LA_PAZ,
    _ficha,
    cliente,
    ficha_hoy,
    firmado,
    medico_a,
    paciente,
)

pytestmark = pytest.mark.django_db

PERMISOS = ["backups.backup.create", "backups.backup.restore"]


@pytest.fixture
def admin_a(org_a, user_a):
    dar_rol(user_a, org_a, "admin-respaldos", "Administración", PERMISOS)
    return user_a


@pytest.fixture
def admin_b(org_b, user_b):
    dar_rol(user_b, org_b, "admin-respaldos", "Administración", PERMISOS)
    return user_b


def con_plan(org, plans, codigo):
    with platform_admin_context():
        Subscription.objects.filter(organization=org).update(plan=plans[codigo])


def automaticas(org):
    with tenant_context(org.id):
        return list(
            BackupRecord.objects
            .filter(organization=org, trigger=BackupRecord.Trigger.AUTOMATIC)
            .order_by("created_at")
        )


def atrasar_automaticas(org, horas):
    """Simula que todas las copias automáticas se hicieron hace `horas` más."""
    with tenant_context(org.id):
        for record in BackupRecord.objects.filter(organization=org):
            BackupRecord.objects.filter(pk=record.pk).update(
                created_at=record.created_at - dt.timedelta(hours=horas),
            )
        for stored in StoredBackup.objects.filter(organization=org):
            StoredBackup.objects.filter(pk=stored.pk).update(
                created_at=stored.created_at - dt.timedelta(hours=horas),
            )


# ==========================================================================
#  El respaldo lleva todo lo del inquilino
# ==========================================================================
def test_toda_tabla_del_inquilino_esta_en_la_copia_o_explicada():
    """Si un sprint agrega una tabla con `organization`, esto falla hasta que
    se decida si va en la copia (`manifest.TABLES`) o por qué no
    (`manifest.EXCLUDED`)."""
    en_la_copia = {t.key for t in manifest.TABLES}
    faltan = sorted(
        f"{m._meta.app_label}.{m.__name__}"
        for m in apps.get_models()
        if any(f.name == "organization" for f in m._meta.fields)
        and f"{m._meta.app_label}.{m.__name__}" not in en_la_copia
        and f"{m._meta.app_label}.{m.__name__}" not in manifest.EXCLUDED
    )
    assert faltan == []


def test_el_respaldo_lleva_fichas_pagos_servicios_e_historia(
    org_a, user_a, medico_a, ficha_hoy,
):
    firmado(medico_a, ficha_hoy)
    with tenant_context(org_a.id):
        Service.objects.create(organization=org_a, name="Ecografía",
                               price="150.00")
        Payment.objects.create(organization=org_a, appointment=ficha_hoy,
                               amount="80.00", created_by=user_a,
                               status=Payment.Status.SUCCEEDED)
    conteos = services.create(org_a)["counts"]
    assert conteos["appointments.Appointment"] == 1
    assert conteos["encounters.Encounter"] == 1
    assert conteos["payments.Payment"] == 1
    assert conteos["catalog.Service"] == 1


# ==========================================================================
#  Restaurar con historia clínica
# ==========================================================================
def test_restaurar_una_organizacion_con_historia_clinica_funciona(
    org_a, medico_a, ficha_hoy,
):
    """Antes del 06/10/26 esto devolvía un 500 en toda organización con fichas."""
    encuentro_id = firmado(medico_a, ficha_hoy)
    documento = services.create(org_a)

    resultado = services.restore(documento, org_a)

    assert resultado["written"]["appointments.Appointment"] == 1
    with tenant_context(org_a.id):
        encuentro = Encounter.objects.get(pk=encuentro_id)
        assert encuentro.status == Encounter.Status.SIGNED
        assert encuentro.diagnosis == "Cefalea tensional."
        assert Appointment.objects.filter(pk=ficha_hoy.pk).exists()


def test_la_historia_posterior_al_respaldo_no_se_borra_al_restaurar(
    org_a, practitioner_a, branches_a, user_a, medico_a, ficha_hoy,
):
    """Volver a un momento no puede borrar una atención firmada después: la
    historia clínica es inalterable. Se conserva, y el paciente que se creó
    después del respaldo queda desactivado en vez de borrado."""
    documento = services.create(org_a)   # sin atenciones y sin Rosa

    with tenant_context(org_a.id):
        rosa = Patient.objects.create(
            organization=org_a, first_name="Rosa", last_name="Quispe",
            document_number="9100",
        )
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    ficha = _ficha(org_a, practitioner_a, branches_a["centro"], rosa, user_a,
                   ahora + dt.timedelta(minutes=1))
    encuentro_id = firmado(medico_a, ficha)
    with tenant_context(org_a.id):
        EncounterAmendment.objects.create(
            organization=org_a, encounter_id=encuentro_id, author=medico_a,
            section="diagnosis", text="Se agrega: migraña sin aura.",
        )
        pago = Payment.objects.create(organization=org_a, appointment=ficha,
                                      amount="80.00", created_by=user_a,
                                      status=Payment.Status.SUCCEEDED)

    resultado = services.restore(documento, org_a)

    with tenant_context(org_a.id):
        assert Encounter.objects.filter(pk=encuentro_id).exists()
        assert EncounterAmendment.objects.filter(encounter_id=encuentro_id).count() == 1
        assert Payment.objects.filter(pk=pago.pk,
                                      status=Payment.Status.SUCCEEDED).exists()
        rosa.refresh_from_db()
        assert rosa.is_active is False
    assert resultado["kept"]["patients.Patient"] == 1
    assert resultado["deactivated"]["patients.Patient"] == 1


def test_lo_que_no_apunta_la_historia_si_vuelve_al_momento_del_respaldo(
    org_a, medico_a, ficha_hoy,
):
    firmado(medico_a, ficha_hoy)
    documento = services.create(org_a)
    with tenant_context(org_a.id):
        suelto = Patient.objects.create(
            organization=org_a, first_name="Sin", last_name="Fichas",
            document_number="9200",
        )
        Patient.objects.filter(pk=ficha_hoy.patient_id).update(phone="70000000")

    services.restore(documento, org_a)

    with tenant_context(org_a.id):
        # El posterior al respaldo sin nada que lo ate se borra...
        assert not Patient.objects.filter(pk=suelto.pk).exists()
        # ...y el que la historia fija vuelve a sus datos del respaldo.
        assert Patient.objects.get(pk=ficha_hoy.patient_id).phone != "70000000"


def test_una_atencion_firmada_no_vuelve_a_borrador_con_un_respaldo_viejo(
    org_a, medico_a, ficha_hoy,
):
    from .test_us24 import abrir
    encuentro_id = abrir(medico_a, ficha_hoy).json()["id"]
    documento = services.create(org_a)   # la atención está en borrador
    firmado(medico_a, ficha_hoy)

    services.restore(documento, org_a)

    with tenant_context(org_a.id):
        assert Encounter.objects.get(pk=encuentro_id).status == Encounter.Status.SIGNED


# ==========================================================================
#  Copias automáticas
# ==========================================================================
def test_el_sistema_respalda_solo_y_guarda_la_copia_cifrada(org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.create(organization=org_a, first_name="Zoila",
                               last_name="Ticona", document_number="9300")

    hechas = automatic.run_due()

    assert [r.organization_id for r in hechas].count(org_a.id) == 1
    (record,) = automaticas(org_a)
    assert record.performed_by is None
    with tenant_context(org_a.id):
        sellado = bytes(StoredBackup.objects.get(record=record).content)
    # En la base no queda nada legible...
    assert b"Ticona" not in sellado
    assert b"plataforma-medica-backup" not in sellado
    # ...pero con la clave vuelve el documento entero.
    with tenant_context(org_a.id):
        documento = automatic.read(record)
    assert documento["checksum"] == record.checksum
    assert any(f["fields"]["last_name"] == "Ticona"
               for f in documento["payload"]["patients.Patient"])


def test_correr_dos_veces_no_duplica_la_copia(org_a):
    automatic.run_due()
    automatic.run_due()
    assert len(automaticas(org_a)) == 1


def test_la_frecuencia_de_las_automaticas_sigue_al_plan(org_a, plans):
    con_plan(org_a, plans, "basic")          # una por semana
    automatic.run_due()
    atrasar_automaticas(org_a, 24 * 6)
    automatic.run_due()
    assert len(automaticas(org_a)) == 1
    atrasar_automaticas(org_a, 24)
    automatic.run_due()
    assert len(automaticas(org_a)) == 2


def test_el_premium_tambien_se_respalda_una_vez_por_dia(org_a, plans):
    con_plan(org_a, plans, "premium")        # a mano, sin límite
    automatic.run_due()
    atrasar_automaticas(org_a, 12)
    automatic.run_due()
    assert len(automaticas(org_a)) == 1
    atrasar_automaticas(org_a, 12)
    automatic.run_due()
    assert len(automaticas(org_a)) == 2


def test_se_conservan_solo_las_que_dice_el_plan_y_el_registro_queda(
    org_a, plans,
):
    con_plan(org_a, plans, "basic")          # conserva 4
    for _ in range(6):
        automatic.run_due()
        atrasar_automaticas(org_a, 24 * 7)

    registros = automaticas(org_a)
    assert len(registros) == 6
    with tenant_context(org_a.id):
        guardadas = set(StoredBackup.objects.values_list("record_id", flat=True))
    assert guardadas == {r.pk for r in registros[-4:]}


def test_las_automaticas_no_gastan_la_cuota_de_las_manuales(
    org_a, plans, admin_a,
):
    con_plan(org_a, plans, "basic")
    automatic.run_due()
    respuesta = cliente(admin_a).post(reverse("backups:create"))
    assert respuesta.status_code == 200


def test_una_organizacion_sin_plan_o_suspendida_no_se_respalda(
    org_a, org_b,
):
    with platform_admin_context():
        Subscription.objects.filter(organization=org_a).delete()
        Organization.objects.filter(pk=org_b.pk).update(
            status=Organization.Status.SUSPENDED,
        )
    automatic.run_due()
    assert automaticas(org_a) == []
    assert automaticas(org_b) == []


def test_si_una_organizacion_falla_las_demas_se_respaldan(
    org_a, org_b, monkeypatch,
):
    original = services.create

    def falla_en_a(organization):
        if organization.pk == org_a.pk:
            raise RuntimeError("se cayó a mitad")
        return original(organization)

    monkeypatch.setattr(automatic.services, "create", falla_en_a)
    automatic.run_due()
    assert automaticas(org_a) == []
    assert len(automaticas(org_b)) == 1


def test_con_otra_clave_la_copia_no_se_lee(org_a):
    automatic.run_due()
    (record,) = automaticas(org_a)
    with override_settings(BACKUP_ENCRYPTION_KEY="x" * 43 + "="):
        with tenant_context(org_a.id), pytest.raises(services.BackupError) as e:
            automatic.read(record)
    assert e.value.code == "copia_ilegible"


# ==========================================================================
#  La API: política, historial, descarga y restauración desde el historial
# ==========================================================================
def test_la_politica_cuenta_las_automaticas(org_a, plans, admin_a):
    con_plan(org_a, plans, "pro")
    automatic.run_due()
    datos = cliente(admin_a).get(reverse("backups:policy")).json()
    assert datos["automatic"]["enabled"] is True
    assert datos["automatic"]["interval_hours"] == 24
    assert datos["automatic"]["retention"] == 7
    assert datos["automatic"]["last_at"] is not None
    assert "una por día" in datos["automatic"]["description"]


def test_el_historial_marca_las_automaticas_descargables(org_a, admin_a):
    automatic.run_due()
    cliente(admin_a).post(reverse("backups:create"))
    filas = cliente(admin_a).get(reverse("backups:record-list")).json()["results"]
    por_tipo = {f["trigger"]: f for f in filas}
    assert por_tipo["automatic"]["downloadable"] is True
    assert por_tipo["automatic"]["trigger_label"] == "Automática"
    assert por_tipo["manual"]["downloadable"] is False


def test_descargar_una_automatica_queda_en_la_bitacora(org_a, admin_a):
    automatic.run_due()
    (record,) = automaticas(org_a)
    respuesta = cliente(admin_a).get(
        reverse("backups:record-download", args=[record.pk]),
    )
    assert respuesta.status_code == 200
    assert record.filename in respuesta["Content-Disposition"]
    documento = json.loads(respuesta.content.decode("utf-8"))
    assert documento["checksum"] == record.checksum
    with tenant_context(org_a.id):
        assert AuditLog.objects.filter(action=Action.BACKUP_DOWNLOAD).count() == 1


def test_una_copia_que_ya_no_se_conserva_da_404(org_a, admin_a):
    automatic.run_due()
    (record,) = automaticas(org_a)
    with tenant_context(org_a.id):
        StoredBackup.objects.all().delete()
    respuesta = cliente(admin_a).get(
        reverse("backups:record-download", args=[record.pk]),
    )
    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "copia_no_disponible"


def test_no_se_baja_ni_se_restaura_la_copia_del_vecino(
    org_a, org_b, admin_a, admin_b,
):
    automatic.run_due()
    (de_b,) = automaticas(org_b)
    api = cliente(admin_a)
    assert api.get(reverse("backups:record-download",
                           args=[de_b.pk])).status_code == 404
    for ruta in ("backups:inspect", "backups:restore"):
        respuesta = api.post(reverse(ruta),
                             {"record": str(de_b.pk), "confirm": True},
                             format="json")
        assert respuesta.status_code == 404, ruta
        assert respuesta.json()["code"] == "copia_no_encontrada"


def test_sin_permiso_no_se_baja_la_automatica(org_a, user_a):
    automatic.run_due()
    (record,) = automaticas(org_a)
    respuesta = cliente(user_a).get(
        reverse("backups:record-download", args=[record.pk]),
    )
    assert respuesta.status_code == 403


def test_se_restaura_desde_una_copia_del_historial(org_a, admin_a):
    with tenant_context(org_a.id):
        Patient.objects.create(organization=org_a, first_name="Ana",
                               last_name="Ayala", document_number="9400")
    automatic.run_due()
    (record,) = automaticas(org_a)
    with tenant_context(org_a.id):
        Patient.objects.filter(document_number="9400").update(first_name="Borrado")

    api = cliente(admin_a)
    resumen = api.post(reverse("backups:inspect"), {"record": str(record.pk)},
                       format="json")
    assert resumen.status_code == 200
    assert resumen.json()["belongs_to_my_organization"] is True

    respuesta = api.post(reverse("backups:restore"),
                         {"record": str(record.pk), "confirm": True},
                         format="json")
    assert respuesta.status_code == 200
    with tenant_context(org_a.id):
        assert Patient.objects.get(document_number="9400").first_name == "Ana"
        restauracion = BackupRecord.objects.get(kind=BackupRecord.Kind.RESTORE)
    assert restauracion.filename == record.filename


def test_un_id_que_no_es_uuid_da_404_y_no_500(admin_a):
    respuesta = cliente(admin_a).post(reverse("backups:inspect"),
                                      {"record": "abc"}, format="json")
    assert respuesta.status_code == 404


# ==========================================================================
#  Editar un plan no borra la frecuencia de las copias
# ==========================================================================
def test_editar_las_funciones_de_un_plan_no_borra_las_de_respaldo(
    plans, platform_admin,
):
    """El formulario de planes manda sólo las funciones que conoce. Antes,
    guardar el plan Básico desde la web le borraba `backup_interval_hours` y
    pasaba a respaldar sin límite."""
    api = APIClient()
    api.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(platform_admin)['access']}",
    )
    plan = plans["basic"]
    respuesta = api.patch(f"/api/platform/plans/{plan.id}/",
                          {"features": {"ai_chatbot": True}}, format="json")
    assert respuesta.status_code == 200
    with platform_admin_context():
        plan.refresh_from_db()
    assert plan.features["ai_chatbot"] is True
    assert plan.features["backup_interval_hours"] == 168
    assert plan.features["backup_retention"] == 4
