"""US-25 — Historial clínico longitudinal.

El caso que justifica la historia: **un paciente atendido por dos médicos en
dos sucursales distintas** aparece en una sola línea de tiempo, y cualquiera
de los dos la ve completa. Y el que la cuida: un médico sin vínculo de
atención con el paciente no la ve, aunque tenga el permiso.
"""

import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog, RolePermission
from audit.actions import Action
from patients.models import Patient
from tenancy.context import platform_admin_context, tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    LA_PAZ,
    _ficha,
    _medico,
    abrir,
    cliente,
    firmado,
    ficha_hoy,
    medico_a,
    otro_medico_a,
    paciente,
)

pytestmark = pytest.mark.django_db


def historial(user, paciente_id):
    return cliente(user).get(reverse("encounters:history", args=[paciente_id]))


@pytest.fixture
def atendido_en_dos_sedes(org_a, practitioner_a, branches_a, paciente, user_a,
                          medico_a, otro_medico_a, ficha_hoy):
    """Laura lo atiende en la Sede Centro y Diego en la Sede Norte."""
    firmado(medico_a, ficha_hoy)
    with tenant_context(org_a.id):
        from catalog.models import Practitioner
        diego = Practitioner.objects.get(user=otro_medico_a)
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    ficha_norte = _ficha(org_a, diego, branches_a["norte"], paciente, user_a,
                         ahora - dt.timedelta(hours=1))
    firmado(otro_medico_a, ficha_norte)
    return paciente


def test_el_historial_junta_las_atenciones_de_todas_las_sucursales(
    atendido_en_dos_sedes, medico_a,
):
    datos = historial(medico_a, atendido_en_dos_sedes.id).json()
    assert len(datos["encounters"]) == 2
    assert {s["name"] for s in datos["branches"]} == {"Sede Centro", "Sede Norte"}
    assert {e["practitioner_name"] for e in datos["encounters"]} == {
        "Laura Gómez", "Diego Ríos",
    }
    assert datos["scope"] == "professional"


def test_los_borradores_no_son_historia(org_a, practitioner_a, branches_a, paciente,
                                        user_a, medico_a, ficha_hoy):
    abrir(medico_a, ficha_hoy)
    datos = historial(medico_a, paciente.id).json()
    assert datos["encounters"] == []


def test_un_medico_sin_ficha_con_el_paciente_no_ve_su_historial(
    atendido_en_dos_sedes, org_a, branches_a,
):
    from catalog.models import Practitioner
    with tenant_context(org_a.id):
        ajeno = Practitioner.objects.create(
            organization=org_a, first_name="Rosa", last_name="Vargas",
            license_number="MP-3000",
        )
    rosa = _medico(org_a, ajeno, "rosa@kolping.test", "7003")
    dar_rol(rosa, org_a, "hist-7003", "Historial", ["encounters.history.read"])
    assert historial(rosa, atendido_en_dos_sedes.id).status_code == 404


