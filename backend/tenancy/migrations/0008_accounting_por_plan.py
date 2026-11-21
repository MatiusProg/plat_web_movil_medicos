"""US-50 — La contabilidad es de los planes Pro y Premium.

Agrega ``accounting`` a las funciones de cada plan del sistema:

    basic     False
    pro       True
    premium   True

Sólo toca esa clave: el resto de ``features`` queda como esté, por si el
superadministrador ya cambió algo desde la pantalla de planes (US-44).
"""

from django.db import migrations

VALUES = {"basic": False, "pro": True, "premium": True}
KEY = "accounting"


def seed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    for plan in SubscriptionPlan.objects.filter(code__in=VALUES):
        features = dict(plan.features or {})
        features[KEY] = VALUES[plan.code]
        plan.features = features
        plan.save(update_fields=["features"])


def unseed(apps, schema_editor):
    SubscriptionPlan = apps.get_model("tenancy", "SubscriptionPlan")
    schema_editor.execute("SELECT set_config('app.is_platform_admin', 'on', true)")
    for plan in SubscriptionPlan.objects.filter(code__in=VALUES):
        features = dict(plan.features or {})
        features.pop(KEY, None)
        plan.features = features
        plan.save(update_fields=["features"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenancy", "0007_waitlist_por_plan"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
