"""US-51: preconsulta opcional asociada a una ficha ya pagada.

Sólo el paciente titular o su tutor pueden leer/escribir; el endpoint no
modifica el pago, la ficha, el historial clínico ni los recordatorios.
"""
from django.http import Http404
from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixins import owns_appointment
from .models import Appointment, AppointmentPreconsultation
from .permissions import CanReadAppointments


class PreconsultationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1200, allow_blank=True, trim_whitespace=True)
    questions = serializers.CharField(max_length=1200, allow_blank=True, trim_whitespace=True)


class PreconsultationView(APIView):
    permission_classes = [IsAuthenticated, CanReadAppointments]

    def _appointment(self, request, pk):
        appointment = (Appointment.objects.select_related("patient")
                       .filter(pk=pk, organization=request.user.organization).first())
        if appointment is None or not owns_appointment(request.user, appointment):
            raise Http404
        # Ninguna preconsulta sobre reservas sin pago, canceladas o vencidas.
        if appointment.status not in (Appointment.Status.CONFIRMED, Appointment.Status.ATTENDED):
            raise Http404
        return appointment

    def get(self, request, pk):
        appointment = self._appointment(request, pk)
        item = AppointmentPreconsultation.objects.filter(
            appointment=appointment, organization=request.user.organization,
        ).first()
        return Response({
            "reason": item.reason if item else "",
            "questions": item.questions if item else "",
            "updated_at": item.updated_at if item else None,
        })

    def put(self, request, pk):
        appointment = self._appointment(request, pk)
        if appointment.status != Appointment.Status.CONFIRMED:
            return Response({"code": "appointment_closed", "detail": "La atención ya terminó."}, status=409)
        entrada = PreconsultationSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        # Restricción temporal: sólo antes del turno; no cambiar antecedentes históricos.
        from django.utils import timezone
        if appointment.starts_at <= timezone.now():
            return Response({"code": "appointment_started", "detail": "La consulta ya comenzó."}, status=409)
        with transaction.atomic():
            item, _ = AppointmentPreconsultation.objects.update_or_create(
                appointment=appointment, organization=request.user.organization,
                defaults=entrada.validated_data,
            )
        return Response({"reason": item.reason, "questions": item.questions,
                         "updated_at": item.updated_at})
