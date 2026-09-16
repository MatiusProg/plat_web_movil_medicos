"""Característica general 5 — El reporte por correo.

La consigna enumera «Excel, HTML, eMail, PDF». El correo no es un formato: es
el envío de alguno de los otros tres —o del CSV— como adjunto. Por eso este
módulo no produce bytes: los recibe de ``exporters`` y los manda.

**A quién se le puede mandar, y por qué hay una lista.** Un endpoint que acepte
cualquier destinatario es un relé de correo abierto con la reputación del
dominio del proyecto: alguien con una cuenta de paciente podría mandar
cualquier cosa a cualquier casilla, firmada por el centro médico. Así que el
destinatario tiene que ser **una dirección de la propia organización** —una
cuenta de usuario activa— o la de quien pide. Es una restricción que el
enunciado no pide y que sin ella la función es un agujero.

**El envío va dentro de la petición**, como el de US-03 y por el mismo motivo:
el proyecto todavía no tiene cola de tareas. Está anotado igual que allá. La
diferencia es que acá el fallo **sí** se informa: quien pidió «mandámelo por
correo» tiene que enterarse de que no salió, mientras que en el
restablecimiento de contraseña informarlo delataría qué correos existen.
"""

import logging

from django.conf import settings
from django.core.mail import EmailMessage

logger = logging.getLogger(__name__)

# Tope del adjunto. Por encima, la mayoría de los servidores rechazan el correo
# y el usuario se queda esperando un mensaje que nunca llega. Mejor decírselo
# de entrada y que acote el reporte.
MAX_ATTACHMENT_BYTES = 8 * 1024 * 1024


class DeliveryError(Exception):
    """No se pudo enviar. ``code`` distingue por qué, para el mensaje."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def allowed_recipients(user) -> set[str]:
    """Las direcciones a las que este usuario puede mandarse un reporte.

    Las cuentas activas de su organización, más la suya. La consulta sale
    filtrada por RLS igual, pero el filtro explícito por organización queda
    escrito por la misma razón que en ``audit.views``.
    """
    from accounts.models import User

    organization = getattr(user, "organization", None)
    if organization is None:
        return {user.email.lower()} if user.email else set()

    direcciones = set(
        User.objects
        .filter(organization=organization, is_active=True)
        .values_list("email", flat=True)
    )
    direcciones.add(user.email)
    return {d.lower() for d in direcciones if d}


def send(user, recipients, subject, body, filename, content, mime):
    """Manda el reporte adjunto. Lanza ``DeliveryError`` si no se puede.

    Devuelve la lista de destinatarios a los que se envió, que es lo que la
    vista le repite al usuario: confirmar «se envió» sin decir a quién es
    justamente lo que no deja detectar una dirección mal escrita.
    """
    destinos = [str(d).strip().lower() for d in (recipients or []) if str(d).strip()]
    if not destinos:
        raise DeliveryError(
            "sin_destinatarios", "Hay que indicar al menos un destinatario.",
        )

    permitidos = allowed_recipients(user)
    ajenos = sorted(set(destinos) - permitidos)
    if ajenos:
        raise DeliveryError(
            "destinatario_no_permitido",
            "Sólo se puede enviar a cuentas de la organización. No "
            f"corresponden a ninguna: {', '.join(ajenos)}.",
        )

    if len(content) > MAX_ATTACHMENT_BYTES:
        megas = MAX_ATTACHMENT_BYTES // (1024 * 1024)
        raise DeliveryError(
            "adjunto_demasiado_grande",
            f"El reporte pesa más de {megas} MB y no se puede adjuntar. "
            "Agregá criterios de selección o quitá columnas.",
        )

    mensaje = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=sorted(set(destinos)),
    )
    mensaje.attach(filename, content, mime)

    try:
        mensaje.send(fail_silently=False)
    except Exception as error:  # noqa: BLE001
        logger.exception("No se pudo enviar el reporte «%s»", subject)
        raise DeliveryError(
            "envio_fallido",
            "No se pudo enviar el correo. Probá de nuevo en unos minutos.",
        ) from error

    return sorted(set(destinos))
