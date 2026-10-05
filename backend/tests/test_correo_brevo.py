"""El correo sale por la API HTTPS de Brevo, no por SMTP.

Railway bloquea SMTP en los planes que no son Pro: sin esto, la confirmación
de la ficha (US-21), el restablecimiento de contraseña (US-03) y los reportes
por correo terminaban impresos en el log. Se prueba con el backend real de
django-anymail y la llamada HTTP interceptada: no sale nada a la red.
"""

import json

import pytest
from django.core.mail import EmailMessage, get_connection
from django.test import override_settings

pytestmark = pytest.mark.django_db

BREVO = {
    "EMAIL_BACKEND": "anymail.backends.brevo.EmailBackend",
    "ANYMAIL": {"BREVO_API_KEY": "xkeysib-prueba"},
    "DEFAULT_FROM_EMAIL": "Centro Médico <remitente@ejemplo.test>",
}


class RespuestaBrevo:
    status_code = 201
    text = '{"messageId": "<prueba@brevo>"}'
    content = text.encode()
    headers = {"content-type": "application/json"}

    def json(self):
        return json.loads(self.text)

    def raise_for_status(self):
        return None


@pytest.fixture
def llamadas(monkeypatch):
    import requests

    capturadas = []

    def request(self, method, url, **kwargs):
        capturadas.append({"method": method, "url": url, **kwargs})
        return RespuestaBrevo()

    monkeypatch.setattr(requests.Session, "request", request)
    return capturadas


@override_settings(**BREVO)
def test_el_correo_sale_por_la_api_de_brevo_con_la_clave(llamadas):
    with get_connection() as conexion:
        enviados = EmailMessage(
            "Tu ficha está confirmada", "Hola", to=["paciente@ejemplo.test"],
            connection=conexion,
        ).send()

    assert enviados == 1
    llamada = llamadas[0]
    assert llamada["method"].upper() == "POST"
    assert llamada["url"].startswith("https://api.brevo.com/")
    assert llamada["headers"]["api-key"] == "xkeysib-prueba"
    cuerpo = json.loads(llamada["data"])
    assert cuerpo["to"] == [{"email": "paciente@ejemplo.test"}]
    assert cuerpo["sender"]["email"] == "remitente@ejemplo.test"


@override_settings(**BREVO)
def test_los_adjuntos_de_los_reportes_viajan(llamadas):
    mensaje = EmailMessage("Reporte", "Adjunto", to=["admin@ejemplo.test"])
    mensaje.attach("reporte.csv", "a,b\n1,2\n", "text/csv")
    mensaje.send()

    cuerpo = json.loads(llamadas[0]["data"])
    assert cuerpo["attachment"][0]["name"] == "reporte.csv"
