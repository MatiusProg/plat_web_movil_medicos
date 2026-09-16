"""Característica general 6 — La tabla del historial de respaldos.

Sólo la tabla. El RLS, la clave foránea compuesta y los permisos van en
``0002_rls_and_permissions``, por la misma razón que en ``reporting``: separar
lo que Django autogenera de lo que hay que escribir a mano.
"""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenancy", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BackupRecord",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ("kind", models.CharField(
                    choices=[("backup", "Copia de seguridad"),
                             ("restore", "Restauración")], max_length=10)),
                ("filename", models.CharField(blank=True, default="",
                                              max_length=200)),
                ("size_bytes", models.PositiveBigIntegerField(default=0)),
                ("row_counts", models.JSONField(blank=True, default=dict)),
                ("checksum", models.CharField(blank=True, default="",
                                              max_length=64)),
                ("ip_address", models.GenericIPAddressField(blank=True,
                                                            null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="backup_records", to="tenancy.organization")),
                ("performed_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="backup_records",
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "registro de respaldo",
                "verbose_name_plural": "registros de respaldo",
                "db_table": "backup_records",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="backuprecord",
            index=models.Index(fields=["organization", "-created_at"],
                               name="ix_backup_records_org"),
        ),
    ]
