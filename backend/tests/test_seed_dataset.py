"""El dataset de demostración (`seed_dataset`).

Lo que se verifica no es cuántas filas exactas salen —eso depende de la
fecha—, sino que lo sembrado respete las mismas reglas que la aplicación:
que cada organización nazca por el alta de US-43, que todo quede dentro de su
inquilino, que las fichas pasadas tengan desenlace y que las atendidas tengan
su atención firmada.
"""

from zoneinfo import ZoneInfo

import pytest
from django.core.management import CommandError, call_command

from accounts.models import Role, User, UserRole
from appointments.models import Appointment
from catalog.models import Practitioner, Service, Specialty
from encounters.models import Encounter
from patients.models import Patient
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization
from assistant.medical_reference import reference_texts

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-del-dataset"


@pytest.fixture
def sembrado(platform_admin, plans):
    call_command("seed_dataset", "--only", "losandes", "--password", CLAVE)
    with platform_admin_context():
        return Organization.objects.get(slug="losandes")


def test_sin_clave_no_siembra(platform_admin, plans, monkeypatch):
    monkeypatch.delenv("DATASET_PASSWORD", raising=False)
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--only", "losandes")


def test_la_organizacion_nace_por_el_alta_de_us43(sembrado):
    with tenant_context(sembrado.id):
        roles = set(Role.objects.filter(organization=sembrado).values_list("code", flat=True))
        admin = User.objects.get(email="admin@losandes.test")
        assert UserRole.objects.filter(user=admin, role__code="org_admin").exists()
    assert {"org_admin", "practitioner", "receptionist", "patient"} <= roles


def test_las_cuentas_entran_con_la_clave_comun(sembrado):
    with tenant_context(sembrado.id):
        medico = User.objects.get(email="medico1@losandes.test")
    assert medico.check_password(CLAVE)


def test_solo_especialidades_con_referencia_medica(sembrado):
    with tenant_context(sembrado.id):
        nombres = list(Specialty.objects.values_list("name", flat=True))
    assert nombres
    assert all(reference_texts(n) for n in nombres)


def test_cada_profesional_tiene_cuenta_rol_y_agenda(sembrado):
    with tenant_context(sembrado.id):
        for prof in Practitioner.objects.all():
            assert prof.user_id is not None
            assert prof.schedules.exists()
            assert UserRole.objects.filter(user_id=prof.user_id, role__code="practitioner").exists()


def test_lo_pasado_tiene_desenlace_y_lo_atendido_su_atencion_firmada(sembrado):
    from django.utils import timezone
    with tenant_context(sembrado.id):
        pasadas = Appointment.objects.filter(starts_at__lt=timezone.now())
        assert not pasadas.filter(status__in=["pending_payment", "confirmed"]).exists()
        atendidas = pasadas.filter(status="attended")
        assert atendidas.exists()
        assert Encounter.objects.filter(status="signed").count() == atendidas.count()
        assert not Encounter.objects.filter(status="draft").exists()
        # Hay ausencias: el modelo de inasistencia del Sprint 4 las necesita.
        assert pasadas.filter(status="no_show").exists()


def test_hay_pacientes_con_cuenta_y_dependientes(sembrado):
    with tenant_context(sembrado.id):
        assert Patient.objects.filter(user__isnull=False).count() == 60
        assert Patient.objects.filter(guardian__isnull=False).exists()


def test_hay_servicios_con_precio_para_el_asistente(sembrado):
    with tenant_context(sembrado.id):
        assert Service.objects.filter(price__isnull=False).exists()


def test_lo_sembrado_no_se_ve_desde_otra_organizacion(sembrado, org_b):
    with tenant_context(org_b.id):
        assert not Appointment.objects.exists()
        assert not Encounter.objects.exists()
        assert not Patient.objects.filter(organization=sembrado).exists()


def test_correrlo_dos_veces_no_duplica(sembrado):
    with tenant_context(sembrado.id):
        antes = Appointment.objects.count()
    call_command("seed_dataset", "--only", "losandes", "--password", CLAVE)
    with tenant_context(sembrado.id):
        assert Appointment.objects.count() == antes


# --------------------------------------------------------------------------
#  --enrich: nutrir una organización que ya existe
# --------------------------------------------------------------------------

@pytest.fixture
def como_en_produccion(platform_admin, plans):
    """Igual que kolping3k y morita2: alta normal, el catálogo de
    `seed_catalog` con agendas, profesionales sin cuenta y un paciente que
    ya estaba (una cuenta de prueba de alguien del equipo)."""
    from tenancy.services import create_organization

    org, admin, _ = create_organization(
        organization_data={"slug": "morita2", "name": "Morita", "legal_name": "Morita",
                           "tax_id": "123456", "contact_email": "contacto@morita.test"},
        admin_data={"email": "admin@morita.test", "first_name": "Ad", "last_name": "Min",
                    "document_number": "1"},
        plan=plans["pro"], created_by=platform_admin,
    )
    call_command("seed_catalog", "--organization", "morita2", "--with-schedules")
    with tenant_context(org.id):
        previo = Patient.objects.create(
            organization=org, document_type=Patient.DocumentType.CI,
            document_number="555", first_name="Prueba", last_name="Del Equipo",
        )
        especialidades = set(Specialty.objects.values_list("name", flat=True))
    return org, previo, especialidades


def test_enrich_agrega_lo_que_falta(como_en_produccion):
    org, _previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert not Practitioner.objects.filter(user__isnull=True).exists()
        assert Service.objects.filter(price__isnull=False).exists()
        assert UserRole.objects.filter(role__code="receptionist").exists()
        assert Patient.objects.count() >= 100
        atendidas = Appointment.objects.filter(status="attended").count()
        assert atendidas > 0
        assert Encounter.objects.filter(status="signed").count() == atendidas


def test_enrich_no_crea_especialidades(como_en_produccion):
    org, _previo, antes = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert set(Specialty.objects.values_list("name", flat=True)) == antes


def test_enrich_no_toca_a_los_pacientes_que_ya_estaban(como_en_produccion):
    org, previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert not Appointment.objects.filter(patient=previo).exists()
        previo_ahora = Patient.objects.get(pk=previo.pk)
    assert (previo_ahora.first_name, previo_ahora.document_number) == ("Prueba", "555")


def test_enrich_respeta_la_vigencia_de_las_agendas(como_en_produccion):
    """Las agendas de `seed_catalog` empiezan hoy: no puede haber fichas
    antes de que la agenda existiera."""
    org, _previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        for ficha in Appointment.objects.select_related("schedule"):
            assert ficha.starts_at.astimezone(ZoneInfo("America/La_Paz")).date() >= ficha.schedule.valid_from


def test_enrich_dos_veces_no_duplica(como_en_produccion):
    org, _previo, _esp = como_en_produccion
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        conteo = (Appointment.objects.count(), Patient.objects.count(),
                  Service.objects.count(), Practitioner.objects.count())
    call_command("seed_dataset", "--enrich", "morita2", "--password", CLAVE)
    with tenant_context(org.id):
        assert (Appointment.objects.count(), Patient.objects.count(),
                Service.objects.count(), Practitioner.objects.count()) == conteo


def test_enrich_de_una_organizacion_inexistente_falla(platform_admin, plans):
    with pytest.raises(CommandError):
        call_command("seed_dataset", "--enrich", "noexiste", "--password", CLAVE)
