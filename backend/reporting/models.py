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
