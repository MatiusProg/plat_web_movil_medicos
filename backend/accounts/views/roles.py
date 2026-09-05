"""US-04 — Roles, permisos y asignación de roles a los usuarios.

    GET    /api/accounts/permissions/           catálogo asignable
    GET    /api/accounts/roles/                 roles de la organización
    POST   /api/accounts/roles/                 alta
    PATCH  /api/accounts/roles/{id}/            edición
    DELETE /api/accounts/roles/{id}/            baja
    PUT    /api/accounts/roles/{id}/permissions/    reemplaza el conjunto
    GET    /api/accounts/users/                 a quién asignarle un rol
    GET    /api/accounts/user-roles/            asignaciones vigentes
    POST   /api/accounts/user-roles/            asignar
    DELETE /api/accounts/user-roles/{id}/       revocar

**Todo lo de acá es de la organización que hizo la petición.** No hace falta
filtrar por ``organization`` en cada consulta —las cuatro tablas tienen RLS y
el contexto lo fijó ``accounts/authentication.py`` al validar el token—, pero
el filtro va igual y es a propósito: hace explícito el alcance para quien lee
el código, y sostiene la consulta el día que alguien la llame desde un
comando de gestión, donde no hay petición que fije el contexto.

La única excepción son las **plantillas del sistema**: su política
``system_templates_read`` las hace legibles desde cualquier inquilino, para
que US-43 pueda clonarlas. Acá se las excluye del listado; lo que el
administrador ve y edita es la copia de su organización.
"""

from django.db.models import Count, Prefetch
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from ..models import Role, User, UserRole
from ..permissions import (
    CanAssignRoles,
    CanCreateRoles,
    CanDeleteRoles,
    CanReadRoles,
    CanReadUsers,
    CanUpdateRoles,
)
from ..serializers.roles import (
    AssignableUserSerializer,
    AssignRoleSerializer,
    PermissionSerializer,
    RolePermissionsSerializer,
    RoleSerializer,
    UserRoleSerializer,
)
from ..services import roles as servicio

# El rol que US-43 le asigna al primer usuario de la organización. Se protege
# de la baja y de la desactivación: sin él la organización se queda sin nadie
# que pueda administrar usuarios, y no hay ninguna otra historia del backlog
# que vuelva a crearlo.
ADMIN_ROLE_CODE = "org_admin"

# Un UUID, para que `users/me/` —que es de US-05— no lo capture la ruta de
# detalle de este router.
UUID_REGEX = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class OrganizationScopedMixin:
    """Limita el queryset a la organización de quien pide.

    El Superadministrador de Plataforma no llega hasta acá —ninguna de las
    clases de permiso de ``accounts`` lo deja pasar, porque su rol sólo lleva
    permisos del módulo ``platform``—, pero si algún día llegara, se va con
    una lista vacía y no con las plantillas del sistema.
    """

    def organization(self):
        return self.request.user.organization

    def scoped(self, queryset):
        organization = self.organization()
        if organization is None:
            return queryset.none()
        return queryset.filter(organization=organization)


class PermissionViewSet(ReadOnlyModelViewSet):
    """El catálogo de permisos que un rol de organización puede tener.

    Los del módulo ``platform`` no aparecen: no son concedibles y mostrarlos
    en la pantalla sólo invita a intentarlo.
    """

    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, CanReadRoles]
    pagination_class = None

    def get_queryset(self):
        return servicio.assignable_permissions()


