"""Característica general 5 — La tabla de reportes guardados.

Sólo la tabla. El RLS, la clave foránea compuesta y los permisos van en
``0002_rls_and_permissions``, igual que en ``patients`` y ``scheduling``: la
migración que Django puede autogenerar se mantiene separada de la que hay que
escribir a mano, para que ``makemigrations`` nunca tenga que reconciliar las
dos.
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
            name="SavedReport",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=120)),
                ("description", models.CharField(blank=True, default="",
                                                 max_length=300)),
                ("dataset", models.CharField(max_length=40)),
                ("definition", models.JSONField(default=dict)),
                ("is_shared", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("organization", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="saved_reports", to="tenancy.organization")),
                ("owner", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="saved_reports",
                    to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "reporte guardado",
                "verbose_name_plural": "reportes guardados",
                "db_table": "saved_reports",
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="savedreport",
            index=models.Index(fields=["organization", "dataset"],
                               name="ix_saved_report_dataset"),
        ),
        migrations.AddConstraint(
            model_name="savedreport",
            constraint=models.UniqueConstraint(
                fields=("organization", "owner", "name"),
                name="uq_saved_report_name"),
        ),
    ]
