"""US-51 — «Agregar a mi calendario» y «Cómo llegar» de una ficha pagada.

El `.ics` lleva la fecha y la hora con `TZID=America/La_Paz` (Bolivia no tiene
horario de verano: UTC−4 todo el año), la sede con su dirección y un aviso 24 h
antes. Lo abren Google Calendar, Outlook y el calendario del teléfono.

Sólo para fichas **confirmadas** (pagadas): una pendiente de pago puede vencer,
y una cancelada no es una cita.
"""

from urllib.parse import quote

from django.http import Http404, HttpResponse
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .mixins import owns_appointment
from .models import Appointment
from .permissions import CanReadAppointments

ZONA = "America/La_Paz"


def maps_url(branch):
    """El enlace de «Cómo llegar», o `None` si la sede no tiene coordenadas."""
    if branch.latitude is None or branch.longitude is None:
        return None
    return f"https://www.google.com/maps/search/?api=1&query={branch.latitude},{branch.longitude}"


def _texto(valor: str) -> str:
    # RFC 5545: se escapan la barra, la coma, el punto y coma y los saltos.
    return (valor.replace("\\", "\\\\").replace(",", "\\,")
            .replace(";", "\\;").replace("\n", "\\n"))


def _plegar(linea: str) -> str:
    # RFC 5545: líneas de hasta 75 octetos; las que siguen empiezan con espacio.
    if len(linea.encode("utf-8")) <= 75:
        return linea
    partes, actual = [], ""
    for caracter in linea:
        limite = 75 if not partes else 74
        if len((actual + caracter).encode("utf-8")) > limite:
            partes.append(actual)
            actual = ""
        actual += caracter
    partes.append(actual)
    return "\r\n ".join(partes)


def build_ics(appointment) -> str:
    inicio = timezone.localtime(appointment.starts_at)
    fin = timezone.localtime(appointment.ends_at)
    sede = appointment.branch
    lugar = f"{sede.name}, {sede.address}" if sede.address else sede.name
    descripcion = (
        f"Ficha con {appointment.practitioner.full_name} en "
        f"{appointment.organization.name}.\n"
        "Lleva tu identificación y el comprobante con QR de la aplicación."
    )
    mapa = maps_url(sede)
    if mapa:
        descripcion += f"\nCómo llegar: {mapa}"
    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Centro Medico//Fichas//ES",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VTIMEZONE",
        f"TZID:{ZONA}",
        "BEGIN:STANDARD",
        "DTSTART:19700101T000000",
        "TZOFFSETFROM:-0400",
        "TZOFFSETTO:-0400",
        "TZNAME:BOT",
        "END:STANDARD",
        "END:VTIMEZONE",
        "BEGIN:VEVENT",
        f"UID:{appointment.id}@centromedico",
        f"DTSTAMP:{timezone.now():%Y%m%dT%H%M%SZ}",
        f"DTSTART;TZID={ZONA}:{inicio:%Y%m%dT%H%M%S}",
        f"DTEND;TZID={ZONA}:{fin:%Y%m%dT%H%M%S}",
        f"SUMMARY:{_texto('Ficha con ' + appointment.practitioner.full_name)}",
        f"LOCATION:{_texto(lugar)}",
        f"DESCRIPTION:{_texto(descripcion)}",
    ]
    if sede.latitude is not None and sede.longitude is not None:
        lineas.append(f"GEO:{sede.latitude};{sede.longitude}")
    lineas += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_texto('Mañana tienes ficha con ' + appointment.practitioner.full_name)}",
        "TRIGGER:-PT24H",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(_plegar(linea) for linea in lineas) + "\r\n"


def ics_filename(appointment) -> str:
    inicio = timezone.localtime(appointment.starts_at)
    return f"ficha-{inicio:%Y-%m-%d-%H%M}.ics"


class CalendarView(APIView):
    """`GET /appointments/appointments/<id>/calendar.ics` — del titular o su tutor."""

    permission_classes = [IsAuthenticated, CanReadAppointments]

    def get(self, request, pk):
        ficha = (Appointment.objects
                 .select_related("patient", "practitioner", "branch", "organization")
                 .filter(pk=pk, organization=request.user.organization).first())
        # Ajena o no pagada: 404, sin decir cuál de las dos.
        if (ficha is None or not owns_appointment(request.user, ficha)
                or ficha.status != Appointment.Status.CONFIRMED):
            raise Http404
        respuesta = HttpResponse(build_ics(ficha), content_type="text/calendar; charset=utf-8")
        nombre = ics_filename(ficha)
        respuesta["Content-Disposition"] = (
            f"attachment; filename=\"{nombre}\"; filename*=UTF-8''{quote(nombre)}")
        return respuesta
