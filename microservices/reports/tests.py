from unittest.mock import patch

from django.test import SimpleTestCase

from microservices.common import token_for

ROOMS = [{"id": 1, "name": "A101", "building": "A", "capacity": 20},
         {"id": 2, "name": "B202", "building": "B", "capacity": 40}]


def remote_for(reservations, assignments):
    def remote(service, path, *args, **kwargs):
        if service == "rooms":
            return ROOMS
        if service == "guardians":
            return assignments
        if service == "reservations":
            remote.reservation_paths.append(path)
            return reservations
        raise AssertionError(service)
    remote.reservation_paths = []
    return remote


class ReportAPITests(SimpleTestCase):
    @patch("microservices.reports.views.call")
    def test_counts_approved_reservations(self, remote):
        remote.side_effect = [[{"id": 1, "name": "A101"}],
                              [{"room_id": 1, "status": "approved"}, {"room_id": 1, "status": "pending"}]]
        token = token_for({"id": 1, "is_admin": True})
        result = self.client.get("/api/reports/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["approved_by_room"][0]["count"], 1)


class OccupancyReportTests(SimpleTestCase):
    def get(self, query, actor):
        token = token_for(actor)
        return self.client.get(f"/api/reports/occupancy/?{query}", HTTP_AUTHORIZATION=f"Bearer {token}")

    @patch("microservices.reports.views.call")
    def test_guardian_gets_occupancy_of_assigned_rooms_only(self, call):
        reservations = [
            # Monday 2026-12-07: 3 h approved, 1.5 h pending
            {"room_id": 1, "status": "approved", "start": "2026-12-07T09:00:00+01:00", "end": "2026-12-07T12:00:00+01:00"},
            {"room_id": 1, "status": "pending", "start": "2026-12-07T13:00:00+01:00", "end": "2026-12-07T14:30:00+01:00"},
            {"room_id": 1, "status": "rejected", "start": "2026-12-08T09:00:00+01:00", "end": "2026-12-08T17:00:00+01:00"},
        ]
        call.side_effect = remote_for(reservations, [{"room_id": 1, "user_id": 7}])
        result = self.get("start=2026-12-07&end=2026-12-08", {"id": 7, "is_admin": False})
        self.assertEqual(result.status_code, 200)
        data = result.json()
        self.assertEqual([room["room_id"] for room in data["rooms"]], [1])
        room = data["rooms"][0]
        self.assertEqual(room["available_hours"], 30)
        self.assertEqual(room["approved_hours"], 3)
        self.assertEqual(room["pending_hours"], 1.5)
        self.assertEqual(room["occupancy"], 10.0)
        self.assertEqual(data["total"]["occupancy"], 10.0)
        self.assertEqual(data["by_weekday"][0], {"weekday": 0, "available_hours": 15, "approved_hours": 3, "occupancy": 20.0})
        self.assertIn("room_id=1", call.side_effect.reservation_paths[0])
        self.assertNotIn("room_id=2", call.side_effect.reservation_paths[0])

    @patch("microservices.reports.views.call")
    def test_workdays_only_skips_weekend(self, call):
        call.side_effect = remote_for([], [])
        result = self.get("start=2026-12-05&end=2026-12-11&workdays=1", {"id": 1, "is_admin": True})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["day_count"], 5)
        self.assertEqual(result.json()["total"]["available_hours"], 5 * 15 * 2)

    @patch("microservices.reports.views.call")
    def test_user_without_rooms_is_forbidden(self, call):
        call.side_effect = remote_for([], [])
        result = self.get("start=2026-12-01&end=2026-12-31", {"id": 9, "is_admin": False})
        self.assertEqual(result.status_code, 403)

    @patch("microservices.reports.views.call")
    def test_guardian_cannot_request_foreign_room(self, call):
        call.side_effect = remote_for([], [{"room_id": 1, "user_id": 7}])
        result = self.get("start=2026-12-01&end=2026-12-31&room_id=2", {"id": 7, "is_admin": False})
        self.assertEqual(result.status_code, 403)

    def test_invalid_range_is_rejected(self):
        actor = {"id": 1, "is_admin": True}
        self.assertEqual(self.get("start=2026-12-10&end=2026-12-01", actor).status_code, 400)
        self.assertEqual(self.get("start=2025-01-01&end=2026-12-31", actor).status_code, 400)
        self.assertEqual(self.get("start=abc&end=2026-12-31", actor).status_code, 400)

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/reports/occupancy/?start=2026-12-01&end=2026-12-02").status_code, 401)
