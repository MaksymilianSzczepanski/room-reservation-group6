import json
from unittest.mock import patch

from django.test import TestCase

from microservices.common import token_for


class RoomAPITests(TestCase):
    def setUp(self):
        self.token = token_for({"id": 1, "is_admin": True})
        self.headers = {"HTTP_AUTHORIZATION": f"Bearer {self.token}"}

    def test_create_and_filter_rooms(self):
        created = self.client.post(
            "/api/rooms/", json.dumps({"name": "A101", "building": "A", "capacity": 30}),
            content_type="application/json", **self.headers,
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(len(self.client.get("/api/rooms/?building__icontains=A&capacity__gte=20").json()), 1)
        self.assertEqual(self.client.get("/api/rooms/?capacity__gte=40").json(), [])

    def test_write_requires_admin(self):
        response = self.client.post("/api/rooms/", json.dumps({"name": "A101"}), content_type="application/json")
        self.assertEqual(response.status_code, 401)

    @patch("microservices.rooms.views.call")
    def test_used_room_cannot_be_deleted(self, remote):
        created = self.client.post(
            "/api/rooms/", json.dumps({"name": "A101"}),
            content_type="application/json", **self.headers,
        ).json()
        remote.side_effect = [{"used": True}, []]
        result = self.client.delete(f"/api/rooms/{created['id']}/", **self.headers)
        self.assertEqual(result.status_code, 409)
        self.assertEqual(len(self.client.get("/api/rooms/").json()), 1)
