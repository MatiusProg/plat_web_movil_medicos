"""US-47 — Chat entre el paciente atendido y el médico de esa atención.

Lo que se prueba (regla 17 del Sprint 4: los bordes, no sólo el camino feliz):

- el chat nace de una atención **firmada**: un borrador no tiene chat;
- entra el paciente o el titular del dependiente, y el médico de la atención.
  Otro médico del centro, otro paciente y otra organización reciben 404;
- la ventana: vencida o cerrada por el médico, nadie escribe;
- la barrera de urgencias de US-34 marca el mensaje del paciente y la
  respuesta trae la derivación; el del médico nunca se marca;
- los sin leer de la bandeja del médico;
- el push al paciente sale después del COMMIT, sin el texto, y si falla el
  mensaje queda guardado igual;
- la base no deja editar ni borrar mensajes, ni reabrir una conversación;
- la bitácora sabe que hubo un mensaje, nunca lo que dice;
- las copias llevan la conversación y restaurar no la borra.
"""

import datetime as dt
import uuid

import pytest
from django.db import transaction
from django.db.utils import DatabaseError
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AuditLog
from encounters.models import Encounter
from messaging import services
from messaging.models import EncounterMessage, EncounterThread
from patients.models import Patient
from tenancy.context import tenant_context

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

URGENCIA = "Desde que tomo el remedio me duele el pecho y no puedo respirar."
CONSULTA = "¿El paracetamol lo tomo antes o después de comer?"


def _chat(user, org):
    dar_rol(user, org, f"chat-{user.document_number}", "Chat", ["encounters.chat"])
    return user


@pytest.fixture
def laura(medico_a, org_a):
    return _chat(medico_a, org_a)


@pytest.fixture
def diego(otro_medico_a, org_a):
    return _chat(otro_medico_a, org_a)


@pytest.fixture
def pedro(paciente, org_a, user_a):
    """El paciente de la atención, con cuenta y con el permiso del chat."""
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    return _chat(user_a, org_a)


@pytest.fixture
def encuentro(laura, ficha_hoy):
    return firmado(laura, ficha_hoy)


def ver(user, encuentro_id):
    return cliente(user).get(reverse("messaging:chat", args=[encuentro_id]))


def escribir(user, encuentro_id, body):
    return cliente(user).post(reverse("messaging:send", args=[encuentro_id]),
                              {"body": body}, format="json")


def cerrar(user, encuentro_id):
    return cliente(user).post(reverse("messaging:close", args=[encuentro_id]))


def bandeja(user):
    return cliente(user).get(reverse("messaging:inbox"))


def _mensajes(org):
    with tenant_context(org.id):
        return list(EncounterMessage.objects.order_by("created_at"))


# --------------------------------------------------------------------------
#  El camino feliz
# --------------------------------------------------------------------------

def test_paciente_pregunta_y_el_medico_responde(encuentro, pedro, laura, org_a):
    respuesta = escribir(pedro, encuentro, CONSULTA)
    assert respuesta.status_code == 201
    assert respuesta.json()["emergency"] is None

    assert escribir(laura, encuentro, "Después de comer.").status_code == 201

    conversacion = ver(pedro, encuentro).json()
    assert [m["body"] for m in conversacion["messages"]] == [CONSULTA, "Después de comer."]
    assert [m["mine"] for m in conversacion["messages"]] == [True, False]
    assert conversacion["side"] == "patient"
    assert conversacion["can_write"] is True
    assert conversacion["practitioner_name"] == "Laura Gómez"


def test_la_conversacion_muestra_la_receta_y_el_aviso(encuentro, pedro):
    datos = ver(pedro, encuentro).json()
    assert "urgencias" in datos["notice"]
    assert datos["messages"] == []
    assert "prescription" in datos and "orders" in datos
    assert datos["window_days"] == 15


def test_ver_sin_mensajes_no_crea_la_conversacion(encuentro, pedro, org_a):
    ver(pedro, encuentro)
    with tenant_context(org_a.id):
        assert EncounterThread.objects.count() == 0


# --------------------------------------------------------------------------
#  Quién entra
# --------------------------------------------------------------------------

def test_una_atencion_en_borrador_no_tiene_chat(laura, ficha_hoy, pedro):
    borrador = abrir(laura, ficha_hoy).json()["id"]
    assert ver(pedro, borrador).status_code == 404
    assert escribir(pedro, borrador, CONSULTA).status_code == 404
    assert escribir(laura, borrador, "Hola").status_code == 404


