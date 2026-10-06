"""Característica general 6 — Las copias automáticas.

El sistema respalda a cada organización activa sin que nadie lo pida, con la
misma frecuencia que su plan permite para las manuales:

    Básico    una por semana     conserva las últimas 4
    Pro       una por día        conserva las últimas 7
    Premium   una por día        conserva las últimas 30

La frecuencia sale de ``backup_interval_hours`` (el Premium, que a mano no
tiene límite, se respalda solo una vez por día) y cuántas se conservan, de
``backup_retention``. Las dos son funciones del plan: el superadministrador
las cambia editando el plan.

Cuatro decisiones:

- **Se guardan, y cifradas.** Ver ``vault``. Las manuales se siguen
  descargando y no se guardan: quien la pidió ya la tiene.
- **Sólo se conservan las últimas N.** Al vencer, se borra el archivo y queda
  el registro en el historial («ya no se conserva»): el historial no miente
  sobre lo que hubo.
- **Las automáticas no gastan la cuota de las manuales.** Ver ``policy``.
- **Es idempotente.** ``run_due`` se puede llamar cada cinco minutos o cada
  hora: sólo respalda a quien le toca, y un candado de PostgreSQL impide que
  dos procesos —el contenedor viejo y el nuevo durante un despliegue—
  respalden dos veces a la misma organización.
"""

import datetime as dt
import json
import logging
import zlib
from dataclasses import dataclass

from django.db import connection, transaction
from django.utils import timezone

from tenancy.context import platform_admin_context, tenant_context
from tenancy.models import Organization
from tenancy.plans import current_plan

from . import services, vault
from .models import BackupRecord, StoredBackup
from .policy import INTERVAL_KEY

logger = logging.getLogger(__name__)

RETENTION_KEY = "backup_retention"
# Si el plan no dice nada: una por día y las últimas siete.
DEFAULT_INTERVAL_HOURS = 24
DEFAULT_RETENTION = 7
# Margen para que una copia que «vence» a las 03:00:20 la tome la vuelta de
# las 03:00 y no la siguiente: sin esto, la hora de la copia se corre un
# intervalo del programador cada día.
SLACK = dt.timedelta(minutes=10)


@dataclass(frozen=True)
class AutomaticSchedule:
    interval_hours: int | None   # None = la organización no tiene plan
    retention: int
    last_at: dt.datetime | None
    next_at: dt.datetime | None

    @property
    def enabled(self) -> bool:
        return self.interval_hours is not None

    def describe(self) -> str:
        if not self.enabled:
            return "Sin un plan vigente no se generan copias automáticas."
        if self.interval_hours % 24 == 0:
            dias = self.interval_hours // 24
            cada = {1: "una por día", 7: "una por semana"}.get(
                dias, f"una cada {dias} días")
        else:
            cada = f"una cada {self.interval_hours} horas"
        return (f"El sistema genera {cada} sola y conserva las últimas "
                f"{self.retention}.")


def schedule(organization) -> AutomaticSchedule:
    plan = current_plan(organization)
    if plan is None:
        return AutomaticSchedule(None, 0, None, None)
    features = plan.features or {}
    intervalo = int(features.get(INTERVAL_KEY) or DEFAULT_INTERVAL_HOURS)
    retencion = int(features.get(RETENTION_KEY) or DEFAULT_RETENTION)
    with tenant_context(organization.id):
        ultima = (
            BackupRecord.objects
            .filter(organization=organization, kind=BackupRecord.Kind.BACKUP,
                    trigger=BackupRecord.Trigger.AUTOMATIC)
            .order_by("-created_at")
            .values_list("created_at", flat=True)
            .first()
        )
    proxima = ultima + dt.timedelta(hours=intervalo) if ultima else None
    return AutomaticSchedule(intervalo, retencion, ultima, proxima)


def is_due(plan_schedule: AutomaticSchedule, now=None) -> bool:
    if not plan_schedule.enabled:
        return False
    if plan_schedule.next_at is None:
        return True
    return plan_schedule.next_at - SLACK <= (now or timezone.now())


def run_for(organization) -> BackupRecord | None:
    """Genera la copia automática de una organización si le toca.

    Devuelve el registro, o ``None`` si no le tocaba o la tomó otro proceso.
    """
    with transaction.atomic():
        # Candado por organización, que se suelta solo al terminar la
        # transacción. `try`: si lo tiene otro proceso, éste sigue de largo.
        clave = zlib.crc32(f"backup:{organization.id}".encode()) & 0x7FFFFFFF
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", [clave])
            if not cursor.fetchone()[0]:
                return None

        # Se vuelve a preguntar con el candado tomado: otro proceso pudo haber
        # terminado la copia entre la consulta de afuera y ésta.
        plan_schedule = schedule(organization)
        if not is_due(plan_schedule):
            return None

        documento = services.create(organization)
        contenido = services.to_bytes(documento)
        with tenant_context(organization.id):
            record = BackupRecord.objects.create(
                organization=organization,
                kind=BackupRecord.Kind.BACKUP,
                trigger=BackupRecord.Trigger.AUTOMATIC,
                performed_by=None,
                filename=services.filename(organization,
                                           documento["generated_at"]),
                size_bytes=len(contenido),
                row_counts=documento["counts"],
                checksum=documento["checksum"],
            )
            StoredBackup.objects.create(
                organization=organization, record=record,
                content=vault.seal(contenido),
            )
            prune(organization, plan_schedule.retention)
    return record


def prune(organization, retention: int) -> int:
    """Borra los archivos que pasan la retención. El registro queda."""
    with tenant_context(organization.id):
        conservar = list(
            StoredBackup.objects
            .filter(organization=organization)
            .order_by("-created_at")
            .values_list("pk", flat=True)[:max(retention, 1)]
        )
        borradas, _ = (
            StoredBackup.objects
            .filter(organization=organization)
            .exclude(pk__in=conservar)
            .delete()
        )
    return borradas


def run_due() -> list[BackupRecord]:
    """Respaldar a todas las organizaciones activas a las que les toca.

    Una que falla no frena a las demás: se anota y se sigue. La que falló
    vuelve a intentarse en la vuelta siguiente, porque sigue «debiendo» copia.
    """
    with platform_admin_context():
        organizaciones = list(
            Organization.objects.filter(status=Organization.Status.ACTIVE)
        )

    hechas = []
    for organization in organizaciones:
        try:
            record = run_for(organization)
        except Exception:  # noqa: BLE001 - una organización no frena al resto
            logger.exception("Falló la copia automática de «%s».",
                             organization.slug)
            continue
        if record is not None:
            logger.info("Copia automática de «%s»: %s (%d bytes).",
                        organization.slug, record.filename, record.size_bytes)
            hechas.append(record)
    return hechas


def read(record: BackupRecord) -> dict:
    """El documento de una copia guardada, descifrado.

    Es lo que usan la descarga y la restauración desde el historial.
    """
    stored = StoredBackup.objects.filter(record=record).first()
    if stored is None:
        raise services.BackupError(
            "copia_no_disponible",
            "Esta copia ya no se conserva: pasó la cantidad que guarda el plan.",
        )
    try:
        contenido = vault.open_sealed(stored.content)
    except vault.VaultError as error:
        raise services.BackupError("copia_ilegible", str(error)) from error
    return json.loads(contenido.decode("utf-8"))
