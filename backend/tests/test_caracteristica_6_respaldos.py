"""Característica general 6 — Copias de seguridad y restauración.

La consigna dice «funciones para posibilitar las copias de seguridad y
restauración de todo el sistema». En un sistema multi-inquilino eso son dos
cosas y acá se prueba la que es de la aplicación: **la copia de una
organización**, que es lo que un cliente de un SaaS puede exigir llevarse. La
copia de la instalación entera es ``manage.py dump_database`` y es trabajo de
consola, no de la API.

Las pruebas que más importan son las tres que no salen del enunciado:

- que el respaldo de un centro médico **no se pueda restaurar dentro de otro**;
- que la restauración sea **todo o nada**, porque empieza borrando;
- que la **bitácora no vuelva** con el archivo, o restaurar sería la forma de
  borrar el rastro de lo que uno hizo.
"""

import json

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog
from accounts.tokens import tokens_for_user
from audit.actions import Action
from backups import services
from backups.models import BackupRecord
from catalog.models import Specialty
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

PERMISOS_ADMIN = ["backups.backup.create", "backups.backup.restore"]


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


@pytest.fixture
def admin_a(db, org_a, user_a):
    dar_rol(user_a, org_a, "admin_backup", "Administrador", PERMISOS_ADMIN)
    return user_a


@pytest.fixture
def datos_a(db, org_a):
    """Algo que respaldar: tres pacientes y dos especialidades."""
    with tenant_context(org_a.id):
        for nombre, apellido, documento in [
            ("Ana", "Álvarez", "8001"),
            ("Bruno", "Bustos", "8002"),
            ("Carla", "Cárdenas", "8003"),
        ]:
            Patient.objects.create(
                organization=org_a, first_name=nombre, last_name=apellido,
                document_number=documento,
            )
        for nombre in ("Cardiología", "Pediatría"):
            Specialty.objects.create(
                organization=org_a, name=nombre,
                description=f"Atención de {nombre.lower()}",
            )


def descargar(api_client, user):
    """Genera el respaldo por HTTP y devuelve el documento ya parseado."""
    respuesta = autenticar(api_client, user).post(
        reverse("backups:create"), {}, format="json",
    )
    assert respuesta.status_code == 200
    return json.loads(respuesta.content.decode("utf-8")), respuesta


# --------------------------------------------------------------------------
#  La copia
# --------------------------------------------------------------------------
def test_el_respaldo_trae_los_datos_de_la_organizacion(
    api_client, admin_a, datos_a,
):
    documento, respuesta = descargar(api_client, admin_a)

    assert documento["format"] == "plataforma-medica-backup"
    assert documento["organization"]["slug"] == admin_a.organization.slug
    assert documento["counts"]["patients.Patient"] == 3
    assert documento["counts"]["catalog.Specialty"] == 2

    apellidos = {
        fila["fields"]["last_name"]
        for fila in documento["payload"]["patients.Patient"]
    }
    assert apellidos == {"Álvarez", "Bustos", "Cárdenas"}

    assert respuesta["Content-Disposition"].startswith("attachment;")
    assert ".json" in respuesta["Content-Disposition"]


def test_el_respaldo_no_incluye_datos_de_otra_organizacion(
    api_client, org_b, admin_a, datos_a,
):
    """Lo que el proyecto entero existe para impedir, aplicado al respaldo.

    Un archivo que se lleva el cliente es el lugar donde una fuga de
    aislamiento sale del sistema y ya no vuelve.
    """
    with tenant_context(org_b.id):
        Patient.objects.create(
            organization=org_b, first_name="Zulma", last_name="Zapata",
            document_number="8999",
        )

    documento, _ = descargar(api_client, admin_a)
    contenido = json.dumps(documento, ensure_ascii=False)
    assert "Zapata" not in contenido
    assert documento["counts"]["patients.Patient"] == 3


