import json
from unittest.mock import patch

from django.test import TestCase

from microservices.common import APIError, token_for
from .models import Decision
from .views import apply_record


class DecisionAPITests(TestCase):
    @patch("microservices.decisions.views.call")
    def test_guardian_approval(self, remote):
        remote.side_effect = [
            {"id": 10, "room_id": 2, "status": "pending"},
            {"assigned": True},
            {"id": 10, "status": "approved"},
        ]
        token = token_for({"id": 5, "is_admin": False})
        result = self.client.post(
            "/api/decisions/", json.dumps({"reservation_id": 10, "status": "approved"}),
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json()["reservation"]["status"], "approved")

    @patch("microservices.decisions.views.call")
    def test_remote_outage_keeps_decision_for_retry(self, remote):
        remote.side_effect = [
            {"id": 10, "room_id": 2, "status": "pending"},
            {"assigned": True},
            APIError("reservations unavailable", 503),
        ]
        token = token_for({"id": 5, "is_admin": False})
        result = self.client.post(
            "/api/decisions/", json.dumps({"reservation_id": 10, "status": "approved"}),
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(result.status_code, 202)
        item = Decision.objects.get()
        self.assertFalse(item.applied)
        remote.side_effect = None
        remote.return_value = {"id": 10, "status": "approved"}
        self.assertEqual(apply_record(item)["status"], "approved")
        item.refresh_from_db()
        self.assertTrue(item.applied)
