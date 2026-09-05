"""US-03 — Serializers de la solicitud y de la nueva contraseña.

Validan **forma**, no vigencia: que el enlace sirva lo decide
``services/password_reset.py``, que es quien puede distinguir entre vencido,
ya usado e inválido —los tres mensajes que pide el punto (h)—.

La política de complejidad no se escribe acá: viene de ``accounts/passwords.py``,
que es el archivo compartido del sprint. US-03, US-05 y el alta usan la misma.
"""

from rest_framework import serializers

from ..passwords import PasswordField, confirm_match, validate_password_strength


class PasswordResetRequestSerializer(serializers.Serializer):
    """El cuerpo de ``POST /password-reset/``.

    ``organization`` es obligatoria y no es un detalle burocrático: el correo
    es único **por inquilino**, no de forma global, así que sin saber en qué
    centro médico buscar la consulta es ambigua. Es el punto (a) de la
    historia, y el mismo motivo por el que el login la pide.
    """

    organization = serializers.CharField(max_length=40)
    email = serializers.EmailField()


class PasswordResetVerifySerializer(serializers.Serializer):
    """El cuerpo de ``POST /password-reset/verify/``: sólo el token.

    Existe para que la pantalla pueda decir "este enlace venció" **antes** de
    que la persona escriba una contraseña nueva dos veces, en vez de después.
    """

    token = serializers.CharField(max_length=128, trim_whitespace=True)


class PasswordResetConfirmSerializer(serializers.Serializer):
    """El cuerpo de ``POST /password-reset/confirm/``.

    La fuerza de la contraseña se comprueba dos veces y a propósito: acá sin
    conocer al usuario —el largo, que no sea común, que no sea sólo números— y
    otra vez en la vista pasándole el usuario, que es lo único que permite
    rechazar una contraseña que sea su propio correo o su apellido.
    """

    token = serializers.CharField(max_length=128, trim_whitespace=True)
    password = PasswordField()
    password_confirmation = serializers.CharField(
        write_only=True, trim_whitespace=False, max_length=128,
    )

    def validate(self, attrs):
        confirm_match(attrs["password"], attrs["password_confirmation"])
        return attrs

    def validate_for(self, user):
        """Segunda pasada, ya sabiendo de quién es la cuenta."""
        return validate_password_strength(self.validated_data["password"], user)
