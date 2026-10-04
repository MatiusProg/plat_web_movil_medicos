"""US-21 — Confirmación de asistencia.

El paciente confirma que va a ir. La infraestructura de notificaciones push
es US-28 (Sprint 3): en este sprint la confirmación vive **dentro de la app**
y **por correo**, con un enlace firmado que no exige iniciar sesión.

**Se deja asentado el desenlace** (sección 3 del reparto): la confirmación
queda con fecha y hora en `Appointment.attendance_confirmed_at`. Una ficha
`attended` o `no_show` con ese campo en NULL es un *no confirmó*; con fecha,
un *confirmó*. Es la etiqueta que el modelo de inasistencia del Sprint 4
necesita, y si no se guarda desde ahora no hay historial que etiquetar.
"""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.html import format_html
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.actions import Action
from audit.services import record
from tenancy.context import tenant_context

from .mixins import owns_appointment
from .models import Appointment
from .permissions import CanConfirmAttendance
from .receipts import issue_code
from .serializers import AppointmentSerializer

logger = logging.getLogger(__name__)

LINK_SALT = "appointments.attendance-link"


def confirm_attendance(appointment: Appointment, *, now=None) -> Appointment:
    """Asienta la confirmación. Idempotente: confirmar dos veces no cambia la fecha."""
    now = now or timezone.now()
    if appointment.status != Appointment.Status.CONFIRMED:
        raise ValidationError(
            "Sólo se confirma la asistencia de una ficha pagada.",
            code="ficha_no_confirmada",
        )
    if appointment.starts_at <= now:
        raise ValidationError("Esta ficha ya pasó.", code="ficha_pasada")
    if appointment.attendance_confirmed_at is None:
        appointment.attendance_confirmed_at = now
        appointment.save(update_fields=["attendance_confirmed_at", "updated_at"])
    return appointment


class ConfirmAttendanceView(APIView):
    """`POST /appointments/appointments/{id}/confirm-attendance/` (US-21)."""

    permission_classes = [IsAuthenticated, CanConfirmAttendance]

    def post(self, request, pk=None):
        appointment = (
            Appointment.objects
            .select_related("patient", "practitioner", "branch")
            .filter(pk=pk, organization=request.user.organization)
            .first()
        )
        if appointment is None or not owns_appointment(request.user, appointment):
            return Response({"detail": "La ficha no existe."},
                            status=status.HTTP_404_NOT_FOUND)
        ya_estaba = appointment.attendance_confirmed_at is not None
        try:
            confirm_attendance(appointment)
        except ValidationError as error:
            return Response({"code": error.code, "detail": error.messages[0]},
                            status=status.HTTP_400_BAD_REQUEST)
        if not ya_estaba:
            record(request, Action.APPOINTMENT_ATTENDANCE_CONFIRM, "appointment",
                   appointment.id, detail={"canal": "app"})
        return Response(AppointmentSerializer(appointment).data)


# ---------- Por correo ---------------------------------------------------

def attendance_link(appointment: Appointment) -> str:
    token = signing.dumps(
        {"a": str(appointment.id), "o": str(appointment.organization_id)},
        salt=LINK_SALT,
    )
    return settings.PUBLIC_API_BASE_URL + reverse(
        "appointments:attendance-link", args=[token],
    )


def _destinatario(appointment: Appointment) -> str:
    """El correo del paciente o, si es un dependiente sin cuenta, el del titular."""
    paciente = appointment.patient
    for candidato in (paciente, paciente.guardian):
        user = getattr(candidato, "user", None) if candidato else None
        if user is not None and user.email:
            return user.email
    return ""


