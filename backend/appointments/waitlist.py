"""US-52 — Lista de espera con aviso de cupo liberado.

Cómo funciona, de punta a punta:

1. El paciente no encuentra turno y se **anota** (`join`) con el rango de
   fechas que le sirve, por un profesional o por una especialidad.
2. Alguien **cancela** una ficha (o la reprograma, que libera el turno viejo):
   `offer_freed_slot` busca al primero de la fila que encaje y le **guarda el
   turno 15 minutos**. El turno guardado es una ficha `pending_payment` real,
   a su nombre, con `expires_at` a `APPOINTMENT_HOLD_MINUTES`. Por eso no hay
   carrera: el índice único `uq_appointment_active_slot` deja que sólo una
   ficha activa ocupe el turno, sea cual sea el orden en que lleguen.
3. Se le **avisa** por push y correo (`notifications.services.CUPO_LIBERADO`).
   Al tocar el aviso la app abre esa ficha, donde ya está el botón de pagar.
4. Si **no la paga**, la reserva vence (`holds.release_expired_holds`) y el
   proceso `process_waitlist` ofrece el turno al siguiente.
5. Si la paga, la entrada queda `booked`.

El **orden** es el de llegada (`created_at`). El **alcance** es la
organización: toda consulta lleva `organization` además de RLS, y el aviso
nunca menciona a otro paciente.

Nada de esto debe tumbar una cancelación: `offer_freed_slot` no propaga
errores (se anotan), igual que los avisos de `notifications.services`.
"""

from __future__ import annotations

import datetime as dt
import logging
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Exists, Max, Min, OuterRef, Q
from django.utils import timezone

from catalog.models import Branch, Practitioner, Specialty
from patients.models import Patient
from scheduling.availability import consolidated_availability
from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization
from tenancy.plans import (
    PlanLimitExceeded, appointments_this_month, check_limit, current_plan,
)

from . import kpis
from .booking import SlotAlreadyTaken, book_appointment
from .holds import release_expired_holds
from .models import Appointment, WaitlistEntry

logger = logging.getLogger(__name__)

FEATURE = "waitlist"
FEATURE_TEXT = "la lista de espera"


def has_feature(organization) -> bool:
    plan = current_plan(organization)
    return plan is not None and plan.allows(FEATURE)


def _error(mensaje, codigo):
    return ValidationError(mensaje, code=codigo)


def _hoy(organization) -> dt.date:
    """La fecha de hoy en la zona de la organización (como el panel de KPIs)."""
    zona = ZoneInfo(organization.timezone or "America/La_Paz")
    return timezone.now().astimezone(zona).date()