def test_el_paciente_lee_su_propio_historial(atendido_en_dos_sedes, org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=atendido_en_dos_sedes.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-hist", "Paciente", ["encounters.history.read"])
    datos = historial(user_a, atendido_en_dos_sedes.id).json()
    assert datos["scope"] == "own"
    assert len(datos["encounters"]) == 2


def test_un_paciente_no_lee_el_historial_de_otro(atendido_en_dos_sedes, org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
    dar_rol(user_a, org_a, "paciente-hist", "Paciente", ["encounters.history.read"])
    assert historial(user_a, atendido_en_dos_sedes.id).status_code == 404


def test_cada_lectura_queda_en_la_bitacora_sin_contenido(atendido_en_dos_sedes, medico_a, org_a):
    historial(medico_a, atendido_en_dos_sedes.id)
    historial(medico_a, atendido_en_dos_sedes.id)
    with tenant_context(org_a.id):
        asientos = list(AuditLog.objects.filter(
            action=Action.RECORD_READ, entity_id=str(atendido_en_dos_sedes.id),
        ))
    assert len(asientos) == 2
    assert asientos[0].detail == {"origen": "historial", "alcance": "professional",
                                  "encuentros": 2}


def test_sin_el_permiso_no_se_entra(atendido_en_dos_sedes, org_a, user_a):
    # Es el paciente, pero sin el permiso explícito.
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=atendido_en_dos_sedes.pk).update(user=user_a)
    assert historial(user_a, atendido_en_dos_sedes.id).status_code == 403


def test_otra_organizacion_no_ve_el_historial(atendido_en_dos_sedes, org_b, branch_b):
    from catalog.models import Practitioner
    with tenant_context(org_b.id):
        ajeno = Practitioner.objects.create(
            organization=org_b, first_name="Ana", last_name="Paz",
            license_number="MP-9000",
        )
    medico_b = _medico(org_b, ajeno, "ana@otra.test", "8001")
    dar_rol(medico_b, org_b, "hist-8001", "Historial", ["encounters.history.read"])
    assert historial(medico_b, atendido_en_dos_sedes.id).status_code == 404


def test_el_permiso_es_del_medico_y_del_paciente(db):
    with platform_admin_context():
        con_permiso = set(RolePermission.objects.filter(
            role__organization__isnull=True,
            permission__code="encounters.history.read",
        ).values_list("role__code", flat=True))
    assert con_permiso == {"practitioner", "patient"}


# --------------------------------------------------------------------------
#  Quién NO tiene que leerlo: los bordes del vínculo de atención
# --------------------------------------------------------------------------

def _rosa(org_a):
    """Una médica del centro, con el permiso del historial, sin fichas."""
    from catalog.models import Practitioner
    with tenant_context(org_a.id):
        rosa = Practitioner.objects.create(
            organization=org_a, first_name="Rosa", last_name="Vargas",
            license_number="MP-3000",
        )
    return rosa, _medico(org_a, rosa, "rosa@kolping.test", "7003")


def test_una_ficha_cancelada_no_da_acceso_al_historial(
    atendido_en_dos_sedes, org_a, branches_a, user_a,
):
    """Reservar y cancelar no es haber atendido: si bastara, cualquier médico
    podría ganarse el acceso con una ficha que nunca existió."""
    rosa, usuario_rosa = _rosa(org_a)
    _ficha(org_a, rosa, branches_a["sur"], atendido_en_dos_sedes, user_a,
           timezone.now(), "cancelled")
    assert historial(usuario_rosa, atendido_en_dos_sedes.id).status_code == 404


def test_una_ficha_vigente_si_da_acceso(atendido_en_dos_sedes, org_a, branches_a, user_a):
    """El otro lado del borde anterior: con una ficha en pie, lo ve completo."""
    rosa, usuario_rosa = _rosa(org_a)
    _ficha(org_a, rosa, branches_a["sur"], atendido_en_dos_sedes, user_a,
           timezone.now() + dt.timedelta(days=2))
    datos = historial(usuario_rosa, atendido_en_dos_sedes.id).json()
    assert len(datos["encounters"]) == 2


def test_un_medico_dado_de_baja_pierde_el_acceso_en_el_acto(
    atendido_en_dos_sedes, medico_a, practitioner_a, org_a,
):
    assert historial(medico_a, atendido_en_dos_sedes.id).status_code == 200
    with tenant_context(org_a.id):
        practitioner_a.is_active = False
        practitioner_a.save()
    # Mismo token: la baja corta el acceso sin esperar a que venza.
    assert historial(medico_a, atendido_en_dos_sedes.id).status_code == 404


def test_un_rol_administrativo_con_el_permiso_pero_sin_vinculo_no_lo_ve(
    atendido_en_dos_sedes, org_a,
):
    """El permiso no alcanza: hace falta el vínculo. Un rol administrativo al
    que alguien le haya dado el permiso por error sigue sin ver nada."""
    from accounts.models import User
    with tenant_context(org_a.id):
        admin = User.objects.create_user(
            email="admin@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Admin", last_name="Centro",
            document_number="6001",
        )
    dar_rol(admin, org_a, "admin-hist", "Administración",
            ["encounters.history.read", "appointments.appointment.read"])
    assert historial(admin, atendido_en_dos_sedes.id).status_code == 404


def test_un_paciente_inexistente_responde_404(medico_a):
    import uuid
    assert historial(medico_a, uuid.uuid4()).status_code == 404


# --------------------------------------------------------------------------
#  Titular y dependientes (US-07)
# --------------------------------------------------------------------------

@pytest.fixture
def hijo_atendido(org_a, practitioner_a, branches_a, user_a, medico_a):
    """El titular es la cuenta de `user_a`; el hijo no tiene cuenta propia."""
    with tenant_context(org_a.id):
        titular = Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
        hijo = Patient.objects.create(
            organization=org_a, guardian=titular, relationship="child",
            first_name="Tomás", last_name="Ríos", birth_date=dt.date(2018, 6, 1),
        )
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    firmado(medico_a, _ficha(org_a, practitioner_a, branches_a["centro"], hijo,
                             user_a, ahora))
    dar_rol(user_a, org_a, "paciente-hist", "Paciente", ["encounters.history.read"])
    return hijo


def test_el_titular_lee_el_historial_de_su_dependiente(hijo_atendido, user_a):
    datos = historial(user_a, hijo_atendido.id).json()
    assert datos["scope"] == "own"
    assert len(datos["encounters"]) == 1


def test_otro_titular_no_lee_el_historial_del_dependiente_ajeno(hijo_atendido, org_a):
    from accounts.models import User
    with tenant_context(org_a.id):
        otro = User.objects.create_user(
            email="otro@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Otro", last_name="Padre",
            document_number="5009",
        )
        Patient.objects.create(
            organization=org_a, user=otro, document_type=Patient.DocumentType.CI,
            document_number="5009", first_name="Otro", last_name="Padre",
        )
    dar_rol(otro, org_a, "paciente-hist-2", "Paciente", ["encounters.history.read"])
    assert historial(otro, hijo_atendido.id).status_code == 404


# --------------------------------------------------------------------------
#  Qué muestra y qué no
# --------------------------------------------------------------------------

def test_el_borrador_de_otro_medico_no_aparece_pero_lo_firmado_si(
    org_a, practitioner_a, branches_a, paciente, user_a, medico_a,
    otro_medico_a, ficha_hoy,
):
    firmado(medico_a, ficha_hoy)
    from catalog.models import Practitioner
    with tenant_context(org_a.id):
        diego = Practitioner.objects.get(user=otro_medico_a)
    ficha_diego = _ficha(org_a, diego, branches_a["norte"], paciente, user_a,
                         timezone.now() - dt.timedelta(hours=2))
    abrir(otro_medico_a, ficha_diego)   # queda en borrador
    datos = historial(medico_a, paciente.id).json()
    assert [e["practitioner_name"] for e in datos["encounters"]] == ["Laura Gómez"]


def test_las_enmiendas_viajan_con_el_encuentro_y_el_original_queda(
    atendido_en_dos_sedes, medico_a,
):
    def de_laura():
        datos = historial(medico_a, atendido_en_dos_sedes.id).json()
        return next(e for e in datos["encounters"]
                    if e["practitioner_name"] == "Laura Gómez")

    cliente(medico_a).post(reverse("encounters:amend", args=[de_laura()["id"]]),
                           {"section": "diagnosis", "text": "Agrego: sin signos de alarma."},
                           format="json")
    laura = de_laura()
    assert laura["amendments"][0]["text"] == "Agrego: sin signos de alarma."
    assert laura["diagnosis"] == "Cefalea tensional."


def test_la_linea_de_tiempo_va_de_lo_mas_reciente_a_lo_mas_antiguo(
    atendido_en_dos_sedes, medico_a,
):
    encuentros = historial(medico_a, atendido_en_dos_sedes.id).json()["encounters"]
    fechas = [e["appointment_starts_at"] for e in encuentros]
    assert fechas == sorted(fechas, reverse=True)


def test_el_historial_es_de_solo_lectura(atendido_en_dos_sedes, medico_a):
    api = cliente(medico_a)
    url = reverse("encounters:history", args=[atendido_en_dos_sedes.id])
    assert api.post(url, {}, format="json").status_code == 405
    assert api.delete(url).status_code == 405


def test_la_lectura_del_propio_paciente_tambien_queda_en_la_bitacora(
    atendido_en_dos_sedes, org_a, user_a,
):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=atendido_en_dos_sedes.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-hist", "Paciente", ["encounters.history.read"])
    historial(user_a, atendido_en_dos_sedes.id)
    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action=Action.RECORD_READ)
    assert asiento.user_id == user_a.id
    assert asiento.detail["alcance"] == "own"
