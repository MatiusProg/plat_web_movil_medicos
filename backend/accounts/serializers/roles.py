"""US-04 — Serializers de roles, permisos y asignaciones.

Tres reglas se hacen cumplir acá y conviene tenerlas juntas a la vista:

1. **Un rol del sistema no se edita.** Las plantillas viven a nivel plataforma
   (``organization`` NULL) y las lee cualquier inquilino para poder clonarlas
   al darse de alta. Que sean legibles no las hace editables: lo que el
   administrador ajusta es *su copia*, no la plantilla de todos.
2. **Un rol de organización no lleva permisos de plataforma.** Sin ese corte,
   el administrador de un centro médico podría concederse
   ``platform.organization.create``.
3. **Un rol sólo se asigna a un usuario de la misma organización.** La base ya
   lo impide con la clave foránea compuesta ``fk_user_role_role_same_org``,
   pero un IntegrityError es un 500: acá se responde 400 con el motivo.
"""

import re

from django.db import transaction
from rest_framework import serializers

from ..models import Permission, Role, User, UserRole
from ..services import roles as servicio

# Mismo formato que el `code` de las plantillas del sistema: minúsculas,
# números y guión bajo. El modelo lo deja libre porque es un CharField, así
# que la forma se valida acá.
CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,39}$")


def resolve_permissions(codes):
    """Resuelve códigos de permiso contra el catálogo asignable.

    Está a nivel de módulo porque la usan dos serializers: el del rol completo
    y el de la pantalla de permisos. Devuelve las instancias en orden de
    código; levanta ``ValidationError`` con un renglón por código que no
    resolvió.
    """
    codes = sorted(set(codes))
    encontrados = {
        permission.code: permission
        for permission in servicio.assignable_permissions().filter(code__in=codes)
    }

    faltantes = [code for code in codes if code not in encontrados]
    if faltantes:
        # Un permiso de plataforma existe pero no es asignable, así que cae
        # acá igual que uno inventado. El mensaje los distingue para que quien
        # lo lea no salga a buscar un error de tipeo que no existe.
        de_plataforma = set(
            Permission.objects
            .filter(code__in=faltantes, module=servicio.PLATFORM_MODULE)
            .values_list("code", flat=True)
        )
        raise serializers.ValidationError([
            f"{code}: es un permiso de plataforma y no se puede conceder a un "
            "rol de una organización."
            if code in de_plataforma
            else f"{code}: no existe en el catálogo de permisos."
            for code in faltantes
        ])

    return [encontrados[code] for code in codes]


class PermissionSerializer(serializers.ModelSerializer):
    """El catálogo de permisos. Sólo lectura: lo declara una migración."""

    class Meta:
        model = Permission
        fields = ["id", "code", "module", "description"]
        read_only_fields = fields


class RoleSerializer(serializers.ModelSerializer):
    """Un rol de la organización, con su conjunto de permisos.

    ``permissions`` viaja como lista de **códigos** y no de UUID: es lo que el
    frontend dibuja, lo que la bitácora guarda y lo que se lee en un asiento
    de auditoría sin tener que resolver ninguna clave.
    """

    permissions = serializers.ListField(
        child=serializers.CharField(max_length=80),
        required=False,
        help_text="Códigos de permiso, con el formato modulo.recurso.accion.",
    )
    assigned_users = serializers.IntegerField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id", "code", "name", "description",
            "is_system", "is_active", "permissions", "assigned_users",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        datos["permissions"] = sorted(
            instance.role_permissions.values_list("permission__code", flat=True)
        )
        # `assigned_users` puede venir anotado por el queryset de la vista; si
        # el serializer se usa suelto —al crear, por ejemplo— se cuenta acá.
        if not isinstance(getattr(instance, "assigned_users", None), int):
            datos["assigned_users"] = instance.user_roles.count()
        return datos

    def validate_code(self, value):
        value = value.strip().lower()

        if not CODE_PATTERN.match(value):
            raise serializers.ValidationError(
                "El código va en minúsculas, empieza con letra y admite números "
                "y guión bajo; entre 3 y 40 caracteres."
            )

        organization = self.context["request"].user.organization
        existente = Role.objects.filter(organization=organization, code=value)
        if self.instance is not None:
            existente = existente.exclude(pk=self.instance.pk)

        if existente.exists():
            raise serializers.ValidationError(
                "Ya hay un rol con ese código en la organización."
            )

        return value

    def validate_permissions(self, value):
        return resolve_permissions(value)

    def validate(self, attrs):
        if self.instance is not None and self.instance.is_system:
            raise serializers.ValidationError(
                "Las plantillas del sistema no se editan. Lo que se ajusta es "
                "la copia que tiene la organización."
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        permissions = validated_data.pop("permissions", [])

        role = Role.objects.create(
            organization=request.user.organization,
            # `is_system` no se acepta del cliente: el CHECK `ck_role_system`
            # sólo lo admite con `organization` NULL, y un rol creado acá
            # siempre pertenece a una organización.
            is_system=False,
            **validated_data,
        )

        added, _removed = servicio.replace_permissions(role, permissions)
        servicio.record(
            request,
            action="role.create",
            entity="roles",
            entity_id=role.id,
            detail={"code": role.code, "name": role.name, "permissions": added},
        )
        return role

    @transaction.atomic
    def update(self, instance, validated_data):
        request = self.context["request"]
        permissions = validated_data.pop("permissions", None)

        anterior = {
            "code": instance.code,
            "name": instance.name,
            "description": instance.description,
            "is_active": instance.is_active,
        }

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)
        instance.save()

        cambios = {
            campo: {"antes": anterior[campo], "despues": getattr(instance, campo)}
            for campo in anterior
            if anterior[campo] != getattr(instance, campo)
        }

        if permissions is not None:
            added, removed = servicio.replace_permissions(instance, permissions)
            if added or removed:
                cambios["permissions"] = {"agregados": added, "quitados": removed}

        if cambios:
            servicio.record(
                request,
                action="role.update",
                entity="roles",
                entity_id=instance.id,
                detail=cambios,
            )
        return instance


