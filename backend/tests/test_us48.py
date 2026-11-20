"""US-48 — Calificación de la atención con estrellas.

Los bordes de la regla 17 que pide la ampliación del 17/11:
- calificar una atención que no es tuya o que no está firmada;
- calificar dos veces;
- corregir pasados los 7 días;
- estrellas en 0, 6 o no numéricas, y un comentario de 501 caracteres;
- otra organización;
- que el médico no vea el nombre del paciente en ningún endpoint.

Lo que importa además se prueba **contra la base**: que una calificación no se
borre, no se ponga sobre un borrador y no se cambie pasados los 7 días aunque
alguien salte la API.
"""

import datetime as dt

import pytest
from django.db import connection, transaction
from django.db.utils import DatabaseError
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from encounters.models import Encounter, EncounterRating
from patients.models import Patient
from tenancy.context import tenant_context

from .conftest import dar_rol
from .test_us24 import (  # noqa: F401  (fixtures reutilizadas)
    LA_PAZ,
    _ficha,
    _medico,
    abrir,
    cliente,
    ficha_hoy,
    firmado,
    medico_a,
    otro_medico_a,
    paciente,
)

pytestmark = pytest.mark.django_db


def url(encuentro_id):
    return reverse("encounters:rating", args=[encuentro_id])


def calificar(user, encuentro_id, stars=5, comment="Muy buena atención."):
    return cliente(user).post(url(encuentro_id), {"stars": stars, "comment": comment},
                              format="json")


def corregir(user, encuentro_id, stars=3, comment=""):
    return cliente(user).patch(url(encuentro_id), {"stars": stars, "comment": comment},
                               format="json")


@pytest.fixture
def atencion(medico_a, ficha_hoy):
    """El id de una atención firmada de Pedro con Laura, en la Sede Centro."""
    return firmado(medico_a, ficha_hoy)


@pytest.fixture
def pedro(org_a, paciente, user_a):
    """`user_a` es Pedro: el paciente de la atención, con el rol Paciente."""
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    dar_rol(user_a, org_a, "paciente-48", "Paciente", ["encounters.history.read"])
    return user_a


@pytest.fixture
def admin_a(org_a):
    with tenant_context(org_a.id):
        user = User.objects.create_user(
            email="admin@kolping.test", password="clave-de-prueba-1",
            organization=org_a, first_name="Marta", last_name="Paz",
            document_number="8001",
        )
    dar_rol(user, org_a, "admin-48", "Administrador", ["reporting.kpi.read"])
    return user


def _rating(org, encuentro_id):
    with tenant_context(org.id):
        return EncounterRating.objects.filter(encounter_id=encuentro_id).first()


# --------------------------------------------------------------------------
#  Calificar
# --------------------------------------------------------------------------

def test_el_paciente_califica_su_atencion(atencion, pedro, org_a, practitioner_a,
                                          branches_a):
    r = calificar(pedro, atencion, stars=4, comment="  Puntual y amable.  ")
    assert r.status_code == 201, r.content
    assert r.json()["rating"]["stars"] == 4
    assert r.json()["rating"]["comment"] == "Puntual y amable."
    assert r.json()["rating"]["editable"] is True

    guardada = _rating(org_a, atencion)
    # Médico y sede se copian del encuentro, no vienen del cliente.
    assert guardada.practitioner_id == practitioner_a.id
    assert guardada.branch_id == branches_a["centro"].id
    assert guardada.rated_by_id == pedro.id


def test_el_comentario_es_opcional(atencion, pedro):
    r = cliente(pedro).post(url(atencion), {"stars": 5}, format="json")
    assert r.status_code == 201
    assert r.json()["rating"]["comment"] == ""


def test_el_historial_propio_trae_la_calificacion(atencion, pedro, paciente):
    calificar(pedro, atencion, stars=3)
    datos = cliente(pedro).get(reverse("encounters:history", args=[paciente.id])).json()
    assert datos["encounters"][0]["rating"]["stars"] == 3


def test_el_titular_califica_la_atencion_de_su_dependiente(
    atencion, org_a, paciente, user_a,
):
    with tenant_context(org_a.id):
        titular = Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
        Patient.objects.filter(pk=paciente.pk).update(
            guardian=titular, relationship=Patient.Relationship.OTHER)
    dar_rol(user_a, org_a, "titular-48", "Paciente", ["encounters.history.read"])
    assert calificar(user_a, atencion).status_code == 201


def test_no_se_califica_una_atencion_ajena(atencion, org_a, user_a):
    # Ana es paciente del centro, pero la atención es de Pedro.
    with tenant_context(org_a.id):
        Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
    dar_rol(user_a, org_a, "paciente-48", "Paciente", ["encounters.history.read"])
    assert calificar(user_a, atencion).status_code == 404
    assert cliente(user_a).get(url(atencion)).status_code == 404


def test_el_medico_no_califica_aunque_lea_el_historial(atencion, medico_a):
    assert calificar(medico_a, atencion).status_code == 404


def test_no_se_califica_un_borrador(medico_a, ficha_hoy, pedro):
    borrador = abrir(medico_a, ficha_hoy).json()["id"]
    assert calificar(pedro, borrador).status_code == 404


