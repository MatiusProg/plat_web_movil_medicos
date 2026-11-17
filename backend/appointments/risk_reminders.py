"""US-37: segundo recordatorio para fichas con predicción de riesgo ALTO.

Se apoya en US-35 sin modificarlo y utiliza el texto neutral del evento de
notificaciones existente. Lleva control independiente de aceptación por canal.
Una aceptación FCM no demuestra lectura del mensaje por el paciente.
"""

import datetime as dt
import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization
from tenancy.plans import current_plan
from noshow.models import NoShowPrediction, ModelVersion
from .models import Appointment

logger = logging.getLogger(__name__)


def due(now=None):
    now = now or timezone.now()
    hours = int(getattr(settings, "APPOINTMENT_RISK_REMINDER_HOURS", 3))
    if hours < 1:
        return Appointment.objects.none()
    return Appointment.objects.filter(
        status=Appointment.Status.CONFIRMED,
        attendance_confirmed_at__isnull=True,
        reminder_sent_at__isnull=False,
        risk_reminder_sent_at__isnull=True,
        starts_at__gt=now,
        starts_at__lte=now + dt.timedelta(hours=hours),
        created_at__lte=F("starts_at") - dt.timedelta(hours=hours),
        noshow_prediction__level=NoShowPrediction.Level.HIGH,
        noshow_prediction__model_version__status=ModelVersion.Status.ACTIVE,
    )


def _complete(ficha, has_email: bool, has_devices: bool) -> bool:
    """Los canales disponibles deben haber aceptado su aviso al menos una vez."""
    return (
        (has_email or has_devices)
        and (not has_email or ficha.risk_reminder_email_accepted_at is not None)
        and (not has_devices or ficha.risk_reminder_push_accepted_at is not None)
    )


def _deliver_locked(ficha):
    """Entrega específica US-37, llamada con ficha bloqueada y tenant activo.

    No modifica `notifications.notify` ni los eventos de US-28. El estado
    de cada canal sólo avanza si el proveedor acepta el envío.
    """
    from notifications import push
    from notifications.models import DeviceToken
    from notifications.services import RISK_REMINDER, _recipient, _push_text, _email

    user = _recipient(ficha)
    if user is None:
        logger.warning("US-37: ficha %s sin destinatario", ficha.pk)
        return False

    has_email = bool(user.email)
    has_devices = DeviceToken.objects.filter(user=user).exists()

    if has_devices and ficha.risk_reminder_push_accepted_at is None:
        try:
            title, body = _push_text(RISK_REMINDER, ficha)
            count = push.send_to_user(
                user,
                push.Message(
                    title=title,
                    body=body,
                    data={"appointment_id": str(ficha.id), "event": RISK_REMINDER},
                ),
            )
            if count > 0:
                ficha.risk_reminder_push_accepted_at = timezone.now()
                ficha.save(update_fields=["risk_reminder_push_accepted_at", "updated_at"])
        except Exception:
            logger.exception("US-37: fallo del push de ficha %s", ficha.pk)

    if has_email and ficha.risk_reminder_email_accepted_at is None:
        try:
            subject, body = _email(RISK_REMINDER, ficha)
            count = send_mail(
                subject, body, settings.DEFAULT_FROM_EMAIL, [user.email],
                fail_silently=False,
            )
            if count > 0:
                ficha.risk_reminder_email_accepted_at = timezone.now()
                ficha.save(update_fields=["risk_reminder_email_accepted_at", "updated_at"])
        except Exception:
            logger.exception("US-37: fallo del correo de ficha %s", ficha.pk)

    if _complete(ficha, has_email, has_devices):
        ficha.risk_reminder_sent_at = timezone.now()
        ficha.save(update_fields=["risk_reminder_sent_at", "updated_at"])
        return True
    return False


def run_for(organization, now=None):
    plan = current_plan(organization)
    if plan is None or not plan.allows("noshow_prediction"):
        return 0
    now = now or timezone.now()
    with tenant_context(organization.id):
        ids = list(due(now).filter(organization=organization).values_list("pk", flat=True))

    completed = 0
    for pk in ids:
        try:
            # tenant_context abre una transacción; dejamos atomic explícito
            # para hacer evidente la protección del lock y de los updates.
            with tenant_context(organization.id):
                with transaction.atomic():
                    ficha = (
                        due(now)
                        .filter(organization=organization, pk=pk)
                        .select_for_update(skip_locked=True)
                        .select_related(
                            "organization", "patient__user", "patient__guardian__user",
                            "practitioner", "branch",
                        )
                        .first()
                    )
                    if ficha is None:
                        continue
                    if _deliver_locked(ficha):
                        completed += 1
        except Exception:
            logger.exception("US-37: error organización=%s ficha=%s", organization.slug, pk)
    return completed


def run_due(now=None):
    with platform_admin_context():
        organizations = list(Organization.objects.filter(status=Organization.Status.ACTIVE))
    total = 0
    for organization in organizations:
        try:
            total += run_for(organization, now)
        except Exception:
            logger.exception("US-37: error en organización %s", organization.slug)
    return total