def send_confirmation_email(appointment_id, organization_id) -> bool:
    """Aviso de ficha pagada: comprobante y enlace para confirmar asistencia.

    Corre después del COMMIT del pago, fuera de la petición: abre su propio
    contexto. Nunca propaga un error —un correo caído no deshace un pago—.
    """
    try:
        with tenant_context(organization_id):
            appointment = (
                Appointment.objects
                .select_related("organization", "patient__user",
                                "patient__guardian__user", "practitioner", "branch")
                .get(pk=appointment_id)
            )
            destino = _destinatario(appointment)
            if not destino:
                return False
            inicio = timezone.localtime(appointment.starts_at)
            cuerpo = (
                f"Hola {appointment.patient.first_name}:\n\n"
                f"Tu ficha en {appointment.organization.name} quedó confirmada.\n\n"
                f"  Profesional: {appointment.practitioner.full_name}\n"
                f"  Sucursal:    {appointment.branch.name} {appointment.branch.address}\n"
                f"  Fecha:       {inicio:%d/%m/%Y a las %H:%M}\n\n"
                "Presentá el comprobante con QR de la aplicación en recepción. "
                "Si no tenés la app a mano, este es el código del comprobante:\n\n"
                f"  {issue_code(appointment)}\n\n"
                "Confirmá que vas a asistir con este enlace:\n\n"
                f"  {attendance_link(appointment)}\n"
            )
        send_mail(
            "Tu ficha está confirmada", cuerpo,
            settings.DEFAULT_FROM_EMAIL, [destino], fail_silently=False,
        )
        return True
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo enviar el aviso de la ficha %s", appointment_id)
        return False


@csrf_exempt
def attendance_link_view(request, token):
    """`GET/POST /appointments/attendance/{token}/` — el enlace del correo.

    GET muestra un botón y POST confirma: los clientes de correo y los
    antivirus abren los enlaces solos para revisarlos, y un GET que confirma
    asentaría confirmaciones que nadie dio.
    """
    try:
        datos = signing.loads(token, salt=LINK_SALT)
        appointment_id = uuid.UUID(datos["a"])
        organization_id = uuid.UUID(datos["o"])
    except (signing.BadSignature, KeyError, ValueError):
        return _pagina("Enlace inválido", "El enlace no es válido.", status=400)

    with tenant_context(organization_id):
        appointment = (
            Appointment.objects.select_related("practitioner", "branch")
            .filter(pk=appointment_id).first()
        )
        if appointment is None:
            return _pagina("Enlace inválido", "La ficha no existe.", status=404)
        inicio = timezone.localtime(appointment.starts_at)
        if request.method == "POST":
            ya_estaba = appointment.attendance_confirmed_at is not None
            try:
                confirm_attendance(appointment)
            except ValidationError as error:
                return _pagina("No se pudo confirmar", error.messages[0], status=400)
            if not ya_estaba:
                record(request, Action.APPOINTMENT_ATTENDANCE_CONFIRM, "appointment",
                       appointment.id, detail={"canal": "correo"},
                       organization=appointment.organization,
                       user=appointment.booked_by)
            return _pagina("¡Gracias!", f"Confirmaste tu asistencia del "
                                        f"{inicio:%d/%m/%Y a las %H:%M}.")
        if appointment.attendance_confirmed_at is not None:
            return _pagina("Asistencia confirmada", "Ya habías confirmado esta ficha.")
        return HttpResponse(format_html(
            _PLANTILLA, "Confirmar asistencia", format_html(
                "<h1>Confirmar asistencia</h1><p>{} · {}<br>{}</p>"
                '<form method="post"><button>Sí, voy a asistir</button></form>',
                appointment.practitioner.full_name, appointment.branch.name,
                f"{inicio:%d/%m/%Y a las %H:%M}",
            ),
        ))


_PLANTILLA = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f4f6f8;margin:0;padding:24px}}
main{{max-width:420px;margin:40px auto;background:#fff;border-radius:14px;padding:28px}}
button{{width:100%;padding:14px;border:0;border-radius:10px;background:#0f7b6c;color:#fff;
font-size:1rem}}</style></head><body><main>{}</main></body></html>"""


def _pagina(titulo, texto, status=200):
    return HttpResponse(
        format_html(_PLANTILLA, titulo, format_html("<h1>{}</h1><p>{}</p>", titulo, texto)),
        status=status,
    )