def test_otro_medico_del_centro_no_entra(encuentro, pedro, diego, org_a):
    escribir(pedro, encuentro, CONSULTA)
    assert ver(diego, encuentro).status_code == 404
    assert escribir(diego, encuentro, "Lo atiendo yo.").status_code == 404
    assert cerrar(diego, encuentro).status_code == 404
    assert bandeja(diego).json()["results"] == []
    assert len(_mensajes(org_a)) == 1


def test_otro_paciente_no_entra(encuentro, org_a):
    from accounts.models import User
    with tenant_context(org_a.id):
        otra = User.objects.create_user(
            email="eva@kolping.test", password="clave-de-prueba-1", organization=org_a,
            first_name="Eva", last_name="Paz", document_number="5050",
        )
        Patient.objects.create(organization=org_a, user=otra,
                               document_type=Patient.DocumentType.CI,
                               document_number="5050", first_name="Eva", last_name="Paz")
    _chat(otra, org_a)
    assert ver(otra, encuentro).status_code == 404
    assert escribir(otra, encuentro, CONSULTA).status_code == 404


def test_otra_organizacion_no_entra(encuentro, pedro, org_b, branch_b):
    from catalog.models import Practitioner
    escribir(pedro, encuentro, CONSULTA)
    with tenant_context(org_b.id):
        ajena = Practitioner.objects.create(organization=org_b, first_name="Ana",
                                            last_name="Paz", license_number="MP-9000")
    medica_b = _chat(_medico(org_b, ajena, "ana@otra.test", "8001"), org_b)
    assert ver(medica_b, encuentro).status_code == 404
    assert escribir(medica_b, encuentro, "Hola").status_code == 404
    assert bandeja(medica_b).json()["results"] == []


def test_la_rls_esconde_las_conversaciones_de_otra_organizacion(encuentro, pedro, org_b):
    escribir(pedro, encuentro, CONSULTA)
    with tenant_context(org_b.id):
        assert EncounterThread.objects.count() == 0
        assert EncounterMessage.objects.count() == 0


def test_el_titular_escribe_por_su_dependiente(org_a, user_a, laura, practitioner_a,
                                               branches_a):
    with tenant_context(org_a.id):
        titular = Patient.objects.create(
            organization=org_a, user=user_a, document_type=Patient.DocumentType.CI,
            document_number="5001", first_name="Ana", last_name="Ríos",
        )
        hijo = Patient.objects.create(
            organization=org_a, guardian=titular, relationship="child",
            first_name="Tomás", last_name="Ríos", birth_date=dt.date(2018, 6, 1),
        )
    _chat(user_a, org_a)
    ahora = timezone.now().astimezone(LA_PAZ).replace(second=0, microsecond=0)
    encuentro_id = firmado(laura, _ficha(org_a, practitioner_a, branches_a["centro"],
                                         hijo, user_a, ahora))
    respuesta = escribir(user_a, encuentro_id, "¿Le doy el jarabe con la leche?")
    assert respuesta.status_code == 201
    assert ver(user_a, encuentro_id).json()["patient_name"] == "Tomás Ríos"
    (fila,) = bandeja(laura).json()["results"]
    assert fila["patient_name"] == "Tomás Ríos"


def test_sin_el_permiso_no_hay_chat(encuentro, paciente, org_a, user_a):
    with tenant_context(org_a.id):
        Patient.objects.filter(pk=paciente.pk).update(user=user_a)
    assert ver(user_a, encuentro).status_code == 403
    assert escribir(user_a, encuentro, CONSULTA).status_code == 403


@pytest.mark.parametrize("valor", ["no-es-un-uuid", "123", str(uuid.uuid4())])
def test_una_atencion_malformada_o_inexistente_da_404(pedro, valor):
    assert ver(pedro, valor).status_code == 404
    assert escribir(pedro, valor, CONSULTA).status_code == 404


# --------------------------------------------------------------------------
#  La ventana y el cierre
# --------------------------------------------------------------------------

def test_vencida_la_ventana_nadie_escribe(encuentro, pedro, laura):
    escribir(pedro, encuentro, CONSULTA)
    with override_settings(ENCOUNTER_CHAT_DAYS=0):
        assert escribir(pedro, encuentro, "¿Sigue ahí?").status_code == 409
        assert escribir(laura, encuentro, "Sí.").status_code == 409
        datos = ver(pedro, encuentro).json()
    assert datos["can_write"] is False
    assert datos["closed_reason"] == "expired"
    # Se sigue leyendo.
    assert [m["body"] for m in datos["messages"]] == [CONSULTA]


