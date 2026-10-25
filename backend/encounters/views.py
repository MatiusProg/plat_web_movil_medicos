"""US-24 — `/api/encounters/`

    GET   agenda/?date=AAAA-MM-DD   las fichas del día del profesional
    POST  /                         abrir la atención de una ficha
    GET   <id>/                     ver el encuentro          → bitácora
    PATCH <id>/                     editar el borrador
    POST  <id>/sign/                firmar (queda fijo)
    POST  <id>/amendments/          enmendar un encuentro firmado

    US-26 — la receta y las órdenes, mientras el encuentro es borrador:

    POST         <id>/prescription/          agregar un medicamento
    PATCH|DELETE <id>/prescription/<renglón>/
    POST         <id>/orders/                agregar una orden
    PATCH|DELETE <id>/orders/<orden>/
    GET          <id>/prescription.pdf       la receta firmada  → bitácora

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

from django.http import Http404, HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from appointments.models import Appointment
from audit import services as bitacora
from audit.actions import Action

from . import prescription_pdf, services
from .models import Encounter
from .permissions import CanAmendEncounters, CanCreateEncounters, CanReadEncounters
from .serializers import (
    AgendaItemSerializer,
    AmendmentSerializer,
    AmendmentWriteSerializer,
    EncounterDraftSerializer,
    EncounterSerializer,
    MedicalOrderSerializer,
    OpenEncounterSerializer,
    PrescriptionItemSerializer,
)

CHILD_SERIALIZERS = {
    "prescription": PrescriptionItemSerializer,
    "orders": MedicalOrderSerializer,
}


def _own_encounter(request, pk):
    """El encuentro, si es del profesional que pide. Si no, 404."""
    encuentro = (
        Encounter.objects
        .filter(organization=request.user.organization, pk=pk)
        .select_related("patient", "practitioner", "branch", "appointment",
                        "signed_by")
        .prefetch_related("amendments__author", "prescription_items", "orders")
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
                {"detail": "No tienes ficha de profesional en esta organización."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tz = ZoneInfo(request.user.organization.timezone or "America/La_Paz")
        texto = request.query_params.get("date")
        try:
            dia = dt.date.fromisoformat(texto) if texto else timezone.now().astimezone(tz).date()
        except ValueError:
            return Response({"date": ["Usa el formato AAAA-MM-DD."]},
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


# --------------------------------------------------------------------------
#  US-26 — Receta y órdenes
# --------------------------------------------------------------------------

class EncounterChildrenView(APIView):
    """Agregar un medicamento (``kind="prescription"``) o una orden.

    Devuelve el encuentro entero y no sólo el renglón: la pantalla de la
    atención se redibuja con lo que dice el servidor, no con lo que cree que
    pasó.
    """

    permission_classes = [IsAuthenticated, CanCreateEncounters]
    kind = ""

    def post(self, request, pk):
        encuentro = _own_encounter(request, pk)
        entrada = CHILD_SERIALIZERS[self.kind](data=request.data)
        entrada.is_valid(raise_exception=True)
        services.add_child(encuentro, self.kind, entrada.validated_data)
        return Response(EncounterSerializer(_own_encounter(request, pk)).data,
                        status=status.HTTP_201_CREATED)


class EncounterChildDetailView(APIView):
    """Corregir o quitar un renglón de la receta, o una orden, del borrador."""

    permission_classes = [IsAuthenticated, CanCreateEncounters]
    kind = ""

    def _child(self, encuentro, child_pk):
        modelo = services.CHILDREN[self.kind]
        renglon = modelo.objects.filter(encounter=encuentro, pk=child_pk).first()
        if renglon is None:
            raise Http404
        return renglon

    def patch(self, request, pk, child_pk):
        encuentro = _own_encounter(request, pk)
        renglon = self._child(encuentro, child_pk)
        entrada = CHILD_SERIALIZERS[self.kind](renglon, data=request.data, partial=True)
        entrada.is_valid(raise_exception=True)
        services.update_child(encuentro, renglon, entrada.validated_data)
        return Response(EncounterSerializer(_own_encounter(request, pk)).data)

    def delete(self, request, pk, child_pk):
        encuentro = _own_encounter(request, pk)
        services.delete_child(encuentro, self._child(encuentro, child_pk))
        return Response(EncounterSerializer(_own_encounter(request, pk)).data)


class PrescriptionPdfView(APIView):
    """La receta y las órdenes de una atención firmada, en PDF.

    La pueden bajar dos personas, cada una con su permiso:

    - **el médico que atendió** (``encounters.encounter.read``), para
      imprimirla en la consulta;
    - **quien tiene alcance sobre el historial del paciente**
      (``encounters.history.read`` y ``services.history_scope``): el propio
      paciente, el titular de un dependiente (US-27) y un médico con vínculo
      de atención, igual que el historial de US-25.

    **Sólo de un encuentro firmado.** Un borrador todavía puede cambiar, y una
    receta impresa que después cambia es una receta que no coincide con la
    historia. Al médico que atiende se le dice por qué (409); a cualquier otro
    un borrador ajeno le responde 404, como en el historial.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        encuentro = (
            Encounter.objects
            .filter(organization=user.organization, pk=pk)
            .select_related("organization", "patient", "practitioner", "branch",
                            "appointment", "signed_by")
            .prefetch_related("amendments__author", "prescription_items", "orders")
            .first()
        )
        if encuentro is None:
            raise Http404

        if services.is_own(user, encuentro) and user.has_permission(
            "encounters.encounter.read",
        ):
            alcance = "attending"
        else:
            alcance = (
                services.history_scope(user, encuentro.patient)
                if user.has_permission("encounters.history.read") else None
            )
            if alcance is None or not encuentro.is_signed:
                raise Http404

        if not encuentro.is_signed:
            raise services.Conflict(
                "Firma la atención antes de descargar la receta: un borrador "
                "todavía puede cambiar.",
            )
        if not encuentro.prescription_items.all() and not encuentro.orders.all():
            raise services.Conflict("La atención no tiene receta ni órdenes.")

        contenido = prescription_pdf.render(encuentro)
        _audit(request, Action.RECORD_READ, encuentro,
               origen="receta_pdf", alcance=alcance)

        nombre = prescription_pdf.filename(encuentro)
        respuesta = HttpResponse(contenido, content_type="application/pdf")
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        respuesta["Access-Control-Expose-Headers"] = "Content-Disposition"
        return respuesta
