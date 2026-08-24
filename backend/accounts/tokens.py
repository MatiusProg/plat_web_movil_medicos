"""Emisión de tokens JWT con el contexto de inquilino incorporado.

**Por qué el token lleva la organización.**

SimpleJWT resuelve el usuario con ``User.objects.get(id=<claim user_id>)``.
Pero ``users`` está protegida por Row Level Security: sin ``app.tenant_id``
fijado, esa consulta devuelve cero filas y la autenticación falla con
*"User not found"*.

O sea que el contexto tiene que fijarse **antes** de resolver el usuario, y por
lo tanto no puede salir de la base: tiene que venir en el propio token, que se
valida con la firma y sin tocar la base.

Por eso todo token emitido por este proyecto lleva dos claims adicionales:

    organization_id     uuid de la organización, o null para el superadmin
    is_platform_admin   true sólo para el Superadministrador de Plataforma

Nunca se emiten tokens con ``AccessToken.for_user()`` ni con
``RefreshToken.for_user()`` directamente: usar ``tokens_para()``.
"""

from rest_framework_simplejwt.tokens import RefreshToken

CLAIM_ORGANIZACION = "organization_id"
CLAIM_ADMIN_PLATAFORMA = "is_platform_admin"


class TokenDeInquilino(RefreshToken):
    """Token de refresco que arrastra el contexto de inquilino.

    El token de acceso derivado (``.access_token``) hereda los claims, así que
    alcanza con agregarlos acá.
    """

    @classmethod
    def for_user(cls, user):
        token = super().for_user(user)
        token[CLAIM_ORGANIZACION] = (
            str(user.organization_id) if user.organization_id else None
        )
        token[CLAIM_ADMIN_PLATAFORMA] = bool(user.is_platform_admin)
        return token


def tokens_para(user) -> dict[str, str]:
    """Par de tokens para un usuario recién autenticado.

    Es lo que devuelve el endpoint de inicio de sesión (US-02)::

        return Response(tokens_para(usuario))
    """
    refresh = TokenDeInquilino.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }
