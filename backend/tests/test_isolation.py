"""Aislamiento multi-inquilino — RNF-08 y criterio 4 de la Definición de Terminado.

Si alguna de estas pruebas falla, el aislamiento está roto y ninguna historia
del sprint puede darse por terminada.

Toda tabla nueva con ``organization_id`` tiene que sumar su caso acá.
"""

import pytest
from django.db import IntegrityError, ProgrammingError, connection, transaction

from accounts.models import AuditLog, LoginAttempt, Permission, Role, User
from patients.models import Patient
from tenancy.context import no_tenant_context, platform_admin_context, tenant_context
from tenancy.models import (
    IsolationAlert,
    Organization,
    Subscription,
    SubscriptionPlan,
)

pytestmark = [pytest.mark.django_db, pytest.mark.isolation]


# --------------------------------------------------------------------------
#  Lectura
# --------------------------------------------------------------------------
def test_inquilino_solo_ve_sus_usuarios(org_a, user_a, user_b):
    with tenant_context(org_a.id):
        assert list(User.objects.values_list("email", flat=True)) == [user_a.email]


def test_inquilino_no_alcanza_al_usuario_de_otro(org_a, user_a, user_b):
    with tenant_context(org_a.id):
        assert not User.objects.filter(email=user_b.email).exists()


def test_sin_contexto_devuelve_cero_y_no_todo(org_a, user_a, user_b):
    """El fallo abre en cerrado: si el middleware falla, no se devuelve nada."""
    with no_tenant_context():
        assert User.objects.count() == 0
        assert Patient.objects.count() == 0


def test_inquilino_lee_solo_su_propia_ficha_de_organizacion(org_a, org_b):
    with tenant_context(org_a.id):
        assert list(Organization.objects.values_list("slug", flat=True)) == [org_a.slug]


# --------------------------------------------------------------------------
#  Escritura
# --------------------------------------------------------------------------
def test_inquilino_no_puede_escribir_en_otro(org_a, org_b):
    with tenant_context(org_a.id):
        with pytest.raises(ProgrammingError):
            with transaction.atomic():
                User.objects.create_user(
                    email="intruso@x.test", password="clave-de-prueba-1",
                    organization=org_b, first_name="I", last_name="X",
                    document_number="9999",
                )


def test_usuario_no_admite_sucursal_de_otra_organizacion(org_a, branch_b):
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(
                    email="cruzado@x.test", password="clave-de-prueba-1",
                    organization=org_a, branch=branch_b,
                    first_name="C", last_name="X", document_number="8888",
                )


# --------------------------------------------------------------------------
#  El Superadministrador de Plataforma
# --------------------------------------------------------------------------
def test_superadmin_ve_todas_las_organizaciones(platform_admin, org_a, org_b):
    with platform_admin_context():
        assert Organization.objects.count() == 2


def test_superadmin_no_ve_usuarios_de_ninguna_organizacion(
    platform_admin, org_a, org_b, user_a, user_b
):
    """No es una limitación a sortear: es la garantía del alcance del proyecto.

    El Superadministrador no accede a información clínica de ninguna
    organización, y eso se hace cumplir en la base.
    """
    with platform_admin_context():
        assert list(User.objects.values_list("email", flat=True)) == [
            platform_admin.email
        ]


def test_superadmin_no_puede_pertenecer_a_una_organizacion(org_a):
    """Se prueba DENTRO del contexto del inquilino a propósito.

    Con contexto de plataforma la política RLS rechazaría la fila antes de que
    ck_user_scope llegue a evaluarse, y la prueba pasaría sin haber probado la
    restricción.
    """
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                User.objects.create(
                    email="malo@x.test", organization=org_a,
                    first_name="M", last_name="X", document_number="7777",
                    is_platform_admin=True, password="x",
                )


# --------------------------------------------------------------------------
#  Los cinco defectos que encontró la revisión del modelo.
#  Cada una de estas pruebas fallaba antes de corregirlo.
# --------------------------------------------------------------------------
def test_el_middleware_puede_registrar_una_alerta_de_aislamiento(org_a, org_b):
    """US-45. Quien detecta el acceso cruzado está en contexto de inquilino,
    no de superadministrador: tiene que poder insertar igual."""
    with tenant_context(org_a.id):
        IsolationAlert.objects.create(
            source_organization=org_a, target_organization=org_b,
            alert_type=IsolationAlert.AlertType.CROSS_TENANT,
            severity=IsolationAlert.Severity.HIGH,
            description="intento de lectura cruzada",
            endpoint="/api/patients/", http_method="GET",
        )

    with platform_admin_context():
        assert IsolationAlert.objects.count() == 1


def test_un_login_fallido_se_registra_sin_contexto(db):
    """US-02 y RNF-07. El intento se registra ANTES de saber el inquilino."""
    with no_tenant_context():
        LoginAttempt.objects.create(
            attempted_email="quien@sea.test", succeeded=False,
            failure_reason=LoginAttempt.FailureReason.UNKNOWN_USER,
        )

    with platform_admin_context():
        assert LoginAttempt.objects.count() == 1