# ==========================================================================
#  Anotarse y salir
# ==========================================================================
def join(
    *, organization, user, patient_id, practitioner_id=None, specialty_id=None,
    branch_id=None, date_from, date_to, today=None,
) -> WaitlistEntry:
    """Anota a un paciente. Lanza `ValidationError` con un código de la API.

    `patient_id` tiene que ser el del propio usuario o el de un dependiente
    suyo. Se pide **un** destino —profesional o especialidad— y no se acepta
    si hoy ya hay un turno libre que le sirva: en ese caso lo que corresponde
    es reservarlo.
    """
    perfil = getattr(user, "patient_profile", None)
    if perfil is None:
        raise _error("Sólo un paciente puede anotarse en la lista de espera.",
                     "no_es_paciente")

    paciente = (
        Patient.objects.filter(pk=patient_id, organization=organization,
                               is_active=True)
        .filter(Q(pk=perfil.pk) | Q(guardian_id=perfil.pk))
        .first()
    )
    if paciente is None:
        raise _error("El paciente no existe o no es tuyo.", "paciente_invalido")

    if bool(practitioner_id) == bool(specialty_id):
        raise _error("Elige un profesional o una especialidad, no las dos ni ninguna.",
                     "destino_invalido")

    profesional = especialidad = None
    if practitioner_id:
        profesional = Practitioner.objects.filter(
            pk=practitioner_id, organization=organization, is_active=True,
        ).first()
        if profesional is None:
            raise _error("El profesional no existe o está inactivo.",
                         "profesional_invalido")
    else:
        especialidad = Specialty.objects.filter(
            pk=specialty_id, organization=organization, is_active=True,
        ).first()
        if especialidad is None:
            raise _error("La especialidad no existe.", "especialidad_invalida")

    sucursal = None
    if branch_id:
        sucursal = Branch.objects.filter(
            pk=branch_id, organization=organization, is_active=True,
        ).first()
        if sucursal is None:
            raise _error("La sucursal no existe o está inactiva.",
                         "sucursal_invalida")

    hoy = today or _hoy(organization)
    if date_from < hoy:
        raise _error("El rango no puede empezar en el pasado.", "rango_pasado")
    if date_to < date_from:
        raise _error("El rango de fechas está invertido.", "rango_invalido")
    tope = settings.AVAILABILITY_MAX_HORIZON_DAYS
    if (date_to - date_from).days > tope:
        raise _error(f"El rango no puede superar {tope} días.", "rango_largo")

    if _hay_turno_libre(profesional, especialidad, sucursal, date_from, date_to):
        raise _error(
            "Ya hay turnos libres en esas fechas: reserva uno en vez de anotarte.",
            "hay_turnos",
        )

    try:
        with transaction.atomic():
            return WaitlistEntry.objects.create(
                organization=organization, patient=paciente, requested_by=user,
                practitioner=profesional, specialty=especialidad,
                branch=sucursal, date_from=date_from, date_to=date_to,
            )
    except IntegrityError as error:
        if "uq_waitlist_live" in str(error):
            raise _error("Ya estás anotado para eso.", "ya_anotado") from error
        raise


def _hay_turno_libre(profesional, especialidad, sucursal, desde, hasta) -> bool:
    """Si en el rango queda un espacio reservable con ese profesional o
    con alguno de la especialidad."""
    if profesional is not None:
        profesionales = [profesional]
    else:
        profesionales = list(Practitioner.objects.filter(
            organization_id=especialidad.organization_id, is_active=True,
            specialties=especialidad,
        ))
    for prof in profesionales:
        datos = consolidated_availability(
            practitioner_id=prof.id, date_from=desde, date_to=hasta,
            branch_id=sucursal.id if sucursal else None,
        )
        if any(espacio["reservable"] for dia in datos["days"]
               for espacio in dia["slots"]):
            return True
    return False


def leave(entry: WaitlistEntry):
    """Sale de la lista. Idempotente; una entrada ya cerrada no cambia.

    Si ya se le había guardado un turno, **se lo suelta**: la reserva pasa a
    `expired` y el turno queda libre para el siguiente. Devuelve la ficha
    soltada —para que quien llama se lo ofrezca a otro después del COMMIT— o
    `None`. Si el turno ya estaba pagado, la entrada queda `booked`: salir de
    la lista no cancela una ficha confirmada.
    """
    if entry.status not in WaitlistEntry.LIVE_STATUSES:
        return None
    Estado = WaitlistEntry.Status
    soltada = None
    if entry.status == Estado.OFFERED and entry.offered_appointment_id:
        ficha = Appointment.objects.select_for_update().get(
            pk=entry.offered_appointment_id)
        if ficha.status == Appointment.Status.PENDING_PAYMENT:
            ficha.status = Appointment.Status.EXPIRED
            ficha.save(update_fields=["status", "updated_at"])
            soltada = ficha
        elif ficha.status in (Appointment.Status.CONFIRMED,
                              Appointment.Status.ATTENDED):
            entry.status = Estado.BOOKED
            entry.save(update_fields=["status", "updated_at"])
            return None
    entry.status = Estado.CANCELLED
    entry.save(update_fields=["status", "updated_at"])
    return soltada