def test_sin_el_permiso_no_se_entra(atencion, org_a, paciente, user_a):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    assert calificar(user_a, atencion).status_code == 403


def test_otra_organizacion_no_califica(atencion, org_b, user_b):
    dar_rol(user_b, org_b, "paciente-48", "Paciente", ["encounters.history.read"])
    assert calificar(user_b, atencion).status_code == 404


@pytest.mark.parametrize("stars", [0, 6, -1, "cinco", None, 4.5])
def test_estrellas_fuera_de_rango_o_no_numericas(atencion, pedro, stars):
    r = calificar(pedro, atencion, stars=stars)
    assert r.status_code == 400
    assert "stars" in r.json()


def test_un_comentario_de_501_caracteres(atencion, pedro):
    assert calificar(pedro, atencion, comment="a" * 501).status_code == 400
    assert calificar(pedro, atencion, comment="a" * 500).status_code == 201


# --------------------------------------------------------------------------
#  Una sola, que se corrige durante 7 días
# --------------------------------------------------------------------------

def test_no_se_califica_dos_veces(atencion, pedro, org_a):
    assert calificar(pedro, atencion, stars=5).status_code == 201
    r = calificar(pedro, atencion, stars=1)
    assert r.status_code == 409
    assert r.json()["code"] == "already_rated"
    assert _rating(org_a, atencion).stars == 5
    with tenant_context(org_a.id):
        assert EncounterRating.objects.filter(encounter_id=atencion).count() == 1


def test_se_corrige_dentro_de_los_7_dias(atencion, pedro, org_a):
    calificar(pedro, atencion, stars=2)
    r = corregir(pedro, atencion, stars=4, comment="Lo pensé mejor.")
    assert r.status_code == 200
    assert _rating(org_a, atencion).stars == 4


def test_corregir_sin_haber_calificado(atencion, pedro):
    r = corregir(pedro, atencion)
    assert r.status_code == 409
    assert r.json()["code"] == "not_rated"


def _envejecer(org, encuentro_id, dias):
    """Inserta la calificación con fecha vieja: el trigger no deja moverla."""
    with tenant_context(org.id):
        e = Encounter.objects.get(pk=encuentro_id)
        hace = timezone.now() - dt.timedelta(days=dias)
        with connection.cursor() as c:
            c.execute(
                """INSERT INTO encounter_ratings
                   (id, organization_id, encounter_id, patient_id, practitioner_id,
                    branch_id, rated_by_id, stars, comment, created_at, updated_at)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, 2, '', %s, %s)""",
                [org.id, e.id, e.patient_id, e.practitioner_id, e.branch_id,
                 e.signed_by_id, hace, hace],
            )


def test_pasados_los_7_dias_no_se_corrige(atencion, pedro, org_a):
    _envejecer(org_a, atencion, 8)
    r = corregir(pedro, atencion, stars=5)
    assert r.status_code == 409
    assert r.json()["code"] == "rating_locked"
    datos = cliente(pedro).get(url(atencion)).json()
    assert datos["rating"]["editable"] is False


