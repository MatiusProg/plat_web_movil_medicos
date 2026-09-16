"""Cómo se lee un registro de respaldo.

Sólo lectura, como la bitácora y por lo mismo: el registro de que alguien
restauró la organización no puede editarse después.
"""

from rest_framework import serializers

from . import manifest
from .models import BackupRecord


class BackupRecordSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.EmailField(
        source="performed_by.email", read_only=True, default=None,
    )
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    total_rows = serializers.IntegerField(read_only=True)
    detail = serializers.SerializerMethodField()

    class Meta:
        model = BackupRecord
        fields = [
            "id", "kind", "kind_label", "filename", "size_bytes",
            "total_rows", "detail", "checksum", "ip_address",
            "performed_by_email", "created_at",
        ]
        read_only_fields = fields

    def get_detail(self, record):
        """Las filas por tabla, con el nombre legible y sin las vacías.

        Las tablas en cero se omiten: un detalle de veinte líneas de las que
        catorce dicen «0» esconde las seis que importan.
        """
        conteos = record.row_counts or {}
        return [
            {"table": clave,
             "label": manifest.BY_KEY[clave].label if clave in manifest.BY_KEY
                      else clave,
             "rows": cantidad}
            for clave, cantidad in conteos.items()
            if isinstance(cantidad, int) and cantidad > 0
        ]
