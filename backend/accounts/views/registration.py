"""US-01 — Alta de paciente desde la aplicación móvil."""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from ..serializers.registration import PatientRegistrationSerializer


@api_view(["POST"])
@permission_classes([AllowAny])
def register_patient(request):
    serializer = PatientRegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(
        serializer.to_representation(user), status=status.HTTP_201_CREATED,
    )