def test_el_superadmin_audita_sus_propias_acciones(platform_admin, org_a):
    """US-43 y US-44. Las acciones de plataforma van con organization NULL."""
    with platform_admin_context():
        AuditLog.objects.create(
            organization=None, user=platform_admin,
            action="organization.create", entity="organizations",
            entity_id=str(org_a.id),
        )
        assert AuditLog.objects.count() == 1


def test_las_plantillas_de_rol_quedaron_sembradas(db):
    """US-04. La migración semilla corre como app_user, sujeto a RLS."""
    with platform_admin_context():
        plantillas = Role.objects.filter(organization__isnull=True, is_system=True)
        assert plantillas.count() == 5
        assert Permission.objects.count() == 25
        assert SubscriptionPlan.objects.count() == 3


def test_un_menor_sin_documento_se_registra_con_titular(org_a):
    """US-07. Un recién nacido no tiene CI y tiene que poder registrarse."""
    with tenant_context(org_a.id):
        titular = Patient.objects.create(
            organization=org_a, first_name="Ana", last_name="Ríos",
            document_number="5001",
        )
        Patient.objects.create(
            organization=org_a, first_name="Bebé", last_name="Ríos",
            document_number=None, guardian=titular,
        )
        # Dos menores sin documento no deben chocar entre sí.
        Patient.objects.create(
            organization=org_a, first_name="Otro", last_name="Ríos",
            document_number=None, guardian=titular,
        )
        assert Patient.objects.count() == 3


def test_un_paciente_sin_documento_ni_titular_es_rechazado(org_a):
    with tenant_context(org_a.id):
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Patient.objects.create(
                    organization=org_a, first_name="Huérfano",
                    last_name="Sin Doc", document_number=None,
                )


# --------------------------------------------------------------------------
#  Reglas de negocio garantizadas por la base
# --------------------------------------------------------------------------
def test_una_sola_suscripcion_vigente_por_organizacion(org_a, plans):
    with platform_admin_context():
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Subscription.objects.create(
                    organization=org_a, plan=plans["pro"], starts_at="2026-09-01",
                )


def test_la_bitacora_es_inalterable(org_a, user_a):
    """RNF-18. app_user no tiene UPDATE ni DELETE sobre audit_log."""
    with tenant_context(org_a.id):
        AuditLog.objects.create(
            organization=org_a, user=user_a,
            action="role.assign", entity="user_roles",
        )

    with tenant_context(org_a.id):
        with pytest.raises(ProgrammingError):
            with transaction.atomic():
                AuditLog.objects.all().delete()


# --------------------------------------------------------------------------
#  Resolución del inquilino para el login
# --------------------------------------------------------------------------
def test_el_slug_resuelve_el_inquilino_sin_contexto(org_a):
    """Sin esto, US-02 no puede ni empezar: el correo es único por
    organización, así que hay que saber en cuál buscar antes de autenticar."""
    with no_tenant_context():
        with connection.cursor() as cursor:
            cursor.execute("SELECT app_resolve_tenant(%s)", [org_a.slug])
            assert cursor.fetchone()[0] == org_a.id


def test_resolver_un_slug_inexistente_devuelve_nulo(db):
    with no_tenant_context():
        with connection.cursor() as cursor:
            cursor.execute("SELECT app_resolve_tenant(%s)", ["no-existe"])
            assert cursor.fetchone()[0] is None


def test_resolver_el_slug_no_deja_permisos_de_plataforma(org_a, org_b, user_b):
    """La función activa el permiso de plataforma y lo restaura antes de
    devolver. Si se filtrara, cualquier inquilino podría leerlo todo."""
    with tenant_context(org_a.id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT app_resolve_tenant(%s)", [org_b.slug])
            cursor.fetchone()
        # Sigue viendo sólo lo suyo.
        assert Organization.objects.count() == 1
        assert not User.objects.filter(email=user_b.email).exists()


# --------------------------------------------------------------------------
#  Cobertura: ninguna tabla con organization_id sin RLS forzado
# --------------------------------------------------------------------------
def test_toda_tabla_de_inquilino_tiene_rls_forzado(db):
    """Guardia contra el olvido más caro: crear una tabla con
    organization_id y no protegerla. Falla apenas alguien lo haga."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.relname
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
              JOIN information_schema.columns col
                ON col.table_name = c.relname AND col.table_schema = n.nspname
             WHERE n.nspname = 'public'
               AND c.relkind = 'r'
               AND col.column_name = 'organization_id'
               AND NOT (c.relrowsecurity AND c.relforcerowsecurity)
             ORDER BY 1
        """)
        desprotegidas = [row[0] for row in cursor.fetchall()]
    assert desprotegidas == [], (
        f"Tablas con organization_id y sin RLS forzado: {desprotegidas}. "
        "Agregar ENABLE + FORCE y su política en una migración."
    )
