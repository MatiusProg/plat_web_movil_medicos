"""US-10 — ABM administrativo de pacientes.

Permite:
- alta manual;
- corrección de datos;
- baja lógica;
- fusión transaccional de duplicados.

Nunca elimina físicamente un paciente.
"""

from django.db import transaction
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audit.actions import Action
from audit.services import record

from .models import Patient
from .permissions import (
    CanCreatePatients,
    CanDeactivatePatients,
    CanMergePatients,
    CanUpdatePatients,
)


class PatientAdminSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id",
            "document_type",
            "document_number",
            "first_name",
            "last_name",
            "full_name",
            "birth_date",
            "sex",
            "phone",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "created_at",
            "updated_at",
        ]

    def validate_document_number(self, value):
        if value is None:
            return None

        value = value.strip()

        return value or None

    def validate(self, attrs):
        request = self.context["request"]
        organization = request.user.organization

        document_type = attrs.get(
            "document_type",
            getattr(
                self.instance,
                "document_type",
                Patient.DocumentType.CI,
            ),
        )

        document_number = attrs.get(
            "document_number",
            getattr(
                self.instance,
                "document_number",
                None,
            ),
        )

        if document_number:
            duplicado = Patient.objects.filter(
                organization=organization,
                document_type=document_type,
                document_number=document_number,
            )

            if self.instance is not None:
                duplicado = duplicado.exclude(
                    id=self.instance.id,
                )

            if duplicado.exists():
                raise serializers.ValidationError({
                    "document_number": (
                        "Ya existe un paciente con ese documento "
                        "en esta organización."
                    )
                })

        return attrs


class MergePatientsSerializer(serializers.Serializer):
    source_patient = serializers.UUIDField()
    target_patient = serializers.UUIDField()

    def validate(self, attrs):
        if attrs["source_patient"] == attrs["target_patient"]:
            raise serializers.ValidationError({
                "target_patient": (
                    "El paciente origen y destino no pueden ser el mismo."
                )
            })

        return attrs


