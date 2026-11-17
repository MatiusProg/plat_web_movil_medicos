from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("appointments", "0007_risk_reminder_sent_at"),
    ]
    operations = [
        migrations.AddField(
            model_name="appointment",
            name="risk_reminder_push_accepted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="risk_reminder_email_accepted_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
