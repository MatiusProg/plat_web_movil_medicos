"""US-49 — Endpoints de los recordatorios de medicamentos.

- ``GET  /api/encounters/medications/<paciente>/``  los medicamentos de las
  atenciones firmadas recientes, con su horario, su cumplimiento y las tomas
  marcadas. Es lo que arma *Mis medicamentos* en el móvil.
- ``GET  /api/encounters/prescription/<medicamento>/intakes/``  las tomas.
- ``POST /api/encounters/prescription/<medicamento>/intakes/``  marcar una.

Todo pide ``encounters.history.read`` **y** el alcance propio sobre el
paciente (el paciente o el titular de su dependiente). El médico ve el
cumplimiento en el historial y en la atención, no acá.
"""

import datetime as dt
import uuid

from django.http import Http404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from patients.models import Patient

from . import intakes, services
from .frequency import para_la_api
from .history_views import CanReadHistory
from .models import Encounter, MedicationIntake, PrescriptionItem

# *Mis medicamentos* muestra lo recetado en este plazo: un tratamiento de más
# de 90 días no se recuerda con avisos (`frequency.MAX_DIAS`).
VENTANA_DIAS = 120


class IntakeWriteSerializer(serializers.Serializer):
    dose_number = serializers.IntegerField(min_value=1)
    status = serializers.ChoiceField(choices=MedicationIntake.Status.choices)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)


class IntakeReadSerializer(serializers.Serializer):
    dose_number = serializers.IntegerField()
    status = serializers.CharField()
    scheduled_at = serializers.DateTimeField(allow_null=True)
    recorded_at = serializers.DateTimeField()


def _uuid(valor):
    try:
        return uuid.UUID(str(valor))
    except ValueError:
        raise Http404


def _medicamento_propio(request, item_pk):
    item = (PrescriptionItem.objects
            .filter(organization=request.user.organization, pk=_uuid(item_pk),
                    encounter__status=Encounter.Status.SIGNED)
            .select_related("encounter__patient").first())
    if item is None or services.history_scope(
        request.user, item.encounter.patient,
    ) != services.OWN:
        raise Http404
    return item


class MedicationIntakesView(APIView):
    permission_classes = [IsAuthenticated, CanReadHistory]

    def get(self, request, item_pk):
        item = _medicamento_propio(request, item_pk)
        return Response({"intakes": IntakeReadSerializer(
            [intakes.as_dict(t) for t in item.intakes.all()], many=True).data})

    def post(self, request, item_pk):
        item = _medicamento_propio(request, item_pk)
        datos = IntakeWriteSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        toma = intakes.registrar(
            request.user, item, datos.validated_data["dose_number"],
            datos.validated_data["status"],
            datos.validated_data.get("scheduled_at"),
        )
        return Response(IntakeReadSerializer(intakes.as_dict(toma)).data, status=201)


class MyMedicationsView(APIView):
    permission_classes = [IsAuthenticated, CanReadHistory]

    def get(self, request, patient_id):
        paciente = Patient.objects.filter(
            organization=request.user.organization, pk=_uuid(patient_id),
        ).first()
        if services.history_scope(request.user, paciente) != services.OWN:
            raise Http404

        desde = timezone.now() - dt.timedelta(days=VENTANA_DIAS)
        items = (PrescriptionItem.objects
                 .filter(organization=request.user.organization,
                         encounter__patient=paciente,
                         encounter__status=Encounter.Status.SIGNED,
                         encounter__signed_at__gte=desde)
                 .select_related("encounter__practitioner")
                 .prefetch_related("intakes")
                 .order_by("-encounter__signed_at", "created_at"))

        salida = []
        for item in items:
            horario = para_la_api(item.frequency, item.duration)
            salida.append({
                "id": str(item.id),
                "encounter": str(item.encounter_id),
                "prescribed_at": item.encounter.signed_at,
                "practitioner_name": item.encounter.practitioner.full_name,
                "medication": item.medication,
                "dose": item.dose,
                "frequency": item.frequency,
                "duration": item.duration,
                "instructions": item.instructions,
                **horario,
                "adherence": intakes.cumplimiento(item, horario["schedule"]),
                "intakes": IntakeReadSerializer(
                    [intakes.as_dict(t) for t in item.intakes.all()], many=True).data,
            })
        return Response({"patient": str(paciente.id), "medications": salida})