class RolePermissionsSerializer(serializers.Serializer):
    """El cuerpo de ``PUT /roles/{id}/permissions/``.

    Existe aparte del ``RoleSerializer`` porque la pantalla de permisos es
    otra: se abre sobre un rol ya creado y manda el conjunto completo, sin
    tocar el nombre ni la descripción.
    """

    permissions = serializers.ListField(
        child=serializers.CharField(max_length=80), allow_empty=True,
    )

    def validate_permissions(self, value):
        return resolve_permissions(value)


class UserRoleSerializer(serializers.ModelSerializer):
    """Una asignación, con lo justo para dibujar la fila sin otra llamada."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_full_name = serializers.CharField(source="user.full_name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    assigned_by_email = serializers.EmailField(
        source="assigned_by.email", read_only=True, allow_null=True,
    )

    class Meta:
        model = UserRole
        fields = [
            "id", "user", "user_email", "user_full_name",
            "role", "role_code", "role_name",
            "assigned_by", "assigned_by_email", "assigned_at",
        ]
        read_only_fields = fields


class AssignRoleSerializer(serializers.Serializer):
    """El cuerpo de ``POST /user-roles/``: a quién y qué rol."""

    user = serializers.UUIDField()
    role = serializers.UUIDField()

    def validate(self, attrs):
        organization = self.context["request"].user.organization

        # Las dos búsquedas corren bajo el contexto del inquilino, así que un
        # identificador de otra organización simplemente no aparece. El filtro
        # explícito por organización es la segunda barrera, para el día en que
        # alguien llame a este serializer desde un script sin contexto.
        try:
            user = User.objects.get(id=attrs["user"], organization=organization)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                {"user": "No hay un usuario con ese identificador en la organización."}
            )

        try:
            role = Role.objects.get(id=attrs["role"], organization=organization)
        except Role.DoesNotExist:
            raise serializers.ValidationError(
                {"role": "No hay un rol con ese identificador en la organización. "
                         "Las plantillas del sistema no se asignan: se asigna la "
                         "copia de la organización."}
            )

        if not role.is_active:
            raise serializers.ValidationError(
                {"role": "El rol está inactivo y no se puede asignar."}
            )

        if UserRole.objects.filter(user=user, role=role).exists():
            raise serializers.ValidationError(
                {"role": "El usuario ya tiene ese rol."}
            )

        attrs["user"] = user
        attrs["role"] = role
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context["request"]
        user = validated_data["user"]
        role = validated_data["role"]

        assignment = UserRole.objects.create(
            user=user,
            role=role,
            organization=role.organization,
            assigned_by=request.user,
        )

        servicio.record(
            request,
            action="role.assign",
            entity="user_roles",
            entity_id=assignment.id,
            detail={
                "user_id": str(user.id),
                "user_email": user.email,
                "role_code": role.code,
                "role_name": role.name,
            },
        )
        return assignment

    def to_representation(self, instance):
        return UserRoleSerializer(instance, context=self.context).data


class AssignableUserSerializer(serializers.ModelSerializer):
    """El usuario visto desde la pantalla de asignación de roles.

    Es sólo lectura y deliberadamente corto: US-04 necesita saber a quién le
    asigna un rol, no administrar usuarios. El ABM de usuarios no está en el
    Sprint 1, y el perfil propio es US-05.
    """

    full_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "full_name",
            "document_type", "document_number", "is_active", "roles",
        ]
        read_only_fields = fields

    def get_roles(self, user):
        return [
            {"id": str(assignment.role_id),
             "code": assignment.role.code,
             "name": assignment.role.name}
            for assignment in user.user_roles.all()
        ]
