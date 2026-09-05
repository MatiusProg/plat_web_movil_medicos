"""US-03 — Recuperación de contraseña: solicitud, envío y confirmación.

El flujo entero vive acá porque se apoya en tres decisiones que no son de una
vista ni de un serializer:

1. **La respuesta es idéntica exista o no la cuenta** (punto b). El formulario
   de "olvidé mi contraseña" no puede servir para averiguar qué correos están
   registrados en cada centro médico. Por eso el servicio nunca informa si
   encontró al usuario: devuelve siempre lo mismo, y hace el mismo trabajo
   costoso —generar el token y calcular su hash— haya o no a quién mandarle el
   correo, para que el tiempo de respuesta tampoco lo delate.
2. **El token se consume al primer uso** (punto g) y se guarda como hash
   (punto c). El detalle está en el docstring de ``PasswordResetToken``.
3. **Al completar el cambio se invalidan todas las sesiones abiertas**
   (punto f). Es la lista negra de tokens de refresco que construyó US-02,
   aplicada ahora a todos los tokens vigentes del usuario y no sólo al de la
   petición.

**Sobre el envío del correo.** Va dentro de la petición porque el proyecto no
tiene todavía una cola de tareas. Con ``EMAIL_BACKEND`` de consola —el de
desarrollo— eso no cuesta nada; contra un SMTP real, el envío añade latencia y
lo correcto sería sacarlo del ciclo HTTP. Queda anotado para cuando el
proyecto incorpore tareas en segundo plano; mientras tanto, un fallo de envío
**no** rompe la solicitud ni revela nada: se registra y la respuesta sigue
siendo la misma.
"""

import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)

from ..models import AuditLog, PasswordResetToken, User
from .auth import _ip_del_cliente

logger = logging.getLogger(__name__)

# 32 bytes de aleatoriedad: 256 bits. Contra eso no hay fuerza bruta posible,
# que es lo que permite guardar sólo un SHA-256 y no un hash lento.
TOKEN_BYTES = 32

# Punto (c) de la historia. Media hora es suficiente para ir al correo y
# volver, y corta para alguien que consiga acceso a la casilla más tarde.
TOKEN_LIFETIME_MINUTES = 30


