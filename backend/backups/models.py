"""Característica general 6 — El registro de lo que se respaldó y se restauró.

**Esta tabla no guarda el respaldo**; guarda que hubo uno. El porqué está en el
encabezado de ``services``: el archivo lleva en claro todo lo que el sistema
protege, y guardarlo dentro del sistema sería poner una copia sin RLS al lado
de la original.

Lo que sí hace falta registrar, y por dos razones distintas:

- **Operativa.** Quien administra tiene que poder contestar «¿cuándo fue el
  último respaldo?» sin buscar en su carpeta de descargas. Sin esta tabla, la
  respuesta depende de que alguien se acuerde.
- **De auditoría.** Una restauración reemplaza los datos de la organización. Es
  la operación más destructiva de la plataforma y tiene que quedar dicho quién
  la hizo, desde qué IP y de qué archivo venía. Eso además va a la bitácora de
  US-06; acá queda con el detalle por tabla, que en la bitácora sería un JSON
  gigante en la columna ``detail``.

**La excepción son las copias automáticas** (``StoredBackup``). Una copia que
genera el sistema sin que nadie la pida no tiene a quién descargarse: si no se
guarda, no existe. Se guarda **cifrada**, en una tabla aparte y con RLS, y sólo
las últimas que el plan conserva. El porqué de cada decisión está en
``automatic`` y en ``vault``.
"""

import uuid

from django.db import models


class BackupRecord(models.Model):
    """Un respaldo generado o una restauración ejecutada."""

    class Kind(models.TextChoices):
        BACKUP = "backup", "Copia de seguridad"
        RESTORE = "restore", "Restauración"

    class Trigger(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automática"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="backup_records",
    )
    kind = models.CharField(max_length=10, choices=Kind)
    # Quién la pidió: una persona (o la consola) o el programador de copias
    # automáticas. Importa para la cuota del plan, que limita sólo las
    # manuales: si las automáticas contaran, el Básico no podría generar
    # nunca una a mano, porque la semanal ya le habría gastado la cuota.
    trigger = models.CharField(max_length=10, choices=Trigger,
                               default=Trigger.MANUAL)
    # Quién lo hizo. SET_NULL y no CASCADE: si la cuenta se borra, el registro
    # de que alguien restauró la organización no puede desaparecer con ella.
    performed_by = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="backup_records",
    )
    # El nombre del archivo que se descargó o que se subió. Es lo que permite
    # cruzar este registro con el archivo que la persona tiene guardado.
    filename = models.CharField(max_length=200, blank=True, default="")
    # Tamaño en bytes y filas por tabla. `row_counts` es el detalle que la
    # bitácora no puede llevar.
    size_bytes = models.PositiveBigIntegerField(default=0)
    row_counts = models.JSONField(default=dict, blank=True)
    # El SHA-256 del contenido. En una restauración es el del archivo subido:
    # sirve para comprobar, meses después, que el archivo que alguien conserva
    # es el mismo que se restauró.
    checksum = models.CharField(max_length=64, blank=True, default="")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "backup_records"
        verbose_name = "registro de respaldo"
        verbose_name_plural = "registros de respaldo"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"],
                         name="ix_backup_records_org"),
        ]

    def __str__(self):
        return f"{self.get_kind_display()} · {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def total_rows(self) -> int:
        valores = (self.row_counts or {}).values()
        return sum(v for v in valores if isinstance(v, int))


class StoredBackup(models.Model):
    """El archivo de una copia automática, comprimido y cifrado.

    Tabla aparte y no una columna de ``BackupRecord`` por dos razones: listar
    el historial no tiene que leer megas de contenido, y al vencer la
    retención se borra el archivo sin borrar el registro de que existió.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.CASCADE,
        related_name="stored_backups",
    )
    record = models.OneToOneField(
        BackupRecord, on_delete=models.CASCADE, related_name="stored",
    )
    # gzip + Fernet (AES-128-CBC con HMAC-SHA256). Ver ``vault``.
    content = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "backup_files"
        verbose_name = "copia automática guardada"
        verbose_name_plural = "copias automáticas guardadas"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "-created_at"],
                         name="ix_backup_files_org"),
        ]

    def __str__(self):
        return f"Copia automática · {self.created_at:%Y-%m-%d %H:%M}"
