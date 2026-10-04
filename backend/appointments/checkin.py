"""US-22 — Check-in en recepción."""

import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Appointment
from .permissions import CanReadAppointments


class CheckInSerializer(serializers.Serializer):
    qr_code = serializers.CharField(
        required=False,
        allow_blank=False,
    )
    document_number = serializers.CharField(
        required=False,
        allow_blank=False,
    )

    def validate(self, attrs):
        qr_code = attrs.get("qr_code")
        document_number = attrs.get("document_number")

        if not qr_code and not document_number:
            raise serializers.ValidationError({
                "code": "identificador_requerido",
                "detail": "Indicá el código QR o el número de documento.",
            })

        if qr_code and document_number:
            raise serializers.ValidationError({
                "code": "identificador_ambiguo",
                "detail": "Indicá solamente QR o documento, no ambos.",
            })

        return attrs


class CheckInView(APIView):
    permission_classes = [
        IsAuthenticated,
        CanReadAppointments,
    ]

    def post(self, request):
        serializer = CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        organization = request.user.organization

        qr_code = serializer.validated_data.get("qr_code")
        document_number = serializer.validated_data.get("document_number")

        with transaction.atomic():
            if qr_code:
                appointment = self._find_by_qr(
                    organization,
                    qr_code,
                )
            else:
                appointment = self._find_by_document(
                    organization,
                    document_number,
                )

            if appointment is None:
                return Response(
                    {
                        "code": "ficha_no_encontrada",
                        "detail": (
                            "No se encontró una ficha válida "
                            "para realizar el check-in."
                        ),
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if appointment.status == Appointment.Status.ATTENDED:
                return Response(
                    {
                        "code": "comprobante_ya_utilizado",
                        "detail": "Esta ficha ya registró su check-in.",
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            if appointment.status != Appointment.Status.CONFIRMED:
                return Response(
                    {
                        "code": "ficha_no_confirmada",
                        "detail": (
                            "Sólo se puede realizar check-in "
                            "sobre una ficha confirmada."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            appointment.status = Appointment.Status.ATTENDED
            appointment.checked_in_at = timezone.now()

            appointment.save(
                update_fields=[
                    "status",
                    "checked_in_at",
                    "updated_at",
                ],
            )

        return Response(
            {
                "id": str(appointment.id),
                "status": appointment.status,
                "checked_in_at": appointment.checked_in_at.isoformat(),
                "patient": {
                    "id": str(appointment.patient_id),
                    "name": appointment.patient.full_name,
                    "document_number": appointment.patient.document_number,
                },
                "branch": {
                    "id": str(appointment.branch_id),
                    "name": appointment.branch.name,
                },
                "practitioner": {
                    "id": str(appointment.practitioner_id),
                    "name": (
                        f"{appointment.practitioner.first_name} "
                        f"{appointment.practitioner.last_name}"
                    ).strip(),
                },
                "starts_at": appointment.starts_at.isoformat(),
                "ends_at": appointment.ends_at.isoformat(),
            },
            status=status.HTTP_200_OK,
        )

    def _find_by_document(
        self,
        organization,
        document_number,
    ):
        return (
            Appointment.objects
            .select_for_update()
            .select_related(
                "patient",
                "branch",
                "practitioner",
            )
            .filter(
                organization=organization,
                patient__document_number=document_number.strip(),
            )
            .order_by(
                "starts_at",
            )
            .first()
        )

    def _find_by_qr(
        self,
        organization,
        qr_code,
    ):
        """
        Compatibilidad temporal con US-19.

        Mientras US-19 no publique su comprobante/QR en esta rama,
        usamos el UUID de la ficha como payload.

        Cuando receipts.py llegue, sólo habrá que reemplazar esta
        función por el verificador real del comprobante.
        """

        try:
            appointment_id = uuid.UUID(
                qr_code.strip(),
            )
        except (ValueError, AttributeError):
            return None

        return (
            Appointment.objects
            .select_for_update()
            .select_related(
                "patient",
                "branch",
                "practitioner",
            )
            .filter(
                organization=organization,
                id=appointment_id,
            )
            .first()
        )