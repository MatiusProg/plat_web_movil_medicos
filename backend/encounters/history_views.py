"""US-25 — `GET /api/encounters/history/<paciente>/`

Todos los encuentros **firmados** del paciente, en una sola línea de tiempo,
**sin importar la sucursal ni el médico**. Es el argumento multi-sede del
proyecto aplicado a la historia clínica, el mismo que US-15 aplicó a la
disponibilidad: el paciente es uno, aunque lo hayan atendido en tres sedes.

- Los borradores no aparecen: lo que no está firmado todavía no es historia
  clínica, y el borrador de otro médico no es asunto de quien lee.
- La lectura exige el permiso `encounters.history.read` **y** un alcance
  sobre el paciente (ver `services.history_scope`). Sin alcance, 404.
- **Cada lectura deja asiento en la bitácora**, con el alcance con que se
  leyó y sin una sola línea del contenido.
"""

from collections import Counter

from django.http import Http404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit import services as bitacora
from audit.actions import Action
from patients.models import Patient

from . import services
from .models import Encounter
from .permissions import RequiresPermission
from .serializers import EncounterSerializer, PatientSummarySerializer


class CanReadHistory(RequiresPermission):
    code = "encounters.history.read"


class PatientHistoryView(APIView):
    permission_classes = [IsAuthenticated, CanReadHistory]

    def get(self, request, patient_id):
        paciente = Patient.objects.filter(
            organization=request.user.organization, pk=patient_id,
        ).first()
        alcance = services.history_scope(request.user, paciente)
        if alcance is None:
            raise Http404

        encuentros = list(
            Encounter.objects
            .filter(organization=request.user.organization, patient=paciente,
                    status=Encounter.Status.SIGNED)
            .select_related("patient", "practitioner", "branch", "appointment",
                            "signed_by")
            .prefetch_related("amendments__author", "prescription_items", "orders")
            .order_by("-appointment__starts_at")
        )

        bitacora.record(
            request, Action.RECORD_READ, "patients", entity_id=paciente.pk,
            detail={"origen": "historial", "alcance": alcance,
                    "encuentros": len(encuentros)},
        )

        por_sucursal = Counter(e.branch.name for e in encuentros)
        return Response({
            "patient": PatientSummarySerializer(paciente).data,
            "scope": alcance,
            "branches": [{"name": n, "encounters": c}
                         for n, c in sorted(por_sucursal.items())],
            "encounters": EncounterSerializer(encuentros, many=True).data,
        })


class PatientHistorySummaryView(APIView):
    """US-41 — `GET /api/encounters/history/<paciente>/summary/`

    El resumen del historial, **sólo para el médico con vínculo de atención**.
    El propio paciente recibe 404 aunque lea su historial: un texto generado
    no le llega sin que un médico lo apruebe (regla 14 del Sprint 4). Ver
    `summary.py`.

    Deja el mismo asiento que leer el historial, más quién redactó el texto,
    y ni una línea del resumen.
    """

    permission_classes = [IsAuthenticated, CanReadHistory]

    def get(self, request, patient_id):
        from .summary import summarize

        paciente = Patient.objects.filter(
            organization=request.user.organization, pk=patient_id,
        ).first()
        if services.history_scope(request.user, paciente) != services.PROFESSIONAL:
            raise Http404

        resumen = summarize(paciente)
        bitacora.record(
            request, Action.RECORD_READ, "patients", entity_id=paciente.pk,
            detail={"origen": "resumen", "alcance": services.PROFESSIONAL,
                    "encuentros": len(resumen["sources"]),
                    "generado_por": resumen["generated_by"]},
        )
        return Response({"patient": PatientSummarySerializer(paciente).data, **resumen})
