"""``GET /api/platform/my-panel/`` — el panel de inicio, según quién entra.

Cada bloque aparece sólo si el rol lo puede ver, con el mismo criterio que
el resto de la API (permisos y alcance). No es un resumen genérico: es lo que
cada persona necesita al empezar el día.

    plan        administración: uso del plan contra sus topes (tenancy/plans.py)
    hoy         recepción y administración: las fichas de hoy del centro
    asistencia  recepción y administración: atendidas, ausentes y canceladas
                de los últimos 30 días (el dato del modelo de inasistencia)
    mi_agenda   médico: sus fichas de hoy y sus atenciones sin firmar
    mis_fichas  paciente: sus próximas fichas y las de sus dependientes

El superadministrador no usa esto: tiene su propio panel (``dashboard/``).
"""

import datetime as dt
from zoneinfo import ZoneInfo

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from appointments.models import Appointment
from catalog.models import Branch, Practitioner

from ..plans import (
    ai_queries_this_month,
    appointments_this_month,
    current_plan,
    is_staff_member,
    staff_count,
)

# Estados que todavía cuentan como "en pie" para mostrar en el día.
EN_PIE = ["pending_payment", "confirmed", "attended", "no_show"]


def _ficha(ficha, con_paciente=True):
    tz = ZoneInfo(ficha.branch.timezone or "America/La_Paz")
    datos = {
        "id": str(ficha.id),
        "starts_at": ficha.starts_at,
        "hora": ficha.starts_at.astimezone(tz).strftime("%H:%M"),
        "status": ficha.status,
        "status_display": ficha.get_status_display(),
        "branch": ficha.branch.name,
        "practitioner": ficha.practitioner.full_name,
    }
    if con_paciente:
        datos["patient"] = ficha.patient.full_name
    return datos


def _rango_de_hoy(organizacion):
    tz = ZoneInfo(organizacion.timezone or "America/La_Paz")
    hoy = timezone.now().astimezone(tz).date()
    desde = dt.datetime.combine(hoy, dt.time.min, tzinfo=tz)
    return hoy, desde, desde + dt.timedelta(days=1)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def mi_panel(request):
    usuario = request.user
    organizacion = getattr(usuario, "organization", None)
    if organizacion is None:
        return Response({"plataforma": True})

    hoy, desde, hasta = _rango_de_hoy(organizacion)
    datos = {"fecha": hoy.isoformat(), "organizacion": organizacion.name}
    es_personal = is_staff_member(organizacion, usuario)

    # Qué incluye el plan, para todos: la pantalla no ofrece lo que no hay.
    plan_vigente = current_plan(organizacion)
    datos["incluye"] = {
        "asistente": bool(plan_vigente and plan_vigente.allows("ai_chatbot")),
        "exportar_reportes": bool(plan_vigente and plan_vigente.allows("report_export")),
    }

    # ---- Administración: el plan y cuánto se usa de él -------------------
    if usuario.has_permission("users.user.read"):
        plan = current_plan(organizacion)
        if plan is not None:
            uso = [
                ("Sucursales activas", Branch.objects.filter(organization=organizacion, is_active=True).count(), plan.max_branches),
                ("Personal", staff_count(organizacion), plan.max_users),
                ("Profesionales activos", Practitioner.objects.filter(organization=organizacion, is_active=True).count(), plan.max_practitioners),
                ("Fichas este mes", appointments_this_month(organizacion), plan.max_appointments_month),
            ]
            if plan.allows("ai_chatbot"):
                uso.append(("Consultas al asistente este mes", ai_queries_this_month(organizacion), plan.max_ai_queries_month))
            datos["plan"] = {
                "code": plan.code,
                "name": plan.name,
                "uso": [{"etiqueta": e, "usados": u, "tope": t} for e, u, t in uso],
                "incluye": {
                    "asistente": plan.allows("ai_chatbot"),
                    "exportar_reportes": plan.allows("report_export"),
                },
            }

    # ---- Recepción y administración: el día del centro --------------------
    if es_personal and usuario.has_permission("appointments.appointment.read"):
        del_dia = (
            Appointment.objects
            .filter(organization=organizacion, starts_at__gte=desde, starts_at__lt=hasta)
            .select_related("patient", "practitioner", "branch")
            .order_by("starts_at")
        )
        conteo = del_dia.aggregate(
            total=Count("id", filter=Q(status__in=EN_PIE)),
            atendidas=Count("id", filter=Q(status="attended")),
            por_atender=Count("id", filter=Q(status__in=["pending_payment", "confirmed"])),
            canceladas=Count("id", filter=Q(status="cancelled")),
        )
        ahora = timezone.now()
        proximas = [f for f in del_dia if f.starts_at >= ahora and f.status in ("pending_payment", "confirmed")][:8]
        datos["hoy"] = {**conteo, "proximas": [_ficha(f) for f in proximas]}

        hace_30 = ahora - dt.timedelta(days=30)
        datos["asistencia"] = Appointment.objects.filter(
            organization=organizacion, starts_at__gte=hace_30, starts_at__lt=ahora,
        ).aggregate(
            atendidas=Count("id", filter=Q(status="attended")),
            ausentes=Count("id", filter=Q(status="no_show")),
            canceladas=Count("id", filter=Q(status="cancelled")),
        )

    # ---- Médico: su agenda del día ----------------------------------------
    profesional = Practitioner.objects.filter(user=usuario, is_active=True).first()
    if profesional is not None and usuario.has_permission("encounters.encounter.read"):
        from encounters.models import Encounter

        suyas = (
            Appointment.objects
            .filter(organization=organizacion, practitioner=profesional,
                    starts_at__gte=desde, starts_at__lt=hasta, status__in=EN_PIE)
            .select_related("patient", "practitioner", "branch", "encounter")
            .order_by("starts_at")
        )
        filas = []
        for ficha in suyas:
            fila = _ficha(ficha)
            encuentro = getattr(ficha, "encounter", None)
            fila["encounter"] = (
                {"id": str(encuentro.id), "status": encuentro.status} if encuentro else None
            )
            filas.append(fila)
        datos["mi_agenda"] = {
            "fichas": filas,
            "sin_firmar": Encounter.objects.filter(
                organization=organizacion, practitioner=profesional, status="draft",
            ).count(),
        }

    # ---- Paciente: sus próximas fichas ------------------------------------
    paciente = getattr(usuario, "patient_profile", None)
    if paciente is not None and not es_personal:
        proximas = (
            Appointment.objects
            .filter(organization=organizacion, starts_at__gte=timezone.now(),
                    status__in=["pending_payment", "confirmed"])
            .filter(Q(patient=paciente) | Q(patient__guardian=paciente))
            .select_related("patient", "practitioner", "branch")
            .order_by("starts_at")[:3]
        )
        # "Para …" sólo cuando la ficha es de un dependiente: en la propia
        # sobra decirle a la persona su nombre.
        datos["mis_fichas"] = [_ficha(f, con_paciente=f.patient_id != paciente.id) for f in proximas]

    return Response(datos)
