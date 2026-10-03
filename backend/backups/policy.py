"""Característica general 6 — Cada cuánto puede respaldar una organización.

La frecuencia depende del plan, y la declara el plan en sus funciones:
``features["backup_interval_hours"]``.

    Básico    168   una copia por semana
    Pro        24   una copia por día
    Premium   —     a voluntad (sin la clave, o en null)

Lo sembró ``tenancy/0005_backup_por_plan``; el superadministrador lo puede
cambiar editando el plan.

Tres decisiones:

- **Sólo se limita generar la copia, nunca restaurar.** Recuperarse de un
  desastre no puede depender de cuánto paga el cliente.
- **Se cuenta desde la última copia de la organización**, sea de quien sea:
  el límite es del centro médico, no de cada administrador. Si no, dos
  administradores duplican la cuota.
- **Sin plan vigente, no se respalda.** Una organización sin suscripción
  activa no tiene un contrato que diga cuánto le toca.
"""

import datetime as dt
from dataclasses import dataclass

from django.utils import timezone

from tenancy.plans import current_plan

from .models import BackupRecord

INTERVAL_KEY = "backup_interval_hours"


@dataclass(frozen=True)
class BackupPolicy:
    plan_code: str | None
    plan_name: str | None
    interval_hours: int | None      # None = sin límite
    last_backup_at: dt.datetime | None
    next_available_at: dt.datetime | None

    @property
    def allowed_now(self) -> bool:
        if self.plan_code is None:
            return False
        return self.next_available_at is None or self.next_available_at <= timezone.now()

    def describe(self) -> str:
        """La regla en una frase, para la pantalla y para el error."""
        if self.plan_code is None:
            return "La organización no tiene un plan vigente: no puede generar copias."
        if self.interval_hours is None:
            return f"Tu plan {self.plan_name} permite generar copias a voluntad."
        if self.interval_hours % 24 == 0 and self.interval_hours >= 24:
            dias = self.interval_hours // 24
            cada = {1: "por día", 7: "por semana"}.get(dias, f"cada {dias} días")
        else:
            cada = f"cada {self.interval_hours} horas"
        return f"Tu plan {self.plan_name} permite una copia {cada}."


def backup_policy(organization) -> BackupPolicy:
    plan = current_plan(organization)
    if plan is None:
        return BackupPolicy(None, None, None, None, None)

    intervalo = (plan.features or {}).get(INTERVAL_KEY)
    ultima = (
        BackupRecord.objects
        .filter(organization=organization, kind=BackupRecord.Kind.BACKUP)
        .order_by("-created_at")
        .values_list("created_at", flat=True)
        .first()
    )
    proxima = None
    if intervalo and ultima:
        proxima = ultima + dt.timedelta(hours=int(intervalo))
    return BackupPolicy(
        plan_code=plan.code, plan_name=plan.name,
        interval_hours=int(intervalo) if intervalo else None,
        last_backup_at=ultima, next_available_at=proxima,
    )