def test_generar_un_respaldo_queda_registrado_y_auditado(
    api_client, org_a, admin_a, datos_a,
):
    documento, _ = descargar(api_client, admin_a)

    with tenant_context(org_a.id):
        registro = BackupRecord.objects.get(kind=BackupRecord.Kind.BACKUP)
        asiento = AuditLog.objects.filter(action=Action.BACKUP_CREATE).first()

    assert registro.performed_by_id == admin_a.id
    assert registro.checksum == documento["checksum"]
    assert registro.total_rows == sum(documento["counts"].values())
    assert asiento is not None


def test_sin_permiso_no_se_puede_bajar_el_respaldo(api_client, org_a, user_a):
    """Es la exportación más completa que existe en el sistema: el padrón,
    los antecedentes y los correos, todo en claro."""
    dar_rol(user_a, org_a, "recepcion", "Recepción", ["patients.patient.read"])
    respuesta = autenticar(api_client, user_a).post(
        reverse("backups:create"), {}, format="json",
    )
    assert respuesta.status_code == 403


def test_el_superadministrador_no_respalda_una_organizacion(
    api_client, platform_admin,
):
    """No pertenece a ninguna y su alcance no incluye los datos de ninguna.
    Para la instalación entera está `manage.py dump_database`."""
    respuesta = autenticar(api_client, platform_admin).post(
        reverse("backups:create"), {}, format="json",
    )
    assert respuesta.status_code in (400, 403)


# --------------------------------------------------------------------------
#  La inspección previa
# --------------------------------------------------------------------------
def test_se_puede_ver_que_trae_el_archivo_sin_restaurar_nada(
    api_client, org_a, admin_a, datos_a,
):
    """Restaurar a ciegas es cómo se pierden los datos que el respaldo venía
    a proteger. Por eso el flujo son dos pasos."""
    documento, _ = descargar(api_client, admin_a)

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:inspect"), {"backup": documento}, format="json",
    )
    assert respuesta.status_code == 200
    assert respuesta.data["belongs_to_my_organization"] is True
    assert respuesta.data["counts"]["patients.Patient"] == 3
    assert "accounts.AuditLog" in respuesta.data["skipped"]

    # No escribió nada.
    with tenant_context(org_a.id):
        assert Patient.objects.count() == 3
        assert not BackupRecord.objects.filter(
            kind=BackupRecord.Kind.RESTORE,
        ).exists()


def test_un_archivo_alterado_se_detecta(api_client, admin_a, datos_a):
    """La suma de verificación no es una firma, pero atrapa el caso real:
    la descarga incompleta y el archivo tocado a mano."""
    documento, _ = descargar(api_client, admin_a)
    documento["payload"]["patients.Patient"][0]["fields"]["last_name"] = "Otro"

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:inspect"), {"backup": documento}, format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "checksum_no_coincide"


def test_un_archivo_que_no_es_un_respaldo_se_rechaza_con_su_motivo(
    api_client, admin_a,
):
    """Subir el archivo equivocado es lo más normal del mundo: tiene que dar
    400 con el motivo, no 500."""
    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:inspect"),
        {"backup": {"hola": "mundo"}}, format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "formato_desconocido"


# --------------------------------------------------------------------------
#  La restauración
# --------------------------------------------------------------------------
def test_la_restauracion_devuelve_los_datos_al_momento_del_respaldo(
    api_client, org_a, admin_a, datos_a,
):
    """El caso de uso entero, de punta a punta."""
    documento, _ = descargar(api_client, admin_a)

    # Pasa el desastre: se borra uno y se agrega otro que no estaba.
    with tenant_context(org_a.id):
        Patient.objects.filter(document_number="8001").delete()
        Patient.objects.create(
            organization=org_a, first_name="Nuevo", last_name="Posterior",
            document_number="8500",
        )
        assert Patient.objects.count() == 3

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )
    assert respuesta.status_code == 200

    with tenant_context(org_a.id):
        apellidos = set(Patient.objects.values_list("last_name", flat=True))

    # Volvió el que faltaba y se fue el posterior: restaurar es volver a un
    # momento, no fusionar dos.
    assert apellidos == {"Álvarez", "Bustos", "Cárdenas"}