def test_el_medico_la_cierra_y_nadie_escribe(encuentro, pedro, laura):
    escribir(pedro, encuentro, CONSULTA)
    respuesta = cerrar(laura, encuentro)
    assert respuesta.status_code == 200
    assert respuesta.json()["closed_reason"] == "closed"
    assert escribir(pedro, encuentro, "¿Hola?").status_code == 409
    assert escribir(laura, encuentro, "Una más.").status_code == 409
    assert ver(pedro, encuentro).json()["can_write"] is False


def test_cerrar_dos_veces_da_409(encuentro, laura):
    assert cerrar(laura, encuentro).status_code == 200
    assert cerrar(laura, encuentro).status_code == 409


def test_el_paciente_no_puede_cerrar(encuentro, pedro):
    assert cerrar(pedro, encuentro).status_code == 404


# --------------------------------------------------------------------------
#  La barrera de urgencias
# --------------------------------------------------------------------------

def test_una_urgencia_se_guarda_marcada_y_trae_la_derivacion(encuentro, pedro, laura, org_a):
    respuesta = escribir(pedro, encuentro, URGENCIA)
    assert respuesta.status_code == 201
    assert "emergencias" in respuesta.json()["emergency"]["message"]

    (mensaje,) = _mensajes(org_a)
    assert mensaje.flagged_emergency is True
    # El médico la ve marcada y contada aparte.
    (fila,) = bandeja(laura).json()["results"]
    assert fila["unread_emergency"] == 1
    assert ver(laura, encuentro).json()["messages"][0]["flagged_emergency"] is True
    # El paciente no ve la marca: ya vio la derivación al escribir.
    assert ver(pedro, encuentro).json()["messages"][0]["flagged_emergency"] is False


def test_el_mensaje_del_medico_nunca_se_marca(encuentro, pedro, laura, org_a):
    escribir(pedro, encuentro, CONSULTA)
    respuesta = escribir(laura, encuentro, "Si le duele el pecho y no puede respirar, vaya a emergencias.")
    assert respuesta.status_code == 201
    assert respuesta.json()["emergency"] is None
    assert [m.flagged_emergency for m in _mensajes(org_a)] == [False, False]


# --------------------------------------------------------------------------
#  Textos vacíos y largos
# --------------------------------------------------------------------------

@pytest.mark.parametrize("texto", ["", "   ", "\n\t"])
def test_no_se_manda_un_mensaje_vacio(encuentro, pedro, org_a, texto):
    assert escribir(pedro, encuentro, texto).status_code == 400
    assert _mensajes(org_a) == []


def test_el_tope_de_largo(encuentro, pedro, org_a):
    assert escribir(pedro, encuentro, "a" * services.MAX_BODY_CHARS).status_code == 201
    assert escribir(pedro, encuentro, "a" * (services.MAX_BODY_CHARS + 1)).status_code == 400
    assert len(_mensajes(org_a)) == 1


def test_el_servicio_tambien_pone_el_tope(encuentro, pedro, org_a):
    from rest_framework.exceptions import ValidationError
    with tenant_context(org_a.id):
        atencion = Encounter.objects.get(pk=encuentro)
        with pytest.raises(ValidationError):
            services.send(pedro, atencion, services.PATIENT, "a" * (services.MAX_BODY_CHARS + 1))


# --------------------------------------------------------------------------
#  La bandeja del médico y los sin leer
# --------------------------------------------------------------------------

def test_los_sin_leer_del_medico(encuentro, pedro, laura):
    assert bandeja(laura).json()["results"] == []   # sin mensajes no aparece
    escribir(pedro, encuentro, CONSULTA)
    escribir(pedro, encuentro, "Y otra cosa más.")
    datos = bandeja(laura).json()
    assert datos["unread_total"] == 2
    assert datos["results"][0]["unread"] == 2

    ver(laura, encuentro)                            # leer marca como leído
    assert bandeja(laura).json()["unread_total"] == 0

    escribir(pedro, encuentro, "¿Me leyó?")
    assert bandeja(laura).json()["unread_total"] == 1


def test_lo_que_escribe_el_medico_no_cuenta_como_sin_leer(encuentro, pedro, laura):
    escribir(pedro, encuentro, CONSULTA)
    escribir(laura, encuentro, "Después de comer.")
    assert bandeja(laura).json()["unread_total"] == 0


def test_el_paciente_no_tiene_bandeja(encuentro, pedro):
    escribir(pedro, encuentro, CONSULTA)
    assert bandeja(pedro).json()["results"] == []


# --------------------------------------------------------------------------
#  El aviso al paciente
# --------------------------------------------------------------------------