def position(entry: WaitlistEntry) -> int | None:
    """Su lugar en la fila de quienes esperan lo mismo: 1 es el primero.

    `None` si ya no está esperando (se le ofreció un turno o se cerró).
    """
    if entry.status != WaitlistEntry.Status.WAITING:
        return None
    mismos = WaitlistEntry.objects.filter(
        organization_id=entry.organization_id,
        status=WaitlistEntry.Status.WAITING,
    )
    if entry.practitioner_id:
        mismos = mismos.filter(practitioner_id=entry.practitioner_id)
    else:
        mismos = mismos.filter(specialty_id=entry.specialty_id,
                               practitioner__isnull=True)
    delante = mismos.filter(
        Q(created_at__lt=entry.created_at)
        | Q(created_at=entry.created_at, id__lt=entry.id)
    ).count()
    return delante + 1


# ==========================================================================
#  Ofrecer el turno liberado
# ==========================================================================
def _candidatos(ficha: Appointment):
    """Las entradas que esperan este turno, en orden de llegada."""
    zona = ZoneInfo(ficha.branch.timezone or "America/La_Paz")
    dia = ficha.starts_at.astimezone(zona).date()
    especialidades = list(
        ficha.practitioner.specialties.values_list("id", flat=True),
    )
    return (
        WaitlistEntry.objects
        .filter(organization_id=ficha.organization_id,
                status=WaitlistEntry.Status.WAITING,
                date_from__lte=dia, date_to__gte=dia)
        .filter(Q(practitioner_id=ficha.practitioner_id)
                | Q(practitioner__isnull=True, specialty_id__in=especialidades))
        .filter(Q(branch__isnull=True) | Q(branch_id=ficha.branch_id))
        .exclude(patient_id=ficha.patient_id)
        .exclude(patient_id__in=_quienes_lo_soltaron(ficha))
        .order_by("created_at", "id")
    )


def _quienes_lo_soltaron(ficha: Appointment):
    """Los pacientes que tuvieron este mismo turno y lo cancelaron, lo
    reprogramaron o lo dejaron vencer: no se les vuelve a ofrecer."""
    return Appointment.objects.filter(
        organization_id=ficha.organization_id, schedule_id=ficha.schedule_id,
        starts_at=ficha.starts_at,
        status__in=[Appointment.Status.CANCELLED, Appointment.Status.RESCHEDULED,
                    Appointment.Status.EXPIRED],
    ).values("patient_id")


def _ocupado_a_esa_hora(entry: WaitlistEntry, ficha: Appointment) -> bool:
    """El paciente ya tiene otra ficha activa que se pisa con este turno."""
    return Appointment.objects.filter(
        patient_id=entry.patient_id, status__in=Appointment.ACTIVE_STATUSES,
        starts_at__lt=ficha.ends_at, ends_at__gt=ficha.starts_at,
    ).exists()


def offer_slot(ficha: Appointment, *, now=None):
    """Le guarda el turno de [ficha] —ya libre— al primero que encaje.

    Supone el contexto de la organización. Devuelve `(entrada, ficha_nueva)`
    o `None` si nadie lo toma. Se salta a quien no puede recibirlo (ya está
    ocupado a esa hora, su paciente se desactivó) y sigue con el siguiente.
    """
    now = now or timezone.now()
    if ficha.starts_at <= now:
        return None
    organizacion = ficha.organization
    try:
        check_limit(organizacion, "max_appointments_month",
                    appointments_this_month(organizacion),
                    "fichas por mes", "ficha por mes")
    except PlanLimitExceeded:
        logger.info("Sin cupo de fichas del mes: no se ofrece el turno de «%s».",
                    organizacion.slug)
        return None

    for candidata in list(_candidatos(ficha)):
        with transaction.atomic():
            entrada = (
                WaitlistEntry.objects.select_for_update()
                .filter(pk=candidata.pk, status=WaitlistEntry.Status.WAITING)
                .first()
            )
            if entrada is None or _ocupado_a_esa_hora(entrada, ficha):
                continue
            try:
                nueva = book_appointment(
                    organization=organizacion,
                    patient_id=entrada.patient_id,
                    practitioner_id=ficha.practitioner_id,
                    branch_id=ficha.branch_id,
                    schedule_id=ficha.schedule_id,
                    starts_at=ficha.starts_at,
                    booked_by=entrada.requested_by,
                )
            except SlotAlreadyTaken:
                # Alguien lo reservó antes: el turno ya no está libre.
                return None
            except ValidationError:
                continue
            entrada.status = WaitlistEntry.Status.OFFERED
            entrada.offered_appointment = nueva
            entrada.offered_at = now
            entrada.save(update_fields=[
                "status", "offered_appointment", "offered_at", "updated_at",
            ])
            return entrada, nueva
    return None


