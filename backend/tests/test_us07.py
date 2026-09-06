"""US-07 — Pacientes dependientes.

Todas entran por HTTP: lo que se prueba es que el titular sólo alcanza lo suyo,
y eso vive en la vista y en el contexto de inquilino que fija la autenticación.

El bloque final es el criterio 4 de la Definition of Done: aislamiento
comprobado (RNF-08). Acá tiene dos capas, porque el caso las tiene: un titular
de la organización A no ve nada de la B, y un titular de la organización A
tampoco ve a los dependientes de su propio vecino de organización.
"""

import datetime as dt

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AuditLog, Permission, Role, RolePermission, User, UserRole
from accounts.tokens import tokens_for_user
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol

pytestmark = pytest.mark.django_db

CLAVE = "clave-de-prueba-1"

PERMISOS_DEPENDIENTES = [
    "patients.dependent.read",
    "patients.dependent.write",
]


@pytest.fixture
def api_client():
    return APIClient()


def autenticar(api_client, user):
    api_client.credentials(
        HTTP_AUTHORIZATION=f"Bearer {tokens_for_user(user)['access']}",
    )
    return api_client


def dar_rol_paciente(user, organization):
    """Le da a `user` el rol *Paciente* de su organización, creándolo una sola vez.

    No se usa `conftest.dar_rol` porque el código de rol es único por
    organización (`uq_role_code_org`) y estas pruebas necesitan **dos**
    pacientes en el mismo centro médico para comprobar que uno no ve a los
    dependientes del otro.

    Es también el rol que busca la promoción a titular del punto (f), que lo
    resuelve por el código `patient`.
    """
    with tenant_context(organization.id):
        role, creado = Role.objects.get_or_create(
            organization=organization, code="patient",
            defaults={"name": "Paciente"},
        )
        if creado:
            RolePermission.objects.bulk_create([
                RolePermission(
                    role=role, permission=permission, organization=organization,
                )
                for permission in Permission.objects.filter(
                    code__in=PERMISOS_DEPENDIENTES,
                )
            ])
        UserRole.objects.create(user=user, role=role, organization=organization)
    return role


def ficha_de(user, organization, **extra):
    """La ficha de paciente titular de una cuenta que ya existe."""
    with tenant_context(organization.id):
        return Patient.objects.create(
            organization=organization,
            user=user,
            document_type=Patient.DocumentType.CI,
            document_number=extra.pop("document_number", user.document_number),
            first_name=user.first_name,
            last_name=user.last_name,
            birth_date=extra.pop("birth_date", dt.date(1990, 5, 20)),
            **extra,
        )


@pytest.fixture
def titular_a(db, org_a, user_a):
    """`user_a` con su ficha de paciente y los permisos de la historia."""
    dar_rol_paciente(user_a, org_a)
    ficha_de(user_a, org_a)
    return user_a


@pytest.fixture
def titular_b(db, org_b, user_b):
    dar_rol_paciente(user_b, org_b)
    ficha_de(user_b, org_b)
    return user_b


@pytest.fixture
def otro_titular_a(db, org_a):
    """Un segundo paciente de la MISMA organización que `titular_a`."""
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="carla@kolping.test", password=CLAVE, organization=org_a,
            first_name="Carla", last_name="Vaca", document_number="5003",
        )
    dar_rol_paciente(user, org_a)
    ficha_de(user, org_a)
    return user


def alta(api_client, user, **datos):
    cuerpo = {
        "first_name": "Mateo",
        "last_name": "Ríos",
        "relationship": "child",
        "birth_date": "2020-03-15",
        "sex": "M",
    }
    cuerpo.update(datos)
    return autenticar(api_client, user).post(
        reverse("patients:dependent-list"), cuerpo, format="json",
    )


# --------------------------------------------------------------------------
#  Puntos (a) y (b) — ficha demográfica sin cuenta de acceso
# --------------------------------------------------------------------------

def test_un_menor_sin_documento_se_registra_con_su_titular(
    api_client, titular_a, org_a,
):
    """Es el caso que da sentido a la historia: un recién nacido no tiene
    documento y no puede tener cuenta de correo, y hay que poder atenderlo."""
    respuesta = alta(api_client, titular_a)

    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["full_name"] == "Mateo Ríos"
    assert cuerpo["relationship_label"] == "Hijo/a"
    assert cuerpo["document_number"] is None

    with tenant_context(org_a.id):
        dependiente = Patient.objects.get(id=cuerpo["id"])
        assert dependiente.guardian_id == titular_a.patient_profile.id
        assert dependiente.organization_id == org_a.id


