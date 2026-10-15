"""US-28 — Los avisos de la ficha: push y correo.

Tres eventos. Para cada uno sale un push a todos los teléfonos del
destinatario y un correo:

    confirmacion   se pagó la ficha       el correo es el de US-21: comprobante
                                          y enlace para confirmar asistencia
    recordatorio   unas horas antes       lo dispara `appointments/reminders.py`
    cancelacion    se canceló la ficha    dice si se devolvió el pago

El destinatario es el paciente o, si es un dependiente sin cuenta, su titular
(`appointments.attendance.recipient_user`, el mismo criterio que el correo).

`notify` corre después del COMMIT o desde el proceso de recordatorios, fuera
de una petición: abre su propio `tenant_context`. **Nunca propaga un error**:
un aviso caído no deshace un pago ni una cancelación (mismo criterio que
`send_confirmation_email`).
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from tenancy.context import tenant_context

from . import push

logger = logging.getLogger(__name__)

CONFIRMED = "confirmacion"
REMINDER = "recordatorio"
CANCELLED = "cancelacion"
EVENTS = (CONFIRMED, REMINDER, CANCELLED)


def notify(event: str, appointment_id, organization_id) -> None:
    """Avisa al paciente de [event] por push y por correo."""
    from appointments.attendance import send_confirmation_email

    if event not in EVENTS:
        raise ValueError(f"Evento desconocido: {event}")
    if event == CONFIRMED:
        # El correo de confirmación ya existía (US-21) y no se toca.
        send_confirmation_email(appointment_id, organization_id)

    correo = None
    try:
        with tenant_context(organization_id):
            appointment = _load(appointment_id)
            user = _recipient(appointment)
            if user is None:
                return
            titulo, cuerpo_push = _push_text(event, appointment)
            push.send_to_user(user, push.Message(
                titulo, cuerpo_push,
                data={"appointment_id": str(appointment.id), "event": event},
            ))
            if event != CONFIRMED:
                correo = (user.email, *_email(event, appointment))
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo avisar «%s» de la ficha %s", event, appointment_id)
        return

    if correo is None:
        return
    destino, asunto, cuerpo = correo
    try:
        send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [destino],
                  fail_silently=False)
    except Exception:  # noqa: BLE001
        logger.exception("No se pudo mandar el correo «%s» de la ficha %s",
                         event, appointment_id)


# ---------- Textos ----------------------------------------------------------

def _load(appointment_id):
    from appointments.models import Appointment

    return (
        Appointment.objects
        .select_related("organization", "patient__user", "patient__guardian__user",
                        "practitioner", "branch")
        .get(pk=appointment_id)
    )


def _recipient(appointment):
    from appointments.attendance import recipient_user

    return recipient_user(appointment)


def _cuando(appointment) -> str:
    inicio = timezone.localtime(appointment.starts_at)
    dias = (inicio.date() - timezone.localdate()).days
    dia = {0: "Hoy", 1: "Mañana"}.get(dias, f"El {inicio:%d/%m}")
    return f"{dia} a las {inicio:%H:%M}"


def _push_text(event: str, appointment) -> tuple[str, str]:
    inicio = timezone.localtime(appointment.starts_at)
    profesional = appointment.practitioner.full_name
    sucursal = appointment.branch.name
    if event == CONFIRMED:
        return ("Tu ficha quedó confirmada",
                f"{profesional} · {sucursal} · {inicio:%d/%m} a las {inicio:%H:%M}")
    if event == REMINDER:
        return ("Recordatorio de tu ficha",
                f"{_cuando(appointment)} con {profesional} en {sucursal}.")
    devolucion = _devolucion(appointment)
    return ("Tu ficha fue cancelada",
            f"La del {inicio:%d/%m} a las {inicio:%H:%M} con {profesional}."
            + (f" {devolucion}" if devolucion else ""))


def _datos(appointment) -> str:
    inicio = timezone.localtime(appointment.starts_at)
    return (
        f"  Profesional: {appointment.practitioner.full_name}\n"
        f"  Sucursal:    {appointment.branch.name} {appointment.branch.address}\n"
        f"  Fecha:       {inicio:%d/%m/%Y a las %H:%M}\n"
    )


def _email(event: str, appointment) -> tuple[str, str]:
    from appointments.attendance import attendance_link

    inicio = timezone.localtime(appointment.starts_at)
    saludo = f"Hola {appointment.patient.first_name}:\n\n"
    organizacion = appointment.organization
    if event == REMINDER:
        cuerpo = (
            saludo
            + f"Te recordamos tu ficha en {organizacion.name}.\n\n"
            + _datos(appointment) + "\n"
        )
        if appointment.attendance_confirmed_at is None:
            cuerpo += ("Confirmá que vas a asistir con este enlace:\n\n"
                       f"  {attendance_link(appointment)}\n\n")
        cuerpo += ("Si no podés ir, cancelala desde la aplicación para liberar "
                   "el turno.\n")
        return f"Recordatorio: tu ficha del {inicio:%d/%m}", cuerpo

    devolucion = _devolucion(appointment)
    cuerpo = (
        saludo
        + f"Tu ficha en {organizacion.name} fue cancelada.\n\n"
        + _datos(appointment)
        + (f"\n{devolucion}\n" if devolucion else "")
        + "\nPodés reservar otra desde la aplicación.\n"
    )
    return f"Tu ficha del {inicio:%d/%m} fue cancelada", cuerpo


def _devolucion(appointment) -> str:
    """Qué pasó con el pago: US-20 decide si corresponde y US-18 lo devuelve."""
    from payments.models import Payment

    pagos = Payment.objects.filter(appointment_id=appointment.id)
    devuelto = pagos.filter(status=Payment.Status.REFUNDED).first()
    if devuelto is not None:
        return f"Te devolvimos el pago de {devuelto.amount} {devuelto.currency}."
    if not pagos.filter(status=Payment.Status.SUCCEEDED).exists():
        return ""
    if appointment.refund_eligible:
        return "La devolución del pago está en trámite."
    horas = appointment.organization.cancellation_notice_hours
    return (f"Se canceló con menos de {horas} horas de anticipación: "
            "el pago no se devuelve.")
