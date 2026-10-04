"""US-19 — Comprobante digital con QR.

**Formato acordado con US-22 (check-in, Daniel).** El QR contiene una sola
cadena:

    MC1.<firma de django.core.signing>

- `MC1` es la versión del formato: si mañana cambia, el mostrador sabe qué
  verificador usar sin adivinar.
- Lo firmado es `{"a": <id de la ficha>, "o": <id de la organización>}`, con
  HMAC-SHA256 sobre la `SECRET_KEY` y una sal propia (`appointments.receipt`).
  Nadie puede fabricar un comprobante sin la clave, ni reusar la firma de otro
  documento del sistema —la sal es distinta—.

**Se presenta sin conexión.** El código no se consulta contra nada para
mostrarse: el móvil lo guarda la primera vez y lo dibuja aunque no haya
señal. La verificación ocurre del lado del mostrador, que sí tiene red.

**Un solo uso.** La firma no vence ni se consume: lo que se consume es la
ficha. El check-in la pasa a `attended`, y un segundo escaneo de la misma
firma se rechaza porque la ficha ya no está `confirmed` (`checkin.py`). Una
ficha reprogramada tiene id nuevo y, por lo tanto, un comprobante nuevo; el
viejo apunta a una ficha `rescheduled` y también se rechaza.
"""

from __future__ import annotations

import uuid

from django.core import signing
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixins import owns_appointment
from .models import Appointment
from .permissions import CanReadAppointments

PREFIX = "MC1."
SALT = "appointments.receipt"


class ReceiptError(Exception):
    """El código no es un comprobante válido. `code` dice por qué."""

    def __init__(self, code: str, detail: str):
        super().__init__(detail)
        self.code = code
        self.detail = detail


def issue_code(appointment: Appointment) -> str:
    """El contenido del QR de una ficha. Determinístico: misma ficha, mismo código."""
    firma = signing.dumps(
        {"a": str(appointment.id), "o": str(appointment.organization_id)},
        salt=SALT, compress=True,
    )
    return PREFIX + firma


def read_code(code: str, organization) -> uuid.UUID:
    """Verifica la firma y devuelve el id de la ficha. Lanza `ReceiptError`."""
    code = (code or "").strip()
    if not code.startswith(PREFIX):
        raise ReceiptError(
            "comprobante_invalido",
            "El código no es un comprobante de esta plataforma.",
        )
    try:
        datos = signing.loads(code[len(PREFIX):], salt=SALT)
        appointment_id = uuid.UUID(datos["a"])
        organization_id = uuid.UUID(datos["o"])
    except (signing.BadSignature, KeyError, ValueError, TypeError) as error:
        raise ReceiptError(
            "comprobante_adulterado",
            "La firma del comprobante no es válida: el código fue alterado.",
        ) from error
    if organization is None or organization_id != organization.id:
        raise ReceiptError(
            "comprobante_de_otra_organizacion",
            "El comprobante es de otro centro médico.",
        )
    return appointment_id


def receipt_payload(appointment: Appointment) -> dict:
    return {
        "appointment_id": str(appointment.id),
        "code": issue_code(appointment),
        "issued_at": appointment.updated_at.isoformat(),
        "organization_name": appointment.organization.name,
        "patient_name": appointment.patient.full_name,
        "document_number": appointment.patient.document_number or "",
        "practitioner_name": appointment.practitioner.full_name,
        "branch_name": appointment.branch.name,
        "branch_address": appointment.branch.address,
        "starts_at": appointment.starts_at.isoformat(),
        "ends_at": appointment.ends_at.isoformat(),
        "status": appointment.status,
    }


class ReceiptView(APIView):
    """`GET /appointments/appointments/{id}/receipt/` (US-19).

    Sólo hay comprobante de una ficha pagada: `confirmed`, o `attended` para
    que el paciente lo siga viendo después de usarlo.
    """

    permission_classes = [IsAuthenticated, CanReadAppointments]

    def get(self, request, pk=None):
        appointment = (
            Appointment.objects
            .select_related("organization", "patient", "practitioner", "branch")
            .filter(pk=pk, organization=request.user.organization)
            .first()
        )
        if appointment is None or (
            getattr(request.user, "patient_profile", None) is not None
            and not owns_appointment(request.user, appointment)
        ):
            return Response({"detail": "La ficha no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        if appointment.status not in (Appointment.Status.CONFIRMED,
                                      Appointment.Status.ATTENDED):
            return Response(
                {"code": "ficha_no_confirmada",
                 "detail": "El comprobante existe recién cuando la ficha está pagada."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(receipt_payload(appointment))
