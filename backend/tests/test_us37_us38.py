"""US-37 / US-38: contrato básico; las pruebas de integración requieren PostgreSQL RLS."""
import datetime as dt

from django.test import SimpleTestCase
from unittest.mock import patch

from appointments.risk_reminders import due
from reporting.demand import band
from notifications.services import RISK_REMINDER, EVENTS


class NewFeatureContractTests(SimpleTestCase):
    def test_risk_event_is_supported(self):
        self.assertIn(RISK_REMINDER, EVENTS)

    def test_time_bands(self):
        self.assertEqual(band(8), "manana")
        self.assertEqual(band(12), "tarde")
        self.assertEqual(band(18), "noche")

    def test_risk_due_filters_only_active_high_risk_and_unsent(self):
        with patch("appointments.risk_reminders.Appointment.objects") as manager:
            manager.filter.return_value = "query"
            self.assertEqual(due(dt.datetime(2026, 11, 16, tzinfo=dt.timezone.utc)), "query")
            kwargs = manager.filter.call_args.kwargs
            self.assertEqual(kwargs["noshow_prediction__level"], "high")
            self.assertEqual(kwargs["noshow_prediction__model_version__status"], "active")
            self.assertTrue(kwargs["reminder_sent_at__isnull"] is False)
            self.assertTrue(kwargs["risk_reminder_sent_at__isnull"])
            self.assertTrue(kwargs["attendance_confirmed_at__isnull"])

    def test_second_reminder_is_neutral_about_risk(self):
        from unittest.mock import MagicMock
        from notifications.services import _push_text
        app = MagicMock()
        app.starts_at = dt.datetime(2026, 11, 18, 16, tzinfo=dt.timezone.utc)
        app.practitioner.full_name = "Dra. Ejemplo"
        app.branch.name = "Central"
        title, message = _push_text(RISK_REMINDER, app)
        self.assertIn("confirma", title.lower())
        self.assertNotIn("riesgo", (title + message).lower())
