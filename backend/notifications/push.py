"""US-28 — El envío de push por Firebase Cloud Messaging (FCM).

El backend no le habla al teléfono: le pide a FCM «mandá esto a este token»
y FCM lo entrega, aunque el teléfono esté apagado (lo entrega al encenderse).

Se usa directo la API HTTP v1 de FCM, autenticada con la credencial de
servicio. No se usa `firebase-admin`: trae Firestore, Storage y gRPC para
hacer una sola llamada HTTP. `google-auth` y `requests` ya estaban —los trae
`google-genai`, el asistente— y alcanzan.

Tres reglas:

- **Sin credencial no falla.** Con `FIREBASE_CREDENTIALS` vacía —en local, en
  las pruebas— se anota en el log y se sigue, igual que el correo de consola.
- **Un token muerto se borra.** Si FCM contesta que esa instalación ya no
  existe (la app se desinstaló), la fila se borra para no volver a intentar.
- **Nunca propaga un error.** Un push caído no deshace un pago ni frena una
  cancelación.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from django.conf import settings

from .models import DeviceToken

logger = logging.getLogger(__name__)

SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
SEND_URL = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"
TIMEOUT_SECONDS = 10
# El canal de Android en que la app muestra los avisos de fichas. Tiene que
# coincidir con el que crea `mobile/lib/core/notifications/push.dart`.
ANDROID_CHANNEL = "fichas"

# (credencial cruda, project_id, sesión autenticada): una por proceso. La
# sesión renueva sola el token de acceso de Google cuando vence.
_session: tuple[str, str, object] | None = None


@dataclass
class Message:
    title: str
    body: str
    # Datos ocultos que viajan con el aviso. La app lee `appointment_id` para
    # abrir esa ficha cuando el paciente toca la notificación. FCM sólo
    # acepta textos.
    data: dict[str, str] = field(default_factory=dict)


def _read_credentials(raw: str) -> dict:
    """El JSON de la credencial, pegado en la variable o en un archivo."""
    texto = raw.strip()
    if not texto.startswith("{"):
        texto = Path(texto).read_text(encoding="utf-8")
    return json.loads(texto)


def _authorized_session():
    """Devuelve `(project_id, sesión)`, o `(None, None)` sin credencial."""
    global _session
    raw = settings.FIREBASE_CREDENTIALS
    if not raw:
        return None, None
    if _session is None or _session[0] != raw:
        # Adentro y no arriba: un despliegue sin estas bibliotecas falla al
        # mandar un push, no al arrancar.
        from google.auth.transport.requests import AuthorizedSession
        from google.oauth2 import service_account

        info = _read_credentials(raw)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=[SCOPE],
        )
        _session = (raw, info["project_id"], AuthorizedSession(credentials))
    return _session[1], _session[2]


def _payload(token: str, message: Message) -> dict:
    return {
        "message": {
            # Token de registro, no FID: Firebase recomienda ahora mandar al
            # *Firebase Installation ID* (`fid`), pero `token` sigue andando y
            # es lo que entrega la app. Migrar es cambiar las dos puntas juntas
            # (ver `mobile/lib/core/notifications/push.dart`).
            "token": token,
            "notification": {"title": message.title, "body": message.body},
            "data": {k: str(v) for k, v in message.data.items()},
            "android": {
                "priority": "high",
                "notification": {"channel_id": ANDROID_CHANNEL},
            },
        },
    }


def _is_dead(response) -> bool:
    """FCM dice que el token ya no sirve: la app se desinstaló o es inválido."""
    if response.status_code == 404:
        return True
    if response.status_code != 400:
        return False
    try:
        error = response.json().get("error", {})
    except ValueError:
        return False
    codes = {detail.get("errorCode") for detail in error.get("details", [])}
    return "UNREGISTERED" in codes or (
        "INVALID_ARGUMENT" in codes
        and "registration token" in error.get("message", "").lower()
    )


def send_to_user(user, message: Message) -> int:
    """Manda [message] a todos los teléfonos de [user]. Devuelve cuántos salieron.

    Supone el contexto del inquilino ya fijado: lee y borra `DeviceToken`.
    """
    dispositivos = list(DeviceToken.objects.filter(user=user))
    if not dispositivos:
        return 0
    try:
        project, session = _authorized_session()
    except Exception:  # noqa: BLE001 - una credencial rota no tira el aviso
        logger.exception("La credencial de Firebase no se pudo leer.")
        return 0
    if session is None:
        logger.info("Push sin enviar (falta FIREBASE_CREDENTIALS): %s — %s",
                    message.title, message.body)
        return 0

    url = SEND_URL.format(project=project)
    enviados = 0
    for dispositivo in dispositivos:
        try:
            response = session.post(url, json=_payload(dispositivo.token, message),
                                    timeout=TIMEOUT_SECONDS)
        except Exception:  # noqa: BLE001 - la red caída no frena al resto
            logger.exception("No se pudo mandar el push al dispositivo %s.",
                             dispositivo.id)
            continue
        if response.status_code == 200:
            enviados += 1
        elif _is_dead(response):
            logger.info("Token de FCM vencido: se borra el dispositivo %s.",
                        dispositivo.id)
            dispositivo.delete()
        else:
            logger.warning("FCM rechazó el push al dispositivo %s: %s %s",
                           dispositivo.id, response.status_code, response.text[:300])
    return enviados