class RoleViewSet(OrganizationScopedMixin, ModelViewSet):
    """ABM de los roles de la organización y edición de sus permisos."""

    serializer_class = RoleSerializer
    lookup_value_regex = UUID_REGEX

    # Un permiso por acción: leer roles no habilita a crearlos, y asignarlos
    # no habilita a editarles los permisos.
    permission_classes_by_action = {
        "list": [CanReadRoles],
        "retrieve": [CanReadRoles],
        "create": [CanCreateRoles],
        "update": [CanUpdateRoles],
        "partial_update": [CanUpdateRoles],
        "permissions": [CanUpdateRoles],
        "destroy": [CanDeleteRoles],
    }

    def get_permissions(self):
        clases = self.permission_classes_by_action.get(self.action, [CanReadRoles])
        return [IsAuthenticated()] + [clase() for clase in clases]

    def get_queryset(self):
        return (
            self.scoped(Role.objects.all())
            .prefetch_related("role_permissions__permission")
            .annotate(assigned_users=Count("user_roles", distinct=True))
            # El `ordering` del modelo se pierde al anotar, y sin orden la
            # paginación puede repetir o saltear filas entre páginas.
            .order_by("name")
        )

    def destroy(self, request, *args, **kwargs):
        """Baja de un rol, con las dos negativas que la historia necesita.

        ``UserRole.role`` es ``PROTECT``, así que borrar un rol asignado ya
        falla en la base — pero con un ``IntegrityError``, que es un 500. Acá
        se responde 409 diciendo a cuántos usuarios hay que reasignar primero.
        """
        role = self.get_object()

        if role.code == ADMIN_ROLE_CODE:
            return Response(
                {"code": "rol_de_administracion",
                 "detail": "El rol de Administrador de Organización no se elimina: "
                           "es el único que puede administrar usuarios y roles."},
                status=status.HTTP_409_CONFLICT,
            )

        asignados = role.user_roles.count()
        if asignados:
            return Response(
                {"code": "rol_asignado",
                 "detail": f"El rol está asignado a {asignados} usuario(s). "
                           "Reasignalos antes de eliminarlo.",
                 "assigned_users": asignados},
                status=status.HTTP_409_CONFLICT,
            )

        detalle = {"code": role.code, "name": role.name}
        role_id = role.id
        role.delete()

        servicio.record(
            request,
            action="role.delete",
            entity="roles",
            entity_id=role_id,
            detail=detalle,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_update(self, serializer):
        """Impide dejar sin administración a la organización.

        Desactivar el rol no borra ninguna fila, pero ``permission_codes()``
        filtra por ``role__is_active``: un rol de administración desactivado
        deja a sus usuarios sin permisos, y sin permisos nadie puede volver a
        activarlo.
        """
        role = serializer.instance
        desactiva = serializer.validated_data.get("is_active") is False

        if role.code == ADMIN_ROLE_CODE and desactiva:
            raise ValidationError({
                "is_active": "El rol de Administrador de Organización no se "
                             "desactiva: nadie podría volver a activarlo.",
            })

        serializer.save()

    @action(detail=True, methods=["put"], url_path="permissions")
    def permissions(self, request, pk=None):
        """Reemplaza el conjunto de permisos del rol por el que llega.

        Es un PUT y no un PATCH porque el cuerpo es el conjunto **completo**:
        la pantalla manda todas las casillas marcadas, y lo que no viene se
        quita. Con un PATCH nunca se podría revocar un permiso.
        """
        role = self.get_object()

        if role.is_system:
            return Response(
                {"code": "rol_del_sistema",
                 "detail": "Las plantillas del sistema no se editan."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RolePermissionsSerializer(
            data=request.data, context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        added, removed = servicio.replace_permissions(
            role, serializer.validated_data["permissions"],
        )

        if added or removed:
            servicio.record(
                request,
                action="role.permissions.update",
                entity="role_permissions",
                entity_id=role.id,
                detail={"role_code": role.code,
                        "agregados": added, "quitados": removed},
            )

        role.refresh_from_db()
        return Response(
            RoleSerializer(role, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


class AssignableUserViewSet(OrganizationScopedMixin, ReadOnlyModelViewSet):
    """Los usuarios de la organización, para la pantalla de asignación.

    Es de sólo lectura y a propósito: el ABM de usuarios no está en el Sprint
    1 y el perfil propio es US-05. Lo que US-04 necesita es saber a quién le
    está asignando un rol.

    ``lookup_value_regex`` deja libre ``users/me/`` para cuando US-05 lo
    registre: sin eso, el router capturaría "me" como identificador y US-05
    tendría que pelear con esta ruta.
    """

    serializer_class = AssignableUserSerializer
    permission_classes = [IsAuthenticated, CanReadUsers]
    lookup_value_regex = UUID_REGEX

    def get_queryset(self):
        queryset = self.scoped(User.objects.all()).prefetch_related(
            Prefetch("user_roles", queryset=UserRole.objects.select_related("role")),
        )

        buscado = self.request.query_params.get("search", "").strip()
        if buscado:
            queryset = queryset.filter(email__icontains=buscado)

        role_id = self.request.query_params.get("role")
        if role_id:
            queryset = queryset.filter(user_roles__role_id=role_id)

        return queryset.distinct()


class UserRoleViewSet(OrganizationScopedMixin, ModelViewSet):
    """Asignación y revocación de roles. Sin edición: se revoca y se asigna."""

    permission_classes = [IsAuthenticated, CanAssignRoles]
    http_method_names = ["get", "post", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return AssignRoleSerializer
        return UserRoleSerializer

    def get_queryset(self):
        queryset = self.scoped(UserRole.objects.all()).select_related(
            "user", "role", "assigned_by",
        )

        user_id = self.request.query_params.get("user")
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        role_id = self.request.query_params.get("role")
        if role_id:
            queryset = queryset.filter(role_id=role_id)

        return queryset

    def destroy(self, request, *args, **kwargs):
        """Revoca una asignación.

        Nadie se revoca a sí mismo: quien tiene ``users.role.assign`` lo tiene
        por un rol, y quitárselo lo deja sin poder devolvérselo. Se lo pide a
        otro administrador, que es una molestia mucho menor que quedarse
        afuera de la administración de la organización.
        """
        assignment = self.get_object()

        if assignment.user_id == request.user.id:
            return Response(
                {"code": "revocacion_propia",
                 "detail": "No podés quitarte un rol a vos mismo. Pedíselo a "
                           "otro administrador."},
                status=status.HTTP_409_CONFLICT,
            )

        detalle = {
            "user_id": str(assignment.user_id),
            "user_email": assignment.user.email,
            "role_code": assignment.role.code,
            "role_name": assignment.role.name,
        }
        assignment_id = assignment.id
        assignment.delete()

        servicio.record(
            request,
            action="role.revoke",
            entity="user_roles",
            entity_id=assignment_id,
            detail=detalle,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
