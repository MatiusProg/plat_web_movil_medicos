"""US-05 — Serializers del perfil propio y del cambio de contraseña.

**Qué se puede editar y qué no.** Lo dice el punto (d) de la historia: el
documento, el rol, la organización y el estado de la cuenta definen quién es
la persona *dentro* del centro médico, y cambiarlos es potestad del
administrador (US-10) o del superadministrador (US-43). El propio usuario sólo
toca sus datos de contacto: nombres, teléfono y correo.

Los campos no editables **se rechazan**, no se ignoran. DRF descarta en
silencio lo que llega para un campo de sólo lectura, y entonces un cliente que
manda el documento cree que lo cambió y recibe un 200. Un 400 con el nombre
del campo dice exactamente qué pasó.
"""

from rest_framework import serializers

from ..models import Role, User
from ..passwords import (
    PasswordField,
    confirm_match,
    validate_password_strength,
)

# Lo único que el usuario puede cambiar de sí mismo. Punto (b).
EDITABLE_FIELDS = ("first_name", "last_name", "phone", "email")


class ProfileSerializer(serializers.ModelSerializer):
    """El perfil de quien está autenticado. Puntos (a), (b), (d) y (e).

    ``organization`` y ``roles`` van armados a mano y no como relaciones de
    DRF: el perfil muestra *a qué* centro médico pertenece la persona y *qué*
    rol tiene, no identificadores que la pantalla tendría que volver a
    resolver con otra llamada.
    """

    full_name = serializers.CharField(read_only=True)
    organization = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "birth_date",
            "document_type",
            "document_number",
            "organization",
            "roles",
            "is_platform_admin",
            "is_active",
        )
        read_only_fields = tuple(
            campo for campo in fields if campo not in EDITABLE_FIELDS
        )
        extra_kwargs = {
            # Mismos topes que el alta de US-01 (`serializers/registration.py`),
            # que es lo que pide el punto (b): "las mismas validaciones".
            "first_name": {"max_length": 80, "allow_blank": False},
            "last_name": {"max_length": 80, "allow_blank": False},
            "phone": {"max_length": 30, "allow_blank": True},
        }

    def get_organization(self, user):
        if not user.organization_id:
            return None
        return {"slug": user.organization.slug, "name": user.organization.name}

    def get_roles(self, user):
        # Bajo el contexto de la petición: `user_roles` tiene RLS, y fuera de
        # contexto devolvería cero filas. Es la misma consulta que arma la
        # sesión en `serializers/auth.py::sesion_iniciada`.
        return list(
            Role.objects.filter(user_roles__user=user, is_active=True)
            .values("code", "name")
        )

    def to_internal_value(self, data):
        # Punto (d): un campo no editable se rechaza con su nombre, no se
        # ignora en silencio. Ver el docstring del módulo.
        if hasattr(data, "keys"):
            ajenos = sorted(set(data.keys()) - set(EDITABLE_FIELDS))
            if ajenos:
                raise serializers.ValidationError({
                    campo: ["Este dato no lo puedes cambiar desde tu perfil. "
                            "Pídeselo al administrador de tu centro médico."]
                    for campo in ajenos
                })
        return super().to_internal_value(data)

    def validate_first_name(self, value):
        return _sin_vacios(value)

    def validate_last_name(self, value):
        return _sin_vacios(value)

    def validate_email(self, value):
        """Punto (e): el correo es único **por organización**, no global.

        La misma persona puede ser paciente en dos centros médicos con el
        mismo correo; lo que no puede es haber dos cuentas con ese correo en
        el mismo. Se compara sin distinguir mayúsculas, igual que el alta.
        """
        email = User.objects.normalize_email(value)
        user = self.instance
        repetido = (
            User.objects.filter(
                organization_id=user.organization_id, email__iexact=email,
            )
            .exclude(pk=user.pk)
            .exists()
        )
        if repetido:
            raise serializers.ValidationError(
                "Ya hay otra cuenta con este correo en tu centro médico.",
            )
        return email


class PasswordChangeSerializer(serializers.Serializer):
    """Punto (c) — la contraseña actual y la nueva, repetida.

    ``password`` pasa por ``accounts/passwords.py``, que es el archivo
    compartido con US-03: la política no se duplica. La segunda pasada, la que
    necesita al usuario para rechazar una contraseña parecida a su correo, se
    hace en ``validate()`` con el usuario que la vista pone en el contexto.
    """

    current_password = serializers.CharField(
        write_only=True, trim_whitespace=False,
    )
    password = PasswordField()
    password_confirmation = serializers.CharField(
        write_only=True, trim_whitespace=False,
    )

    def validate(self, attrs):
        confirm_match(attrs["password"], attrs["password_confirmation"])
        try:
            validate_password_strength(attrs["password"], self.context["user"])
        except serializers.ValidationError as error:
            # `validate_password_strength` levanta una lista suelta, que DRF
            # devuelve sin nombre de campo. Se la cuelga de `password` para
            # que el formulario la muestre debajo de la casilla que toca.
            raise serializers.ValidationError({"password": error.detail})
        return attrs


def _sin_vacios(value):
    """Un nombre de puros espacios no es un nombre."""
    limpio = value.strip()
    if not limpio:
        raise serializers.ValidationError("Este campo no puede quedar vacío.")
    return limpio
