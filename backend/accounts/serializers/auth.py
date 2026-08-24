"""US-02 — Serializers del inicio, la renovación y el cierre de sesión.

Estos serializers validan **forma**, no credenciales. Que el correo tenga
formato de correo y que los campos estén presentes se resuelve acá y responde
400. Que la contraseña sea la correcta lo decide ``services/auth.py`` y
responde 401, sin lanzar excepción — el porqué está en el docstring de ese
módulo.
"""

from rest_framework import serializers

from ..models import Role


class LoginSerializer(serializers.Serializer):
    """Las credenciales que llegan al endpoint de inicio de sesión.

    ``organization`` es el slug del centro médico y es opcional **sólo** para el
    Superadministrador de Plataforma, que no pertenece a ninguno. Para todos los
    demás es obligatorio: sin él no se sabe en qué inquilino buscar el correo,
    que es único por organización y no de forma global.

    También se acepta por el encabezado ``X-Organization``, que es lo que va a
    mandar el frontend cuando el centro médico ya esté fijado por la URL. El
    campo del cuerpo tiene prioridad sobre el encabezado.
    """

    organization = serializers.CharField(
        max_length=40, required=False, allow_blank=True,
    )
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class RefreshSerializer(serializers.Serializer):
    """RNF-06 — El token de refresco que se cambia por uno de acceso nuevo."""

    refresh = serializers.CharField()


class LogoutSerializer(serializers.Serializer):
    """CU4 — El token de refresco que se manda a la lista negra."""

    refresh = serializers.CharField()


def sesion_iniciada(user, tokens):
    """El cuerpo de una respuesta de login exitoso.

    Lleva los roles y los permisos porque es literalmente lo que pide la
    historia —*"para acceder a las funciones según mi rol"*—: sin esto el
    frontend tendría que pedir los permisos en una segunda llamada para saber
    qué menú dibujar.

    Se arma **dentro** del contexto de inquilino, no fuera: ``user_roles`` y
    ``role_permissions`` están protegidas por RLS y sin contexto devolverían
    cero filas, con lo que todo usuario parecería no tener ningún permiso.
    """
    roles = Role.objects.filter(
        user_roles__user=user, is_active=True,
    ).values("code", "name")

    return {
        **tokens,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "document_type": user.document_type,
            "document_number": user.document_number,
            "organization": user.organization.slug if user.organization_id else None,
            "is_platform_admin": user.is_platform_admin,
            "roles": list(roles),
            "permissions": sorted(user.permission_codes()),
        },
    }
