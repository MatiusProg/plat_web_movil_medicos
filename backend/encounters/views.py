"""US-24 — `/api/encounters/`

    GET   agenda/?date=AAAA-MM-DD   las fichas del día del profesional
    POST  /                         abrir la atención de una ficha
    GET   <id>/                     ver el encuentro          → bitácora
    PATCH <id>/                     editar el borrador
    POST  <id>/sign/                firmar (queda fijo)
    POST  <id>/amendments/          enmendar un encuentro firmado

**Un encuentro ajeno responde 404, no 403.** Un 403 confirma que ese
encuentro existe, y la existencia de una atención ya es un dato clínico
(dice que esa persona se atendió). Es el mismo criterio de US-08 con los
antecedentes.

**La bitácora guarda quién abrió qué historia, nunca su contenido.** Igual
que el asistente con las consultas: copiar el texto clínico a la bitácora
sería una historia paralela sin ninguna de sus protecciones.
"""

import datetime as dt
from zoneinfo import ZoneInfo

from django.http import Http404
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from audit import services as bitacora
from audit.actions import Action

from . import services
from .models import Encounter
from .permissions import CanAmendEncounters, CanCreateEncounters, CanReadEncounters
from .serializers import (
    AgendaItemSerializer,
    AmendmentSerializer,
    AmendmentWriteSerializer,
    EncounterDraftSerializer,
    EncounterSerializer,
    OpenEncounterSerializer,
)


def _own_encounter(request, pk):
    """El encuentro, si es del profesional que pide. Si no, 404."""
    encuentro = (
        Encounter.objects
        .filter(organization=request.user.organization, pk=pk)
        .select_related("patient", "practitioner", "branch", "appointment",
                        "signed_by")
        .prefetch_related("amendments__author")
        .first()
    )
    if encuentro is None or not services.is_own(request.user, encuentro):
        raise Http404
    return encuentro


def _audit(request, action, encuentro, **extra):
    bitacora.record(
        request, action, "encounters", entity_id=encuentro.pk,
        detail={"patient": str(encuentro.patient_id), **extra},
    )


class AgendaView(APIView):
    """Las fichas del profesional para un día, con el estado de su atención."""

    permission_classes = [IsAuthenticated, CanReadEncounters]

    def get(self, request):
        profesional = services.practitioner_of(request.user)
        if profesional is None:
            return Response(
                {"detail": "No tenés ficha de profesional en esta organización."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tz = ZoneInfo(request.user.organization.timezone or "America/La_Paz")
        texto = request.query_params.get("date")
        try:
            dia = dt.date.fromisoformat(texto) if texto else timezone.now().astimezone(tz).date()
        except ValueError:
            return Response({"date": ["Usá el formato AAAA-MM-DD."]},
                            status=status.HTTP_400_BAD_REQUEST)

        desde = dt.datetime.combine(dia, dt.time.min, tzinfo=tz)
        fichas = (
            Appointment.objects
            .filter(
                organization=request.user.organization,
                practitioner=profesional,
                starts_at__gte=desde,
                starts_at__lt=desde + dt.timedelta(days=1),
                status__in=services.ATTENDABLE_STATUSES,
            )
            .select_related("patient", "branch", "encounter")
            .order_by("starts_at")
        )
        return Response({
            "date": dia.isoformat(),
            "practitioner": profesional.full_name,
            "appointments": AgendaItemSerializer(fichas, many=True).data,
        })


class EncounterOpenView(APIView):
    permission_classes = [IsAuthenticated, CanCreateEncounters]

    def post(self, request):
        entrada = OpenEncounterSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        ficha = entrada.validated_data["appointment"]
        if ficha.organization_id != request.user.organization_id:
            raise Http404

        encuentro, creado = services.open_encounter(request.user, ficha)
        if creado:
            _audit(request, Action.ENCOUNTER_OPEN, encuentro)
        encuentro = _own_encounter(request, encuentro.pk)
        return Response(
            EncounterSerializer(encuentro).data,
            status=status.HTTP_201_CREATED if creado else status.HTTP_200_OK,
        )


class EncounterDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        cls = CanReadEncounters if self.request.method == "GET" else CanCreateEncounters
        return [IsAuthenticated(), cls()]

    def get(self, request, pk):
        encuentro = _own_encounter(request, pk)
        # La apertura de la historia clínica: el asiento que más importa.
        _audit(request, Action.RECORD_READ, encuentro)
        return Response(EncounterSerializer(encuentro).data)

    def patch(self, request, pk):
        encuentro = _own_encounter(request, pk)
        entrada = EncounterDraftSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        services.update_draft(encuentro, entrada.validated_data)
        return Response(EncounterSerializer(_own_encounter(request, pk)).data)


class EncounterSignView(APIView):
    permission_classes = [IsAuthenticated, CanCreateEncounters]

    def post(self, request, pk):
        encuentro = _own_encounter(request, pk)
        services.sign(encuentro, request.user)
        _audit(request, Action.ENCOUNTER_SIGN, encuentro)
        return Response(EncounterSerializer(_own_encounter(request, pk)).data)


class EncounterAmendView(APIView):
    permission_classes = [IsAuthenticated, CanAmendEncounters]

    def post(self, request, pk):
        encuentro = _own_encounter(request, pk)
        entrada = AmendmentWriteSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        enmienda = services.amend(
            encuentro, request.user,
            entrada.validated_data["section"], entrada.validated_data["text"],
        )
        _audit(request, Action.ENCOUNTER_AMEND, encuentro,
               section=enmienda.section)
        return Response(AmendmentSerializer(enmienda).data,
                        status=status.HTTP_201_CREATED)
