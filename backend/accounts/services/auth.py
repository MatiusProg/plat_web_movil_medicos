"""US-02 — Verificación de credenciales, bloqueo por intentos y bitácora.

Acá vive todo lo que el inicio de sesión hace *antes* de emitir un token. Está
fuera de la vista y fuera del serializer a propósito: son tres reglas que se
prueban por separado y que ninguna otra historia debería reimplementar.

**Por qué nada de esto lanza excepciones.**

Un fallo de credenciales tiene que dejar rastro: la fila en ``login_attempts``
y el contador de ``users.failed_login_attempts``. Pero cuando DRF maneja una
excepción llama a ``set_rollback()``, y como toda la petición corre dentro de
la transacción que abre ``TenantMiddleware``, ese rastro se descartaría al
cerrar. Es el mismo problema que ya resolvió ``accounts.authentication`` con
las alertas de aislamiento.

Por eso estas funciones **devuelven** un ``LoginResult`` en lugar de lanzar, y
la vista responde con un ``Response`` construido a mano. Si alguna vez alguien
lo cambia por un ``raise ValidationError``, el bloqueo del RNF-07 deja de
funcionar sin dar ningún error: el contador vuelve a cero en cada intento.

**Por qué no se usa ``django.contrib.auth.authenticate``.**

El correo es único *por organización*, no de forma global (decisión D-5, ver el
comentario de ``SILENCED_SYSTEM_CHECKS`` en ``config/settings.py``). El backend
estándar hace ``User.objects.get(email=...)``, que con dos inquilinos que
comparten un correo lanzaría ``MultipleObjectsReturned``. Acá la organización
se resuelve **primero**, y recién con el contexto puesto se busca el correo,
que dentro del inquilino sí es único.
"""

from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization

from ..models import LoginAttempt, User

Reason = LoginAttempt.FailureReason


@dataclass(frozen=True)
class LoginResult:
    """Lo que devuelve un intento de autenticación.

    En los fallos ``user`` puede venir poblado igual —para saber contra qué
    cuenta se intentó— o quedar en ``None`` si el correo no existe.
    """

    succeeded: bool
    reason: str = Reason.NONE
    user: User | None = None
    organization: Organization | None = None


def resolve_organization(slug):
    """Traduce el slug del formulario de login a su organización.

    Devuelve ``(organization, reason)``. Un slug vacío significa que quien
    inicia sesión dice ser el Superadministrador de Plataforma, que por
    definición no pertenece a ninguna organización: en ese caso devuelve
    ``(None, Reason.NONE)``, que no es un error.

    Problema del huevo y la gallina: en este punto todavía no hay contexto, así
    que un ``SELECT`` sobre ``organizations`` devolvería cero filas por su
    propia política. Lo resuelve ``app_resolve_tenant``, la función de base de
    datos que ya usa el middleware: dado un slug exacto devuelve el uuid de la
    organización **activa**, o NULL, sin permitir enumerar.
    """
    if not slug:
        return None, Reason.NONE

    with connection.cursor() as cursor:
        cursor.execute("SELECT app_resolve_tenant(%s)", [slug])
        row = cursor.fetchone()
    organization_id = row[0] if row else None

    if organization_id:
        with tenant_context(organization_id):
            organization = Organization.objects.filter(id=organization_id).first()
        return organization, Reason.NONE

    # No resolvió. Distinguir "no existe" de "existe pero está suspendida" sólo
    # cambia lo que se guarda en login_attempts, que lee únicamente el
    # superadministrador: la respuesta al cliente es la misma en los dos casos.
    with platform_admin_context():
        existe = Organization.objects.filter(slug=slug).exists()
    return None, Reason.INACTIVE_TENANT if existe else Reason.UNKNOWN_TENANT


def authenticate(email, password, organization):
    """Verifica las credenciales dentro del contexto que corresponda.

    ``organization`` en ``None`` significa nivel plataforma: el
    superadministrador es el único usuario con ``organization_id`` NULL, y su
    propia política RLS lo deja verse a sí mismo y a nadie más.

    El orden de las comprobaciones importa: el bloqueo se mira **antes** que la
    contraseña. Si se mirara después, cada intento contra una cuenta ya
    bloqueada seguiría verificando una contraseña, y el bloqueo del RNF-07
    dejaría de ser una defensa contra fuerza bruta para pasar a ser un mensaje.
    """
    scope = (
        platform_admin_context() if organization is None
        else tenant_context(organization.id)
    )
    with scope:
        user = User.objects.filter(email__iexact=email).first()

        if user is None:
            return LoginResult(False, Reason.UNKNOWN_USER, organization=organization)

        if user.is_locked:
            # No suma al contador: la cuenta ya está bloqueada, y si sumara,
            # insistir extendería el bloqueo indefinidamente.
            return LoginResult(
                False, Reason.LOCKED, user=user, organization=organization,
            )

        if not user.check_password(password):
            _registrar_fallo(user)
            return LoginResult(
                False, Reason.BAD_CREDENTIALS, user=user, organization=organization,
            )

        # La baja se comprueba al final, con la contraseña ya validada: así el
        # mensaje "tu cuenta fue dada de baja" sólo lo ve quien efectivamente es
        # el dueño de la cuenta, y no cualquiera que pruebe correos.
        if not user.is_active:
            return LoginResult(
                False, Reason.INACTIVE_USER, user=user, organization=organization,
            )

        _registrar_exito(user)
        return LoginResult(True, Reason.NONE, user=user, organization=organization)


def _registrar_fallo(user):
    """RNF-07 — Suma un intento fallido y bloquea al llegar al límite."""
    user.failed_login_attempts += 1
    campos = ["failed_login_attempts", "updated_at"]

    if user.failed_login_attempts >= settings.LOGIN_MAX_FAILED_ATTEMPTS:
        user.locked_until = timezone.now() + timedelta(
            minutes=settings.LOGIN_LOCKOUT_MINUTES,
        )
        campos.append("locked_until")

    user.save(update_fields=campos)


def _registrar_exito(user):
    """Un inicio de sesión válido limpia el contador y el bloqueo vencido."""
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = timezone.now()
    user.save(update_fields=[
        "failed_login_attempts", "locked_until", "last_login_at", "updated_at",
    ])


def record_attempt(result, email, request):
    """Deja la fila en ``login_attempts``, pase lo que pase.

    ``login_attempts`` es un buzón de sólo escritura: su política
    ``anyone_reports`` permite INSERT en cualquier contexto —hace falta, porque
    un correo desconocido se registra antes de saber a qué organización
    pertenece— y sólo el superadministrador puede leerla.

    El ``user`` se guarda únicamente cuando el intento tuvo éxito. En un fallo
    la fila viaja sin clave foránea a propósito: ``login_attempts`` no está
    filtrada por inquilino, y apuntar a un usuario desde una fila que cualquiera
    puede insertar convertiría el buzón en una forma de confirmar qué correos
    existen en qué organización.
    """
    LoginAttempt.objects.create(
        organization=result.organization,
        user=result.user if result.succeeded else None,
        attempted_email=email[:254],
        succeeded=result.succeeded,
        failure_reason=result.reason,
        ip_address=_ip_del_cliente(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:300],
    )


def _ip_del_cliente(request):
    """La IP del cliente, mirando primero el encabezado del proxy.

    En Railway la aplicación corre detrás de un proxy, así que ``REMOTE_ADDR``
    es el del proxy y no el del cliente. ``X-Forwarded-For`` lleva la cadena
    completa: el primero es el cliente.
    """
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if reenviada:
        return reenviada.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None