def test_la_respuesta_del_medico_avisa_al_paciente_sin_el_texto(
    encuentro, pedro, laura, monkeypatch, django_capture_on_commit_callbacks,
):
    from notifications import push
    enviados = []
    monkeypatch.setattr(push, "send_to_user", lambda user, msg: enviados.append((user, msg)) or 1)

    with django_capture_on_commit_callbacks(execute=True):
        escribir(pedro, encuentro, CONSULTA)
    assert enviados == []                      # el paciente no se avisa a sí mismo

    with django_capture_on_commit_callbacks(execute=True):
        escribir(laura, encuentro, "Tómelo después de comer, con agua.")
    ((user, mensaje),) = enviados
    assert user.pk == pedro.pk
    assert mensaje.data == {"encounter_id": str(encuentro), "event": "chat"}
    assert "comer" not in mensaje.body and "comer" not in mensaje.title


def test_si_el_push_falla_el_mensaje_queda(encuentro, pedro, laura, org_a, monkeypatch,
                                           django_capture_on_commit_callbacks):
    from notifications import push

    def roto(*_):
        raise RuntimeError("FCM caído")

    monkeypatch.setattr(push, "send_to_user", roto)
    with django_capture_on_commit_callbacks(execute=True):
        assert escribir(laura, encuentro, "Respuesta.").status_code == 201
    assert len(_mensajes(org_a)) == 1


# --------------------------------------------------------------------------
#  Lo que garantiza la base
# --------------------------------------------------------------------------

def test_la_base_no_deja_editar_ni_borrar_un_mensaje(encuentro, pedro, org_a):
    escribir(pedro, encuentro, CONSULTA)
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterMessage.objects.update(body="Otra cosa.")
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterMessage.objects.all().delete()
        assert EncounterMessage.objects.get().body == CONSULTA


def test_la_base_no_deja_borrar_ni_reabrir_una_conversacion(encuentro, pedro, laura, org_a):
    escribir(pedro, encuentro, CONSULTA)
    cerrar(laura, encuentro)
    with tenant_context(org_a.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterThread.objects.update(closed_at=None, closed_by=None)
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterThread.objects.all().delete()
        assert EncounterThread.objects.get().closed_at is not None


def test_la_base_no_deja_cambiar_de_paciente(encuentro, pedro, org_a):
    escribir(pedro, encuentro, CONSULTA)
    with tenant_context(org_a.id):
        otro = Patient.objects.create(organization=org_a, document_type=Patient.DocumentType.CI,
                                      document_number="7070", first_name="Ana", last_name="Ríos")
        with pytest.raises(DatabaseError), transaction.atomic():
            EncounterThread.objects.update(patient=otro)


# --------------------------------------------------------------------------
#  Bitácora y copias
# --------------------------------------------------------------------------

def test_la_bitacora_registra_el_mensaje_sin_el_texto(encuentro, pedro, laura, org_a):
    escribir(pedro, encuentro, "Tengo VIH, ¿interactúa con el paracetamol?")
    cerrar(laura, encuentro)
    with tenant_context(org_a.id):
        asientos = list(AuditLog.objects.filter(action__in=["chat.message", "chat.close"]))
    assert {a.action for a in asientos} == {"chat.message", "chat.close"}
    assert all("VIH" not in str(a.detail) for a in asientos)


def test_la_copia_lleva_el_chat_y_restaurar_no_lo_borra(encuentro, pedro, laura, org_a):
    from backups import services as copias

    escribir(pedro, encuentro, CONSULTA)
    documento = copias.create(org_a)
    assert documento["counts"]["messaging.EncounterMessage"] == 1
    assert documento["counts"]["messaging.EncounterThread"] == 1

    escribir(laura, encuentro, "Escrito después de la copia.")
    copias.restore(documento, org_a)

    assert [m.body for m in _mensajes(org_a)] == [CONSULTA, "Escrito después de la copia."]


def test_un_mensaje_del_medico_agregado_por_fuera_no_cuenta_como_sin_leer(
    encuentro, pedro, laura, org_a,
):
    """Una restauración agrega mensajes (APPEND) sin tocar las marcas de
    lectura. Uno del propio médico no puede aparecerle como sin leer."""
    escribir(pedro, encuentro, CONSULTA)
    ver(laura, encuentro)
    with tenant_context(org_a.id):
        hilo = EncounterThread.objects.get()
        EncounterMessage.objects.create(organization=org_a, thread=hilo, author=laura,
                                        side=EncounterMessage.Side.PRACTITIONER,
                                        body="Restaurado de una copia.")
    assert bandeja(laura).json()["unread_total"] == 0
