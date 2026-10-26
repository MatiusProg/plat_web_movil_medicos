"""US-23: reserva asistida por recepción, separada de la reserva del paciente."""
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from tenancy.plans import appointments_this_month, check_limit
from .booking import SlotAlreadyTaken, book_appointment
from .permissions import RequiresPermission
from .serializers import AppointmentSerializer, BookAppointmentSerializer


class CanBookAtCounter(RequiresPermission):
    code = "appointments.appointment.book_at_counter"


class CounterBookingView(APIView):
    permission_classes = [IsAuthenticated, CanBookAtCounter]

    def post(self, request):
        entrada = BookAppointmentSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        organization = request.user.organization
        if organization is None:
            return Response({"code": "organizacion_requerida", "detail": "Necesitás seleccionar un centro médico."}, status=403)
        check_limit(organization, "max_appointments_month",
                    appointments_this_month(organization), "fichas por mes", "ficha por mes")
        datos = entrada.validated_data
        try:
            ficha = book_appointment(
                organization=organization, patient_id=datos["patient"],
                practitioner_id=datos["practitioner"], branch_id=datos["branch"],
                schedule_id=datos["schedule"], starts_at=datos["starts_at"],
                booked_by=request.user,
            )
        except ValidationError as error:
            return Response({"code": getattr(error, "code", None) or "reserva_invalida",
                             "detail": error.messages[0]}, status=status.HTTP_400_BAD_REQUEST)
        except SlotAlreadyTaken as error:
            return Response({"code": "turno_ocupado", "detail": str(error)}, status=status.HTTP_409_CONFLICT)
        return Response(AppointmentSerializer(ficha, context={"request": request}).data,
                        status=status.HTTP_201_CREATED)
