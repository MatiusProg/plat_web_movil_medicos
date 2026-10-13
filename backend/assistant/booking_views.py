"""US-33 — Reserva conversacional.

Dos pasos, y en ninguno el modelo de lenguaje decide nada:

    1. ``POST /api/assistant/slots/``  — los turnos que se ofrecen
    2. ``POST /api/assistant/book/``   — la reserva, con el turno que el
                                         paciente confirmó

**El modelo propone, no reserva.** La reserva es ``book_appointment``, la
misma función de la pantalla de US-17, con su bloqueo sobre la agenda y su
índice único (regla 12 del Sprint 3: una sola forma de reservar). Este
módulo no escribe en ``appointments``.

**Nada se reserva sin confirmación.** ``book/`` sólo existe para que lo llame
el botón *Confirmar*, después de que el paciente vio sucursal, profesional,
fecha y hora. No hay un camino que reserve como efecto de una pregunta.

**La conversación no se guarda en el servidor.** La memoria —qué turnos se
ofrecieron, cuál eligió— vive en el cliente. Ningún texto del paciente queda
en la base, igual que en US-31 y US-34.

**La barrera de urgencias sigue primero.** La preferencia de horario es texto
libre: "mejor hoy, no puedo respirar" es una preferencia y es una urgencia, y
se deriva antes de buscar turnos.
"""

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.booking import SlotAlreadyTaken, book_appointment
from appointments.permissions import CanCreateAppointments
from appointments.serializers import AppointmentSerializer
from audit import services as bitacora
from audit.actions import Action
from catalog.models import Specialty
from patients.models import Patient
from scheduling.permissions import CanReadSlots
from tenancy.plans import appointments_this_month, check_limit, require_feature

from . import preferences, triage
from .offers import offer_slots
from .permissions import CanUseAssistant
from .serializers import BookFromAssistantSerializer, SlotsRequestSerializer
from .views import _audit, _emergency_response


def _sin_organizacion():
    return Response(
        {"detail": "El asistente funciona dentro de una organización."},
        status=status.HTTP_403_FORBIDDEN,
    )


class SlotsView(APIView):
    """Los próximos turnos reales de una especialidad, filtrados por lo que
    el paciente pidió del horario."""

    permission_classes = [IsAuthenticated, CanUseAssistant, CanReadSlots]

    def post(self, request):
        entrada = SlotsRequestSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        organization = request.user.organization
        if organization is None:
            return _sin_organizacion()
        require_feature(organization, "ai_chatbot", "el asistente")

        # US-34, primera capa. La preferencia es texto del paciente.
        if triage.check(datos["preference"]).is_emergency:
            _audit(request, emergency_layer="regla")
            return _emergency_response("regla")

        specialty = Specialty.objects.filter(
            pk=datos["specialty"], organization=organization, is_active=True,
        ).first()
        if specialty is None:
            return Response(
                {"code": "especialidad_invalida",
                 "detail": "La especialidad no existe o no está disponible."},
                status=status.HTTP_404_NOT_FOUND,
            )

        hoy = timezone.localdate()
        preferencia = preferences.parse(datos["preference"], today=hoy)
        ofertas = offer_slots(
            organization, specialty, preferencia, branch_id=datos["branch"],
        )

        # Lo pedido no tiene turnos: se dice, y se ofrece lo más próximo. Es
        # mejor que una lista vacía, y el paciente decide si le sirve.
        cumple = True
        if not ofertas and not preferencia.is_empty:
            cumple = False
            ofertas = offer_slots(
                organization, specialty,
                preferences.parse("", today=hoy), branch_id=datos["branch"],
            )

        return Response({
            "emergency": False,
            "kind": "reserva",
            "answer": _redactar(specialty.name, ofertas, cumple),
            "generated_by": "regla",
            "specialty": {"id": str(specialty.id), "name": specialty.name},
            "preference": preferencia.as_dict(),
            "matched_preference": cumple,
            "offers": ofertas,
        })


def _redactar(especialidad, ofertas, cumple) -> str:
    """El texto que acompaña a las tarjetas. Lo arma el backend, no el
    modelo: es una frase fija sobre datos que ya están en las tarjetas."""
    if not ofertas:
        return (
            f"No encontré horarios libres de {especialidad} en las próximas "
            "dos semanas. Puedes buscar otra fecha en la pantalla de reserva."
        )
    if not cumple:
        return (
            f"No hay horarios de {especialidad} en lo que pediste. Estos son "
            "los más próximos. Elige uno y confirma para reservar."
        )
    return (
        f"Estos son los próximos horarios de {especialidad}. Elige uno y "
        "confirma para reservar."
    )


class BookView(APIView):
    """Reserva el turno que el paciente confirmó en la conversación."""

    permission_classes = [IsAuthenticated, CanUseAssistant, CanCreateAppointments]

    def post(self, request):
        entrada = BookFromAssistantSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        datos = entrada.validated_data

        organization = request.user.organization
        if organization is None:
            return _sin_organizacion()
        require_feature(organization, "ai_chatbot", "el asistente")

        titular = getattr(request.user, "patient_profile", None)
        if titular is None:
            return Response(
                {"code": "sin_ficha_de_paciente",
                 "detail": "Sólo un paciente puede reservar desde el asistente."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Para sí mismo o para un dependiente a cargo (US-07), nadie más. Un
        # paciente ajeno responde igual que uno que no existe.
        paciente_id = datos["patient"] or titular.id
        propio = Patient.objects.filter(
            Q(pk=titular.id) | Q(guardian_id=titular.id),
            pk=paciente_id, organization=organization, is_active=True,
        ).exists()
        if not propio:
            return Response(
                {"code": "paciente_invalido", "detail": "El paciente no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )

        check_limit(organization, "max_appointments_month",
                    appointments_this_month(organization),
                    "fichas por mes", "ficha por mes")

        try:
            ficha = book_appointment(
                organization=organization,
                patient_id=paciente_id,
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
        except SlotAlreadyTaken:
            return Response(
                {"code": "turno_ocupado",
                 "detail": "Ese horario se acaba de ocupar. Elige otro."},
                status=status.HTTP_409_CONFLICT,
            )

        bitacora.record(
            request, Action.ASSISTANT_BOOKING, "appointment", ficha.id,
        )
        return Response(
            AppointmentSerializer(ficha).data, status=status.HTTP_201_CREATED,
        )
