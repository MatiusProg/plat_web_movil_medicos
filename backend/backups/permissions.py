"""Clases de permiso de la app `backups`. Característica general 6.

Dos códigos y no uno. **Respaldar es inofensivo; restaurar destruye.** Quien
administra un centro médico puede querer que recepción baje la copia del mes
sin poder reemplazar la base con un archivo. Con un solo permiso habría que
elegir entre negarle lo primero o concederle lo segundo.

``backup.restore`` va únicamente al Administrador de la organización, y es el
permiso más peligroso de la plataforma: su efecto es irreversible y alcanza a
todos los datos del inquilino.
"""

from rest_framework.permissions import BasePermission


class RequiresPermission(BasePermission):
    code = ""
    message = "No tenés permiso para realizar esta acción."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and self.code
            and user.has_permission(self.code)
        )


class CanCreateBackup(RequiresPermission):
    code = "backups.backup.create"


class CanRestoreBackup(RequiresPermission):
    code = "backups.backup.restore"
