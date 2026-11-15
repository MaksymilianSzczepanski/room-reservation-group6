import json
from unittest.mock import patch

from django.test import TestCase

from microservices.common import token_for


class GuardianAPITests(TestCase):
    def test_mine_requires_login_and_cannot_read_another_guardian(self):
        from .models import Assignment
        Assignment.objects.create(user_id=1, room_id=2)
        Assignment.objects.create(user_id=3, room_id=4)
        self.assertEqual(self.client.get("/api/guardians/mine/").status_code, 401)
        token = token_for({"id": 1, "is_admin": False})
        result = self.client.get("/api/guardians/mine/?user_id=3",
                                 HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual([row["room_id"] for row in result.json()], [2])
        self.assertEqual(self.client.get("/api/guardians/",
                         HTTP_AUTHORIZATION=f"Bearer {token}").status_code, 403)

    @patch("microservices.guardians.views.call", return_value={"id": 1})
    def test_assignment_and_internal_check(self, remote):
        token = token_for({"id": 1, "is_admin": True})
        created = self.client.post(
            "/api/guardians/", json.dumps({"user_id": 1, "room_id": 2}),
            content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertEqual(created.status_code, 201)
        checked = self.client.get(
            "/api/guardians/internal/check/?user_id=1&room_id=2",
            HTTP_X_SERVICE_KEY="local-service-key",
        )
        self.assertEqual(checked.json(), {"assigned": True})
        self.assertEqual(remote.call_count, 2)

    def test_internal_assignments_for_user_require_service_key(self):
        from .models import Assignment
        Assignment.objects.create(user_id=5, room_id=3)
        Assignment.objects.create(user_id=5, room_id=1)
        Assignment.objects.create(user_id=6, room_id=2)
        self.assertEqual(self.client.get("/api/guardians/internal/user/5/").status_code, 403)
        result = self.client.get("/api/guardians/internal/user/5/", HTTP_X_SERVICE_KEY="local-service-key")
        self.assertEqual([row["room_id"] for row in result.json()], [1, 3])
