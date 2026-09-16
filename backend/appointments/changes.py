"""US-20 — Cancelación y reprogramación de fichas.

Dentro de la política de anticipación de la organización, que es un parámetro
—`Organization.cancellation_notice_hours`— y no una constante en código.
Cancelar libera el turno en el acto: al dejar de estar en
`Appointment.ACTIVE_STATUSES`, `scheduling.availability._booked_slots` ya no
lo cuenta. Reprogramar es liberar y volver a tomar **en una sola
transacción**: si la segunda mitad falla, la ficha original sigue intacta y el
paciente no se queda sin las dos.
"""

from __future__ import annotations

import datetime as dt

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.actions import Action
from audit.services import record

from .booking import SlotAlreadyTaken, book_appointment
from .mixins import owns_appointment
from .models import Appointment
from .permissions import CanCancelAppointments, CanRescheduleAppointments
from .serializers import AppointmentSerializer, RescheduleAppointmentSerializer


def _notice(appointment: Appointment, now: dt.datetime) -> dt.timedelta:
    return appointment.starts_at - now


def _assert_cancellable(appointment: Appointment, now: dt.datetime) -> None:
    if not appointment.is_active:
        raise ValidationError(
            "Esta ficha ya no se puede cancelar ni reprogramar.",
            code="ficha_no_activa",
        )
    if appointment.starts_at <= now:
        raise ValidationError(
            "Esta ficha ya pasó.", code="ficha_pasada",
        )


def cancel_appointment(appointment: Appointment, *, now=None) -> Appointment:
    """US-20 — Cancela la ficha y decide si corresponde devolución.

    No ejecuta el reembolso: eso lo hace US-18 (pago con Stripe, ajeno a este
    alcance) leyendo `refund_eligible`. Acá sólo se decide, según la
    anticipación, si corresponde.
    """
    now = now or timezone.now()
    _assert_cancellable(appointment, now)

    notice = _notice(appointment, now)
    umbral = dt.timedelta(hours=appointment.organization.cancellation_notice_hours)

    appointment.status = Appointment.Status.CANCELLED
    appointment.cancelled_at = now
    appointment.cancellation_reason = Appointment.CancellationReason.PATIENT
    appointment.refund_eligible = notice >= umbral
    appointment.save(update_fields=[
        "status", "cancelled_at", "cancellation_reason", "refund_eligible",
        "updated_at",
    ])
    return appointment


def reschedule_appointment(
    appointment: Appointment,
    *,
    branch_id,
    schedule_id,
    starts_at: dt.datetime,
    now=None,
) -> Appointment:
    """US-20 — Reprograma: libera el turno viejo y toma uno nuevo, atómico.

    La ficha nueva hereda el estado de pago de la vieja: si ya estaba
    `confirmed`, la nueva nace `confirmed` también —es la misma compra movida
    de horario, no una reserva nueva—.
    """
    now = now or timezone.now()
    _assert_cancellable(appointment, now)

    with transaction.atomic():
        try:
            nueva = book_appointment(
                organization=appointment.organization,
                patient_id=appointment.patient_id,
                practitioner_id=appointment.practitioner_id,
                branch_id=branch_id,
                schedule_id=schedule_id,
                starts_at=starts_at,
                booked_by=appointment.booked_by,
            )
        except (ValidationError, SlotAlreadyTaken):
            # La transacción revierte sola al salir con la excepción: la
            # ficha original no se toca.
            raise

        if appointment.status == Appointment.Status.CONFIRMED:
            nueva.status = Appointment.Status.CONFIRMED
            nueva.expires_at = None
            nueva.save(update_fields=["status", "expires_at", "updated_at"])

        appointment.status = Appointment.Status.RESCHEDULED
        appointment.save(update_fields=["status", "updated_at"])
        nueva.rescheduled_from = appointment
        nueva.save(update_fields=["rescheduled_from", "updated_at"])

    return nueva


def _puede_operar(user, appointment) -> bool:
    """El propio paciente/titular, o mostrador con permiso explícito.

    Quien tiene ficha de paciente (`patient_profile`) sólo opera sobre la
    suya o la de sus dependientes; quien no —personal de mostrador— ya pasó el
    filtro de permiso de la vista (`appointments.appointment.cancel/
    reschedule`), así que puede operar sobre cualquiera de su organización.
    """
    if getattr(user, "patient_profile", None) is None:
        return True
    return owns_appointment(user, appointment)


def _get_appointment_or_404(request, pk):
    return (
        Appointment.objects.select_related(
            "organization", "patient", "booked_by",
        )
        .filter(pk=pk, organization=request.user.organization)
        .first()
    )


class CancelAppointmentView(APIView):
    """`POST /appointments/appointments/{id}/cancel/` (US-20)."""

    permission_classes = [IsAuthenticated, CanCancelAppointments]

    def post(self, request, pk=None):
        appointment = _get_appointment_or_404(request, pk)
        if appointment is None:
            return Response(
                {"detail": "La ficha no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _puede_operar(request.user, appointment):
            return Response(
                {"detail": "No podés cancelar una ficha que no es tuya."},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            cancel_appointment(appointment)
        except ValidationError as error:
            return Response(
                {"code": error.code or "cancelacion_invalida",
                 "detail": error.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record(
            request, Action.APPOINTMENT_CANCEL, "appointment", appointment.id,
            detail={"refund_eligible": appointment.refund_eligible},
        )
        return Response(AppointmentSerializer(appointment).data)


class RescheduleAppointmentView(APIView):
    """`POST /appointments/appointments/{id}/reschedule/` (US-20)."""

    permission_classes = [IsAuthenticated, CanRescheduleAppointments]

    def post(self, request, pk=None):
        appointment = _get_appointment_or_404(request, pk)
        if appointment is None:
            return Response(
                {"detail": "La ficha no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not _puede_operar(request.user, appointment):
            return Response(
                {"detail": "No podés reprogramar una ficha que no es tuya."},
                status=status.HTTP_403_FORBIDDEN,
            )

        entrada = RescheduleAppointmentSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        try:
            nueva = reschedule_appointment(
                appointment,
                branch_id=datos["branch"],
                schedule_id=datos["schedule"],
                starts_at=datos["starts_at"],
            )
        except ValidationError as error:
            return Response(
                {"code": error.code or "reprogramacion_invalida",
                 "detail": error.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SlotAlreadyTaken as error:
            return Response(
                {"code": "turno_ocupado", "detail": str(error)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(AppointmentSerializer(nueva).data)