def offer_freed_slot(appointment_id, organization_id) -> bool:
    """El gancho de la cancelación: ofrece el turno y avisa. Nunca propaga.

    Corre después del COMMIT de la cancelación o desde el proceso, fuera de
    una petición: abre su propio contexto de organización. Devuelve si se
    ofreció a alguien.
    """
    try:
        with tenant_context(organization_id):
            ficha = (
                Appointment.objects
                .select_related("organization", "practitioner", "branch")
                .get(pk=appointment_id)
            )
            if not has_feature(ficha.organization):
                return False
            resultado = offer_slot(ficha)
        if resultado is None:
            return False
        _entrada, nueva = resultado
    except Exception:  # noqa: BLE001 - la cancelación no se deshace por esto
        logger.exception("No se pudo ofrecer el turno liberado de la ficha %s",
                         appointment_id)
        return False

    from notifications.services import CUPO_LIBERADO, notify

    notify(CUPO_LIBERADO, nueva.id, organization_id)
    return True


# ==========================================================================
#  Mantener las entradas al día
# ==========================================================================
def refresh_entries(*, organization=None, today=None) -> int:
    """Cierra las entradas que ya no esperan. Supone el contexto de la
    organización. Devuelve cuántas cambiaron.

    - `offered` cuya ficha se pagó → `booked`; si se canceló → `cancelled`;
      si venció → `expired`.
    - `waiting` cuyo rango terminó → `expired`.
    - `waiting` cuyo paciente ya **pagó** por su cuenta un turno que le servía
      → `booked`: la entrada se cierra sola. Una reserva pendiente de pago no
      alcanza: si la abandona, sigue esperando.
    """
    hoy = today or (_hoy(organization) if organization is not None
                    else timezone.localdate())
    cambiadas = 0
    Estado = WaitlistEntry.Status

    for entrada in WaitlistEntry.objects.filter(
        status=Estado.OFFERED,
    ).select_related("offered_appointment"):
        ficha = entrada.offered_appointment
        if ficha is None or ficha.status == Appointment.Status.PENDING_PAYMENT:
            continue
        if ficha.status in (Appointment.Status.CONFIRMED,
                            Appointment.Status.ATTENDED,
                            Appointment.Status.NO_SHOW):
            nuevo = Estado.BOOKED
        elif ficha.status == Appointment.Status.CANCELLED:
            nuevo = Estado.CANCELLED
        else:
            nuevo = Estado.EXPIRED
        entrada.status = nuevo
        entrada.save(update_fields=["status", "updated_at"])
        cambiadas += 1

    cambiadas += WaitlistEntry.objects.filter(
        status=Estado.WAITING, date_to__lt=hoy,
    ).update(status=Estado.EXPIRED, updated_at=timezone.now())

    for entrada in WaitlistEntry.objects.filter(
        status=Estado.WAITING,
    ).select_related("organization"):
        if _ya_reservo(entrada):
            entrada.status = Estado.BOOKED
            entrada.save(update_fields=["status", "updated_at"])
            cambiadas += 1
    return cambiadas