def test_no_se_restaura_el_respaldo_de_otra_organizacion(
    api_client, org_a, org_b, admin_a, user_b, datos_a,
):
    """La prueba más importante de esta app.

    RLS no alcanzaría por sí solo: las filas se insertarían bajo el
    `organization_id` de acá, que es el correcto. Lo que estaría mal es el
    contenido —el padrón de otro centro médico, con sus antecedentes— y eso lo
    tiene que impedir la aplicación.
    """
    dar_rol(user_b, org_b, "admin_backup", "Administrador", PERMISOS_ADMIN)

    with tenant_context(org_b.id):
        Patient.objects.create(
            organization=org_b, first_name="Zulma", last_name="Zapata",
            document_number="8999",
        )

    cliente_b = APIClient()
    documento_b, _ = descargar(cliente_b, user_b)

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento_b, "confirm": True}, format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "organizacion_distinta"

    with tenant_context(org_a.id):
        assert Patient.objects.count() == 3
        assert not Patient.objects.filter(last_name="Zapata").exists()


def test_la_restauracion_exige_confirmacion_explicita(
    api_client, org_a, admin_a, datos_a,
):
    """Sin esto, una llamada repetida por un reintento del navegador
    reemplaza la organización."""
    documento, _ = descargar(api_client, admin_a)

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:restore"), {"backup": documento}, format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "confirmacion_requerida"

    with tenant_context(org_a.id):
        assert Patient.objects.count() == 3


def test_la_bitacora_no_vuelve_con_el_respaldo(
    api_client, org_a, admin_a, datos_a,
):
    """Si la bitácora se pudiera reponer desde un archivo del usuario,
    restaurar sería la forma de borrar el rastro de lo que uno hizo.

    Se exporta —quien se lleva sus datos se lleva su bitácora— y se niega a
    volver.
    """
    documento, _ = descargar(api_client, admin_a)
    assert "accounts.AuditLog" in documento["payload"]

    with tenant_context(org_a.id):
        antes = AuditLog.objects.count()
    assert antes > 0

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )
    assert respuesta.status_code == 200
    assert "accounts.AuditLog" in respuesta.data["skipped"]
    assert "accounts.AuditLog" not in respuesta.data["deleted"]

    with tenant_context(org_a.id):
        # No se borró ninguno, y encima quedó el asiento de la restauración.
        assert AuditLog.objects.count() >= antes


def test_restaurar_deja_el_asiento_mas_detallado_de_la_bitacora(
    api_client, org_a, admin_a, datos_a,
):
    """Es la operación más destructiva de la plataforma. La pregunta que se
    hace después es siempre la misma: quién, cuándo y con qué archivo."""
    documento, _ = descargar(api_client, admin_a)

    autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.filter(action=Action.BACKUP_RESTORE).first()
        registro = BackupRecord.objects.get(kind=BackupRecord.Kind.RESTORE)

    assert asiento is not None
    assert asiento.user_id == admin_a.id
    assert asiento.detail["written"]["patients.Patient"] == 3
    assert asiento.detail["generated_at"] == documento["generated_at"]
    assert registro.performed_by_id == admin_a.id


def test_sin_permiso_de_restaurar_no_se_restaura_aunque_se_pueda_respaldar(
    api_client, org_a, user_a, datos_a,
):
    """Respaldar es inofensivo; restaurar destruye. Por eso son dos permisos.

    Una organización puede querer que recepción baje la copia del mes sin
    poder reemplazar la base con un archivo.
    """
    dar_rol(user_a, org_a, "solo_copia", "Sólo copia",
            ["backups.backup.create"])

    documento, _ = descargar(api_client, user_a)

    respuesta = autenticar(api_client, user_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )
    assert respuesta.status_code == 403


