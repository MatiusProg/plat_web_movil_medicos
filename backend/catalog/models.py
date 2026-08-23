"""Catálogo médico.

En el Sprint 0 sólo existe Branch, y mínima: la historia que le corresponde es
US-11, del Sprint 1. Está acá porque ``User.branch`` la necesita y crearla
después obligaría a migrar usuarios ya cargados.

El Sprint 1 agrega a este módulo: Specialty, Practitioner,
PractitionerSpecialty, PractitionerBranch, Schedule y ScheduleBlock. Y le suma
a Branch el horario de atención.
"""

import uuid

from django.db import models


class Branch(models.Model):
    """US-11 (Sprint 1) — Sucursal de una organización."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="branches",
    )
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "branches"
        verbose_name = "sucursal"
        verbose_name_plural = "sucursales"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uq_branch_name",
            ),
            # La necesita la clave foránea compuesta desde users, que impide
            # asignarle a un usuario una sucursal de otra organización.
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_branch_id_org",
            ),
        ]

    def __str__(self):
        return self.name
