"""Característica general 6 — La frecuencia de las copias, por plan.

Agrega ``backup_interval_hours`` a las funciones de cada plan del sistema:

    basic     168   una copia por semana
    pro        24   una copia por día
    premium   None  a voluntad

Sólo toca esa clave: el resto de ``features`` queda como esté, por si el
superadministrador ya cambió algo desde la pantalla de planes (US-44).
"""

from django.db import migrations

INTERVALS = {"basic": 168, "pro": 24, "premium": None}
KEY = "backup_interval_hours"


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    for plan in SubscriptionPlan.objects.filter(code__in=INTERVALS):
        features = dict(plan.features or {})
        features[KEY] = INTERVALS[plan.code]
        plan.features = features
        plan.save(update_fields=["features"])


def unseed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    for plan in SubscriptionPlan.objects.filter(code__in=INTERVALS):
        features = dict(plan.features or {})
        features.pop(KEY, None)
        plan.features = features
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0004_organization_cancellation_notice_hours"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