def test_el_dependiente_no_es_un_usuario(api_client, titular_a, org_a):
    """Punto (b). La distinción entre persona atendida y credencial es la que
    hace posible el caso: si el dependiente tuviera que ser un usuario, un
    recién nacido necesitaría un correo para poder ser atendido."""
    with tenant_context(org_a.id):
        cuentas_antes = User.objects.count()

    respuesta = alta(api_client, titular_a)
    assert respuesta.status_code == 201

    with tenant_context(org_a.id):
        assert User.objects.count() == cuentas_antes
        assert Patient.objects.get(id=respuesta.json()["id"]).user_id is None


def test_el_parentesco_es_obligatorio(api_client, titular_a):
    """Punto (a). Un dependiente sin parentesco no dice de quién es qué, y la
    base lo rechazaría igual con `ck_patient_relationship`."""
    respuesta = alta(api_client, titular_a, relationship="")

    assert respuesta.status_code == 400
    assert "relationship" in respuesta.json()


def test_el_alta_queda_en_la_bitacora(api_client, titular_a, org_a):
    respuesta = alta(api_client, titular_a)

    with tenant_context(org_a.id):
        asiento = AuditLog.objects.get(entity_id=respuesta.json()["id"])
    assert asiento.detail["alta"] == "dependiente"
    assert asiento.user_id == titular_a.id


# --------------------------------------------------------------------------
#  Punto (c) — documento repetido: se vincula, no se duplica
# --------------------------------------------------------------------------

@pytest.fixture
def ficha_suelta(db, org_a):
    """Una ficha que ya existe en el padrón, sin cuenta y sin titular."""
    with tenant_context(org_a.id):
        return Patient.objects.create(
            organization=org_a,
            document_type=Patient.DocumentType.CI,
            document_number="9001",
            first_name="José",
            last_name="Peña",
            birth_date=dt.date(2015, 7, 1),
        )


def test_un_documento_ya_registrado_no_crea_un_duplicado(
    api_client, titular_a, org_a, ficha_suelta,
):
    respuesta = alta(
        api_client, titular_a,
        first_name="José", last_name="Peña",
        document_number="9001", birth_date="2015-07-01",
    )

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "documento_existente"
    assert cuerpo["can_link"] is True

    with tenant_context(org_a.id):
        assert Patient.objects.filter(document_number="9001").count() == 1


def test_la_respuesta_no_revela_de_quien_es_la_ficha(
    api_client, titular_a, ficha_suelta,
):
    """Si el 409 dijera el nombre, la pantalla de alta sería una forma de
    averiguar quién está registrado en el centro médico tipeando documentos."""
    respuesta = alta(
        api_client, titular_a,
        first_name="Cualquier", last_name="Cosa",
        document_number="9001", birth_date="2000-01-01",
    )

    texto = respuesta.content.decode()
    assert "Peña" not in texto
    assert "José" not in texto
    assert str(ficha_suelta.id) not in texto


