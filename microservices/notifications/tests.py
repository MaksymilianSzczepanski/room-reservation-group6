import json
from unittest.mock import patch

from django.test import TestCase

from .models import Notification


class NotificationAPITests(TestCase):
    @patch("microservices.notifications.views.send_mail")
    @patch("microservices.notifications.views.call")
    def test_delivery_is_idempotent(self, remote, send):
        remote.side_effect = [[{"user_id": 5}], {"id": 5, "email": "guardian@example.test"},
                              [{"user_id": 5}], {"id": 5, "email": "guardian@example.test"}]
        data = {"kind": "created", "reservation": {
            "id": 1, "room_id": 2, "user_id": 3, "title": "Spotkanie",
            "start": "2026-10-19T09:00:00+02:00", "end": "2026-10-19T10:00:00+02:00", "status": "pending",
        }}
        for _ in range(2):
            result = self.client.post(
                "/api/notifications/internal/", json.dumps(data), content_type="application/json",
                HTTP_X_SERVICE_KEY="local-service-key",
            )
            self.assertEqual(result.status_code, 200)
        self.assertEqual(send.call_count, 1)
        self.assertEqual(Notification.objects.count(), 1)

    @patch("microservices.notifications.views.send_mail", side_effect=OSError("SMTP unavailable"))
    @patch("microservices.notifications.views.call", return_value={"id": 3, "email": "worker@example.test"})
    def test_failed_email_remains_visible(self, remote, send):
        data = {"kind": "decided", "reservation": {
            "id": 2, "room_id": 1, "user_id": 3, "title": "Spotkanie",
            "start": "2026-10-19T09:00:00+02:00", "end": "2026-10-19T10:00:00+02:00", "status": "approved",
        }}
        result = self.client.post(
            "/api/notifications/internal/", json.dumps(data), content_type="application/json",
            HTTP_X_SERVICE_KEY="local-service-key",
        )
        self.assertEqual(result.status_code, 503)
        self.assertEqual(Notification.objects.get().state, "failed")
