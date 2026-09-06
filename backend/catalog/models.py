"""Catálogo médico: sucursales, especialidades y profesionales.

`Branch` viene del Sprint 0. El Sprint 1 le agrega el horario de atención y la
zona horaria, y suma `Specialty`, `Practitioner` y sus dos asociaciones muchos
a muchos —con especialidades y con sucursales—. La segunda es la que hace
posible la disponibilidad consolidada de US-15: un profesional que atiende en
tres sedes es un solo registro, no tres.

Las agendas (`Schedule`, `ScheduleBlock`) viven en la app `scheduling`.
"""

import unicodedata
import uuid

from django.db import models


def normalize_text(value: str) -> str:
    """Minúsculas y sin tildes, para buscar sin que el acento importe.

    El proyecto no tiene la extensión `unaccent` de PostgreSQL y `app_user` no
    puede instalarla, así que la normalización se hace en Python y se guarda en
    una columna aparte (`Practitioner.search_name`), sobre la que US-16 hace un
    `contains` común.
    """
    sin_tildes = (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return sin_tildes.lower().strip()


class Branch(models.Model):
    """US-11 — Sucursal de una organización."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="branches",
    )
    name = models.CharField(max_length=120)
    address = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    # La zona horaria de la sucursal, no la del servidor: el corte de "hora ya
    # pasada" de US-15 se calcula acá. `Organization` también tiene una; manda
    # la de la sucursal porque una organización podría tener sedes en husos
    # distintos.
    timezone = models.CharField(max_length=40, default="America/La_Paz")
    # Para ordenar por cercanía en la búsqueda del Sprint 2 (US-11 e). Por
    # ahora sólo se guardan.
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
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


class BranchHours(models.Model):
    """Horario de atención de una sucursal, por día de la semana.

    Varias filas por día para el corte de mediodía (US-11 a). Una agenda
    (US-13) no puede extenderse fuera de estas franjas. Si una sucursal no
    tiene ninguna fila cargada, la validación se omite: no se asume "cerrada".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="branch_hours",
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="hours",
    )
    # 0 = lunes … 6 = domingo (isoweekday - 1).
    weekday = models.PositiveSmallIntegerField()
    opens_at = models.TimeField()
    closes_at = models.TimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "branch_hours"
        verbose_name = "horario de sucursal"
        verbose_name_plural = "horarios de sucursal"
        ordering = ["branch_id", "weekday", "opens_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(weekday__gte=0) & models.Q(weekday__lte=6),
                name="ck_branch_hours_weekday",
            ),
            models.CheckConstraint(
                condition=models.Q(closes_at__gt=models.F("opens_at")),
                name="ck_branch_hours_order",
            ),
        ]

    def __str__(self):
        return f"{self.branch} · día {self.weekday} {self.opens_at}–{self.closes_at}"


class Specialty(models.Model):
    """US-12 — Especialidad médica del catálogo de la organización."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="specialties",
    )
    name = models.CharField(max_length=120)
    # No es decorativa: el chatbot del Sprint 4 la recupera por RAG (US-12 a).
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "specialties"
        verbose_name = "especialidad"
        verbose_name_plural = "especialidades"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uq_specialty_name",
            ),
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_specialty_id_org",
            ),
        ]

    def __str__(self):
        return self.name


class Practitioner(models.Model):
    """US-12 — Profesional del catálogo.

    Entidad aparte de `User`, igual que `Patient`: figura en el directorio,
    tiene especialidad y agenda, y puede existir en el catálogo antes de tener
    cuenta de acceso.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT,
        related_name="practitioners",
    )
    user = models.OneToOneField(
        "accounts.User", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="practitioner_profile",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    license_number = models.CharField(
        "matrícula", max_length=40, blank=True, default="",
    )
    # Nombre normalizado —minúsculas, sin tildes— para la búsqueda de US-16.
    search_name = models.CharField(max_length=170, editable=False, default="")
    is_active = models.BooleanField(default=True)
    specialties = models.ManyToManyField(
        Specialty, through="PractitionerSpecialty", related_name="practitioners",
    )
    branches = models.ManyToManyField(
        Branch, through="PractitionerBranch", related_name="practitioners",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "practitioners"
        verbose_name = "profesional"
        verbose_name_plural = "profesionales"
        ordering = ["last_name", "first_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["id", "organization"], name="uq_practitioner_id_org",
            ),
            models.UniqueConstraint(
                fields=["organization", "license_number"],
                condition=~models.Q(license_number=""),
                name="uq_practitioner_license",
            ),
        ]

    def __str__(self):
        return self.full_name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        self.search_name = normalize_text(f"{self.first_name} {self.last_name}")
        super().save(*args, **kwargs)


class PractitionerSpecialty(models.Model):
    """Asociación profesional ↔ especialidad (US-12 c)."""

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="practitioner_specialties",
    )
    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.CASCADE, related_name="specialty_links",
    )
    specialty = models.ForeignKey(
        Specialty, on_delete=models.CASCADE, related_name="practitioner_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "practitioner_specialties"
        verbose_name = "especialidad de profesional"
        verbose_name_plural = "especialidades de profesional"
        ordering = ["practitioner_id", "specialty_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["practitioner", "specialty"],
                name="uq_practitioner_specialty",
            ),
        ]


class PractitionerBranch(models.Model):
    """Asociación profesional ↔ sucursal (US-12 d).

    Es la que hace posible la disponibilidad consolidada de US-15.
    """

    id = models.BigAutoField(primary_key=True)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="practitioner_branches",
    )
    practitioner = models.ForeignKey(
        Practitioner, on_delete=models.CASCADE, related_name="branch_links",
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.CASCADE, related_name="practitioner_links",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "practitioner_branches"
        verbose_name = "sucursal de profesional"
        verbose_name_plural = "sucursales de profesional"
        ordering = ["practitioner_id", "branch_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["practitioner", "branch"],
                name="uq_practitioner_branch",
            ),
        ]
