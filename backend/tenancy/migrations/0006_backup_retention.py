"""Característica general 6 — Cuántas copias automáticas conserva cada plan.

Agrega ``backup_retention`` a las funciones de cada plan del sistema:

    basic       4   un mes de copias semanales
    pro         7   una semana de copias diarias
    premium    30   un mes de copias diarias

Como ``0005``, sólo toca esa clave.
"""

from django.db import migrations

RETENTION = {"basic": 4, "pro": 7, "premium": 30}
KEY = "backup_retention"


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    for plan in SubscriptionPlan.objects.filter(code__in=RETENTION):
        features = dict(plan.features or {})
        features[KEY] = RETENTION[plan.code]
        plan.features = features
        plan.save(update_fields=["features"])


def unseed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    for plan in SubscriptionPlan.objects.filter(code__in=RETENTION):
        features = dict(plan.features or {})
        features.pop(KEY, None)
        plan.features = features
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0005_backup_por_plan"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
