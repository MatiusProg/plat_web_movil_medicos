"""US-03 — Recuperación de contraseña (CU3).

Tres endpoints, todos sin autenticar — es el punto: quien los usa es
justamente alguien que no puede entrar.

    POST /api/accounts/password-reset/          organización + correo -> enlace
    POST /api/accounts/password-reset/verify/   token -> ¿sirve este enlace?
    POST /api/accounts/password-reset/confirm/  token + contraseña -> cambiada

**Todo corre bajo el contexto del inquilino**, que resuelve el slug antes de
tocar la base: ``password_reset_tokens`` tiene RLS, y fuera de contexto
devolvería cero filas —o sea, todos los enlaces parecerían inválidos—.

Los errores responden con ``Response`` y no con ``raise``, por el mismo motivo
que en el login de US-02: la petición corre dentro de la transacción que abre
``TenantMiddleware``, y cuando DRF maneja una excepción llama a
``set_rollback()``. Con un ``raise`` se perderían las filas que el flujo tiene
que dejar sí o sí —el asiento de la bitácora, el token consumido—.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from tenancy.context import tenant_context
from tenancy.middleware import ORGANIZATION_HEADER

from ..serializers.password_reset import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
)
from ..services import auth as servicio_auth
from ..services import password_reset as servicio

# La misma respuesta exista o no la cuenta. Es el punto (b) de la historia: si
# el mensaje distinguiera, este formulario serviría para averiguar qué correos
# están registrados en cada centro médico —justamente lo que no puede pasar en
# un sistema donde el correo dice que alguien es paciente de ese lugar—.
RESPUESTA_UNIFORME = {
    "detail": "Si el correo corresponde a una cuenta de este centro médico, "
              "te enviamos un enlace para restablecer la contraseña. "
              "Revisá tu bandeja de entrada y el correo no deseado.",
}


@api_view(["POST"])
@permission_classes([AllowAny])
def request_reset(request):
    """Punto (a) — Solicitud del enlace.

    El slug de la organización se toma del cuerpo o del encabezado
    ``X-Organization``, igual que en el login. Que la organización no exista
    **sí** se informa: el slug no es un secreto —hace falta conocerlo para
    entrar— y no decirlo dejaría a quien se equivocó de centro médico
    esperando un correo que nunca va a llegar.
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    datos = serializer.validated_data

    slug = datos.get("organization") or request.META.get(ORGANIZATION_HEADER) or ""
    organization, motivo = servicio_auth.resolve_organization(slug)

    if organization is None or motivo != servicio_auth.Reason.NONE:
        return Response(
            {"code": "organizacion_no_disponible",
             "organization": ["El centro médico no existe o no está activo."]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with tenant_context(organization.id):
        servicio.request_reset(organization, datos["email"], request)

    return Response(RESPUESTA_UNIFORME, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def verify_reset(request):
    """Comprueba el enlace antes de pedir la contraseña nueva.

    Le ahorra a la persona escribir dos veces una contraseña para recién
    después enterarse de que el enlace venció. Devuelve el correo enmascarado
    para que se vea de qué cuenta se trata sin publicar la dirección entera a
    quien tenga el enlace en la mano.
    """
    serializer = PasswordResetVerifySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    organization = _organization_of(request)
    if organization is None:
        return _sin_organizacion()

    with tenant_context(organization.id):
        try:
            reset_token = servicio.find_usable_token(
                serializer.validated_data["token"],
            )
        except servicio.ResetError as error:
            return _respuesta_de_enlace(error)

        return Response(
            {"valid": True,
             "email": _enmascarar(reset_token.user.email),
             "expires_at": reset_token.expires_at},
            status=status.HTTP_200_OK,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_reset(request):
    """Puntos (e), (f) y (g) — Reemplaza la contraseña y cierra las sesiones."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    organization = _organization_of(request)
    if organization is None:
        return _sin_organizacion()

    with tenant_context(organization.id):
        try:
            reset_token = servicio.find_usable_token(
                serializer.validated_data["token"],
            )
        except servicio.ResetError as error:
            return _respuesta_de_enlace(error)

        # Segunda pasada de la política de contraseñas, ahora con el usuario:
        # es lo que permite rechazar que use su propio correo o su apellido.
        # `validate_password_strength` lanza ValidationError de DRF, que acá sí
        # conviene dejar subir: no hay nada escrito todavía que se pueda perder.
        serializer.validate_for(reset_token.user)

        servicio.complete_reset(
            reset_token, serializer.validated_data["password"], request,
        )

    return Response(
        {"detail": "Tu contraseña se cambió. Ya podés iniciar sesión con la "
                   "nueva, y las sesiones que tuvieras abiertas se cerraron."},
        status=status.HTTP_200_OK,
    )


def _organization_of(request):
    """El inquilino del enlace, por el cuerpo o por el encabezado.

    El enlace del correo lleva el slug además del token, así que la pantalla
    siempre lo tiene. Sin él no hay contexto, y sin contexto la tabla de
    tokens devuelve cero filas por RLS.
    """
    slug = (
        request.data.get("organization")
        or request.META.get(ORGANIZATION_HEADER)
        or ""
    )
    organization, motivo = servicio_auth.resolve_organization(slug)
    if motivo != servicio_auth.Reason.NONE:
        return None
    return organization


def _sin_organizacion():
    return Response(
        {"code": "organizacion_no_disponible",
         "organization": ["El centro médico no existe o no está activo."]},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _respuesta_de_enlace(error):
    """Punto (h) — un mensaje distinto por cada motivo.

    Los tres van con 400 y con su ``code`` estable, para que la pantalla no
    tenga que comparar contra el texto.
    """
    return Response(
        {"code": error.code, "detail": error.detail},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _enmascarar(email: str) -> str:
    """``ana@kolping.test`` -> ``a**@kolping.test``.

    Alcanza para reconocer la cuenta propia y no alcanza para aprenderse una
    dirección ajena a partir de un enlace que se filtró.
    """
    nombre, _, dominio = email.partition("@")
    if len(nombre) <= 1:
        return f"{nombre}@{dominio}"
    return f"{nombre[0]}{'*' * (len(nombre) - 1)}@{dominio}"