def test_una_restauracion_fallida_no_deja_la_organizacion_a_medias(
    api_client, org_a, admin_a, datos_a,
):
    """Todo o nada. Es el único comportamiento aceptable para algo que
    empieza borrando.

    Se rompe el archivo a propósito: un paciente que apunta a un titular
    inexistente. La comprobación de claves salta al cerrar la transacción y
    todo tiene que volver atrás — y responder 400 con el motivo, no un 500:
    un archivo malo no es una falla del servidor.
    """
    documento, _ = descargar(api_client, admin_a)
    documento["payload"]["patients.Patient"][0]["fields"]["guardian"] = (
        "00000000-0000-0000-0000-000000000000"
    )
    # El checksum se recalcula para que falle por la referencia rota y no por
    # la suma de verificación, que es lo que se quiere probar acá.
    documento["checksum"] = services.checksum(documento["payload"])

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )
    assert respuesta.status_code == 400
    assert respuesta.data["code"] == "referencia_rota"

    with tenant_context(org_a.id):
        assert Patient.objects.count() == 3
        assert Specialty.objects.count() == 2


def test_un_usuario_posterior_al_respaldo_se_desactiva_en_vez_de_borrarse(
    api_client, org_a, admin_a, datos_a,
):
    """La única tabla con tratamiento propio, y el porqué.

    `audit_log` y `login_attempts` apuntan al usuario con SET_NULL y
    `app_user` no tiene UPDATE sobre ninguna de las dos: borrar un usuario que
    dejó un asiento es imposible en esta base, y está bien que lo sea. La baja
    lógica es la misma decisión que US-10 tomó para los pacientes.
    """
    from accounts.models import User

    documento, _ = descargar(api_client, admin_a)

    with tenant_context(org_a.id):
        posterior = User.objects.create_user(
            organization=org_a, email="posterior@a.test",
            password="clave-de-prueba-1", first_name="Pos", last_name="Terior",
        )

    respuesta = autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )
    assert respuesta.status_code == 200
    assert respuesta.data["deactivated"]["accounts.User"] == 1
    # No figura entre lo borrado: a `users` no se le borra nada.
    assert "accounts.User" not in respuesta.data["deleted"]

    with tenant_context(org_a.id):
        posterior.refresh_from_db()
        assert posterior.is_active is False
        # Y el que sí estaba en el respaldo sigue activo.
        assert User.objects.get(pk=admin_a.pk).is_active is True


# --------------------------------------------------------------------------
#  El historial
# --------------------------------------------------------------------------
def test_el_historial_lista_copias_y_restauraciones(
    api_client, admin_a, datos_a,
):
    """Quien administra tiene que poder contestar «¿cuándo fue el último
    respaldo?» sin buscar en su carpeta de descargas."""
    documento, _ = descargar(api_client, admin_a)
    autenticar(api_client, admin_a).post(
        reverse("backups:restore"),
        {"backup": documento, "confirm": True}, format="json",
    )

    respuesta = autenticar(api_client, admin_a).get(
        reverse("backups:record-list"),
    )
    assert respuesta.status_code == 200
    tipos = [r["kind"] for r in respuesta.data["results"]]
    assert sorted(tipos) == ["backup", "restore"]

    copia = next(r for r in respuesta.data["results"] if r["kind"] == "backup")
    assert copia["kind_label"] == "Copia de seguridad"
    # El detalle sale con nombres legibles y sin las tablas en cero.
    etiquetas = {d["label"] for d in copia["detail"]}
    assert "Pacientes" in etiquetas
    assert all(d["rows"] > 0 for d in copia["detail"])


def test_el_historial_no_expone_el_del_vecino(
    api_client, org_b, user_b, admin_a, datos_a,
):
    """El tamaño y el conteo de filas describen el tamaño del negocio del
    otro inquilino."""
    descargar(api_client, admin_a)

    dar_rol(user_b, org_b, "admin_backup", "Administrador", PERMISOS_ADMIN)
    cliente_b = APIClient()
    respuesta = autenticar(cliente_b, user_b).get(
        reverse("backups:record-list"),
    )
    assert respuesta.data["results"] == []