class PatientAdminViewSet(viewsets.ModelViewSet):
    serializer_class = PatientAdminSerializer
    queryset = Patient.objects.none()

    def get_queryset(self):
        organization = self.request.user.organization

        if organization is None:
            return Patient.objects.none()

        return Patient.objects.filter(
            organization=organization,
        ).order_by(
            "last_name",
            "first_name",
        )

    def get_permissions(self):
        if self.action == "create":
            clases = [
                IsAuthenticated,
                CanCreatePatients,
            ]

        elif self.action in {
            "update",
            "partial_update",
        }:
            clases = [
                IsAuthenticated,
                CanUpdatePatients,
            ]

        elif self.action == "destroy":
            clases = [
                IsAuthenticated,
                CanDeactivatePatients,
            ]

        elif self.action == "merge":
            clases = [
                IsAuthenticated,
                CanMergePatients,
            ]

        else:
            clases = [
                IsAuthenticated,
                CanUpdatePatients,
            ]

        return [
            clase()
            for clase in clases
        ]

    def perform_create(self, serializer):
        serializer.save(
            organization=self.request.user.organization,
        )

    def perform_update(self, serializer):
        paciente = self.get_object()

        anterior = {
            "document_type": paciente.document_type,
            "document_number": paciente.document_number,
            "first_name": paciente.first_name,
            "last_name": paciente.last_name,
            "birth_date": (
                paciente.birth_date.isoformat()
                if paciente.birth_date
                else None
            ),
            "sex": paciente.sex,
            "phone": paciente.phone,
            "is_active": paciente.is_active,
        }

        actualizado = serializer.save()

        nuevo = {
            "document_type": actualizado.document_type,
            "document_number": actualizado.document_number,
            "first_name": actualizado.first_name,
            "last_name": actualizado.last_name,
            "birth_date": (
                actualizado.birth_date.isoformat()
                if actualizado.birth_date
                else None
            ),
            "sex": actualizado.sex,
            "phone": actualizado.phone,
            "is_active": actualizado.is_active,
        }

        record(
            self.request,
            Action.PATIENT_UPDATE,
            "patients",
            actualizado.id,
            detail={
                "before": anterior,
                "after": nuevo,
            },
        )

    def destroy(self, request, *args, **kwargs):
        paciente = self.get_object()

        anterior = {
            "is_active": paciente.is_active,
        }

        paciente.is_active = False
        paciente.save(
            update_fields=[
                "is_active",
                "updated_at",
            ]
        )

        record(
            request,
            Action.PATIENT_DEACTIVATE,
            "patients",
            paciente.id,
            detail={
                "before": anterior,
                "after": {
                    "is_active": False,
                },
            },
        )

        return Response(
            status=status.HTTP_204_NO_CONTENT,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="merge",
    )
    def merge(self, request):
        entrada = MergePatientsSerializer(
            data=request.data,
        )
        entrada.is_valid(
            raise_exception=True,
        )

        organization = request.user.organization

        source_id = entrada.validated_data[
            "source_patient"
        ]
        target_id = entrada.validated_data[
            "target_patient"
        ]

        with transaction.atomic():
            source = (
                Patient.objects
                .select_for_update()
                .filter(
                    organization=organization,
                    id=source_id,
                )
                .first()
            )

            target = (
                Patient.objects
                .select_for_update()
                .filter(
                    organization=organization,
                    id=target_id,
                )
                .first()
            )

            if source is None or target is None:
                return Response(
                    {
                        "code": "paciente_no_encontrado",
                        "detail": "Paciente no encontrado.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            if not source.is_active:
                return Response(
                    {
                        "code": "paciente_origen_inactivo",
                        "detail": (
                            "El paciente origen ya se encuentra inactivo."
                        ),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            anterior = {
                "source_patient": str(source.id),
                "target_patient": str(target.id),
                "source_active": source.is_active,
                "target_active": target.is_active,
            }

            # Dependientes que estaban a cargo del registro absorbido.
            Patient.objects.filter(
                organization=organization,
                guardian=source,
            ).update(
                guardian=target,
            )

            # Antecedentes declarados.
            source.history_entries.update(
                patient=target,
            )

            # Fichas/reservas.
            source.appointments.update(
                patient=target,
            )

            # Si el registro absorbido tiene cuenta y el sobreviviente no,
            # se transfiere conservando la restricción OneToOne.
            if (
                source.user_id is not None
                and target.user_id is None
            ):
                usuario = source.user

                source.user = None
                source.save(
                    update_fields=[
                        "user",
                        "updated_at",
                    ]
                )

                target.user = usuario

            # Completar solamente datos faltantes del sobreviviente.
            campos_actualizados = []

            for campo in [
                "birth_date",
                "sex",
                "phone",
            ]:
                destino = getattr(
                    target,
                    campo,
                )
                origen = getattr(
                    source,
                    campo,
                )

                if not destino and origen:
                    setattr(
                        target,
                        campo,
                        origen,
                    )
                    campos_actualizados.append(
                        campo,
                    )

            if target.user_id is not None:
                campos_actualizados.append(
                    "user",
                )

            if campos_actualizados:
                campos_actualizados.append(
                    "updated_at",
                )

                target.save(
                    update_fields=list(
                        dict.fromkeys(
                            campos_actualizados
                        )
                    ),
                )

            source.is_active = False
            source.save(
                update_fields=[
                    "is_active",
                    "updated_at",
                ]
            )

            nuevo = {
                "source_patient": str(source.id),
                "target_patient": str(target.id),
                "source_active": False,
                "target_active": target.is_active,
            }

            record(
                request,
                Action.PATIENT_MERGE,
                "patients",
                target.id,
                detail={
                    "before": anterior,
                    "after": nuevo,
                },
            )

        return Response(
            PatientAdminSerializer(
                target,
                context={
                    "request": request,
                },
            ).data,
            status=status.HTTP_200_OK,
        )