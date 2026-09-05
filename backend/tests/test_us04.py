"""US-04 — Crear y asignar roles.

Todas entran por HTTP, como pide el punto 6 de las convenciones: lo que se
está probando es la autorización, y la autorización vive en la vista y en el
contexto de inquilino que fija la autenticación. Una prueba que sólo toca el
ORM se saltea las dos.

El bloque final es el criterio 4 de la Definition of Done —aislamiento
comprobado (RNF-08)—: un administrador de la organización A no ve, no edita y
no asigna ni una fila de la B.
"""

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import (
    AuditLog,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from accounts.tokens import tokens_for_user
from tenancy.context import tenant_context

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"

# Los permisos que la historia administra. El de baja lo crea la migración
# 0003 de accounts; los otros cuatro vienen del seed del Sprint 0.
PERMISOS_DE_ROLES = [
    "users.role.create",
    "users.role.read",
    "users.role.update",
    "users.role.delete",
    "users.role.assign",
    "users.user.read",
]


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def dar_rol(user, organization, code, name, permission_codes):
    """Crea un rol con esos permisos y se lo asigna al usuario."""
    with tenant_context(organization.id):
        role = Role.objects.create(
            organization=organization, code=code, name=name,
        )
        RolePermission.objects.bulk_create([
            RolePermission(
                role=role, permission=permission, organization=organization,
            )
            for permission in Permission.objects.filter(code__in=permission_codes)
        ])
        UserRole.objects.create(user=user, role=role, organization=organization)
    return role


@pytest.fixture
def admin_a(org_a, user_a):
    """``user_a`` con el rol de administración de su organización."""
    dar_rol(
        user_a, org_a, "org_admin", "Administrador de Organización",
        PERMISOS_DE_ROLES,
    )
    return user_a


@pytest.fixture
def admin_b(org_b, user_b):
    dar_rol(
        user_b, org_b, "org_admin", "Administrador de Organización",
        PERMISOS_DE_ROLES,
    )
    return user_b


@pytest.fixture
def solo_lectura_a(org_a, user_a):
    """Un usuario de A que puede mirar los roles pero no tocarlos."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="mirona@kolping.test", password=CLAVE, organization=org_a,
            first_name="Mirta", last_name="Ona", document_number="5011",
        )
    dar_rol(user, org_a, "auditor", "Auditor", ["users.role.read"])
    return user


# --------------------------------------------------------------------------
#  El catálogo de permisos
# --------------------------------------------------------------------------
def test_el_catalogo_no_ofrece_permisos_de_plataforma(api_client, admin_a):
    respuesta = autenticar(api_client, admin_a).get(reverse("accounts:permission-list"))

    assert respuesta.status_code == 200
    modulos = {permiso["module"] for permiso in respuesta.json()}
    assert "platform" not in modulos
    assert "users" in modulos


def test_la_plantilla_del_paciente_lee_el_catalogo_del_centro_medico():
    """El criterio de aceptación que no está en el Product Backlog.

    Sin estos cuatro permisos la aplicación móvil no puede listar sucursales
    ni buscar profesionales, y el Sprint 2 no puede reservar. Los pone la
    migración ``accounts/0003_seed_permissions_sprint_1``.
    """
    plantilla = Role.objects.get(organization__isnull=True, code="patient")
    concedidos = set(
        plantilla.role_permissions.values_list("permission__code", flat=True)
    )

    assert {
        "catalog.branch.read",
        "catalog.specialty.read",
        "catalog.professional.read",
        "scheduling.slot.read",
    } <= concedidos


def test_la_migracion_alcanza_a_las_organizaciones_ya_dadas_de_alta(org_a):
    """El seed del Sprint 0 sólo tocaba las plantillas del sistema.

    Una organización dada de alta antes de la migración ya tiene sus copias
    clonadas, y una copia no se entera de un permiso nuevo. Sin el recorrido
    por inquilino de ``accounts/0003``, el criterio de aceptación se cumpliría
    únicamente para las organizaciones que se den de alta a partir de ahora
    —y las de local y Supabase se quedarían sin los permisos.
    """
    from importlib import import_module

    from django.apps import apps as registro
    from django.db import connection

    migracion = import_module("accounts.migrations.0003_seed_permissions_sprint_1")

    # Una copia del rol Paciente como la que dejó el alta del Sprint 0: sin
    # ningún permiso, porque la plantilla tampoco tenía.
    with tenant_context(org_a.id):
        copia = Role.objects.create(
            organization=org_a, code="patient", name="Paciente",
        )
        assert not copia.role_permissions.exists()

    with connection.schema_editor() as editor:
        migracion.seed(registro, editor)

    with tenant_context(org_a.id):
        concedidos = set(
            copia.role_permissions.values_list("permission__code", flat=True)
        )

    assert {
        "catalog.branch.read",
        "catalog.specialty.read",
        "catalog.professional.read",
        "scheduling.slot.read",
    } <= concedidos


# --------------------------------------------------------------------------
#  ABM de roles
# --------------------------------------------------------------------------
def test_se_crea_un_rol_con_sus_permisos(api_client, admin_a, org_a):
    respuesta = autenticar(api_client, admin_a).post(
        reverse("accounts:role-list"),
        {
            "code": "caja",
            "name": "Caja",
            "description": "Cobra fichas y cierra la caja del día.",
            "permissions": ["patients.patient.read", "catalog.branch.read"],
        },
        format="json",
    )

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["permissions"] == ["catalog.branch.read", "patients.patient.read"]
    assert cuerpo["is_system"] is False
    assert cuerpo["assigned_users"] == 0

    with tenant_context(org_a.id):
        rol = Role.objects.get(code="caja")
        assert rol.organization_id == org_a.id
        assert AuditLog.objects.filter(
            action="role.create", entity_id=str(rol.id),
        ).exists()


def test_un_rol_de_organizacion_no_lleva_permisos_de_plataforma(api_client, admin_a):
    respuesta = autenticar(api_client, admin_a).post(
        reverse("accounts:role-list"),
        {"code": "atajo", "name": "Atajo",
         "permissions": ["platform.organization.create"]},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "plataforma" in str(respuesta.json()["permissions"])


def test_el_codigo_del_rol_no_se_repite_en_la_organizacion(api_client, admin_a):
    cliente = autenticar(api_client, admin_a)
    cuerpo = {"code": "caja", "name": "Caja"}

    assert cliente.post(reverse("accounts:role-list"), cuerpo, format="json").status_code == 201
    repetido = cliente.post(reverse("accounts:role-list"), cuerpo, format="json")

    assert repetido.status_code == 400
    assert "code" in repetido.json()


def test_el_listado_no_muestra_las_plantillas_del_sistema(api_client, admin_a):
    respuesta = autenticar(api_client, admin_a).get(reverse("accounts:role-list"))

    assert respuesta.status_code == 200
    devueltos = respuesta.json()["results"]
    assert devueltos, "el administrador tiene que ver al menos su propio rol"
    assert all(rol["is_system"] is False for rol in devueltos)
    assert {rol["code"] for rol in devueltos} == {"org_admin"}


def test_reemplazar_los_permisos_quita_los_que_no_vienen(api_client, admin_a, org_a):
    cliente = autenticar(api_client, admin_a)
    creado = cliente.post(
        reverse("accounts:role-list"),
        {"code": "caja", "name": "Caja",
         "permissions": ["patients.patient.read", "catalog.branch.read"]},
        format="json",
    ).json()

    respuesta = cliente.put(
        reverse("accounts:role-permissions", args=[creado["id"]]),
        {"permissions": ["catalog.branch.read"]},
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["permissions"] == ["catalog.branch.read"]

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(action="role.permissions.update")
        assert asiento.detail["quitados"] == ["patients.patient.read"]
        assert asiento.detail["agregados"] == []


def test_no_se_elimina_un_rol_asignado(api_client, admin_a, org_a):
    """``UserRole.role`` es PROTECT: sin este control sería un 500."""
    with tenant_context(org_a.id):
        rol = Role.objects.get(organization=org_a, code="org_admin")

    respuesta = autenticar(api_client, admin_a).delete(
        reverse("accounts:role-detail", args=[rol.id]),
    )

    assert respuesta.status_code == 409


def test_no_se_elimina_el_rol_de_administracion(api_client, admin_a, org_a):
    """Aunque no tenga a nadie asignado: es el único que administra.

    Los permisos le llegan por un segundo rol, no por ``org_admin``: si se
    los quitara al vaciar la asignación, la respuesta sería un 403 y la
    prueba no estaría probando lo que dice.
    """
    dar_rol(admin_a, org_a, "supervisor", "Supervisor", PERMISOS_DE_ROLES)

    with tenant_context(org_a.id):
        UserRole.objects.filter(role__code="org_admin").delete()
        rol = Role.objects.get(organization=org_a, code="org_admin")

    respuesta = autenticar(api_client, admin_a).delete(
        reverse("accounts:role-detail", args=[rol.id]),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "rol_de_administracion"


def test_se_elimina_un_rol_sin_usuarios(api_client, admin_a, org_a):
    cliente = autenticar(api_client, admin_a)
    creado = cliente.post(
        reverse("accounts:role-list"),
        {"code": "temporal", "name": "Temporal"}, format="json",
    ).json()

    respuesta = cliente.delete(reverse("accounts:role-detail", args=[creado["id"]]))

    assert respuesta.status_code == 204
    with tenant_context(org_a.id):
        assert not Role.objects.filter(code="temporal").exists()
        assert AuditLog.objects.filter(action="role.delete").exists()


def test_el_rol_de_administracion_no_se_desactiva(api_client, admin_a, org_a):
    with tenant_context(org_a.id):
        rol = Role.objects.get(organization=org_a, code="org_admin")

    respuesta = autenticar(api_client, admin_a).patch(
        reverse("accounts:role-detail", args=[rol.id]),
        {"is_active": False}, format="json",
    )

    assert respuesta.status_code == 400
    assert "is_active" in respuesta.json()


# --------------------------------------------------------------------------
#  Autorización: cada acción exige su permiso
# --------------------------------------------------------------------------
def test_sin_permiso_de_alta_no_se_crea_un_rol(api_client, solo_lectura_a):
    cliente = autenticar(api_client, solo_lectura_a)

    assert cliente.get(reverse("accounts:role-list")).status_code == 200
    respuesta = cliente.post(
        reverse("accounts:role-list"),
        {"code": "caja", "name": "Caja"}, format="json",
    )

    assert respuesta.status_code == 403


def test_un_usuario_sin_roles_no_entra_a_la_administracion(api_client, user_b):
    respuesta = autenticar(api_client, user_b).get(reverse("accounts:role-list"))

    assert respuesta.status_code == 403


def test_el_superadministrador_no_administra_roles_de_un_inquilino(
    api_client, platform_admin,
):
    """Su rol sólo lleva permisos del módulo `platform`, y es a propósito."""
    respuesta = autenticar(api_client, platform_admin).get(
        reverse("accounts:role-list"),
    )

    assert respuesta.status_code == 403


# --------------------------------------------------------------------------
#  Asignación de roles a los usuarios
# --------------------------------------------------------------------------
def test_se_asigna_un_rol_a_un_usuario(api_client, admin_a, org_a):
    with tenant_context(org_a.id):
        destinatario = User.objects.create_user(
            email="nuevo@kolping.test", password=CLAVE, organization=org_a,
            first_name="Noe", last_name="Vera", document_number="5021",
        )
        rol = Role.objects.create(
            organization=org_a, code="caja", name="Caja",
        )

    respuesta = autenticar(api_client, admin_a).post(
        reverse("accounts:user_role-list"),
        {"user": str(destinatario.id), "role": str(rol.id)},
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["role_code"] == "caja"

    with tenant_context(org_a.id):
        assert UserRole.objects.filter(user=destinatario, role=rol).exists()
        asiento = AuditLog.objects.get(action="role.assign")
        assert asiento.detail["user_email"] == "nuevo@kolping.test"
        assert asiento.organization_id == org_a.id


def test_el_mismo_rol_no_se_asigna_dos_veces(api_client, admin_a, org_a):
    with tenant_context(org_a.id):
        rol = Role.objects.get(organization=org_a, code="org_admin")

    respuesta = autenticar(api_client, admin_a).post(
        reverse("accounts:user_role-list"),
        {"user": str(admin_a.id), "role": str(rol.id)},
        format="json",
    )

    assert respuesta.status_code == 400


def test_nadie_se_revoca_un_rol_a_si_mismo(api_client, admin_a, org_a):
    with tenant_context(org_a.id):
        asignacion = UserRole.objects.get(user=admin_a, role__code="org_admin")

    respuesta = autenticar(api_client, admin_a).delete(
        reverse("accounts:user_role-detail", args=[asignacion.id]),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "revocacion_propia"


def test_se_revoca_el_rol_de_otro_usuario(api_client, admin_a, org_a):
    with tenant_context(org_a.id):
        otro = User.objects.create_user(
            email="otro@kolping.test", password=CLAVE, organization=org_a,
            first_name="Otro", last_name="Usuario", document_number="5031",
        )
        rol = Role.objects.create(organization=org_a, code="caja", name="Caja")
        asignacion = UserRole.objects.create(
            user=otro, role=rol, organization=org_a,
        )

    respuesta = autenticar(api_client, admin_a).delete(
        reverse("accounts:user_role-detail", args=[asignacion.id]),
    )

    assert respuesta.status_code == 204
    with tenant_context(org_a.id):
        assert not UserRole.objects.filter(id=asignacion.id).exists()
        assert AuditLog.objects.filter(action="role.revoke").exists()


def test_el_listado_de_usuarios_trae_sus_roles(api_client, admin_a, org_a):
    respuesta = autenticar(api_client, admin_a).get(reverse("accounts:user-list"))

    assert respuesta.status_code == 200
    usuarios = respuesta.json()["results"]
    quien = next(u for u in usuarios if u["id"] == str(admin_a.id))
    assert [rol["code"] for rol in quien["roles"]] == ["org_admin"]


# --------------------------------------------------------------------------
#  Aislamiento (RNF-08) — criterio 4 de la Definition of Done
# --------------------------------------------------------------------------
@pytest.mark.isolation
def test_el_administrador_de_a_no_ve_los_roles_de_b(api_client, admin_a, admin_b):
    respuesta = autenticar(api_client, admin_a).get(reverse("accounts:role-list"))

    assert respuesta.status_code == 200
    devueltos = respuesta.json()["results"]
    assert len(devueltos) == 1
    assert all(rol["assigned_users"] == 1 for rol in devueltos)


@pytest.mark.isolation
def test_el_administrador_de_a_no_ve_los_usuarios_de_b(
    api_client, admin_a, admin_b, user_b,
):
    respuesta = autenticar(api_client, admin_a).get(reverse("accounts:user-list"))

    assert respuesta.status_code == 200
    correos = {usuario["email"] for usuario in respuesta.json()["results"]}
    assert user_b.email not in correos


@pytest.mark.isolation
def test_no_se_asigna_un_rol_de_otra_organizacion(
    api_client, admin_a, admin_b, org_b,
):
    with tenant_context(org_b.id):
        rol_de_b = Role.objects.get(organization=org_b, code="org_admin")

    respuesta = autenticar(api_client, admin_a).post(
        reverse("accounts:user_role-list"),
        {"user": str(admin_a.id), "role": str(rol_de_b.id)},
        format="json",
    )

    assert respuesta.status_code == 400
    assert "role" in respuesta.json()


@pytest.mark.isolation
def test_no_se_edita_un_rol_de_otra_organizacion(
    api_client, admin_a, admin_b, org_b,
):
    with tenant_context(org_b.id):
        rol_de_b = Role.objects.get(organization=org_b, code="org_admin")

    respuesta = autenticar(api_client, admin_a).patch(
        reverse("accounts:role-detail", args=[rol_de_b.id]),
        {"name": "Robado"}, format="json",
    )

    assert respuesta.status_code == 404

    with tenant_context(org_b.id):
        rol_de_b.refresh_from_db()
        assert rol_de_b.name == "Administrador de Organización"
