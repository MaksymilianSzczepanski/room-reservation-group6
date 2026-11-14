from unittest.mock import patch

from django.test import SimpleTestCase

from microservices.common import token_for


class ReportAPITests(SimpleTestCase):
    @patch("microservices.reports.views.call")
    def test_counts_approved_reservations(self, remote):
        remote.side_effect = [[{"id": 1, "name": "A101"}],
                              [{"room_id": 1, "status": "approved"}, {"room_id": 1, "status": "pending"}]]
        token = token_for({"id": 1, "is_admin": True})
        result = self.client.get("/api/reports/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["approved_by_room"][0]["count"], 1)
