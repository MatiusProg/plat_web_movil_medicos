"""Pruebas de lógica US-37 sin necesidad de enviar mensajes reales."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from appointments.risk_reminders import _complete, _deliver_locked


class US37DeliveryTests(SimpleTestCase):
    def test_only_email_suffices_when_no_devices(self):
        app = SimpleNamespace(
            risk_reminder_email_accepted_at=object(),
            risk_reminder_push_accepted_at=None,
        )
        self.assertTrue(_complete(app, True, False))
        self.assertFalse(_complete(app, True, True))

    def test_two_channels_are_required_when_available(self):
        app = SimpleNamespace(
            risk_reminder_email_accepted_at=object(),
            risk_reminder_push_accepted_at=None,
        )
        self.assertFalse(_complete(app, True, True))
        app.risk_reminder_push_accepted_at = object()
        self.assertTrue(_complete(app, True, True))

    def test_no_recipient_does_not_mark_sent(self):
        app = MagicMock()
        with patch("notifications.services._recipient", return_value=None):
            self.assertFalse(_deliver_locked(app))
        app.save.assert_not_called()

    def test_partial_email_success_is_not_repeated_when_push_retries(self):
        app = MagicMock()
        app.id = "example-id"
        app.pk = "example-id"
        app.risk_reminder_email_accepted_at = None
        app.risk_reminder_push_accepted_at = None
        recipient = SimpleNamespace(email="patient@example.test")
        with (
            patch("notifications.services._recipient", return_value=recipient),
            patch("notifications.models.DeviceToken.objects") as tokens,
            patch("notifications.push.send_to_user", side_effect=[0, 1]) as push_send,
            patch("appointments.risk_reminders.send_mail", return_value=1) as mail_send,
            patch("notifications.services._push_text", return_value=("Titulo", "Texto")),
            patch("notifications.services._email", return_value=("Asunto", "Cuerpo")),
        ):
            tokens.filter.return_value.exists.return_value = True
            self.assertFalse(_deliver_locked(app))
            self.assertIsNotNone(app.risk_reminder_email_accepted_at)
            self.assertIsNone(app.risk_reminder_push_accepted_at)
            self.assertTrue(_deliver_locked(app))
            self.assertIsNotNone(app.risk_reminder_sent_at)
            self.assertEqual(mail_send.call_count, 1)
            self.assertEqual(push_send.call_count, 2)