def _ya_reservo(entrada: WaitlistEntry) -> bool:
    """El paciente tiene una ficha pagada que cumple lo que pidió."""
    inicio, _ = kpis.rango_utc(entrada.organization, entrada.date_from,
                               entrada.date_from)
    _, fin = kpis.rango_utc(entrada.organization, entrada.date_to, entrada.date_to)
    fichas = Appointment.objects.filter(
        patient_id=entrada.patient_id,
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.ATTENDED],
        starts_at__gte=inicio, starts_at__lt=fin,
        created_at__gte=entrada.created_at,
    )
    if entrada.branch_id:
        fichas = fichas.filter(branch_id=entrada.branch_id)
    if entrada.practitioner_id:
        fichas = fichas.filter(practitioner_id=entrada.practitioner_id)
    else:
        fichas = fichas.filter(practitioner__specialties=entrada.specialty_id)
    return fichas.exists()


def _turnos_libres_que_alguien_espera(organization, now) -> list:
    """Una ficha por cada turno futuro que quedó libre (cancelado, reprogramado
    o vencido, sin otra ficha activa encima) dentro de los días que algún
    paciente espera. Supone el contexto de la organización.

    Es lo que vuelve a la lista **a prueba de fallas**: no depende de haber
    visto la cancelación. Si la oferta falló —el proceso se cayó, la base
    parpadeó— el turno sigue libre y la vuelta siguiente lo reintenta.
    """
    esperando = WaitlistEntry.objects.filter(status=WaitlistEntry.Status.WAITING)
    rango = esperando.aggregate(desde=Min("date_from"), hasta=Max("date_to"))
    if rango["desde"] is None:
        return []
    inicio, _ = kpis.rango_utc(organization, rango["desde"], rango["desde"])
    _, fin = kpis.rango_utc(organization, rango["hasta"], rango["hasta"])
    ocupado = Appointment.objects.filter(
        schedule_id=OuterRef("schedule_id"), starts_at=OuterRef("starts_at"),
        status__in=Appointment.ACTIVE_STATUSES,
    )
    sueltas = (
        Appointment.objects
        .filter(organization=organization,
                status__in=[Appointment.Status.CANCELLED,
                            Appointment.Status.RESCHEDULED,
                            Appointment.Status.EXPIRED],
                starts_at__gt=now, starts_at__gte=inicio, starts_at__lt=fin)
        .exclude(Exists(ocupado))
        .order_by("starts_at", "-updated_at")
    )
    por_turno = {}
    for ficha in sueltas:
        por_turno.setdefault((ficha.schedule_id, ficha.starts_at), ficha)
    return list(por_turno.values())


def run_organization(organization, *, now=None) -> dict:
    """Una vuelta para una organización: libera reservas vencidas, ofrece los
    turnos libres que alguien espera y pone al día las entradas."""
    now = now or timezone.now()
    ofrecidas = 0
    with tenant_context(organization.id):
        liberadas = release_expired_holds(now=now, include_offers=True)
        refresh_entries(organization=organization)
        pendientes = _turnos_libres_que_alguien_espera(organization, now)
    for ficha in pendientes:
        if offer_freed_slot(ficha.id, organization.id):
            ofrecidas += 1
    with tenant_context(organization.id):
        refresh_entries(organization=organization)
    return {"liberadas": len(liberadas), "ofrecidas": ofrecidas}


def eligible_organizations() -> list[Organization]:
    """Organizaciones activas cuyo plan incluye la lista de espera."""
    with platform_admin_context():
        organizaciones = list(
            Organization.objects.filter(status=Organization.Status.ACTIVE),
        )
    return [o for o in organizaciones if has_feature(o)]


