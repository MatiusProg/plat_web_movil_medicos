"""US-17 — Reserva de ficha.

Sucursal, profesional, fecha y hora sobre el endpoint de disponibilidad de
US-15. Lo que hace difícil la historia no es el formulario: es que dos
pacientes pidiendo el mismo turno al mismo tiempo tienen que terminar en una
reserva y un rechazo, nunca en dos reservas.

Eso se resuelve en dos capas:

1. `select_for_update()` sobre el `Schedule` serializa los intentos
   concurrentes sobre turnos de la misma regla de agenda.
2. El índice único parcial `uq_appointment_active_slot` (ver
   `appointments/models.py`) es la garantía real, a nivel de base: aunque la
   capa 1 fallara, dos filas para el mismo `(schedule, starts_at)` activo no
   pueden coexistir. La segunda inserción revienta con `IntegrityError`, que
   acá se traduce a un rechazo limpio.

La ficha nace `pending_payment`: sólo la confirma el webhook de Stripe de
US-18 (ajeno a este alcance). Una reserva pendiente vencida deja de contar
para `scheduling.availability._booked_slots`, así que el turno vuelve a
ofrecerse solo, sin tarea en segundo plano.
"""

from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from catalog.models import Branch, Practitioner
from patients.models import Patient
from scheduling.availability import generate_slots
from scheduling.models import Schedule

from .mixins import UUID_REGEX, OrganizationScopedMixin
from .models import Appointment
from .permissions import CanCreateAppointments, CanReadAppointments
from .serializers import AppointmentSerializer, BookAppointmentSerializer


class SlotAlreadyTaken(Exception):
    """El turno se ocupó entre que se mostró y que se confirmó la reserva."""


def _validate_slot_is_real(*, schedule: Schedule, starts_at: dt.datetime) -> dt.datetime:
    """Recalcula el turno a partir de la regla de agenda.

    Nunca se confía en la hora que manda el cliente: se reconstruye con
    `generate_slots` y se compara. Devuelve `ends_at`. Lanza
    `django.core.exceptions.ValidationError` si `starts_at` no es un espacio
    real de esa regla.
    """
    tz = ZoneInfo(schedule.branch.timezone or "America/La_Paz")
    day = starts_at.astimezone(tz).date()
    for _day, slot_start, slot_end in generate_slots(schedule, day, day, tz=tz):
        if slot_start == starts_at:
            return slot_end
    raise ValidationError(
        "Ese horario no corresponde a un espacio real de la agenda.",
        code="turno_invalido",
    )


def book_appointment(
    *,
    organization,
    patient_id,
    practitioner_id,
    branch_id,
    schedule_id,
    starts_at: dt.datetime,
    booked_by,
) -> Appointment:
    """Reserva un turno. Lanza `ValidationError` o `SlotAlreadyTaken`."""
    patient = Patient.objects.filter(
        pk=patient_id, organization=organization, is_active=True,
    ).first()
    if patient is None:
        raise ValidationError("El paciente no existe.", code="paciente_invalido")

    practitioner = Practitioner.objects.filter(
        pk=practitioner_id, organization=organization, is_active=True,
    ).first()
    if practitioner is None:
        raise ValidationError(
            "El profesional no existe o está inactivo.", code="profesional_invalido",
        )

    branch = Branch.objects.filter(
        pk=branch_id, organization=organization, is_active=True,
    ).first()
    if branch is None:
        raise ValidationError(
            "La sucursal no existe o está inactiva.", code="sucursal_invalida",
        )

    now = timezone.now()
    if starts_at <= now:
        raise ValidationError("Ese horario ya pasó.", code="turno_pasado")

    hold_minutes = settings.APPOINTMENT_HOLD_MINUTES

    with transaction.atomic():
        schedule = (
            Schedule.objects.select_for_update()
            .select_related("branch")
            .filter(
                pk=schedule_id, organization=organization, branch_id=branch_id,
                practitioner_id=practitioner_id, is_active=True,
            )
            .first()
        )
        if schedule is None:
            raise ValidationError(
                "La agenda no existe o no coincide con el profesional y la "
                "sucursal.", code="agenda_invalida",
            )

        ends_at = _validate_slot_is_real(schedule=schedule, starts_at=starts_at)

        try:
            return Appointment.objects.create(
                organization=organization,
                patient=patient,
                booked_by=booked_by,
                practitioner=practitioner,
                branch=branch,
                schedule=schedule,
                starts_at=starts_at,
                ends_at=ends_at,
                status=Appointment.Status.PENDING_PAYMENT,
                expires_at=now + dt.timedelta(minutes=hold_minutes),
            )
        except IntegrityError as error:
            if "uq_appointment_active_slot" in str(error):
                raise SlotAlreadyTaken(
                    "Ese horario se acaba de ocupar. Elegí otro."
                ) from error
            raise


class AppointmentViewSet(OrganizationScopedMixin, viewsets.ModelViewSet):
    """`GET/POST /appointments/appointments/`.

    Un paciente ve —y reserva— sólo las fichas suyas y las de sus
    dependientes (US-07). Quien tiene `appointments.appointment.read` de
    mostrador —sin ser paciente— ve las de toda la organización, para el
    check-in de US-22.
    """

    serializer_class = AppointmentSerializer
    lookup_value_regex = UUID_REGEX
    http_method_names = ["get", "post", "head", "options"]
    # Las fichas de un paciente son un conjunto acotado —"mis fichas"—, igual
    # que `catalog.branches`/`specialties`: no hace falta paginar.
    pagination_class = None
    permission_classes_by_action = {
        "list": [CanReadAppointments],
        "retrieve": [CanReadAppointments],
        "create": [CanCreateAppointments],
    }

    def get_permissions(self):
        clases = self.permission_classes_by_action.get(
            self.action, [CanReadAppointments],
        )
        return [IsAuthenticated()] + [clase() for clase in clases]

    def get_queryset(self):
        queryset = self.scoped(
            Appointment.objects.select_related(
                "patient", "practitioner", "branch",
            ),
        )
        paciente = getattr(self.request.user, "patient_profile", None)
        if paciente is not None:
            queryset = queryset.filter(
                models.Q(patient_id=paciente.id)
                | models.Q(patient__guardian_id=paciente.id),
            )
        params = self.request.query_params
        if estado := params.get("status"):
            queryset = queryset.filter(status=estado)
        return queryset

    def create(self, request, *args, **kwargs):
        entrada = BookAppointmentSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        try:
            ficha = book_appointment(
                organization=request.user.organization,
                patient_id=datos["patient"],
                practitioner_id=datos["practitioner"],
                branch_id=datos["branch"],
                schedule_id=datos["schedule"],
                starts_at=datos["starts_at"],
                booked_by=request.user,
            )
        except ValidationError as error:
            return Response(
                {"code": error.code or "reserva_invalida",
                 "detail": error.messages[0]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except SlotAlreadyTaken as error:
            return Response(
                {"code": "turno_ocupado", "detail": str(error)},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            self.get_serializer(ficha).data, status=status.HTTP_201_CREATED,
        )
