from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("appointments", "0006_seed_counter_booking_permission")]
    operations = [
        migrations.AddField(
            model_name="appointment", name="risk_reminder_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
