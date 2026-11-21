"""Característica general 5 — Los reportes que el usuario se guarda.

Sin esta tabla la característica queda a medias: se podrían generar reportes a
medida, pero habría que rearmar el mismo a mano cada lunes. Lo que la consigna
pide —«mecanismos que permitan al usuario construir sus propios reportes»— sólo
sirve si lo construido se conserva.

**La definición va en un ``JSONField`` y no en tablas normalizadas.** Una tabla
de columnas elegidas y otra de criterios serían tres tablas, tres políticas RLS
y tres claves foráneas compuestas para guardar algo que nunca se consulta por
partes: el reporte se lee entero o no se lee. Lo que sí hay que sostener es que
**la definición guardada puede quedar obsoleta** —alguien saca una columna del
catálogo de ``datasets.py``— y por eso se vuelve a validar en cada ejecución,
no al guardar.
"""

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SavedReport(models.Model):
    """Un reporte que alguien armó y quiere volver a correr.

    ``owner`` es quien lo creó. ``is_shared`` lo pone a disposición del resto
    de la organización: el caso real es el administrador que arma «pacientes
    dados de alta este mes» y quiere que recepción lo corra sin rearmarlo.

    **Compartir no presta permisos.** Al ejecutarlo se vuelve a exigir el
    permiso del conjunto de datos contra quien lo corre, no contra quien lo
    guardó. Si no fuera así, un reporte compartido sería la forma de regalar
    acceso a la bitácora sin pasar por la pantalla de roles.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="saved_reports",
    )
    # Si se borra la cuenta que lo creó, el reporte compartido sobrevive sin
    # dueño en lugar de desaparecer de la lista de todos los demás.
    owner = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="saved_reports",
    )
    name = models.CharField(max_length=120)
    description = models.CharField(max_length=300, blank=True, default="")
    # El código del conjunto en `datasets.REGISTRY`. Se guarda desnormalizado
    # además de estar dentro de `definition` para poder listar «mis reportes de
    # pacientes» sin abrir el JSON de cada fila.
    dataset = models.CharField(max_length=40)
    definition = models.JSONField(default=dict)
    is_shared = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_reports"
        verbose_name = "reporte guardado"
        verbose_name_plural = "reportes guardados"
        ordering = ["name"]
        constraints = [
            # Por dueño y no por organización: dos personas pueden tener cada
            # una su «Pacientes del mes» sin pisarse.
            models.UniqueConstraint(
                fields=["organization", "owner", "name"],
                name="uq_saved_report_name",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "dataset"],
                         name="ix_saved_report_dataset"),
        ]

    def __str__(self):
        return self.name


class Expense(models.Model):
    """US-50 — Un gasto de la organización o de una sucursal.

    Es el dato que la contabilidad no puede sacar de los pagos: el alquiler, los
    insumos, los sueldos. Se carga a mano, con una categoría cerrada, y entra a
    la utilidad. ``branch`` vacío es un gasto **general** del centro (no de una
    sede en particular).

    Un gasto no se mezcla entre monedas: lleva la suya, y la contabilidad suma
    por moneda.
    """

    class Category(models.TextChoices):
        SUPPLIES = "insumos", "Insumos"
        RENT = "alquiler", "Alquiler"
        PAYROLL = "sueldos", "Sueldos"
        UTILITIES = "servicios", "Servicios"
        OTHER = "otros", "Otros"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="expenses",
    )
    branch = models.ForeignKey(
        "catalog.Branch", on_delete=models.PROTECT, null=True, blank=True,
        related_name="expenses",
    )
    category = models.CharField(max_length=12, choices=Category.choices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    spent_on = models.DateField()
    note = models.CharField(max_length=200, blank=True, default="")
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="expenses_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "expenses"
        verbose_name = "gasto"
        verbose_name_plural = "gastos"
        ordering = ["-spent_on", "-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0), name="ck_expense_amount",
            ),
        ]
        indexes = [
            models.Index(fields=["organization", "spent_on"],
                         name="ix_expense_org_date"),
        ]

    def __str__(self):
        return f"{self.category} · {self.amount} {self.currency}"


class FinanceSettings(models.Model):
    """US-50 — Cuánto cobra cada pasarela, por organización.

    ``stripe_percent`` es el porcentaje que se queda la pasarela de los pagos en
    línea (Stripe y el simulado); el efectivo en ventanilla no tiene comisión.
    Una fila por organización, creada al primer uso.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="finance_settings",
    )
    stripe_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "finance_settings"
        verbose_name = "ajustes de finanzas"
        verbose_name_plural = "ajustes de finanzas"
