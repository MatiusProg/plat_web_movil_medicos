"""Política de contraseñas del proyecto. RNF-04.

**Este archivo es compartido.** Lo escribe US-03 y lo consumen US-05 (cambio de
contraseña desde el perfil) y el alta de usuarios. La validación no se duplica:
si mañana el equipo decide exigir un símbolo, se cambia acá y las tres
historias lo heredan. Está acordado en el reparto del Sprint 1, sección 4.

Dos cosas que conviene tener claras:

1. **El hash lo hace Django, no este módulo.** ``AbstractBaseUser.set_password``
   usa el primer ``PASSWORD_HASHERS`` de ``config/settings.py``, que es Argon2.
   Acá sólo se valida la fuerza de la contraseña *antes* de dársela.
2. **Las reglas viven en ``AUTH_PASSWORD_VALIDATORS``**, no acá: largo mínimo
   de 8, nada de contraseñas comunes, nada de sólo números y nada demasiado
   parecido al correo o al nombre. Este módulo las aplica; no las redefine.
   Django ya las trae configuradas y nadie las estaba invocando.
"""

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


def validate_password_strength(password, user=None):
    """Aplica ``AUTH_PASSWORD_VALIDATORS`` y traduce el error a DRF.

    ``user`` es opcional pero conviene pasarlo: con él,
    ``UserAttributeSimilarityValidator`` puede rechazar una contraseña que sea
    el propio correo o el apellido de la persona, que es de las más comunes.

    Devuelve la contraseña para poder encadenarla en un ``validate_<campo>``.
    """
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as error:
        # Django devuelve una lista de mensajes; DRF espera lo mismo, así que
        # el usuario ve todas las reglas que incumplió y no sólo la primera.
        raise serializers.ValidationError(list(error.messages))
    return password


class PasswordField(serializers.CharField):
    """Campo de contraseña con la política del proyecto ya aplicada.

    ``trim_whitespace`` va en ``False`` a propósito: un espacio al final es
    parte de la contraseña, y recortarlo haría que la que se guarda no sea la
    que la persona escribió.

    El validador de similitud necesita al usuario, y un campo no lo conoce.
    Cuando importe —el cambio de contraseña de US-05, donde se sabe quién es—,
    se llama a ``validate_password_strength(valor, user)`` desde el
    ``validate()`` del serializer, que sí lo tiene.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("write_only", True)
        kwargs.setdefault("trim_whitespace", False)
        kwargs.setdefault("max_length", 128)
        super().__init__(**kwargs)

    def run_validation(self, data=serializers.empty):
        valor = super().run_validation(data)
        return validate_password_strength(valor)


def confirm_match(password, confirmation, campo="password_confirmation"):
    """Comprueba que la repetición coincida.

    Se pide repetir porque la contraseña va enmascarada: un error de tipeo en
    un alta o en un restablecimiento deja a la persona sin poder entrar y sin
    saber por qué.
    """
    if password != confirmation:
        raise serializers.ValidationError({campo: "Las contraseñas no coinciden."})
    return password
