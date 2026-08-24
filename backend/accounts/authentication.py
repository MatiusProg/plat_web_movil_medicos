"""Autenticación JWT que fija el contexto de inquilino.

**Acá vive el contrato del aislamiento en tiempo de ejecución.** Si tocás este
archivo, corré `pytest` antes de subir nada.

Por qué no está en un middleware de Django: un middleware corre *antes* de la
vista, y la autenticación de DRF ocurre *dentro* de la vista. En un middleware,
``request.user`` es siempre anónimo para un cliente que manda JWT, así que el
contexto nunca se fijaría a partir del token.

El orden que sigue esta clase es el único que funciona:

1. validar la firma del token — sin tocar la base,
2. leer ``organization_id`` del claim y fijar ``app.tenant_id``,
3. recién ahí resolver el usuario, que ya es visible bajo RLS,
4. comprobar que la organización real del usuario coincide con la del claim.

El paso 4 es defensa en profundidad: aunque un token firmado no se puede
falsificar, si alguna vez se emitiera mal —o si un usuario cambiara de
organización con un token viejo todavía vigente— la petición se rechaza y queda
registrada la alerta.
"""

import logging

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from tenancy.context import set_context

from .tokens import CLAIM_ADMIN_PLATAFORMA, CLAIM_ORGANIZACION

logger = logging.getLogger(__name__)


class AutenticacionDeInquilino(JWTAuthentication):
    """La clase de autenticación por omisión del proyecto."""

    def authenticate(self, request):
        """Igual que la de SimpleJWT, pero recordando la petición.

        Hace falta para poder dejar una alerta pendiente: cuando DRF maneja una
        excepción llama a ``set_rollback()``, así que cualquier fila escrita
        durante el rechazo se descarta. Las alertas se guardan en la petición y
        las persiste el middleware **después** de cerrar la transacción.
        """
        self._peticion = request
        try:
            return super().authenticate(request)
        finally:
            self._peticion = None

    def get_user(self, validated_token):
        organizacion = validated_token.get(CLAIM_ORGANIZACION)
        es_admin_plataforma = bool(validated_token.get(CLAIM_ADMIN_PLATAFORMA, False))

        if organizacion is None and not es_admin_plataforma:
            # Token emitido sin los claims del proyecto: o es anterior al
            # cambio, o alguien lo genero con AccessToken.for_user() a mano.
            # No se puede resolver el usuario sin contexto, asi que se rechaza
            # de forma explicita en lugar de fallar con "User not found".
            raise AuthenticationFailed(
                "El token no lleva el contexto de organización. Volvé a iniciar sesión.",
                code="token_sin_organizacion",
            )

        # Paso 2: el contexto, ANTES de tocar la base.
        set_context(organization_id=organizacion, platform_admin=es_admin_plataforma)

        # Paso 3: ahora el usuario es visible bajo RLS.
        #
        # Si el claim declara una organización que no es la del usuario, la
        # propia política RLS lo deja fuera y SimpleJWT responde "User not
        # found". O sea que el rechazo ya está garantizado por la base, sin
        # depender de ninguna comprobación de la aplicación. Lo que falta es
        # dejar constancia: sin esto el intento pasa en silencio y el panel de
        # US-45 nunca lo ve.
        try:
            usuario = super().get_user(validated_token)
        except AuthenticationFailed:
            self._alertar(
                usuario_id=validated_token.get("user_id"),
                reclamada=organizacion,
                motivo="El token declara una organización en la que el usuario no existe.",
            )
            raise

        # Paso 4: segunda barrera, para lo que la RLS no puede ver.
        #
        # Un token cuya organización coincide pero que se atribuye nivel de
        # plataforma pasaría el filtro de la base, porque la fila es visible.
        if bool(usuario.is_platform_admin) != es_admin_plataforma:
            self._alertar(
                usuario_id=usuario.pk,
                reclamada=organizacion,
                motivo="El token no corresponde al nivel de acceso del usuario.",
                organizacion_real=usuario.organization_id,
            )
            raise AuthenticationFailed(
                "El token no corresponde al nivel de acceso del usuario.",
                code="nivel_no_coincide",
            )

        return usuario

    def _alertar(self, usuario_id, reclamada, motivo, organizacion_real=None):
        """Deja la alerta pendiente para que el middleware la persista.

        No se escribe acá: enseguida se lanza AuthenticationFailed, DRF llama a
        ``set_rollback()`` y la fila se perdería. El middleware la guarda una
        vez cerrada la transacción de la petición.
        """
        logger.warning("%s (reclamada: %s, usuario: %s)", motivo, reclamada, usuario_id)
        peticion = getattr(self, "_peticion", None)
        if peticion is None:
            return
        # DRF envuelve el HttpRequest de Django en su propio objeto Request, y
        # los atributos que se le asignan quedan en el envoltorio. El
        # middleware ve el de abajo, así que hay que desenvolverlo.
        peticion = getattr(peticion, "_request", peticion)

        pendientes = getattr(peticion, "alertas_pendientes", None)
        if pendientes is None:
            pendientes = peticion.alertas_pendientes = []
        pendientes.append({
            # user_id se deja en None a propósito: la fila del usuario puede no
            # ser visible bajo el contexto reclamado, y la clave foránea
            # fallaría. El uuid queda en `detail`, que basta para investigar.
            "user_id": None,
            "source_organization_id": organizacion_real,
            "alert_type": "jwt_tenant_mismatch",
            "severity": "critical",
            "description": motivo[:300],
            "endpoint": peticion.path[:200],
            "http_method": peticion.method[:10],
            "detail": {
                "organizacion_reclamada": str(reclamada),
                "usuario": str(usuario_id),
            },
        })