def test_confirmando_con_los_datos_correctos_se_vincula_la_ficha_existente(
    api_client, titular_a, org_a, ficha_suelta,
):
    respuesta = alta(
        api_client, titular_a,
        first_name="jose", last_name="PEÑA",   # sin tildes y en mayúsculas
        document_number="9001", birth_date="2015-07-01",
        relationship="ward", confirm_link=True,
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == str(ficha_suelta.id)

    with tenant_context(org_a.id):
        ficha_suelta.refresh_from_db()
        assert ficha_suelta.guardian_id == titular_a.patient_profile.id
        assert ficha_suelta.relationship == "ward"
        # Sigue siendo la MISMA ficha: el historial no se parte en dos.
        assert Patient.objects.filter(document_number="9001").count() == 1


def test_no_se_vincula_una_ficha_ajena_sabiendo_solo_el_documento(
    api_client, titular_a, ficha_suelta,
):
    """El vínculo da el mismo alcance sobre el dependiente que sobre uno mismo
    (punto d). Sin esta comprobación, saber un número de documento alcanzaría
    para leerle el historial a un desconocido."""
    respuesta = alta(
        api_client, titular_a,
        first_name="Otro", last_name="Nombre",
        document_number="9001", birth_date="2015-07-01",
        confirm_link=True,
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "datos_no_coinciden"


def test_no_se_vincula_una_ficha_que_ya_tiene_cuenta(
    api_client, titular_a, otro_titular_a,
):
    respuesta = alta(
        api_client, titular_a,
        first_name=otro_titular_a.first_name,
        last_name=otro_titular_a.last_name,
        document_number=otro_titular_a.document_number,
        confirm_link=True,
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "ficha_con_cuenta"


# --------------------------------------------------------------------------
#  Punto (g) — tope de dependientes
# --------------------------------------------------------------------------

def test_el_tope_de_dependientes_se_respeta(api_client, titular_a, settings):
    settings.PATIENT_MAX_DEPENDENTS = 2

    assert alta(api_client, titular_a, first_name="Uno").status_code == 201
    assert alta(api_client, titular_a, first_name="Dos").status_code == 201

    tercero = alta(api_client, titular_a, first_name="Tres")
    assert tercero.status_code == 409
    assert tercero.json()["code"] == "limite_de_dependientes"


# --------------------------------------------------------------------------
#  Punto (e) — la baja es del vínculo, no de la ficha
# --------------------------------------------------------------------------

def test_la_baja_del_vinculo_no_borra_la_ficha(
    api_client, titular_a, org_a, ficha_suelta,
):
    """La historia clínica es longitudinal y sobrevive al vínculo."""
    alta(
        api_client, titular_a,
        first_name="José", last_name="Peña",
        document_number="9001", birth_date="2015-07-01",
        confirm_link=True,
    )

    respuesta = autenticar(api_client, titular_a).delete(
        reverse("patients:dependent-detail", args=[ficha_suelta.id]),
    )

    assert respuesta.status_code == 204
    with tenant_context(org_a.id):
        ficha_suelta.refresh_from_db()
        assert ficha_suelta.guardian_id is None
        assert ficha_suelta.is_active is True
        assert ficha_suelta.relationship == ""


def test_no_se_desvincula_una_ficha_sin_documento(
    api_client, titular_a, org_a,
):
    """La base no admite una ficha sin documento y sin titular: nadie
    respondería por ella. Se explica en vez de reventar con un error de
    integridad."""
    creado = alta(api_client, titular_a).json()

    respuesta = autenticar(api_client, titular_a).delete(
        reverse("patients:dependent-detail", args=[creado["id"]]),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "sin_documento"


# --------------------------------------------------------------------------
#  Punto (f) — paso a titular
# --------------------------------------------------------------------------

def test_un_menor_no_pasa_a_titular(api_client, titular_a):
    creado = alta(
        api_client, titular_a, document_number="9100", birth_date="2020-03-15",
    ).json()

    respuesta = autenticar(api_client, titular_a).post(
        reverse("patients:dependent-promote", args=[creado["id"]]),
        {"email": "mateo@kolping.test", "password": CLAVE,
         "password_confirmation": CLAVE},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "menor_de_edad"


def test_al_cumplir_la_mayoria_de_edad_conserva_su_ficha_y_su_historial(
    api_client, titular_a, org_a,
):
    """Punto (f). La ficha es la misma —mismo uuid—: crear una nueva partiría
    el historial en dos justo en el cumpleaños número dieciocho."""
    hace_veinte_anios = dt.date.today().replace(year=dt.date.today().year - 20)
    creado = alta(
        api_client, titular_a,
        first_name="Ana", last_name="Ríos",
        document_number="9200", birth_date=hace_veinte_anios.isoformat(),
    ).json()

    respuesta = autenticar(api_client, titular_a).post(
        reverse("patients:dependent-promote", args=[creado["id"]]),
        {"email": "ana.hija@kolping.test", "password": CLAVE,
         "password_confirmation": CLAVE},
        format="json",
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["id"] == creado["id"]

    with tenant_context(org_a.id):
        ficha = Patient.objects.get(id=creado["id"])
        assert ficha.user is not None
        assert ficha.user.email == "ana.hija@kolping.test"
        assert ficha.guardian_id is None
        assert ficha.relationship == ""
        # Le quedó asignado el rol Paciente de su organización, que es de
        # donde salen sus permisos: la ficha promocionada no nace sin nada.
        assert UserRole.objects.filter(
            user=ficha.user, role__code="patient",
        ).exists()
        assert ficha.user.has_permission("patients.dependent.read")

    # Y deja de figurar entre los que el titular tiene a cargo.
    listado = autenticar(api_client, titular_a).get(
        reverse("patients:dependent-list"),
    )
    assert listado.json()["count"] == 0


def test_no_se_promociona_con_un_correo_ya_usado(
    api_client, titular_a, org_a, otro_titular_a,
):
    hace_veinte_anios = dt.date.today().replace(year=dt.date.today().year - 20)
    creado = alta(
        api_client, titular_a,
        document_number="9300", birth_date=hace_veinte_anios.isoformat(),
    ).json()

    respuesta = autenticar(api_client, titular_a).post(
        reverse("patients:dependent-promote", args=[creado["id"]]),
        {"email": otro_titular_a.email, "password": CLAVE,
         "password_confirmation": CLAVE},
        format="json",
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "correo_en_uso"


# --------------------------------------------------------------------------
#  Punto (h) — el selector compartido
# --------------------------------------------------------------------------

def test_el_selector_trae_al_titular_primero_y_despues_a_los_suyos(
    api_client, titular_a,
):
    """Lo consume US-08 y lo va a consumir la reserva del Sprint 2. El titular
    va primero porque reservar para uno mismo es el caso más común."""
    alta(api_client, titular_a, first_name="Mateo")

    respuesta = autenticar(api_client, titular_a).get(
        reverse("patients:dependent-options-for-selector"),
    )

    assert respuesta.status_code == 200
    opciones = respuesta.json()
    assert len(opciones) == 2
    assert opciones[0]["is_self"] is True
    assert opciones[0]["relationship_label"] == "Yo"
    assert opciones[1]["is_self"] is False
    assert opciones[1]["full_name"] == "Mateo Ríos"


def test_quien_no_tiene_ficha_de_paciente_recibe_una_explicacion(
    api_client, org_a, user_a,
):
    """Un administrador tiene cuenta pero no ficha. Devolverle una lista vacía
    parecería que se perdieron los datos."""
    dar_rol(user_a, org_a, "admin", "Admin", PERMISOS_DEPENDIENTES)

    respuesta = autenticar(api_client, user_a).get(
        reverse("patients:dependent-list"),
    )

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "sin_ficha_de_paciente"


def test_sin_permiso_no_se_listan_dependientes(api_client, org_a, user_a):
    dar_rol(user_a, org_a, "pelado", "Sin permisos", [])

    respuesta = autenticar(api_client, user_a).get(
        reverse("patients:dependent-list"),
    )

    assert respuesta.status_code == 403


# --------------------------------------------------------------------------
#  Aislamiento (RNF-08). Criterio 4 de la Definition of Done.
# --------------------------------------------------------------------------

def test_un_titular_no_ve_los_dependientes_de_otro_de_su_organizacion(
    api_client, titular_a, otro_titular_a,
):
    """El aislamiento por inquilino no alcanza acá: los dos son de la misma
    organización. Lo que separa es el vínculo."""
    alta(api_client, titular_a, first_name="Mateo")

    respuesta = autenticar(api_client, otro_titular_a).get(
        reverse("patients:dependent-list"),
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["count"] == 0


def test_un_titular_no_alcanza_el_dependiente_de_otro_por_su_id(
    api_client, titular_a, otro_titular_a,
):
    creado = alta(api_client, titular_a, first_name="Mateo").json()

    respuesta = autenticar(api_client, otro_titular_a).get(
        reverse("patients:dependent-detail", args=[creado["id"]]),
    )

    assert respuesta.status_code == 404


def test_un_titular_no_ve_ni_vincula_fichas_de_otra_organizacion(
    api_client, titular_a, titular_b, org_a, org_b,
):
    with tenant_context(org_b.id):
        ajena = Patient.objects.create(
            organization=org_b,
            document_type=Patient.DocumentType.CI,
            document_number="9001",
            first_name="José", last_name="Peña",
            birth_date=dt.date(2015, 7, 1),
        )

    # Mismo documento, misma persona, otra organización: se crea una ficha
    # nueva en la organización de quien pide. La unicidad es por inquilino.
    respuesta = alta(
        api_client, titular_a,
        first_name="José", last_name="Peña",
        document_number="9001", birth_date="2015-07-01",
    )

    assert respuesta.status_code == 201
    assert respuesta.json()["id"] != str(ajena.id)

    with tenant_context(org_a.id):
        assert Patient.objects.filter(document_number="9001").count() == 1
    with tenant_context(org_b.id):
        assert Patient.objects.get(document_number="9001").id == ajena.id


def test_rls_esconde_las_fichas_ajenas_en_el_orm(titular_a, titular_b, org_a, org_b):
    with tenant_context(org_a.id):
        propias = set(Patient.objects.values_list("organization_id", flat=True))
    assert propias == {org_a.id}

    with tenant_context(org_b.id):
        propias = set(Patient.objects.values_list("organization_id", flat=True))
    assert propias == {org_b.id}
