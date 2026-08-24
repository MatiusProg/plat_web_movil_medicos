"""US-02 — Inicio de sesión (CU1), renovación (RNF-06) y cierre (CU4).

Tres endpoints, todos sin autenticar salvo el de cierre:

    POST /api/accounts/login/            credenciales -> par de tokens
    POST /api/accounts/token/refresh/    refresh      -> access nuevo
    POST /api/accounts/logout/           refresh      -> lista negra

**Los fallos de credenciales responden con ``Response``, no con ``raise``.**
No es estilo: toda la petición corre dentro de la transacción que abre
``TenantMiddleware``, y cuando DRF maneja una excepción llama a
``set_rollback()``. Con un ``raise`` se perderían las dos cosas que un intento
fallido tiene que dejar —la fila en ``login_attempts`` y el contador de
``failed_login_attempts``— y el bloqueo del RNF-07 dejaría de contar sin dar
ningún error. Está explicado en ``services/auth.py``.

Todas las respuestas de error llevan un campo ``code`` estable, para que el
frontend no tenga que comparar contra el texto del mensaje.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from tenancy.context import platform_admin_context, tenant_context
from tenancy.middleware import ORGANIZATION_HEADER

from ..serializers.auth import (
    LoginSerializer, LogoutSerializer, RefreshSerializer, sesion_iniciada,
)
from ..services import auth as servicio
from ..tokens import CLAIM_ORGANIZATION, CLAIM_PLATFORM_ADMIN, tokens_for_user

# Un mismo texto para "no existe el correo" y "la contraseña no es esa": la
# diferencia queda en login_attempts, que sólo lee el superadministrador. Si el
# mensaje distinguiera, el formulario de login serviría para averiguar qué
# correos están registrados en cada centro médico.
CREDENCIALES_INVALIDAS = "El correo o la contraseña no son correctos."


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """CU1 — Inicio de sesión.

    El slug de la organización se toma del cuerpo o del encabezado
    ``X-Organization``. Sin slug se interpreta como el Superadministrador de
    Plataforma, que es el único usuario sin organización.
    """
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    datos = serializer.validated_data

    slug = datos.get("organization") or request.META.get(ORGANIZATION_HEADER) or ""
    email = datos["email"]

    organization, motivo = servicio.resolve_organization(slug)
    if motivo != servicio.Reason.NONE:
        # La organización no resolvió: no hay dónde buscar el correo. Se
        # registra igual, porque un slug inventado repetido es exactamente la
        # pinta que tiene alguien tanteando el sistema.
        servicio.record_attempt(
            servicio.LoginResult(False, motivo), email, request,
        )
        return Response(
            {"code": "organizacion_no_disponible",
             "organization": ["El centro médico no existe o no está activo."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    resultado = servicio.authenticate(email, datos["password"], organization)
    servicio.record_attempt(resultado, email, request)

    if not resultado.succeeded:
        return _respuesta_de_fallo(resultado)

    user = resultado.user
    # Los roles y los permisos se leen bajo el contexto del usuario: ambas
    # tablas tienen RLS y fuera de contexto devolverían cero filas, con lo que
    # todo el mundo entraría al sistema sin ningún permiso.
    alcance = (
        platform_admin_context() if organization is None
        else tenant_context(organization.id)
    )
    with alcance:
        cuerpo = sesion_iniciada(user, tokens_for_user(user))

    return Response(cuerpo, status=status.HTTP_200_OK)


def _respuesta_de_fallo(resultado):
    """Traduce el motivo del servicio a una respuesta HTTP.

    El bloqueo y la baja se informan de forma explícita, y los dos sólo pueden
    verlos cuentas que existen. Es una filtración deliberada y acotada: quien
    tiene la cuenta bloqueada necesita saber que el problema es ese y no su
    contraseña, y a la baja se llega únicamente con la contraseña ya validada.
    """
    Reason = servicio.Reason

    if resultado.reason == Reason.LOCKED:
        return Response(
            {"code": "cuenta_bloqueada",
             "detail": "La cuenta está bloqueada temporalmente por intentos "
                       "fallidos. Volvé a intentar más tarde.",
             "locked_until": resultado.user.locked_until},
            status=status.HTTP_423_LOCKED,
        )

    if resultado.reason == Reason.INACTIVE_USER:
        return Response(
            {"code": "cuenta_inactiva",
             "detail": "La cuenta fue dada de baja. Consultá con el centro médico."},
            status=status.HTTP_403_FORBIDDEN,
        )

    return Response(
        {"code": "credenciales_invalidas", "detail": CREDENCIALES_INVALIDAS},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh(request):
    """RNF-06 — Cambia un token de refresco por un par nuevo.

    Con ``ROTATE_REFRESH_TOKENS`` el token entregado queda invalidado y se
    devuelve uno nuevo, así que el cliente tiene que guardar los dos valores de
    la respuesta y descartar los anteriores.

    No se usa la ``TokenRefreshView`` de SimpleJWT por una razón concreta: hay
    que verificar que el token traiga los claims del proyecto. Un token sin
    ``organization_id`` no puede autenticar —la búsqueda del usuario devuelve
    cero filas por RLS— y sin esta comprobación el cliente recibiría un token
    nuevo, aparentemente válido, que falla en la petición siguiente con un
    confuso *"User not found"*.
    """
    serializer = RefreshSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = RefreshToken(serializer.validated_data["refresh"])
    except TokenError:
        return Response(
            {"code": "refresh_invalido",
             "detail": "El token de refresco no es válido o ya expiró."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if token.get(CLAIM_ORGANIZATION) is None and not token.get(CLAIM_PLATFORM_ADMIN):
        return Response(
            {"code": "token_sin_organizacion",
             "detail": "El token no lleva el contexto de organización. "
                       "Volvé a iniciar sesión."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    nuevo_acceso = str(token.access_token)

    # Rotación: el token usado va a la lista negra y se emite otro. Los claims
    # del proyecto viajan en el mismo objeto, así que sobreviven al cambio de
    # jti sin necesidad de volver a leer el usuario de la base.
    token.blacklist()
    token.set_jti()
    token.set_exp()
    token.set_iat()

    return Response(
        {"access": nuevo_acceso, "refresh": str(token)},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """CU4 — Cierre de sesión: manda el token de refresco a la lista negra.

    El token de acceso no se invalida y sigue siendo válido hasta que expire
    (30 minutos, ``ACCESS_TOKEN_LIFETIME``). Es la contrapartida conocida de
    JWT: invalidarlo al instante exigiría consultar la base en cada petición,
    que es exactamente lo que JWT evita. Lo que este endpoint garantiza es que
    la sesión no se pueda **renovar**.

    Se exige estar autenticado y que el token de refresco sea del propio
    usuario. Sin esa comprobación, cualquiera que consiguiera un refresh ajeno
    podría cerrarle la sesión a otro.
    """
    serializer = LogoutSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        token = RefreshToken(serializer.validated_data["refresh"])
    except TokenError:
        return Response(
            {"code": "refresh_invalido",
             "detail": "El token de refresco no es válido o ya expiró."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    if str(token.get("user_id")) != str(request.user.id):
        return Response(
            {"code": "refresh_ajeno",
             "detail": "El token de refresco no pertenece a esta sesión."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # `blacklist()` sólo existe si `token_blacklist` está en INSTALLED_APPS.
    # Está, y `config/settings.py` documenta que es justamente para CU4.
    token.blacklist()

    return Response(status=status.HTTP_204_NO_CONTENT)
