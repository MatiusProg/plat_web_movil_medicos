from django.db import migrations, models


class Migration(migrations.Migration):
    """US-36 — la marca del segundo recordatorio (fichas con riesgo alto).

    Sólo agrega una columna nula: no cambia RLS ni políticas, la tabla
    `appointments` ya las tiene (0002).
    """

    dependencies = [
        ('appointments', '0006_seed_counter_booking_permission'),
    ]

    operations = [
        migrations.AddField(
            model_name='appointment',
            name='reinforced_reminder_sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