def test_pasados_los_7_dias_la_base_tampoco_deja(atencion, org_a):
    _envejecer(org_a, atencion, 8)
    with tenant_context(org_a.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            EncounterRating.objects.filter(encounter_id=atencion).update(stars=5)


# --------------------------------------------------------------------------
#  Lo que la base hace cumplir
# --------------------------------------------------------------------------

def test_la_base_no_deja_borrar_una_calificacion(atencion, pedro, org_a):
    calificar(pedro, atencion)
    with tenant_context(org_a.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            EncounterRating.objects.filter(encounter_id=atencion).delete()


def test_la_base_no_deja_calificar_un_borrador(medico_a, ficha_hoy, org_a, pedro):
    borrador = abrir(medico_a, ficha_hoy).json()["id"]
    with tenant_context(org_a.id):
        e = Encounter.objects.get(pk=borrador)
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterRating.objects.create(
                organization=org_a, encounter=e, patient_id=e.patient_id,
                practitioner_id=e.practitioner_id, branch_id=e.branch_id,
                rated_by=pedro, stars=5,
            )


def test_la_base_no_deja_estrellas_fuera_de_rango(atencion, pedro, org_a):
    calificar(pedro, atencion)
    with tenant_context(org_a.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            EncounterRating.objects.filter(encounter_id=atencion).update(stars=6)


def test_la_base_no_deja_cambiar_de_atencion_ni_de_autor(atencion, pedro, org_a,
                                                         medico_a):
    calificar(pedro, atencion)
    with tenant_context(org_a.id), pytest.raises(DatabaseError):
        with transaction.atomic():
            EncounterRating.objects.filter(encounter_id=atencion).update(
                rated_by=medico_a)


def test_otra_organizacion_no_ve_las_calificaciones(atencion, pedro, org_b):
    calificar(pedro, atencion)
    with tenant_context(org_b.id):
        assert EncounterRating.objects.count() == 0


# --------------------------------------------------------------------------
#  El médico ve su promedio, nunca quién
# --------------------------------------------------------------------------

def test_el_medico_ve_su_promedio(atencion, pedro, medico_a):
    calificar(pedro, atencion, stars=4)
    datos = cliente(medico_a).get(reverse("encounters:my-ratings")).json()
    assert datos["average"] == 4.0
    assert datos["count"] == 1
    assert datos["distribution"][3] == {"stars": 4, "total": 1}


def test_otro_medico_no_ve_las_estrellas_ajenas(atencion, pedro, otro_medico_a):
    calificar(pedro, atencion, stars=4)
    datos = cliente(otro_medico_a).get(reverse("encounters:my-ratings")).json()
    assert datos["count"] == 0
    assert datos["average"] is None


def test_el_medico_no_ve_el_nombre_del_paciente_en_ningun_endpoint(
    atencion, pedro, medico_a, paciente,
):
    calificar(pedro, atencion, stars=2, comment="Me hizo esperar mucho.")
    api = cliente(medico_a)

    mio = api.get(reverse("encounters:my-ratings"))
    assert mio.status_code == 200
    texto = mio.content.decode()
    for dato in ("Pedro", "Mamani", "Me hizo esperar", str(paciente.id), str(atencion)):
        assert dato not in texto

    # En el historial que lee como profesional, la calificación no viaja.
    historial = api.get(reverse("encounters:history", args=[paciente.id])).json()
    assert all("rating" not in e for e in historial["encounters"])

    # Y la calificación de la atención tampoco la puede pedir.
    assert api.get(url(atencion)).status_code == 404
    # Ni el tablero del administrador.
    assert api.get(reverse("reporting:satisfaction")).status_code == 403


# --------------------------------------------------------------------------
#  El tablero del administrador
# --------------------------------------------------------------------------

@pytest.fixture
def dos_calificaciones(atencion, pedro, org_a, branches_a, paciente, user_a,
                       otro_medico_a):
    """Pedro le pone 5 a Laura (Sede Centro) y 2 a Diego (Sede Norte)."""
    calificar(pedro, atencion, stars=5, comment="Excelente.")
    from catalog.models import Practitioner
    with tenant_context(org_a.id):
        diego = Practitioner.objects.get(user=otro_medico_a)
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    ficha = _ficha(org_a, diego, branches_a["norte"], paciente, user_a,
                   ahora - dt.timedelta(hours=1))
    otra = firmado(otro_medico_a, ficha)
    calificar(pedro, otra, stars=2, comment="")
    return atencion, otra


def test_el_admin_ve_promedios_y_distribucion(dos_calificaciones, admin_a):
    datos = cliente(admin_a).get(reverse("reporting:satisfaction")).json()
    assert datos["count"] == 2
    assert datos["average"] == 3.5
    assert [d["total"] for d in datos["distribution"]] == [0, 1, 0, 0, 1]
    assert {(m["name"], m["average"]) for m in datos["by_practitioner"]} == {
        ("Laura Gómez", 5.0), ("Diego Ríos", 2.0),
    }
    assert {(s["name"], s["count"]) for s in datos["by_branch"]} == {
        ("Sede Centro", 1), ("Sede Norte", 1),
    }
    # Laura es de Cardiología; Diego no tiene especialidad cargada.
    assert {s["name"] for s in datos["by_specialty"]} == {"Cardiología", "Sin especialidad"}


def test_los_comentarios_del_admin_no_traen_al_paciente(dos_calificaciones, admin_a):
    datos = cliente(admin_a).get(reverse("reporting:satisfaction")).json()
    assert [c["comment"] for c in datos["latest_comments"]] == ["Excelente."]
    assert set(datos["latest_comments"][0]) == {
        "stars", "comment", "practitioner_name", "branch_name", "created_at",
    }
    assert "Pedro" not in str(datos) and "Mamani" not in str(datos)


def test_el_admin_filtra_por_sede(dos_calificaciones, admin_a, branches_a):
    datos = cliente(admin_a).get(reverse("reporting:satisfaction"),
                                 {"branch": str(branches_a["norte"].id)}).json()
    assert datos["count"] == 1
    assert datos["average"] == 2.0


def test_un_rango_sin_calificaciones_da_cero(dos_calificaciones, admin_a):
    datos = cliente(admin_a).get(reverse("reporting:satisfaction"),
                                 {"from": "2020-01-01", "to": "2020-01-31"}).json()
    assert datos["count"] == 0
    assert datos["average"] is None
    assert datos["by_practitioner"] == []


def test_fechas_invalidas_en_el_tablero(admin_a):
    r = cliente(admin_a).get(reverse("reporting:satisfaction"), {"from": "ayer"})
    assert r.status_code == 400


def test_el_admin_de_otra_organizacion_no_ve_nada(dos_calificaciones, org_b, user_b):
    dar_rol(user_b, org_b, "admin-48", "Administrador", ["reporting.kpi.read"])
    datos = cliente(user_b).get(reverse("reporting:satisfaction")).json()
    assert datos["count"] == 0


def test_el_paciente_no_entra_al_tablero(dos_calificaciones, pedro):
    assert cliente(pedro).get(reverse("reporting:satisfaction")).status_code == 403
