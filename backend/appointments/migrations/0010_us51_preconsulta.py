"""US-51: preconsulta por ficha y tenant, con RLS y FK compuesta."""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("appointments", "0009_waitlist_rls_y_claves_compuestas")]

    operations = [
        migrations.CreateModel(
            name="AppointmentPreconsultation",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("reason", models.TextField(blank=True, default="")),
                ("questions", models.TextField(blank=True, default="")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("appointment", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT,
                    related_name="preconsultation", to="appointments.appointment")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,
                    related_name="appointment_preconsultations", to="tenancy.organization")),
            ],
            options={"db_table": "appointment_preconsultations"},
        ),
        migrations.AddConstraint(
            model_name="appointmentpreconsultation",
            constraint=models.UniqueConstraint(fields=("appointment", "organization"),
                name="uq_preconsult_appointment_org"),
        ),
        migrations.RunSQL(
            """
            ALTER TABLE appointment_preconsultations ENABLE ROW LEVEL SECURITY;
            ALTER TABLE appointment_preconsultations FORCE ROW LEVEL SECURITY;
            CREATE POLICY tenant_isolation ON appointment_preconsultations
              USING (organization_id = app_current_tenant())
              WITH CHECK (organization_id = app_current_tenant());
            ALTER TABLE appointment_preconsultations ADD CONSTRAINT fk_preconsult_appointment_org
              FOREIGN KEY (appointment_id, organization_id)
              REFERENCES appointments (id, organization_id) ON DELETE RESTRICT;
            """,
            """
            ALTER TABLE appointment_preconsultations DROP CONSTRAINT IF EXISTS fk_preconsult_appointment_org;
            DROP POLICY IF EXISTS tenant_isolation ON appointment_preconsultations;
            ALTER TABLE appointment_preconsultations NO FORCE ROW LEVEL SECURITY;
            ALTER TABLE appointment_preconsultations DISABLE ROW LEVEL SECURITY;
            """,
        ),
    ]
