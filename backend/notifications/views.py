"""US-28 — La app registra y olvida el token de su teléfono.

    POST   /api/notifications/devices/   {token, platform}   al iniciar sesión
    DELETE /api/notifications/devices/   {token}             al cerrarla

Cada quien registra sólo su propio teléfono: el usuario sale del token de
acceso, nunca del cuerpo. Registrar dos veces el mismo token no duplica nada;
si el teléfono pasó a otra cuenta de la organización, el token se mueve a la
nueva y la anterior deja de recibir sus avisos.
"""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceToken
from .serializers import DeviceTokenSerializer, ForgetDeviceSerializer


class DeviceTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.organization_id is None:
            # El superadministrador no tiene fichas de las que avisarle.
            return Response(
                {"code": "sin_organizacion",
                 "detail": "Sólo se registran teléfonos de una organización."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        entrada = DeviceTokenSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data
        dispositivo, creado = DeviceToken.objects.update_or_create(
            organization_id=user.organization_id, token=datos["token"],
            defaults={"user": user, "platform": datos["platform"]},
        )
        return Response(
            {"id": str(dispositivo.id), "platform": dispositivo.platform},
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )

    def delete(self, request):
        entrada = ForgetDeviceSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        DeviceToken.objects.filter(
            user=request.user, token=entrada.validated_data["token"],
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
