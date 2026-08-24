from rest_framework.permissions import BasePermission


class IsPlatformAdmin(BasePermission):
    message = (
        "Esta operación es exclusiva del "
        "Superadministrador de Plataforma."
    )

    def has_permission(self, request, view):
        user = request.user

        return bool(
            user
            and user.is_authenticated
            and user.is_platform_admin
        )