def run_due(now=None) -> dict:
    """Una vuelta de todas las organizaciones habilitadas. Una que falla no
    frena a las demás."""
    total = {"liberadas": 0, "ofrecidas": 0}
    for organizacion in eligible_organizations():
        try:
            parcial = run_organization(organizacion, now=now)
        except Exception:  # noqa: BLE001 - una organización no frena al resto
            logger.exception("Falló la lista de espera de «%s».", organizacion.slug)
            continue
        for clave, valor in parcial.items():
            total[clave] += valor
    return total


# ==========================================================================
#  Resumen para la administración
# ==========================================================================
def summary(organization, desde: dt.date, hasta: dt.date) -> dict:
    """Anotados, cuántos tomaron el turno y la tasa de recuperación.

    **Tasa de recuperación** = de las fichas que se cancelaron en el período
    (con el turno todavía por delante), cuántas volvieron a ocuparse: otra
    ficha `confirmed`, `attended` o `no_show` sobre el mismo `(agenda, hora)`,
    creada después de la cancelación. Se calcula sólo con las fichas, así que
    vale también para lo que se llenó sin pasar por la lista.
    """
    inicio, fin = kpis.rango_utc(organization, desde, hasta)
    Estado = WaitlistEntry.Status

    entradas = WaitlistEntry.objects.filter(
        organization=organization, created_at__gte=inicio, created_at__lt=fin,
    )
    por_estado = dict(entradas.values_list("status").annotate(n=Count("id")))
    anotados = sum(por_estado.values())
    tomaron = por_estado.get(Estado.BOOKED, 0)

    por_medico = [
        {"practitioner": str(fila["practitioner_id"]),
         "name": f'{fila["practitioner__first_name"]} {fila["practitioner__last_name"]}',
         "enrolled": fila["n"], "booked": fila["tomaron"]}
        for fila in entradas.filter(practitioner__isnull=False)
        .values("practitioner_id", "practitioner__first_name",
                "practitioner__last_name")
        .annotate(n=Count("id"),
                  tomaron=Count("id", filter=Q(status=Estado.BOOKED)))
        .order_by("-n", "practitioner__last_name", "practitioner__first_name")
    ]
    por_especialidad = [
        {"specialty": str(fila["specialty_id"]),
         "name": fila["specialty__name"],
         "enrolled": fila["n"], "booked": fila["tomaron"]}
        for fila in entradas.filter(practitioner__isnull=True)
        .values("specialty_id", "specialty__name")
        .annotate(n=Count("id"),
                  tomaron=Count("id", filter=Q(status=Estado.BOOKED)))
        .order_by("-n", "specialty__name")
    ]

    ocupa_de_nuevo = Appointment.objects.filter(
        organization=organization,
        schedule_id=OuterRef("schedule_id"), starts_at=OuterRef("starts_at"),
        status__in=[Appointment.Status.CONFIRMED, Appointment.Status.ATTENDED,
                    Appointment.Status.NO_SHOW],
        created_at__gt=OuterRef("cancelled_at"),
    )
    # `cancel_appointment` sólo deja cancelar un turno que todavía no pasó.
    canceladas = Appointment.objects.filter(
        organization=organization, status=Appointment.Status.CANCELLED,
        cancelled_at__gte=inicio, cancelled_at__lt=fin,
    )
    total = canceladas.count()
    recuperadas = canceladas.filter(Exists(ocupa_de_nuevo)).count()

    return {
        "range": {"from": desde.isoformat(), "to": hasta.isoformat()},
        "waitlist": {
            "enrolled": anotados,
            "booked": tomaron,
            "waiting": por_estado.get(Estado.WAITING, 0),
            "offered": por_estado.get(Estado.OFFERED, 0),
            "expired": por_estado.get(Estado.EXPIRED, 0),
            "cancelled": por_estado.get(Estado.CANCELLED, 0),
            "by_practitioner": por_medico,
            "by_specialty": por_especialidad,
        },
        "recovery": {
            "cancelled": total,
            "recovered": recuperadas,
            "rate": round(recuperadas / total, 4) if total else None,
        },
    }