def hash_token(token: str) -> str:
    """El SHA-256 en hexadecimal, que es lo que se guarda y lo que se busca."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def request_reset(organization, email, request):
    """Genera el enlace y lo manda, si hay a quién.

    No devuelve nada a propósito: quien la llama no debe poder distinguir el
    caso en que la cuenta existe del caso en que no, ni siquiera por accidente
    al construir la respuesta.
    """
    # El trabajo costoso se hace SIEMPRE, antes de saber si hay usuario: es lo
    # que iguala el tiempo de respuesta entre un correo registrado y uno que
    # no lo está.
    token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = hash_token(token)

    user = User.objects.filter(
        organization=organization, email__iexact=email, is_active=True,
    ).first()

    if user is None:
        return

    with transaction.atomic():
        # Los enlaces anteriores que siguieran vivos se dan por vencidos: vale
        # el último que se pidió y nada más. Sin esto, pedir el
        # restablecimiento diez veces deja diez enlaces utilizables.
        PasswordResetToken.objects.filter(
            user=user, used_at__isnull=True, expires_at__gt=timezone.now(),
        ).update(expires_at=timezone.now())

        PasswordResetToken.objects.create(
            organization=organization,
            user=user,
            token_hash=token_hash,
            expires_at=timezone.now() + timedelta(minutes=TOKEN_LIFETIME_MINUTES),
            ip_address=_ip_del_cliente(request),
        )

        # Punto (d): el envío queda registrado. Se audita aunque el correo
        # después falle — lo que interesa es que alguien pidió restablecer esa
        # cuenta, no si el servidor de correo respondió.
        AuditLog.objects.create(
            organization=organization,
            user=user,
            action="password.reset.request",
            entity="password_reset_tokens",
            entity_id=str(user.id),
            detail={"email": user.email, "organization": organization.slug},
            ip_address=_ip_del_cliente(request),
        )

    _send_email(user, organization, token)


def _send_email(user, organization, token):
    """Manda el enlace con la marca de la organización. Punto (d).

    Un fallo de envío se registra y no se propaga: la solicitud ya quedó
    asentada, y dejar que la excepción suba cambiaría la respuesta —un 500 en
    vez del 200 de siempre— justo para los correos que **sí** existen. Sería
    exactamente el oráculo que el punto (b) quiere evitar.
    """
    enlace = (
        f"{settings.FRONTEND_BASE_URL}/restablecer"
        f"?token={token}&organization={organization.slug}"
    )
    vigencia = TOKEN_LIFETIME_MINUTES

    cuerpo = (
        f"Hola {user.first_name},\n\n"
        f"Alguien pidió restablecer la contraseña de tu cuenta en "
        f"{organization.name}. Si fuiste vos, entrá a este enlace:\n\n"
        f"{enlace}\n\n"
        f"El enlace vence en {vigencia} minutos y sirve una sola vez.\n\n"
        f"Si no pediste nada, ignorá este mensaje: tu contraseña sigue siendo "
        f"la misma.\n\n"
        f"— {organization.name}\n"
    )

    try:
        send_mail(
            subject=f"Restablecer tu contraseña · {organization.name}",
            message=cuerpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "No se pudo enviar el correo de restablecimiento a la organización %s",
            organization.slug,
        )


class ResetError(Exception):
    """El enlace no sirve. ``code`` distingue por qué, para el mensaje."""

    def __init__(self, code, detail):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def find_usable_token(token: str) -> PasswordResetToken:
    """Busca el token y explica por qué no sirve, si no sirve.

    Los tres motivos del punto (h) se distinguen a propósito —vencido, ya
    usado, inválido—, y no filtran nada: para llegar a "vencido" o "ya usado"
    hay que tener en la mano un token que el servidor generó.
    """
    encontrado = PasswordResetToken.objects.filter(
        token_hash=hash_token(token),
    ).select_related("user", "organization").first()

    if encontrado is None:
        raise ResetError(
            "enlace_invalido",
            "El enlace no es válido. Pedí uno nuevo desde la pantalla de ingreso.",
        )

    if encontrado.used_at is not None:
        raise ResetError(
            "enlace_usado",
            "Este enlace ya se usó. Si necesitás cambiar la contraseña otra vez, "
            "pedí uno nuevo.",
        )

    if encontrado.is_expired:
        raise ResetError(
            "enlace_vencido",
            f"El enlace venció: dura {TOKEN_LIFETIME_MINUTES} minutos. "
            "Pedí uno nuevo.",
        )

    return encontrado


@transaction.atomic
def complete_reset(reset_token, new_password, request):
    """Cambia la contraseña, consume el enlace y cierra todas las sesiones.

    Las tres cosas van en una transacción: una contraseña cambiada con el
    enlace todavía utilizable, o con las sesiones viejas abiertas, es
    justamente el estado que la historia quiere impedir.
    """
    user = reset_token.user

    # El hash es Argon2, el primero de PASSWORD_HASHERS (RNF-04). La política
    # de complejidad ya la aplicó el serializer con `accounts/passwords.py`.
    user.set_password(new_password)

    # Quien recupera el acceso no debería seguir bloqueado por los intentos
    # fallidos que lo llevaron hasta acá (RNF-07).
    user.failed_login_attempts = 0
    user.locked_until = None
    user.save(update_fields=["password", "failed_login_attempts", "locked_until"])

    reset_token.used_at = timezone.now()
    reset_token.save(update_fields=["used_at"])

    revocadas = revoke_all_sessions(user)

    AuditLog.objects.create(
        organization=reset_token.organization,
        user=user,
        action="password.reset.complete",
        entity="users",
        entity_id=str(user.id),
        detail={"email": user.email, "sesiones_invalidadas": revocadas},
        ip_address=_ip_del_cliente(request),
    )

    return user


def revoke_all_sessions(user) -> int:
    """Manda a la lista negra todos los tokens de refresco vigentes. Punto (f).

    Es la misma lista negra que usa el cierre de sesión de US-02, sólo que
    aplicada a todos los tokens del usuario en vez de al de la petición.
    ``OutstandingToken`` los tiene registrados porque ``tokens_for_user`` los
    emite con la app ``token_blacklist`` instalada.

    Los tokens de **acceso** siguen sirviendo hasta que expiren, como máximo 30
    minutos: es la contrapartida conocida de JWT y está explicada en el cierre
    de sesión de US-02. Lo que queda garantizado es que ninguna sesión vieja se
    puede **renovar**.

    Estas tablas son de ``django.contrib``, no llevan ``organization_id`` y no
    tienen RLS. El filtro por usuario es lo único que acota el alcance, así que
    va siempre y nunca se recorre la tabla entera.
    """
    vigentes = OutstandingToken.objects.filter(user=user)

    revocadas = 0
    for token in vigentes:
        _, creada = BlacklistedToken.objects.get_or_create(token=token)
        if creada:
            revocadas += 1

    return revocadas
