"""Permiso de la app `noshow` (US-35)."""

from rest_framework.permissions import BasePermission


class CanReadNoShow(BasePermission):
    """Ver el riesgo de inasistencia de las fichas de la organización.

    Se siembra sólo a la Administración (``noshow/migrations/0003_*``). No se
    le da a recepción ni a los profesionales por defecto: es una calificación
    sobre personas, y quien la ve decide qué hacer con ella.
    """

    code = "appointments.noshow.read"
    message = "No tenés permiso para ver el riesgo de inasistencia."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.has_permission(self.code))
